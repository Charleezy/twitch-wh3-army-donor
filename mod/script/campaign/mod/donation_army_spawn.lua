-- Donation Army: picks a tier and spawns its army near the player.
-- Anchor order (spec decision 8): faction leader -> strongest army -> capital.

donation_army_spawn = donation_army_spawn or {}
local sp = donation_army_spawn

local function log(msg)
	if donation_army and donation_army.log then
		donation_army.log(msg)
	end
end

function sp.pick_tier(tiers, amount)
	local best
	for _, tier in ipairs(tiers) do
		if amount >= tier.min_usd and (not best or tier.min_usd > best.min_usd) then
			best = tier
		end
	end
	return best
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
			return x, y
		end
	end
end

function sp.on_spawned(cqi, entry, tier, player_key)
	local general = cm:get_character_by_cqi(cqi)
	if general then
		cm:change_character_custom_name(general, entry.donor, "", "", "")
	end
	if (tier.xp_ranks or 0) > 0 then
		cm:add_experience_to_units_commanded_by_character(cm:char_lookup_str(cqi), tier.xp_ranks)
	end
	local spawned, player = cm:get_faction(tier.faction), cm:get_faction(player_key)
	if spawned and player and not spawned:at_war_with(player) then
		cm:force_declare_war(tier.faction, player_key, false, false)
	end
	log("spawned " .. tier.name .. " for " .. entry.donor .. " (" .. entry.id .. ")")
end

function sp.spawn(entry, tier, faction, distance)
	local x, y = sp.find_position(faction, distance)
	if not x then
		return false
	end
	-- region only seeds the general's home; same choice as PJ's Console
	local region_key = cm:model():world():region_manager():region_list():item_at(0):name()
	local player_key = faction:name()
	-- a bad key in the config must not break the turn; log it and treat the entry as handled
	local ok, err = pcall(function()
		cm:create_force_with_general(tier.faction, table.concat(tier.units, ","), region_key, x, y,
			"general", tier.subtype, "", "", "", "", false,
			function(cqi) sp.on_spawned(cqi, entry, tier, player_key) end)
	end)
	if not ok then
		log("spawn failed for " .. entry.id .. " (check tier '" .. tier.name .. "' keys): " .. tostring(err))
	end
	return true
end
