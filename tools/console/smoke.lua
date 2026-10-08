-- Run with PJ's Console: copy to the WH3 game folder as exec.lua, type `e`.
-- Writes donation_army_smoke.txt next to Warhammer3.exe.
local LOG = "donation_army_smoke.txt"
io.open(LOG, "w"):close()
local function w(msg)
	local f = io.open(LOG, "a")
	f:write(tostring(msg) .. "\n")
	f:close()
end
local function step(name, fn)
	local ok, err = pcall(fn)
	w(name .. ": " .. (ok and "ok" or ("ERROR " .. tostring(err))))
end

local REBELS = "wh_main_chs_chaos_rebels"
local player = cm:get_faction(cm:get_local_faction_name(true))
local leader = player:faction_leader()
local x, y

step("file roundtrip", function()
	local q = assert(io.open("donation_army_smoke_queue.txt", "w"))
	q:write("smoke-1\tSmoke Donor\t20.00\n")
	q:close()
	local r = assert(io.open("donation_army_smoke_queue.txt", "r"))
	w("  read back: " .. r:read("*a"))
	r:close()
end)

step("spawn location", function()
	w("  leader at " .. leader:logical_position_x() .. "," .. leader:logical_position_y()
		.. " wounded=" .. tostring(leader:is_wounded()))
	for _, distance in ipairs({ 1, 5, 10 }) do
		local sx, sy = cm:find_valid_spawn_location_for_character_from_character(REBELS, cm:char_lookup_str(leader), true, distance)
		w("  distance " .. distance .. " -> " .. tostring(sx) .. "," .. tostring(sy))
		if distance == 5 then
			x, y = sx, sy
		end
	end
end)

step("spawn + rename + xp", function()
	local region_key = cm:model():world():region_manager():region_list():item_at(0):name()
	cm:create_force_with_general(REBELS, "wh_main_chs_inf_chaos_marauders_0,wh_main_chs_inf_chaos_marauders_0",
		region_key, x, y, "general", "wh_main_chs_lord", "", "", "", "", false,
		function(cqi)
			local ok, err = pcall(function()
				w("  callback arg: " .. type(cqi) .. " " .. tostring(cqi))
				cm:change_character_custom_name(cm:get_character_by_cqi(cqi), "Smoke Donor", "", "", "")
				cm:add_experience_to_units_commanded_by_character(cm:char_lookup_str(cqi), 2)
				w("  callback: renamed + xp applied")
			end)
			if not ok then
				w("  callback ERROR " .. tostring(err))
			end
		end)
end)

step("warning dialog", function()
	local box = core:get_or_create_component("donation_army_smoke_box", "ui/common ui/dialogue_box")
	box:SetVisible(true)
	local text = find_uicomponent(box, "DY_text")
	w("  DY_text found: " .. tostring(text and true or false))
	text:SetStateText("Smoke Donor ($20.00) has summoned a Warband! It arrives next turn.")
	core:add_listener("donation_army_smoke_box_close", "ComponentLClickUp",
		function(context) return context.string == "button_tick" or context.string == "button_cancel" end,
		function() box:Destroy() end, false)
end)
