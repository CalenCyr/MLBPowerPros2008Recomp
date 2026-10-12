// SPDX-License-Identifier: GPL-3.0-or-later
// MLB Power Pros 2008 Setup. The player picks their own disc image; workspace\LocalBuild.ps1 then
// extracts it, translates the game code and compiles the native game on this PC. This program
// ships no game code or assets: it only drives the bundled toolchain and shows progress, in the
// style of the game's own menus (power_pros_ui.h, shared with the in-game launcher).
#include "power_pros_ui.h"

#include <SDL3/SDL.h>
#include <backends/imgui_impl_sdl3.h>
#include <backends/imgui_impl_sdlrenderer3.h>

#include <windows.h>
#include <shellapi.h>

#include <atomic>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <mutex>
#include <string>
#include <thread>

using namespace power_pros_ui;
namespace fs = std::filesystem;

namespace {

std::wstring Wide(const std::string& s) {
    std::wstring w(MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, w.data(), static_cast<int>(w.size()));
    w.pop_back();
    return w;
}

std::string Utf8(const fs::path& p) {
    const std::u8string s = p.u8string();
    return std::string(s.begin(), s.end());
}

// One run of LocalBuild.ps1 in a hidden PowerShell, inside a job object so cancelling or closing
// the Setup also stops every compiler it started.
struct Build {
    std::mutex mutex;
    int percent = 0;
    std::string message;
    std::string error;
    std::deque<std::string> tail;
    std::atomic<bool> running{false};
    std::atomic<bool> finished{false};
    std::atomic<bool> succeeded{false};
    HANDLE job = nullptr;
    std::thread reader;

    void Start(const fs::path& script, const std::string& iso, const fs::path& install, bool shortcut) {
        Stop();
        percent = 0;
        message = "Preparando...";
        error.clear();
        tail.clear();
        finished = false;
        succeeded = false;
        fs::create_directories(install);
        std::wstring command = L"powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" +
                               script.wstring() + L"\" -Iso \"" + Wide(iso) + L"\" -Install \"" + install.wstring() +
                               L"\"" + (shortcut ? L" -Shortcut" : L"");
        SECURITY_ATTRIBUTES sa{sizeof(sa), nullptr, TRUE};
        HANDLE readPipe = nullptr;
        HANDLE writePipe = nullptr;
        CreatePipe(&readPipe, &writePipe, &sa, 0);
        SetHandleInformation(readPipe, HANDLE_FLAG_INHERIT, 0);
        STARTUPINFOW si{};
        si.cb = sizeof(si);
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdOutput = writePipe;
        si.hStdError = writePipe;
        si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
        PROCESS_INFORMATION pi{};
        job = CreateJobObjectW(nullptr, nullptr);
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits));
        const bool started = CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE,
                                            CREATE_NO_WINDOW | CREATE_SUSPENDED, nullptr,
                                            script.parent_path().c_str(), &si, &pi);
        CloseHandle(writePipe);
        if (!started) {
            CloseHandle(readPipe);
            error = "No se pudo iniciar PowerShell.";
            finished = true;
            return;
        }
        AssignProcessToJobObject(job, pi.hProcess);
        ResumeThread(pi.hThread);
        CloseHandle(pi.hThread);
        running = true;
        const fs::path logPath = install / "setup.log";
        reader = std::thread([this, readPipe, process = pi.hProcess, logPath] {
            FILE* log = _wfopen(logPath.c_str(), L"wb");
            std::string pending;
            char buffer[4096];
            DWORD got = 0;
            while (ReadFile(readPipe, buffer, sizeof(buffer), &got, nullptr) && got > 0) {
                if (log != nullptr) fwrite(buffer, 1, got, log);
                pending.append(buffer, got);
                for (size_t nl; (nl = pending.find('\n')) != std::string::npos;) {
                    std::string line = pending.substr(0, nl);
                    pending.erase(0, nl + 1);
                    if (!line.empty() && line.back() == '\r') line.pop_back();
                    OnLine(line);
                }
            }
            if (log != nullptr) fclose(log);
            CloseHandle(readPipe);
            WaitForSingleObject(process, INFINITE);
            DWORD code = 1;
            GetExitCodeProcess(process, &code);
            CloseHandle(process);
            {
                std::lock_guard lock(mutex);
                if (code != 0 && error.empty()) error = "La instalación falló. Revisa setup.log.";
            }
            succeeded = code == 0;
            running = false;
            finished = true;
        });
    }

    void OnLine(const std::string& line) {
        std::lock_guard lock(mutex);
        if (line.rfind("@@ERROR ", 0) == 0) {
            error = line.substr(8);
        } else if (line.rfind("@@ ", 0) == 0) {
            const size_t space = line.find(' ', 3);
            percent = std::atoi(line.c_str() + 3);
            message = space == std::string::npos ? "" : line.substr(space + 1);
        } else if (!line.empty()) {
            tail.push_back(line.size() > 140 ? line.substr(0, 140) + "..." : line);
            while (tail.size() > 4) tail.pop_front();
        }
    }

    void Stop() {
        if (job != nullptr) {
            TerminateJobObject(job, 1);
            CloseHandle(job);
            job = nullptr;
        }
        if (reader.joinable()) reader.join();
        running = false;
    }
};

