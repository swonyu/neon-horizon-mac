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
- The optional two-second edge-switch module and eight app/window shortcuts. The example config discovers a single attached display rather than embedding a machine ID.
- A native local generator for four folder icons and a visual-only Terminal profile.
- A prompt for another assistant to complete the setup on another Mac, an MIT license, and runnable checks.

## Deliberate boundaries

The native clipboard uses macOS retention; this is not a permanent clipboard database. Desktop files and apps are not removed. Per-folder Finder state, app ordering, toolbar customization, menu-bar layout and permission-dependent features use the manual guide instead of copying another person's preference files.

Faster key repeat and temporary TextEdit behavior changes were cancelled and are not bundled. Stage Manager is not enabled. Unfinished widget changes, a magenta pointer outline, and blocked browser settings are not claimed as applied features. The optional Terminal profile and Hammerspoon controls are provided without claiming a completed live installation.

## Verification scope

Developed on macOS 27.0 beta (26A428), on M5 Max. Native preset readback was checked during the original makeover; the portable apply/undo adapter is tested separately in an isolated domain. The original desktop wallpaper ran through Plash, but this edition's login installer and complete preset have not been applied to a second Mac. A full reboot test has not been performed.

The packaged wallpaper is byte-identical to the finished source HTML. An attempt to reopen it for a new browser preview was blocked by browser security policy; that block was respected. The check suite verifies the assets, scene layers, HTTP routes, and service configuration. Optional Node checks verify the visibility pause/resume logic. Lua simulations exercise the actual edge and shortcut modules against a mocked host; they do not certify live Accessibility-controlled desktop switching.
