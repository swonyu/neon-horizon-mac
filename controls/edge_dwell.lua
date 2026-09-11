-- Loading this module does nothing. Call the returned function when you choose to enable edge switching.
-- Keep its returned handle alive; handle:stop() releases every watcher and timer.
return function(config)
    assert(type(config)=="table" and type(config.screenUUID)=="string"
        and #config.screenUUID>0, "Supply the selected display UUID")
    local delay, strip = config.delay or 2, config.strip or 2
    local top, bottom = config.top or 0.40, config.bottom or 0.60
    local function finite(n) return type(n)=="number" and n==n and math.abs(n)<math.huge end
    assert(finite(delay) and delay>0 and finite(strip) and strip>0, "Invalid delay or strip")
    assert(finite(top) and finite(bottom) and top>=0 and top<bottom and bottom<=1,
        "Invalid vertical zone")
    local timer, side, blocked, tap
    local function cancel(requireLeave)
        if timer then timer:stop(); timer=nil end
        side=nil; blocked=requireLeave
    end
    local function anyTrue(values)
        for _, value in pairs(values) do if value==true then return true end end
        return false
    end
    local function inputBlocked()
        return hs.eventtap.isSecureInputEnabled()
            or anyTrue(hs.eventtap.checkMouseButtons())
            or anyTrue(hs.eventtap.checkKeyboardModifiers())
    end
    local function zone(point)
        -- ponytail: one display only; validate shortcut focus before adding multi-display support.
        if #hs.screen.allScreens()~=1 then return nil end
        local screen=hs.screen.find(config.screenUUID)
        if not screen or screen:getUUID()~=config.screenUUID then return nil end
        local f=screen:fullFrame()
        if strip*2>=f.w then return nil end
        local geometry=table.concat({f.x,f.y,f.w,f.h}, ":")
        if point.y<f.y+f.h*top or point.y>f.y+f.h*bottom
            or point.x<f.x or point.x>=f.x+f.w then return nil, geometry end
        if point.x<f.x+strip then return "left", geometry end
        if point.x>=f.x+f.w-strip then return "right", geometry end
        return nil, geometry
    end
    local function observe(point)
        local current, geometry=zone(point)
        if not geometry then cancel(true); return end
        if not current then cancel(false); return end
        if inputBlocked() then cancel(true); return end
        if blocked then return end
        if current==side then return end
        cancel(false); side=current
        timer=hs.timer.doAfter(delay, function()
            timer=nil
            local actual, actualGeometry=zone(hs.mouse.absolutePosition())
            if actual==current and actualGeometry==geometry and tap:isEnabled() and not inputBlocked() then
                cancel(true) -- Latch before sending our own modifier events.
                hs.eventtap.keyStroke({"ctrl"}, current, 0)
            else
                cancel(true)
            end
        end)
    end
    local events=hs.eventtap.event.types
    tap=hs.eventtap.new({events.mouseMoved, events.leftMouseDown, events.leftMouseUp,
        events.leftMouseDragged, events.rightMouseDown, events.rightMouseUp,
        events.rightMouseDragged, events.otherMouseDown, events.otherMouseUp,
        events.otherMouseDragged, events.flagsChanged}, function(event)
        if event:getType()==events.mouseMoved then observe(event:location()) else cancel(true) end
        return false -- Do not consume clicks, drags, motion, or modifier events.
    end):start()
    local displayWatcher=hs.screen.watcher.new(function() cancel(true) end):start()
    local sleepWatcher=hs.caffeinate.watcher.new(function() cancel(true) end):start()
    return {stop=function()
        cancel(true); tap:stop(); displayWatcher:stop(); sleepWatcher:stop()
    end}
end
