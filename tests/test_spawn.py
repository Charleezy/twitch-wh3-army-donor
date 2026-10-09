TIERS = """
tiers = {
	{ name = "Warband", min_usd = 5, faction = "wh_main_chs_chaos_qb1", subtype = "wh_main_chs_lord", units = { "u1", "u2" }, xp_ranks = 0 },
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
    assert game.eval("#fake.spawn_queries") == 1
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
    assert game.eval("inv.units") == "u3"
    assert game.eval("inv.spawn.x") == 100 and game.eval("inv.spawn.y") == 200
    assert game.eval("inv.general_subtype") == "wh_main_chs_lord"
    assert game.eval("inv.xp") == 3
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
        invasion_manager.new_invasion = function() error("bad unit key") end
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("ok") is True
    assert any("bad unit key" in line and "Warband" in line for line in game.log)


def test_spawn_skips_xp_when_zero(game):
    game.run(TIERS + """
        make_faction("wh_main_chs_chaos_qb1")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("#fake.invasions") == 1
    assert game.eval("fake.invasions[1].xp") is None


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


def test_unknown_faction_is_logged_and_entry_done(game):
    game.run(TIERS + """
        donation_army = { log = function(msg) out(msg) end }
        player = make_faction("player", { leader = make_character(1) })
        ok = donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 25 }, tiers[2], player, 5)
    """)
    assert game.eval("ok") is True
    assert game.eval("#fake.invasions") == 0
    assert any("a1" in line and "invasion" in line for line in game.log)


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


def test_subtype_string_passes_through(game):
    assert game.eval('donation_army_spawn.pick_subtype("wh_main_chs_lord")') == "wh_main_chs_lord"


def test_subtype_list_uses_random_pick(game):
    game.run("fake.random_pick = 2")
    assert game.eval('donation_army_spawn.pick_subtype({ "a", "b", "c" })') == "b"
    game.run("fake.random_pick = nil")
    assert game.eval('donation_army_spawn.pick_subtype({ "a", "b", "c" })') == "a"
