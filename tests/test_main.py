PLAYER = 'make_faction("player", { leader = make_character(1), capital = "capital_region" })'


def setup(game):
    game.run(PLAYER)
    game.run('make_faction("wh_main_chs_chaos_qb1")')


def test_new_campaign_skips_backlog(game):
    setup(game)
    game.queue("old1\tBob\t50.00")
    game.first_tick()
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 0
    assert "[DonationArmy] skipped 1 donations queued before this save was loaded" in game.log


NOW = 1_800_000_000


def load_at_now(game):
    game.run(f"donation_army.now = function() return {NOW} end")


def test_load_skips_old_entries_but_keeps_recent_ones(game):
    setup(game)
    load_at_now(game)
    game.queue(f"old\tBob\t50.00\t{NOW - 11 * 60}", f"recent\tAmy\t20.00\t{NOW - 9 * 60}", f"future\tZed\t5.00\t{NOW + 5}")
    game.first_tick()
    assert "[DonationArmy] skipped 1 donations queued before this save was loaded" in game.log
    game.poll()
    assert "Amy" in game.eval("fake.popups[1]") and "Zed" in game.eval("fake.popups[1]") and "Bob" not in game.eval("fake.popups[1]")
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 2
    assert game.eval("fake.saved.donation_army_handled.old") is True


def test_load_treats_three_field_legacy_lines_as_stale(game):
    setup(game)
    load_at_now(game)
    game.queue("legacy\tBob\t50.00")
    game.first_tick()
    game.poll()
    game.player_turn_start()
    assert game.eval("#fake.popups") == 0
    assert game.eval("#fake.invasions") == 0


def test_load_keeps_entries_handled_earlier(game):
    setup(game)
    load_at_now(game)
    game.run('fake.saved.donation_army_handled = { done = true }')
    game.queue(f"done\tBob\t50.00\t{NOW - 60}", f"mine\tAmy\t20.00\t{NOW - 60}")
    game.first_tick()
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 1
    assert game.eval("fake.renames[fake.invasions[1].cqi]") == "Amy"


def test_load_without_os_time_treats_everything_as_stale(game):
    setup(game)
    game.run("os.time = function() error('unavailable') end")
    game.queue(f"a\tBob\t50.00\t{NOW}")
    game.first_tick()
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 0


def test_running_save_is_unaffected_after_first_tick(game):
    setup(game)
    load_at_now(game)
    game.first_tick()
    game.queue("old_style\tBob\t20.00", f"ancient\tAmy\t20.00\t{NOW - 3600}")
    game.poll()
    assert "Bob" in game.eval("fake.popups[1]") and "Amy" in game.eval("fake.popups[1]")
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 2


def test_warning_then_spawn_next_turn(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t20.00")
    game.poll()
    assert game.eval("#fake.popups") == 1
    assert "Bob ($20.00) has summoned a Horde" in game.eval("fake.popups[1]")
    assert game.eval("#fake.invasions") == 0
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 1
    assert game.eval("fake.renames[fake.invasions[1].cqi]") == "Bob"


def test_warns_once_and_batches(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00", "b2\tAlice\t50.00")
    game.poll()
    game.poll()
    assert game.eval("#fake.popups") == 1
    text = game.eval("fake.popups[1]")
    assert "Bob" in text and "Alice" in text and "Doomstack" in text


def test_each_entry_spawns_once(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00", "b2\tAlice\t5.00")
    game.player_turn_start()
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 2


def test_below_lowest_tier_is_ignored(game):
    setup(game)
    game.run("donation_army_config.tiers[1].min_usd = 5")  # default Warband has no floor
    game.first_tick()
    game.queue("a1\tCheap\t1.00")
    game.poll()
    game.player_turn_start()
    assert game.eval("#fake.popups") == 0
    assert game.eval("#fake.invasions") == 0
    assert game.eval('fake.saved.donation_army_handled["a1"]') is True


def test_no_valid_spot_retries_next_turn(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00")
    game.run("fake.valid_spawn = false")
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 0
    game.run("fake.valid_spawn = { x = 1, y = 2 }")
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 1


def test_poll_errors_are_logged_not_raised(game):
    setup(game)
    game.first_tick()
    game.run("donation_army_queue.read = function() error('boom') end")
    game.poll()
    assert any("boom" in line for line in game.log)


def test_throwing_spawn_is_retried_without_losing_others(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00", "b2\tAlice\t5.00")
    game.run('''
        local real = donation_army_spawn.spawn
        fail_a1 = true
        donation_army_spawn.spawn = function(entry, ...)
            if entry.id == "a1" and fail_a1 then error("boom spawn") end
            return real(entry, ...)
        end
    ''')
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 1
    assert any("spawn failed for a1" in line and "boom spawn" in line for line in game.log)
    assert game.eval('fake.saved.donation_army_handled["a1"]') is None
    assert game.eval('fake.saved.donation_army_handled["b2"]') is True
    game.run("fail_a1 = false")
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 2


def test_install_logs_missing_race_factions(game):
    setup(game)
    game.run('donation_army_config.races = { "chs", "skv", "nope" }')
    game.first_tick()
    missing = [line for line in game.log if "will not be rolled" in line]
    assert len(missing) == 2
    assert any("skv" in line and "wh2_main_skv_skaven_qb1" in line for line in missing)
    assert any("nope" in line and "no roster" in line for line in missing)
    assert not any("no allowed race" in line for line in game.log)


def test_install_logs_when_no_race_can_spawn(game):
    game.run(PLAYER)
    game.first_tick()
    assert any("no allowed race" in line for line in game.log)


def test_install_logs_unknown_tier_difficulty(game):
    setup(game)
    game.run('donation_army_config.tiers[2].difficulty = "nightmare"')
    game.first_tick()
    bad = [line for line in game.log if "nightmare" in line]
    assert len(bad) == 1 and "Horde" in bad[0]


def test_warning_names_scaled_tier(game):
    setup(game)
    game.first_tick()
    game.queue("a1\tBob\t5.00")
    game.run("fake.turn = 5")
    game.poll()
    assert "Horde" in game.eval("fake.popups[1]")


def test_spawn_uses_scaled_tier_difficulty_and_rolled_race(game):
    setup(game)
    game.first_tick()
    game.queue("a1	Bob	5.00")
    game.run("fake.turn = 5")
    game.player_turn_start()
    assert game.eval("#fake.invasions") == 1
    inv = "fake.invasions[1]"
    # only the Chaos faction exists in this fake campaign, so chs is rolled; $5 at turn 5 is a Horde (medium)
    assert game.eval(f"{inv}.faction") == "wh_main_chs_chaos_qb1"
    chs_lords = [s for group in game.eval("donation_army_rosters.chs.lords").values() for s in group.values()]
    assert game.eval(f"{inv}.general_subtype") in chs_lords
    units = game.eval(f"{inv}.units").split(",")
    medium = "donation_army_config.difficulties.medium"
    assert game.eval(f"{medium}.min_units") <= len(units) + 1 <= game.eval(f"{medium}.max_units")
