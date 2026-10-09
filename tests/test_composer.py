import pytest

# deterministic Park-Miller rng(min, max), inclusive
RNG = """
function seeded_rng(seed)
	local state = seed
	return function(a, b)
		state = (state * 16807) % 2147483647
		return a + state % (b - a + 1)
	end
end
c = donation_army_composer
D = donation_army_config.difficulties
R = donation_army_rosters
"""

# per-army facts computed in Lua: unit count, total size, per-role counts, tiers used, duplicates
CHECK = """
function role_of(roster, unit)
	for tier, roles in pairs(roster.units) do
		for role, keys in pairs(roles) do
			for _, k in ipairs(keys) do
				if k == unit then return role, tier end
			end
		end
	end
end
function facts(roster, army)
	local f = { roles = {}, min_tier = 99, max_tier = 0, dup = false, unknown = 0 }
	local seen = {}
	for _, u in ipairs(army.units) do
		local role, tier = role_of(roster, u)
		if not role then f.unknown = f.unknown + 1 else
			f.roles[role] = (f.roles[role] or 0) + 1
			f.min_tier = math.min(f.min_tier, tier)
			f.max_tier = math.max(f.max_tier, tier)
			if seen[u] and (role == "warmachine" or role == "monster" or u:find("_ror")) then f.dup = true end
		end
		seen[u] = true
	end
	f.total = #army.units + 1 + #army.heroes
	return f
end
"""


def compose(game, race, difficulty, seed):
    game.run(RNG + CHECK + f'army = c.compose(R["{race}"], D["{difficulty}"], seeded_rng({seed}), c.weights_for("{race}")); f = facts(R["{race}"], army)')


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard", "apocalypse"])
def test_size_within_range_and_army_cap(game, difficulty):
    for seed in range(1, 40):
        compose(game, "chs", difficulty, seed)
        lo, hi = game.eval(f"D.{difficulty}.min_units"), game.eval(f"D.{difficulty}.max_units")
        total = game.eval("f.total")
        assert lo <= total <= hi and total <= 20
        assert game.eval("f.unknown") == 0


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard", "apocalypse"])
def test_hero_counts_per_difficulty(game, difficulty):
    counts = set()
    for seed in range(1, 60):
        compose(game, "emp", difficulty, seed)
        counts.add(game.eval("#army.heroes"))
        assert game.eval("army.heroes[1] == nil or army.heroes[1].agent_type ~= nil")
    lo, hi = game.eval(f"D.{difficulty}.limits.hero[1]"), game.eval(f"D.{difficulty}.limits.hero[2]")
    assert counts == set(range(lo, hi + 1))


def test_heroes_are_distinct(game):
    for seed in range(1, 40):
        compose(game, "emp", "hard", seed)
        if game.eval("#army.heroes") == 2:
            assert game.eval("army.heroes[1].agent_subtype ~= army.heroes[2].agent_subtype")


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_non_infantry_role_caps_respected(game, difficulty):
    # infantry and monstrous infantry may overflow their cap when no other role has eligible units
    for race in ["chs", "grn", "lzd", "emp"]:
        for seed in range(1, 15):
            compose(game, race, difficulty, seed)
            game.run(f"""
                over = nil
                for role, n in pairs(f.roles) do
                    if role ~= "melee_infantry" and role ~= "missile_infantry" and role ~= "monstrous_infantry" and n > D.{difficulty}.limits[role][2] then over = role end
                end
            """)
            assert game.eval("over") is None, (race, seed)


def test_easy_has_no_chariot_warmachine_monster_generic(game):
    for race in ["chs", "emp", "grn", "nor"]:
        for seed in range(1, 15):
            compose(game, race, "easy", seed)
            assert game.eval("(f.roles.chariot or 0) + (f.roles.warmachine or 0) + (f.roles.monster or 0) + (f.roles.generic or 0)") == 0


def test_tier_range_respected_when_pools_exist(game):
    # chs has every infantry/cavalry role at low tiers, so easy must stay within tiers 1-2 (widening only on empty pools)
    for seed in range(1, 30):
        compose(game, "chs", "easy", seed)
        assert game.eval("f.max_tier") <= 2
        assert game.eval("f.min_tier") >= 1


def test_no_duplicate_warmachine_monster_or_ror(game):
    for race in ["chs", "lzd", "dwf", "brt", "emp"]:
        for seed in range(1, 25):
            compose(game, race, "hard", seed)
            assert game.eval("f.dup") is False, (race, seed)


