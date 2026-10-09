# WH3 Donation Army Spawn

A Total War: WARHAMMER III campaign mod plus a small companion app. When a viewer donates through Streamlabs, the app appends the donation to a queue file in the game folder. The mod polls that file, warns you as soon as a donation is seen, and at your next turn start spawns a hostile Chaos rebel army near you. Bigger donations spawn bigger armies; every donation that meets the lowest tier spawns (no cap).

## Install the mod

1. Run `build.ps1` from the repo root (needs `rpfm_cli.exe` at `C:\dev\gaming\rpfm\rpfm_cli.exe`; edit the path at the top of `build.ps1` if yours differs). It builds `dist\donation_army.pack` and installs it.
2. Enable `donation_army.pack` in the Total War launcher's mod list.

## Mod config

Edit `mod/script/campaign/mod/donation_army_config.lua`, then rebuild with `build.ps1`.

| Key | Meaning |
| --- | --- |
| `queue_file` | Queue file name, relative to the WH3 install folder (default `donation_army_queue.txt`). Must match the app's `queuePath`. |
| `poll_interval_ms` | How often the mod checks the queue file (default 10000, i.e. 10 seconds). |
| `spawn_distance` | Spawn distance from the anchor (default 5). |
| `tiers` | List of tiers. The tier with the highest `min_usd` that a donation meets wins. |

Each tier has: `name`, `min_usd`, `faction`, `subtype` (the general), `xp_ranks`, and `units` (at most 19 besides the general). Valid keys are in the game's DB tables `main_units_tables` (units), `agent_subtypes_tables` (subtypes) and `factions_tables` (factions). Open `db.pack` in RPFM and export them as TSV; dropping them at the repo root keeps them out of git (`*.tsv` is gitignored).

Default tiers, all Chaos rebels (`wh_main_chs_chaos_rebels`): $5 Warband, $20 Horde, $50 Doomstack.

## Streamer setup

Get your Streamlabs socket token: Streamlabs account, Settings, API Settings, API Tokens, copy "Your Socket API Token" (the path may differ slightly). Treat it like a password; it only goes in `app/config.local.json`, which is gitignored.

## Run the app

```
cd app
npm install
copy config.example.json config.local.json   # then edit it
npm start
```

App config keys (`app/config.local.json`):

| Key | Meaning |
| --- | --- |
| `socketToken` | Your Streamlabs socket API token. Never logged. |
| `queuePath` | Full path to the queue file; must be in the WH3 install folder (where `Warhammer3.exe` is). In JSON, Windows paths need doubled backslashes (`C:\\Games\\...`) or forward slashes. |
| `currencyRates` | Map of currency code to USD rate, used to convert non-USD donations. Unknown currencies are treated as USD. |
| `acceptTestAlerts` | If true, Streamlabs test alerts are queued too (each gets a unique id). Set to `false` for live streams, or dashboard test alerts will spawn armies. |
| `logRawEvents` | If true, prints every raw Streamlabs event (may include donor messages). |

## Testing

- `python -m pytest` (repo root): Lua mod tests.
- `cd app && npm test`: companion app tests.
- `cd app && npm run fake -- Bob 20`: append a fake $20 donation from Bob to the queue.
- Streamlabs dashboard "Test Alert" with the app running (needs `acceptTestAlerts: true`).
- In-game smoke test: copy `tools/console/smoke.lua` to the game folder as `exec.lua`, then type `e` in PJ's Console mod.

## Limits

- Donations made while the app is off are lost.
- A new campaign skips donations queued before it started.
- Loading an older save may re-spawn armies already spawned in a later save.
- The queue file lives in the game folder.
