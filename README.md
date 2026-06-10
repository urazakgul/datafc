# datafc v2.7.0

## Overview

`datafc` fetches, processes, and exports structured football data. It provides **45 functions** covering tournament metadata, standings, squad rosters, match fixtures, shots, lineups, player heatmaps, odds, club & national-team Elo ratings, and more — all returning clean `pandas` DataFrames ready for analysis. Sofascore, ClubElo, and eloratings.net are the supported data sources.

> **Finding IDs:** `tournament_id` and `season_id` can be discovered two ways:
> - **From the URL:** navigating to a league page on Sofascore (e.g. `sofascore.com/.../trendyol-super-lig/52#id:63814`) shows `tournament_id=52` and `season_id=63814`.
> - **Programmatically:** use `search_data("super lig", entity_type="tournament")` to find the tournament ID, then `seasons_data(tournament_id)` to list all available seasons.

---

<p align="center">
  If you find <strong>datafc</strong> useful, consider supporting the project ☕<br><br>
  <a href="https://buymeacoffee.com/urazdev">
    <img src="https://img.shields.io/badge/Buy%20Me%20A%20Coffee-urazdev-%23FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me A Coffee">
  </a>
</p>

---

## What Data Can You Access?

### Discovery

| Function | What it returns |
|---|---|
| `search_data` | Search for players, teams, tournaments, or managers by name |
| `seasons_data` | All seasons and their IDs for a given tournament |

### Tournament / Season Metadata

| Function | What it returns |
|---|---|
| `season_rounds_data` | All rounds/matchweeks in a season |

### League / Season

| Function | What it returns |
|---|---|
| `standings_data` | League table (Total, Home, Away) with W/D/L, goals, points |
| `team_data` | Team profiles: stadium, kit colors, manager, venue capacity |
| `team_stats_data` | 100+ season-level stats per team |
| `team_transfers_data` | All incoming and outgoing transfers per team |
| `player_stats_data` | Top player stats per team (goals, assists, key passes, …) |
| `squad_data` | Squad roster with age, height, market value, contract expiry |
| `upcoming_matches_data` | Upcoming fixtures for all teams in the standings |
| `team_match_history_data` | Full match history for a team across all competitions |
| `league_player_stats_data` | Wide-format player rankings, sortable by any metric |

### Matchweek

| Function | What it returns |
|---|---|
| `match_data` | Fixtures for a matchweek: score, status, home/away teams |
| `match_details_data` | Referee info (name, cards, games) and venue details per match |
| `formations_data` | Home and away formation for each match |
| `match_stats_data` | Aggregate team stats per match (possession, shots, fouls, …) |
| `match_odds_data` | Pre-match 1/X/2 betting odds |
| `match_h2h_data` | All-time H2H record between the two teams |
| `momentum_data` | Minute-by-minute momentum score throughout the match |
| `pregame_form_data` | Last 5 results, avg rating, league position, and squad value before each match |
| `shots_data` | Every shot: coordinates, xG, xGOT, outcome, body part |
| `lineups_data` | Starting XI and substitutes with per-match player stats |
| `substitutions_data` | Substitution events: minute, player in, player out |
| `incidents_data` | Goals, cards, and VAR decisions per match |
| `average_positions_data` | Average pitch position (x/y) per player |
| `coordinates_data` | Heatmap touch coordinates per player (requires `lineups_data` output) |
| `goal_networks_data` | Goal-sequence coordinates (passes, shots, goalkeeper position) |
| `past_matches_data` | Historical H2H results for team pairs in a given matchweek |

### Player

| Function | What it returns |
|---|---|
| `player_data` | Player profile: age, nationality, height, market value |
| `player_attribute_overviews_data` | Radar attribute snapshots (attacking, technical, tactical, defending, creativity) per player and position average |
| `player_transfers_data` | Transfer history per player |
| `player_career_stats_data` | Season-by-season career stats across all competitions (long format) |
| `player_national_team_data` | National team appearances, goals, and debut date |
| `player_match_log_data` | Match-by-match in-game statistics across all recorded matches |

### Referee

| Function | What it returns |
|---|---|
| `referee_stats_data` | Career stats for a referee: games, cards, and per-game averages |

### ClubElo

| Function | What it returns |
|---|---|
| `clubelo.daily_ranking_data` | Full ClubElo ranking for a given calendar day (since 1939) |
| `clubelo.club_history_data` | Complete Elo rating history for a single club |
| `clubelo.fixtures_data` | Per-goal-difference and exact-result probabilities for upcoming matches |

### EloRatings (national teams)

| Function | What it returns |
|---|---|
| `eloratings.world_ranking_data` | Current global Elo ranking for all national teams |
| `eloratings.country_matches_data` | Complete international match history for a national team |
| `eloratings.country_codes_data` | Country code → English country name reference |
| `eloratings.tournament_codes_data` | Tournament code → English tournament name reference |
| `eloratings.tournament_editions_data` | Every tournament edition with start/end dates and page slug |
| `eloratings.tournament_groups_data` | Specific tournament code → broader group code (e.g. all WC qualifier variants → `WQT`) |
| `eloratings.teams_data` | Legacy/historical country code → ISO code mapping |

