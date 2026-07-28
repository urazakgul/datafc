# datafc v2.8.0

`datafc` is a Python package that turns four public football data sources into clean `pandas` DataFrames: **Sofascore** (tournaments, matches, players, shots, lineups, odds), **ClubElo** (club Elo ratings back to 1939), **eloratings.net** (national team Elo ratings back to 1872), and **tff.org** (Turkish Football Federation fixtures, standings, match sheets, and player pages). 59 functions in total, all with the same call style and an async equivalent under `datafc.aio`.

## Sofascore

Import from top-level `datafc`.

### Discovery and Metadata

#### `search_data(query, entity_type=None)`
Search by name.
- `query` (str): the search term.
- `entity_type` (str, optional): `"team"`, `"player"`, `"tournament"`, or `"manager"`. `None` returns all types.

#### `seasons_data(tournament_id)`
Lists every season for a tournament.
- `tournament_id` (int)

#### `season_rounds_data(tournament_id, season_id)`
Lists every matchweek defined for a season.
- `tournament_id` (int)
- `season_id` (int)

### League / Season

#### `standings_data(tournament_id, season_id)`
League table for Total, Home, and Away categories.
- `tournament_id` (int)
- `season_id` (int)

#### `team_data(standings_df)`
Team profiles: stadium, kit colors, manager, venue capacity.
- `standings_df` (DataFrame): output of `standings_data`.

#### `team_stats_data(standings_df, tournament_id, season_id, season=None)`
Season-level team statistics (long format).
- `standings_df` (DataFrame)
- `tournament_id` (int)
- `season_id` (int)
- `season` (str, optional): human-readable label used only in the export filename.

#### `team_transfers_data(standings_df)`
All incoming and outgoing transfer records per team.
- `standings_df` (DataFrame)

#### `player_stats_data(standings_df, tournament_id, season_id)`
Top player statistics per team (long format).
- `standings_df` (DataFrame)
- `tournament_id` (int)
- `season_id` (int)

#### `squad_data(standings_df)`
Squad roster: age, height, position, preferred foot, contract expiry, market value.
- `standings_df` (DataFrame)

#### `upcoming_matches_data(standings_df)`
Upcoming fixtures for every team in the standings.
- `standings_df` (DataFrame)

#### `team_match_history_data(team_id)`
Full match history for a single team across all competitions.
- `team_id` (int): from `standings_data`, `squad_data`, or `search_data`.

#### `league_player_stats_data(tournament_id, season_id, order="-rating", accumulation="total", fields=None, position=None, max_players=100)`
Wide-format player rankings across an entire league.
- `tournament_id` (int)
- `season_id` (int)
- `order` (str): field to sort by; prefix with `-` for descending.
- `accumulation` (str): `"total"`, `"per90"`, or `"perMatch"`.
- `fields` (list, optional): stat columns to include. `None` uses 14 defaults.
- `position` (str, optional): `"G"`, `"D"`, `"M"`, or `"F"`.
- `max_players` (int): paginates as needed.

Available fields: `goals`, `assists`, `rating`, `expectedGoals`, `expectedAssists`, `goalsAssistsSum`, `penaltyGoals`, `freeKickGoal`, `scoringFrequency`, `totalShots`, `shotsOnTarget`, `bigChancesCreated`, `bigChancesMissed`, `accuratePasses`, `accuratePassesPercentage`, `keyPasses`, `accurateLongBalls`, `accurateLongBallsPercentage`, `successfulDribbles`, `successfulDribblesPercentage`, `tackles`, `interceptions`, `clearances`, `possessionLost`, `yellowCards`, `redCards`, `saves`, `goalsPrevented`, `minutesPlayed`, `appearances`.

### Match

