TIERS = """
tiers = {
	{ name = "Warband", min_usd = 5, difficulty = "small" },
	{ name = "Horde", min_usd = 20, difficulty = "test" },
}
-- one fake race owned by "invader": fixed lord, two heroes, one unit key
donation_army_rosters = {
	inv = {
		faction = "invader",
		units = { [1] = { melee_infantry = { "u3" } } },
		lords = { { "lord_a" } },
		heroes = { { { agent_type = "champion", agent_subtype = "hero_a" } }, { { agent_type = "wizard", agent_subtype = "hero_b" } } },
	},
}
donation_army_config.races = nil
donation_army_config.difficulties = {
	test = { tiers = { 1, 1 }, min_units = 6, max_units = 6, unit_xp = { 3, 3 }, lord_level = { 12, 12 },
		limits = { hero = { 2, 2 }, melee_infantry = { 3, 3 } } },
	small = { tiers = { 1, 1 }, min_units = 3, max_units = 3, unit_xp = { 0, 0 }, lord_level = { 1, 1 },
		limits = { hero = { 0, 0 }, melee_infantry = { 2, 2 } } },
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
        x, y = donation_army_spawn.find_position(player, 5)
    """)
    assert game.eval("x") == 100
    assert game.eval("fake.spawn_queries[1].from") == "capital_region"
    assert game.eval("fake.spawn_queries[1].distance") == 5


def test_find_position_queries_with_player_faction_key(game):
    game.run(TIERS + """
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
    """)
    assert game.eval("fake.spawn_queries[1].faction") == "player"


def test_find_position_none_when_no_valid_spot(game):
    game.run("""
        fake.valid_spawn = false
        player = make_faction("player", { leader = make_character(1), capital = "capital_region" })
    """)
    assert game.eval("donation_army_spawn.find_position(player, 5)") is None
    assert game.eval("#fake.spawn_queries") == 2


def test_spawn_creates_hunting_invasion_named_after_donor(game):
    game.run(TIERS + """
        donation_army_config.army_effect_bundle = "attrition_bundle"
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1), capital = "capital_region" })
        ok = donation_army_spawn.spawn({ id = "a-1!", donor = "Bob", amount = 25 }, tiers[2], player, 5)
        inv = fake.invasions[1]
    """)
    assert game.eval("ok") is True
    assert game.eval("#fake.invasions") == 1
    assert game.eval("inv.key") == "donation_army_a_1_"
    assert game.eval("inv.faction") == "invader"
    assert game.eval("inv.units") == "u3,u3,u3"
    assert game.eval("inv.spawn.x") == 100 and game.eval("inv.spawn.y") == 200
    assert game.eval("inv.general_subtype") == "lord_a"
    assert game.eval("inv.xp") == 3
    assert game.eval("inv.lord_xp") is None  # add_character_experience ignores by_level in the game
    assert game.eval("fake.ranks[inv.cqi]") == 12
    assert game.eval("inv.start.declare_war") is True
    assert game.eval("inv.start.invade") is False
    assert game.eval("inv.start.show") is False
    assert game.eval("fake.renames[inv.cqi]") == "Bob"


def test_target_is_leader_character_when_present(game):
    game.run(TIERS + """
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1), capital = "capital_region" })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
        t = fake.invasions[1].target
    """)
    assert game.eval("t.type") == "CHARACTER"
    assert game.eval("t.value") == 1
    assert game.eval("t.faction") == "player"


def test_target_is_strongest_army_when_leader_unavailable(game):
    game.run(TIERS + """
        make_faction("invader")
        player = make_faction("player", {
            leader = make_character(1, { wounded = true }),
            forces = { make_force(make_character(7), 9) },
            capital = "capital_region",
        })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
        t = fake.invasions[1].target
    """)
    assert game.eval("t.type") == "CHARACTER"
    assert game.eval("t.value") == 7


def test_target_is_capital_region_when_only_capital(game):
    game.run(TIERS + """
        make_faction("invader")
        player = make_faction("player", { capital = "capital_region" })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
        t = fake.invasions[1].target
    """)
    assert game.eval("t.type") == "REGION"
    assert game.eval("t.value") == "capital_region"
    assert game.eval("t.faction") == "player"


