# Direct match benchmark implementation plan

> **For agentic workers:** Use inline execution with the executing-plans workflow. Steps use checkbox syntax for tracking.

**Goal:** Start a repeatable Yankees–Colorado match without navigating the launcher or game menus, with live graphics controls and measurements saved for GPU diagnosis.

**Architecture:** An opt-in RL8E54 runtime hook at the guest's retrace boundary uses the game's scene manager and original match initialization routines. Benchmark settings are transient; ordinary launches and the player's stored configuration remain independent. Aurora measures GPU command execution asynchronously; the overlay records every presented frame within a wall-clock measurement window.

**Tech Stack:** C++17 runtime, PowerPC translated entry points, Aurora/Dawn, ImGui, PowerShell diagnostic runner.

---

### 1. Prove direct match initialization

- [x] Identify native scene transitions and original team/roster initialization.
- [x] Add `runtime/tests/match_benchmark_tests.cpp`; observe compilation fail without its header.
- [x] Add `runtime/include/match_benchmark.h` and `runtime/src/match_benchmark.cpp`, gated by `WIICOMPILED_MATCH_BENCH=1` and RL8E54.
- [x] Hook `runtime/src/hle/vi.cpp` before interrupts are disabled; preserve the complete guest CPU context around original helpers.
- [x] Verify two cold launches reach the actual playing field with the same teams and stadium, without an input script.
- [x] Record which original initialization remains necessary and distinguish automated CPU gameplay from a frozen reproducible frame.

### 2. Graphics and measurement controls

- [x] Add x1/x2/x3/x4, Force 16:9, and existing graphics settings access to the benchmark overlay in `runtime/src/settings_overlay.cpp`.
- [x] Keep benchmark changes in memory through `runtime/include/runtime_config.h`; accept explicit startup resolution/aspect/backend overrides.
- [x] Add asynchronous timestamp query slots under `aurora-main/lib/webgpu/gpu_timing.hpp`, request optional timestamp support in `gpu.cpp`, and bracket the encoded render workload in `aurora.cpp`.
- [x] Report unsupported GPU timing as unavailable. Distinguish GPU execution from CPU encoding and presentation pacing.
- [x] Record all frames during a wall-clock measurement window, with warmup and settings-change restart. Save CSV and a compact summary, including EFB copies/readbacks and shader compilation status.

### 3. Make the mode runnable and reproducible

- [x] Add a direct benchmark entry in the build directory and a PowerShell runner under `tools/` for graphics preset comparisons and Windows process GPU utilization sampling.
- [x] Integrate the transition unit test into CMake; run it, configuration tests, and GPU readback tests.
- [x] Validate x1 and x4 plus Force 16:9 toggling in the compiled build. Check the normal Config.toml hash remains unchanged.
- [x] Export the runtime changes as a new reproducible patch under `tools/patches/`, include it after the existing EFB snapshot patch in `tools/wiicompiled-translate.ps1`, and replay the complete patch sequence against pinned upstream.
- [x] Document usage, evidence, and remaining measurement limitations in `docs/wiicompiled-feasibility.md`.
