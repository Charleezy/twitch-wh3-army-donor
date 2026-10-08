# Donation Army Spawn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Streamlabs donation makes the streamer's Total War: Warhammer 3 campaign warn on screen and then spawn a hostile army, named after the donor, at the start of the player's next turn.

**Architecture:** A small Node CLI (`app/`) listens to the Streamlabs Socket API and appends `id<TAB>donor<TAB>amount_usd` lines to a queue file in the game folder. A campaign Lua mod (`mod/`) polls that file on a real-time timer to show a warning, and at `ScriptEventPlayerFactionTurnStart` spawns one army per unhandled entry. Handled IDs live in the save via `cm:set_saved_value`. Tiers exist only in the mod's Lua config.

**Tech Stack:** Node 24 (ESM, `node:test`, `socket.io-client@2`), WH3 campaign Lua, Python pytest + `lupa` (LuaJIT) for Lua unit tests, `rpfm_cli` for packing.

**Spec:** `docs/superpowers/specs/2026-10-08-donation-army-spawn-design.md`

## Global Constraints

- Hostile armies only; no friendly armies, no viewer-count buff, no Twitch Extension (out of scope for v1).
- No cap: every queued donation that meets the lowest tier spawns at the next player turn start.
- Spawn anchor order: faction leader (not wounded) → strongest army (most units, tie-break general rank, garrisons excluded) → capital → otherwise leave queued and retry next turn.
- Spawn at the player's next turn start; warning as soon as the donation is seen.
- Queue line format (exact): `id\tdonor\tamount_usd\n`, amount with 2 decimals, donor stripped of tabs/newlines and cut to 40 chars, empty donor → `Anonymous`.
- Queue file name: `donation_army_queue.txt`, in the WH3 install folder (where `Warhammer3.exe` is; `io.open` relative paths resolve there).
- Never print or log the Streamlabs socket token. It lives only in `app/config.local.json` (gitignored via `*.local.json`).
- Lua style: tabs, globals as tables (`donation_army`, `donation_army_queue`, `donation_army_spawn`, `donation_army_config`), log prefix `[DonationArmy]` via `out()`.
- Reuse patterns from `C:\dev\gaming\wh3-ultimate-endgame-mod` (its `build.ps1`, `tests/conftest.py`, `tests/lua/stubs.lua`).

## File Structure

```
mod/script/campaign/mod/
  donation_army_config.lua   -- tiers, queue file name, poll interval, spawn distance (user-editable)
  donation_army_queue.lua    -- parse/read the queue file
  donation_army_spawn.lua    -- tier pick, spawn anchors, find position, create force, post-spawn
  donation_army.lua          -- saved state, warning poll, turn-start spawning, install
tests/
  conftest.py                -- lupa Game fixture
  lua/stubs.lua              -- fake cm/core/world
  test_queue.py, test_spawn.py, test_main.py
tools/console/smoke.lua      -- in-game smoke test run via PJ's Console `e`
app/
  package.json, config.example.json
  src/currency.js, src/donation.js, src/queue.js, src/index.js, src/fake.js
  test/*.test.js
build.ps1, requirements-dev.txt, README.md
```

---

### Task 1: In-game smoke test of the unknowns

Proves the engine calls the mod relies on before building on them. **Needs the user to run it in-game.** Results decide the `spawn_distance` default and whether the warning dialog approach works.

**Files:**
- Create: `tools/console/smoke.lua`

**Interfaces:**
- Produces: `donation_army_smoke.txt` in the game folder with one `ok`/`ERROR` line per step.

- [ ] **Step 1: Write the smoke script**

```lua
-- Run with PJ's Console: copy to the WH3 game folder as exec.lua, type `e`.
-- Writes donation_army_smoke.txt next to Warhammer3.exe.
local LOG = "donation_army_smoke.txt"
io.open(LOG, "w"):close()
local function w(msg)
	local f = io.open(LOG, "a")
	f:write(tostring(msg) .. "\n")
	f:close()
end
local function step(name, fn)
	local ok, err = pcall(fn)
	w(name .. ": " .. (ok and "ok" or ("ERROR " .. tostring(err))))
end

local REBELS = "wh_main_chs_chaos_rebels"
local player = cm:get_faction(cm:get_local_faction_name(true))
local leader = player:faction_leader()
local x, y

step("file roundtrip", function()
	local q = assert(io.open("donation_army_smoke_queue.txt", "w"))
	q:write("smoke-1\tSmoke Donor\t20.00\n")
	q:close()
	local r = assert(io.open("donation_army_smoke_queue.txt", "r"))
	w("  read back: " .. r:read("*a"))
	r:close()
end)

step("spawn location", function()
	w("  leader at " .. leader:logical_position_x() .. "," .. leader:logical_position_y()
		.. " wounded=" .. tostring(leader:is_wounded()))
	for _, distance in ipairs({ 1, 5, 10 }) do
		local sx, sy = cm:find_valid_spawn_location_for_character_from_character(REBELS, cm:char_lookup_str(leader), true, distance)
		w("  distance " .. distance .. " -> " .. tostring(sx) .. "," .. tostring(sy))
		if distance == 5 then
			x, y = sx, sy
		end
	end
end)

step("spawn + rename + xp", function()
	local region_key = cm:model():world():region_manager():region_list():item_at(0):name()
	cm:create_force_with_general(REBELS, "wh_main_chs_inf_chaos_marauders_0,wh_main_chs_inf_chaos_marauders_0",
		region_key, x, y, "general", "wh_main_chs_lord", "", "", "", "", false,
		function(cqi)
			local ok, err = pcall(function()
				w("  callback arg: " .. type(cqi) .. " " .. tostring(cqi))
				cm:change_character_custom_name(cm:get_character_by_cqi(cqi), "Smoke Donor", "", "", "")
				cm:add_experience_to_units_commanded_by_character(cm:char_lookup_str(cqi), 2)
				w("  callback: renamed + xp applied")
			end)
			if not ok then
				w("  callback ERROR " .. tostring(err))
			end
		end)
end)

step("warning dialog", function()
	local box = core:get_or_create_component("donation_army_smoke_box", "ui/common ui/dialogue_box")
	box:SetVisible(true)
	local text = find_uicomponent(box, "DY_text")
	w("  DY_text found: " .. tostring(text and true or false))
	text:SetStateText("Smoke Donor ($20.00) has summoned a Warband! It arrives next turn.")
	core:add_listener("donation_army_smoke_box_close", "ComponentLClickUp",
		function(context) return context.string == "button_tick" or context.string == "button_cancel" end,
		function() box:Destroy() end, false)
end)
```

