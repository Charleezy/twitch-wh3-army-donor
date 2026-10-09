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

-- armies are CA invasions: they hunt their target and (with the effect bundle) take no attrition
function sp.spawn(entry, tier, faction, distance)
	local x, y, anchor = sp.find_position(faction, distance)
	if not x then
		return false
	end
	local player_key = faction:name()
	-- a bad key in the config must not break the turn; log it and treat the entry as handled
	local ok, err = pcall(function()
		local key = "donation_army_" .. tostring(entry.id):gsub("[^%w_]", "_")
		local invasion = invasion_manager:new_invasion(key, tier.faction, table.concat(tier.units, ","), { x = x, y = y })
		if not invasion then
			log("invasion not created for " .. entry.id .. " (duplicate key or tier '" .. tier.name .. "' faction missing)")
			return
		end
		if anchor.character then
			invasion:set_target("CHARACTER", anchor.character:command_queue_index(), player_key)
		else
			invasion:set_target("REGION", anchor.region_key, player_key)
		end
		invasion:create_general(false, tier.subtype)
		local bundle = donation_army_config and donation_army_config.army_effect_bundle
		if type(bundle) == "string" and bundle ~= "" then
			invasion:apply_effect(bundle, -1)
		end
		if (tier.xp_ranks or 0) > 0 then
			invasion:add_unit_experience(tier.xp_ranks)
		end
		invasion:start_invasion(function(started)
			local general = cm:get_character_by_cqi(started:get_general():command_queue_index())
			if general then
				cm:change_character_custom_name(general, entry.donor, "", "", "")
			end
			log("spawned " .. tier.name .. " for " .. entry.donor .. " (" .. entry.id .. ")")
		end, true, false, false)
	end)
	if not ok then
		log("spawn failed for " .. entry.id .. " (check tier '" .. tier.name .. "' keys): " .. tostring(err))
	end
	return true
end