> **Coverage:** Any league and season available on Sofascore. For Turkey Super Lig, every season from 1980/81 to the present is accessible.

## Installation

```bash
pip install datafc
```

To install the latest development version:

```bash
pip install git+https://github.com/urazakgul/datafc.git
```

To upgrade an existing installation:

```bash
pip install --upgrade datafc
```

## Quick Start

```python
from datafc import (
    standings_data,
    match_data,
    shots_data,
    league_player_stats_data,
)

standings_df = standings_data(tournament_id=52, season_id=77805)

match_df = match_data(tournament_id=52, season_id=77805, week_number=1)

shots_df = shots_data(match_df=match_df)


top_scorers = league_player_stats_data(
    tournament_id=52,
    season_id=77805,
    order="-goals",
    fields=["goals", "assists", "rating"],
    max_players=20,
)
```

## Async API

All functions are also available in async form via `datafc.aio`, designed for fetching multiple weeks or matches in parallel with `asyncio.gather()`.

```python
import asyncio
import pandas as pd
from datafc import aio

async def fetch_full_season(tournament_id, season_id, total_weeks):
    tasks = [
        aio.match_data(tournament_id, season_id, week_number=w)
        for w in range(1, total_weeks + 1)
    ]
    frames = await asyncio.gather(*tasks)
    return pd.concat(frames, ignore_index=True)

df = asyncio.run(fetch_full_season(52, 63814, total_weeks=38))
```

Use `return_exceptions=True` when mixing independent coroutines so that one failure does not cancel the rest:

```python
results = await asyncio.gather(
    aio.match_data(52, 77805, week_number=1),
    aio.standings_data(52, 77805),
    return_exceptions=True,
)
for label, result in zip(["match", "standings"], results):
    if isinstance(result, Exception):
        print(f"{label} failed: {result}")
```