#### `match_data(tournament_id, season_id, week_number=None, tournament_type=None, tournament_stage=None)`
Fixtures and scores for a matchweek or tournament stage.
- `tournament_id` (int)
- `season_id` (int)
- `week_number` (int, optional): required for league rounds, UEFA stages, `world_cup` + `group_stage_week`, and every `league_playoff` stage. Not needed for World Cup knockouts.
- `tournament_type` (str, optional): `"uefa"`, `"world_cup"`, or `"league_playoff"`. `None` assumes a domestic league.
- `tournament_stage` (str, optional): required when `tournament_type` is set.
  - `"uefa"`: `preliminary_semifinals`, `preliminary_final`, `qualification_round`, `qualification_playoff`, `group_stage_week`, `playoff_round`, `round_of_16`, `quarterfinals`, `semifinals`, `match_for_3rd_place`, `final`.
  - `"world_cup"`: `group_stage_week`, `round_of_32`, `round_of_16`, `quarterfinals`, `semifinals`, `match_for_3rd_place`, `final`.
  - `"league_playoff"`: `qualification_round`, `quarterfinals`, `semifinals`, `final`.

The match functions below (except `coordinates_data`) all take `match_df` as their only argument.

#### `match_details_data(match_df)`
Referee info (name, cards, career games) and venue details per match.

#### `formations_data(match_df)`
Home and away formation string (e.g. `4-3-3`).

#### `match_stats_data(match_df)`
Team stats per match (possession, shots, fouls, per period).

#### `match_odds_data(match_df)`
Pre-match and live 1/X/2 betting odds.

#### `match_h2h_data(match_df)`
All-time head-to-head record between the two teams.

#### `momentum_data(match_df)`
Minute-by-minute momentum score (positive: home; negative: away).

#### `pregame_form_data(match_df)`
Last 5 results, average rating, league position, and squad value before the match for each side.

#### `shots_data(match_df)`
Every shot event with coordinates, xG, xGOT, body part, situation, and goal mouth location.

#### `lineups_data(match_df)`
Starting XI and substitutes plus per-match player stats (long format).

#### `substitutions_data(match_df)`
Substitution events with minute, player in, player out.

#### `incidents_data(match_df)`
Goals, cards, and VAR decisions per match.

#### `average_positions_data(match_df)`
Each player's average pitch position (X/Y on a 0 to 100 scale).

#### `goal_networks_data(match_df)`
Coordinates for every action in a goal-scoring sequence (passes, shots, goalkeeper position).

#### `past_matches_data(tournament_id, season_id, week_number=None, tournament_type=None, tournament_stage=None)`
Full head-to-head history for every team pair in the given matchweek. Same signature and stage options as `match_data`.

#### `coordinates_data(lineups_df)`
Heatmap touch coordinates per player.
- `lineups_df` (DataFrame): output of `lineups_data`.

### Player

Every function below takes `squad_df` (output of `squad_data`) as its only argument.

#### `player_data(squad_df)`
Player profile: nationality, date of birth, height, weight, preferred foot, jersey number, position, market value.

#### `player_attribute_overviews_data(squad_df)`
Radar attribute snapshots (attacking, technical, tactical, defending, creativity) per player, with the position-average baseline and previous-year snapshots.

#### `player_transfers_data(squad_df)`
Transfer history per player.

#### `player_career_stats_data(squad_df)`
Season-by-season career stats across all competitions (long format, `overall` entries only).

#### `player_national_team_data(squad_df)`
National team career: appearances, goals, debut date.

#### `player_match_log_data(squad_df)`
Match-by-match in-game stats across every recorded match (wide format).

### Referee

#### `referee_stats_data(referee_id)`
Career stats for a referee (per tournament).
- `referee_id` (int): from the `referee_id` column of `match_details_data`.

## ClubElo

Import from `datafc.clubelo`. Club names must match ClubElo's spelling (e.g. `"Man City"`, `"Real Madrid"`, `"Paris SG"`).

#### `clubelo.daily_ranking_data(date)`
Full ClubElo ranking for a given calendar day.
- `date` (str or `datetime.date`): `"YYYY-MM-DD"` or a `date` object.

#### `clubelo.club_history_data(club)`
Complete Elo rating history for a single club (values before 1960 are provisional).
- `club` (str): the ClubElo spelling.

#### `clubelo.fixtures_data()`
Per-goal-difference and exact-result probabilities for upcoming matches. No arguments.

## EloRatings (National Teams)

Import from `datafc.eloratings`. Country arguments are page slugs, not ISO codes (e.g. `"Czech_Republic"`, `"United_States"`).

#### `eloratings.world_ranking_data()`
Current global Elo ranking for every national team.

