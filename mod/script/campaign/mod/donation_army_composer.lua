-- Donation Army: builds a random army from a race roster (donation_army_rosters) and difficulty settings.
-- Composition rules adapted from Land Encounters and Points of Interest (Steam Workshop).
-- Pure functions: all randomness goes through rng(min, max) (inclusive) so tests can seed it.

donation_army_composer = donation_army_composer or {}
local c = donation_army_composer

c.MAX_ARMY = 20 -- units + lord + heroes

-- fixed order keeps weighted picks deterministic for a given rng
c.ROLES = {
	"melee_infantry", "missile_infantry", "melee_cavalry", "missile_cavalry", "monstrous_infantry",
	"monstrous_cavalry", "war_beast", "chariot", "warmachine", "monster", "generic",
}

-- relative chance (percent) of each role being picked once the infantry core is filled
c.WEIGHTS = {
	melee_infantry = 40, missile_infantry = 40, melee_cavalry = 15, missile_cavalry = 15,
	monstrous_infantry = 40, monstrous_cavalry = 20, war_beast = 40, chariot = 20,
	warmachine = 20, monster = 20, generic = 10,
}
c.RACE_WEIGHTS = { ogr = { monstrous_infantry = 80 } }

-- roles whose units (and any *_ror* unit) never appear twice in one army
local NO_DUPLICATES = { warmachine = true, monster = true }
-- roles that may fill past their cap when no other role has eligible units
local OVERFLOW = { melee_infantry = true, missile_infantry = true, monstrous_infantry = true }

function c.weights_for(race)
	local weights = {}
	for role, w in pairs(c.WEIGHTS) do
		weights[role] = w
	end
	for role, w in pairs(c.RACE_WEIGHTS[race] or {}) do
		weights[role] = w
	end
	return weights
end

