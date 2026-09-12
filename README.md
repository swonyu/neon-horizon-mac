# Neon Horizon — Mac Makeover

For Macs with **M5 Pro and higher chips**: a clean, magenta desktop with an animated cyberpunk painting, a calmer Dock, a tidier Finder, and optional two-second edge switching between desktops.

![Neon Horizon cyberpunk painting](wallpaper/still.png)

**Start here:** [Setup guide](docs/SETUP.md) · [Wallpaper design notes](docs/WALLPAPER.md) · [Another-Mac setup prompt](docs/SETUP-PROMPT.md) · [What is included](docs/CHANGELOG.md) · [Repository audit](docs/REVIEW-2026-09-12.md)

## Use it

1. Copy or unzip the entire `neon-horizon-mac` folder onto your Mac.
2. Open `wallpaper/index.html` to preview the finished animation.
3. Double-click **Start.command**. Choose **1** to preview, then **2** to apply the complete native preset after reviewing it. The setup tool needs [Python 3](https://www.python.org/downloads/macos/); the wallpaper and manual guide do not.
4. In **Start.command**, choose **6** to preview a personalized Dock, then **7** to apply it. Screen Sharing stays first after Finder; your own app groups keep their spacing, with usage ordering inside each group.
5. Follow [Setup](docs/SETUP.md) for Plash, the remaining native UI settings, and optional desktop controls.

The preset offers **39 settings in seven groups**. It saves the original values outside the repository before changing them. It never replaces your Dock app list, moves your existing files, changes key-repeat speed, installs apps, grants permissions, or restarts your Mac.

For a smaller selection, open a terminal in this folder:

```sh
python3 makeover.py plan --groups appearance,dock,finder
python3 makeover.py apply --groups appearance,dock,finder
```

The available groups are `appearance`, `dock`, `finder`, `desktop`, `calendar`, `clipboard`, and `corners`; `all` selects every group. With no group argument, the tool uses the first five. The clipboard group enables native seven-day history; macOS controls which copied items it retains.

## One Dock layout, your apps

The optional layout tool puts **Screen Sharing immediately after Finder**, at the start of your first app group. Existing small gaps keep your groups separate, so work tools and media apps stay where you expect them. Usage sorting happens **inside each group**: available Spotlight use counts first, then last-used date; pins without counts retain their relative order afterward in that group. Counts are local metadata, not Screen Time minutes or a guaranteed recent-time window.

For a Dock without meaningful groups, the tool sorts once and adds balanced spacing: roughly four apps per group, up to four groups. Later runs preserve those groups. It does not guess app categories or copy the source Mac’s lineup.

```sh
python3 dock.py plan
python3 dock.py apply --confirm
# Optional: consider up to three unpinned, locally installed apps with positive usage counts
python3 dock.py plan --discover
python3 dock.py apply --discover --confirm
```

It preserves app installations, folder stacks and existing group boundaries, collapses empty gaps and duplicate paths, and saves the original app layout outside the repository. Discovered apps appear in a separate final group; existing groups keep their membership. It runs only when requested: icons do not rearrange in the background. No usage history, personal app list, or backup is shipped with the repo. To refresh the order later, run it again.

```sh
python3 dock.py backups
python3 dock.py undo --backup "PASTE_THE_EXACT_DOCK_BACKUP_PATH_HERE"
```

Undo preserves the entire current app layout if its stored tiles have changed since that run, including metadata changes made by macOS. Relaunch the Dock or log out/in to display a saved layout.

## Animated wallpaper

Rain that gusts and obeys aerial perspective, landing across the whole wet promenade and the near river. Traffic on the bridges and two aerial lanes. The sun's reflection crawling on the water. Neon ballast stutter, windows coming on over minutes, distant lightning alongside a seven-minute storm cycle. A near-promenade plane that dollies against the camera for real depth, and a source-derived bloom that makes every light in the painting halate.

Everything is embedded in one HTML file. It works offline, has no audio or tracking, respects Reduce Motion, and pauses when the browser reports it hidden. Varied animation periods reduce obvious synchronization; some layers deliberately share timing.

Open `index.html#calm` to run every animation at one third speed. Adding or removing the fragment also changes an open page. This changes motion speed; battery savings have not been measured. Use Plash’s deactivate-on-battery option to stop its animation on battery.

Use [Plash](https://sindresorhus.com/plash) to place it behind your windows. The guide includes its local-file setup and an optional loopback host with login startup. Plash and Hammerspoon are separate projects and are not bundled.

The base painting is **1536 × 1024**; the boat sprite is **768 × 256**. Both ship as WebP, so the file is **~0.75 MB** rather than the 5.0 MB the PNG build cost. The scene fits continuously to your display, retaining both boats, waterfalls and the foreground across narrow and wide screens. Its blurred backdrop fills the remaining space. This is layered animation, not native 4K video. Plash cannot animate the Lock Screen.

To rebuild the wallpaper after editing anything under `wallpaper/build/`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'Pillow==12.3.0' 'numpy==2.3.5'
.venv/bin/python wallpaper/build/prepare_images.py && .venv/bin/python wallpaper/build/build.py
.venv/bin/python tests/build-selfcheck.py
```

These are the reference versions checked with Python 3.12; they are optional build dependencies, not requirements for using the wallpaper. Different image-encoder versions can produce different compressed bytes.

The first script validates both source images and stages every encoded output before publishing, so source, grading or encoding failures leave previous outputs intact. Publication replaces several files individually; it is not a cross-file crash transaction. The HTML builder validates the prepared asset structure and replaces the page only when assembly succeeds. See [wallpaper design notes](docs/WALLPAPER.md) for the composition and verification limits.

## Undo

```sh
python3 makeover.py backups
python3 makeover.py undo --backup "PASTE_THE_EXACT_BACKUP_PATH_HERE"
```

Restore the most recent backup first if you applied several groups separately. Undo changes only values that still match what that run applied, keeping your later edits. It removes keys that were originally absent. Backups and created folders remain available.

The preset undo covers **preset preferences only**. The personalized Dock layout has its separate undo command above. Plash, its optional login host, manually chosen UI settings, imported profiles, and Hammerspoon have their own removal instructions in [Setup](docs/SETUP.md).

## Compatibility and checks

The target is **any Mac with M5 Pro or a higher-tier/newer Pro, Max, or Ultra chip**, using supported macOS versions. Paths, installed apps and the edge helper’s display ID are detected on the receiving Mac; there is no model-specific or owner-specific configuration. Hardware branding is not a compatibility certification.

Developed on a MacBook Pro with M5 Max running **macOS 27.0 beta, build 26A428**. The preset permits macOS **26.1–27**; macOS 26.1 and other Macs have **not** been live-tested. Some preference keys are undocumented and may change in OS updates. Review the guide and verify visible results after applying; a saved value alone does not guarantee an OS version uses it.

The optional edge helper currently supports **one attached display**. Its guard conditions and shortcuts have simulation checks; live Accessibility-controlled desktop switching has not been verified. No installer bypasses macOS permission prompts.

Run the portable checks:

```sh
python3 tests/check.py
python3 tests/dock-selfcheck.py
# Optional: with Lua 5.4 installed
(cd tests && lua edge-selfcheck.lua && lua shortcuts-selfcheck.lua)
```

Node.js is optional for executing the wallpaper’s small interaction script against a mocked document. The image-grading failure check runs when Pillow and NumPy are installed; missing optional tools are reported as skipped.

The Python check uses a disposable preference domain on macOS, not your real UI settings. The wallpaper host checks use an ephemeral loopback port and do not install a service. It also rebuilds the HTML from its embedded assets and compares it with the shipped page, catching template changes that were not rebuilt.

[GitHub Actions](.github/workflows/checks.yml) runs these checks, the Dock tests and both Lua simulations on a disposable macOS runner for pull requests and pushes to `main`. It installs the optional check dependencies so those checks cannot silently disappear due to a missing tool. Hosted tests do not certify an M5 Mac, a Plash render, Accessibility permissions or a login/reboot.

## License

[MIT](LICENSE) for this repository's code and included generated artwork. Artwork was created with AI and then composed into the animated scene. No third-party app binaries or Apple symbol images are distributed. The optional Mac-only icon generator uses system-provided symbols locally. Apple, Plash, and Hammerspoon names identify their respective products; this project is independent.
