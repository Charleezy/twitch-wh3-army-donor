-- Donation Army: picks a tier, rolls a race, composes its army and spawns it near the player with heroes.
-- Anchor order (spec decision 8): faction leader -> strongest army -> capital.

donation_army_spawn = donation_army_spawn or {}
local sp = donation_army_spawn

local function log(msg)
	if donation_army and donation_army.log then
		donation_army.log(msg)
	end
end

-- base tier: the highest min_usd the amount meets (nil if below the lowest tier; a bonus never rescues it)
function sp.base_tier(tiers, amount)
	local best
	for _, tier in ipairs(tiers) do
		if amount >= tier.min_usd and (not best or tier.min_usd > best.min_usd) then
			best = tier
		end
	end
	return best
end

-- extra tiers from turn_tier_bonus: the entry with the highest `turn` <= the current turn
function sp.tier_bonus(turn, turn_tier_bonus)
	local best_turn, bonus = -1, 0
	for _, entry in ipairs(turn_tier_bonus or {}) do
		if turn and turn >= entry.turn and entry.turn > best_turn then
			best_turn, bonus = entry.turn, entry.tiers
		end
	end
	return bonus
end

-- base tier moved up by the turn bonus (tiers ordered by min_usd), capped at the top tier.
-- turn and turn_tier_bonus are optional: without them this is the plain base tier.
function sp.pick_tier(tiers, amount, turn, turn_tier_bonus)
	local base = sp.base_tier(tiers, amount)
	if not base then
		return nil
	end
	local bonus = sp.tier_bonus(turn, turn_tier_bonus)
	if bonus <= 0 then
		return base
	end
	local sorted = {}
	for _, tier in ipairs(tiers) do
		table.insert(sorted, tier)
	end
	table.sort(sorted, function(a, b) return a.min_usd < b.min_usd end)
	for i, tier in ipairs(sorted) do
		if tier == base then
			return sorted[math.min(i + bonus, #sorted)]
		end
	end
	return base
end

-- the game's random_number is (max, min), inclusive; the composer wants rng(min, max)
function sp.rng(a, b)
	return cm:random_number(b, a)
end

-- races that may be rolled: config list (nil = every roster) limited to rosters whose faction exists here
function sp.allowed_races(races, rosters)
	local list = {}
	if races then
		for _, race in ipairs(races) do
			table.insert(list, race)
		end
	else
		for race in pairs(rosters or {}) do
			table.insert(list, race)
		end
	end
	table.sort(list)
	local allowed = {}
	for _, race in ipairs(list) do
		local roster = rosters and rosters[race]
		local faction = roster and cm:get_faction(roster.faction)
		if faction and not faction:is_null_interface() then
			table.insert(allowed, race)
		end
	end
	return allowed
end

-- most units wins, general rank breaks ties; garrisons are skipped
function sp.strongest_army(faction)
	local best, best_units, best_rank
	local forces = faction:military_force_list()
	for i = 0, forces:num_items() - 1 do
		local force = forces:item_at(i)
		if force:has_general() and not force:is_armed_citizenry() then
			local general = force:general_character()
			local units, rank = force:unit_list():num_items(), general:rank()
			if not best or units > best_units or (units == best_units and rank > best_rank) then
				best, best_units, best_rank = general, units, rank
			end
		end
	end
	return best
end

function sp.anchors(faction)
	local list = {}
	local leader = faction:faction_leader()
	if leader and not leader:is_null_interface() and not leader:is_wounded() then
		table.insert(list, { character = leader })
	end
	local strongest = sp.strongest_army(faction)
	if strongest then
		table.insert(list, { character = strongest })
	end
	if faction:has_home_region() then
		table.insert(list, { region_key = faction:home_region():name() })
	end
	return list
end

-- spawn-spot lookups use the player's own faction key: they return -1,-1 for factions absent from the campaign
-- returns x, y and the anchor that produced them
function sp.find_position(faction, distance)
	local faction_key = faction:name()
	for _, anchor in ipairs(sp.anchors(faction)) do
		local x, y
		if anchor.character then
			x, y = cm:find_valid_spawn_location_for_character_from_character(faction_key, cm:char_lookup_str(anchor.character), true, distance)
		else
			x, y = cm:find_valid_spawn_location_for_character_from_settlement(faction_key, anchor.region_key, false, true, distance)
		end
		if x and y and x >= 0 and y >= 0 then
			return x, y, anchor
		end
	end
end

-- heroes join the spawned army: created next to its general, then embedded in its force
local function add_heroes(general, heroes, owner, player_key)
	for _, hero in ipairs(heroes) do
		local x, y = cm:find_valid_spawn_location_for_character_from_character(player_key, cm:char_lookup_str(general), true, 3)
		local agent = x and x >= 0 and cm:create_agent(owner, hero.agent_type, hero.agent_subtype, x, y)
		if agent then
			cm:embed_agent_in_force(agent, general:military_force())
		else
			log("hero " .. hero.agent_subtype .. " not created (no spot or create_agent failed)")
		end
	end
end

-- armies are CA invasions: they hunt their target and (with the effect bundle) take no attrition.
-- The race is rolled per spawn; the army is composed from that race's roster for the tier's difficulty.
function sp.spawn(entry, tier, faction, distance)
	local x, y, anchor = sp.find_position(faction, distance)
	if not x then
		return false
	end
	local player_key = faction:name()
	local config = donation_army_config or {}
	-- a bad key in the config must not break the turn; log it and treat the entry as handled
	local ok, err = pcall(function()
		local races = sp.allowed_races(config.races, donation_army_rosters)
		if #races == 0 then
			log("no allowed race has a faction in this campaign; " .. entry.id .. " not spawned")
			return
		end
		local race = races[donation_army_composer.roll(sp.rng, 1, #races)]
		local roster = donation_army_rosters[race]
		local settings = (config.difficulties or {})[tier.difficulty]
		if not settings then
			error("unknown difficulty '" .. tostring(tier.difficulty) .. "'")
		end
		local army = donation_army_composer.compose(roster, settings, sp.rng, donation_army_composer.weights_for(race))
		local summary = race .. ", lord " .. army.lord .. ", " .. #army.units .. " units, " .. #army.heroes .. " heroes"
		local key = "donation_army_" .. tostring(entry.id):gsub("[^%w_]", "_")
		local invasion = invasion_manager:new_invasion(key, roster.faction, table.concat(army.units, ","), { x = x, y = y })
		if not invasion then
			log("invasion not created for " .. entry.id .. " (duplicate key or faction " .. roster.faction .. " missing)")
			return
		end
		if anchor.character then
			invasion:set_target("CHARACTER", anchor.character:command_queue_index(), player_key)
		else
			invasion:set_target("REGION", anchor.region_key, player_key)
		end
		invasion:create_general(false, army.lord)
		local bundle = config.army_effect_bundle
		if type(bundle) == "string" and bundle ~= "" then
			invasion:apply_effect(bundle, -1)
		end
		if army.unit_xp > 0 then
			invasion:add_unit_experience(army.unit_xp)
		end
		if army.lord_level > 1 then
			invasion:add_character_experience(army.lord_level, true)
		end
		invasion:start_invasion(function(started)
			-- runs when the army appears, possibly outside the pcall above
			local cb_ok, cb_err = pcall(function()
				local general = cm:get_character_by_cqi(started:get_general():command_queue_index())
				if general then
					cm:change_character_custom_name(general, entry.donor, "", "", "")
					add_heroes(general, army.heroes, roster.faction, player_key)
				end
				log("spawned " .. tier.name .. " (" .. summary .. ") for " .. entry.donor .. " (" .. entry.id .. ")")
			end)
			if not cb_ok then
				log("spawn callback failed for " .. entry.id .. " (" .. summary .. "): " .. tostring(cb_err))
			end
		end, true, false, false)
	end)
	if not ok then
		log("spawn failed for " .. entry.id .. " (tier '" .. tier.name .. "'): " .. tostring(err))
	end
	return true
end
