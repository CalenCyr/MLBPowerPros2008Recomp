// SPDX-License-Identifier: GPL-3.0-or-later
// Diagnostic point samples of our Windows x64 runtime; not an ETW CPU profiler.
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <map>
#include <random>
#include <string>

struct Handle
{
  HANDLE value = nullptr;
  explicit Handle(HANDLE v = nullptr) : value(v) {}
  ~Handle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
  Handle(const Handle&) = delete;
  Handle& operator=(const Handle&) = delete;
};

struct ThreadInfo
{
  HANDLE handle = nullptr;
  DWORD id = 0;
  ULONG64 start_cycles = 0;
  unsigned long long start_user = 0, start_kernel = 0;
  std::string name;
};

unsigned long long Ticks(FILETIME t)
{
  return (static_cast<unsigned long long>(t.dwHighDateTime) << 32) | t.dwLowDateTime;
}

bool Times(HANDLE h, unsigned long long& user, unsigned long long& kernel)
{
  FILETIME created{}, exited{}, k{}, u{};
  if (!GetThreadTimes(h, &created, &exited, &k, &u)) return false;
  user = Ticks(u); kernel = Ticks(k); return true;
}

std::string ThreadName(HANDLE h)
{
  PWSTR name = nullptr;
  if (FAILED(GetThreadDescription(h, &name))) return "";
  std::string result;
  for (const wchar_t* p = name; *p; ++p)
    result += *p >= 32 && *p <= 126 && *p != '"' ? static_cast<char>(*p) : '_';
  LocalFree(name);
  return result;
}

void Discover(DWORD pid, std::map<DWORD, ThreadInfo>& threads)
{
  Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0));
  if (snapshot.value == INVALID_HANDLE_VALUE) return;
  THREADENTRY32 entry{}; entry.dwSize = sizeof(entry);
  if (!Thread32First(snapshot.value, &entry)) return;
  do
  {
    if (entry.th32OwnerProcessID != pid || threads.count(entry.th32ThreadID)) continue;
    HANDLE h = OpenThread(THREAD_QUERY_INFORMATION | THREAD_GET_CONTEXT | THREAD_SUSPEND_RESUME,
                          FALSE, entry.th32ThreadID);
    if (!h) continue;
    ThreadInfo t; t.handle = h; t.id = entry.th32ThreadID;
    QueryThreadCycleTime(h, &t.start_cycles);
    Times(h, t.start_user, t.start_kernel);
    t.name = ThreadName(h);
    threads.emplace(t.id, t);
  } while (Thread32Next(snapshot.value, &entry));
}

// Returns the main executable range (first module) for stack-scan caller hints.
std::pair<ULONG64, ULONG64> Modules(DWORD pid, const std::filesystem::path& out)
{
  Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid));
  if (snapshot.value == INVALID_HANDLE_VALUE) throw std::runtime_error("module snapshot failed");
  std::ofstream f(out / "modules.csv");
  f << "base,size,path\n";
  MODULEENTRY32W m{}; m.dwSize = sizeof(m);
  if (!Module32FirstW(snapshot.value, &m)) throw std::runtime_error("module enumeration failed");
  const std::pair<ULONG64, ULONG64> exe{reinterpret_cast<ULONG64>(m.modBaseAddr),
                                        reinterpret_cast<ULONG64>(m.modBaseAddr) + m.modBaseSize};
  do
  {
    // This project's paths are ASCII. Fail rather than corrupt a Unicode path.
    std::string path;
    for (const wchar_t* p = m.szExePath; *p; ++p)
    {
      if (*p > 127) throw std::runtime_error("non-ASCII module path");
      path += static_cast<char>(*p);
    }
    f << reinterpret_cast<unsigned long long>(m.modBaseAddr) << ',' << m.modBaseSize
      << ",\"" << path << "\"\n";
  } while (Module32NextW(snapshot.value, &m));
  if (!f) throw std::runtime_error("module write failed");
  return exe;
}

