# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual pad_frames dispatch with stationary guest frames and queued stop.

The parser and dispatch body come from the pinned implementation. CPU/video/
input hardware boundaries are stubs; this check does not run game code.
"""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from check_automation_queue import method

HARNESS = r'''
#include <atomic>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <stop_token>
#include <thread>
#include "automation_protocol.hpp"
using u32 = unsigned;
namespace Core {
enum class State { Running };
struct System { static System& GetInstance() { static System s; return s; } };
State GetState(System&) { return State::Running; }
}
namespace State { void SaveAs(Core::System&, std::string) {} void LoadAs(Core::System&, std::string) {} }
namespace moderngekko {
enum class RuntimeErrorCode { InvalidState };
struct RuntimeError { RuntimeErrorCode code; std::string message; };
struct RuntimeAutomationState { std::atomic<std::uint64_t> frame_count{0}; };
struct Runtime {
  struct Config { struct Settings { std::filesystem::path directory; } automation; } config;
  const Config& GetConfig() const { return config; }
  std::optional<RuntimeError> Pause() { return {}; }
  std::optional<RuntimeError> Resume() { return {}; }
  void RequestStop() {}
};
std::atomic<bool> held{false};
void ApplyAutomationPad(const automation::PadState&) { held = true; }
void ClearAutomationPad(int) { held = false; }
void MarkAutomationCommand(RuntimeAutomationState&, std::string) {}
auto NormalizeScreenshotPath(const std::filesystem::path& p) { return p; }
void SaveAutomationScreenshot(const std::filesystem::path&) {}
std::optional<RuntimeError> ReadAutomationMemory(const std::filesystem::path&, u32, u32) { return {}; }
std::optional<RuntimeError> WriteAutomationMemory(u32, const std::vector<std::uint8_t>&) { return {}; }
#include "dispatch.inc"
}
bool wait_for(auto predicate) {
  for (int n=0; n<100; ++n) { if (predicate()) return true; std::this_thread::sleep_for(std::chrono::milliseconds(10)); }
  return false;
}
int main(int argc, char** argv) {
  using namespace moderngekko;
  const std::filesystem::path root(argv[1]);
  std::filesystem::create_directories(root / "commands");
  Runtime runtime; runtime.config.automation.directory=root;
  RuntimeAutomationState state;
  automation::Command pad; pad.type=automation::CommandType::PadFrames; pad.frames=6000; pad.pad.port=0;
  std::optional<RuntimeError> error;
  std::atomic<bool> completed{false};
  std::jthread worker([&](std::stop_token token) { error=ApplyAutomationCommand(runtime,state,pad,token); completed=true; });
  if (!wait_for([] { return held.load(); })) { worker.request_stop(); worker.join(); return 2; }
  std::ofstream(root / "commands/0009-stop.ini") << "command=stop\n";
  bool interrupted = wait_for([&] { return completed.load(); });
  worker.request_stop(); worker.join();
  const bool stop_ok=interrupted && error.has_value() && !held.load() && std::filesystem::exists(root / "commands/0009-stop.ini");
  std::cout << (stop_ok ? "PASS" : "FAIL") << " queued stop interrupts pad_frames without guest progress and releases input\n";
  std::filesystem::rename(root / "commands/0009-stop.ini",root / "stop-receipt.ini");
  std::ofstream(root / "commands/0010-invalid.ini") << "command=wrong\n";
  state.frame_count=0; pad.frames=2; completed=false; error.reset();
  std::jthread normal([&](std::stop_token token) { error=ApplyAutomationCommand(runtime,state,pad,token); completed=true; });
  const bool started=wait_for([] { return held.load(); });
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  const bool not_interrupted=!completed.load();
  state.frame_count=2;
  const bool ended=wait_for([&] { return completed.load(); });
  normal.request_stop(); normal.join();
  const bool normal_ok=started && not_interrupted && ended && !error.has_value() && !held.load();
  std::cout << (normal_ok ? "PASS" : "FAIL") << " invalid queued command does not interrupt normal frame duration\n";
  return stop_ok && normal_ok ? 0 : 1;
}
'''


def main():
    root = Path(__file__).resolve().parents[1]
    upstream = root / 'local/vendor/ModernGekko'
    source = (upstream / 'src/runtime/dolphin_runtime.cpp').read_text(encoding='utf-8')
    extracted = method(source, 'std::optional<RuntimeError> ApplyAutomationCommand(')
    if 'bool AutomationStopPending(' in source:
        extracted = method(source, 'bool AutomationStopPending(') + '\n\n' + extracted
    build = root / 'local/build/pad-frame-shutdown-check'
    build.mkdir(parents=True, exist_ok=True)
    (build / 'dispatch.inc').write_text(extracted, encoding='utf-8')
    (build / 'check.cpp').write_text(HARNESS, encoding='utf-8')
    (build / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(PadFrameShutdownChecks LANGUAGES CXX)\n'
        'add_executable(pad_check check.cpp "' + upstream.as_posix() + '/tools/automation_protocol.cpp")\n'
        'target_include_directories(pad_check PRIVATE "' + upstream.as_posix() + '/tools" "'
        + upstream.as_posix() + '/vendor/dolphin/Source/Core")\n'
        'target_compile_features(pad_check PRIVATE cxx_std_23)\n', encoding='utf-8')
    run = root / ('local/analysis/pad-frame-shutdown-check-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    run.mkdir()
    with (run / 'build.log').open('w', encoding='utf-8') as log:
        subprocess.run(['cmake','-S',str(build),'-B',str(build/'cmake'),'-G','Visual Studio 17 2022','-A','x64'],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(build/'cmake'),'--config','Release'],stdout=log,stderr=subprocess.STDOUT,check=True)
    result = subprocess.run([str(build/'cmake/Release/pad_check.exe'),str(run)],capture_output=True,text=True)
    (run/'result.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'extracted_sha256':hashlib.sha256(extracted.encode()).hexdigest(),'exit_code':result.returncode,
        'checks':result.stdout.splitlines(),'errors':result.stderr,'scope':'Actual pad_frames dispatch and parser with stationary CPU/input hardware fixture; no game execution.'},indent=2)+'\n',encoding='utf-8')
    print(result.stdout,end=''); print('Evidence:',run)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
