# Working agreement

- Keep this recomp project on drive D in its dedicated directory. Preserve the original disc image and read-only synced references.
- User decision, 2026-10-08: prioritize recomp code, native replacements and measured performance work. Do not spend development turns manually playing each inning or repeatedly pitching merely to advance the score.
- User decision, 2026-10-09: use the reviewed recomp/decomp developer guidance to pursue larger measured improvements. Identify the major cost, compare preserved behavior and benchmark from the same saved state; do not equate small diagnostics changes with gameplay or completion progress.
- Use short, targeted integration probes from saved states. Automate control sequences when needed. A full match is a later integration check, not a prerequisite for each code improvement.
- Report linked/translated code separately from validated behavior. Match progress does not increase recomp coverage, and 100% experimental linking does not mean a complete native port.
- Preserve generated game code. Runtime fixes must remain reproducible patches against pinned dependencies; private binaries, assets, saves and traces stay under local/.
