-- Donation Army: reads the queue file written by the companion app.
-- One entry per line: id<TAB>donor<TAB>amount_usd<TAB>epoch_seconds (the epoch is absent in old 3-field lines)

donation_army_queue = donation_army_queue or {}
local q = donation_army_queue

function q.parse(text)
	local entries = {}
	-- only complete lines: the app may be mid-append, so ignore text after the last newline
	local complete = (text or ""):match("^(.*\n)") or ""
	for line in complete:gmatch("[^\r\n]+") do
		local id, donor, amount, time = line:match("^([^\t]+)\t([^\t]*)\t([^\t]+)\t([^\t]*)$")
		if not id then
			id, donor, amount = line:match("^([^\t]+)\t([^\t]*)\t([^\t]+)$")
		end
		amount = tonumber(amount)
		if id and amount then
			table.insert(entries, { id = id, donor = donor, amount = amount, time = tonumber(time) })
		end
	end
	return entries
end

function q.read(path)
	local file = io.open(path, "r")
	if not file then
		return {}
	end
	local text = file:read("*a")
	file:close()
	return q.parse(text)
end
