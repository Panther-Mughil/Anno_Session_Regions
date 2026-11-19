"""Build a session menu gate from a config file and a region preset.

The generated mod has four parts:
  * modinfo.json, with the Streets Unified dependency
  * data/config/export/main/asset/assets.xml, the session triggers
  * data/script/<prefix>_<module>_{hide,show,creative}.lua, the lock lists
  * runtime logs under logs/<prefix>.log, written by every generated script

The engine matches the hardened private generator:
  * hide: ConditionActiveSession on the hidden session, ResetTrigger 2000 ms;
  * restore: one trigger per named show session, a generic trigger conditioned
    on the hidden session with SessionBlacklist 1, and a settle trigger that
    consumes a locked FeatureUnlock flag after a 500 ms arrival cue;
  * creative variants of the named, generic and settle triggers;
  * v2 restore markers with a signature and a 6 h age limit;
  * a rotated runtime log with per-key dedupe and every io/os call in pcall.

Each module is independent. The core module covers the base game, and every
compatibility module covers one group of installed mods, so a problem in one
module cannot break the other modules.

Usage:
  python src/generate.py --config examples/new_world/config.json
  python src/generate.py --config examples/new_world/config.json \
      --compat compat.json --out out/new_world
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    ToolError,
    as_guid,
    fail,
    guid_list,
    info,
    load_preset,
    load_sessions,
    preset_street_guids,
    read_item_file,
    read_json,
    warn,
)
from version import __version__  # noqa: E402

TOOLKIT_NAME = "Anno Session Regions"
DEFAULT_INCLUDE = ["leaves", "containers", "tabs"]
LANGUAGES = (
    "Chinese",
    "English",
    "French",
    "German",
    "Italian",
    "Japanese",
    "Korean",
    "Polish",
    "Russian",
    "Spanish",
    "Taiwanese",
)


def localized(value: str) -> dict:
    """All 11 modinfo language keys, with the English value filled in."""
    return {language: (value if language == "English" else None) for language in LANGUAGES}


# Runtime log and marker block, prepended to every generated script. It is NOT
# passed through str.format: braces are literal Lua. Placeholders are plain
# replaces. This block is byte-for-byte the hardened engine.
#
# Rules it implements:
#   - one line per state change: an identical ident+session+branch+marker+failed
#     repeat inside LOGWINDOW seconds is skipped (the hide trigger re-fires
#     every 2 s). With no clock, dedupe is skipped entirely rather than storing
#     a zero timestamp;
#   - bounded: logs/<name>.log rotates to logs/<name>.prev.log at LIMIT bytes,
#     one backup kept; the backup is only replaced by a successful rename;
#   - fail-safe: every file call runs inside pcall(function() ... end), so a
#     missing io/os table cannot break the gate; logs/menugate_debug.off
#     disables the log entirely;
#   - restore markers are stamped "v2|<signature>|<os.time>". A marker counts
#     only when its signature (script ident + item count) matches and it is
#     younger than MARKER_AGE seconds, so one that survives a failed removal
#     expires instead of latching a restore off forever.
LOG_LUA = """-- ---------------------------------------------------------------------------
-- Runtime log and file helpers. Writes logs/menugate.log next to the game's
-- other logs. One line per state change; an identical script+session+branch+
-- marker+failed repeat inside 60 s is skipped, so the 2 s re-fire does not
-- spam. Rotates to logs/menugate.prev.log at 256 KB and keeps one backup.
-- Every file call runs inside pcall(function() ... end), so a missing io or os
-- table cannot break the gate. Create logs/menugate_debug.off to silence it.
--
-- Restore markers are stamped "v2|<signature>|<os.time>". A marker only counts
-- when the signature (script ident + item count) matches and it is younger
-- than MARKER_AGE seconds. Empty, garbled, foreign and stale markers are
-- treated as absent, so a marker that survives a failed removal expires
-- instead of latching a restore off forever.
-- ---------------------------------------------------------------------------
local IDENT = "__IDENT__"
local LOGFILE = "__LOGFILE__"
local LOGBACKUP = "__LOGBACKUP__"
local LOGCURSOR = "__LOGCURSOR__"
local LOGLIMIT = __LIMIT__
local LOGWINDOW = __WINDOW__
local MARKER_AGE = __MARKERAGE__
local NAMED_SESSIONS = { __NAMED__ }
local KNOWN_SESSIONS = {
__KNOWN__
}

local fails = {}

