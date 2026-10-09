-- Minimal stand-ins for the WH3 campaign scripting environment used by the mod.
test_log = {}
script_errors = {}
function out(msg) table.insert(test_log, msg) end
function script_error(msg) table.insert(script_errors, msg) end

fake = {
	saved = {},
	factions = {},
	characters = {},
	invasions = {},
	spawn_queries = {},
	renames = {},
	popups = {},
	first_tick = {},
	real_callbacks = {},
	valid_spawn = { x = 100, y = 200 }, -- set to false to make every spawn query fail
	local_faction = "player",
	next_cqi = 1000,
	turn = 1,
	random_pick = nil, -- value returned by cm:random_number; nil returns min
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
	fake.factions[key] = f
	return f
end

local function spawn_query(faction_key, from, distance)
	table.insert(fake.spawn_queries, { faction = faction_key, from = from, distance = distance })
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
	return spawn_query(faction_key, lookup, distance)
end
function cm:find_valid_spawn_location_for_character_from_settlement(faction_key, region_key, b1, b2, distance)
	return spawn_query(faction_key, region_key, distance)
end
function cm:random_number(max, min)
	min = min or 1
	return fake.random_pick or min
end
function cm:model()
	local region = { name = function() return "first_region" end }
	local region_manager = { region_list = function() return make_list({ region }) end }
	local world = { region_manager = function() return region_manager end }
	return { world = function() return world end, turn_number = function() return fake.turn end }
end
function cm:change_character_custom_name(character, forename) fake.renames[character:command_queue_index()] = forename end

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

-- records every invasion; new_invasion returns nil for a duplicate key or an unknown faction
invasion_manager = {}
function invasion_manager:new_invasion(key, faction_key, units, spawn)
	if fake.invasion_keys and fake.invasion_keys[key] or not cm:get_faction(faction_key) then
		script_error("invasion_manager: cannot create invasion " .. tostring(key))
		return nil
	end
	fake.invasion_keys = fake.invasion_keys or {}
	fake.invasion_keys[key] = true
	local rec = { key = key, faction = faction_key, units = units, spawn = spawn, effects = {} }
	table.insert(fake.invasions, rec)
	local inv = {}
	function inv:set_target(type, value, faction) rec.target = { type = type, value = value, faction = faction } end
	function inv:create_general(a, subtype) rec.general_subtype = subtype end
	function inv:apply_effect(bundle, turns) table.insert(rec.effects, { bundle = bundle, turns = turns }) end
	function inv:add_unit_experience(amount) rec.xp = amount end
	function inv:start_invasion(callback, declare_war, invade, show)
		rec.start = { declare_war = declare_war, invade = invade, show = show }
		fake.next_cqi = fake.next_cqi + 1
		rec.cqi = fake.next_cqi
		local general = make_character(rec.cqi)
		callback({ get_general = function() return general end })
	end
	return inv
end
