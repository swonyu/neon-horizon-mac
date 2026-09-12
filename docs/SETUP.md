# Set up Neon Horizon on another Mac

Keep this folder somewhere permanent. Start with the preview; choose the changes you want. Save any open work before logging out to refresh settings.

## 1. Apply the native preset

Double-click `Start.command` in the repository root. Option 1 previews the complete preset; option 2 shows it again, asks you to type `yes`, saves a backup, then applies it. If Python is missing, install Python 3 from [python.org](https://www.python.org/downloads/macos/) or use the manual steps below. No packages from pip are required for the setup tool. Wallpaper rebuilding has separate optional dependencies listed in the README.

From a terminal opened in the repository folder:

```sh
python3 makeover.py plan --groups all
python3 makeover.py apply --groups all --confirm
```

The complete preset includes:

| Group | Result |
|---|---|
| Appearance | Dark appearance, Pink/magenta accent, large sidebar icons, scroll bars when scrolling, click-to-position scrolling, less wallpaper tint in windows |
| Dock | 48-point icons, magnification up to 60, Scale minimize effect, opening bounce off, recent suggestions off, minimize into app icons, stable desktop order |
| Finder | Filename extensions, Home for new windows, current-folder search, folders first when sorting by name, path and status bars, fewer volume icons on the Desktop |
| Desktop | Tiling margins, hidden desktop file icons and widgets, future screenshots in `~/Pictures/Screenshots` |
| Calendar | Week numbers and activity shading in Year view |
| Clipboard | Native history enabled for seven days |
| Corners | Hold Option: top-left Mission Control, bottom-left Desktop, top-right Lock Screen, bottom-right Quick Note |

The tool refuses values it cannot write and restore exactly, including decimal values the native preference writer would round.

The screenshot folder is created if needed. Existing screenshots are not moved. Desktop files remain in Finder's Desktop folder. Clipboard history applies to future supported copies; it cannot recover earlier copies or promise permanent storage of everything.

Open System Settings and Finder to verify the visible results. Some values take effect after an app is reopened or after your next logout/login. The script does not force-quit apps. If macOS ignores a setting, use its corresponding native control in this guide.

## 2. Put the animation on the desktop

### Recommended: Plash local file

1. Install [Plash from its author's site or linked App Store page](https://sindresorhus.com/plash). Choose a release compatible with your macOS version.
2. Open Plash. In its menu-bar menu, open **Websites… / Manage Websites…**.
3. Use the add button's **Add Local Website… / local-file** option, and select this repository's `wallpaper/index.html`. A normal browser address bar preview does not make it your desktop.
4. Select that site as the current wallpaper. Turn on **Show on all Spaces** and, if wanted, **Launch at login**. Keep this repository folder in place.
5. In System Settings > Wallpaper, add `wallpaper/still.png` as the ordinary wallpaper. It provides the matching static background and Lock Screen; the animation runs through Plash on the desktop.

Plash documents local websites, but its `plash:add` URL command does **not** accept local file URLs. Use its file picker, or use the HTTP fallback below. Menu wording can vary by release. Plash's multi-display support is limited; it can select a display but does not natively assign separate websites to every display. [Plash documentation](https://sindresorhus.com/plash)

For less activity on battery, use Plash's deactivate-on-battery option. The artwork honors system Reduce Motion. Browser visibility pausing is not a promise that animation stops whenever another window covers the desktop.

### Optional fallback: local HTTP host

This is useful if Plash's local-file picker is unavailable. Python 3 is required. It serves only the embedded wallpaper on your own Mac; it does not expose a folder or other files.

```sh
python3 wallpaper/host.py
```

Add `http://127.0.0.1:8766/` in Plash and select it. Leave the terminal running; Control-C stops it. If the port is already used, choose another, for example `--port 8767`, and use that port in Plash too.

To make the fallback run at login instead:

```sh
python3 wallpaper/host.py --install
```

The installer copies only the HTML and host script into `~/Library/Application Support/Neon Horizon Makeover/Wallpaper`, writes `~/Library/LaunchAgents/org.neonhorizon.wallpaper.plist`, and starts the host. It opens Plash only after the listening socket is ready. Add/select the URL in Plash once. Turn off Plash's separate Launch at login option to avoid a startup race. The installed copy works even if you move the repository afterward.

Repeating the command verifies an identical running install and restores any missing matching files. It checks the loaded service identity and the served artwork before reporting success. A matching partial install can be resumed. It refuses different or edited setup files, a changed port/interpreter configuration, or a port occupied by another service. If setup stops partway, the two exact locations above contain its files; the disable command below can remove a recognized service file. A malformed or edited plist is preserved: keep a copy and inspect it before manually moving it aside, then retry. Do not remove an unfamiliar service by its label. It will not replace another existing installation.

To disable the login host:

```sh
python3 wallpaper/host.py --uninstall
```

Then choose a different Plash website, or quit Plash. Artwork and host files are retained. To update the installed copy, disable it first, rename the retained `Wallpaper` folder to keep it as a backup, then run the install command from the new repository version. If your Python installation moves or is removed, reinstall the login host so its interpreter path is refreshed.

To remove the local-file setup, choose a different site or quit Plash and disable its Launch at login. Restore the ordinary wallpaper through System Settings.

## 3. Finish the native UI touches

These reproduce the remaining visual choices through each Mac's own controls. Record your previous choices before changing them. OS releases may label or place these controls differently.

### Appearance and readability

- System Settings > Appearance: choose **Tinted + Dark** icons/widgets and **Pink** for icons, widgets, and folders, when available. Keep the Pink accent.
- Accessibility > Display: enable **Show borders**, **Differentiate without color**, and **Show window title icons**. Keep transparency unless you prefer a more opaque look.
- In Display > Text size: choose **14 pt** for supported apps. Retain any app-specific custom sizes you prefer.
- In Display > Pointer: increase size to approximately **1.25×**. Leave the outline at its default; a magenta outline was not part of the verified setup.
- Accessibility > Hover Text: enable it, set text to **28 pt**, hold **Command** to activate, and leave activation lock off.
- Accessibility > Zoom: enable keyboard shortcuts and choose **Picture-in-Picture**. Option-Command-8 toggles zoom; Option-Command-plus/minus adjusts it.

### Desktop and window behavior

- Desktop & Dock: set clicking the wallpaper to reveal the desktop to **Only in Stage Manager**.
- Under Mission Control: disable dragging windows to the top of the screen to enter Mission Control. Keep the separate fill-screen tiling gesture if you use it.
- Leave Stage Manager at your preferred setting; it is not enabled by this preset.
- Confirm the four Option-protected Hot Corners. Hold Option while selecting a corner's action to set its modifier in the native menu.
- If you re-enable desktop icons, turn on Stacks, group by Kind, and use approximately **36-point icons**, **13-point labels**, and **64-point spacing**. With desktop icons hidden these sizes have no visible effect.

### Finder organization

- Settings > Sidebar: keep your useful Favorites; hide Recents, Shared, Recent Tags, Bonjour computers, and Connected servers if you do not use them. This hides sidebar entries only.
- Collapse the Tags section; this does not delete tags.
- Drag your Work, Code, Screenshots, and Wallpapers folders into Favorites. Use your own folder names; do not recreate someone else's folder tree.
- View > Show Tab Bar. Open Home, Applications, Screenshots, Wallpapers, and Documents as separate tabs, then resize the window comfortably.
- Downloads: List view, newest Date Added first, with Date Added, Kind, and Size columns visible.
- Screenshots: Icon view, approximately **96-point** thumbnails.
- Wallpapers: Gallery view for a large preview.
- Documents: List view, grouped by Kind; turn on View > Show Preview for selected-file details.
- View > Customize Toolbar: keep navigation, view, grouping, sharing, search, **New Folder**, and **Quick Look**. Remove Tags and Action if you prefer the context menu. Drag the default toolbar back to undo the customization.

### Dock and menu bar

- Keep your own everyday apps and arrange them by purpose. Remove unused **shortcuts**, not apps.
- Drag Downloads to the folder side of the Dock. Choose **List** and **Date Added** in its context menu.
- Drag Applications to the folder side; display it as a folder and use Grid or List.
- Native Dock separators are optional; see the small command below. No personal app lineup is bundled.
- System Settings > Menu Bar (or Control Center): show **Sound** and **Bluetooth**, enable **battery percentage**, and keep Focus/Now Playing visible when active.
- Enable the menu-bar background where supported. Turn off Control Gallery suggestions, and set Recent Items to **5**.

Add a small, movable Dock gap with this optional native preference command, then log out/in or relaunch the Dock when convenient:

```sh
defaults write com.apple.dock persistent-apps -array-add '{"tile-type"="small-spacer-tile";}'
```

Run it once per gap, up to three, then drag each gap to the boundary you want. **Each execution adds another gap**, so this is not part of the repeatable preset. To undo, drag the blank gap out of the Dock. It does not remove an application.

### Trackpad and keyboard lighting

- Trackpad > Point & Click: choose **Light** physical click pressure if comfortable.
- Accessibility > Pointer Control > Trackpad Options: enable **three-finger dragging**. Use four fingers for desktop switching if macOS reallocates the gesture.
- Keyboard: turn keyboard backlight off after **one minute** of inactivity.
- Keyboard: turn on keyboard navigation if you want Tab to move among controls.
- Keep your existing key repeat and delay. Faster held-key repeat is intentionally excluded.

### Clipboard

In System Settings > Spotlight, enable Clipboard results/history and set retention to **7 days** if the choice is available. Open Spotlight with Command-Space, then Command-4 to view history. You may need to enable it once in Spotlight. Copy two harmless test phrases, then retrieve the first. Clear history from the Clipboard view's More menu. [Apple's clipboard guide](https://support.apple.com/en-gb/guide/mac-help/mchl40d5b86b/mac)

### Calendar

Calendar > Settings > Advanced: show week numbers and the Year-view activity/heat display. These change presentation only; no events or accounts are created.

## 4. Optional folder icons and Terminal theme

### Four local folder icons

The native generator creates magenta Work, Code, Screenshots, and Wallpapers icons using symbols supplied by macOS. It requires Apple's command line development tools and does not modify folders itself:

```sh
swift controls/folder-icons.swift
```

Images appear in `generated-icons/`, which is ignored by Git. To apply one: open its PNG in Preview, Select All and Copy; select your folder in Finder, choose Get Info, select the small icon at the top, then Paste. For a folder that already has a custom icon, copy/save its current icon first so you can restore it. To return to the standard folder icon, select the small icon in Get Info and press Delete.

The generator is Mac-only. Apple system symbols are not included as redistributable image assets in this repository.

### Neon Minimal Terminal profile

Open `controls/Neon-Minimal.terminal` to import the dark magenta, 14-point monospace profile. Select it in Terminal > Settings > Profiles and choose Default only if wanted. Return to your previous default profile to undo. The file contains only visual properties; it contains no shell command or working directory. Importing it was prepared, but setting it as the startup/default profile was not live-verified in the source session.

## 5. Optional two-second desktop edge switch

Requires [Hammerspoon](https://www.hammerspoon.org/) and Accessibility permission you grant yourself in System Settings. It is not installed or enabled by the preset. Use the [official getting-started guide](https://www.hammerspoon.org/go/) for installation and permissions.

1. Create at least two desktops in Mission Control.
2. System Settings > Keyboard > Keyboard Shortcuts > Mission Control: enable **Move left a space** and **Move right a space**, assigned to **Control-Left** and **Control-Right**.
3. Back up your existing `~/.hammerspoon` folder if it exists. Copy this repository's `controls` folder into it as `neon_horizon`; do not replace an existing configuration or same-named folder.
4. Add this line to your existing `~/.hammerspoon/init.lua` (create the file if absent):

```lua
dofile(hs.configdir .. "/neon_horizon/init.example.lua")
```

5. Reload Hammerspoon's configuration. With exactly one display attached, the helper detects its ID locally. Hold the pointer in the middle **40–60%** of the far-left/right **2-point strip** for **two continuous seconds**.
6. It sends Control-Left/Right once. Caps Lock may remain on. Leave the edge before another switch. Clicks, dragging, held modifiers, secure input, sleep, and display changes cancel pending switches. At the first/last Space the native shortcut may have nowhere to move; it does not wrap around.

If Accessibility prevents the event tap from starting, the helper reports it and releases its startup resources. Grant permission through System Settings, then reload.

For multiple displays it disables edge switching rather than guessing the active desktop. Reload after changing displays. If Control-Left/Right itself cannot switch desktops, correct that native shortcut before testing the helper. The OS decides which adjacent Space a shortcut enters, including full-screen app Spaces.

To enable the optional window/app shortcuts too, uncomment the final line of `controls/init.example.lua` in the installed copy. Check that the key combinations are unused. If an existing Hammerspoon binding conflicts or a new binding fails, startup stops and removes the shortcuts created by that attempt while preserving the existing ones:

| Keys | Action |
|---|---|
| Control-Option-Command-Left / Right | Left / right half |
| Control-Option-Command-C | Center at 80% of usable screen |
| Control-Option-Command-M | Maximize / restore |
| Control-Option-Command-Shift-G | Chrome |
| Control-Option-Command-Shift-T | Codex |
| Control-Option-Command-Shift-C | Claude |
| Control-Option-Command-Shift-F | Finder |

Edit the bundle IDs in `shortcuts.lua` for your apps. These shortcuts do not install missing apps. Full-screen and nonstandard windows are skipped.

**Disable:** quit Hammerspoon immediately, or remove the added line from `init.lua` and reload. Preserve the rest of your configuration. Remove the `neon_horizon` folder after disabling it. Accessibility permission can be revoked in System Settings.

Simulation checks cover dwell timing, cancellation, leave-to-rearm, display changes, shortcut geometry, and cleanup. A real desktop-switching permission/session test remains necessary on each Mac.

## 6. Undo and verify

Use `python3 makeover.py backups` to list original values saved in `~/Library/Application Support/Neon Horizon Makeover`. Restore the latest relevant file with:

```sh
python3 makeover.py undo --backup "PASTE_THE_EXACT_BACKUP_PATH_HERE"
```

Undo leaves any value you changed later and reports its key. It keeps created folders and backups. This command does not undo hand-configured UI choices, folder icons, Hammerspoon, Plash, or Dock gaps: use their instructions above. For native settings, reverse the choice in the same control using your recorded previous value.

Check appearance, Finder paths, a new screenshot's save location, clipboard copy/retrieval, desktop animation, and any optional gestures. Try the next login before relying on automatic wallpaper startup. Preference readback and simulated tests are useful but do not establish complete behavior on a different macOS version.