def test_xp_and_lord_level_in_range(game):
    for seed in range(1, 20):
        compose(game, "skv", "medium", seed)
        assert game.eval("D.medium.unit_xp[1] <= army.unit_xp and army.unit_xp <= D.medium.unit_xp[2]")
        assert game.eval("D.medium.lord_level[1] <= army.lord_level and army.lord_level <= D.medium.lord_level[2]")
        assert game.eval("army.lord") in [s for g in game.eval("R.skv.lords").values() for s in g.values()]


def test_fallback_when_role_pools_are_empty(game):
    # only melee infantry exists, only at tier 4: medium's 1-3 range widens and missile infantry falls back to melee
    game.run(RNG + """
        roster = { faction = "x", lords = { { "lord" } }, heroes = {}, units = { [4] = { melee_infantry = { "a", "b" } } } }
        army = c.compose(roster, D.medium, seeded_rng(7))
    """)
    total = game.eval("#army.units") + 1
    assert game.eval("D.medium.min_units") <= total <= game.eval("D.medium.max_units")
    assert game.eval("#army.heroes") == 0
    assert all(u in ("a", "b") for u in game.eval("army.units").values())


def test_all_races_all_difficulties_compose(game):
    game.run(RNG + """
        failures = {}
        for race, roster in pairs(R) do
            for name, settings in pairs(D) do
                for seed = 1, 5 do
                    local ok, army = pcall(c.compose, roster, settings, seeded_rng(seed), c.weights_for(race))
                    if not ok then
                        table.insert(failures, race .. "/" .. name .. ": " .. tostring(army))
                    else
                        local total = #army.units + 1 + #army.heroes
                        if not army.lord or total < settings.min_units or total > settings.max_units or total > 20 then
                            table.insert(failures, race .. "/" .. name .. ": size " .. total)
                        end
                    end
                end
            end
        end
    """)
    assert list(game.eval("failures").values()) == []


def test_out_of_range_rng_is_clamped(game):
    # the game stub's random_number may return a fixed value outside the asked range
    game.run(RNG + "army = c.compose(R.chs, D.hard, function(a, b) return 999 end)")
    assert game.eval("#army.units + 1 + #army.heroes") <= 20


def test_ogre_weights_favour_monstrous_infantry(game):
    assert game.eval('donation_army_composer.weights_for("ogr").monstrous_infantry') > game.eval(
        'donation_army_composer.weights_for("chs").monstrous_infantry'
    )


def test_easy_armies_are_6_to_8(game):
    game.run(RNG)
    assert game.eval("D.easy.min_units") == 6 and game.eval("D.easy.max_units") == 8
    totals = set()
    for race in ["chs", "emp", "grn", "nor", "nur", "lzd"]:
        for seed in range(1, 20):
            compose(game, race, "easy", seed)
            totals.add(game.eval("f.total"))
    assert totals <= {6, 7, 8} and len(totals) > 1


def test_lord_picked_by_group_then_subtype(game):
    # scripted rng: first roll chooses the group, second the subtype within it
    game.run(RNG + """
        roster = { faction = "x", units = { [1] = { melee_infantry = { "a" } } },
            lords = { { "caster_1", "caster_2", "caster_3", "caster_4" }, { "warrior" } }, heroes = {} }
        local function scripted(first)
            local n = 0
            return function(a, b)
                n = n + 1
                if n == 1 then return first end
                return a
            end
        end
        lord_a = c.compose(roster, D.easy, scripted(2)).lord
        lord_b = c.compose(roster, D.easy, scripted(1)).lord
        counts = { caster = 0, warrior = 0 }
        local rng = seeded_rng(11)
        for _ = 1, 400 do
            local l = c.compose(roster, D.easy, rng).lord
            counts[l == "warrior" and "warrior" or "caster"] = counts[l == "warrior" and "warrior" or "caster"] + 1
        end
    """)
    assert game.eval("lord_a") == "warrior" and game.eval("lord_b") == "caster_1"
    assert 150 < game.eval("counts.warrior") < 250  # about half, not 1 in 5


def test_heroes_come_from_distinct_types(game):
    game.run(RNG + """
        roster = { faction = "x", units = { [1] = { melee_infantry = { "a", "b" } } }, lords = { { "l" } },
            heroes = {
                { { agent_type = "wizard", agent_subtype = "w1" }, { agent_type = "wizard", agent_subtype = "w2" }, { agent_type = "wizard", agent_subtype = "w3" } },
                { { agent_type = "champion", agent_subtype = "c1" } },
                { { agent_type = "spy", agent_subtype = "s1" } },
            } }
        types = {}
        for seed = 1, 60 do
            local army = c.compose(roster, D.hard, seeded_rng(seed))
            local seen = {}
            for _, h in ipairs(army.heroes) do
                local t = h.agent_subtype:sub(1, 1)
                if seen[t] then table.insert(types, "dup") end
                seen[t] = true
            end
        end
    """)
    assert game.eval("#types") == 0