- [ ] **Step 2: User runs it in-game**

Ask the user to: load any campaign save, copy `tools/console/smoke.lua` to `C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\exec.lua`, type `e` in PJ's Console, click the dialog's tick, then paste the contents of `donation_army_smoke.txt` and say what they saw (army next to the leader? general named "Smoke Donor"? dialog text right? dialog closed?).

Expected: every step `ok`, `callback arg: number <cqi>`, coordinates ≥ 0 for all distances, a Chaos rebel army near the leader named "Smoke Donor".

- [ ] **Step 3: Record results and adjust**

- Pick `spawn_distance` for Task 5's config: the smallest distance whose coordinates were visibly not adjacent to the leader (default `5` if the user can't tell).
- If `warning dialog` failed or the dialog couldn't be closed, STOP and ask the user before Task 4. The fallback is logging only, plus `cm:show_message_event` with a static loc string, which means no donor name.
- If the callback arg was not a number, adjust `donation_army_spawn.on_spawned` in Task 3 to match.
- Append a "Smoke test results (date)" section to the spec with the raw findings.

- [ ] **Step 4: Commit**

```bash
git add tools/console/smoke.lua docs/superpowers/specs/2026-10-08-donation-army-spawn-design.md
git commit -m "test: in-game smoke script for spawn, rename, file IO and warning dialog"
```

---

### Task 2: Lua test harness + queue parser

**Files:**
- Create: `requirements-dev.txt`, `pytest.ini`, `tests/conftest.py`, `tests/lua/stubs.lua`, `tests/test_queue.py`
- Create: `mod/script/campaign/mod/donation_army_queue.lua`

**Interfaces:**
- Produces: `donation_army_queue.parse(text) -> { {id=string, donor=string, amount=number}, ... }`, `donation_army_queue.read(path) -> same` (missing file → `{}`).
- Produces (tests): `Game` fixture with `run`, `eval`, `log`, `errors`, `queue(*lines)`, `first_tick()`, `poll()`, `player_turn_start()`. Lua helpers `make_character`, `make_force`, `make_faction`, `fire_event`, `fake.*`.

- [ ] **Step 1: Test tooling**

`requirements-dev.txt`:
```
lupa>=2.8
pytest>=9
```
`pytest.ini`:
```ini
[pytest]
testpaths = tests
# LuaJIT unwinds Lua errors with a Windows SEH exception that faulthandler reports as fatal. Harmless.
addopts = -p no:faulthandler
```
Run: `python -m pip install -r requirements-dev.txt`

- [ ] **Step 2: Stubs**

`tests/lua/stubs.lua`:
```lua
-- Minimal stand-ins for the WH3 campaign scripting environment used by the mod.
test_log = {}
script_errors = {}
function out(msg) table.insert(test_log, msg) end
function script_error(msg) table.insert(script_errors, msg) end

fake = {
	saved = {},
	factions = {},
	characters = {},
	spawns = {},
	spawn_queries = {},
	renames = {},
	xp = {},
	wars = {},
	popups = {},
	first_tick = {},
	real_callbacks = {},
	valid_spawn = { x = 100, y = 200 }, -- set to false to make every spawn query fail
	local_faction = "player",
	next_cqi = 1000,
}
listeners = {}

function make_list(items)
	return {
		num_items = function() return #items end,
		item_at = function(_, i) return items[i + 1] end,
	}
end

-- opts: null, wounded, rank
function make_character(cqi, opts)
	opts = opts or {}
	local c = {}
	c.command_queue_index = function() return cqi end
	c.is_null_interface = function() return opts.null == true end
	c.is_wounded = function() return opts.wounded == true end
	c.rank = function() return opts.rank or 1 end
	fake.characters[cqi] = c
	return c
end

-- general: character or nil; opts: garrison
function make_force(general, num_units, opts)
	opts = opts or {}
	local units = {}
	for i = 1, num_units do units[i] = {} end
	return {
		has_general = function() return general ~= nil end,
		general_character = function() return general end,
		unit_list = function() return make_list(units) end,
		is_armed_citizenry = function() return opts.garrison == true end,
	}
end

-- opts: leader (character), forces (list of make_force), capital (region key)
function make_faction(key, opts)
	opts = opts or {}
	local f = {}
	f.name = function() return key end
	f.is_null_interface = function() return false end
	f.faction_leader = function() return opts.leader or make_character(0, { null = true }) end
	f.military_force_list = function() return make_list(opts.forces or {}) end
	f.has_home_region = function() return opts.capital ~= nil end
	f.home_region = function() return { name = function() return opts.capital end } end
	f.at_war_with = function(_, other) return fake.wars[key .. "|" .. other:name()] == true or fake.wars[other:name() .. "|" .. key] == true end
	fake.factions[key] = f
	return f
end

local function spawn_query(from, distance)
	table.insert(fake.spawn_queries, { from = from, distance = distance })
	if fake.valid_spawn then
		return fake.valid_spawn.x, fake.valid_spawn.y
	end
	return -1, -1
end

cm = {}
function cm:get_saved_value(key) return fake.saved[key] end
function cm:set_saved_value(key, value) fake.saved[key] = value end
function cm:add_first_tick_callback(f) table.insert(fake.first_tick, f) end
function cm:repeat_real_callback(f, ms, name) fake.real_callbacks[name] = f end
function cm:get_local_faction_name() return fake.local_faction end
function cm:get_faction(key) return fake.factions[key] or false end
function cm:get_character_by_cqi(cqi) return fake.characters[cqi] or false end
function cm:char_lookup_str(c)
	if type(c) == "table" then c = c:command_queue_index() end
	return "character_cqi:" .. tostring(c)
end
function cm:find_valid_spawn_location_for_character_from_character(faction_key, lookup, b, distance)
	return spawn_query(lookup, distance)
end
function cm:find_valid_spawn_location_for_character_from_settlement(faction_key, region_key, b1, b2, distance)
	return spawn_query(region_key, distance)
end
function cm:model()
	local region = { name = function() return "first_region" end }
	local region_manager = { region_list = function() return make_list({ region }) end }
	local world = { region_manager = function() return region_manager end }
	return { world = function() return world end }
end
function cm:create_force_with_general(faction_key, units, region_key, x, y, agent_type, subtype, f, c, fam, o, leader, callback)
	fake.next_cqi = fake.next_cqi + 1
	local cqi = fake.next_cqi
	make_character(cqi)
	table.insert(fake.spawns, { faction = faction_key, units = units, x = x, y = y, subtype = subtype, cqi = cqi })
	callback(cqi)
end
function cm:change_character_custom_name(character, forename) fake.renames[character:command_queue_index()] = forename end
function cm:add_experience_to_units_commanded_by_character(lookup, ranks) fake.xp[lookup] = ranks end
function cm:force_declare_war(a, b) fake.wars[a .. "|" .. b] = true end

core = {}
function core:add_listener(name, event, condition, callback)
	listeners[event] = listeners[event] or {}
	table.insert(listeners[event], { condition = condition, callback = callback })
end

function fire_event(event, context)
	for _, listener in ipairs(listeners[event] or {}) do
		local condition = listener.condition
		if condition == true or (type(condition) == "function" and condition(context)) then
			listener.callback(context)
		end
	end
end
```

