// SPDX-License-Identifier: GPL-3.0-or-later
// Runs the game with WIICOMPILED_TEXTURE_DUMPS=1 (patch wiicompiled-texture-studio) and the launcher
// skipped, then keeps the textures it dumped as a numbered capture session.
#include "capture.h"

#include "core.h"

#include <windows.h>

#include <algorithm>
#include <cstdlib>

namespace tstudio {
namespace {
std::set<std::string> Names(const std::filesystem::path& dir) {
    std::set<std::string> out;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(dir, ec)) out.insert(Utf8(e.path().filename()));
    return out;
}
} // namespace

void Capture::SeedForTest(const std::filesystem::path& dumpsDir) {
    dumps_ = dumpsDir;
    before_ = Names(dumpsDir);
}

bool Capture::Start(const std::filesystem::path& gameExe, const std::filesystem::path& dumpsDir, std::string* error) {
    SeedForTest(dumpsDir);
    std::wstring command = L"\"" + gameExe.wstring() + L"\"";
    SetEnvironmentVariableW(L"WIICOMPILED_TEXTURE_DUMPS", L"1");
    SetEnvironmentVariableW(L"WIICOMPILED_SKIP_LAUNCHER", L"1");
    STARTUPINFOW si{};
    si.cb = sizeof si;
    PROCESS_INFORMATION pi{};
    const BOOL ok = CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, 0, nullptr,
                                   gameExe.parent_path().c_str(), &si, &pi);
    SetEnvironmentVariableW(L"WIICOMPILED_TEXTURE_DUMPS", nullptr);
    SetEnvironmentVariableW(L"WIICOMPILED_SKIP_LAUNCHER", nullptr);
    if (!ok) {
        if (error) *error = "No se pudo abrir el juego para capturar (" + std::to_string(GetLastError()) + ").";
        return false;
    }
    CloseHandle(pi.hThread);
    process_ = pi.hProcess;
    return true;
}

bool Capture::Running() const {
    return process_ != nullptr && WaitForSingleObject(static_cast<HANDLE>(process_), 0) == WAIT_TIMEOUT;
}

std::pair<int, std::vector<std::filesystem::path>> Capture::Collect(const std::filesystem::path& capturesDir) {
    if (process_) {
        CloseHandle(static_cast<HANDLE>(process_));
        process_ = nullptr;
    }
    std::vector<std::filesystem::path> fresh;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(dumps_, ec))
        if (e.is_regular_file(ec) && !before_.count(Utf8(e.path().filename()))) fresh.push_back(e.path());
    if (fresh.empty()) return {0, {}};
    int n = 1;
    for (const auto& [session, _] : LoadSessions(capturesDir)) n = std::max(n, session + 1);
    const auto dir = capturesDir / std::to_string(n);
    std::filesystem::create_directories(dir, ec);
    std::vector<std::filesystem::path> moved;
    for (const auto& f : fresh) {
        const auto target = dir / f.filename();
        std::filesystem::rename(f, target, ec);
        if (ec) {
            ec.clear();
            std::filesystem::copy_file(f, target, ec);
            if (ec) continue;  // left in the dump folder; not part of this session
            std::filesystem::remove(f, ec);
        }
        moved.push_back(target);
    }
    return {n, moved};
}

std::vector<std::pair<int, std::vector<std::filesystem::path>>> LoadSessions(const std::filesystem::path& capturesDir) {
    std::vector<std::pair<int, std::vector<std::filesystem::path>>> out;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(capturesDir, ec)) {
        const int n = std::atoi(Utf8(e.path().filename()).c_str());
        if (!e.is_directory(ec) || n <= 0) continue;
        std::vector<std::filesystem::path> files;
        for (const auto& f : std::filesystem::directory_iterator(e.path(), ec)) files.push_back(f.path());
        out.emplace_back(n, std::move(files));
    }
    std::sort(out.begin(), out.end());
    return out;
}

} // namespace tstudio
