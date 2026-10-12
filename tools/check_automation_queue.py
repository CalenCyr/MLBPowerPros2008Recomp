# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the actual command loop/parser with a transient Windows file lock.

Hardware command execution is replaced by a file receipt; parsing, queue order,
failed/processed moves and retry behavior use the pinned C++ implementation.
"""
import hashlib
import json
import subprocess
from pathlib import Path


def method(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


HARNESS = r'''
#define NOMINMAX
#include <windows.h>
#include <atomic>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <stop_token>
#include <string>
#include <thread>
#include "automation_protocol.hpp"
namespace moderngekko {
struct RuntimeError { std::string message; };
struct RuntimeAutomationState { std::atomic<bool> saw_error{false}; };
struct Runtime {
  std::filesystem::path receipt;
};
struct Impl {
  struct Config {
    struct Settings { std::filesystem::path directory; } automation;
  } config;
  RuntimeAutomationState automation_state;
};
void SetAutomationError(RuntimeAutomationState& s, std::string) { s.saw_error = true; }
bool AutomationCommandNeedsReadyCore(automation::CommandType) { return false; }
bool AutomationCoreIsReady() { return true; }
void WriteAutomationStatus(const std::filesystem::path&, Impl&) {}
std::optional<RuntimeError> ApplyAutomationCommand(Runtime& r, RuntimeAutomationState&,
    const automation::Command& c, std::stop_token) {
  std::ofstream(r.receipt, std::ios::app) << c.source_name << '\n';
  return {};
}
#include "loop.inc"
}
bool wait_for(auto predicate) {
  for (int n = 0; n < 200; ++n) {
    if (predicate()) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return false;
}
int main(int argc, char** argv) {
  using namespace moderngekko;
  const auto root = std::filesystem::path(argv[1]);
  const auto locked_root = root / "locked";
  EnsureAutomationDirectories(locked_root);
  const auto command = locked_root / "commands/0000-stop.ini";
  std::ofstream(command) << "command=stop\n";
  HANDLE lock = CreateFileW(command.c_str(), GENERIC_WRITE, FILE_SHARE_DELETE,
                           nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (lock == INVALID_HANDLE_VALUE) { std::cerr << "fixture lock failed\n"; return 2; }
  Impl impl; impl.config.automation.directory = locked_root;
  Runtime runtime{locked_root / "receipt.txt"};
  std::jthread worker([&](std::stop_token token) { AutomationLoop(runtime, impl, token); });
  const bool saw_error = wait_for([&] { return impl.automation_state.saw_error.load(); });
  std::this_thread::sleep_for(std::chrono::milliseconds(150));
  const bool retained = std::filesystem::exists(command);
  CloseHandle(lock);
  const bool processed = wait_for([&] { return std::filesystem::exists(locked_root / "processed/0000-stop.ini"); });
  worker.request_stop(); worker.join();
  std::ifstream receipt(runtime.receipt);
  std::string first, second; std::getline(receipt, first); std::getline(receipt, second);
  const bool recovered = saw_error && retained && processed && first == "0000-stop.ini" && second.empty()
      && !std::filesystem::exists(locked_root / "failed/0000-stop.ini");
  std::cout << (recovered ? "PASS" : "FAIL") << " valid command survives transient open failure\n";

  const auto bad_root = root / "malformed";
  EnsureAutomationDirectories(bad_root);
  std::ofstream(bad_root / "commands/0000-invalid.ini") << "command=not-a-command\n";
  Impl bad_impl; bad_impl.config.automation.directory = bad_root;
  Runtime bad_runtime{bad_root / "receipt.txt"};
  std::jthread bad_worker([&](std::stop_token token) { AutomationLoop(bad_runtime, bad_impl, token); });
  const bool rejected = wait_for([&] { return std::filesystem::exists(bad_root / "failed/0000-invalid.ini"); });
  bad_worker.request_stop(); bad_worker.join();
  const bool invalid = rejected && !std::filesystem::exists(bad_runtime.receipt);
  std::cout << (invalid ? "PASS" : "FAIL") << " malformed command is rejected without execution\n";
  return recovered && invalid ? 0 : 1;
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    upstream = root / 'local/vendor/ModernGekko'
    source = (upstream / 'src/runtime/dolphin_runtime.cpp').read_text(encoding='utf-8')
    extracted = '\n\n'.join(method(source, signature) for signature in (
        'void EnsureAutomationDirectories(', 'void MoveAutomationCommand(',
        'template <typename ImplT>\nvoid AutomationLoop('))
    build = root / 'local/build/automation-queue-check'
    build.mkdir(parents=True, exist_ok=True)
    (build / 'loop.inc').write_text(extracted, encoding='utf-8')
    (build / 'check.cpp').write_text(HARNESS, encoding='utf-8')
    (build / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(AutomationQueueChecks LANGUAGES CXX)\n'
        'add_executable(queue_check check.cpp "' + upstream.as_posix() + '/tools/automation_protocol.cpp")\n'
        'target_include_directories(queue_check PRIVATE "' + upstream.as_posix() + '/tools" "'
        + upstream.as_posix() + '/vendor/dolphin/Source/Core")\n'
        'target_compile_features(queue_check PRIVATE cxx_std_23)\n', encoding='utf-8')
    import datetime
    run = root / ('local/analysis/automation-queue-check-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    run.mkdir()
    with (run / 'build.log').open('w', encoding='utf-8') as output:
        subprocess.run(['cmake', '-S', str(build), '-B', str(build / 'cmake'), '-G', 'Visual Studio 17 2022', '-A', 'x64'], stdout=output, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['cmake', '--build', str(build / 'cmake'), '--config', 'Release'], stdout=output, stderr=subprocess.STDOUT, check=True)
    result = subprocess.run([str(build / 'cmake/Release/queue_check.exe'), str(run)], capture_output=True, text=True)
    (run / 'result.json').write_text(json.dumps({'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'extracted_sha256': hashlib.sha256(extracted.encode()).hexdigest(), 'exit_code': result.returncode,
        'checks': result.stdout.splitlines(), 'errors': result.stderr,
        'scope': 'Actual automation loop and parser; Windows sharing lock. Hardware command body replaced with file receipt.'}, indent=2) + '\n', encoding='utf-8')
    print(result.stdout, end='')
    print('Evidence:', run)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
