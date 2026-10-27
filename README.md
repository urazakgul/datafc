# datafc v2.10.0

Football data from **Sofascore**, **ClubElo**, **eloratings.net** (Elo since 1872) and **tff.org** (Turkish federation) as pandas DataFrames. 60 functions total, each with an async mirror under `datafc.aio`, optional `DiskCache`.

```bash
pip install datafc
```

---

## Sofascore — `from datafc import ...`

Grouped by the argument each function needs. Chain them: id → root frame → derived frame.

### Discovery
| Function | Purpose |
| --- | --- |
| `search_data(query, entity_type=None)` | search teams, players, tournaments, managers |
| `seasons_data(tournament_id)` | every season of a tournament |
| `season_rounds_data(tournament_id, season_id)` | defined matchweeks |

### Root (id-driven)
| Function | Purpose |
| --- | --- |
| `standings_data(tournament_id, season_id)` | Total / Home / Away table |
| `match_data(tournament_id, season_id, week_number=None, tournament_type=None, tournament_stage=None)` | fixtures + scores |
| `past_matches_data(...)` | same signature; H2H history per pair |
| `team_match_history_data(team_id)` | full match history for one team |
| `league_player_stats_data(tournament_id, season_id, order='-rating', accumulation='total', fields=None, position=None, max_players=100)` | wide-format player leaderboard |
| `referee_stats_data(referee_id)` | per-tournament career stats |

`tournament_type` ∈ `{"uefa", "world_cup", "league_playoff"}` with matching `tournament_stage` (`group_stage_week`, `round_of_16`, `quarterfinals`, `semifinals`, `final`, …).

### From `standings_df`
| Function | Purpose |
| --- | --- |
| `team_data(standings_df)` | profile, kits, manager, venue |
| `team_stats_data(standings_df, tournament_id, season_id, season=None)` | season team stats (long) |
| `team_transfers_data(standings_df)` | team transfer log |
| `player_stats_data(standings_df, tournament_id, season_id)` | top players per team |
| `squad_data(standings_df)` | full roster |
| `upcoming_matches_data(standings_df)` | upcoming fixtures |

### From `match_df`
| Function | Purpose |
| --- | --- |
| `match_details_data` | referee + venue |
| `formations_data` | formation strings |
| `match_stats_data` | team stats per match |
| `match_odds_data` | 1/X/2 odds |
| `match_h2h_data` | head-to-head record |
| `momentum_data` | minute-by-minute momentum |
| `pregame_form_data` | last-5 form, rating, position, market value |
| `shots_data` | every shot (xG, xGOT, body part, situation) |
| `lineups_data` | XI + subs + per-match player stats |
| `substitutions_data` | substitutions |
| `incidents_data` | goals, cards, VAR |
| `average_positions_data` | average pitch position (X/Y) |
| `goal_networks_data` | coordinates for every action in a goal sequence |

### From `lineups_df`
| Function | Purpose |
| --- | --- |
| `coordinates_data(lineups_df)` | touch heatmap per player |
| `rating_breakdown_data(lineups_df)` | every pass / dribble / defensive action / ball-carry with start-end coordinates and outcome flags |

### From `squad_df`
| Function | Purpose |
| --- | --- |
| `player_data` | profile |
| `player_attribute_overviews_data` | radar attributes + baselines |
| `player_transfers_data` | transfer history |
| `player_career_stats_data` | season-by-season career stats |
| `player_national_team_data` | international career |
| `player_match_log_data` | match-by-match in-game stats (wide) |

---

## ClubElo — `from datafc import clubelo`

Club names use ClubElo spelling (`Man City`, `Real Madrid`, `Paris SG`).

| Function | Purpose |
| --- | --- |
| `daily_ranking_data(date)` | full ranking on a calendar day (`"YYYY-MM-DD"` or `date`) |
| `club_history_data(club)` | Elo history for one club (pre-1960 values are provisional) |
| `fixtures_data()` | probability grid for upcoming matches |

---

## EloRatings — `from datafc import eloratings`

Country arguments are page slugs (`Czech_Republic`, `United_States`).

| Function | Purpose |
| --- | --- |
| `world_ranking_data()` | current national-team ranking |
| `country_matches_data(country)` | full international match history |
| `country_codes_data()` | code → country |
| `tournament_codes_data()` | code → tournament |
| `tournament_editions_data()` | edition list with dates + slugs |
| `tournament_groups_data()` | subcode → group code (e.g. WC qualifiers → `WQT`) |
| `teams_data()` | legacy country code → ISO |

---

## TFF — `from datafc import tff`

Süper Lig, 1. Lig, 2. Lig, 3. Lig.

### Discovery / league
| Function | Purpose |
| --- | --- |
| `fixtures_data(page_id, week=None, group=None, playoff=False, round=None, stage=None)` | weekly fixtures or play-off bracket (`stage` picks a stage group, e.g. Süper Lig 2011/12 Süper Final) |
| `standings_data(page_id, week, group=None, stage=None)` | league table (`group` required for 2. Lig / 3. Lig; `stage` picks a play-off table, e.g. Süper Lig 2011/12) |
| `team_data(club_id)` | club profile |

### From `match_id`
| Function | Purpose |
| --- | --- |
| `match_details_data` | teams, score, officials |
| `match_lineups_data` | XI + bench |
| `match_staff_data` | head coaches |
| `match_goals_data` | goals with type (`F`/`H`/`P`/`K`/`KG`) |
| `match_cards_data` | bookings (yellow / red / second_yellow) |

### From `player_id`
| Function | Purpose |
| --- | --- |
| `player_data` | profile (licence, current club) |
| `player_career_data` | licence history |
| `player_national_matches_data` | national-team appearances |
| `player_goals_data` | every recorded goal |
| `player_matches_data(player_id, season)` | club matches in a season (`"2025-2026"`) |
| `player_cards_data(player_id, season)` | bookings in a season |

---

## Async

Every function has a mirror in `datafc.aio` with the same signature:

```python
import asyncio
from datafc import aio

async def main():
    tasks = [aio.match_data(52, 63814, week_number=w) for w in range(1, 39)]
    return await asyncio.gather(*tasks, return_exceptions=True)

asyncio.run(main())
```

## Cache

```python
from datafc import DiskCache

cache = DiskCache(cache_dir=".datafc_cache", ttl_hours=24)
```

Pass `cache=cache` to any function. `ttl_hours=0` disables expiry; `cache.clear()` empties it.

## Exceptions

`DataFCError` (base), `InvalidParameterError`, `APIError`, `RateLimitError`, `ServerError`, `DataNotAvailableError`.