- [ ] **Step 3: Fixture**

`tests/conftest.py`:
```python
import pathlib

import pytest
from lupa.luajit21 import LuaRuntime

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD_DIR = ROOT / "mod/script/campaign/mod"
# load order matters only for the test runtime; the game loads all mod files before first tick
MOD_FILES = ["donation_army_config.lua", "donation_army_queue.lua", "donation_army_spawn.lua", "donation_army.lua"]
LUA_DIR = pathlib.Path(__file__).parent / "lua"


class Game:
    """LuaJIT runtime with game stubs and the mod files that exist so far."""

    def __init__(self, queue_path):
        self.queue_path = queue_path
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.run((LUA_DIR / "stubs.lua").read_text(encoding="utf-8"))
        for name in MOD_FILES:
            path = MOD_DIR / name
            if path.exists():
                self.run(path.read_text(encoding="utf-8"))
        config = self.lua.globals().donation_army_config
        if config is not None:
            config.queue_file = str(queue_path)
        if self.lua.globals().donation_army is not None:
            self.run("donation_army.show_warning = function(text) table.insert(fake.popups, text) end")

    def run(self, code):
        self.lua.execute(code)

    def eval(self, expr):
        return self.lua.eval(expr)

    def queue(self, *lines):
        with open(self.queue_path, "a", encoding="utf-8", newline="\n") as f:
            for line in lines:
                f.write(line + "\n")

    def first_tick(self):
        self.run("for _, f in ipairs(fake.first_tick) do f() end")

    def poll(self):
        self.run('fake.real_callbacks["donation_army_poll"]()')

    def player_turn_start(self):
        self.run('fire_event("ScriptEventPlayerFactionTurnStart", { faction = function() return fake.factions[fake.local_faction] end })')

    @property
    def log(self):
        return list(self.lua.globals().test_log.values())

    @property
    def errors(self):
        return list(self.lua.globals().script_errors.values())


@pytest.fixture
def game(tmp_path):
    return Game(tmp_path / "donation_army_queue.txt")
```

- [ ] **Step 4: Write the failing queue tests**

`tests/test_queue.py`:
```python
def test_parse_reads_tab_separated_lines(game):
    game.run('entries = donation_army_queue.parse("a1\\tBob\\t20.00\\nb2\\tAlice\\t5.50\\n")')
    assert game.eval("#entries") == 2
    assert game.eval("entries[1].id") == "a1"
    assert game.eval("entries[1].donor") == "Bob"
    assert game.eval("entries[1].amount") == 20.0
    assert game.eval("entries[2].amount") == 5.5


def test_parse_skips_malformed_lines_and_handles_crlf(game):
    game.run('entries = donation_army_queue.parse("junk\\r\\na1\\tBob\\tnot_a_number\\r\\nc3\\tCarl\\t7\\r\\n")')
    assert game.eval("#entries") == 1
    assert game.eval("entries[1].id") == "c3"


def test_read_missing_file_is_empty(game):
    assert game.eval('#donation_army_queue.read("does_not_exist_here.txt")') == 0


def test_read_file(game):
    game.queue("a1\tBob\t20.00")
    game.run(f'entries = donation_army_queue.read([[{game.queue_path}]])')
    assert game.eval("entries[1].donor") == "Bob"
```

- [ ] **Step 5: Run to verify failure**

Run: `python -m pytest tests/test_queue.py -v`
Expected: FAIL, `donation_army_queue` is nil.

- [ ] **Step 6: Implement**

`mod/script/campaign/mod/donation_army_queue.lua`:
```lua
-- Donation Army: reads the queue file written by the companion app.
-- One entry per line: id<TAB>donor<TAB>amount_usd

donation_army_queue = donation_army_queue or {}
local q = donation_army_queue

function q.parse(text)
	local entries = {}
	for line in (text or ""):gmatch("[^\r\n]+") do
		local id, donor, amount = line:match("^([^\t]+)\t([^\t]*)\t([^\t]+)$")
		amount = tonumber(amount)
		if id and amount then
			table.insert(entries, { id = id, donor = donor, amount = amount })
		end
	end
	return entries
end

function q.read(path)
	local file = io.open(path, "r")
	if not file then
		return {}
	end
	local text = file:read("*a")
	file:close()
	return q.parse(text)
end
```

- [ ] **Step 7: Run to verify pass**

Run: `python -m pytest tests/test_queue.py -v`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add requirements-dev.txt pytest.ini tests mod
git commit -m "feat: queue file parser with lupa test harness"
```

---

### Task 3: Tier pick + spawn module

**Files:**
- Create: `mod/script/campaign/mod/donation_army_spawn.lua`
- Test: `tests/test_spawn.py`

**Interfaces:**
- Consumes: `donation_army.log(msg)` at runtime (defined in Task 4; guarded so this module works without it).
- Produces:
  - `donation_army_spawn.pick_tier(tiers, amount) -> tier|nil`. A tier is `{name, min_usd, faction, subtype, units = {unit_key,...}, xp_ranks}`.
  - `donation_army_spawn.anchors(faction) -> { {character=c} | {region_key=k}, ... }`
  - `donation_army_spawn.find_position(faction, spawn_faction_key, distance) -> x, y | nil`
  - `donation_army_spawn.spawn(entry, tier, faction, distance) -> boolean` (true = entry is done: force requested, or creation errored and was logged; false = no valid position, retry later)

- [ ] **Step 1: Write the failing tests**

`tests/test_spawn.py`:
```python
TIERS = """
tiers = {
	{ name = "Warband", min_usd = 5, faction = "wh_main_chs_chaos_rebels", subtype = "wh_main_chs_lord", units = { "u1", "u2" }, xp_ranks = 0 },
	{ name = "Horde", min_usd = 20, faction = "invader", subtype = "wh_main_chs_lord", units = { "u3" }, xp_ranks = 3 },
}
"""


