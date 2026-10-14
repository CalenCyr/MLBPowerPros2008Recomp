// SPDX-License-Identifier: GPL-3.0-or-later
// Reads and writes single keys of Config.toml line by line, like the runtime's WriteSetting: comments
// and every other line stay as they are.
#include "config.h"

#include <algorithm>
#include <fstream>

namespace tstudio {
namespace {
std::string Trim(std::string_view s) {
    const size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
    return a == std::string_view::npos ? std::string() : std::string(s.substr(a, b - a + 1));
}
std::vector<std::string> Lines(const std::filesystem::path& file) {
    std::ifstream in(file, std::ios::binary);
    std::vector<std::string> lines;
    for (std::string line; std::getline(in, line);) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(line);
    }
    return lines;
}
// [first, end) of the section's lines (after its header); first == end == lines.size() if absent.
std::pair<size_t, size_t> Section(const std::vector<std::string>& lines, std::string_view section) {
    size_t start = lines.size();
    for (size_t i = 0; i < lines.size(); ++i) {
        const std::string t = Trim(lines[i]);
        if (t.size() < 2 || t.front() != '[' || t.back() != ']') continue;
        if (start != lines.size()) return {start, i};
        if (Trim(std::string_view(t).substr(1, t.size() - 2)) == section) start = i + 1;
    }
    return {start, lines.size()};
}
size_t KeyLine(const std::vector<std::string>& lines, std::pair<size_t, size_t> range, std::string_view key) {
    for (size_t i = range.first; i < range.second; ++i) {
        const size_t eq = lines[i].find('=');
        if (eq != std::string::npos && Trim(std::string_view(lines[i]).substr(0, eq)) == key) return i;
    }
    return lines.size();
}
std::string Unquote(std::string v) {
    if (v.size() >= 2 && (v.front() == '"' || v.front() == '\'') && v.back() == v.front()) return v.substr(1, v.size() - 2);
    return v;
}
} // namespace

std::optional<std::string> ReadSetting(const std::filesystem::path& config, std::string_view section, std::string_view key) {
    const auto lines = Lines(config);
    const size_t i = KeyLine(lines, Section(lines, section), key);
    if (i == lines.size()) return std::nullopt;
    std::string value = Trim(std::string_view(lines[i]).substr(lines[i].find('=') + 1));
    if (const size_t hash = value.find(" #"); hash != std::string::npos) value = Trim(value.substr(0, hash));
    return Unquote(value);
}

std::vector<std::string> ReadEnabledMods(const std::filesystem::path& config) {
    std::vector<std::string> out;
    const auto value = ReadSetting(config, "mods", "enabled");
    if (!value) return out;
    for (size_t i = 0; i < value->size(); ++i) {
        const char q = (*value)[i];
        if (q != '"' && q != '\'') continue;
        std::string item;
        for (++i; i < value->size() && (*value)[i] != q; ++i) {
            if (q == '"' && (*value)[i] == '\\' && i + 1 < value->size()) ++i;
            item += (*value)[i];
        }
        out.push_back(item);
    }
    return out;
}

bool SetModEnabled(const std::filesystem::path& config, const std::string& id, bool enabled) {
    auto list = ReadEnabledMods(config);
    std::erase(list, id);
    if (enabled) list.push_back(id);
    std::string value = "[";
    for (size_t i = 0; i < list.size(); ++i) {
        value += i ? ", \"" : "\"";
        for (char c : list[i]) {
            if (c == '"' || c == '\\') value += '\\';
            value += c;
        }
        value += '"';
    }
    value += "]";
    auto lines = Lines(config);
    auto range = Section(lines, "mods");
    if (range.first == lines.size()) {
        if (!lines.empty() && !lines.back().empty()) lines.emplace_back();
        lines.emplace_back("[mods]");
        range = {lines.size(), lines.size()};
    }
    const size_t i = KeyLine(lines, range, "enabled");
    if (i == lines.size()) lines.insert(lines.begin() + static_cast<std::ptrdiff_t>(range.second), "enabled = " + value);
    else lines[i] = "enabled = " + value;
    std::ofstream out(config, std::ios::binary | std::ios::trunc);
    for (const auto& line : lines) out << line << "\r\n";
    return static_cast<bool>(out);
}

} // namespace tstudio
