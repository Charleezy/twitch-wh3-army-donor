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


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_size_within_range_and_army_cap(game, difficulty):
    for seed in range(1, 40):
        compose(game, "chs", difficulty, seed)
        lo, hi = game.eval(f"D.{difficulty}.min_units"), game.eval(f"D.{difficulty}.max_units")
        total = game.eval("f.total")
        assert lo <= total <= hi and total <= 20
        assert game.eval("f.unknown") == 0


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
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
    for race in ["chs", "grn", "lzd", "emp"]:
        for seed in range(1, 15):
            compose(game, race, difficulty, seed)
            game.run(f"""
                over = nil
                for role, n in pairs(f.roles) do
                    if role ~= "melee_infantry" and role ~= "missile_infantry" and n > D.{difficulty}.limits[role][2] then over = role end
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
        assert game.eval("army.lord") in list(game.eval("R.skv.lords").values())


def test_fallback_when_role_pools_are_empty(game):
    # only melee infantry exists, only at tier 4: medium's 1-3 range widens and missile infantry falls back to melee
    game.run(RNG + """
        roster = { faction = "x", lords = { "lord" }, heroes = {}, units = { [4] = { melee_infantry = { "a", "b" } } } }
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
                    elseif #army.units == 0 or not army.lord or #army.units + 1 + #army.heroes > 20 then
                        table.insert(failures, race .. "/" .. name .. ": bad army")
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
