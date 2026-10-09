-- Run with PJ's Console: copy to the WH3 game folder as exec.lua, type `e`.
-- Finds which owning factions exist in this campaign and tries spawning a small army into each
-- candidate. Writes donation_army_probe.txt. Spawns up to two 2-unit armies. Use a throwaway save.
local LOG = "donation_army_probe.txt"
io.open(LOG, "w"):close()
local function w(msg)
	local f = io.open(LOG, "a")
	f:write(tostring(msg) .. "\n")
	f:close()
end
local function step(name, fn)
	local ok, err = pcall(fn)
	if not ok then w(name .. ": ERROR " .. tostring(err)) end
end

local CANDIDATES = { "rebels", "wh_main_chs_chaos_qb1" }
local player_key = cm:get_local_faction_name(true)
local leader = cm:get_faction(player_key):faction_leader()

step("faction list", function()
	local list = cm:model():world():faction_list()
	w("factions in campaign: " .. list:num_items())
	for i = 0, list:num_items() - 1 do
		local f = list:item_at(i)
		local key = f:name()
		if key:find("rebel") or key:find("_qb%d") or key:find("invasion") then
			w("  " .. key .. " dead=" .. tostring(f:is_dead()))
		end
	end
end)

for i, faction_key in ipairs(CANDIDATES) do
	step("spawn " .. faction_key, function()
		local f = cm:get_faction(faction_key)
		w(faction_key .. " exists: " .. tostring(f and not f:is_null_interface()))
		-- spot found with the player's faction (the spawning faction may not path-check if absent)
		local x, y = cm:find_valid_spawn_location_for_character_from_character(player_key, cm:char_lookup_str(leader), true, 4 + i * 3)
		w("  spot " .. tostring(x) .. "," .. tostring(y))
		if not x or x < 0 then return end
		local region_key = cm:model():world():region_manager():region_list():item_at(0):name()
		cm:create_force_with_general(faction_key, "wh_main_chs_inf_chaos_marauders_0,wh_main_chs_inf_chaos_marauders_0",
			region_key, x, y, "general", "wh_main_chs_lord", "", "", "", "", false,
			function(cqi)
				local ok, err = pcall(function()
					w("  [" .. faction_key .. "] callback cqi " .. tostring(cqi))
					cm:change_character_custom_name(cm:get_character_by_cqi(cqi), "Probe " .. faction_key, "", "", "")
					local owner = cm:get_faction(faction_key)
					w("  [" .. faction_key .. "] at war with player: " .. tostring(owner:at_war_with(cm:get_faction(player_key))))
				end)
				if not ok then w("  [" .. faction_key .. "] callback ERROR " .. tostring(err)) end
			end)
		w("  create_force_with_general called")
	end)
end
