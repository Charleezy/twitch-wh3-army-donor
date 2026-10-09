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
    assert game.eval("fake.saved.donation_army_initialized") is True


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


def test_install_logs_missing_tier_factions(game):
    setup(game)
    game.run('make_faction("wh_main_chs_chaos_qb1")')
    game.run('donation_army_config.tiers[2].faction = "no_such_faction"')
    game.first_tick()
    missing = [line for line in game.log if "does not exist in this campaign" in line]
    assert len(missing) == 1
    assert "Horde" in missing[0] and "no_such_faction" in missing[0]