def test_apocalypse_fills_19_to_20_for_every_race(game):
    game.run(RNG + CHECK + """
        failures = {}
        for race, roster in pairs(R) do
            for seed = 1, 10 do
                local ok, army = pcall(c.compose, roster, D.apocalypse, seeded_rng(seed), c.weights_for(race))
                if not ok then
                    table.insert(failures, race .. ": " .. tostring(army))
                else
                    local total = #army.units + 1 + #army.heroes
                    if total < 19 or total > 20 then table.insert(failures, race .. ": size " .. total) end
                    if #roster.heroes > 0 and (#army.heroes < 1 or #army.heroes > 2) then
                        table.insert(failures, race .. ": heroes " .. #army.heroes)
                    end
                end
            end
        end
    """)
    assert list(game.eval("failures").values()) == []


def test_fallback_lowers_cost_floor_and_tier_until_army_fills(game):
    # only cheap tier-1 units: apocalypse (tiers 3-5, min cost 750) relaxes by 200 gold and one tier per step
    game.run(RNG + """
        roster = { faction = "x", lords = { { "lord" } }, heroes = {}, units = { [1] = { melee_infantry = { "a", "b", "c" } } },
            costs = { a = 300, b = 300, c = 300 } }
        army = c.compose(roster, D.apocalypse, seeded_rng(3))
    """)
    assert 19 <= game.eval("#army.units + 1") <= 20
    assert game.eval("army.relaxed") is True
    assert game.eval("army.min_unit_cost") == 150  # 750 -> 550 -> 350 -> 150: stops once units fit
    assert game.eval("army.min_tier") == 1


def test_units_without_cost_relax_to_zero(game):
    game.run(RNG + """
        roster = { faction = "x", lords = { { "lord" } }, heroes = {}, units = { [1] = { melee_infantry = { "a", "b", "c" } } } }
        army = c.compose(roster, D.apocalypse, seeded_rng(3))
    """)
    assert game.eval("#army.units + 1") >= 19
    assert game.eval("army.min_unit_cost") == 0


def test_infantry_minimum_only_up_to_eligible_units(game):
    # missile infantry exists only below the cost floor: its minimum is skipped, the slots go to eligible roles
    game.run(RNG + CHECK + """
        roster = { faction = "x", lords = { { "lord" } }, heroes = {},
            units = { [3] = { missile_infantry = { "cheap_bow" }, melee_infantry = { "elite" }, monstrous_infantry = { "big" } } },
            costs = { cheap_bow = 200, elite = 900, big = 1500 } }
        found = 0
        for seed = 1, 30 do
            local army = c.compose(roster, D.apocalypse, seeded_rng(seed))
            local total = #army.units + 1 + #army.heroes
            for _, u in ipairs(army.units) do
                if u == "cheap_bow" then found = found + 1 end
            end
            if army.relaxed or total < 19 then found = found + 100 end
        end
    """)
    assert game.eval("found") == 0


def cheap_units(game, difficulty, seeds=range(1, 40)):
    """(race, seed, unit, cost) for units under the difficulty's min_unit_cost in armies that did not relax."""
    game.run(RNG + f"""
        cheap = {{}}
        for race, roster in pairs(R) do
            for seed = {seeds.start}, {seeds.stop - 1} do
                local army = c.compose(roster, D.{difficulty}, seeded_rng(seed), c.weights_for(race))
                for _, u in ipairs(army.units) do
                    if not army.relaxed and c.cost(roster, u) < D.{difficulty}.min_unit_cost then
                        table.insert(cheap, race .. "/" .. seed .. ": " .. u)
                    end
                end
            end
        end
    """)
    return list(game.eval("cheap").values())


def test_min_unit_cost_per_difficulty(game):
    assert [game.eval(f"donation_army_config.difficulties.{d}.min_unit_cost") for d in ("easy", "medium", "hard", "apocalypse")] == [0, 0, 500, 750]


def test_ogre_apocalypse_has_no_unit_under_750(game):
    game.run(RNG + """
        bad, relaxed = {}, 0
        for seed = 1, 300 do
            local army = c.compose(R.ogr, D.apocalypse, seeded_rng(seed), c.weights_for("ogr"))
            if army.relaxed then relaxed = relaxed + 1 end
            for _, u in ipairs(army.units) do
                if c.cost(R.ogr, u) < 750 or u:find("gnoblar") or u:find("pigback") then table.insert(bad, seed .. ": " .. u) end
            end
        end
    """)
    assert list(game.eval("bad").values()) == []
    assert game.eval("relaxed") == 0


