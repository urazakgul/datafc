# datafc v1.2.0

## Overview

`datafc` is a Python library designed for fetching, processing, and exporting football match data using Selenium WebDriver. It provides structured and detailed match data to support advanced analysis, visualization, and reporting processes for football analysts, researchers, and data-driven professionals.

Currently, `datafc` supports **Sofascore** as a data source. However, the library is built with scalability in mind. Future updates will integrate additional data sources and extend its functionality beyond data fetching, contributing more comprehensively to football analytics.

> **Note:**
> The `tournament_id` and `season_id` values can be obtained by visiting the league's page directly on Sofascore. For example, when navigating to
> <a href="https://www.sofascore.com/tr/turnuva/futbol/turkey/trendyol-super-lig/52#id:63814" target="_blank" rel="noopener noreferrer">this link</a>,
> you will see that **52** is the `tournament_id` for the Super Lig, and **63814** corresponds to the 2024/25 season.

## Features

* **Automated Web Scraping**: Utilizes Selenium WebDriver for fetching data dynamically.
* **Multi-format Data Export**: Supports JSON and Excel exports.
* **Alternative in case of regional restrictions**: If `sofascore` is restricted in certain regions, `sofavpn` can be used as an alternative access method.
* **Match Dependencies**: Functions rely on pre-fetched match or lineup data where applicable.

## Installation

You can install `datafc` directly from PyPI using pip:

```bash
pip install datafc
```

This will automatically install all required dependencies.

If you want the most up-to-date version, you can install the development version directly from GitHub:

```bash
pip install git+https://github.com/urazakgul/datafc.git
```

To install a specific version of `datafc`, use:

```bash
pip install datafc==1.2.0
```

If you already have `datafc` installed and want to upgrade to the latest version, run:

```bash
pip install --upgrade datafc
```

## Why Selenium?

`datafc` fetches football match data using Selenium WebDriver because direct HTTP requests resulted in inconsistent data, with values changing on each request, leading to unreliable results.

By using Selenium, `datafc` ensures stable and reliable data fetching, providing consistent and accurate data for football analysis.

## WebDriver Setup

`datafc` uses Selenium WebDriver to fetch football match data dynamically. The package automatically installs and manages the correct WebDriver version using <a href="https://github.com/SergeyPirogov/webdriver_manager" target="_blank" rel="noopener noreferrer">webdriver-manager</a>, ensuring compatibility with your system.

### Requirements

* Google Chrome must be installed on your system.
* The correct WebDriver version is managed automatically.
* The script runs exclusively in headless mode for efficiency.

### WebDriver Initialization

To ensure stable and reliable data fetching, `datafc` initializes WebDriver with the following configurations:

* Headless mode enforced: The browser runs without a graphical interface.
* Platform-specific optimizations:
  * Linux: Uses `--no-sandbox` and `--disable-dev-shm-usage` for compatibility with containerized environments.
  * Windows/macOS: Includes optimizations to prevent pop-ups and interruptions.

## Error Handling and Troubleshooting

* `TimeoutException`: Increase the `element_load_timeout` value.
* `WebDriverException`: Verify that the WebDriver is correctly installed and matches your browser version.
* `ValueError`: Check your input parameters and validate API responses.

Additional troubleshooting tips and detailed error management guidelines can be added in future releases.

## Importing Functions

Instead of importing each function separately, you can import the necessary functions from `datafc.sofascore`:

```python
from datafc.sofascore import (
    match_data,
    match_odds_data,
    match_stats_data,
    momentum_data,
    lineups_data,
    coordinates_data,
    substitutions_data,
    goal_networks_data,
    shots_data,
    standings_data
)
```

## Functions

### Match Data & Lineups Data: Critical Dependencies for Other Functions

`match_data`

The `match_data` function is essential for fetching basic match details and serves as the foundation for multiple other functions. Without `match_data`, the following functions cannot be executed:

* `match_odds_data`
* `match_stats_data`
* `momentum_data`
* `lineups_data`
* `substitutions_data`
* `goal_networks_data`
* `shots_data`

Thus, before running any of these functions, ensure that `match_data` has been successfully executed.

`lineups_data`

The `lineups_data` function fetches player lineup details for each match and is a prerequisite for obtaining individual player-related statistics. It is required for the following function:

* `coordinates_data`

Without `lineups_data`, these dependent functions will not work as expected.

Exception: `standings_data`

Unlike the other functions, `standings_data` does not require `match_data` or `lineups_data`. It can be executed independently using only `tournament_id` and `season_id`.

### Match Data

#### `match_data`

The `match_data` function fetches match data for a specified tournament, season, and matchweek. It returns a DataFrame containing details such as country, tournament name, season, week number, game ID, home team, home team ID, away team, away team ID, added injury times for both halves, start timestamp, match status, and score-related information.

Example Usage:

```python
# Fetch match data for a specific tournament, season, and week
match_df = match_data(
    tournament_id=52,
    season_id=63814,
    week_number=21,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(match_df)
```

