-- Donation Army settings. Edit tiers freely: the highest min_usd a donation meets wins.
-- Keys come from the game DB tables main_units_tables (units), agent_subtypes_tables (subtypes), factions_tables (factions)
-- An army holds at most 19 units besides its general.

donation_army_config = {
	queue_file = "donation_army_queue.txt", -- relative to the WH3 install folder
	poll_interval_ms = 10000,
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