int main(int argc, char** argv)
{
#if !defined(_M_X64)
#error This diagnostic requires Windows x64.
#endif
  if (argc != 5 && argc != 6) { std::fprintf(stderr, "usage: sampler PID SECONDS OUTPUT EXPECTED_EXE [RANK]\n"); return 2; }
  DWORD pid = static_cast<DWORD>(std::strtoul(argv[1], nullptr, 10));
  int seconds = std::atoi(argv[2]);
  if (!pid || seconds < 1 || seconds > 300) return 2;
  Handle process(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | SYNCHRONIZE, FALSE, pid));
  wchar_t image[32768]; DWORD length = 32768;
  if (!process.value || !QueryFullProcessImageNameW(process.value, 0, image, &length)) return 3;
  if (!std::filesystem::equivalent(std::filesystem::path(image), std::filesystem::path(argv[4])))
    { std::fprintf(stderr, "refusing unexpected executable\n"); return 3; }
  const std::filesystem::path out(argv[3]);
  std::filesystem::create_directories(out);
  std::map<DWORD, ThreadInfo> threads;
  Discover(pid, threads);
  Sleep(1000);
  // RANK picks the Nth busiest thread over the warm-up second (0, the default, is the busiest).
  std::vector<std::pair<ULONG64, DWORD>> busy;
  for (auto& pair : threads)
  {
    ULONG64 cycles = 0;
    if (QueryThreadCycleTime(pair.second.handle, &cycles)) busy.emplace_back(cycles - pair.second.start_cycles, pair.first);
  }
  std::sort(busy.rbegin(), busy.rend());
  const size_t rank = argc == 6 ? std::strtoul(argv[5], nullptr, 10) : 0;
  if (rank >= busy.size() || !busy[rank].first) return 4;
  const DWORD selected = busy[rank].second;
  // Fix the selected thread for the whole run; report other threads' CPU time separately.
  for (auto& pair : threads)
  {
    QueryThreadCycleTime(pair.second.handle, &pair.second.start_cycles);
    Times(pair.second.handle, pair.second.start_user, pair.second.start_kernel);
  }
  HANDLE thread = threads.at(selected).handle;
  const auto exe = Modules(pid, out);
  // Heuristic caller hints: executable-range qwords near RSP. Stale slots are possible.
  std::ofstream stacks(out / "stacks.csv");
  stacks << "elapsed_ns,exe_stack_hits\n";
  static ULONG64 stack[512];
  std::ofstream samples(out / "samples.csv");
  samples << "elapsed_ns,tid,rip,cycles_since_last,suspend_ns\n";
  ULONG64 last_cycles = 0; QueryThreadCycleTime(thread, &last_cycles);
  unsigned successful = 0, inactive = 0, failed = 0;
  unsigned long long suspended_ns = 0;
  std::mt19937 random(0x524C3845);
  std::uniform_int_distribution<int> delay(7, 17);
  using Clock = std::chrono::steady_clock;
  const auto begin = Clock::now();
  while (Clock::now() - begin < std::chrono::seconds(seconds) &&
         WaitForSingleObject(process.value, 0) == WAIT_TIMEOUT)
  {
    Sleep(delay(random));
    ULONG64 cycles = 0;
    if (!QueryThreadCycleTime(thread, &cycles)) { ++failed; continue; }
    const ULONG64 delta = cycles - last_cycles;
    last_cycles = cycles;
    if (!delta) { ++inactive; continue; }
    const auto start = Clock::now();
    const DWORD previous = SuspendThread(thread);
    if (previous == static_cast<DWORD>(-1)) { ++failed; continue; }
    CONTEXT context{}; context.ContextFlags = CONTEXT_CONTROL;
    const bool valid = GetThreadContext(thread, &context) != 0;
    SIZE_T stack_bytes = 0;
    if (valid && !ReadProcessMemory(process.value, reinterpret_cast<LPCVOID>(context.Rsp), stack,
                                    sizeof(stack), &stack_bytes))
      stack_bytes = 0;
    // Resume immediately, before allocation, file I/O or any symbol lookup.
    const DWORD resumed = ResumeThread(thread);
    if (resumed == static_cast<DWORD>(-1))
      { std::fprintf(stderr, "ResumeThread failed: %lu\n", GetLastError()); return 5; }
    const auto end = Clock::now();
    const auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    suspended_ns += duration;
    if (!valid || previous != 0) { ++failed; continue; }
    ++successful;
    samples << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count()
            << ',' << selected << ',' << context.Rip << ',' << delta << ',' << duration << '\n';
    stacks << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count() << ',';
    for (SIZE_T i = 0, hits = 0; i < stack_bytes / 8 && hits < 8; ++i)
      if (stack[i] >= exe.first && stack[i] < exe.second)
        stacks << (hits++ ? ";" : "") << stack[i];
    stacks << '\n';
  }
  const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - begin).count();
  std::ofstream summary(out / "summary.txt");
  summary << "pid=" << pid << "\nselected_tid=" << selected << "\nselected_name="
          << threads.at(selected).name << "\nelapsed_ns=" << elapsed << "\nsamples=" << successful
          << "\ninactive=" << inactive << "\nfailed=" << failed << "\nsuspend_ns=" << suspended_ns << '\n';
  std::ofstream totals(out / "threads.csv");
  totals << "tid,name,cycles,user_100ns,kernel_100ns\n";
  for (const auto& pair : threads)
  {
    ULONG64 cycles = 0; unsigned long long user = 0, kernel = 0;
    const auto& t = pair.second;
    if (QueryThreadCycleTime(t.handle, &cycles) && Times(t.handle, user, kernel))
      totals << t.id << ",\"" << t.name << "\"," << cycles - t.start_cycles << ','
             << user - t.start_user << ',' << kernel - t.start_kernel << '\n';
    CloseHandle(t.handle);
  }
  if (!samples || !summary || !totals || !successful) return 6;
  std::printf("sampled %u instruction pointers from tid %lu (%s)\n", successful, selected,
              threads.at(selected).name.c_str());
}
