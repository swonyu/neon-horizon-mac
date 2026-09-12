# Portable edition — September 11, 2026

This edition packages a multi-pass Mac makeover into an independent local Git repository. It contains the final retained choices, reusable files, and a complete setup guide. Private session history and machine backups are not included.

## Included

- The final, self-contained Neon Horizon wallpaper: gusting depth-graded rain, a 50-instance impact field across the wet promenade and near river, traffic on four painted decks plus two aerial lanes, a source-derived bloom, the sun's specular column as the focal point, neon ballast stutter, windows coming on over minutes, distant lightning on the storm cycle, two boats with vertical light columns, waterfalls and rising mist.
- Rebuilt from `wallpaper/build/`, at 0.75 MB rather than 5.0 MB; `#calm` runs everything at one third speed.
- A static copy of the background painting for the ordinary wallpaper and Lock Screen.
- A preview-first launcher and 39 explicit native preference values in seven selectable groups.
- Original-value backups before writes, readback verification, repeat-safe apply, and undo that preserves later edits. Backup files stay outside the repository.
- The full manual UI checklist: appearance, typography, accessibility presentation, Finder views/sidebar/toolbar, Dock arrangement, menu bar, trackpad, keyboard lighting, Calendar, and clipboard.
- The optional loopback-only wallpaper host with portable login install/disable commands.
- The optional two-second edge-switch module and nine app/window shortcuts. The example config discovers a single attached display rather than embedding a machine ID.
- A native local generator for four folder icons and a visual-only Terminal profile.
- A prompt for another assistant to complete the setup on another Mac, an MIT license, and runnable checks.

## Deliberate boundaries

The native clipboard uses macOS retention; this is not a permanent clipboard database. Desktop files and apps are not removed. Per-folder Finder state, toolbar customization, menu-bar layout and permission-dependent features use the manual guide instead of copying another person's preference files.

Faster key repeat and temporary TextEdit behavior changes were cancelled and are not bundled. Stage Manager is not enabled. Unfinished widget changes, a magenta pointer outline, and blocked browser settings are not claimed as applied features. The optional Terminal profile and Hammerspoon controls are provided without claiming a completed live installation.

## Verification scope

Developed on macOS 27.0 beta (26A428), on M5 Max. Native preset readback was checked during the original makeover; the portable apply/undo adapter is tested separately in an isolated domain. The original desktop wallpaper ran through Plash, but this edition's login installer and complete preset have not been applied to a second Mac. A full reboot test has not been performed.

The packaged wallpaper is byte-identical to the finished source HTML. An attempt to reopen it for a new browser preview was blocked by browser security policy; that block was respected. The check suite verifies the assets, scene layers, HTTP routes, and service configuration. Optional Node checks verify the visibility pause/resume logic. Lua simulations exercise the actual edge and shortcut modules against a mocked host; they do not certify live Accessibility-controlled desktop switching.

## 12 September 2026 — repository audit repairs

The [22-finding audit](AUDIT-2026-09-12.md) covers command-level preview and undo
races, input validation, journal publication, host ownership and interrupted
installation, launcher dependency handling, optional control startup, and artwork
behavior/build reliability. The image recipe and embedded artwork remain the same;
reflection placement, calm-fragment updates and Reduce Motion brightness are fixed.
Documentation now separates measured image gates and simulated behavior from
unverified rendering, power and live Mac installation. The [implementation plan](plans/2026-09-12-audit-fixes.md)
tracks completion and the audit records final checks.

## 12 September 2026 — wallpaper composition repairs

The [13-finding wallpaper critique](WALLPAPER-CRITIQUE.md) addresses abrupt
cropping, effects on the wrong painted surfaces, a moving shimmer mask, rain
scale and sky exclusion, calm-mode phase changes, and retained preparation
hints. The scene keeps its original artwork, boat movement and palette. It
uses continuous fitting, conservative water masks, individually placed lights
and native playback-rate changes. Source, geometry and generated-script checks
cover the changes; fresh Chrome rendering remains blocked by browser policy.

## 12 September 2026 — supplied-recording follow-up

The user-provided Chrome recording showed older window placements and framing,
so it did not verify the current build. The review did reveal straight-sided
pavement and boat glows in code retained by both versions. Their existing
backgrounds now fade elliptically. Source checks and package rebuilding cover
the change; a post-reload recording is still needed to judge its appearance.

## 12 September 2026 — personalized portable Dock and installed controls

- The shared Dock policy now uses each Mac's own pins and Spotlight usage metadata. Screen Sharing is first after Finder, with one small separator. Missing-count and unavailable pins keep their order after measured apps. Optional discovery adds up to three locally installed apps with positive use counts.
- Start.command includes preview, apply and undo for the layout. Durable owner-only Dock backups are separate from scalar preset backups. Undo skips a changed array conservatively, including changes macOS may make to tile metadata.
- Dock magnification increases to 72 points while resting icons stay at 48. The optional controls add Control-Option-Command-Shift-S for Screen Sharing.
- The intended audience is M5 Pro and higher Macs. Apps, home paths and the edge helper's display ID are local; the source Mac remains the only live-tested hardware/OS combination.
- The layout was applied and read back on the source Mac, including after Dock restart. Hammerspoon 1.1.1 was installed from its official release, passed native signature and Gatekeeper assessment, loaded the edge helper and nine hotkeys, and showed Accessibility and login startup enabled. A real edge-triggered desktop transition and login/reboot test remain unverified.
- The latest wallpaper HTML was copied into the source Mac's existing installed artwork location with a backup. This verifies the installed file, not a fresh Plash render; the earlier browser policy block remains respected.

Checks: 18 Dock cases, 18 edge scenarios, nine shortcut bindings and existing full source/package checks. Another Mac still needs its own visible verification and permissions. The setup tool does not install Hammerspoon or copy any personal app list.

## 12 September 2026 — restore grouped Dock spacing

The default Dock policy now preserves each person's spacer-defined app groups and sorts usage only inside those groups. Screen Sharing leads the first group without an isolated gap. Empty gaps are consolidated, and unavailable pins keep their group membership. For an ungrouped Dock, setup creates balanced visual groups of roughly four apps, capped at four groups, then respects those boundaries on later runs. Optional discovered apps form a separate final group.

This replaces the earlier single-gap, globally ranked layout. Native Dock backups and conservative undo remain unchanged. No app categories, personal app lineup or continuous app tracker are bundled.

## 12 September 2026 — second repository review

- Recheck a preference after its journal is published so an edit made during backup writing is preserved.
- Recreate a selected screenshot directory on repeat apply even when its saved preference already matches. Preview and cancellation remain inert.
- Revalidate installed host files and the service plist at the start/acceptance boundary; preserve a service plist replaced during uninstall.
- Prepare and encode wallpaper assets in staging before publishing; reject invalid prepared assets before replacing the HTML.
- Compare rebuilt HTML with the shipped page, and add a macOS CI workflow running the existing Python, native-adapter, image, Node, Dock and Lua checks.
- Refresh the [current review](REVIEW-2026-09-12.md) and setup instructions. Existing Dock group behavior, painting, animation design and keyboard settings are unchanged.

The review report records verification status and remaining live-render, gesture, login and other-Mac limits.
