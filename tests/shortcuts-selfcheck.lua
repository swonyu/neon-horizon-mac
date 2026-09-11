-- Run from tests/: lua shortcuts-selfcheck.lua
local bindings, launched, created, focused, failKey = {}, {}, {}, nil, nil
local function chord(mods, key) return table.concat(mods, "+") .. ":" .. key end
hs = {
    hotkey = {bind=function(mods, key, callback)
        if key == failKey then return nil end
        local name = chord(mods, key)
        local hotkey = {deleted=false}
        function hotkey:delete()
            assert(not self.deleted, "hotkey deleted twice")
            self.deleted = true; bindings[name] = nil
        end
        bindings[name] = callback; created[#created+1] = hotkey
        return hotkey
    end},
    window = {focusedWindow=function() return focused end},
    application = {launchOrFocusByBundleID=function(id)
        launched[#launched+1] = id; return true
    end},
}
local mods = {"ctrl", "alt", "cmd"}
local appMods = {"ctrl", "alt", "cmd", "shift"}
local function press(key, app)
    local callback = bindings[chord(app and appMods or mods, key)]
    assert(callback, "missing shortcut: " .. key)
    callback()
end
local function copy(f) return {x=f.x, y=f.y, w=f.w, h=f.h} end
local screen = {frame=function() return {x=-1600, y=24, w=1600, h=876} end}
local function window(id, frame)
    local w = {rect=copy(frame), standard=true, fullscreen=false, display=screen}
    function w:id() return id end
    function w:isStandard() return self.standard end
    function w:isFullScreen() return self.fullscreen end
    function w:screen() return self.display end
    function w:frame() return copy(self.rect) end
    function w:setFrameInScreenBounds(f) self.rect=copy(f); return self end
    function w:moveToUnit(unit)
        local f = self.display:frame()
        self.rect = {x=f.x+f.w*unit.x, y=f.y+f.h*unit.y, w=f.w*unit.w, h=f.h*unit.h}
        return self
    end
    function w:maximize() self.rect=self.display:frame(); return self end
    return w
end
local function frameIs(w, f, label)
    for _, k in ipairs({"x", "y", "w", "h"}) do
        assert(math.abs(w.rect[k]-f[k]) < 0.00001, label .. " mismatch: " .. k)
    end
end
local start = dofile("../controls/shortcuts.lua")
assert(type(start)=="function" and next(bindings)==nil, "loading must be inert")
local handle = start()
assert(#created==8, "expected exactly eight hotkeys")
assert(type(handle.stop)=="function", "missing stop()")
for _, key in ipairs({"left", "right", "c", "m"}) do press(key) end -- no window
local original = {x=-1480, y=120, w=900, h=650}
local a = window(1, original); focused=a
press("left"); frameIs(a, {x=-1600,y=24,w=800,h=876}, "left half")
press("right"); frameIs(a, {x=-800,y=24,w=800,h=876}, "right half")
press("c"); frameIs(a, {x=-1440,y=111.6,w=1280,h=700.8}, "centered 80 percent")
a.rect=copy(original)
press("m"); frameIs(a, screen:frame(), "maximize")
local other = {x=-1200,y=100,w=1000,h=720}
local b = window(2, other); focused=b
press("m"); frameIs(b, screen:frame(), "second maximize")
focused=a; press("m"); frameIs(a, original, "first restore")
focused=b; press("m"); frameIs(b, other, "second restore")
focused=a; press("m"); press("left"); press("m")
frameIs(a, screen:frame(), "layout resets restore state")
press("m"); frameIs(a, {x=-1600,y=24,w=800,h=876}, "restore new layout")
for _, invalid in ipairs({window(nil, original), window(3, original), window(4, original), window(5, original)}) do
    if invalid:id()==3 then invalid.standard=false end
    if invalid:id()==4 then invalid.fullscreen=true end
    if invalid:id()==5 then invalid.display=nil end
    focused=invalid
    for _, key in ipairs({"left", "right", "c", "m"}) do press(key) end
    frameIs(invalid, original, "unsupported window unchanged")
end
for _, item in ipairs({{"g","com.google.Chrome"}, {"t","com.openai.codex"},
    {"c","com.anthropic.claudefordesktop"}, {"f","com.apple.finder"}}) do
    press(item[1], true); assert(launched[#launched]==item[2], "wrong application")
end
handle:stop(); handle:stop()
assert(next(bindings)==nil, "stop left active shortcuts")
for _, hotkey in ipairs(created) do assert(hotkey.deleted, "hotkey leaked") end
failKey="t"
local ok, err = pcall(start)
assert(not ok and tostring(err):find("hotkey"), "binding failure must be reported")
assert(next(bindings)==nil, "failed start leaked active shortcuts")
print("PASS: 8 shortcuts; geometry, per-window restore, missing/unsupported windows, app IDs, stop and failed-start cleanup")
