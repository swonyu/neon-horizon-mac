-- Run with Lua 5.4: lua edge-selfcheck.lua (from this directory).
-- Only the Hammerspoon host is mocked; edge_dwell.lua is the real implementation.
local implementation = assert(loadfile("../controls/edge_dwell.lua"), "edge_dwell.lua must exist")()
local tests = 0
local function check(name, scenario, config)
    local now, timers, taps, watchers, sent = 0, {}, {}, {}, {}
    local p = {x = 500, y = 500}
    local frame = {x = 0, y = 0, w = 1000, h = 1000}
    local buttons, modifiers, secure, connected = {}, {}, false, 1
    local screen = {getUUID = function() return "BUILT-IN" end,
        fullFrame = function() return {x=frame.x,y=frame.y,w=frame.w,h=frame.h} end}
    local function handle(fn)
        return {fn=fn, active=false,
            start=function(self) self.active=true; return self end,
            stop=function(self) self.active=false; return self end,
            isEnabled=function(self) return self.active end}
    end
    local types = {}
    for n, label in ipairs({"mouseMoved", "leftMouseDown", "leftMouseUp", "leftMouseDragged",
        "rightMouseDown", "rightMouseUp", "rightMouseDragged", "otherMouseDown",
        "otherMouseUp", "otherMouseDragged", "flagsChanged"}) do types[label] = n end
    hs = {
        mouse = {absolutePosition=function() return p end},
        screen = {find=function(uuid) if uuid=="BUILT-IN" and connected>0 then return screen end end,
            allScreens=function() local s={}; for i=1,connected do s[i]=screen end; return s end,
            watcher={new=function(fn) local w=handle(fn); watchers.screen=w; return w end}},
        caffeinate={watcher={new=function(fn) local w=handle(fn); watchers.sleep=w; return w end}},
        timer = {doAfter=function(delay, fn)
            local t=handle(fn); t.at=now+delay; t:start(); timers[#timers+1]=t; return t
        end},
        eventtap = {event={types=types},
            checkMouseButtons=function() return buttons end,
            checkKeyboardModifiers=function() return modifiers end,
            isSecureInputEnabled=function() return secure end,
            keyStroke=function(mods,key,delay)
                assert(#mods==1 and mods[1]=="ctrl" and delay==0, "only Ctrl-arrow is allowed")
                sent[#sent+1]={key=key,at=now}
            end,
            new=function(events, fn) local t=handle(fn); t.events=events; taps[#taps+1]=t; return t end}
    }
    local function event(label, x, y)
        if x then p={x=x,y=y} end
        for _, t in ipairs(taps) do
            for _, kind in ipairs(t.events) do
                if t.active and kind==types[label] then
                    local e={getType=function() return types[label] end,location=function() return p end}
                    assert(t.fn(e)==false, "events must pass through")
                end
            end
        end
    end
    local function wait(seconds)
        local deadline=now+seconds
        while true do
            local nextTimer
            for _, t in ipairs(timers) do
                if t.active and t.at<=deadline and (not nextTimer or t.at<nextTimer.at) then nextTimer=t end
            end
            if not nextTimer then break end
            now=nextTimer.at; nextTimer.active=false; nextTimer.fn()
        end
        now=deadline
    end
    local helper=implementation(config or {screenUUID="BUILT-IN"})
    scenario({move=function(x,y) event("mouseMoved",x,y) end, event=event, wait=wait, sent=sent,
        buttons=function(v) buttons=v end, modifiers=function(v) modifiers=v end,
        secure=function(v) secure=v end, displays=function(v) connected=v end,
        frame=frame, screenChange=function() watchers.screen.fn() end,
        sleep=function() watchers.sleep.fn(1) end, stop=function() helper:stop() end,
        disableTap=function() taps[1]:stop() end,
        teleport=function(x,y) p={x=x,y=y} end})
    helper:stop()
    tests=tests+1; print("PASS "..name)
end

check("two continuous seconds, one switch, leave to rearm, both sides", function(h)
    h.move(0,500); h.wait(1.99); assert(#h.sent==0, "fired early")
    h.move(1,510); h.wait(0.01); assert(#h.sent==1 and h.sent[1].key=="left", "left dwell did not fire")
    h.wait(6); h.move(0,500); h.wait(2); assert(#h.sent==1, "repeated while held")
    h.move(500,500); h.move(999,500); h.wait(2)
    assert(#h.sent==2 and h.sent[2].key=="right", "right did not rearm")
end)
check("leaving cancels and starts a fresh delay", function(h)
    h.move(0,500); h.wait(1.5); h.move(10,500); h.move(0,500)
    h.wait(0.5); assert(#h.sent==0); h.wait(1.5); assert(#h.sent==1)
end)
check("corners, outside display, center, exact strip boundaries", function(h)
    for _,p in ipairs({{0,399.9},{0,600.1},{2,500},{997.9,500},{1000,500},{-1,500},{500,500}}) do
        h.move(p[1],p[2]); h.wait(3); assert(#h.sent==0)
    end
    h.move(0,400); h.wait(2); assert(#h.sent==1)
    h.move(500,500); h.move(998,600); h.wait(2); assert(#h.sent==2)
end)
check("clicks and drags cancel and require leaving", function(h)
    for _,label in ipairs({"leftMouseDown","leftMouseUp","leftMouseDragged","rightMouseDown",
        "rightMouseUp","rightMouseDragged","otherMouseDown","otherMouseUp","otherMouseDragged"}) do
        h.move(500,500); h.move(0,500); h.wait(1); h.event(label); h.wait(2)
        h.move(1,500); h.wait(2); assert(#h.sent==0, label.." did not cancel")
    end
end)
check("button values, including false entries and extra buttons", function(h)
    h.buttons({[1]=false,left=false}); h.move(0,500); h.wait(2); assert(#h.sent==1)
    h.move(500,500); h.buttons({[1]=false,[4]=true}); h.move(0,500); h.wait(2); assert(#h.sent==1)
    h.buttons({}); h.move(500,500); h.move(0,500); h.wait(1); h.buttons({right=true}); h.wait(1)
    assert(#h.sent==1, "timer ignored a held button")
end)
check("modifiers and secure input gate entry and timer firing", function(h)
    for _,setter in ipairs({h.modifiers,h.secure}) do
        h.move(500,500); setter(setter==h.modifiers and {cmd=true} or true)
        h.move(0,500); h.wait(2); assert(#h.sent==0)
        setter(setter==h.modifiers and {} or false)
        h.move(500,500); h.move(0,500); h.wait(1)
        setter(setter==h.modifiers and {shift=true} or true); h.wait(1); assert(#h.sent==0)
        setter(setter==h.modifiers and {} or false)
    end
    h.move(500,500); h.move(0,500); h.wait(1); h.event("flagsChanged"); h.wait(1)
    assert(#h.sent==0, "brief modifier event failed to cancel")
end)
check("sleep and display notifications cancel until leaving", function(h)
    for _,signal in ipairs({h.sleep,h.screenChange}) do
        h.move(500,500); h.move(0,500); h.wait(1); signal(); h.wait(2)
        h.move(1,500); h.wait(2); assert(#h.sent==0)
    end
    h.move(500,500); h.move(0,500); h.wait(2); assert(#h.sent==1)
end)
check("frame changes and screen removal rechecked at firing", function(h)
    h.move(0,500); h.wait(1); h.frame.h=900; h.wait(1); assert(#h.sent==0)
    h.move(500,500); h.move(0,500); h.wait(1); h.displays(0); h.wait(1); assert(#h.sent==0)
end)
check("extra display disables both entry and firing", function(h)
    h.displays(2); h.move(0,500); h.wait(2); assert(#h.sent==0)
    h.displays(1); h.move(500,500); h.move(0,500); h.wait(1); h.displays(2); h.wait(1)
    assert(#h.sent==0)
end)
check("timer rechecks actual pointer and event tap; stop cancels", function(h)
    h.move(0,500); h.wait(1); h.teleport(500,500); h.wait(1); assert(#h.sent==0)
    h.move(500,500); h.move(0,500); h.wait(1); h.disableTap(); h.wait(1); assert(#h.sent==0)
end)
check("stopping releases timers and watchers", function(h)
    h.move(0,500); h.wait(1); h.stop(); h.wait(3); assert(#h.sent==0)
    h.move(500,500); h.move(0,500); h.wait(3); assert(#h.sent==0)
end)
check("configured delay and zone work with an offset display", function(h)
    h.frame.x=-1000; h.frame.y=200
    h.move(-997.5,500); h.wait(2.99); assert(#h.sent==0)
    h.wait(0.01); assert(#h.sent==1)
end, {screenUUID="BUILT-IN", delay=3, strip=3, top=0.30, bottom=0.70})
check("UUID must match instead of silently using the only display", function(h)
    h.move(0,500); h.wait(3); assert(#h.sent==0)
end, {screenUUID="UNKNOWN"})
for _,config in ipairs({{}, {screenUUID=""}, {screenUUID="BUILT-IN",delay=0},
    {screenUUID="BUILT-IN",delay=math.huge}, {screenUUID="BUILT-IN",strip=-1},
    {screenUUID="BUILT-IN",top=0.8,bottom=0.2}}) do
    assert(not pcall(implementation,config), "invalid configuration must fail before watching")
end
print("PASS invalid configuration is rejected")
print(string.format("PASS %d scenarios; real module, mocked Hammerspoon host; no UI actions",tests))