-- rng result clamped to [a, b] (the game's random_number contract is trusted, but stubs and mistakes are not)
function c.roll(rng, a, b)
	if b <= a then
		return a
	end
	local n = tonumber(rng(a, b)) or a
	return math.max(a, math.min(b, math.floor(n)))
end

local function range(pair, default)
	pair = pair or { default, default }
	return pair[1], pair[2]
end

local function shuffled(list, rng)
	local out = {}
	for i, v in ipairs(list) do
		out[i] = v
	end
	for i = #out, 2, -1 do
		local j = c.roll(rng, 1, i)
		out[i], out[j] = out[j], out[i]
	end
	return out
end

local function unique(unit, role)
	return NO_DUPLICATES[role] or unit:find("_ror") ~= nil
end

-- the unit's gold cost from the roster's costs map (generated rosters always have one; unknown units cost 0)
function c.cost(roster, unit)
	return (roster.costs or {})[unit] or 0
end

-- eligible units of a role: tier within [lo, hi] and cost >= min_cost. An empty pool widens the tier range once by
-- one tier each way (an upper bound of 2 never widens, so easy armies stay low-tier). Units that may not repeat
-- and are already used are left out.
local function pool(roster, limits, role, used)
	local lo, hi, min_cost = limits.lo, limits.hi, limits.min_cost
	local function collect(a, b)
		local list, seen = {}, {}
		for tier = a, b do
			for _, unit in ipairs((roster.units[tier] or {})[role] or {}) do
				if not seen[unit] and c.cost(roster, unit) >= min_cost and not (used[unit] and unique(unit, role)) then
					seen[unit] = true
					table.insert(list, unit)
				end
			end
		end
		return list
	end
	local list = collect(lo, hi)
	if #list == 0 then
		list = collect(math.max(lo - 1, 1), hi == 2 and 2 or math.min(hi + 1, 5))
	end
	return list
end

function c.compose(roster, settings, rng, weights)
	weights = weights or c.WEIGHTS
	local limits = settings.limits or {}
	local army = { units = {}, heroes = {} }

	-- lords: a type group first (so lore variants of one caster don't outweigh the other lord types), then a subtype
	local lord_group = roster.lords[c.roll(rng, 1, #roster.lords)]
	army.lord = lord_group[c.roll(rng, 1, #lord_group)]
	army.unit_xp = c.roll(rng, range(settings.unit_xp, 0))
	army.lord_level = c.roll(rng, range(settings.lord_level, 1))

	local size = math.min(c.roll(rng, settings.min_units, settings.max_units), c.MAX_ARMY)
	local hero_count = math.min(c.roll(rng, range(limits.hero, 0)), #roster.heroes, size - 2)
	-- heroes: shuffle the type groups and take one random hero from each, so heroes differ in type when possible
	for i, group in ipairs(shuffled(roster.heroes, rng)) do
		if i > hero_count then
			break
		end
		local hero = group[c.roll(rng, 1, #group)]
		table.insert(army.heroes, { agent_type = hero.agent_type, agent_subtype = hero.agent_subtype })
	end
	local slots = size - 1 - #army.heroes

	-- what a unit must meet to be picked: tier within [lo, hi] and cost >= min_cost (relaxed below if the army can't fill)
	local lo, hi = range(settings.tiers, 1)
	local eligible = { lo = lo, hi = hi, min_cost = settings.min_unit_cost or 0 }

	local counts, used = {}, {}
	local function cap(role)
		local _, top = range(limits[role], c.MAX_ARMY)
		return top
	end
	local function available(role)
		return #pool(roster, eligible, role, used) > 0
	end
	-- adds up to `copies` of one random unit of the role; returns how many were added
	local function add(role, copies)
		local list = pool(roster, eligible, role, used)
		if #list == 0 then
			return 0
		end
		local unit = list[c.roll(rng, 1, #list)]
		if unique(unit, role) then
			copies = 1
		end
		copies = math.min(copies, slots - #army.units)
		for _ = 1, copies do
			table.insert(army.units, unit)
		end
		used[unit] = true
		counts[role] = (counts[role] or 0) + copies
		return copies
	end

	-- infantry core first, only as far as eligible units allow (e.g. Ogres have no tier 3+ missile infantry);
	-- slots the core can't fill go to the weighted roles below. When melee infantry runs out (Ogres: only a unique
	-- Regiment of Renown at tier 3+), the melee core is filled from monstrous infantry (Ironguts, Maneaters) instead.
	local melee_target = c.roll(rng, range(limits.melee_infantry, 0))
	local missile_target = c.roll(rng, range(limits.missile_infantry, 0))
	local core = { { "melee_infantry", melee_target, "monstrous_infantry" }, { "missile_infantry", missile_target } }
	for _, entry in ipairs(core) do
		local role, target, fallback = entry[1], entry[2], entry[3]
		local filled = 0
		while filled < target and #army.units < slots do
			local added = add(role, 1)
			if added == 0 and fallback then
				added = add(fallback, 1)
			end
			if added == 0 then
				break
			end
			filled = filled + added
		end
	end

	-- weighted random roles until the army is full; roles at their cap or with no eligible units are skipped.
	-- When nothing else fits, infantry and monstrous infantry fill the rest past their cap. When even that is
	-- empty, the cost floor drops by 200 (never below 0) and the tier range widens down by one, until it fills.
	while #army.units < slots do
		local candidates, total = {}, 0
		for _, role in ipairs(c.ROLES) do
			local w = weights[role] or 0
			if w > 0 and (counts[role] or 0) < cap(role) and available(role) then
				table.insert(candidates, { role = role, weight = w })
				total = total + w
			end
		end
		if #candidates == 0 then
			for _, role in ipairs(c.ROLES) do
				if OVERFLOW[role] and available(role) then
					local w = math.max(weights[role] or 0, 1)
					table.insert(candidates, { role = role, weight = w })
					total = total + w
				end
			end
		end
		if #candidates == 0 then
			if eligible.min_cost <= 0 and eligible.lo <= 1 then
				break
			end
			eligible.min_cost = math.max(0, eligible.min_cost - 200)
			eligible.lo = math.max(1, eligible.lo - 1)
			army.relaxed = true
		else
			local pick, role = c.roll(rng, 1, total), candidates[#candidates].role
			for _, cand in ipairs(candidates) do
				pick = pick - cand.weight
				if pick <= 0 then
					role = cand.role
					break
				end
			end
			-- occasionally take several copies of one unit, as Land Encounters does (at most 3, within the cap)
			local copies = 1
			if not unique("", role) and c.roll(rng, 1, 4) == 1 then
				copies = math.min(3, math.max(1, cap(role) - (counts[role] or 0)))
				copies = c.roll(rng, 1, copies)
			end
			if (counts[role] or 0) >= cap(role) then
				copies = 1 -- overflow past the cap
			end
			add(role, copies)
		end
	end
	-- the floor actually used (lower than the difficulty's when the army had to relax it)
	army.min_unit_cost, army.min_tier = eligible.min_cost, eligible.lo
	return army
end
