# WH3 Donation Army Spawn

A Total War: WARHAMMER III campaign mod plus a small companion app. When a viewer donates through Streamlabs, the app appends the donation to a queue file in the game folder. The mod polls that file, warns you as soon as a donation is seen, and at your next turn start spawns a hostile army of a random race, with a random lord and possibly heroes, near you. Armies are spawned as CA invasions (the game's `invasion_manager`): they march at and attack your faction leader (or your strongest army, or your capital if neither is available), are upkeep-free and immune to regionless attrition. Bigger donations spawn bigger, higher-tier, more experienced armies; every donation that meets the lowest tier spawns (no cap).

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
| `army_effect_bundle` | Effect bundle applied to every spawned army for its lifetime (default `wh2_dlc16_bundle_military_upkeep_free_force_immune_to_regionless_attrition`, which removes upkeep and regionless attrition). Set to `""` to disable. |
| `turn_tier_bonus` | List of `{ turn, tiers }`. From that turn on, every donation spawns that many tiers higher (tiers ordered by `min_usd`), capped at the top tier; the entry with the highest `turn` reached applies. Donations below the lowest tier are still ignored. Default `{ turn = 5, tiers = 1 }, { turn = 30, tiers = 2 }`; set to `{}` to disable. |
| `tiers` | List of `{ name, min_usd, difficulty, min_turn }`. The tier with the highest `min_usd` that a donation meets wins; `difficulty` names an entry of `difficulties`. `min_turn` is optional: before that campaign turn the tier does not exist (it is skipped by the base pick and by the `turn_tier_bonus` cap). |
| `races` | Races an army may be rolled from, as roster keys (e.g. `{ "chs", "skv", "emp" }`). `nil` (default) allows every race in `donation_army_rosters.lua`. |
| `difficulties` | Army generation settings per difficulty (see below). |

### Default tiers

| Tier | Donation | Difficulty | Unit tiers | Min unit cost | Army size (incl. lord) | Unit xp | Lord level | Heroes | Available |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Warband | any amount under $20 | `easy` | 1-2 | none | 6-8 | 1-3 | 5-10 | none | always |
| Horde | $20+ | `medium` | 1-3 | none | 14-16 | 3-5 | 10-15 | 0-1 | always |
| Doomstack | $50+ | `hard` | 1-5 | 500 | 17-20 | 5-7 | 15-20 | 0-2 | always |
| Apocalypse | $100+ | `apocalypse` | 3-5 | 750 | 19-20 | 7-9 | 25-30 | 1-2 | from turn 30 |

What a donation spawns, by campaign turn (`turn_tier_bonus`: +1 tier from turn 5, +2 from turn 30, capped at the highest tier available that turn):

| Donation | Turns 1-4 | Turns 5-29 | Turn 30+ |
| --- | --- | --- | --- |
| under $20 | Warband | Horde | Doomstack |
| $20-49 | Horde | Doomstack | Apocalypse |
| $50-99 | Doomstack | Doomstack | Apocalypse |
| $100+ | Doomstack | Doomstack | Apocalypse |

The warning popup names the tier for the turn the donation arrives; the spawn re-checks the tier on the turn it spawns, so a donation seen on turn 4 can arrive a tier bigger on turn 5.

### How armies are generated

Each spawn rolls a random race from `races` (only races whose faction exists in the campaign; the mod logs the others at startup), then builds an army from that race's roster:

- A random lord of the race (generic lords only, no legendary lords), plus a random number of heroes, which join the army. Lords and heroes are picked by type first, then by lore: every lore variant of a caster (e.g. the nine high elf archmage lores) counts as one type (a lore-variant caster is one choice among the race's lord types, not one choice per lore). Heroes are drawn from different types when possible.
- A unit is eligible only if its tier is in the difficulty's range and its gold cost (multiplayer cost, from the generated rosters) is at least the difficulty's `min_unit_cost`. When a role has no eligible units in the range, that role's range widens by one tier.
- An infantry core (random melee and missile infantry counts, filled only as far as eligible units allow: e.g. Ogres have no missile infantry costing 750+; when melee infantry runs out, the melee core is filled from monstrous infantry instead, so Ogres get Ironguts and Maneaters), then weighted random roles with eligible units (cavalry, monstrous infantry/cavalry, war beasts, chariots, war machines, monsters) until the army reaches a random size. Ogres favour monstrous infantry. When every role is at its cap, infantry and monstrous infantry fill the rest. War machines, monsters and Regiments of Renown never appear twice; other units may repeat.
- If the army still can't fill, the cost floor drops by 200 gold (never below 0) and the tier range widens down by one, step by step until it fills (e.g. Bretonnia, with no infantry above tier 2, at Apocalypse).

Each `difficulties` entry has `tiers` (unit tier range, 1-5), `min_unit_cost` (gold; cheaper units are left out, see above), `min_units`/`max_units` (army size including lord and heroes, at most 20), `unit_xp` (range of ranks for the invasion manager's `add_unit_experience`), `lord_level` (range; the general's rank is set to exactly the rolled level with `cm:character_details_set_rank` when the army appears), and `limits`: per role `{ min, max }` (`hero`, `melee_infantry`, `missile_infantry`, `melee_cavalry`, `missile_cavalry`, `monstrous_infantry`, `monstrous_cavalry`, `war_beast`, `chariot`, `warmachine`, `monster`, `generic`). Infantry min/max set the core; other roles only use max. Defaults:

| Difficulty | Unit tiers | Min unit cost | Size | Unit xp | Lord level | Heroes | Chariot / war machine / monster |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `easy` | 1-2 | 0 | 6-8 | 1-3 | 5-10 | 0 | none |
| `medium` | 1-3 | 0 | 14-16 | 3-5 | 10-15 | 0-1 | at most 1 each |
| `hard` | 1-5 | 500 | 17-20 | 5-7 | 15-20 | 0-2 | at most 1 each |
| `apocalypse` | 3-5 | 750 | 19-20 | 7-9 | 25-30 | 1-2 | at most 1 each |

Rosters live in `mod/script/campaign/mod/donation_army_rosters.lua`, generated from `tools/data/land_encounters_factions_data.lua` (vanilla units, lords and heroes only, with each unit's gold cost). Each race spawns as its quest-battle faction (e.g. `wh_main_chs_chaos_qb1`, `wh2_main_skv_skaven_qb1`); all 23 exist in Immortal Empires. A few units the source data files under an unfitting role are moved by `ROLE_OVERRIDES` in `tools/gen_rosters.py` (e.g. Ogre Gorgers count as monstrous infantry, not melee infantry). Do not edit the rosters file by hand: change the data or `tools/gen_rosters.py`, then regenerate with `python tools/gen_rosters.py` (a test fails if the committed file drifts). The generator always drops special units by name (`_boss` Monster Hunt units, `_grudge_unit`, `_driver`, quest-battle `_qb` copies; patterns in `EXCLUDED_NAME_PATTERNS`) and, when the RPFM exports `main_units_tables.tsv` and `agent_subtypes_tables.tsv` are at the repo root, any unit, lord or hero key missing from them (it prints what it dropped). Regenerate with those exports present, since the committed file is the validated output (the drift test skips without `main_units_tables.tsv`). Unit, subtype and faction keys are in the game's DB tables `main_units_tables`, `agent_subtypes_tables` and `factions_tables` (export them from `db.pack` with RPFM; `*.tsv` at the repo root is gitignored).

Army rosters and composition rules adapted from Land Encounters and Points of Interest (Steam Workshop).

## Streamer setup

Get your Streamlabs socket token: in the Streamlabs dashboard go to **Settings → API Settings → API Tokens** ([streamlabs.com/dashboard#/settings/api-settings](https://streamlabs.com/dashboard#/settings/api-settings)) and copy **Your Socket API Token**, the second, longer token (a few hundred characters, starts with `eyJ`). Not "Your API Access Token" above it: that short one makes the app fail with `Socket error: Authentication error`. Treat it like a password; it only goes in `app/config.local.json`, which is gitignored.

![Streamlabs API Tokens page: use "Your Socket API Token"](docs/images/streamlabs-guide.png)

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

- `python -m pytest` (repo root): Lua mod tests, plus a check that the committed rosters match `python tools/gen_rosters.py`.
- `cd app && npm test`: companion app tests.
- `cd app && npm run fake -- Bob 20`: append a fake $20 donation from Bob to the queue.
- Streamlabs dashboard "Test Alert" with the app running (needs `acceptTestAlerts: true`).
- In-game smoke test: copy `tools/console/smoke.lua` to the game folder as `exec.lua`, then type `e` in PJ's Console mod. `tools/console/spawn_probe.lua` is the same kind of probe for spawn-spot lookups and `create_force_with_general` per faction key. `tools/console/invasion_probe.lua` spawns an invasion-manager army that hunts your faction leader, the same sequence the mod uses. `tools/console/race_probe.lua` reports which per-race `_qb1` factions exist and spawns one Skaven invasion with a hero embedded via `create_agent` + `embed_agent_in_force`.

## Limits

- Donations made while the app is off are lost.
- A new campaign skips donations queued before it started.
- Loading an older save may re-spawn armies already spawned in a later save.
- The queue file lives in the game folder.
