-- Run with PJ's Console: copy to the WH3 game folder as exec.lua, type `e`.
-- Spawns one small hostile army through CA's invasion manager, targeting the player's faction
-- leader, with upkeep-free + regionless-attrition-immune bundle. Writes donation_army_invasion.txt.
-- Then end a turn or two and watch whether it marches at the leader. Use a throwaway save.
local LOG = "donation_army_invasion.txt"
io.open(LOG, "w"):close()
local function w(msg)
	local f = io.open(LOG, "a")
	f:write(tostring(msg) .. "\n")
	f:close()
end

local ok, err = pcall(function()
	local OWNER = "wh_main_chs_chaos_qb1"
	local BUNDLE = "wh2_dlc16_bundle_military_upkeep_free_force_immune_to_regionless_attrition"
	local player_key = cm:get_local_faction_name(true)
	local leader = cm:get_faction(player_key):faction_leader()
	local x, y = cm:find_valid_spawn_location_for_character_from_character(player_key, cm:char_lookup_str(leader), true, 8)
	w("player " .. player_key .. ", leader cqi " .. leader:command_queue_index() .. ", spot " .. tostring(x) .. "," .. tostring(y))
	if x < 0 then
		w("no valid spot; aborting")
		return
	end

	local key = "donation_army_probe_" .. cm:model():turn_number() .. "_" .. x .. "_" .. y
	local inv = invasion_manager:new_invasion(key, OWNER,
		"wh_main_chs_inf_chaos_marauders_0,wh_main_chs_inf_chaos_marauders_0,wh_main_chs_mon_chaos_warhounds_0", { x, y })
	w("new_invasion " .. key .. " -> " .. tostring(inv))
	inv:set_target("CHARACTER", leader:command_queue_index(), player_key)
	inv:create_general(false, "wh_main_chs_lord")
	inv:apply_effect(BUNDLE, -1)
	inv:add_unit_experience(2)
	inv:start_invasion(function(self)
		local ok2, err2 = pcall(function()
			local cqi = self:get_general():command_queue_index()
			w("started; general cqi " .. cqi)
			cm:change_character_custom_name(cm:get_character_by_cqi(cqi), "Invasion Probe", "", "", "")
			local owner = cm:get_faction(OWNER)
			w("at war with player: " .. tostring(owner:at_war_with(cm:get_faction(player_key))))
		end)
		if not ok2 then w("callback ERROR " .. tostring(err2)) end
	end, true, false, false)
	w("start_invasion called")
end)
if not ok then w("ERROR " .. tostring(err)) end