local function note_fail(guid, err)
    fails[#fails + 1] = { guid, err }
end

local function log_stamp()
    local ok, s = pcall(function() return os.date("!%Y-%m-%d %H:%M:%S") end)
    if ok and type(s) == "string" and s ~= "" then return s end
    return "0000-00-00 00:00:00"
end

local function log_now()
    local ok, t = pcall(function() return os.time() end)
    if ok and type(t) == "number" then return t end
    return nil
end

local function log_disabled()
    local ok, f = pcall(function() return io.open("logs/menugate_debug.off", "r") end)
    if ok and f then
        pcall(function() f:close() end)
        return true
    end
    return false
end

-- ---------------------------------------------------------------- markers --
local function marker_exists(path)
    local ok, f = pcall(function() return io.open(path, "r") end)
    if ok and f then
        pcall(function() f:close() end)
        return true
    end
    return false
end

local function marker_sig_of(count)
    return IDENT .. "|" .. tostring(count)
end

local function marker_now()
    local ok, t = pcall(function() return os.time() end)
    if ok and type(t) == "number" then return t end
    return nil
end

local function marker_valid(path, sig, limit)
    local ok, f = pcall(function() return io.open(path, "r") end)
    if not (ok and f) then return false end
    local rok, data = pcall(function() return f:read("*a") end)
    pcall(function() f:close() end)
    if not (rok and type(data) == "string") then return false end
    local msig, at = data:match("^v2|(.*)|(%-?%d+)%s*$")
    if not msig or msig ~= sig then return false end
    local n = tonumber(at)
    if not n or n <= 0 then return false end
    local now = marker_now()
    if not now then return false end
    local age = now - n
    if age < 0 or age > limit then return false end
    return true
end

local function marker_write(path, sig, at)
    local ok, err = pcall(function()
        local out = io.open(path, "w")
        if not out then error("cannot open for write") end
        out:write("v2|" .. tostring(sig) .. "|" .. tostring(at) .. "\\n")
        out:close()
    end)
    if not ok then note_fail(path, "marker_write:" .. tostring(err)) end
end

-- Removing a marker must never latch a restore off. If the file cannot be
-- deleted, overwrite it with an invalid stamp so the next restore still runs.
-- A failed write here is logged and the age limit bounds the damage.
local function marker_remove(path)
    if not marker_exists(path) then return end
    local ok, err = pcall(function()
        local rok, rerr = os.remove(path)
        if not rok then error(tostring(rerr or "remove failed")) end
    end)
    if ok then return end
    note_fail(path, "marker_remove:" .. tostring(err))
    marker_write(path, "invalidated", 0)
end

-- -------------------------------------------------------------------- log --
local function log_rotate()
    local ok, f = pcall(function() return io.open(LOGFILE, "r") end)
    if not (ok and f) then return end
    local sok, size = pcall(function() return f:seek("end") end)
    pcall(function() f:close() end)
    if not (sok and type(size) == "number" and size >= LOGLIMIT) then return end
    -- Rename first. A successful rename is what replaces the old backup, so a
    -- failed rename can never leave the log path missing.
    local rok = pcall(function()
        local r, e = os.rename(LOGFILE, LOGBACKUP)
        if not r then error(tostring(e or "rename failed")) end
    end)
    if rok then return end
    -- A filesystem that refuses to overwrite the backup: drop it and retry.
    local dropped = pcall(function()
        local r, e = os.remove(LOGBACKUP)
        if not r then error(tostring(e or "remove failed")) end
    end)
    if dropped then
        pcall(function()
            local r, e = os.rename(LOGFILE, LOGBACKUP)
            if not r then error(tostring(e or "rename failed")) end
        end)
    end
end

-- Cursor: one "epoch|ident|session|branch|marker|failed=N" line per distinct
-- key, so two modules alternating every 2 s do not overwrite each other's
-- dedup state. It is rewritten through a temp file and renamed into place, so
-- an interrupted write cannot truncate the history.
local function log_state_read(key)
    local ok, f = pcall(function() return io.open(LOGCURSOR, "r") end)
    if not (ok and f) then return nil end
    local rok, data = pcall(function() return f:read("*a") end)
    pcall(function() f:close() end)
    if not (rok and type(data) == "string") then return nil end
    for line in data:gmatch("[^\\r\\n]+") do
        local at, k = line:match("^(%-?%d+)|(.*)$")
        if k == key then return tonumber(at) end
    end
    return nil
end

local function log_state_write(at, key)
    pcall(function()
        local kept = {}
        local f = io.open(LOGCURSOR, "r")
        if f then
            local data = f:read("*a")
            f:close()
            if type(data) == "string" then
                for line in data:gmatch("[^\\r\\n]+") do
                    local k = line:match("^%-?%d+|(.*)$")
                    if k ~= key then kept[#kept + 1] = line end
                end
            end
        end
        kept[#kept + 1] = tostring(at or 0) .. "|" .. key
        while #kept > 48 do table.remove(kept, 1) end
        local tmp = LOGCURSOR .. ".tmp"
        local out = io.open(tmp, "w")
        if out then
            out:write(table.concat(kept, "\\n") .. "\\n")
            out:close()
            local rok = os.rename(tmp, LOGCURSOR)
            if not rok then
                os.remove(LOGCURSOR)
                local r2 = os.rename(tmp, LOGCURSOR)
                if not r2 then os.remove(tmp) end
            end
        end
    end)
end

local function log_clean(value)
    local s = tostring(value or "")
    s = s:gsub("[%c]", " ")
    s = s:gsub("|", "/")
    if #s > 120 then s = s:sub(1, 120) end
    return s
end

-- Display label for a session GUID. Named sessions come from the config's
-- known_sessions list; this affects LOG TEXT ONLY. It never changes branch,
-- via, marker, item actions, dedupe or rotation, and an unlisted GUID still
-- restores exactly as before.
local function session_label(sid)
    local n = tonumber(sid)
    if not n then return tostring(sid) end
    local known = KNOWN_SESSIONS[n]
    if known then return tostring(sid) .. "(" .. known.name .. ")" end
    return tostring(sid) .. "(unknown)"
end

local function region_label(sid)
    local n = tonumber(sid)
    if not n then return nil end
    local known = KNOWN_SESSIONS[n]
    if known and known.region then
        return tostring(known.region) .. "(" .. known.region_name .. ")"
    end
    return nil
end

local function gate_log(sid, branch, via, marker, items, okc)
    if log_disabled() then return end
    -- The failed count is part of the key: a successful hide must never mask a
    -- failed one with the same key. With no clock, dedupe is skipped entirely.
    local key = IDENT .. "|" .. tostring(sid) .. "|" .. tostring(branch)
        .. "|" .. tostring(marker) .. "|failed=" .. tostring(#fails)
    local now = log_now()
    if now then
        local at = log_state_read(key)
        if at and (now - at) < LOGWINDOW then return end
    end
    local parts = {
        log_stamp(),
        IDENT,
        "session=" .. session_label(sid),
        "branch=" .. tostring(branch),
        "via=" .. tostring(via),
        "marker=" .. tostring(marker),
        "items=" .. tostring(items),
        "ok=" .. tostring(okc),
        "failed=" .. tostring(#fails),
    }
    local region = region_label(sid)
    if region then
        table.insert(parts, 4, "region=" .. region)
    end
    for i = 1, #fails do
        if i > 5 then
            parts[#parts + 1] = "..."
            break
        end
        parts[#parts + 1] = "fail=" .. tostring(fails[i][1]) .. ":" .. log_clean(fails[i][2])
    end
    local line = table.concat(parts, " | ")
    log_rotate()
    local wrote = false
    pcall(function()
        local f = io.open(LOGFILE, "a")
        if f then
            f:write(line .. "\\n")
            f:close()
            wrote = true
        end
    end)
    -- Only remember the line once it was actually appended, so a failed append
    -- cannot suppress the next report.
    if wrote and now then log_state_write(now, key) end
end

local function session_guid()
    local active = nil
    pcall(function() active = session.getSessionGUID() end)
    local n = tonumber(active)
    if n then return tostring(n), n end
    return "unknown", nil
end

local function via_for(sid_num)
    for i = 1, #NAMED_SESSIONS do
        if sid_num == NAMED_SESSIONS[i] then return "named" end
    end
    return "generic"
end
"""


def lua_string(text: object) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def render_known(known_sessions: list[dict]) -> str:
    """Lua entries for the display-name map. Log text only, never behaviour."""
    lines = []
    for entry in known_sessions:
        fields = ['name = "%s"' % lua_string(entry["name"])]
        if entry.get("region") is not None:
            fields.append("region = %d" % int(entry["region"]))
            fields.append('region_name = "%s"' % lua_string(entry.get("region_name", "")))
        lines.append("    [%d] = { %s }," % (int(entry["guid"]), ", ".join(fields)))
    return "\n".join(lines)


def render_log(
    ident: str,
    named: list[str],
    known: list[dict],
    log_file: str,
    log_backup: str,
    log_cursor: str,
    limit: int,
    window: int,
    marker_age: int,
) -> str:
    """Fill the logging prelude. Plain replaces: the block keeps literal braces."""
    named_lua = ", ".join(str(guid) for guid in named)
    return (
        LOG_LUA.replace("__IDENT__", ident)
        .replace("__NAMED__", named_lua)
        .replace("__KNOWN__", render_known(known))
        .replace("__LOGFILE__", log_file)
        .replace("__LOGBACKUP__", log_backup)
        .replace("__LOGCURSOR__", log_cursor)
        .replace("__LIMIT__", str(limit))
        .replace("__WINDOW__", str(window))
        .replace("__MARKERAGE__", str(marker_age))
    )


HIDE_LUA = """-- Generated by Anno Session Regions {toolkit_version}. Do not hand edit.
-- Module: {module_name}
-- Locks {count} assets while the active session is {session_name} ({session_guid}).
-- Restore is handled by the session-entry script in every other session.
-- Writes one runtime log line per state change (log block below).

local ITEMS = {{
{items}
}}

local ALWAYS_UNLOCKED = {{
{always}
}}

local MARKER = "{marker}"
local MARKER_CREATIVE = "{marker_creative}"

{log}

for i = 1, #ALWAYS_UNLOCKED do
    local ok, err = pcall(ts.Unlock.SetUnlockNet, ALWAYS_UNLOCKED[i])
    if not ok then note_fail(ALWAYS_UNLOCKED[i], "keep_unlocked:" .. tostring(err)) end
end

local sid = session_guid()
local marker_before = marker_exists(MARKER)

local okc = 0
for i = 1, #ITEMS do
    local ok, err = pcall(ts.Unlock.SetRelockNet, ITEMS[i])
    if ok then okc = okc + 1 else note_fail(ITEMS[i], err) end
end

-- Re-arm both one-shot restores for the next session change. A removal that
-- fails is logged and leaves an invalid marker, never a valid one.
marker_remove(MARKER)
marker_remove(MARKER_CREATIVE)

gate_log(sid, "hide", "hide", marker_before and "present" or "absent", #ITEMS, okc)
"""

SHOW_LUA = """-- Generated by Anno Session Regions {toolkit_version}. Do not hand edit.
-- Module: {module_name}
-- Runs on every session entry. Reads the active session GUID and decides:
--   inside {session_name} ({session_guid}) -> relock {count} assets (hide);
--   any other session                      -> restore progression.
-- Restoring re-registers the game's own unlock triggers so progression decides
-- what is available. Assets without a trigger are unlocked directly.
-- Writes one runtime log line per state change (log block below).

local HIDE_SESSION = {session_guid}

local ITEMS = {{
{items}
}}

local ALWAYS_UNLOCKED = {{
{always}
}}

local MARKER = "{marker}"
local MARKER_CREATIVE = "{marker_creative}"

{log}

local SIG = marker_sig_of(#ITEMS)

for i = 1, #ALWAYS_UNLOCKED do
    local ok, err = pcall(ts.Unlock.SetUnlockNet, ALWAYS_UNLOCKED[i])
    if not ok then note_fail(ALWAYS_UNLOCKED[i], "keep_unlocked:" .. tostring(err)) end
end

-- The client that runs ActionExecuteScript answers for its own session. If the
-- API is unavailable this stays nil and the script takes the restore path; the
-- hide trigger still re-locks {session_name} every 2 s.
local sid, sid_num = session_guid()

if sid_num == HIDE_SESSION then
    local okc = 0
    for i = 1, #ITEMS do
        local ok, err = pcall(ts.Unlock.SetRelockNet, ITEMS[i])
        if ok then okc = okc + 1 else note_fail(ITEMS[i], err) end
    end
    local marker_before = marker_exists(MARKER)
    marker_remove(MARKER)
    marker_remove(MARKER_CREATIVE)
    gate_log(sid, "hide", "hide", marker_before and "present" or "absent", #ITEMS, okc)
    return
end

if marker_valid(MARKER, SIG, MARKER_AGE) then
    -- A repeat after a successful restore: the settle/arrival re-run or a
    -- trigger re-arm. Neither is distinguishable without a script parameter,
    -- so both log as branch=settle. No item action is taken on this path.
    gate_log(sid, "settle", "settle", "present", #ITEMS, 0)
    return
end

local triggers = {{}}
for i = 1, #ITEMS do
    local ok, t = pcall(ts.ToolOneDataHelper.GetUnlockTriggerForAsset, ITEMS[i])
    if ok and t and tonumber(t) and tonumber(t) ~= 0 then
        triggers[tonumber(t)] = true
    end
end

local reg_ok, reg_err = {{}}, {{}}
for t in pairs(triggers) do
    local ok, err = pcall(ts.Conditions.RegisterTriggerForCurrentParticipant, t)
    reg_ok[t] = ok
    if not ok then reg_err[t] = err end
end

local okc = 0
for i = 1, #ITEMS do
    local g = ITEMS[i]
    local qok, t = pcall(ts.ToolOneDataHelper.GetUnlockTriggerForAsset, g)
    if not qok then
        -- An exception is NOT "no progression trigger". Never fall through to a
        -- direct unlock after a failed lookup: that grants an unearned item.
        note_fail(g, "lookup:" .. tostring(t))
    elseif t and tonumber(t) and tonumber(t) ~= 0 then
        local tt = tonumber(t)
        -- Success is counted only for a trigger this run actually registered.
        -- A trigger first seen on this second lookup was never registered.
        if reg_ok[tt] == true then
            okc = okc + 1
        else
            note_fail(g, reg_err[tt] or "trigger not registered")
        end
    else
        local ok, err = pcall(ts.Unlock.SetUnlockNet, g)
        if ok then okc = okc + 1 else note_fail(g, err) end
    end
end

-- The marker is written only when every item succeeded: a failure is retried
-- on the next visit instead of being latched. It carries the signature and
-- os.time so a survivor of a failed removal expires (MARKER_AGE) and a change
-- in the item list invalidates it.
if okc == #ITEMS and #fails == 0 then
    local now = marker_now()
    if now then marker_write(MARKER, SIG, now) end
end

gate_log(sid, "restore", via_for(sid_num), "absent", #ITEMS, okc)
"""

CREATIVE_LUA = """-- Generated by Anno Session Regions {toolkit_version}. Do not hand edit.
-- Module: {module_name}
-- Runs on every session entry in creative mode. Reads the active session GUID
-- and decides: inside {session_name} ({session_guid}) -> relock {count} assets;
-- any other session -> unlock every item directly, because creative has no
-- progression triggers. One-shot per visit: the creative marker stops the 2 s
-- re-arm from re-issuing the unlocks. Writes one log line per state change.

local HIDE_SESSION = {session_guid}

local ITEMS = {{
{items}
}}

local ALWAYS_UNLOCKED = {{
{always}
}}

local MARKER = "{marker_creative}"

{log}

local SIG = marker_sig_of(#ITEMS)

for i = 1, #ALWAYS_UNLOCKED do
    local ok, err = pcall(ts.Unlock.SetUnlockNet, ALWAYS_UNLOCKED[i])
    if not ok then note_fail(ALWAYS_UNLOCKED[i], "keep_unlocked:" .. tostring(err)) end
end

local sid, sid_num = session_guid()

if sid_num == HIDE_SESSION then
    local okc = 0
    for i = 1, #ITEMS do
        local ok, err = pcall(ts.Unlock.SetRelockNet, ITEMS[i])
        if ok then okc = okc + 1 else note_fail(ITEMS[i], err) end
    end
    marker_remove(MARKER)
    gate_log(sid, "hide", "hide", "none", #ITEMS, okc)
    return
end

-- Creative restore is one-shot per visit too. Without this guard the module's
-- trigger re-arms every 2 s and re-issues every direct unlock forever.
if marker_valid(MARKER, SIG, MARKER_AGE) then
    gate_log(sid, "settle", "settle", "present", #ITEMS, 0)
    return
end

local okc = 0
for i = 1, #ITEMS do
    local ok, err = pcall(ts.Unlock.SetUnlockNet, ITEMS[i])
    if ok then okc = okc + 1 else note_fail(ITEMS[i], err) end
end

-- Written only when every item succeeded, so a partial restore is retried.
if okc == #ITEMS and #fails == 0 then
    local now = marker_now()
    if now then marker_write(MARKER, SIG, now) end
end

gate_log(sid, "creative", via_for(sid_num), "absent", #ITEMS, okc)
"""

HIDE_TRIGGER = """    <ModOp Type="addNextSibling" GUID="130248">
        <Asset>
            <Template>Trigger</Template>
            <Values>
                <Standard>
                    <GUID>{guid}</GUID>
                    <Name>{name}</Name>
                </Standard>
                <Trigger>
                    <TriggerCondition>
                        <Template>ConditionActiveSession</Template>
                        <Values>
                            <Condition />
                            <ConditionActiveSession>
                                <ActiveSession>{session}</ActiveSession>
                            </ConditionActiveSession>
                        </Values>
                    </TriggerCondition>
                    <TriggerActions>
                        <Item>
                            <TriggerAction>
                                <Template>ActionExecuteScript</Template>
                                <Values>
                                    <Action />
                                    <ActionExecuteScript>
                                        <ScriptFileName>data/script/{script}</ScriptFileName>
                                    </ActionExecuteScript>
                                </Values>
                            </TriggerAction>
                        </Item>
                    </TriggerActions>{subs}
                    <ResetTrigger>
                        <Template>AutoCreateTrigger</Template>
                        <Values>
                            <Trigger>
                                <TriggerCondition>
                                    <Template>ConditionTimer</Template>
                                    <Values>
                                        <Condition />
                                        <ConditionTimer>
                                            <TimeLimit>2000</TimeLimit>
                                        </ConditionTimer>
                                    </Values>
                                </TriggerCondition>
                            </Trigger>
                        </Values>
                    </ResetTrigger>
                </Trigger>
                <TriggerSetup>
                    <AutoRegisterTrigger>1</AutoRegisterTrigger>
                </TriggerSetup>
            </Values>
        </Asset>
    </ModOp>
"""

# The generic restore path. One trigger per module per mode, conditioned on
# "active session is NOT the hide session" with the vanilla SessionBlacklist
# flag (vanilla uses this shape, e.g. ActiveSession 180039 with
# SessionBlacklist 1).
#
# The script is the same restore script the named-session triggers run, so the
# restore marker keeps both paths idempotent. ActionDelayedActions re-runs the
# same script after the delay, in whatever session is active then (the
# arrival-last cue). The ResetTrigger timer re-arms the state trigger; the
# marker makes every re-run a no-op, so the cue cannot loop.
GENERIC_TRIGGER = """    <ModOp Type="addNextSibling" GUID="130248">
        <Asset>
            <Template>Trigger</Template>
            <Values>
                <Standard>
                    <GUID>{guid}</GUID>
                    <Name>{name}</Name>
                </Standard>
                <Trigger>
                    <TriggerCondition>
                        <Template>ConditionActiveSession</Template>
                        <Values>
                            <Condition />
                            <ConditionActiveSession>
                                <ActiveSession>{hide_session}</ActiveSession>
                                <SessionBlacklist>1</SessionBlacklist>
                            </ConditionActiveSession>
                        </Values>
                    </TriggerCondition>
                    <TriggerActions>
                        <Item>
                            <TriggerAction>
                                <Template>ActionExecuteScript</Template>
                                <Values>
                                    <Action />
                                    <ActionExecuteScript>
                                        <ScriptFileName>data/script/{script}</ScriptFileName>
                                    </ActionExecuteScript>
                                </Values>
                            </TriggerAction>
                        </Item>
                        <Item>
                            <TriggerAction>
                                <Template>ActionDelayedActions</Template>
                                <Values>
                                    <Action />
                                    <ActionDelayedActions>
                                        <ExecutionDelay>{delay}</ExecutionDelay>
                                        <DelayedActions>
                                            <IsBaseAutoCreateAsset>1</IsBaseAutoCreateAsset>
                                            <Values>
                                                <ActionList>
                                                    <Actions>
                                                        <Item>
                                                            <Action>
                                                                <Template>ActionUnlockAsset</Template>
                                                                <Values>
                                                                    <Action />
                                                                    <ActionUnlockAsset>
                                                                        <UnlockAssets>
                                                                            <Item>
                                                                                <Asset>{settle_flag}</Asset>
                                                                            </Item>
                                                                        </UnlockAssets>
                                                                    </ActionUnlockAsset>
                                                                </Values>
                                                            </Action>
                                                        </Item>
                                                    </Actions>
                                                </ActionList>
                                            </Values>
                                        </DelayedActions>
                                    </ActionDelayedActions>
                                </Values>
                            </TriggerAction>
                        </Item>
                    </TriggerActions>{subs}
                    <ResetTrigger>
                        <Template>AutoCreateTrigger</Template>
                        <Values>
                            <Trigger>
                                <TriggerCondition>
                                    <Template>ConditionTimer</Template>
                                    <Values>
                                        <Condition />
                                        <ConditionTimer>
                                            <TimeLimit>2000</TimeLimit>
                                        </ConditionTimer>
                                    </Values>
                                </TriggerCondition>
                            </Trigger>
                        </Values>
                    </ResetTrigger>
                </Trigger>
                <TriggerSetup>
                    <AutoRegisterTrigger>1</AutoRegisterTrigger>
                </TriggerSetup>
            </Values>
        </Asset>
    </ModOp>
"""

# A locked flag, copied from the shared semi-region menu's FeatureUnlock flag
# (anchored on vanilla 133179 = "Player has 10 000 Asset", a FeatureUnlock).
# The delayed action unlocks it; the settle trigger consumes it.
FLAG_ASSET = """    <ModOp Type="addNextSibling" GUID="133179">
        <Asset>
            <Template>FeatureUnlock</Template>
            <Values>
                <Standard>
                    <GUID>{guid}</GUID>
                    <Name>{name}</Name>
                </Standard>
                <Locked />
                <Trigger>
                    <TriggerCondition>
                        <IsBaseAutoCreateAsset>1</IsBaseAutoCreateAsset>
                        <Values>
                            <Condition />
                            <ConditionAlwaysTrue />
                        </Values>
                    </TriggerCondition>
                    <ResetTrigger>
                        <IsBaseAutoCreateAsset>1</IsBaseAutoCreateAsset>
                        <Values>
                            <EmptyAutoCreateValue />
                        </Values>
                    </ResetTrigger>
                </Trigger>
                <TriggerSetup>
                    <AutoRegisterTrigger>0</AutoRegisterTrigger>
                    <UsedBySecondParties>0</UsedBySecondParties>
                </TriggerSetup>
            </Values>
        </Asset>
    </ModOp>
"""

# Fires once each time the delayed action unlocks the settle flag. It runs the
# same restore script (in whatever session is active now, which is the
# arrival-last cue) and locks the flag again, so the cue is one-shot and cannot
# loop. The 100 ms timer only re-arms the condition.
SETTLE_TRIGGER = """    <ModOp Type="addNextSibling" GUID="130248">
        <Asset>
            <Template>Trigger</Template>
            <Values>
                <Standard>
                    <GUID>{guid}</GUID>
                    <Name>{name}</Name>
                </Standard>
                <Trigger>
                    <TriggerCondition>
                        <Template>ConditionUnlocked</Template>
                        <Values>
                            <Condition />
                            <ConditionUnlocked>
                                <UnlockNeeded>{flag}</UnlockNeeded>
                            </ConditionUnlocked>
                        </Values>
                    </TriggerCondition>
                    <TriggerActions>
                        <Item>
                            <TriggerAction>
                                <Template>ActionExecuteScript</Template>
                                <Values>
                                    <Action />
                                    <ActionExecuteScript>
                                        <ScriptFileName>data/script/{script}</ScriptFileName>
                                    </ActionExecuteScript>
                                </Values>
                            </TriggerAction>
                        </Item>
                        <Item>
                            <TriggerAction>
                                <Template>ActionLockAsset</Template>
                                <Values>
                                    <Action />
                                    <ActionLockAsset>
                                        <LockAssets>
                                            <Item>
                                                <Asset>{flag}</Asset>
                                            </Item>
                                        </LockAssets>
                                    </ActionLockAsset>
                                </Values>
                            </TriggerAction>
                        </Item>
                    </TriggerActions>{subs}
                    <ResetTrigger>
                        <Template>AutoCreateTrigger</Template>
                        <Values>
                            <Trigger>
                                <TriggerCondition>
                                    <Template>ConditionTimer</Template>
                                    <Values>
                                        <Condition />
                                        <ConditionTimer>
                                            <TimeLimit>100</TimeLimit>
                                        </ConditionTimer>
                                    </Values>
                                </TriggerCondition>
                            </Trigger>
                        </Values>
                    </ResetTrigger>
                </Trigger>
                <TriggerSetup>
                    <AutoRegisterTrigger>1</AutoRegisterTrigger>
                </TriggerSetup>
            </Values>
        </Asset>
    </ModOp>
"""

SUB_WRAP_OPEN = """
                    <SubTriggers>"""
SUB_WRAP_CLOSE = """
                    </SubTriggers>"""

SUB_CREATIVE_ITEM = """
                        <Item>
                            <SubTrigger>
                                <Template>AutoCreateTrigger</Template>
                                <Values>
                                    <Trigger>
                                        <TriggerCondition>
                                            <Template>ConditionIsCreativeMode</Template>
                                            <Values>
                                                <ConditionPropsNegatable />
                                                <Condition />
                                                <ConditionIsCreativeMode />
                                            </Values>
                                        </TriggerCondition>
                                    </Trigger>
                                </Values>
                            </SubTrigger>
                        </Item>"""

SUB_NOT_CREATIVE_ITEM = """
                        <Item>
                            <SubTrigger>
                                <Template>AutoCreateTrigger</Template>
                                <Values>
                                    <Trigger>
                                        <TriggerCondition>
                                            <Template>ConditionIsCreativeMode</Template>
                                            <Values>
                                                <ConditionPropsNegatable>
                                                    <NegateCondition>1</NegateCondition>
                                                </ConditionPropsNegatable>
                                                <Condition />
                                                <ConditionIsCreativeMode />
                                            </Values>
                                        </TriggerCondition>
                                    </Trigger>
                                </Values>
                            </SubTrigger>
                        </Item>"""

# "The active session is NOT the hide session", with the vanilla SessionBlacklist
# flag. The same condition the generic restore triggers use. A SubTrigger is an
# additional condition on the parent trigger, so a settle trigger carrying this
# can never run its script inside the hidden session.
SUB_NOT_HIDE_SESSION_ITEM = """
                        <Item>
                            <SubTrigger>
                                <Template>AutoCreateTrigger</Template>
                                <Values>
                                    <Trigger>
                                        <TriggerCondition>
                                            <Template>ConditionActiveSession</Template>
                                            <Values>
                                                <Condition />
                                                <ConditionActiveSession>
                                                    <ActiveSession>__HIDE__</ActiveSession>
                                                    <SessionBlacklist>1</SessionBlacklist>
                                                </ConditionActiveSession>
                                            </Values>
                                        </TriggerCondition>
                                    </Trigger>
                                </Values>
                            </SubTrigger>
                        </Item>"""

SUB_CREATIVE = SUB_WRAP_OPEN + SUB_CREATIVE_ITEM + SUB_WRAP_CLOSE
SUB_NOT_CREATIVE = SUB_WRAP_OPEN + SUB_NOT_CREATIVE_ITEM + SUB_WRAP_CLOSE


def settle_subs(creative: bool, hide_session: str) -> str:
    """Settle subtriggers: mode gate plus 'not in the hide session'."""
    mode = SUB_CREATIVE_ITEM if creative else SUB_NOT_CREATIVE_ITEM
    not_hide = SUB_NOT_HIDE_SESSION_ITEM.replace("__HIDE__", str(hide_session))
    return SUB_WRAP_OPEN + mode + not_hide + SUB_WRAP_CLOSE


def item_guids_from_file(path: Path, include: list[str]) -> list[str]:
    data = read_item_file(path)
    items: list[object] = []
    for key in include:
        if key == "tabs":
            for tab in data.get("tabs", []):
                items.append(tab.get("guid"))
        else:
            items.extend(data.get(key, []))
    return guid_list(items, f"item GUID in {path}")


def collect_module_items(module: dict, config_dir: Path, preset: dict, compat: dict | None) -> list[str]:
    items: list[object] = []
    items_file = module.get("items_file")
    if items_file:
        path = Path(items_file)
        if not path.is_absolute():
            path = config_dir / path
        if not path.exists():
            raise ToolError(f"items file not found: {path}")
        items.extend(item_guids_from_file(path, module.get("include", DEFAULT_INCLUDE)))
    items.extend(module.get("items", []))
    if module.get("key") == "compat" and compat is not None:
        for entry in compat.get("items", []):
            items.append(entry.get("guid") if isinstance(entry, dict) else entry)

    keep = set(guid_list(module.get("keep_unlocked", preset_street_guids(preset)), "keep_unlocked"))
    exclude = set(guid_list(module.get("exclude", []), "exclude"))
    seen: set[str] = set()
    result: list[str] = []
    for value in items:
        guid = as_guid(value)
        if guid in keep or guid in exclude or guid in seen:
            continue
        seen.add(guid)
        result.append(guid)
    # Preserve the item-file order: leaves, then nested submenus, then the tab
    # categories, exactly as the extractor and the private engine order them.
    return result


def lua_values(values: list[str], per_line: int = 12) -> str:
    lines = []
    for start in range(0, len(values), per_line):
        lines.append("    " + ", ".join(values[start : start + per_line]))
    return ",\n".join(lines)


def unique_guids(values: object, label: str) -> list[str]:
    """GUIDs in input order, without duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for guid in guid_list(values, label):
        if guid not in seen:
            seen.add(guid)
            result.append(guid)
    return result


def resolve_show_sessions(config: dict, hide: dict) -> list[dict]:
    hide_guid = as_guid(hide["guid"], "hide session GUID")
    raw = config.get("show_sessions")
    if raw is None:
        sessions = [s for s in load_sessions() if as_guid(s["guid"]) != hide_guid]
    else:
        sessions = raw
    result: list[dict] = []
    seen: set[str] = set()
    for session in sessions:
        guid = as_guid(session["guid"], "show session GUID")
        if guid == hide_guid:
            raise ToolError("hide_session must not appear in show_sessions")
        if guid in seen:
            continue
        seen.add(guid)
        result.append({"guid": guid, "name": session.get("name", guid)})
    if not result:
        raise ToolError("no show sessions: the menu would never be restored")
    return result


def resolve_known_sessions(config: dict, hide: dict) -> list[dict]:
    """Display names for the runtime log. This never creates a trigger.

    The map only changes the text of a log line and the optional region label.
    `known_sessions` may name modded sessions the preset list does not contain;
    omitting it uses the vanilla session list plus the hide session.
    """
    raw = config.get("known_sessions")
    if raw is None:
        entries: list[object] = [{"guid": s["guid"], "name": s["name"]} for s in load_sessions()]
        entries.append({"guid": hide["guid"], "name": hide.get("name", hide["guid"])})
    elif isinstance(raw, list):
        entries = raw
    else:
        raise ToolError("known_sessions must be a list of {guid, name} objects")

    by_guid: dict[str, dict] = {}
    order: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or "guid" not in entry:
            raise ToolError("known_sessions entries need a guid and a name")
        guid = as_guid(entry["guid"], "known session GUID")
        record = {"guid": int(guid), "name": str(entry.get("name", guid))}
        if entry.get("region") is not None:
            record["region"] = int(entry["region"])
            record["region_name"] = str(entry.get("region_name", ""))
        if guid not in by_guid:
            order.append(guid)
        # A later entry for the same GUID wins, so the hide session's name is
        # used when it also appears in the vanilla list.
        by_guid[guid] = record
    return [by_guid[guid] for guid in order]


def write_all(outputs: dict[Path, str]) -> None:
    """Write every output to `<path>.tmp`, then rename them all into place.

    Nothing is replaced until every output has been generated, so an
    interrupted run cannot pair new scripts with the old XML, and a failure
    while staging leaves the previous output untouched.
    """
    staged: list[tuple[Path, Path]] = []
    try:
        for path, text in outputs.items():
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            staged.append((tmp, path))
        for tmp, path in staged:
            tmp.replace(path)
    finally:
        for tmp, _ in staged:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass


def validate_config(config: dict) -> None:
    for field in ("mod_id", "mod_name", "hide_session", "script_prefix", "modules"):
        if field not in config:
            raise ToolError(f"config is missing: {field}")
    for field in (
        "session_enter_delay_ms",
        "marker_max_age_seconds",
        "log_rotate_bytes",
        "log_dedupe_seconds",
    ):
        if field in config:
            try:
                value = int(config[field])
            except (TypeError, ValueError):
                raise ToolError(f"{field} must be a number")
            if field == "marker_max_age_seconds" and value <= 0:
                raise ToolError(
                    "marker_max_age_seconds must be positive: an unexpiring "
                    "marker would latch a restore off after one failed removal."
                )
            if value < 0:
                raise ToolError(f"{field} must not be negative")
            config[field] = value
    if not isinstance(config["hide_session"], dict) or "guid" not in config["hide_session"]:
        raise ToolError("hide_session must be an object with a guid")
    if "known_sessions" in config and not isinstance(config["known_sessions"], list):
        raise ToolError("known_sessions must be a list")
    if "trigger_guid_base" not in config or config["trigger_guid_base"] in (None, "", 0, "0"):
        raise ToolError(
            "trigger_guid_base is empty. Choose the first free GUID in your own "
            "range and put it in the config, or pass --guid-base."
        )
    try:
        base = int(config["trigger_guid_base"])
    except (TypeError, ValueError):
        raise ToolError("trigger_guid_base must be a number")
    if not 0 < base <= 2147483647:
        raise ToolError("trigger_guid_base must be between 1 and 2147483647")
    config["trigger_guid_base"] = base
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(config.get("version", "0.1.0"))):
        warn("version is best written as three numbers, for example 1.0.0")
    if config.get("schema_version", 1) != 1:
        raise ToolError("this version of generate.py understands config schema_version 1")
    if any(character.isspace() for character in str(config["mod_id"])):
        warn("mod_id contains whitespace; the loader works best with a simple ID")
    if not str(config["script_prefix"]).replace("_", "").isalnum():
        warn("script_prefix is best kept to letters, numbers and underscores")
    if not config["modules"]:
        raise ToolError("config has no modules")
    if int(config["trigger_guid_base"]) in (900000100, 900000500):
        warn(
            "trigger_guid_base is the example placeholder; choose a free band "
            "in your own GUID range before publishing"
        )


SLOT_NAMES = (
    "hide",
    "generic_restore",
    "generic_restore_creative",
    "settle_flag",
    "settle_restore",
    "settle_restore_creative",
)


def build(config: dict, config_path: Path, out_dir: Path, preset: dict, preset_path: Path, compat: dict | None, dry_run: bool) -> dict:
    validate_config(config)
    hide = config["hide_session"]
    hide_guid = as_guid(hide["guid"], "hide session GUID")
    hide_name = hide.get("name", hide_guid)
    shows = resolve_show_sessions(config, hide)
    named = [as_guid(session["guid"]) for session in shows]
    script_prefix = config["script_prefix"]
    marker_dir = config.get("marker_dir", "logs")
    creative_enabled = bool(config.get("creative_restore", True))
    triggers_enabled = bool(config.get("generate_triggers", True))
    streets_config = config.get("streets_unified", {})
    streets_required = bool(streets_config.get("required", True))
    delay = int(config.get("session_enter_delay_ms", 500))
    marker_age = int(config.get("marker_max_age_seconds", 21600))

    # Runtime log settings. The log lives beside the marker: both are relative
    # to the game's working directory.
    log_file = config.get("log_file", f"{marker_dir}/{script_prefix}.log")
    log_stem = log_file[:-4] if log_file.endswith(".log") else log_file
    log_backup = config.get("log_backup", log_stem + ".prev.log")
    log_cursor = config.get("log_cursor", log_stem + ".cursor")
    log_limit = int(config.get("log_rotate_bytes", 262144))
    log_window = int(config.get("log_dedupe_seconds", 60))
    known = resolve_known_sessions(config, hide)

    modules: list[dict] = []
    seen_keys: set[str] = set()
    for source in config["modules"]:
        if not source.get("enabled", True):
            continue
        module = dict(source)
        key = module["key"]
        if key in seen_keys:
            raise ToolError(f"duplicate module key {key!r}: script and marker names would collide")
        seen_keys.add(key)
        if key == "compat" and compat is not None:
            module["items"] = module.get("items", [])
        items = collect_module_items(module, config_path.parent, preset, compat)
        if not items:
            warn(f"module {key} has no items and was skipped")
            continue
        modules.append(
            {
                "key": key,
                "name": module.get("name", key),
                "items": items,
                "keep_unlocked": unique_guids(
                    module.get("keep_unlocked", preset_street_guids(preset)), "keep_unlocked"
                ),
                "creative": bool(module.get("creative_restore", creative_enabled)),
                "guid_base": module.get("guid_base"),
                "guids": module.get("guids", {}),
            }
        )
    if not modules:
        raise ToolError("no module produced any items; nothing to generate")

    # GUID allocation is checked before a byte is written. Every allocated GUID
    # must be unique across modules and pinned `guids` values; a module may pin
    # its sequential base with `guid_base` so disabling an earlier module does
    # not renumber it. Without a `guid_base` it continues from the previous
    # module's cursor.
    all_item_guids = {guid for module in modules for guid in module["items"]}
    owners: dict[int, str] = {}

    def claim(guid: int, owner: str) -> str:
        if guid in owners:
            raise ToolError(
                f"GUID collision: {guid} is allocated for both {owners[guid]} and "
                f"{owner}. Fix the `guid_base`/`guids` values. Nothing was written."
            )
        if str(guid) in all_item_guids:
            raise ToolError(
                f"trigger GUID {guid} is also an item GUID; move trigger_guid_base"
            )
        owners[guid] = owner
        return str(guid)

    cursor = int(config["trigger_guid_base"])
    for module in modules:
        explicit = module["guids"]
        if not isinstance(explicit, dict):
            raise ToolError(f"{module['key']}: guids must be an object")
        unknown = sorted(set(explicit) - set(SLOT_NAMES))
        if unknown:
            raise ToolError(
                f"{module['key']}: unknown `guids` slot(s) {unknown}; "
                f"known slots: {list(SLOT_NAMES)}"
            )
        if module["guid_base"] is not None:
            cursor = int(module["guid_base"])

        def take_guid(slot: str | None, label: str) -> str:
            nonlocal cursor
            if slot is not None and slot in explicit:
                guid = int(explicit[slot])
            else:
                guid = cursor
                cursor += 1
            return claim(guid, f"{module['key']}:{label}")

        module["hide_guid"] = take_guid("hide", "hide")
        module["show_guids"] = [take_guid(None, "show:" + s["name"]) for s in shows]
        module["creative_guids"] = (
            [take_guid(None, "creative_show:" + s["name"]) for s in shows]
            if module["creative"]
            else []
        )
        module["generic_guid"] = take_guid("generic_restore", "generic_restore")
        module["generic_creative_guid"] = (
            take_guid("generic_restore_creative", "generic_restore_creative")
            if module["creative"]
            else None
        )
        module["settle_flag_guid"] = take_guid("settle_flag", "settle_flag")
        module["settle_guid"] = take_guid("settle_restore", "settle_restore")
        module["settle_creative_guid"] = (
            take_guid("settle_restore_creative", "settle_restore_creative")
            if module["creative"]
            else None
        )
        module["trigger_guids"] = [module["hide_guid"]] + module["show_guids"] + module["creative_guids"]
        module["trigger_guids"] += [module["generic_guid"], module["settle_flag_guid"], module["settle_guid"]]
        if module["generic_creative_guid"]:
            module["trigger_guids"].append(module["generic_creative_guid"])
        if module["settle_creative_guid"]:
            module["trigger_guids"].append(module["settle_creative_guid"])
        module["trigger_count"] = len(module["trigger_guids"])

    if cursor - 1 > 2147483647:
        raise ToolError("the trigger GUID range exceeds the int32 limit; move trigger_guid_base lower")
    trigger_guid_end = str(max(owners)) if owners else str(int(config["trigger_guid_base"]) - 1)

    if dry_run:
        return {
            "out_dir": out_dir,
            "modules": modules,
            "shows": shows,
            "trigger_guid_end": trigger_guid_end,
            "triggers_enabled": triggers_enabled,
        }

    outputs: dict[Path, str] = {}

    def emit(relative: Path, text: str) -> None:
        path = out_dir / relative
        if path in outputs:
            raise ToolError(f"two outputs would write {path}; check the module keys")
        outputs[path] = text

    trigger_parts: list[str] = []
    trigger_records: list[dict] = []

    def record(
        kind: str,
        guid: str,
        name: str,
        script: str | None,
        session: str | None,
        session_name: str,
        creative: bool,
    ) -> None:
        trigger_records.append(
            {
                "kind": kind,
                "guid": guid,
                "name": name,
                "script": script,
                "session": session,
                "session_name": session_name,
                "creative": creative,
            }
        )

    for module in modules:
        key = module["key"]
        name = module["name"]
        items_lua = lua_values(module["items"])
        always_lua = lua_values(module["keep_unlocked"])
        marker = f"{marker_dir}/{script_prefix}_{key}.restore"
        marker_creative = f"{marker_dir}/{script_prefix}_{key}.restore_creative"
        hide_script = f"{script_prefix}_{key}_hide.lua"
        show_script = f"{script_prefix}_{key}_show.lua"
        creative_script = f"{script_prefix}_{key}_creative.lua"

        # With no creative restore there is no way back from a creative hide, so
        # the hide itself is gated to non-creative.
        if not module["creative"]:
            warn(
                f"{key}: creative_restore=false — the hide trigger is gated to "
                f"non-creative, so a creative save cannot hide {name}. Enable "
                f"creative_restore if it should be hidden in creative."
            )
        hide_subs = "" if module["creative"] else SUB_NOT_CREATIVE

        base_context = {
            "toolkit_version": __version__,
            "module_name": name,
            "count": str(len(module["items"])),
            "session_name": hide_name,
            "session_guid": hide_guid,
            "items": items_lua,
            "always": always_lua,
            "marker": marker,
            "marker_creative": marker_creative,
        }

        hide_context = dict(base_context)
        hide_context["log"] = render_log(
            f"{script_prefix}_{key}_hide", [], known, log_file, log_backup,
            log_cursor, log_limit, log_window, marker_age,
        )
        emit(Path("data/script") / hide_script, HIDE_LUA.format(**hide_context))

        show_context = dict(base_context)
        show_context["log"] = render_log(
            f"{script_prefix}_{key}_show", named, known, log_file, log_backup,
            log_cursor, log_limit, log_window, marker_age,
        )
        emit(Path("data/script") / show_script, SHOW_LUA.format(**show_context))

        if module["creative"]:
            creative_context = dict(base_context)
            creative_context["log"] = render_log(
                f"{script_prefix}_{key}_creative", named, known, log_file, log_backup,
                log_cursor, log_limit, log_window, marker_age,
            )
            emit(Path("data/script") / creative_script, CREATIVE_LUA.format(**creative_context))

        hide_trigger_name = f"Hide {name} in {hide_name}"
        trigger_parts.append(
            HIDE_TRIGGER.format(
                guid=module["hide_guid"],
                name=hide_trigger_name,
                session=hide_guid,
                script=hide_script,
                subs=hide_subs,
            )
        )
        record("hide", module["hide_guid"], hide_trigger_name, hide_script, hide_guid, hide_name, False)

        for session, guid in zip(shows, module["show_guids"]):
            trigger_name = f"Restore {name} in {session['name']}"
            trigger_parts.append(
                HIDE_TRIGGER.format(
                    guid=guid,
                    name=trigger_name,
                    session=as_guid(session["guid"]),
                    script=show_script,
                    subs=SUB_NOT_CREATIVE,
                )
            )
            record("show", guid, trigger_name, show_script, as_guid(session["guid"]), session["name"], False)

        if module["creative"]:
            for session, guid in zip(shows, module["creative_guids"]):
                trigger_name = f"Restore {name} in creative ({session['name']})"
                trigger_parts.append(
                    HIDE_TRIGGER.format(
                        guid=guid,
                        name=trigger_name,
                        session=as_guid(session["guid"]),
                        script=creative_script,
                        subs=SUB_CREATIVE,
                    )
                )
                record(
                    "creative", guid, trigger_name, creative_script,
                    as_guid(session["guid"]), session["name"], True,
                )

        flag_name = f"{name} settle flag"
        trigger_parts.append(
            FLAG_ASSET.format(guid=module["settle_flag_guid"], name=flag_name)
        )
        record("settle_flag", module["settle_flag_guid"], flag_name, None, None, "", False)

        generic_name = f"Restore {name} in any other session"
        trigger_parts.append(
            GENERIC_TRIGGER.format(
                guid=module["generic_guid"],
                name=generic_name,
                hide_session=hide_guid,
                script=show_script,
                settle_flag=module["settle_flag_guid"],
                delay=delay,
                subs=SUB_NOT_CREATIVE,
            )
        )
        record("generic", module["generic_guid"], generic_name, show_script, hide_guid, hide_name, False)

        if module["creative"]:
            generic_creative_name = f"Restore {name} in any other session (creative)"
            trigger_parts.append(
                GENERIC_TRIGGER.format(
                    guid=module["generic_creative_guid"],
                    name=generic_creative_name,
                    hide_session=hide_guid,
                    script=creative_script,
                    settle_flag=module["settle_flag_guid"],
                    delay=delay,
                    subs=SUB_CREATIVE,
                )
            )
            record(
                "generic_creative", module["generic_creative_guid"],
                generic_creative_name, creative_script, hide_guid, hide_name, True,
            )

        settle_name = f"Settle {name} after the arrival delay"
        trigger_parts.append(
            SETTLE_TRIGGER.format(
                guid=module["settle_guid"],
                name=settle_name,
                flag=module["settle_flag_guid"],
                script=show_script,
                subs=settle_subs(False, hide_guid),
            )
        )
        record("settle", module["settle_guid"], settle_name, show_script, hide_guid, hide_name, False)

        if module["creative"]:
            settle_creative_name = f"Settle {name} after the arrival delay (creative)"
            trigger_parts.append(
                SETTLE_TRIGGER.format(
                    guid=module["settle_creative_guid"],
                    name=settle_creative_name,
                    flag=module["settle_flag_guid"],
                    script=creative_script,
                    subs=settle_subs(True, hide_guid),
                )
            )
            record(
                "settle_creative", module["settle_creative_guid"],
                settle_creative_name, creative_script, hide_guid, hide_name, True,
            )

    dependencies = ["Streets_Unified"] if streets_required else []
    dependencies.extend(config.get("dependencies", []))
    dependencies = list(dict.fromkeys(dependencies))
    load_after = list(dict.fromkeys(dependencies + list(config.get("load_after", []))))
    modinfo = {
        "Version": str(config.get("version", "0.1.0")),
        "ModID": config["mod_id"],
        "Category": localized(config.get("category", "Gameplay")),
        "ModName": localized(config["mod_name"]),
        "Description": localized(config.get("description", "")),
        "KnownIssues": config.get("known_issues", []),
        "CreatorName": config.get("creator", ""),
    }
    if dependencies:
        modinfo["ModDependencies"] = dependencies
    if load_after:
        modinfo["LoadAfterIds"] = load_after
    outputs[out_dir / "modinfo.json"] = json.dumps(modinfo, indent=2, ensure_ascii=False) + "\n"

    assets_header = (
        "<ModOps>\n"
        f"    <!-- Generated by {TOOLKIT_NAME} {__version__}. Do not edit by hand. -->\n"
        f"    <!-- Region: {preset['display_name']} ({preset['region_node']}). "
        f"Hide session: {hide_name} ({hide_guid}). -->\n"
    )
    assets_path = out_dir / "data/config/export/main/asset/assets.xml"
    manifest_json = out_dir / "menugate.triggers.json"
    manifest_text = out_dir / "menugate.triggers.xml.txt"
    if triggers_enabled:
        outputs[assets_path] = assets_header + "".join(trigger_parts) + "</ModOps>\n"
    else:
        outputs[manifest_json] = (
            json.dumps(
                {
                    "schema_version": 1,
                    "generated_by": f"{TOOLKIT_NAME} {__version__}",
                    "region": preset["key"],
                    "region_node": preset["region_node"],
                    "note": (
                        "Triggers were skipped. Add these to your own assets.xml, or copy "
                        "the snippet in menugate.triggers.xml.txt."
                    ),
                    "triggers": trigger_records,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        manual_header = (
            "<ModOps>\n"
            f"    <!-- Generated by {TOOLKIT_NAME} {__version__}. Triggers were skipped. -->\n"
            f"    <!-- Region: {preset['display_name']} ({preset['region_node']}). "
            f"Hide session: {hide_name} ({hide_guid}). -->\n"
        )
        outputs[manifest_text] = manual_header + "".join(trigger_parts) + "</ModOps>\n"

    provenance = {
        "schema_version": 1,
        "toolkit": TOOLKIT_NAME,
        "toolkit_version": __version__,
        "region": preset["key"],
        "region_node": preset["region_node"],
        "preset": preset_path.name,
        "hide_session": {"guid": hide_guid, "name": hide.get("name", "")},
        "show_sessions": shows,
        "streets_unified_required": streets_required,
        "triggers_generated": triggers_enabled,
        "trigger_count": len(trigger_records),
        "trigger_records": trigger_records,
        "modules": [
            {
                "key": module["key"],
                "name": module["name"],
                "items": len(module["items"]),
                "hide_trigger": module["hide_guid"],
                "show_triggers": module["show_guids"],
                "creative_triggers": module["creative_guids"],
                "generic_trigger": module["generic_guid"],
                "generic_creative_trigger": module["generic_creative_guid"],
                "settle_flag": module["settle_flag_guid"],
                "settle_trigger": module["settle_guid"],
                "settle_creative_trigger": module["settle_creative_guid"],
                "trigger_count": module["trigger_count"],
            }
            for module in modules
        ],
        "trigger_guid_end": trigger_guid_end,
        "config": config,
    }
    canonical = json.dumps(provenance, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    provenance["config_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    outputs[out_dir / "menugate.config.json"] = json.dumps(provenance, indent=2, ensure_ascii=False) + "\n"

    # Every output is fully generated before the first rename.
    write_all(outputs)

    # Remove the alternative mode's stale files only after the new outputs are
    # in place, so an interrupted run never leaves a half-written folder.
    stale = (manifest_json, manifest_text) if triggers_enabled else (assets_path,)
    for path in stale:
        if path.exists():
            path.unlink()

    return {
        "out_dir": out_dir,
        "modules": modules,
        "shows": shows,
        "trigger_guid_end": trigger_guid_end,
        "triggers_enabled": triggers_enabled,
    }


def load_compat(path: Path | None) -> dict | None:
    if path is None:
        return None
    data = read_json(path)
    if not isinstance(data, dict):
        raise ToolError(f"compat file is not an object: {path}")
    if not isinstance(data.get("items", []), list):
        raise ToolError(f"compat file has no items list: {path}")
    return data


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, help="Path to the gate config JSON")
    parser.add_argument("--preset", help="Region preset key or path (default: the config's region)")
    parser.add_argument("--compat", help="Compatibility list from scan_mods.py")
    parser.add_argument("--guid-base", help="First trigger GUID, overriding the config value")
    parser.add_argument(
        "--skip-triggers",
        action="store_true",
        help="Write the Lua and modinfo but not the trigger XML; write a manifest instead",
    )
    parser.add_argument("--out", help="Output folder (default: the config's output, or out/<mod_id>)")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config).resolve()
    try:
        config = read_json(config_path)
        if not isinstance(config, dict):
            raise ToolError(f"config is not an object: {config_path}")
        if args.guid_base is not None:
            config["trigger_guid_base"] = args.guid_base
        if args.skip_triggers:
            config["generate_triggers"] = False
        preset_name = args.preset or config.get("region")
        if not preset_name:
            raise ToolError("config has no region and --preset was not given")
        preset, preset_path = load_preset(preset_name)
        compat = load_compat(Path(args.compat) if args.compat else None)
        if compat is not None and not any(module.get("key") == "compat" for module in config.get("modules", [])):
            config.setdefault("modules", []).append(
                {
                    "key": "compat",
                    "name": "Installed mods",
                    "enabled": True,
                    "items": [],
                }
            )
        out_dir = Path(args.out) if args.out else config_path.parent / config.get("output", f"out/{config['mod_id']}")
        result = build(config, config_path, out_dir.resolve(), preset, preset_path, compat, args.dry_run)
    except FileNotFoundError as error:
        fail(f"file not found: {error.filename}")
    except ToolError as error:
        fail(str(error))

    info(f"region: {preset['display_name']} ({preset['region_node']})")
    for module in result["modules"]:
        info(
            f"  {module['key']}: {len(module['items'])} items, "
            f"hide {module['hide_guid']}, "
            f"{len(module['show_guids'])} restore triggers"
            + (f", {len(module['creative_guids'])} creative triggers" if module["creative"] else "")
            + f", generic {module['generic_guid']}, settle {module['settle_guid']}"
            + (f"/{module['settle_creative_guid']}" if module["creative"] else "")
        )
    info(f"trigger GUIDs allocated: {sum(m['trigger_count'] for m in result['modules'])}")
    info(f"trigger GUIDs end at {result['trigger_guid_end']}")
    if result.get("triggers_enabled", True):
        info("triggers: written to assets.xml")
    else:
        info("triggers: skipped; see menugate.triggers.json and menugate.triggers.xml.txt")
    if args.dry_run:
        info(f"dry run: would write {result['out_dir']}")
    else:
        info(f"wrote {result['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
