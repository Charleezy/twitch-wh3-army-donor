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
        make_faction("wh_main_chs_chaos_qb1")
        player = make_faction("player", { leader = make_character(1) })
        donation_army_spawn.spawn({ id = "a1", donor = "Bob", amount = 5 }, tiers[1], player, 5)
    """)
    assert game.eval("next(fake.xp)") is None