def test_pick_tier_highest_met(game):
    game.run(TIERS)
    assert game.eval("donation_army_spawn.pick_tier(tiers, 4.99)") is None
    assert game.eval("donation_army_spawn.pick_tier(tiers, 5).name") == "Warband"
    assert game.eval("donation_army_spawn.pick_tier(tiers, 19.99).name") == "Warband"
    assert game.eval("donation_army_spawn.pick_tier(tiers, 500).name") == "Horde"


def test_anchor_order_leader_then_strongest_then_capital(game):
    game.run("""
        leader = make_character(1)
        small = make_character(2, { rank = 9 })
        big = make_character(3)
        player = make_faction("player", {
            leader = leader,
            forces = { make_force(small, 5), make_force(big, 12), make_force(nil, 20, { garrison = true }) },
            capital = "capital_region",
        })
        a = donation_army_spawn.anchors(player)
    """)
    assert game.eval("#a") == 3
    assert game.eval("a[1].character == leader")
    assert game.eval("a[2].character == big")
    assert game.eval("a[3].region_key") == "capital_region"


def test_wounded_leader_skipped_and_rank_breaks_ties(game):
    game.run("""
        low = make_character(2, { rank = 1 })
        high = make_character(3, { rank = 7 })
        player = make_faction("player", {
            leader = make_character(1, { wounded = true }),
            forces = { make_force(low, 10), make_force(high, 10) },
        })
        a = donation_army_spawn.anchors(player)
    """)
    assert game.eval("#a") == 1
    assert game.eval("a[1].character == high")


def test_find_position_falls_through_to_capital(game):
    game.run("""
        player = make_faction("player", { capital = "capital_region" })
        x, y = donation_army_spawn.find_position(player, "rebels", 5)
    """)
    assert game.eval("x") == 100
    assert game.eval("fake.spawn_queries[1].from") == "capital_region"
    assert game.eval("fake.spawn_queries[1].distance") == 5


def test_find_position_none_when_no_valid_spot(game):
    game.run("""
        fake.valid_spawn = false
        player = make_faction("player", { leader = make_character(1), capital = "capital_region" })
    """)
    assert game.eval("donation_army_spawn.find_position(player, 'rebels', 5)") is None
    assert game.eval("#fake.spawn_queries") == 2


def test_spawn_creates_named_force_and_declares_war(game):
    game.run(TIERS + """
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
        s = fake.spawns[1]
    """)
    assert game.eval("ok") is True
    assert game.eval("s.faction") == "invader"
    assert game.eval("s.units") == "u3"
    assert game.eval("s.subtype") == "wh_main_chs_lord"
    assert game.eval("fake.renames[s.cqi]") == "Bob"
    assert game.eval('fake.xp["character_cqi:" .. s.cqi]') == 3
    assert game.eval('fake.wars["invader|player"]') is True