Parameters:

* `tournament_id` (int): The unique identifier for the tournament.
* `season_id` (int): The unique identifier for the season.
* `week_number` (int): The matchweek number within the season.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `home_team`: The name of the home team.
* `home_team_id`: The unique identifier for the home team.
* `away_team`: The name of the away team.
* `away_team_id`: The unique identifier for the away team.
* `injury_time_1`: Added injury time in the first half.
* `injury_time_2`: Added injury time in the second half.
* `start_timestamp`: The start time of the match.
* `status`: The current status of the match.
* `home_score_current`: The latest recorded score for the home team.
* `home_score_display`: The displayed score of the home team.
* `home_score_period1`: The home team's score at the end of the first half.
* `home_score_period2`: The home team's goals scored in the second half.
* `home_score_normaltime`: The home team's final score at the end of normal time (90 minutes).
* `away_score_current`: The latest recorded score for the away team.
* `away_score_display`: The displayed score of the away team.
* `away_score_period1`: The away team's score at the end of the first half.
* `away_score_period2`: The away team's goals scored in the second half.
* `away_score_normaltime`: The away team's final score at the end of normal time (90 minutes).

Dependencies:

* No prior function dependency required.

#### `match_odds_data`

The `match_odds_data` function fetches betting odds data for each match in the provided match dataset. It returns a DataFrame containing match odds details, including market names, odds values, and whether the odds changed.

Example Usage:

```python
# Fetch match odds data
match_odds_df = match_odds_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(match_odds_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `market_name`: The name of the betting market.
* `market_id`: The unique identifier for the betting market.
* `is_live`: Whether the odds are live.
* `choice_name`: The name of the betting option.
* `initial_fractional_value`: The initial fractional odds value.
* `current_fractional_value`: The current fractional odds value.
* `winning`: Whether the option won.
* `change`: The change in odds value.

Dependencies:

* Requires `match_data` output as `match_df`.

#### `match_stats_data`

The `match_stats_data` function fetches statistical data for each match in the provided match dataset. It returns a DataFrame containing key match statistics, including team performance metrics.

Example Usage:

```python
# Fetch match statistics data
match_stats_df = match_stats_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(match_stats_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `period`: The period of the match.
* `group_name`: The category of statistics.
* `stat_name`: The name of the statistic.
* `home_team_stat`: The value of the statistic for the home team.
* `away_team_stat`: The value of the statistic for the away team.

Dependencies:

* Requires `match_data` output as `match_df`.

#### `momentum_data`

The `momentum_data` function fetches momentum data for each match in the provided match dataset. It returns a DataFrame containing match momentum values over time.

Example Usage:

```python
# Fetch momentum data
momentum_df = momentum_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(momentum_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `minute`: The minute of the match when the momentum value was recorded.
* `value`: The momentum value at that specific minute.

Dependencies:

* Requires `match_data` output as `match_df`.

### Player Data

#### `lineups_data`

The `lineups_data` function fetches lineup data for each match in the provided match dataset. It returns a DataFrame containing lineup details such as country, tournament name, season, week number, game ID, team, player name, player ID, statistic name, and statistic value.

Example Usage:

```python
# Fetch lineups data based on match data
lineups_df = lineups_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(lineups_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `team`: The team name (home or away).
* `player_name`: The name of the player.
* `player_id`: The unique identifier for the player.
* `stat_name`: The name of the statistic.
* `stat_value`: The value of the statistic.

Dependencies:

* Requires `match_data` output as `match_df`.

#### `coordinates_data`

The `coordinates_data` function fetches coordinate data for each player in the provided lineup dataset. It returns a DataFrame containing coordinate details such as country, tournament name, season, week number, game ID, team, player ID, player name, and x-y coordinates.

Example Usage:

```python
# Fetch coordinates data
coordinates_df = coordinates_data(
    lineups_df=lineups_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(coordinates_df)
```

Parameters:

* `lineups_df` (pd.DataFrame): A DataFrame containing player and match metadata, which should be generated by the `lineups_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `team`: The team name (home or away).
* `player_id`: The unique identifier for the player.
* `player_name`: The name of the player.
* `x`: The x-coordinate of the player's position.
* `y`: The y-coordinate of the player's position.

Dependencies:

* Requires `lineups_data` output as `lineups_df`.

#### `substitutions_data`

The `substitutions_data` function fetches substitution data for each match in the provided match dataset. It returns a DataFrame containing details of player substitutions, including the players involved and the time of the substitution.

Example Usage:

```python
# Fetch substitution data
substitutions_df = substitutions_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(substitutions_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `time`: The minute when the substitution occurred.
* `player_in`: The name of the player who was substituted in.
* `player_in_id`: The unique identifier of the player who was substituted in.
* `player_out`: The name of the player who was substituted out.
* `player_out_id`: The unique identifier of the player who was substituted out.

Dependencies:

* Requires `match_data` output as `match_df`.

### Event Data

#### `goal_networks_data`

The `goal_networks_data` function fetches goal network data for each match in the provided match dataset. It returns a DataFrame containing goal-related events, including passing networks and shot locations.

Example Usage:

```python
# Fetch goal networks data
goal_networks_df = goal_networks_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(goal_networks_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `player_name`: The name of the player involved in the event.
* `player_id`: The unique identifier for the player.
* `event_type`: The type of event (e.g., pass, shot, assist).
* `player_x`: The x-coordinate of the player's position.
* `player_y`: The y-coordinate of the player's position.
* `pass_end_x`: The x-coordinate of the end location of a pass.
* `pass_end_y`: The y-coordinate of the end location of a pass.
* `is_assist`: Whether the event was an assist.
* `id`: The unique identifier for the event.
* `goalkeeper_x`: The x-coordinate of the goalkeeper's position during the event.
* `goalkeeper_y`: The y-coordinate of the goalkeeper's position during the event.
* `goal_shot_x`: The x-coordinate of the shot location.
* `goal_shot_y`: The y-coordinate of the shot location.
* `goal_mouth_x`: The x-coordinate of the goal mouth location.
* `goal_mouth_y`: The y-coordinate of the goal mouth location.
* `goalkeeper_name`: The name of the goalkeeper involved in the event.
* `goalkeeper_id`: The unique identifier for the goalkeeper.

Dependencies:

* Requires `match_data` output as `match_df`.

#### `shots_data`

The `shots_data` function fetches shot data for each match in the provided match dataset. It returns a DataFrame containing detailed shot-related information, including player coordinates, xG values, shot types, and goal mouth locations.

Example Usage:

```python
# Fetch shot data
shots_df = shots_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(shots_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `season`: The season year.
* `week`: The matchweek number.
* `game_id`: The unique identifier for the match.
* `player_name`: The name of the player who took the shot.
* `player_id`: The unique identifier for the player.
* `player_position`: The player's position during the shot.
* `is_home`: Whether the player belongs to the home team.
* `incident_type`: The type of shot incident.
* `shot_type`: The type of shot.
* `body_part`: The part of the body used for the shot.
* `goal_type`: The type of goal (if applicable).
* `situation`: The match situation when the shot was taken.
* `goal_mouth_location`: The location in the goal where the shot was aimed.
* `xg`: The expected goals (xG) value of the shot.
* `xgot`: The expected goals on target (xGOT) value of the shot.
* `player_coordinates_x`: The x-coordinate of the player at the moment of the shot.
* `player_coordinates_y`: The y-coordinate of the player at the moment of the shot.
* `goal_mouth_coordinates_x`: The x-coordinate of the goal mouth target.
* `goal_mouth_coordinates_y`: The y-coordinate of the goal mouth target.
* `draw_start_x`: The x-coordinate where the shot trajectory starts.
* `draw_start_y`: The y-coordinate where the shot trajectory starts.
* `draw_end_x`: The x-coordinate where the shot trajectory ends.
* `draw_end_y`: The y-coordinate where the shot trajectory ends.
* `block_coordinates_x`: The x-coordinate of the block location (if blocked).
* `block_coordinates_y`: The y-coordinate of the block location (if blocked).
* `time`: The match time when the shot was taken.
* `time_seconds`: The exact match time in seconds.
* `added_time`: The additional time in minutes (if applicable).

Dependencies:

* Requires `match_data` output as `match_df`.

### Standings Data

#### `standings_data`

The `standings_data` function fetches league standings for a specific tournament and season. It returns a DataFrame containing team rankings, match results, and points.

Example Usage:

```python
# Fetch league standings
standings_df = standings_data(
    tournament_id=52,
    season_id=63814,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(standings_df)
```

Parameters:

* `tournament_id` (int): The unique identifier for the tournament.
* `season_id` (int): The unique identifier for the season.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
* `enable_json_export` (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `team_name`: The name of the team.
* `team_id`: The unique identifier for the team.
* `position`: The team's position in the standings.
* `matches`: The number of matches played.
* `wins`: The number of matches won.
* `draws`: The number of matches drawn.
* `losses`: The number of matches lost.
* `scores_for`: The number of goals scored by the team.
* `scores_against`: The number of goals conceded by the team.
* `points`: The total points accumulated by the team.
* `category`: The type of standings.

Dependencies:

* No prior function dependency required.

## Changelog

* v1.2.0
  * Added match score columns to `match_data`

* v1.1.0
  * Added 4 new columns to `match_data`
  * Added `data_source` parameter to `save_json` and `save_excel` for including the source in file names

* v1.0.1 (Cancelled, not used)

* v1.0.0
  * Initial release of `datafc`
  * Fetching match data using Selenium WebDriver
  * Supports Sofascore as a data source
  * Exports data in JSON and Excel formats

## License

This project is open-source and licensed under the MIT License.

## Contributing

Contributions are welcome! If you have any bug reports, feature requests, or pull requests, please visit my <a href="https://github.com/urazakgul/datafc/issues" target="_blank" rel="noopener noreferrer">GitHub page</a> to contribute.