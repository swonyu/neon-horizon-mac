-- Optional: copy this folder to ~/.hammerspoon/neon_horizon.
-- Append this line to your existing ~/.hammerspoon/init.lua:
-- dofile(hs.configdir .. "/neon_horizon/init.example.lua")
-- Quit Hammerspoon to disable the controls. Existing configuration stays intact.
local folder = hs.configdir .. "/neon_horizon/"
if neonHorizonEdge then neonHorizonEdge:stop() end
if neonHorizonShortcuts then neonHorizonShortcuts:stop() end
neonHorizonEdge, neonHorizonShortcuts = nil, nil

-- ponytail: one attached display only; reload after changing displays.
local displays = hs.screen.allScreens()
if #displays == 1 then
    neonHorizonEdge = dofile(folder .. "edge_dwell.lua")({
        screenUUID = displays[1]:getUUID(),
        delay = 2, strip = 2, top = 0.40, bottom = 0.60,
    })
else
    hs.alert.show("Neon Horizon edge switching needs one attached display")
end

-- Optional window and app hotkeys. Uncomment only if these chords are free.
-- neonHorizonShortcuts = dofile(folder .. "shortcuts.lua")()
