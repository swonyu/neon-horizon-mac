-- Loading is inert. Keep start()'s handle and call handle:stop() before reloading.
return function()
    local hotkeys, saved = {}, {}
    local handle = {stop=function()
        for _, hotkey in ipairs(hotkeys) do hotkey:delete() end
        hotkeys, saved = {}, {}
    end}
    local function bind(mods, key, callback)
        local ok, err=pcall(function()
            local hotkey=assert(hs.hotkey.new(mods, key, callback), "Could not create hotkey: "..key)
            hotkeys[#hotkeys+1]=hotkey -- Own it before any operation that can fail.
            for _, existing in ipairs(hs.hotkey.getHotkeys()) do
                assert(existing.idx~=hotkey.idx, "Hotkey already in use: "..hotkey.idx)
            end
            assert(hotkey:enable(), "Could not enable hotkey: "..key)
        end)
        if not ok then handle:stop(); error(err, 0) end
    end
    local function focusedWindow()
        local win = hs.window.focusedWindow()
        if win and win:id() and win:isStandard() and not win:isFullScreen() and win:screen() then
            return win
        end
    end
    local mods = {"ctrl", "alt", "cmd"}
    for key, rect in pairs({
        left={x=0,y=0,w=0.5,h=1}, right={x=0.5,y=0,w=0.5,h=1},
        c={x=0.1,y=0.1,w=0.8,h=0.8},
    }) do
        bind(mods, key, function()
            local win = focusedWindow()
            if win then
                saved[win:id()] = nil
                win:moveToUnit(rect, 0)
            end
        end)
    end
    bind(mods, "m", function()
        local win = focusedWindow()
        if not win then return end
        local id = win:id()
        if saved[id] then
            win:setFrameInScreenBounds(saved[id], 0)
            saved[id] = nil
        else
            saved[id] = win:frame()
            win:maximize(0)
        end
    end)
    for _, app in ipairs({
        {"g", "com.google.Chrome"}, {"t", "com.openai.codex"},
        {"c", "com.anthropic.claudefordesktop"}, {"f", "com.apple.finder"},
    }) do
        bind({"ctrl", "alt", "cmd", "shift"}, app[1], function()
            hs.application.launchOrFocusByBundleID(app[2])
        end)
    end
    return handle
end
