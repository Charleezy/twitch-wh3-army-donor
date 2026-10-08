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
