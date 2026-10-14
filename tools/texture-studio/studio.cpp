// SPDX-License-Identifier: GPL-3.0-or-later
// Power Pros Wii 2008 Texture Studio.
#include <SDL3/SDL.h>
#include <cstring>

namespace tstudio { int RunSelftest(); }

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--selftest") == 0) return tstudio::RunSelftest();
    return 0;
}
