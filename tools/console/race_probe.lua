-- Run with PJ's Console: copy to the WH3 game folder as exec.lua, type `e`.
-- 1) Reports which per-race quest-battle factions exist in this campaign (no spawns).
-- 2) Spawns ONE Skaven invasion near the faction leader and embeds a hero into it.
-- Writes donation_army_races.txt. Use a throwaway save.
local LOG = "donation_army_races.txt"
io.open(LOG, "w"):close()
local function w(msg)
	local f = io.open(LOG, "a")
	f:write(tostring(msg) .. "\n")
	f:close()
end

-- race shorthand -> faction key, as used by Land Encounters and Points of Interest
local RACES = {
	skv = "wh2_main_skv_skaven_qb1", tmb = "wh2_dlc09_tmb_tombking_qb1", def = "wh2_main_def_dark_elves_qb1",
	dwf = "wh_main_dwf_dwarfs_qb1", hef = "wh2_main_hef_high_elves_qb1", lzd = "wh2_main_lzd_lizardmen_qb1",
	nor_qb1 = "wh_main_nor_norsca_qb1", nor_qb4 = "wh2_dlc11_nor_norsca_qb4", cst = "wh2_dlc11_cst_vampire_coast_qb1",
	vmp = "wh_main_vmp_vampire_counts_qb1", emp = "wh_main_emp_empire_qb1", brt = "wh_main_brt_bretonnia_qb1",
	grn = "wh_main_grn_greenskins_qb1", wef = "wh_dlc05_wef_wood_elves_qb1", bst = "wh_dlc03_bst_beastmen_qb1",
	cth = "wh3_main_cth_cathay_qb1", tze = "wh3_main_tze_tzeentch_qb1", chs = "wh_main_chs_chaos_qb1",
	kho = "wh3_main_kho_khorne_qb1", nur = "wh3_main_nur_nurgle_qb1", sla = "wh3_main_sla_slaanesh_qb1",
	chd = "wh3_dlc23_chd_chaos_dwarfs_qb1", ksl = "wh3_main_ksl_kislev_qb1", ogr = "wh3_main_ogr_ogre_kingdoms_qb1",
}

local ok, err = pcall(function()
	local names = {}
	for race in pairs(RACES) do table.insert(names, race) end
	table.sort(names)
	for _, race in ipairs(names) do
		local f = cm:get_faction(RACES[race])
		local exists = f and not f:is_null_interface()
		w(race .. " " .. RACES[race] .. " exists=" .. tostring(exists) .. (exists and (" dead=" .. tostring(f:is_dead())) or ""))
	end

	local OWNER = RACES.skv
	local player_key = cm:get_local_faction_name(true)
	local leader = cm:get_faction(player_key):faction_leader()
	local x, y = cm:find_valid_spawn_location_for_character_from_character(player_key, cm:char_lookup_str(leader), true, 8)
	w("spawn spot " .. tostring(x) .. "," .. tostring(y))
	if x < 0 then return end
	local inv = invasion_manager:new_invasion("donation_army_race_probe_" .. cm:model():turn_number() .. "_" .. x, OWNER,
		"wh2_main_skv_inf_clanrats_0,wh2_main_skv_inf_clanrats_0,wh2_main_skv_inf_stormvermin_0", { x, y })
	inv:set_target("CHARACTER", leader:command_queue_index(), player_key)
	inv:create_general(false, "wh2_main_skv_warlord")
	inv:apply_effect("wh2_dlc16_bundle_military_upkeep_free_force_immune_to_regionless_attrition", -1)
	inv:start_invasion(function(self)
		local ok2, err2 = pcall(function()
			local general = self:get_general()
			w("invasion started; general cqi " .. general:command_queue_index())
			cm:change_character_custom_name(general, "Race Probe", "", "", "")
			local hx, hy = cm:find_valid_spawn_location_for_character_from_character(player_key, cm:char_lookup_str(general), true, 3)
			w("hero spot " .. tostring(hx) .. "," .. tostring(hy))
			local hero = cm:create_agent(OWNER, "champion", "wh2_dlc16_skv_chieftain", hx, hy)
			w("create_agent -> " .. tostring(hero))
			if hero then
				cm:embed_agent_in_force(hero, general:military_force())
				w("embedded hero into the army")
			end
		end)
		if not ok2 then w("callback ERROR " .. tostring(err2)) end
	end, true, false, false)
	w("start_invasion called")
end)
if not ok then w("ERROR " .. tostring(err)) end
