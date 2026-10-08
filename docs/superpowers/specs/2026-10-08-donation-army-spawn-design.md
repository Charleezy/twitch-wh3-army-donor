# Donation → Army Spawn (WH3) — Design Decisions

Status: design approved, awaiting implementation plan. Last updated 2026-10-08.

## Goal
A streamer's viewers donate; the streamer's Total War: Warhammer 3 campaign spawns an
enemy army near them. Requested by a streamer who currently has no donation service set up.

## Prior art
- CA's official Twitch integration: chat votes on dilemmas + unit renaming only. No spawning.
- OnePitchMan reportedly has a chat-spawns-armies mod — not found publicly (Workshop, Reddit,
  YouTube). Possibly private/third-party. Worth asking him/his Discord directly.
- No public Total War Twitch/donation spawn mod found (Crowd Control has no TW integration).

## Decisions
| # | Topic | Decision | Notes |
|---|-------|----------|-------|
| 1 | Trigger source | **Donations via Streamlabs** (Socket API) | Covers PayPal/off-platform tips; Streamlabs also relays Bits/subs. Free. "Test Alert" buttons fire fake donations → test without real money. Dev tests on own channel; streamer later sets up Streamlabs and pastes their own Socket API token. |
| 2 | Not doing (for now) | Real Twitch Extension panel; direct Twitch EventSub | Extension needs hosted backend + Twitch review. Could layer on later — game mod is unaffected. |
| 3 | Amount → army | **Fixed tiers** (e.g. $5 warband / $20 full stack / $50 elite) | Tier thresholds + unit lists in an editable config file. |
| 4 | Allegiance | **Hostile to the player** | Friendly armies = possible later addition (so donors who want to help don't feel bad). |
| 5 | Owning faction | **Configurable per tier**: `rebels` or an invasion/crisis faction key | Rebels: familiar, spawn near settlements like low-control rebellions. Invasion/crisis factions: likely all techs unlocked + buffs. Test both in-game. |
| 6 | Flavour | Army's general named after the donor | Cheap, high chat value. |
| 7 | Architecture | **Mod + small companion app (Node)** | WH3 Lua has file IO but no networking, so the app receives Streamlabs events and writes a queue file; the mod does all game-side work. Node because the Streamlabs Socket API is socket.io. |
| 8 | Spawn location | Fallback chain: **faction leader** (their army, or their position if not leading one) → **strongest player army** (most units, tie-break general rank) → **capital** → **any owned settlement** → player has no armies and no settlements: **drop the entry** (mark handled, log it) | Still apply a minimum distance to reduce same-turn attacks. |
| 9 | Spawn timing | **Start of the player's next turn, with a warning when the donation arrives** | Avoids mid-battle/mid-menu weirdness; warning (in-game event message naming donor + tier) builds anticipation on stream. Removes the need for real-time timers in the mod — the queue file can be read on turn start, and polled only for the warning. |

| 10 | Caps | **No cap** — every queued donation spawns at next turn start | 20 × $5 = 20 armies, by design. |

## Reference data (repo root, RPFM TSV exports)
- `main_units_tables.tsv` — unit keys for army unit lists.
- `agent_subtypes_tables.tsv` — general subtypes.
- `faction_tables.tsv` — faction keys, incl. per-culture `*_rebels` (e.g. `wh2_main_skv_skaven_rebels`).

## Proven game API (from PJ's Console, `pj_console.pack`, Workshop 2791241084)
The user has used its `spawn`, `au`, `add axp` commands successfully in WH3. Its Lua calls:
- `cm:create_force_with_general(faction, units_csv, region_key, x, y, "general", subtype, "", "", "", "", false, callback)`
- `cm:find_valid_spawn_location_for_character_from_character(faction, char_lookup_str, true, 1)` and
  `..._from_settlement(faction, region_key, false, true, 1)`
- `cm:grant_unit_to_character(char_lookup_str, unit_key)`
- `cm:add_experience_to_units_commanded_by_character(char_lookup_str, ranks)`
- Custom effect bundles from script: `cm:create_new_custom_effect_bundle(key)`,
  `bundle:set_effect_value(effect, value)`, `bundle:set_duration(-1)`,
  `cm:apply_custom_effect_bundle_to_faction / _to_characters_force(...)`
- `io.open` used to write files.
Still unknown: renaming the spawned general to the donor's name (needs a rename call in the callback).

## Sub-project B: viewer-count buff (requested later, separate)
Buff AI/enemy unit stats based on live Twitch viewer count (streamer has ~90 Twitch viewers;
YouTube excluded as too hard to integrate). Rough target: ~90 viewers → ~+90% HP.
- Companion app polls Twitch Helix `GET /streams` for `viewer_count` (needs a Twitch app client
  ID/secret) and writes it to a file.
- Mod reads it and applies a script-built custom effect bundle (proven pattern above) to AI factions,
  rescaled each turn.
- Open: exact formula + cap, which factions (all AI vs. only those at war with the player),
  which stats (HP only?), and the effect key for unit HP.
- Shares the companion app and file bridge with the spawn feature; build after the spawn feature.

## Design (approved 2026-10-08)

### Companion app (Node, streamer's PC, CLI)
- Connects to Streamlabs Socket API; token from a local, gitignored config file.
- Per donation: normalise amount to USD (Streamlabs supplies currency), pick the highest tier met;
  below the lowest tier → ignored (logged).
- Appends `{id, donor, amount, tier}` to a queue file the game reads. Donation `id` dedupes reconnects.
- Logs to console. Auto-reconnects; donations during downtime are lost (no replay) → logged warning.

### WH3 mod (campaign Lua)
- Config: a Lua tiers file — min amount, owning faction (rebels or invasion key), general subtype,
  unit list, optional XP ranks. Editable by the user.
- Warning: short real-time poll of the queue during the player's turn; new entries → event message
  ("Bob ($20) has summoned a Warband — it arrives next turn").
- Spawn: at player turn start, every pending entry spawns via the decision-8 fallback chain;
  declare war on the player if needed; rename general to donor; apply XP.
- Handled IDs persisted in the save → no double spawns across save/load or restart.

### Error handling
- Player has no armies and no settlements → entry dropped (marked handled, logged); no spawn.
- Candidates exist but no valid spot found near any of them → keep queued, retry next turn.
- Bad unit/subtype key in config → logged, no crash.

### Testing
- App: unit tests for amount→tier mapping; Streamlabs "Test Alert" end-to-end on the dev's channel.
- Mod: dev command that appends a fake queue entry; verify in-game (PJ's Console to skip turns).

### Out of scope for v1
Friendly armies, viewer-count buff (sub-project B), real Twitch Extension.

## Known risks / issues
- Armies that spawn and attack immediately (true of rebels, likely of any spawn). Mitigation
  ideas: spawn at a minimum distance from player armies/settlements, or a grace period. Undecided.
- Queue must survive save/load and game restarts without double-spawning or losing donations.

## Open questions
- How the streamer installs/runs the bridge.
- Specific invasion faction keys (check wh3-ultimate-endgame-mod for the pattern it uses).
