-- Donation Army settings. Edit tiers freely: the highest min_usd a donation meets wins.
-- Keys come from the game DB tables main_units_tables (units), agent_subtypes_tables (subtypes), factions_tables (factions)
-- A tier faction must exist in the campaign (e.g. the Chaos `_qb1` factions). Immortal Empires has no
-- `*_rebels` faction for Chaos and no generic `rebels`; spawning into a missing faction silently does nothing.
-- An army holds at most 19 units besides its general.
-- Armies are spawned as CA invasions that hunt the player. xp_ranks is passed to the invasion manager's add_unit_experience.

-- Random general pool shared by all tiers: generic recruitable Chaos lords and sorcerer lords.
-- Legendary lords are excluded on purpose.
local chaos_lords = {
	"wh_main_chs_lord", "wh3_dlc20_chs_lord_mkho", "wh3_dlc20_chs_lord_msla", "wh3_dlc24_chs_lord_mtze",
	"wh3_dlc25_chs_lord_mnur", "wh_dlc01_chs_sorcerer_lord_death", "wh_dlc01_chs_sorcerer_lord_fire",
	"wh_dlc01_chs_sorcerer_lord_metal", "wh_dlc07_chs_sorcerer_lord_shadow",
	"wh3_dlc20_chs_sorcerer_lord_death_mnur", "wh3_dlc20_chs_sorcerer_lord_nurgle_mnur",
	"wh3_dlc20_chs_sorcerer_lord_metal_mtze", "wh3_dlc20_chs_sorcerer_lord_tzeentch_mtze",
	"wh3_dlc27_chs_sorcerer_lord_shadows_msla", "wh3_dlc27_chs_sorcerer_lord_slaanesh_msla",
}

donation_army_config = {
	queue_file = "donation_army_queue.txt", -- relative to the WH3 install folder
	poll_interval_ms = 10000,
	spawn_distance = 5,
	-- effect bundle applied to every spawned army for its lifetime (no regionless attrition, no upkeep); "" disables
	army_effect_bundle = "wh2_dlc16_bundle_military_upkeep_free_force_immune_to_regionless_attrition",
	-- from that turn on, every donation spawns that many tiers higher, capped at the top tier; set to {} to disable
	turn_tier_bonus = { { turn = 5, tiers = 1 }, { turn = 30, tiers = 2 } },
	-- a tier's subtype may be one key or a list (one is picked at random per spawn)
	tiers = {
		{
			name = "Warband",
			min_usd = 5,
			faction = "wh_main_chs_chaos_qb1",
			subtype = chaos_lords,
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
			faction = "wh_main_chs_chaos_qb1",
			subtype = chaos_lords,
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
			faction = "wh_main_chs_chaos_qb1",
			subtype = chaos_lords,
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