def test_hard_and_apocalypse_respect_cost_floor_unless_relaxed(game):
    assert cheap_units(game, "hard") == []
    assert cheap_units(game, "apocalypse") == []
    # relaxation is the exception: only Bretonnia (no infantry above tier 2) needs it for apocalypse
    game.run(RNG + """
        relaxed = {}
        for race, roster in pairs(R) do
            for _, d in ipairs({ "hard", "apocalypse" }) do
                if c.compose(roster, D[d], seeded_rng(5), c.weights_for(race)).relaxed then table.insert(relaxed, race .. "/" .. d) end
            end
        end
        table.sort(relaxed)
    """)
    assert list(game.eval("relaxed").values()) == ["brt/apocalypse"]


def test_gorgers_are_monstrous_infantry_by_role_override():
    import importlib.util
    from conftest import ROOT
    spec = importlib.util.spec_from_file_location("gen_rosters", ROOT / "tools/gen_rosters.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert gen.ROLE_OVERRIDES["wh3_main_ogr_mon_gorgers_0"] == "monstrous_infantry"
    assert set(gen.ROLE_OVERRIDES.values()) <= set(gen.ROLES)


def test_ogre_apocalypse_core_comes_from_monstrous_infantry(game):
    game.run(RNG + CHECK + """
        bad = {}
        for seed = 1, 200 do
            local army = c.compose(R.ogr, D.apocalypse, seeded_rng(seed), c.weights_for("ogr"))
            local f = facts(R.ogr, army)
            local gorgers_as_melee = false
            for _, u in ipairs(army.units) do
                if u:find("gorgers") and role_of(R.ogr, u) ~= "monstrous_infantry" then gorgers_as_melee = true end
                if c.cost(R.ogr, u) < 750 then table.insert(bad, seed .. ": cheap " .. u) end
            end
            if gorgers_as_melee then table.insert(bad, seed .. ": gorgers as melee infantry") end
            if (f.roles.monstrous_infantry or 0) < 4 then table.insert(bad, seed .. ": monstrous " .. (f.roles.monstrous_infantry or 0)) end
            if (f.roles.melee_infantry or 0) > 1 then table.insert(bad, seed .. ": melee " .. f.roles.melee_infantry) end
        end
    """)
    assert list(game.eval("bad").values()) == []


def test_melee_core_uses_melee_infantry_when_eligible(game):
    # Chaos has plenty of melee infantry at 750+ and tiers 3-5: its core stays melee infantry
    game.run(RNG + CHECK + """
        low = {}
        for seed = 1, 60 do
            local army = c.compose(R.chs, D.apocalypse, seeded_rng(seed), c.weights_for("chs"))
            local f = facts(R.chs, army)
            if (f.roles.melee_infantry or 0) < D.apocalypse.limits.melee_infantry[1] then table.insert(low, seed) end
        end
    """)
    assert list(game.eval("low").values()) == []


def test_melee_core_falls_back_to_monstrous_infantry(game):
    game.run(RNG + CHECK + """
        roster = { faction = "x", lords = { { "lord" } }, heroes = {},
            units = { [3] = { melee_infantry = { "cheap_inf" }, monstrous_infantry = { "brute" }, melee_cavalry = { "knight" } } },
            costs = { cheap_inf = 100, brute = 1200, knight = 1200 } }
        settings = { tiers = { 3, 3 }, min_unit_cost = 750, min_units = 8, max_units = 8,
            limits = { melee_infantry = { 5, 5 }, monstrous_infantry = { 0, 0 }, melee_cavalry = { 0, 20 } } }
        army = c.compose(roster, settings, seeded_rng(4))
        f = facts(roster, army)
    """)
    assert game.eval("f.roles.monstrous_infantry") == 5
    assert game.eval("f.roles.melee_infantry") is None
    assert game.eval("f.roles.melee_cavalry") == 2


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard", "apocalypse"])
def test_every_race_composes_with_known_units(game, difficulty):
    game.run(RNG + CHECK)
    races = game.lua.eval("(function() local t = {} for k in pairs(donation_army_rosters) do t[#t + 1] = k end table.sort(t) return t end)()")
    for race in races.values():
        for seed in range(1, 4):
            compose(game, race, difficulty, seed)
            assert game.eval("#army.units") > 0 and game.eval("f.unknown") == 0, (race, difficulty)
