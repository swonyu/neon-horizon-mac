# Second repository review implementation plan

> Execute the independent installer and wallpaper repairs in parallel; the lead owns documentation, CI, integration and final verification.

**Goal:** Fix the concrete failure and maintenance gaps found in published revision `e0e71c3`, without changing the owner's live Mac setup.

**Architecture:** Keep the standard-library preference/Dock tools, optional Hammerspoon modules and embedded HTML. Extend existing guards and tests at their actual write boundaries. Reuse the current image pipeline and test commands.

**Tech stack:** Python standard library, Pillow/NumPy for optional image rebuilding, Lua 5.4, native macOS preference adapter, Node for mocked wallpaper-script checks, GitHub Actions.

## Constraints

- Preserve local owner edits, personalized Dock groups, magenta appearance and keyboard repeat.
- Do not install or restart services, change permissions, or modify live Mac preferences.
- Respect the existing wallpaper browser-policy block; source checks are not fresh visual verification.
- Keep the repository private and exclude personal paths, app inventories, recordings and backups.
- No new runtime dependencies, framework or speculative UI features.
- Reproduce each code defect before fixing it, then run the smallest relevant regression and final integrated checks.

## Ordered work

- [x] **R1 — Preserve a preference edited during backup publication (P2).** In `makeover.py`, read the original value again after `save(journal, record)` and immediately before `writer`. Stop on a mismatch. Add a `tests/check.py` reproduction that changes the value from the save hook and asserts that the newer value survives with no writer call.
- [x] **R2 — Repair a missing screenshot destination on repeat apply (P2).** In `makeover.py`, prepare the screenshot folder from the selected settings after confirmation and inside the lock, even when its preference already matches. Test missing-folder repair, preview/cancel remaining inert, and an unusable destination failing before preference writes in `tests/check.py`.
- [x] **R3 — Reject host files/plists replaced during setup (P2).** In `wallpaper/host.py`, revalidate exact bytes and symlinks for every expected installed file and the service plist immediately before bootstrap/readiness. A newly appeared file must match rather than being skipped by existence alone. In `tests/host-selfcheck.py`, inject late changes during the Plash lookup and assert no bootstrap/readiness success and no overwritten foreign file.
- [x] **R4 — Preserve a service plist edited during uninstall (P2).** In `wallpaper/host.py`, re-read the recognized configuration after stopping the service and before unlinking its plist. Stop and retain a changed/replaced plist. Exercise a late replacement from the mocked stop command in `tests/host-selfcheck.py`.
- [x] **R5 — Prepare wallpaper assets without partial encode output (P2).** In `wallpaper/build/prepare_images.py`, load and validate both source images, render and encode all five outputs into temporary staging before publishing final files. Clean staging on failure. Extend `tests/build-selfcheck.py` with missing/corrupt boat and later encoding failure cases that compare all previous output bytes. Document the boundary between pre-publication preservation and multi-file publication rather than promise filesystem transactions.
- [x] **R9 — Reject unusable prepared artwork before HTML publication (P2).** In `wallpaper/build/build.py`, validate prepared WebP headers and declared size plus nonempty valid waterfall SVG data before generating HTML. A zero-byte/corrupt prepared image currently replaces a usable page successfully. Add bad-asset fixtures in `tests/build-selfcheck.py` proving failure preserves the target. Validation is structural and does not require optional image libraries or claim full decoding.
- [x] **R6 — Catch a stale shipped wallpaper (P3).** In `tests/build-selfcheck.py`, rebuild from the embedded checked-in assets and require exact equality with the checked-in HTML in addition to repeatability. Reproduce by changing only a template value in an isolated test, then run the check on the unchanged template. This comparison does not require a browser or depend on image encoder versions.
- [x] **R7 — Run existing checks on future changes (P3).** Add `.github/workflows/checks.yml`: one bounded macOS job, Python 3.12, Node, Lua 5.4 and reference image dependencies; run `tests/check.py`, `tests/dock-selfcheck.py` and both Lua scripts. Use official actions pinned to commits, read-only repository permission, no persisted checkout credential, and no deployment. Validate workflow structure locally; a hosted run is separate evidence.
- [x] **R8 — Update the review and operational instructions (P3).** Add `docs/REVIEW-2026-09-12.md` with prioritized findings, complete component coverage, fixes and explicit limits. Point the README's current audit link there while retaining the historical report. Update `docs/SETUP.md`, `docs/WALLPAPER.md` and `docs/CHANGELOG.md` for confirmed recovery behavior, screenshot repair, build publication limits and native-profile readback versus window verification.

## Validation and delivery

- [x] Inspect each reproduction and final patch; have an independent reviewer check integration.
- [x] Run the Python/native adapter/host/build/Node suite, 26 existing Dock cases plus any justified regression, and edge/shortcut simulations after the final edits. No live setup execution.
- [x] Check whitespace, documentation links, distributable privacy, and exact generated HTML consistency.
- Commit the repair set, integrate without disturbing the main worktree's unrelated audit-note edit, and refresh the ZIP from the final commit. Verify every archive entry against that commit.
- Record checks and residual live verification limits in the local session log. If publishing within the existing authorization, verify the remote commit and the new hosted check result separately.