struct DialogResult {
    std::mutex mutex;
    std::string path;
    bool ready = false;
};

void SDLCALL OnDialog(void* userdata, const char* const* files, int) {
    auto* result = static_cast<DialogResult*>(userdata);
    std::lock_guard lock(result->mutex);
    result->path = files != nullptr && files[0] != nullptr ? files[0] : "";
    result->ready = true;
}

} // namespace

int main(int, char**) {
    SetProcessDPIAware();
    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD)) return 1;
    SDL_Window* window = SDL_CreateWindow("MLB Power Pros 2008 - Instalación", 1280, 720,
                                          SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);
    SDL_SetRenderVSync(renderer, 1);
    ImGui::CreateContext();
    ImGui::GetIO().IniFilename = nullptr;
    ImGui::GetIO().ConfigFlags |= ImGuiConfigFlags_NavEnableGamepad;
    ImGui_ImplSDL3_InitForSDLRenderer(window, renderer);
    ImGui_ImplSDLRenderer3_Init(renderer);
    LoadFonts();

    const fs::path base = fs::path(SDL_GetBasePath());
    const fs::path script = base / "workspace" / "LocalBuild.ps1";
    fs::path install = base / "MLB Power Pros 2008";
    auto gameExe = [&] { return install / "Game" / "MLBPowerPros2008.exe"; };
    // A disc image dropped onto the exe (or passed as the first argument) is preselected.
    std::string iso;
    if (int count = 0; LPWSTR* args = CommandLineToArgvW(GetCommandLineW(), &count)) {
        if (count > 1) iso = Utf8(fs::path(args[1]));
        LocalFree(args);
    }
    bool shortcut = true;
    // MLBPP_SETUP_AUTOINSTALL=1 (scripted tests): start installing the preselected image right away,
    // without a desktop shortcut.
    const char* autoInstall = std::getenv("MLBPP_SETUP_AUTOINSTALL");
    const bool autoStart = autoInstall != nullptr && std::strcmp(autoInstall, "1") == 0 && !iso.empty();
    if (autoStart) shortcut = false;
    Build build;
    DialogResult isoDialog;
    DialogResult folderDialog;
    enum class Screen { Welcome, Building, Done, Failed } screen = Screen::Welcome;
    int menu = 0;
    const Uint64 start = SDL_GetTicks();
    Uint64 buildStart = 0;
    bool quit = false;
    if (autoStart) {
        build.Start(script, iso, install, shortcut);
        buildStart = SDL_GetTicks();
        screen = Screen::Building;
    }

    while (!quit) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            ImGui_ImplSDL3_ProcessEvent(&event);
            if (event.type == SDL_EVENT_QUIT) quit = true;
        }
        {
            std::lock_guard lock(isoDialog.mutex);
            if (isoDialog.ready) {
                isoDialog.ready = false;
                if (!isoDialog.path.empty()) iso = isoDialog.path, menu = 0;
            }
        }
        {
            std::lock_guard lock(folderDialog.mutex);
            if (folderDialog.ready) {
                folderDialog.ready = false;
                if (!folderDialog.path.empty()) install = fs::u8path(folderDialog.path) / "MLB Power Pros 2008";
            }
        }
        if (screen == Screen::Building && build.finished) screen = build.succeeded ? Screen::Done : Screen::Failed;

        ImGui_ImplSDLRenderer3_NewFrame();
        ImGui_ImplSDL3_NewFrame();
        ImGui::NewFrame();
        const ImVec2 size = ImGui::GetMainViewport()->Size;
        const float w = size.x;
        const float h = size.y;
        const float u = std::min(h, w * 0.75f) / 720.0f;
        const float t = static_cast<float>(SDL_GetTicks() - start) / 1000.0f;
        ImDrawList* dl = ImGui::GetBackgroundDrawList();
        DrawBackground(dl, w, h, u, t, g_title);
        const bool click = ImGui::IsMouseClicked(ImGuiMouseButton_Left);
        const bool focused = (SDL_GetWindowFlags(window) & SDL_WINDOW_INPUT_FOCUS) != 0;
        auto pressed = [&](std::initializer_list<ImGuiKey> keys) {
            if (!focused) return false;
            for (ImGuiKey key : keys) {
                if (ImGui::IsKeyPressed(key, true)) return true;
            }
            return false;
        };
        const bool left = pressed({ImGuiKey_LeftArrow, ImGuiKey_UpArrow, ImGuiKey_GamepadDpadLeft, ImGuiKey_GamepadLStickLeft});
        const bool right = pressed({ImGuiKey_RightArrow, ImGuiKey_DownArrow, ImGuiKey_GamepadDpadRight, ImGuiKey_GamepadLStickRight});
        const bool accept = pressed({ImGuiKey_Enter, ImGuiKey_KeypadEnter, ImGuiKey_Space, ImGuiKey_GamepadFaceDown});

        // Title.
        const float cx = w * 0.5f;
        LogoTextCentered(dl, g_title, 34 * u, cx - 150 * u, h * 0.09f, Rgba(110, 170, 255), Rgba(24, 70, 180), "MLB");
        const ImVec2 ts = LogoTextCentered(dl, g_title, 84 * u, cx, h * 0.09f + 30 * u, Rgba(255, 110, 96),
                                           Rgba(196, 18, 30), "POWER PROS");
        LogoText(dl, g_title, 46 * u, ImVec2(cx + ts.x * 0.5f - 130 * u, h * 0.09f + 114 * u), Rgba(255, 96, 70),
                 Rgba(200, 16, 20), "2008", Rgba(255, 224, 70));

        // Pills for the current screen.
        struct Item {
            const char* label;
            ImU32 top, bottom, rim;
        };
        const Item orange{"", Rgba(255, 206, 96), Rgba(240, 112, 18), Rgba(150, 50, 0)};
        const Item green{"", Rgba(160, 244, 120), Rgba(34, 164, 58), Rgba(10, 90, 30)};
        const Item purple{"", Rgba(244, 160, 244), Rgba(168, 64, 200), Rgba(90, 20, 120)};
        std::vector<std::pair<const char*, Item>> items;
        const bool installed = fs::exists(gameExe());
        switch (screen) {
        case Screen::Welcome:
            if (installed) items.push_back({"JUGAR", orange});
            items.push_back({iso.empty() ? "ELEGIR DISCO" : (installed ? "REINSTALAR" : "INSTALAR"), installed ? green : orange});
            if (!iso.empty() || installed) items.push_back({iso.empty() ? "OTRO DISCO" : "CAMBIAR DISCO", installed ? purple : green});
            items.push_back({"SALIR", purple});
            break;
        case Screen::Building: items.push_back({"CANCELAR", purple}); break;
        case Screen::Done: items.push_back({"JUGAR", orange}); items.push_back({"SALIR", purple}); break;
        case Screen::Failed: items.push_back({"REINTENTAR", orange}); items.push_back({"VER REGISTRO", green}); items.push_back({"SALIR", purple}); break;
        }
        const int n = static_cast<int>(items.size());
        menu = std::clamp(menu, 0, n - 1);
        if (left) menu = (menu + n - 1) % n;
        if (right) menu = (menu + 1) % n;
        const float pillW = std::min(250 * u, (w * 0.9f - 30 * u * static_cast<float>(n - 1)) / static_cast<float>(n));
        const float pillH = 78 * u;
        const float gap = 30 * u;
        const float rowX = cx - (pillW * static_cast<float>(n) + gap * static_cast<float>(n - 1)) * 0.5f;
        const float rowY = h * 0.42f;
        const char* activated = nullptr;
        for (int i = 0; i < n; ++i) {
            const bool selected = menu == i;
            const float grow = selected ? 1.08f : 1.0f;
            const ImVec2 c(rowX + pillW * 0.5f + static_cast<float>(i) * (pillW + gap),
                           rowY + pillH * 0.5f + (selected ? std::sin(t * 4.0f) * 3.0f * u : 0.0f));
            const ImVec2 a(c.x - pillW * 0.5f * grow, c.y - pillH * 0.5f * grow);
            const ImVec2 b(c.x + pillW * 0.5f * grow, c.y + pillH * 0.5f * grow);
            const ImVec2 m = ImGui::GetIO().MousePos;
            const bool hover = m.x >= a.x && m.x < b.x && m.y >= a.y && m.y < b.y;
            if (hover && (ImGui::GetIO().MouseDelta.x != 0 || ImGui::GetIO().MouseDelta.y != 0)) menu = i;
            if (hover && click) activated = items[static_cast<size_t>(i)].first;
            if (selected) {
                const float pulse = 0.5f + 0.5f * std::sin(t * 5.0f);
                const float e = (10 + 4 * pulse) * u;
                dl->AddRectFilled(ImVec2(a.x - e, a.y - e), ImVec2(b.x + e, b.y + e),
                                  Rgba(255, 244, 140, static_cast<int>(140 + 70 * pulse)), (b.y - a.y) * 0.5f + e);
            }
            const Item& item = items[static_cast<size_t>(i)].second;
            Pill(dl, a, b, item.top, item.bottom, u, selected ? Rgba(255, 250, 200) : IM_COL32_WHITE);
            const char* label = items[static_cast<size_t>(i)].first;
            float fs = 32 * u * grow;
            while (TextSize(g_title, fs, label).x > (b.x - a.x) * 0.84f) fs *= 0.92f;
            LogoTextCentered(dl, g_title, fs, c.x, c.y - fs * 0.62f, IM_COL32_WHITE, Rgba(255, 240, 190), label,
                             item.rim, Rgba(255, 255, 255, 0));
        }
        if (accept) activated = items[static_cast<size_t>(menu)].first;

        // Info box.
        const ImVec2 ia(w * 0.06f, h * 0.60f);
        const ImVec2 ib(w * 0.94f, h * 0.88f);
        dl->AddRectFilled(ImVec2(ia.x, ia.y + 6 * u), ImVec2(ib.x, ib.y + 6 * u), Rgba(0, 20, 70, 110), 16 * u);
        dl->AddRectFilled(ia, ib, IM_COL32_WHITE, 16 * u);
        const int infoStart = dl->VtxBuffer.Size;
        dl->AddRectFilled(ImVec2(ia.x + 4 * u, ia.y + 4 * u), ImVec2(ib.x - 4 * u, ib.y - 4 * u), IM_COL32_WHITE, 13 * u);
        Shade(dl, infoStart, ia.y, ib.y, Rgba(40, 120, 220), Rgba(14, 58, 150));
        const float ix = ia.x + 32 * u;
        const float wrap = ib.x - 32 * u - ix;
        float iy = ia.y + 22 * u;
        auto line = [&](const std::string& text, float size, ImU32 color) {
            ShadowedText(dl, g_text, size, ImVec2(ix, iy), color, text.c_str(), wrap);
            iy += g_text->CalcTextSizeA(size, FLT_MAX, wrap, text.c_str()).y + 8 * u;
        };
        const ImU32 dim = Rgba(190, 225, 255);
        switch (screen) {
        case Screen::Welcome:
            if (iso.empty()) {
                line(installed ? "El juego ya está instalado. Pulsa JUGAR." : "Elige tu copia de MLB Power Pros 2008 para Wii (USA).", 26 * u, IM_COL32_WHITE);
                line("Se aceptan ISO, NKit, RVZ, WBFS, WIA, GCZ y CISO. El juego se traduce y compila en tu PC; "
                     "no se descarga ni se envía nada del juego.", 21 * u, dim);
            } else {
                line("Disco: " + Utf8(fs::u8path(iso).filename()), 25 * u, IM_COL32_WHITE);
                line("La primera instalación tarda varios minutos y usa todos los núcleos del procesador.", 21 * u, dim);
            }
            line("Carpeta: " + Utf8(install), 20 * u, dim);
            break;
        case Screen::Building: {
            std::lock_guard lock(build.mutex);
            line(build.message, 26 * u, IM_COL32_WHITE);
            const ImVec2 pa(ix, iy + 4 * u);
            const ImVec2 pb(ib.x - 32 * u, iy + 34 * u);
            dl->AddRectFilled(pa, pb, Rgba(8, 40, 120, 230), 15 * u);
            const float fill = pa.x + (pb.x - pa.x) * static_cast<float>(std::clamp(build.percent, 0, 100)) / 100.0f;
            if (fill > pa.x + 30 * u) Pill(dl, pa, ImVec2(fill, pb.y), Rgba(255, 210, 100), Rgba(240, 120, 20), u * 0.5f);
            const std::string pct = std::to_string(build.percent) + "%";
            const Uint64 secs = (SDL_GetTicks() - buildStart) / 1000;
            const std::string elapsed = pct + "   ·   " + std::to_string(secs / 60) + ":" + (secs % 60 < 10 ? "0" : "") + std::to_string(secs % 60);
            iy = pb.y + 10 * u;
            line(elapsed, 20 * u, dim);
            for (const std::string& l : build.tail) {
                if (iy + 18 * u > ib.y - 10 * u) break;  // keep the log inside the box
                Text(dl, g_text, 15 * u, ImVec2(ix, iy), Rgba(170, 205, 240), l.c_str());
                iy += 18 * u;
            }
            break;
        }
        case Screen::Done:
            line("¡Listo! MLB Power Pros 2008 está instalado.", 28 * u, IM_COL32_WHITE);
            line("Ejecutable: " + Utf8(gameExe()), 20 * u, dim);
            if (shortcut) line("También hay un acceso directo en el escritorio.", 20 * u, dim);
            break;
        case Screen::Failed: {
            std::lock_guard lock(build.mutex);
            line("No se pudo instalar.", 28 * u, Rgba(255, 190, 170));
            line(build.error, 22 * u, IM_COL32_WHITE);
            line("Registro: " + Utf8(install / "setup.log"), 18 * u, dim);
            break;
        }
        }
        if (screen == Screen::Welcome) {
            // Options: install folder and desktop shortcut.
            const float oy = ib.y - 46 * u;
            const char* folder = "Cambiar carpeta";
            const ImVec2 fa(ix, oy);
            const ImVec2 fb(ix + TextSize(g_bold, 19 * u, folder).x + 36 * u, oy + 34 * u);
            const ImVec2 m = ImGui::GetIO().MousePos;
            Pill(dl, fa, fb, Rgba(90, 150, 240), Rgba(30, 80, 190), u * 0.5f);
            Text(dl, g_bold, 19 * u, ImVec2(fa.x + 18 * u, fa.y + 7 * u), IM_COL32_WHITE, folder);
            if (click && m.x >= fa.x && m.x < fb.x && m.y >= fa.y && m.y < fb.y) {
                SDL_ShowOpenFolderDialog(OnDialog, &folderDialog, window, nullptr, false);
            }
            const ImVec2 ca(fb.x + 30 * u, oy + 5 * u);
            const ImVec2 cb(ca.x + 24 * u, ca.y + 24 * u);
            dl->AddRectFilled(ca, cb, IM_COL32_WHITE, 5 * u);
            if (shortcut) DrawCheck(dl, ImVec2(ca.x + 4 * u, ca.y + 3 * u), 17 * u, Rgba(30, 140, 60));
            const char* sc = "Crear acceso directo en el escritorio";
            ShadowedText(dl, g_text, 20 * u, ImVec2(cb.x + 10 * u, oy + 5 * u), IM_COL32_WHITE, sc);
            const float scEnd = cb.x + 10 * u + TextSize(g_text, 20 * u, sc).x;
            if (click && m.x >= ca.x && m.x < scEnd && m.y >= ca.y && m.y < cb.y) shortcut = !shortcut;
        }

        float hx = w * 0.06f;
        const float hy = h - 50 * u;
        hx = Hint(dl, g_bold, g_text, hx, hy, u, Rgba(40, 170, 80), "A", "Aceptar");
        Hint(dl, g_bold, g_text, hx, hy, u, Rgba(30, 90, 200), "+", "Mover");
        Text(dl, g_text, 17 * u, ImVec2(w * 0.94f - TextSize(g_text, 17 * u, "No incluye nada del juego").x, hy + 4 * u),
             Rgba(190, 225, 255), "No incluye nada del juego");

        // Actions.
        if (activated != nullptr) {
            const std::string a = activated;
            static const SDL_DialogFileFilter filters[] = {
                {"Imagen de disco de Wii", "iso;rvz;wbfs;wia;gcz;ciso;gcm;nfs"}, {"Todos los archivos", "*"}};
            if (a == "ELEGIR DISCO" || a == "CAMBIAR DISCO" || a == "OTRO DISCO") {
                SDL_ShowOpenFileDialog(OnDialog, &isoDialog, window, filters, 2, nullptr, false);
            } else if (a == "INSTALAR" || a == "REINSTALAR" || a == "REINTENTAR") {
                if (iso.empty()) {
                    SDL_ShowOpenFileDialog(OnDialog, &isoDialog, window, filters, 2, nullptr, false);
                } else {
                    build.Start(script, iso, install, shortcut);
                    buildStart = SDL_GetTicks();
                    screen = Screen::Building;
                    menu = 0;
                }
            } else if (a == "CANCELAR") {
                build.Stop();
                screen = Screen::Welcome;
            } else if (a == "VER REGISTRO") {
                ShellExecuteW(nullptr, L"open", (install / "setup.log").c_str(), nullptr, nullptr, SW_SHOWNORMAL);
            } else if (a == "JUGAR") {
                const fs::path exe = gameExe();
                ShellExecuteW(nullptr, L"open", exe.c_str(), nullptr, exe.parent_path().c_str(), SW_SHOWNORMAL);
                quit = true;
            } else if (a == "SALIR") {
                quit = true;
            }
        }

        ImGui::Render();
        SDL_SetRenderDrawColor(renderer, 8, 56, 158, 255);
        SDL_RenderClear(renderer);
        ImGui_ImplSDLRenderer3_RenderDrawData(ImGui::GetDrawData(), renderer);
        SDL_RenderPresent(renderer);
    }

    build.Stop();
    ImGui_ImplSDLRenderer3_Shutdown();
    ImGui_ImplSDL3_Shutdown();
    ImGui::DestroyContext();
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
