-- Donation Army: reads the queue file written by the companion app.
-- One entry per line: id<TAB>donor<TAB>amount_usd

donation_army_queue = donation_army_queue or {}
local q = donation_army_queue

function q.parse(text)
	local entries = {}
	-- only complete lines: the app may be mid-append, so ignore text after the last newline
	local complete = (text or ""):match("^(.*\n)") or ""
	for line in complete:gmatch("[^\r\n]+") do
		local id, donor, amount = line:match("^([^\t]+)\t([^\t]*)\t([^\t]+)$")
		amount = tonumber(amount)
		if id and amount then
			table.insert(entries, { id = id, donor = donor, amount = amount })
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
