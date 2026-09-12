# Neon Horizon audit implementation plan

Scope: resolve the 22 findings in the [audit](../AUDIT-2026-09-12.md), preserving
the existing portable architecture and the owner's live Mac configuration.
Work starts from `3df2c1e` in an isolated worktree. No new runtime dependency is
needed for using the preset, wallpaper or host.

- [x] Read every tracked component; reproduce failures and record severity.
- [x] F01–F05: preserve the confirmed preview, lock journal reads, synchronize
  journal publication, validate input boundaries, and order backups correctly.
- [x] F06–F10: make host publication/recovery and ownership checks reliable;
  verify readiness; keep guide/preview usable without Python and preserve errors.
- [x] F11–F13: repair edge modifier handling and startup cleanup; preserve
  existing hotkeys. Exercise actual Lua modules against the mocked host.
- [x] F14–F19: repair reflection coordinates, calm changes and static brightness;
  reject failed grades, reset build randomness and publish HTML safely.
- [x] F20–F22: correct unsupported claims, document the reference rebuild,
  and keep package checks focused on shipped files.
- [x] Run the combined Python, Node, Lua and source-build checks on the final
  changes; independently review the diff and resolve additional concrete defects.
- [x] Record exact results and remaining live checks; package the reviewed
  source and leave a local commit ready for review.

Acceptance: each finding has an implemented resolution and an appropriate
behavior check or documentation correction. Passing simulations must never be
reported as a completed installation, power benchmark or visible Mac verification.
