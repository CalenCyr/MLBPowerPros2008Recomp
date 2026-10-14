// SPDX-License-Identifier: GPL-3.0-or-later
// Style B of the approved mockup: calm dark panels, blue title band (no red line), Power Pros pills.
// Fonts carry Latin-1 only, so badges and arrows are drawn as shapes.
#pragma once
#include "power_pros_ui.h"

#include <array>
#include <utility>

namespace tstudio::ui {
using power_pros_ui::Rgba;
inline const ImU32 kWindow = Rgba(16, 24, 38), kPanel = Rgba(23, 34, 56), kPanelBorder = Rgba(47, 70, 112),
                   kPanelHeader = Rgba(29, 43, 71), kHeaderText = Rgba(127, 182, 255), kMuted = Rgba(169, 196, 255),
                   kBandTop = Rgba(11, 58, 158), kBandBottom = Rgba(8, 48, 127), kYellow = Rgba(255, 210, 63),
                   kBlueTop = Rgba(54, 163, 255), kBlueBottom = Rgba(11, 95, 208), kGreenTop = Rgba(90, 214, 90),
                   kGreenBottom = Rgba(24, 138, 42), kOrangeTop = Rgba(255, 178, 58), kOrangeBottom = Rgba(224, 106, 0),
                   kRedTop = Rgba(255, 106, 106), kRedBottom = Rgba(200, 30, 42), kGreyTop = Rgba(138, 160, 200),
                   kGreyBottom = Rgba(74, 95, 138), kFooter = Rgba(13, 21, 36), kCheckA = Rgba(90, 106, 138),
                   kCheckB = Rgba(128, 144, 176);

// Glossy pill button sized to its label. Returns true when clicked.
inline bool Pill(const char* label, ImU32 top, ImU32 bottom, bool small = false, bool enabled = true) {
    using namespace power_pros_ui;
    const float fs = small ? 17.0f : 20.0f;
    const ImVec2 ts = TextSize(g_bold, fs, label);
    const ImVec2 size(ts.x + 30, fs + 14);
    const ImVec2 p = ImGui::GetCursorScreenPos();
    ImGui::PushID(label);
    const bool clicked = ImGui::InvisibleButton("##pill", ImVec2(size.x + 8, size.y + 10)) && enabled;
    ImGui::PopID();
    const bool hot = enabled && ImGui::IsItemHovered();
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const ImVec2 a(p.x + 4, p.y + 4), b(a.x + size.x, a.y + size.y);
    power_pros_ui::Pill(dl, a, b, enabled ? (hot ? Rgba(255, 255, 255) : top) : kGreyTop, enabled ? bottom : kGreyBottom, 0.6f);
    ShadowedText(dl, g_bold, fs, ImVec2(a.x + (size.x - ts.x) * 0.5f, a.y + (size.y - fs) * 0.5f - 1),
                 hot ? bottom : IM_COL32_WHITE, label);
    return clicked;
}

// Panel = child window with the calm colours and a header strip. With a header, the content scrolls in
// its own region below it, so rows never slide under the header.
inline std::vector<bool>& PanelStack() {
    static std::vector<bool> stack;
    return stack;
}
inline bool BeginPanel(const char* id, const char* header, ImVec2 size, ImGuiWindowFlags flags = 0) {
    ImGui::PushStyleColor(ImGuiCol_ChildBg, ImGui::ColorConvertU32ToFloat4(kPanel));
    ImGui::PushStyleColor(ImGuiCol_Border, ImGui::ColorConvertU32ToFloat4(kPanelBorder));
    ImGui::PushStyleVar(ImGuiStyleVar_ChildRounding, 12.0f);
    if (!header) {
        PanelStack().push_back(false);
        return ImGui::BeginChild(id, size, ImGuiChildFlags_Borders, flags);
    }
    const bool open = ImGui::BeginChild(id, size, ImGuiChildFlags_Borders, ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoScrollWithMouse);
    ImDrawList* dl = ImGui::GetWindowDrawList();
    const ImVec2 p = ImGui::GetWindowPos();
    const float h = ImGui::GetFontSize() + 12;
    dl->AddRectFilled(p, ImVec2(p.x + ImGui::GetWindowWidth(), p.y + h), kPanelHeader, 12.0f, ImDrawFlags_RoundCornersTop);
    dl->AddText(ImVec2(p.x + 12, p.y + 6), kHeaderText, header);
    ImGui::SetCursorPosY(h + 6);
    ImGui::PushStyleColor(ImGuiCol_ChildBg, ImVec4(0, 0, 0, 0));
    ImGui::BeginChild("##body", ImVec2(0, 0), ImGuiChildFlags_None, flags);
    ImGui::PopStyleColor();
    PanelStack().push_back(true);
    return open;
}
inline void EndPanel() {
    if (PanelStack().back()) ImGui::EndChild();
    PanelStack().pop_back();
    ImGui::EndChild();
    ImGui::PopStyleVar();
    ImGui::PopStyleColor(2);
}

// Transparency checkerboard.
inline void Checker(ImDrawList* dl, ImVec2 a, ImVec2 b, float cell = 8.0f) {
    dl->AddRectFilled(a, b, kCheckB);
    for (float y = a.y; y < b.y; y += cell)
        for (float x = a.x + (static_cast<int>((y - a.y) / cell) % 2) * cell; x < b.x; x += 2 * cell)
            dl->AddRectFilled(ImVec2(x, y), ImVec2(std::min(x + cell, b.x), std::min(y + cell, b.y)), kCheckA);
}

// Round badge: green with a check (replaced) or orange with an eye (seen in a capture).
inline void Badge(ImDrawList* dl, ImVec2 c, float r, bool eye) {
    dl->AddCircleFilled(c, r + 2, IM_COL32_WHITE);
    dl->AddCircleFilled(c, r, eye ? kOrangeBottom : kGreenBottom);
    if (eye) {
        dl->AddEllipse(c, ImVec2(r * 0.7f, r * 0.42f), IM_COL32_WHITE, 0.0f, 0, 1.6f);
        dl->AddCircleFilled(c, r * 0.22f, IM_COL32_WHITE);
    } else {
        dl->AddPolyline(std::array<ImVec2, 3>{ImVec2(c.x - r * 0.5f, c.y), ImVec2(c.x - r * 0.12f, c.y + r * 0.4f),
                                              ImVec2(c.x + r * 0.5f, c.y - r * 0.4f)}.data(),
                        3, IM_COL32_WHITE, 0, 2.2f);
    }
}

// Fits an image of w x h into the box a..b keeping its proportions; returns the drawn rectangle.
inline std::pair<ImVec2, ImVec2> Fit(ImVec2 a, ImVec2 b, float w, float h) {
    const float s = std::min((b.x - a.x) / w, (b.y - a.y) / h);
    const ImVec2 size(w * s, h * s);
    const ImVec2 o(a.x + (b.x - a.x - size.x) * 0.5f, a.y + (b.y - a.y - size.y) * 0.5f);
    return {o, ImVec2(o.x + size.x, o.y + size.y)};
}
} // namespace tstudio::ui