def test_effect_bundle_applied_permanently(game):
    game.run(TIERS + """
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
        effects = fake.invasions[1].effects
    """)
    assert game.eval("#effects") == 1
    assert game.eval("effects[1].bundle") == game.eval("donation_army_config.army_effect_bundle")
    assert game.eval("effects[1].bundle") != ""
    assert game.eval("effects[1].turns") == -1


def test_effect_bundle_omitted_when_empty(game):
    game.run(TIERS + """
        donation_army_config.army_effect_bundle = ""
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
    """)
    assert game.eval("#fake.invasions[1].effects") == 0


def test_spawn_returns_false_without_position(game):
    game.run(TIERS + """
        fake.valid_spawn = false
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("ok") is False
    assert game.eval("#fake.invasions") == 0


def test_spawn_error_is_logged_and_entry_done(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        make_faction("invader")
        invasion_manager.new_invasion = function() error("bad unit key") end
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("ok") is True
    assert any("bad unit key" in line and "Warband" in line for line in game.log)


def test_unknown_difficulty_is_logged_and_entry_done(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        make_faction("invader")
        tiers[1].difficulty = "nightmare"
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("ok") is True
    assert game.eval("#fake.invasions") == 0
    assert any("nightmare" in line for line in game.log)


def test_spawn_skips_xp_and_lord_level_when_minimal(game):
    game.run(TIERS + """
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("#fake.invasions") == 1
    assert game.eval("fake.invasions[1].xp") is None
    assert game.eval("fake.invasions[1].lord_xp") is None
    assert game.eval("fake.ranks[fake.invasions[1].cqi]") is None
    assert game.eval("#fake.agents") == 0


def test_lord_rank_failure_is_logged_and_army_still_spawns(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        fake.rank_fails = true
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
    """)
    assert game.eval("fake.renames[fake.invasions[1].cqi]") == "Bob"
    assert game.eval("#fake.agents") == 2
    assert any("lord level 12 not set" in line for line in game.log)
    assert any(line.startswith("spawned Horde") for line in game.log)


def test_duplicate_invasion_key_is_logged_and_entry_done(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        entry = { id = "a1", donor = "Bob", amount = 25 }
        first = donation_army_spawn.spawn(entry, tiers[2], player, 5)
        second = donation_army_spawn.spawn(entry, tiers[2], player, 5)
    """)
    assert game.eval("first") is True and game.eval("second") is True
    assert game.eval("#fake.invasions") == 1
    assert any("a1" in line and "invasion" in line for line in game.log)


def test_heroes_created_next_to_general_and_embedded(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
        inv = fake.invasions[1]
    """)
    assert game.eval("#fake.agents") == 2
    subtypes = {game.eval(f"fake.agents[{i}].agent_subtype") for i in (1, 2)}
    assert subtypes == {"hero_a", "hero_b"}
    assert game.eval("fake.agents[1].faction") == "invader"
    assert game.eval("fake.agents[1].x") == 100
    # hero spot is looked up from the spawned general with the player's faction key
    assert game.eval("fake.spawn_queries[2].from") == game.eval('"character_cqi:" .. inv.cqi')
    assert game.eval("fake.spawn_queries[2].faction") == "player"
    assert game.eval("#fake.embeds") == 2
    assert game.eval("fake.embeds[1].general_cqi") == game.eval("inv.cqi")
    assert game.eval("fake.embeds[1].agent_cqi") == game.eval("fake.agents[1].cqi")
    assert any("inv" in line and "lord_a" in line and "3 units" in line and "2 heroes" in line for line in game.log)


def test_failed_hero_is_logged_and_skipped(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        fake.agent_fails = true
        make_faction("invader")
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
    """)
    assert game.eval("ok") is True
    assert game.eval("#fake.embeds") == 0
    assert game.eval("fake.renames[fake.invasions[1].cqi]") == "Bob"
    assert sum("not created" in line for line in game.log) == 2


def test_allowed_races_filters_config_and_missing_factions(game):
    game.run("""
        rosters = { a = { faction = "fa" }, b = { faction = "fb" }, c = { faction = "fc" } }
        make_faction("fa"); make_faction("fc")
    """)
    assert list(game.eval("donation_army_spawn.allowed_races(nil, rosters)").values()) == ["a", "c"]
    assert list(game.eval('donation_army_spawn.allowed_races({ "c", "b", "zzz" }, rosters)').values()) == ["c"]


OTHER = """
donation_army_rosters.other = { faction = "other_faction", units = { [1] = { melee_infantry = { "o1" } } }, lords = { { "lord_o" } }, heroes = {} }
make_faction("invader"); make_faction("other_faction")
player = make_faction("player", { leader = make_character(1) })
"""


def test_race_is_rolled_from_allowed_races(game):
    game.run(TIERS + OTHER + """
        fake.random_pick = 2
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    # sorted allowed races: inv, other -> pick 2
    assert game.eval("fake.invasions[1].faction") == "other_faction"
    assert game.eval("fake.invasions[1].general_subtype") == "lord_o"


def test_config_races_restricts_roll(game):
    game.run(TIERS + OTHER + """
        donation_army_config.races = { "other" }
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("fake.invasions[1].faction") == "other_faction"


def test_no_allowed_race_is_logged_and_entry_done(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("ok") is True
    assert game.eval("#fake.invasions") == 0
    assert any("no allowed race" in line for line in game.log)


def test_rng_adapter_uses_game_argument_order(game):
    game.run("seen = nil; cm.random_number = function(self, max, min) seen = { max, min }; return min end")
    assert game.eval("donation_army_spawn.rng(2, 9)") == 2
    assert game.eval("seen[1]") == 9 and game.eval("seen[2]") == 2


SCALE = """
bonus = { { turn = 5, tiers = 1 }, { turn = 30, tiers = 2 } }
three = {
	{ name = "Doomstack", min_usd = 50 }, { name = "Warband", min_usd = 5 }, { name = "Horde", min_usd = 20 },
}
"""


def pick(game, amount, turn):
    game.run(SCALE)
    return game.eval(f"(donation_army_spawn.pick_tier(three, {amount}, {turn}, bonus) or {{}}).name")


def test_no_bonus_before_turn_5(game):
    assert pick(game, 5, 4) == "Warband"
    assert pick(game, 20, 1) == "Horde"


def test_plus_one_from_turn_5(game):
    assert pick(game, 5, 5) == "Horde"
    assert pick(game, 20, 29) == "Doomstack"


def test_plus_two_from_turn_30(game):
    assert pick(game, 5, 30) == "Doomstack"


def test_bonus_capped_at_top_tier(game):
    assert pick(game, 20, 30) == "Doomstack"
    assert pick(game, 500, 99) == "Doomstack"


def test_below_lowest_still_ignored_with_bonus(game):
    assert pick(game, 4.99, 30) is None


def test_unsorted_bonus_entries_and_no_bonus_args(game):
    game.run(SCALE + "bonus = { bonus[2], bonus[1] }")
    assert game.eval("donation_army_spawn.pick_tier(three, 5, 6, bonus).name") == "Horde"
    assert game.eval("donation_army_spawn.pick_tier(three, 5).name") == "Warband"
    assert game.eval("donation_army_spawn.pick_tier(three, 5, 30, {}).name") == "Warband"


def test_min_turn_gates_apocalypse_with_real_config(game):
    def real(amount, turn):
        return game.eval(
            f"donation_army_spawn.pick_tier(donation_army_config.tiers, {amount}, {turn}, donation_army_config.turn_tier_bonus).name"
        )

    assert real(100, 29) == "Doomstack"
    assert real(100, 30) == "Apocalypse"
    assert real(50, 10) == "Doomstack"
    assert real(20, 30) == "Apocalypse"
    assert real(50, 30) == "Apocalypse"
    assert real(5, 30) == "Doomstack"
    assert real(20, 29) == "Doomstack"
