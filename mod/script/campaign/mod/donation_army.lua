-- Donation Army: spawns hostile armies for donations queued by the companion app (app/).
-- Warns as soon as a donation is seen; spawns at the start of the player's next turn.
-- Spec: docs/superpowers/specs/2026-10-08-donation-army-spawn-design.md

donation_army = donation_army or {}
local da = donation_army

local HANDLED = "donation_army_handled"
local WARNED = "donation_army_warned"
local INITIALIZED = "donation_army_initialized"

function da.log(msg)
	out("[DonationArmy] " .. msg)
end

local function saved_set(key)
	local set = cm:get_saved_value(key)
	if type(set) ~= "table" then
		set = {}
	end
	return set
end

local function read_entries()
	return donation_army_queue.read(donation_army_config.queue_file)
end

local function pick_tier(entry)
	return donation_army_spawn.pick_tier(donation_army_config.tiers, entry.amount)
end

local warning_count = 0
function da.show_warning(text)
	warning_count = warning_count + 1
	local box = core:get_or_create_component("donation_army_warning_" .. warning_count, "ui/common ui/dialogue_box")
	box:SetVisible(true)
	find_uicomponent(box, "DY_text"):SetStateText(text)
	core:add_listener("donation_army_warning_close_" .. warning_count, "ComponentLClickUp",
		function(context) return context.string == "button_tick" or context.string == "button_cancel" end,
		function() box:Destroy() end, false)
end

local function poll()
	local handled, warned = saved_set(HANDLED), saved_set(WARNED)
	local lines = {}
	for _, entry in ipairs(read_entries()) do
		if not handled[entry.id] and not warned[entry.id] then
			local tier = pick_tier(entry)
			if tier then
				table.insert(lines, string.format("%s ($%.2f) has summoned a %s! It arrives next turn.", entry.donor, entry.amount, tier.name))
				warned[entry.id] = true
			else
				handled[entry.id] = true
				da.log("ignored " .. entry.id .. ": $" .. entry.amount .. " is below the lowest tier")
			end
		end
	end
	cm:set_saved_value(HANDLED, handled)
	cm:set_saved_value(WARNED, warned)
	if #lines > 0 then
		da.show_warning(table.concat(lines, "\n"))
	end
end

-- runs on a real-time timer: never let an error escape into the game's timer loop
function da.poll()
	local ok, err = pcall(poll)
	if not ok then
		da.log("poll failed: " .. tostring(err))
	end
end

function da.spawn_pending(faction)
	local handled = saved_set(HANDLED)
	-- persist per entry so a later error cannot cause a duplicate spawn next turn
	local function mark_handled(id)
		handled[id] = true
		cm:set_saved_value(HANDLED, handled)
	end
	for _, entry in ipairs(read_entries()) do
		if not handled[entry.id] then
			local tier = pick_tier(entry)
			if not tier then
				mark_handled(entry.id)
			else
				local ok, spawned = pcall(donation_army_spawn.spawn, entry, tier, faction, donation_army_config.spawn_distance)
				if not ok then
					da.log("spawn failed for " .. entry.id .. ": " .. tostring(spawned))
				elseif spawned then
					mark_handled(entry.id)
				else
					da.log("no valid spawn location for " .. entry.id .. "; retrying next turn")
				end
			end
		end
	end
end

function da.install()
	if not cm:get_saved_value(INITIALIZED) then
		local handled = saved_set(HANDLED)
		for _, entry in ipairs(read_entries()) do
			handled[entry.id] = true
		end
		cm:set_saved_value(HANDLED, handled)
		cm:set_saved_value(INITIALIZED, true)
		da.log("new campaign: existing queue entries skipped")
	end
	for _, tier in ipairs(donation_army_config.tiers) do
		local faction = cm:get_faction(tier.faction)
		if not faction or faction:is_null_interface() then
			da.log("tier '" .. tier.name .. "' faction '" .. tier.faction .. "' does not exist in this campaign; its donations will not spawn")
		end
	end
	core:add_listener("donation_army_turn_start", "ScriptEventPlayerFactionTurnStart", true,
		function(context) da.spawn_pending(context:faction()) end, true)
	cm:repeat_real_callback(da.poll, donation_army_config.poll_interval_ms, "donation_army_poll")
	da.log("installed")
end

cm:add_first_tick_callback(function() da.install() end)