def test_spawn_returns_false_without_position(game):
    game.run(TIERS + """
        fake.valid_spawn = false
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("ok") is False
    assert game.eval("#fake.spawns") == 0


def test_spawn_error_is_logged_and_entry_done(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        cm.create_force_with_general = function() error("bad unit key") end
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("ok") is True
    assert any("bad unit key" in line and "Warband" in line for line in game.log)


def test_spawn_skips_xp_when_zero(game):
    game.run(TIERS + """
        make_faction("wh_main_chs_chaos_rebels")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("next(fake.xp)") is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_spawn.py -v`
Expected: FAIL, `donation_army_spawn` is nil.

- [ ] **Step 3: Implement**

`mod/script/campaign/mod/donation_army_spawn.lua`:
```lua
-- Donation Army: picks a tier and spawns its army near the player.
-- Anchor order (spec decision 8): faction leader -> strongest army -> capital.

donation_army_spawn = donation_army_spawn or {}
local sp = donation_army_spawn

local function log(msg)
	if donation_army and donation_army.log then
		donation_army.log(msg)
	end
end

function sp.pick_tier(tiers, amount)
	local best
	for _, tier in ipairs(tiers) do
		if amount >= tier.min_usd and (not best or tier.min_usd > best.min_usd) then
			best = tier
		end
	end
	return best
end

-- most units wins, general rank breaks ties; garrisons are skipped
function sp.strongest_army(faction)
	local best, best_units, best_rank
	local forces = faction:military_force_list()
	for i = 0, forces:num_items() - 1 do
		local force = forces:item_at(i)
		if force:has_general() and not force:is_armed_citizenry() then
			local general = force:general_character()
			local units, rank = force:unit_list():num_items(), general:rank()
			if not best or units > best_units or (units == best_units and rank > best_rank) then
				best, best_units, best_rank = general, units, rank
			end
		end
	end
	return best
end

function sp.anchors(faction)
	local list = {}
	local leader = faction:faction_leader()
	if leader and not leader:is_null_interface() and not leader:is_wounded() then
		table.insert(list, { character = leader })
	end
	local strongest = sp.strongest_army(faction)
	if strongest then
		table.insert(list, { character = strongest })
	end
	if faction:has_home_region() then
		table.insert(list, { region_key = faction:home_region():name() })
	end
	return list
end

function sp.find_position(faction, spawn_faction_key, distance)
	for _, anchor in ipairs(sp.anchors(faction)) do
		local x, y
		if anchor.character then
			x, y = cm:find_valid_spawn_location_for_character_from_character(spawn_faction_key, cm:char_lookup_str(anchor.character), true, distance)
		else
			x, y = cm:find_valid_spawn_location_for_character_from_settlement(spawn_faction_key, anchor.region_key, false, true, distance)
		end
		if x and y and x >= 0 and y >= 0 then
			return x, y
		end
	end
end

function sp.on_spawned(cqi, entry, tier, player_key)
	local general = cm:get_character_by_cqi(cqi)
	if general then
		cm:change_character_custom_name(general, entry.donor, "", "", "")
	end
	if (tier.xp_ranks or 0) > 0 then
		cm:add_experience_to_units_commanded_by_character(cm:char_lookup_str(cqi), tier.xp_ranks)
	end
	local spawned, player = cm:get_faction(tier.faction), cm:get_faction(player_key)
	if spawned and player and not spawned:at_war_with(player) then
		cm:force_declare_war(tier.faction, player_key, false, false)
	end
	log("spawned " .. tier.name .. " for " .. entry.donor .. " (" .. entry.id .. ")")
end

function sp.spawn(entry, tier, faction, distance)
	local x, y = sp.find_position(faction, tier.faction, distance)
	if not x then
		return false
	end
	-- region only seeds the general's home; same choice as PJ's Console
	local region_key = cm:model():world():region_manager():region_list():item_at(0):name()
	local player_key = faction:name()
	-- a bad key in the config must not break the turn; log it and treat the entry as handled
	local ok, err = pcall(function()
		cm:create_force_with_general(tier.faction, table.concat(tier.units, ","), region_key, x, y,
			"general", tier.subtype, "", "", "", "", false,
			function(cqi) sp.on_spawned(cqi, entry, tier, player_key) end)
	end)
	if not ok then
		log("spawn failed for " .. entry.id .. " (check tier '" .. tier.name .. "' keys): " .. tostring(err))
	end
	return true
end
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests -v`
Expected: all queue + spawn tests pass.

- [ ] **Step 5: Commit**

```bash
git add mod tests
git commit -m "feat: tier pick and spawn with leader/strongest/capital anchors"
```

---

### Task 4: Main module (state, warning poll, turn-start spawning) + config

**Files:**
- Create: `mod/script/campaign/mod/donation_army_config.lua`, `mod/script/campaign/mod/donation_army.lua`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `donation_army_queue.read`, `donation_army_spawn.pick_tier`, `donation_army_spawn.spawn`.
- Produces: `donation_army.log(msg)`, `donation_army.poll()`, `donation_army.spawn_pending(faction)`, `donation_army.install()`, `donation_army.show_warning(text)`. Saved keys `donation_army_handled`, `donation_army_warned` (tables id→true), `donation_army_initialized` (bool). Real callback name `donation_army_poll`.

- [ ] **Step 1: Config**

`mod/script/campaign/mod/donation_army_config.lua`. Use the `spawn_distance` chosen in Task 1. Unit and subtype keys are checked against the repo-root TSVs.
```lua
-- Donation Army settings. Edit tiers freely: the highest min_usd a donation meets wins.
-- Unit keys: main_units_tables.tsv, subtypes: agent_subtypes_tables.tsv, factions: faction_tables.tsv
-- An army holds at most 19 units besides its general.

donation_army_config = {
	queue_file = "donation_army_queue.txt", -- relative to the WH3 install folder
	poll_interval_ms = 3000,
	spawn_distance = 5,
	tiers = {
		{
			name = "Warband",
			min_usd = 5,
			faction = "wh_main_chs_chaos_rebels",
			subtype = "wh_main_chs_lord",
			xp_ranks = 0,
			units = {
				"wh_main_chs_inf_chaos_marauders_0", "wh_main_chs_inf_chaos_marauders_0",
				"wh_main_chs_inf_chaos_marauders_1", "wh_main_chs_mon_chaos_warhounds_0",
				"wh_main_chs_cav_marauder_horsemen_0", "wh_main_chs_inf_chaos_warriors_0",
			},
		},
		{
			name = "Horde",
			min_usd = 20,
			faction = "wh_main_chs_chaos_rebels",
			subtype = "wh_main_chs_lord",
			xp_ranks = 2,
			units = {
				"wh_main_chs_inf_chaos_warriors_0", "wh_main_chs_inf_chaos_warriors_0",
				"wh_main_chs_inf_chaos_warriors_1", "wh_main_chs_inf_chaos_warriors_1",
				"wh_main_chs_inf_chaos_marauders_1", "wh_main_chs_inf_chaos_marauders_1",
				"wh_main_chs_cav_chaos_knights_0", "wh_main_chs_cav_chaos_knights_0",
				"wh_main_chs_mon_trolls", "wh_main_chs_mon_trolls",
				"wh_main_chs_cav_chaos_chariot", "wh_main_chs_art_hellcannon",
			},
		},
		{
			name = "Doomstack",
			min_usd = 50,
			faction = "wh_main_chs_chaos_rebels",
			subtype = "wh_main_chs_lord",
			xp_ranks = 5,
			units = {
				"wh_main_chs_inf_chosen_0", "wh_main_chs_inf_chosen_0", "wh_main_chs_inf_chosen_1",
				"wh_main_chs_inf_chosen_1", "wh_dlc01_chs_inf_chosen_2", "wh_dlc01_chs_inf_chosen_2",
				"wh_main_chs_cav_chaos_knights_1", "wh_main_chs_cav_chaos_knights_1",
				"wh_dlc01_chs_cav_gorebeast_chariot", "wh_dlc01_chs_mon_dragon_ogre",
				"wh_dlc01_chs_mon_dragon_ogre", "wh_dlc01_chs_mon_dragon_ogre_shaggoth",
				"wh_main_chs_mon_giant", "wh_main_chs_art_hellcannon", "wh_main_chs_art_hellcannon",
				"wh_main_chs_mon_chaos_spawn", "wh_main_chs_mon_chaos_spawn",
				"wh_main_chs_mon_trolls", "wh_main_chs_mon_trolls",
			},
		},
	},
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_main.py`:
```python
PLAYER = 'make_faction("player", { leader = make_character(1), capital = "capital_region" })'


def setup(game):
    game.run(PLAYER)


def test_new_campaign_skips_backlog(game):
    setup(game)
    game.queue("old1\tBob\t50.00")
    game.first_tick()
    game.player_turn_start()
    assert game.eval("#fake.spawns") == 0
    assert game.eval("fake.saved.donation_army_initialized") is True


def test_warning_then_spawn_next_turn(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t20.00")
    game.poll()
    assert game.eval("#fake.popups") == 1
    assert "Bob ($20.00) has summoned a Horde" in game.eval("fake.popups[1]")
    assert game.eval("#fake.spawns") == 0
    game.player_turn_start()
    assert game.eval("#fake.spawns") == 1
    assert game.eval("fake.renames[fake.spawns[1].cqi]") == "Bob"


def test_warns_once_and_batches(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00", "b2\tAlice\t50.00")
    game.poll()
    game.poll()
    assert game.eval("#fake.popups") == 1
    text = game.eval("fake.popups[1]")
    assert "Bob" in text and "Alice" in text and "Doomstack" in text


def test_each_entry_spawns_once(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00", "b2\tAlice\t5.00")
    game.player_turn_start()
    game.player_turn_start()
    assert game.eval("#fake.spawns") == 2


def test_below_lowest_tier_is_ignored(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tCheap\t1.00")
    game.poll()
    game.player_turn_start()
    assert game.eval("#fake.popups") == 0
    assert game.eval("#fake.spawns") == 0
    assert game.eval('fake.saved.donation_army_handled["a1"]') is True


def test_no_valid_spot_retries_next_turn(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00")
    game.run("fake.valid_spawn = false")
    game.player_turn_start()
    assert game.eval("#fake.spawns") == 0
    game.run("fake.valid_spawn = { x = 1, y = 2 }")
    game.player_turn_start()
    assert game.eval("#fake.spawns") == 1


def test_poll_errors_are_logged_not_raised(game):
    setup(game)
    game.first_tick()
    game.run("donation_army_queue.read = function() error('boom') end")
    game.poll()
    assert any("boom" in line for line in game.log)
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL, `donation_army` is nil / no first-tick callback.

- [ ] **Step 4: Implement**

`mod/script/campaign/mod/donation_army.lua`. The `show_warning` body uses the dialog approach validated in Task 1. If Task 1 chose the fallback, replace only that function.
```lua
-- Donation Army: spawns hostile armies for donations queued by the companion app (app/).
-- Warns as soon as a donation is seen; spawns at the start of the player's next turn.
-- Spec: docs/superpowers/specs/2026-10-08-donation-army-spawn-design.md

donation_army = donation_army or {}
local da = donation_army

local HANDLED = "donation_army_handled"
local WARNED = "donation_army_warned"
local INITIALIZED = "donation_army_initialized"

function da.log(msg)
	out("[DonationArmy] " .. msg)
end

local function saved_set(key)
	local set = cm:get_saved_value(key)
	if type(set) ~= "table" then
		set = {}
	end
	return set
end

local function read_entries()
	return donation_army_queue.read(donation_army_config.queue_file)
end

local function pick_tier(entry)
	return donation_army_spawn.pick_tier(donation_army_config.tiers, entry.amount)
end

local warning_count = 0
function da.show_warning(text)
	warning_count = warning_count + 1
	local box = core:get_or_create_component("donation_army_warning_" .. warning_count, "ui/common ui/dialogue_box")
	box:SetVisible(true)
	find_uicomponent(box, "DY_text"):SetStateText(text)
	core:add_listener("donation_army_warning_close_" .. warning_count, "ComponentLClickUp",
		function(context) return context.string == "button_tick" or context.string == "button_cancel" end,
		function() box:Destroy() end, false)
end

local function poll()
	local handled, warned = saved_set(HANDLED), saved_set(WARNED)
	local lines = {}
	for _, entry in ipairs(read_entries()) do
		if not handled[entry.id] and not warned[entry.id] then
			local tier = pick_tier(entry)
			if tier then
				table.insert(lines, string.format("%s ($%.2f) has summoned a %s! It arrives next turn.", entry.donor, entry.amount, tier.name))
				warned[entry.id] = true
			else
				handled[entry.id] = true
				da.log("ignored " .. entry.id .. ": $" .. entry.amount .. " is below the lowest tier")
			end
		end
	end
	cm:set_saved_value(HANDLED, handled)
	cm:set_saved_value(WARNED, warned)
	if #lines > 0 then
		da.show_warning(table.concat(lines, "\n"))
	end
end

-- runs on a real-time timer: never let an error escape into the game's timer loop
function da.poll()
	local ok, err = pcall(poll)
	if not ok then
		da.log("poll failed: " .. tostring(err))
	end
end

function da.spawn_pending(faction)
	local handled = saved_set(HANDLED)
	for _, entry in ipairs(read_entries()) do
		if not handled[entry.id] then
			local tier = pick_tier(entry)
			if not tier then
				handled[entry.id] = true
			elseif donation_army_spawn.spawn(entry, tier, faction, donation_army_config.spawn_distance) then
				handled[entry.id] = true
			else
				da.log("no valid spawn location for " .. entry.id .. "; retrying next turn")
			end
		end
	end
	cm:set_saved_value(HANDLED, handled)
end

function da.install()
	if not cm:get_saved_value(INITIALIZED) then
		local handled = saved_set(HANDLED)
		for _, entry in ipairs(read_entries()) do
			handled[entry.id] = true
		end
		cm:set_saved_value(HANDLED, handled)
		cm:set_saved_value(INITIALIZED, true)
		da.log("new campaign: existing queue entries skipped")
	end
	core:add_listener("donation_army_turn_start", "ScriptEventPlayerFactionTurnStart", true,
		function(context) da.spawn_pending(context:faction()) end, true)
	cm:repeat_real_callback(da.poll, donation_army_config.poll_interval_ms, "donation_army_poll")
	da.log("installed")
end

cm:add_first_tick_callback(function() da.install() end)
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add mod tests
git commit -m "feat: warning poll, turn-start spawning and default tiers"
```

---

### Task 5: Pack build

**Files:**
- Create: `build.ps1`

**Interfaces:**
- Produces: `dist\donation_army.pack`, installed into the game's `data` folder.

- [ ] **Step 1: Write the build script** (adapted from wh3-ultimate-endgame-mod)

```powershell
# Builds dist\donation_army.pack from mod\script\ and installs it into the game data folder.
$ErrorActionPreference = "Stop"
$root   = $PSScriptRoot
$cli    = "C:\dev\gaming\rpfm\rpfm_cli.exe"
$schema = "$env:APPDATA\FrodoWazEre\rpfm\config\schemas\schema_wh3.ron"
$dist   = "$root\dist"
$pack   = "$dist\donation_army.pack"

New-Item -ItemType Directory -Force -Path $dist | Out-Null
Remove-Item -Force $pack -ErrorAction SilentlyContinue
& $cli -g warhammer_3 pack create -p $pack
if ($LASTEXITCODE -ne 0) { throw "rpfm_cli pack create failed" }
& $cli -g warhammer_3 pack add -p $pack -t "$schema" -F "$root\mod\script;script"
if ($LASTEXITCODE -ne 0) { throw "rpfm_cli pack add failed" }

$gameData = "C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data"
try {
	Copy-Item $pack "$gameData\donation_army.pack" -Force
	Write-Output "Installed -> $gameData\donation_army.pack"
} catch {
	Write-Output "WARNING: could not copy into game data folder (run elevated, or copy manually): $($_.Exception.Message)"
}

Write-Output "=== Pack contents ==="
& $cli -g warhammer_3 pack list -p $pack
```
Add `dist/` to `.gitignore`.

- [ ] **Step 2: Run it**

Run: `powershell -ExecutionPolicy Bypass -File .\build.ps1`
Expected: pack listing shows the four `script/campaign/mod/donation_army*.lua` files.

- [ ] **Step 3: Commit**

```bash
git add build.ps1 .gitignore
git commit -m "build: rpfm pack script"
```

---

### Task 6: Companion app core (currency, donation parsing, queue writer)

**Files:**
- Create: `app/package.json`, `app/src/currency.js`, `app/src/donation.js`, `app/src/queue.js`
- Test: `app/test/currency.test.js`, `app/test/donation.test.js`, `app/test/queue.test.js`

**Interfaces:**
- Produces:
  - `toUsd(amount, currency, rates) -> number|null` (null = unknown currency or non-numeric amount)
  - `parseDonations(event) -> [{id, donor, amount, currency, isTest}]`
  - `sanitizeDonor(name) -> string`, `formatLine({id, donor, amountUsd}) -> string`, `readIds(path) -> Set<string>`, `appendEntry(path, entry, seenIds) -> boolean`

- [ ] **Step 1: package.json**

```json
{
  "name": "donation-army-bridge",
  "private": true,
  "type": "module",
  "scripts": {
    "start": "node src/index.js",
    "fake": "node src/fake.js",
    "test": "node --test"
  },
  "dependencies": {
    "socket.io-client": "^2.5.0"
  }
}
```
Run: `cd app && npm install`. Add `node_modules/` (already in `.gitignore`), commit `package-lock.json`.

- [ ] **Step 2: Write the failing tests**

`app/test/currency.test.js`:
```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { toUsd } from '../src/currency.js';

const rates = { USD: 1, EUR: 1.1 };

test('converts known currencies and rounds to cents', () => {
  assert.equal(toUsd('10', 'EUR', rates), 11);
  assert.equal(toUsd(13.371, 'usd', rates), 13.37);
});

test('unknown currency or bad amount gives null', () => {
  assert.equal(toUsd(5, 'JPY', rates), null);
  assert.equal(toUsd('abc', 'USD', rates), null);
});

test('missing currency means USD', () => {
  assert.equal(toUsd(5, undefined, rates), 5);
});
```
`app/test/donation.test.js`:
```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDonations } from '../src/donation.js';

test('parses a Streamlabs donation event', () => {
  const event = {
    type: 'donation',
    event_id: 'evt_1',
    message: [{ id: 96164121, _id: 'abc123', name: 'Bob', amount: '13.37', currency: 'USD' }],
  };
  assert.deepEqual(parseDonations(event), [
    { id: 'abc123', donor: 'Bob', amount: 13.37, currency: 'USD', isTest: false },
  ]);
});

test('accepts for: streamlabs and flags test alerts', () => {
  const event = { type: 'donation', for: 'streamlabs', message: [{ id: 5, name: '', amount: 5, isTest: true }] };
  const [d] = parseDonations(event);
  assert.equal(d.id, '5');
  assert.equal(d.donor, 'Anonymous');
  assert.equal(d.currency, 'USD');
  assert.equal(d.isTest, true);
});

test('ignores non-donation events', () => {
  assert.deepEqual(parseDonations({ type: 'follow', message: [{}] }), []);
  assert.deepEqual(parseDonations({ type: 'bits', for: 'twitch_account', message: [{}] }), []);
  assert.deepEqual(parseDonations(null), []);
});
```
`app/test/queue.test.js`:
```js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { sanitizeDonor, formatLine, readIds, appendEntry } from '../src/queue.js';

const tmpFile = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-')), 'queue.txt');

test('sanitizeDonor strips separators, trims, caps length, defaults', () => {
  assert.equal(sanitizeDonor(' Bob\tthe\nGreat '), 'Bob the Great');
  assert.equal(sanitizeDonor('x'.repeat(60)).length, 40);
  assert.equal(sanitizeDonor(''), 'Anonymous');
  assert.equal(sanitizeDonor(undefined), 'Anonymous');
});

test('formatLine matches the mod format', () => {
  assert.equal(formatLine({ id: 'a1', donor: 'Bob', amountUsd: 20 }), 'a1\tBob\t20.00\n');
});

test('appendEntry writes once per id and survives restarts via readIds', () => {
  const file = tmpFile();
  const seen = readIds(file);
  assert.equal(appendEntry(file, { id: 'a1', donor: 'Bob', amountUsd: 5 }, seen), true);
  assert.equal(appendEntry(file, { id: 'a1', donor: 'Bob', amountUsd: 5 }, seen), false);
  assert.deepEqual([...readIds(file)], ['a1']);
  assert.equal(fs.readFileSync(file, 'utf8'), 'a1\tBob\t5.00\n');
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd app && npm test`
Expected: FAIL, modules not found.

- [ ] **Step 4: Implement**

`app/src/currency.js`:
```js
// Streamlabs sends the donor's currency and no USD figure; rates come from config.
export function toUsd(amount, currency, rates) {
  const value = Number(amount);
  if (!Number.isFinite(value)) return null;
  const rate = rates[(currency || 'USD').toUpperCase()];
  if (rate === undefined) return null;
  return Math.round(value * rate * 100) / 100;
}
```
`app/src/donation.js`:
```js
// Streamlabs Socket API: donations are { type: 'donation', for?: 'streamlabs', message: [...] }.
export function parseDonations(event) {
  if (!event || event.type !== 'donation' || !Array.isArray(event.message)) return [];
  if (event.for !== undefined && event.for !== 'streamlabs') return [];
  return event.message.map((m) => ({
    id: String(m._id ?? m.id ?? event.event_id),
    donor: m.name || m.from || 'Anonymous',
    amount: Number(m.amount),
    currency: m.currency || 'USD',
    isTest: m.isTest === true,
  }));
}
```
`app/src/queue.js`:
```js
// Queue file shared with the WH3 mod: one `id<TAB>donor<TAB>amount_usd` line per donation.
import fs from 'node:fs';

export function sanitizeDonor(name) {
  const clean = String(name ?? '').replace(/[\t\r\n]+/g, ' ').trim().slice(0, 40);
  return clean || 'Anonymous';
}

export function formatLine({ id, donor, amountUsd }) {
  return `${String(id).replace(/[\t\r\n]/g, '')}\t${sanitizeDonor(donor)}\t${amountUsd.toFixed(2)}\n`;
}

export function readIds(path) {
  if (!fs.existsSync(path)) return new Set();
  const lines = fs.readFileSync(path, 'utf8').split(/\r?\n/).filter(Boolean);
  return new Set(lines.map((line) => line.split('\t')[0]));
}

export function appendEntry(path, entry, seenIds) {
  if (seenIds.has(entry.id)) return false;
  fs.appendFileSync(path, formatLine(entry));
  seenIds.add(entry.id);
  return true;
}
```

- [ ] **Step 5: Run to verify pass**

Run: `cd app && npm test`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app
git commit -m "feat(app): currency conversion, donation parsing and queue writer"
```

---

### Task 7: Companion app CLI, fake-donation tool, docs

**Files:**
- Create: `app/src/config.js`, `app/src/index.js`, `app/src/fake.js`, `app/config.example.json`, `README.md`

**Interfaces:**
- Consumes: everything from Task 6.
- Produces: `loadConfig() -> object` (exits with a message if `app/config.local.json` is missing), `npm start` (listen), `npm run fake -- <donor> <amountUsd>` (append a fake entry).

- [ ] **Step 1: Config example**

`app/config.example.json`:
```json
{
  "socketToken": "paste-your-streamlabs-socket-api-token-here",
  "queuePath": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Total War WARHAMMER III\\donation_army_queue.txt",
  "currencyRates": { "USD": 1, "EUR": 1.08, "GBP": 1.27, "CAD": 0.73, "AUD": 0.66 },
  "acceptTestAlerts": true,
  "logRawEvents": false
}
```

- [ ] **Step 2: Shared config loader + CLI**

`app/src/config.js`:
```js
import fs from 'node:fs';

export function loadConfig() {
  const url = new URL('../config.local.json', import.meta.url);
  if (!fs.existsSync(url)) {
    console.error('Missing app/config.local.json: copy config.example.json and fill it in.');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(url, 'utf8'));
}
```

`app/src/index.js`:
```js
// Listens to Streamlabs donations and appends them to the WH3 mod's queue file.
import io from 'socket.io-client';
import { loadConfig } from './config.js';
import { toUsd } from './currency.js';
import { parseDonations } from './donation.js';
import { readIds, appendEntry } from './queue.js';

function handle(config, seen, donation) {
  if (donation.isTest && !config.acceptTestAlerts) {
    console.log(`Skipped test alert from ${donation.donor}`);
    return;
  }
  // test alerts may reuse ids; give each its own so every click queues a spawn
  const id = donation.isTest ? `test-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` : donation.id;
  let usd = toUsd(donation.amount, donation.currency, config.currencyRates);
  if (usd === null) {
    console.warn(`Unknown currency ${donation.currency}; treating ${donation.amount} as USD`);
    usd = Number(donation.amount);
  }
  if (!Number.isFinite(usd)) {
    console.warn(`Ignored donation ${id}: amount ${donation.amount} is not a number`);
    return;
  }
  const added = appendEntry(config.queuePath, { id, donor: donation.donor, amountUsd: usd }, seen);
  console.log(added ? `Queued ${donation.donor} $${usd.toFixed(2)} (${id})` : `Duplicate ${id} ignored`);
}

const config = loadConfig();
const seen = readIds(config.queuePath);
// token is in the URL: never log the URL
const socket = io(`https://sockets.streamlabs.com?token=${config.socketToken}`, { transports: ['websocket'] });
socket.on('connect', () => console.log('Connected to Streamlabs. Waiting for donations...'));
socket.on('disconnect', (reason) => console.warn(`Disconnected (${reason}). Donations sent while disconnected are lost.`));
socket.on('event', (event) => {
  if (config.logRawEvents) console.log(JSON.stringify(event));
  for (const donation of parseDonations(event)) handle(config, seen, donation);
});
```
`app/src/fake.js`:
```js
// Appends a fake donation to the queue: npm run fake -- <donor> <amountUsd>
import { loadConfig } from './config.js';
import { readIds, appendEntry } from './queue.js';

const [donor = 'Test Donor', amount = '5'] = process.argv.slice(2);
const config = loadConfig();
const id = `fake-${Date.now()}`;
appendEntry(config.queuePath, { id, donor, amountUsd: Number(amount) }, readIds(config.queuePath));
console.log(`Queued fake donation ${donor} $${Number(amount).toFixed(2)} (${id})`);
```

- [ ] **Step 3: Verify the fake tool locally**

Copy `config.example.json` to `config.local.json`, temporarily set `queuePath` to a scratch file, run `npm run fake -- Bob 20`, and confirm the file contains `fake-<n>\tBob\t20.00`. Then run `npm start` with a dummy token: it must start and not print the token. Disconnect/auth errors are expected. Delete the scratch file.

- [ ] **Step 4: README**

`README.md` sections: what it does (one paragraph), install the mod (`build.ps1`, enable `donation_army.pack` in the launcher), editing tiers (`mod/script/campaign/mod/donation_army_config.lua`, the TSVs at repo root for keys), streamer setup (Streamlabs account → Settings → API Settings → API Tokens → copy "Your Socket API Token"; path may differ slightly), run the app (`cd app`, `npm install`, copy `config.example.json` to `config.local.json`, `npm start`), testing (`python -m pytest`, `cd app && npm test`, `npm run fake -- Bob 20`, Streamlabs "Test Alert"), the in-game smoke test (`tools/console/smoke.lua` via PJ's Console `e`), and limits: donations made while the app is off are lost; a new campaign skips donations queued before it started; loading an older save may re-spawn armies already spawned in a later save; queue file lives in the game folder.

- [ ] **Step 5: Run all tests**

Run: `python -m pytest` and `cd app && npm test`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app README.md
git commit -m "feat(app): Streamlabs listener, fake donation tool and README"
```

---

### Task 8: End-to-end verification (user in-game)

**Files:**
- Modify: `docs/superpowers/specs/2026-10-08-donation-army-spawn-design.md` (record results)

- [ ] **Step 1: Fake path.** Run `build.ps1`, enable the pack, start a NEW campaign. Run `npm run fake -- Bob 20` with `queuePath` pointing at the game folder. Expect the warning dialog within ~3 seconds. End turn: at the next player turn start, a Chaos rebel "Horde" named Bob appears near the faction leader with rank 2 units. End another turn: nothing new spawns.
- [ ] **Step 2: Save/load.** Save, queue another fake, load the save. Expect exactly one new spawn next turn, and none re-spawned for Bob.
- [ ] **Step 3: Streamlabs path.** With the user's own token in `config.local.json` and `"logRawEvents": true`, start `npm start`, then click Streamlabs "Test Alert → Donation". Expect a `Queued ...` line and the dialog in game. Paste one raw event (it holds no token) into the spec to confirm the payload shape. Turn `logRawEvents` back off.
- [ ] **Step 4: Record and commit**

```bash
git add docs/superpowers/specs/2026-10-08-donation-army-spawn-design.md
git commit -m "docs: end-to-end verification results"
```