Async functions accept the same parameters as their sync counterparts, including `cache`, `enable_json_export`, `enable_excel_export`, and `output_dir` (see [Caching](#caching) and [Common Parameters](#common-parameters)).

## Common Parameters

Every function accepts the following shared parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data_source` | `str` | `"sofascore"` | Data source: `"sofascore"` or `"sofavpn"` (use `sofavpn` if Sofascore is blocked in your region) |
| `rate_limit` | `float` | `2.0` | Maximum requests per second. The limit is **global across all instances** in the same process (sync) or event loop (async) — creating multiple clients does not multiply throughput. |
| `cache` | `DiskCache` | `None` | Optional `DiskCache` instance for persistent response caching (see [Caching](#caching)). |
| `enable_json_export` | `bool` | `False` | Save output as a JSON file |
| `enable_excel_export` | `bool` | `False` | Save output as an Excel file |
| `output_dir` | `str` | `"."` | Directory for exported files |

## Caching

Responses can be cached to disk to avoid redundant API calls across sessions:

```python
import asyncio
from datafc import DiskCache
from datafc import aio

cache = DiskCache(cache_dir=".datafc_cache", ttl_hours=24)

async def main():
    # First call hits the API; subsequent calls read from disk
    df = await aio.match_data(52, 63814, week_number=1, cache=cache)

asyncio.run(main())
```

`DiskCache` stores responses as JSON files keyed by URL. Cache entries expire after `ttl_hours` (set to `0` to disable expiry). Call `cache.clear()` to invalidate all entries.

## Parquet Export

For large datasets (`player_career_stats_data`, `coordinates_data`, `lineups_data`), Parquet is significantly faster to read and write than JSON. Use `save_parquet` directly on any DataFrame returned by a fetch function:

```python
from datafc import player_career_stats_data, standings_data, squad_data, save_parquet

standings_df = standings_data(52, 63814)
squad_df = squad_data(standings_df=standings_df)
df = player_career_stats_data(squad_df=squad_df)

save_parquet(
    data=df,
    fn_name="player_career_stats_data",
    data_source="sofascore",
    country="Turkey",
    tournament="Trendyol Super Lig",
    season="25/26",
    output_dir="data/processed",
)
```

Parquet export requires `pyarrow`. Install it with:

```bash
pip install datafc[parquet]
# or
pip install pyarrow
```

## Exception Hierarchy

```
DataFCError
├── InvalidParameterError   (bad input: unknown data_source, invalid category, etc.)
├── DataNotAvailableError   (valid request but no data returned)
└── APIError                (HTTP-level error from the Sofascore API)
    ├── RateLimitError      (HTTP 429)
    └── ServerError         (HTTP 5xx)
```

```python
from datafc import match_data, DataNotAvailableError, RateLimitError

try:
    df = match_data(52, 63814, week_number=99)
except DataNotAvailableError:
    print("No data for that week.")
except RateLimitError:
    print("Rate limited. Lower your rate_limit or add delays.")
```

## Function Reference

### Discovery

#### `search_data`

Search for teams, players, tournaments, or managers by name. Useful for finding IDs without visiting the website.

```python
from datafc import search_data

df = search_data("galatasaray", entity_type="team")
```

Parameters:

- `query` (str): Search term.
- `entity_type` (str, optional): Filter by type: `"team"`, `"player"`, `"tournament"`, or `"manager"`. `None` returns all types.

Columns: `entity_id`, `entity_name`, `entity_type`, `score`, `country`, `position`.

---

#### `seasons_data`

List all available seasons for a tournament. Use this to discover valid `season_id` values before calling other functions.

```python
from datafc import seasons_data

df = seasons_data(tournament_id=52)
```

Columns: `tournament_id`, `season_id`, `season_name`, `season_year`.

---

### Tournament / Season Metadata

#### `season_rounds_data`

Fetch all rounds (matchweeks) defined for a season. Useful for iterating over all weeks programmatically.

```python
from datafc import season_rounds_data

df = season_rounds_data(tournament_id=52, season_id=77805)
```

Columns: `tournament_id`, `season_id`, `round_number`, `slug`, `name`, `prefix`, `is_latest`.

---

### League / Season

#### `standings_data`

Fetch league standings for Total, Home, and Away categories.

```python
from datafc import standings_data

df = standings_data(tournament_id=52, season_id=77805)
```

Columns: `country`, `tournament`, `tournament_id`, `season_id`, `team_name`, `team_id`, `position`, `matches`, `wins`, `draws`, `losses`, `scores_for`, `scores_against`, `points`, `category` (`Total` / `Home` / `Away`).

---

#### `team_data`

Fetch profile and infrastructure data for every team in the standings: stadium name and capacity, kit colors, and current manager.

```python
from datafc import standings_data, team_data

standings_df = standings_data(52, 63814)
df = team_data(standings_df=standings_df)
```

Columns: `country`, `tournament`, `team_id`, `team_name`, `short_name`, `slug`, `national`, `country_name`, `country_id`, `primary_color`, `secondary_color`, `text_color`, `venue_id`, `venue_name`, `venue_capacity`, `venue_city`, `manager_id`, `manager_name`, `manager_country`.

Dependencies: `standings_data`

---

#### `team_stats_data`

Fetch season-level team statistics (long format) for every team in the standings.

```python
from datafc import standings_data, team_stats_data

standings_df = standings_data(52, 63814)
df = team_stats_data(standings_df=standings_df, tournament_id=52, season_id=77805)
```

Parameters:

- `standings_df` (DataFrame): Output of `standings_data`.
- `tournament_id` (int)
- `season_id` (int)
- `season` (str, optional): Human-readable season label (e.g. `"24/25"`) used only in the export filename.

Columns: `country`, `tournament`, `team_name`, `team_id`, `stat`, `value`.

Dependencies: `standings_data`

---

#### `team_transfers_data`

Fetch all incoming and outgoing transfer records for every team in the standings.

```python
from datafc import standings_data, team_transfers_data

standings_df = standings_data(52, 63814)
df = team_transfers_data(standings_df=standings_df)
```

Columns: `country`, `tournament`, `team_name`, `team_id`, `direction` (`in` / `out`), `player_id`, `player_name`, `transfer_date`, `from_team_id`, `from_team_name`, `to_team_id`, `to_team_name`, `transfer_type` (`loan` / `permanent` / `free` / `end_of_contract`), `fee`, `fee_currency`.

Dependencies: `standings_data`

---

#### `player_stats_data`

Fetch top player statistics per team (long format). Covers goals, assists, key passes, duels, and more.

```python
from datafc import standings_data, player_stats_data

standings_df = standings_data(52, 63814)
df = player_stats_data(standings_df=standings_df, tournament_id=52, season_id=77805)
```

Columns: `country`, `tournament`, `team_name`, `team_id`, `player_name`, `player_id`, `position`, `stat_name`, `stat_value`.

Dependencies: `standings_data`

---

#### `squad_data`

Fetch full squad roster for every team: age, height, nationality, position, preferred foot, contract expiry, and market value.

```python
from datafc import standings_data, squad_data

standings_df = standings_data(52, 63814)
df = squad_data(standings_df=standings_df)
```

Columns: `country`, `tournament`, `tournament_id`, `season_id`, `team_name`, `team_id`, `player_name`, `player_id`, `age`, `height`, `player_country`, `position`, `preferred_foot`, `contract_until`, `market_value`, `market_currency`.

Dependencies: `standings_data`

---

#### `team_match_history_data`

Fetch the complete match history for a single team across all competitions.

```python
from datafc import team_match_history_data

df = team_match_history_data(team_id=4748)  # Brazil
```

The `team_id` can be obtained from `standings_data()`, `squad_data()`, or `search_data()`.

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `home_team`, `home_team_id`, `away_team`, `away_team_id`, `home_score_period1`, `home_score_period2`, `home_score_normaltime`, `home_score_display`, `home_score_current`, `away_score_period1`, `away_score_period2`, `away_score_normaltime`, `away_score_display`, `away_score_current`, `start_timestamp`, `status`.

> **Note:** Results span all competitions in Sofascore's database (league, cup, international). Filter by the `tournament` column to narrow down to a specific competition.

Dependencies: none

---

#### `upcoming_matches_data`

Fetch upcoming fixtures for all teams currently in the standings.

```python
from datafc import standings_data, upcoming_matches_data

standings_df = standings_data(52, 63814)
df = upcoming_matches_data(standings_df=standings_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `home_team`, `home_team_id`, `away_team`, `away_team_id`, `start_timestamp`, `status`.

> **Note:** Results may include fixtures from cup competitions (e.g. Türkiye Kupası) if a team's next scheduled match is outside the league. Filter by the `tournament` column to restrict to league fixtures only.

Dependencies: `standings_data`

---

#### `league_player_stats_data`

Fetch ranked player statistics across the entire league in wide format (one row per player). Supports pagination, position filtering, and multiple accumulation methods.

```python
from datafc import league_player_stats_data

# Top 50 goalscorers
df = league_player_stats_data(
    tournament_id=52,
    season_id=77805,
    order="-goals",
    accumulation="total",
    fields=["goals", "assists", "rating", "expectedGoals"],
    max_players=50,
)

# Top midfielders by rating per 90
df = league_player_stats_data(
    tournament_id=52,
    season_id=77805,
    order="-rating",
    accumulation="per90",
    position="M",
    max_players=20,
)
```

Parameters:

- `order` (str): Field to sort by, prefix with `-` for descending. Default `"-rating"`.
- `accumulation` (str): `"total"`, `"per90"`, or `"perMatch"`. Default `"total"`.
- `fields` (list, optional): Stats columns to include. `None` returns 14 default fields.
- `position` (str, optional): `"G"`, `"D"`, `"M"`, or `"F"`. `None` includes all positions.
- `max_players` (int): Maximum players to return (fetches multiple pages if needed). Default `100`.

Available fields: `goals`, `assists`, `rating`, `expectedGoals`, `expectedAssists`, `goalsAssistsSum`, `penaltyGoals`, `freeKickGoal`, `scoringFrequency`, `totalShots`, `shotsOnTarget`, `bigChancesCreated`, `bigChancesMissed`, `accuratePasses`, `accuratePassesPercentage`, `keyPasses`, `accurateLongBalls`, `accurateLongBallsPercentage`, `successfulDribbles`, `successfulDribblesPercentage`, `tackles`, `interceptions`, `clearances`, `possessionLost`, `yellowCards`, `redCards`, `saves`, `goalsPrevented`, `minutesPlayed`, `appearances`.

Columns: `tournament_id`, `season_id`, `player_name`, `player_id`, `team_name`, `team_id`, + one column per requested field.

---

### Matchweek

#### `match_data`

Fetch match fixtures and scores for a given matchweek.

```python
from datafc import match_data

match_df = match_data(
    tournament_id=52,
    season_id=77805,
    week_number=21,
)

# UEFA tournaments require additional parameters:
ucl_df = match_data(
    tournament_id=7,
    season_id=61644,
    week_number=5,
    tournament_type="uefa",
    tournament_stage="round_of_16",
)

# World Cup knockout stages — week_number not needed:
wc_df = match_data(
    tournament_id=16,
    season_id=58210,
    tournament_type="world_cup",
    tournament_stage="round_of_16",
)

# World Cup group stage — week_number required:
wc_group_df = match_data(
    tournament_id=16,
    season_id=58210,
    week_number=1,
    tournament_type="world_cup",
    tournament_stage="group_stage_week",
)
```

Parameters:

- `tournament_id` (int)
- `season_id` (int)
- `week_number` (int, optional): Required for league rounds, UEFA stages, and `world_cup` + `group_stage_week`. Not needed for other `world_cup` stages.
- `tournament_type` (str, optional): `"uefa"` for UEFA competitions, `"world_cup"` for FIFA World Cup. `None` assumes a domestic league.
- `tournament_stage` (str, optional): Required when `tournament_type` is set.
  - `"uefa"` options: `preliminary_semifinals`, `preliminary_final`, `qualification_round`, `qualification_playoff`, `group_stage_week`, `playoff_round`, `round_of_16`, `quarterfinals`, `semifinals`, `match_for_3rd_place`, `final`.
  - `"world_cup"` options: `group_stage_week`, `round_of_32`, `round_of_16`, `quarterfinals`, `semifinals`, `match_for_3rd_place`, `final`.

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `home_team`, `home_team_id`, `away_team`, `away_team_id`, `injury_time_1`, `injury_time_2`, `start_timestamp`, `status`, `home_score_current`, `home_score_display`, `home_score_period1`, `home_score_period2`, `home_score_normaltime`, `away_score_current`, `away_score_display`, `away_score_period1`, `away_score_period2`, `away_score_normaltime`.

---

#### `match_details_data`

Fetch referee and venue details for each match.

```python
from datafc import match_details_data

df = match_details_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `referee_id`, `referee_name`, `referee_country`, `referee_yellow_cards`, `referee_red_cards`, `referee_games`, `venue_id`, `venue_name`, `venue_city`, `venue_country`, `venue_capacity`.

Dependencies: `match_data`

---

#### `formations_data`

Fetch home and away formation for each match.

```python
from datafc import formations_data

df = formations_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `team` (`home` / `away`), `formation`.

Dependencies: `match_data`

---

#### `match_stats_data`

Fetch aggregate team statistics (possession, shots, passes, etc.) for each match.

```python
from datafc import match_stats_data

df = match_stats_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `period` (`ALL` / `1ST` / `2ND`), `group_name`, `stat_name`, `home_team_stat`, `away_team_stat`.

Dependencies: `match_data`

---

#### `match_odds_data`

Fetch pre-match and live betting odds.

```python
from datafc import match_odds_data

df = match_odds_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `market_name`, `market_id`, `is_live`, `choice_name`, `initial_fractional_value`, `current_fractional_value`, `winning`, `change`.

Dependencies: `match_data`

---

#### `match_h2h_data`

Fetch all-time head-to-head win/draw/loss record between the two teams in each match.

```python
from datafc import match_h2h_data

df = match_h2h_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `home_team`, `away_team`, `home_wins`, `away_wins`, `draws`.

Dependencies: `match_data`

---

#### `momentum_data`

Fetch minute-by-minute match momentum values (positive = home advantage, negative = away).

```python
from datafc import momentum_data

df = momentum_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `minute`, `value`.

Dependencies: `match_data`

---

#### `pregame_form_data`

Fetch pre-game form context for each match: last 5 results, average rating, league position, and squad market value for both the home and away team.

```python
from datafc import pregame_form_data

df = pregame_form_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `team` (`home` / `away`), `avg_rating`, `position`, `value`, `form_1`, `form_2`, `form_3`, `form_4`, `form_5` (most recent result last).

Dependencies: `match_data`

---

#### `shots_data`

Fetch all shot events with coordinates, xG, xGOT, body part, situation, and goal mouth location.

```python
from datafc import shots_data

df = shots_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `player_name`, `player_id`, `player_position`, `is_home`, `incident_type`, `shot_type`, `body_part`, `goal_type`, `situation`, `goal_mouth_location`, `xg`, `xgot`, `player_coordinates_x`, `player_coordinates_y`, `player_coordinates_z`, `goal_mouth_coordinates_x`, `goal_mouth_coordinates_y`, `goal_mouth_coordinates_z`, `draw_start_x`, `draw_start_y`, `draw_end_x`, `draw_end_y`, `draw_goal_x`, `draw_goal_y`, `block_coordinates_x`, `block_coordinates_y`, `block_coordinates_z`, `time`, `time_seconds`, `added_time`.

Dependencies: `match_data`

---

#### `lineups_data`

Fetch player lineup details and per-match player statistics (long format: one row per player per stat).

```python
from datafc import lineups_data

df = lineups_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `team`, `player_name`, `player_id`, `stat_name`, `stat_value`.

Dependencies: `match_data`

---

#### `substitutions_data`

Fetch substitution events with player names and minute.

```python
from datafc import substitutions_data

df = substitutions_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `time`, `player_in`, `player_in_id`, `player_out`, `player_out_id`.

Dependencies: `match_data`

---

#### `incidents_data`

Fetch goal, card, and VAR decision events for each match.

```python
from datafc import incidents_data

df = incidents_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `incident_type`, `incident_class`, `time`, `added_time`, `is_home`, `player_id`, `player_name`, `home_score`, `away_score`, `goal_from`, `card_reason`, `rescinded`, `var_confirmed`.

> **Note on `var_confirmed`:** `True` = VAR reviewed and upheld the on-field decision. `False` = VAR reviewed and overturned the decision. `None` = no VAR review occurred for that incident.

Dependencies: `match_data`

---

#### `average_positions_data`

Fetch each player's average X/Y position on the pitch during a match. Coordinates are on a 0–100 scale. Useful for formation and tactical analysis.

```python
from datafc import average_positions_data

df = average_positions_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `home_team`, `away_team`, `side` (`home` / `away`), `player_name`, `player_id`, `position`, `jersey_number`, `average_x`, `average_y`, `points_count`.

Dependencies: `match_data`

---

#### `coordinates_data`

Fetch heatmap touch coordinates (X/Y) for each player. Requires `lineups_data` output as input.

```python
from datafc import lineups_data, coordinates_data

lineups_df = lineups_data(match_df=match_df)
df = coordinates_data(lineups_df=lineups_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `team`, `player_id`, `player_name`, `x`, `y`.

> **Note:** Players with no heatmap data (short substitute appearances, 404 or 403 responses) are silently skipped. The function raises `DataNotAvailableError` only if **no** player yields any coordinates.

Dependencies: `lineups_data`

---

#### `goal_networks_data`

Fetch coordinate data for each action in a goal-scoring sequence (passes, shots, goalkeeper position).

```python
from datafc import goal_networks_data

df = goal_networks_data(match_df=match_df)
```

Columns: `country`, `tournament`, `season`, `week`, `game_id`, `player_name`, `player_id`, `event_type`, `player_x`, `player_y`, `pass_end_x`, `pass_end_y`, `is_assist`, `id`, `goalkeeper_x`, `goalkeeper_y`, `goal_shot_x`, `goal_shot_y`, `goal_mouth_x`, `goal_mouth_y`, `goalkeeper_name`, `goalkeeper_id`.

Dependencies: `match_data`

---

#### `past_matches_data`

Fetch the complete head-to-head match history for each team pair playing in a given matchweek.

```python
from datafc import past_matches_data

df = past_matches_data(
    tournament_id=52,
    season_id=77805,
    week_number=21,
)
```

Parameters:

- `tournament_id` (int)
- `season_id` (int)
- `week_number` (int, optional): Required for league rounds, UEFA stages, and `world_cup` + `group_stage_week`. Not needed for other `world_cup` stages.
- `tournament_type` (str, optional): `"uefa"` for UEFA competitions, `"world_cup"` for FIFA World Cup.
- `tournament_stage` (str, optional): Required when `tournament_type` is set. Same options as `match_data`.

Same columns as `match_data`.

---

### Player

#### `player_data`

Fetch profile data for each player in a squad: nationality, date of birth, height, weight, preferred foot, and market value.

```python
from datafc import standings_data, squad_data, player_data

standings_df = standings_data(52, 63814)
squad_df = squad_data(standings_df=standings_df)
df = player_data(squad_df=squad_df)
```

Columns: `player_id`, `player_name`, `date_of_birth`, `age`, `nationality`, `nationality_id`, `height`, `weight`, `preferred_foot`, `jersey_number`, `position`, `position_detailed`, `market_value`, `market_currency`, `team_id`, `team_name`.

Dependencies: `squad_data`

---

#### `player_transfers_data`

Fetch transfer history for each player in a squad.

```python
from datafc import standings_data, squad_data, player_transfers_data

standings_df = standings_data(52, 63814)
squad_df = squad_data(standings_df=standings_df)
df = player_transfers_data(squad_df=squad_df)
```

Columns: `player_id`, `player_name`, `transfer_date`, `from_team_id`, `from_team_name`, `to_team_id`, `to_team_name`, `transfer_type`, `fee`, `fee_currency`.

Dependencies: `squad_data`

---

#### `player_career_stats_data`

Fetch season-by-season career statistics across all competitions for each player in a squad (long format: one row per player-season-stat combination). Only `overall` entries are included; home/away splits are excluded.

```python
from datafc import standings_data, squad_data, player_career_stats_data

standings_df = standings_data(52, 63814)
squad_df = squad_data(standings_df=standings_df)
df = player_career_stats_data(squad_df=squad_df)
```

Columns: `player_id`, `player_name`, `tournament_id`, `tournament_name`, `season_id`, `season_name`, `team_id`, `team_name`, `stat`, `value`.

Dependencies: `squad_data`

---

#### `player_attribute_overviews_data`

Fetch radar attribute overviews (attacking, technical, tactical, defending, creativity) for each player in a squad, including the position-average baseline and previous-year snapshots.

```python
from datafc import standings_data, squad_data, player_attribute_overviews_data

standings_df = standings_data(52, 63814)
squad_df = squad_data(standings_df=standings_df)
df = player_attribute_overviews_data(squad_df=squad_df)
```

Columns: `player_id`, `player_name`, `series` (`'player'` or `'average'`), `position`, `year_shift`, `attacking`, `technical`, `tactical`, `defending`, `creativity`.

Dependencies: `squad_data`

---

#### `player_national_team_data`

Fetch national team career statistics (appearances, goals, debut) for each player in a squad.

```python
from datafc import standings_data, squad_data, player_national_team_data

standings_df = standings_data(52, 63814)
squad_df = squad_data(standings_df=standings_df)
df = player_national_team_data(squad_df=squad_df)
```

Columns: `player_id`, `player_name`, `team_id`, `team_name`, `team_code`, `appearances`, `goals`, `debut_timestamp`.

Dependencies: `squad_data`

---

#### `player_match_log_data`

Fetch match-by-match in-game statistics for each player in a squad across all recorded matches (wide format: one row per player per match).

```python
from datafc import standings_data, squad_data, player_match_log_data

standings_df = standings_data(52, 63814)
squad_df = squad_data(standings_df=standings_df)
df = player_match_log_data(squad_df=squad_df)
```

Columns: `player_id`, `player_name`, `game_id`, `start_timestamp`, `tournament`, `season`, `home_team`, `home_team_id`, `away_team`, `away_team_id`, `home_score`, `away_score`, `status`, + all available in-match stat columns (e.g. `goals`, `assists`, `rating`, `minutesPlayed`, …).

Dependencies: `squad_data`

---

### Referee

#### `referee_stats_data`

Fetch career statistics for a referee. The `referee_id` can be obtained from the `referee_id` column in `match_details_data()` output.

```python
from datafc import referee_stats_data

df = referee_stats_data(referee_id=12345)
```

Parameters:

- `referee_id` (int): The unique Sofascore identifier for the referee.

Columns: `referee_id`, `referee_name`, `tournament_id`, `tournament_name`, `stat`, `value`. One row per stat per tournament. Covers appearances, yellow cards, red cards, second yellow cards, and penalties.

---

### ClubElo

ClubElo (<https://clubelo.com>) maintains daily Elo ratings for European clubs going back to 1939. Three functions wrap the public API; all return `pandas` DataFrames.

```python
from datafc import clubelo

# Full ranking on a given day
df = clubelo.daily_ranking_data("2026-06-10")

# A single club's full Elo history (use the spelling shown in daily_ranking_data)
hist = clubelo.club_history_data("Man City")

# Upcoming matches with per-goal-difference and exact-result probabilities
fix = clubelo.fixtures_data()
```

Common parameters: `rate_limit` (default `2.0` req/s) and `cache` (any `DiskCache` instance, shared with the Sofascore functions).

> **Notes:**
> - Club names must match ClubElo's spelling exactly (e.g. `"Man City"`, `"Real Madrid"`, `"Paris SG"`). Run `daily_ranking_data` first and check the `club` column.
> - Values before 1960 are considered provisional by ClubElo.
> - Dates accept either `"YYYY-MM-DD"` strings or `datetime.date` objects.

If the default `https://api.clubelo.com` is unreachable from your network (some corporate firewalls block port 443 to this host while leaving port 80 open), override the base URL once at startup:

```python
from datafc import clubelo
clubelo.set_clubelo_base_url("http://api.clubelo.com")
```

`clubelo.reset_clubelo_base_url()` restores the default.

---

### EloRatings (national teams)

[eloratings.net](https://www.eloratings.net) maintains daily Elo ratings for national teams going back to 1872. Seven functions wrap the site's underlying `.tsv` data files; all return `pandas` DataFrames.

```python
from datafc import eloratings

# Current global ranking of all national teams (30 columns)
df = eloratings.world_ranking_data()

# Full match history for a single national team
matches = eloratings.country_matches_data("Spain")

# Code reference tables (handy for joining onto the above)
countries = eloratings.country_codes_data()         # country_code → country_name
tournaments = eloratings.tournament_codes_data()    # tournament_code → tournament_name
groups = eloratings.tournament_groups_data()        # specific code → group code (long format)
editions = eloratings.tournament_editions_data()    # every tournament edition + dates + slug

# Legacy/historical country code → ISO code mapping
teams = eloratings.teams_data()

# Example: enrich Spain's matches with full tournament names
spain = (
    eloratings.country_matches_data("Spain")
    .merge(tournaments, left_on="tournament", right_on="tournament_code", how="left")
)

# Example: every World Cup final tournament (filter editions on the WC group)
wc_finals = editions[(editions["code"] == "WC") & editions["start_date"].notna()]
```

Common parameters: `rate_limit` (default `2.0` req/s) and `cache` (same `DiskCache` instance as Sofascore/ClubElo).

> **Column names are verified against the site's JavaScript source.**
> eloratings.net does not publish a documented API; the `.tsv` files have no header row. Column names in `world_ranking_data` are derived from index→field assignments in `scripts/ratings.js`; the remaining files are cross-checked against the live site's display. The ``WORLD_COLUMNS`` / ``COUNTRY_MATCH_COLUMNS`` lists in `datafc/eloratings/_parsers.py` document each position. If the site changes its layout, columns may be silently mis-labelled — please open an issue if you spot a discrepancy.

> **Country argument is a page slug, not an ISO code.**
> `country_matches_data("Spain")` calls `https://www.eloratings.net/Spain.tsv`. Use the same capitalisation and spelling shown in the URL of the country page on eloratings.net (e.g. `"Czech_Republic"`, `"United_States"`).

Override the base URL the same way as ClubElo if needed:

```python
from datafc import eloratings
eloratings.set_eloratings_base_url("http://www.eloratings.net")
```

---

## What's new

### v2.7.0

- **Club Elo ratings via ClubElo.** Pull daily Elo rankings of European clubs (going back to 1939), a single club's full rating history, and probability-based predictions for upcoming matches — all as `pandas` DataFrames. Three functions under `datafc.clubelo`: `daily_ranking_data`, `club_history_data`, `fixtures_data`.
- **National-team Elo ratings via eloratings.net.** Pull the current global ranking of every national team, a country's full international match history (back to 1872), and the site's reference tables for resolving the two-letter country codes and tournament codes into full names. Seven functions under `datafc.eloratings`, including `world_ranking_data`, `country_matches_data`, `country_codes_data`, and `tournament_codes_data`.
- **Shared caching across all sources.** ClubElo and eloratings.net responses use the same `DiskCache` you already pass to the Sofascore functions, so a single cache directory keeps every fetch persistent across sessions.

---

### v2.6.0

- **New function: `formations_data`** — fetches home and away formation for each match. Returns two rows per match (`team`: `home` / `away`) with the formation string (e.g. `4-3-3`).

---

### v2.5.0

- **`player_data` now returns `position_detailed`.** New column containing Sofascore's detailed position list (e.g. `["AM", "MC", "RW"]`) alongside the existing single `position` field.

---

### v2.4.0

- **New function: `player_attribute_overviews_data`** — fetches Sofascore radar attribute snapshots (attacking, technical, tactical, defending, creativity) for each player in a squad. Includes the position-average baseline and previous-year history.
- **More reliable batch fetches.** `match_h2h_data` and `match_odds_data` no longer stop the whole run when one match returns an error. The bad match is skipped and the rest succeed, matching how other batch functions already behaved.
- **Fixed `aio.team_stats_data(season=...)`.** The async version now accepts the `season` argument that the sync version always had — previously it raised `TypeError`.

---

### v2.3.0

- **Fixed `match_data` for World Cup knockout stages across all seasons.** Round numbers are now resolved automatically from the API instead of being hardcoded, so older seasons work correctly.
- **Fixed `standings_data` for tournament-format competitions.** Calling this function for World Cup, Euro, or similar tournaments no longer raises an error. Only the available categories are returned.

---

### v2.2.0

- Added `tournament_type="world_cup"` support to `match_data` and `past_matches_data` for FIFA World Cup competitions. Knockout stage rounds are fixed internally; only `group_stage_week` requires `week_number`.
- `week_number` is now optional (`None` by default). It is required for league rounds, UEFA stages, and `world_cup` + `group_stage_week`. Omitting it when required raises `InvalidParameterError`.

---

### v2.1.0

- Added `team_match_history_data`: fetches the complete match history for a single team across all competitions using `team_id` directly (no standings dependency).

---

### v2.0.0

- **Chrome / Selenium removed — no browser required.** datafc now makes direct HTTP requests. Installation is simpler, and fetches are significantly faster than before.
- **18 new functions.** `seasons_data`, `season_rounds_data`, `team_data`, `team_transfers_data`, `upcoming_matches_data`, `league_player_stats_data`, `match_details_data`, `match_h2h_data`, `pregame_form_data`, `incidents_data`, `average_positions_data`, `player_data`, `player_transfers_data`, `player_career_stats_data`, `player_national_team_data`, `player_match_log_data`, `referee_stats_data`, `search_data`.
- **Async API.** All functions are available in `datafc.aio` for parallel fetching with `asyncio.gather()`, letting you download an entire matchweek's worth of data concurrently.
- **Disk caching.** Pass a `DiskCache` instance to any function to avoid re-fetching data you've already downloaded. Cached responses are returned instantly on subsequent calls.
- **Automatic rate limiting and retries.** All functions accept a `rate_limit` parameter. Temporary failures (rate limits, server errors) are retried automatically without any extra code on your side.
- **New Parquet export.** Use `save_parquet()` on any DataFrame returned by a fetch function to save output as `.parquet`. Requires `pyarrow` (`pip install datafc[parquet]`).
- **Heatmap fetch no longer crashes on partial access errors.** `coordinates_data` now skips players that the API refuses to serve and returns data for everyone else. The function only raises an error if no player yields any coordinates at all.
- **Exported filenames are human-readable.** JSON, Excel, and Parquet files now use the league name (e.g. `trendyol_superlig_shots_data.json`) instead of raw numeric IDs. Turkish and other non-ASCII characters are transliterated correctly — `Şampiyonlar` becomes `sampiyonlar`, not `ampiyonlar`.
- **Valid JSON output.** Exported `.json` files no longer contain invalid `NaN` literals; they use `null` instead, making them compatible with every JSON parser and spreadsheet tool.
- **Cleaner numeric columns.** Score fields, ratings, and market values that were previously returned as strings or empty strings are now proper numeric types (`null` when missing, not `""`).
- **Clearer errors.** When something goes wrong, the exception type tells you what happened: data not available, invalid parameter, API access error, rate limit hit, or server error.

### v1.5.0

- Added `team_stats_data`, `player_stats_data`, and `squad_data`.

### v1.4.0

- Added `tournament_type` and `tournament_stage` parameters to `match_data` and `past_matches_data` for UEFA competitions (UCL, UEL, UECL, UNL).

### v1.3.0

- Added `past_matches_data`.

### v1.2.0

- Added match score columns to `match_data`.

### v1.1.0

- Added 4 new columns to `match_data`.
- Added `data_source` parameter to export functions.

### v1.0.0

- Initial release. Selenium-based Sofascore scraper with JSON/Excel export.

## License

MIT License

## Contributing

Bug reports, feature requests, and pull requests are welcome at [github.com/urazakgul/datafc](https://github.com/urazakgul/datafc/issues).