#### `eloratings.country_matches_data(country)`
Complete international match history for one national team.
- `country` (str): the page slug used on eloratings.net.

#### `eloratings.country_codes_data()`
Country code to English country name lookup.

#### `eloratings.tournament_codes_data()`
Tournament code to English tournament name lookup.

#### `eloratings.tournament_editions_data()`
Every tournament edition with start/end dates and page slug.

#### `eloratings.tournament_groups_data()`
Specific tournament code to broader group code (e.g. every WC qualifier variant to `WQT`).

#### `eloratings.teams_data()`
Legacy/historical country code to ISO code mapping.

## TFF (Turkish Football Federation)

Import from `datafc.tff`. Covers Süper Lig, 1. Lig, 2. Lig, 3. Lig.

### Fixtures, Standings, Club

#### `tff.fixtures_data(page_id, week=None, group=None, playoff=False, round=None)`
Weekly fixtures or the promotion play-off bracket.
- `page_id` (int): the `pageID` query parameter from the tff.org fixture URL.
- `week` (int, optional): matchweek number.
- `group` (str, optional): 2. Lig (`"Kırmızı"` / `"Beyaz"`) or 3. Lig (`"01"` to `"04"`); case-insensitive.
- `playoff` (bool): `True` returns the 1./2./3. Lig play-off bracket with extra-time and penalty-shootout scores.
- `round` (str, optional): filter play-off rounds (e.g. `"Final"`).

#### `tff.standings_data(page_id, week, group=None)`
League table as of a matchweek.
- `page_id` (int)
- `week` (int)
- `group` (str, optional): required for 2. Lig and 3. Lig.

#### `tff.team_data(club_id)`
Club profile: official (unsponsored) name, address, president, plus stadium info.
- `club_id` (int)

### Match Sheet

Every function below takes `match_id` (int) as its only argument.

#### `tff.match_details_data(match_id)`
Match header (teams, score, stadium, tournament) plus every assigned official.

#### `tff.match_lineups_data(match_id)`
Starting XI and bench for both teams (jersey number, player id, player name).

#### `tff.match_staff_data(match_id)`
Head coach for both teams (coach id and name).

#### `tff.match_goals_data(match_id)`
Every goal with scorer, minute, and TFF code (`F` foot, `H` header, `P` penalty, `K` free kick, `KG` own goal).

#### `tff.match_cards_data(match_id)`
Every booking with player, minute, and card colour (yellow / red / second_yellow).

### Player

Every function below takes `player_id` (int).

#### `tff.player_data(player_id)`
Profile: name, birthplace, birthdate, nationality, current licence and club.

#### `tff.player_career_data(player_id)`
Licence history: every licence issue, club, contract dates, licence type.

#### `tff.player_national_matches_data(player_id)`
Every national-team appearance across all Turkey categories (A, U21, U19, etc.).

#### `tff.player_goals_data(player_id)`
Every TFF-recorded goal (club and national) with match, minute, and goal type.

#### `tff.player_matches_data(player_id, season)`
Every club match the player featured in that season.
- `season` (str): e.g. `"2025-2026"`.

#### `tff.player_cards_data(player_id, season)`
Every yellow / red the player picked up that season.
- `season` (str): e.g. `"2025-2026"`.

## Async API

Every function has an async equivalent in `datafc.aio` with the same signature and parameters, designed for `asyncio.gather()`.

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

When mixing independent coroutines, pass `return_exceptions=True` so one failure doesn't cancel the rest:

```python
results = await asyncio.gather(
    aio.match_data(52, 77805, week_number=1),
    aio.standings_data(52, 77805),
    return_exceptions=True,
)
```

## Caching

Cache responses to disk to skip repeated API calls across sessions. The same `DiskCache` instance works across all four data sources.

```python
import asyncio
from datafc import DiskCache, aio

cache = DiskCache(cache_dir=".datafc_cache", ttl_hours=24)

async def main():
    df = await aio.match_data(52, 63814, week_number=1, cache=cache)

asyncio.run(main())
```

`DiskCache` stores responses as JSON files keyed by URL. `ttl_hours=0` disables expiry. `cache.clear()` invalidates every entry.
