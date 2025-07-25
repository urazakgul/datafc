# datafc v1.5.0

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
pip install datafc==1.5.0
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
    past_matches_data,
    lineups_data,
    coordinates_data,
    substitutions_data,
    goal_networks_data,
    shots_data,
    standings_data,
    team_stats_data,
    player_stats_data,
    squad_data
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

### `standings_data`: A Foundation for Team and Player-Level Functions

Exception: `standings_data` and `past_matches_data`

Unlike other functions, `standings_data` and `past_matches_data` do not require `match_data` or `lineups_data`. They can be executed independently using only `tournament_id` and `season_id`. Additionally, `past_matches_data` includes an extra field: `week_number`.

However, `standings_data` serves as a critical dependency for the following functions:

* `team_stats_data`
* `player_stats_data`
* `squad_data`

These functions rely on team-level metadata (such as `team_id`) provided by `standings_data` to fetch more granular data. Ensure that `standings_data` is successfully executed and includes teams with `category == 'Total'` before calling any of the above functions.

`past_matches_data` also works independently and includes an extra field: `week_number`.

### Match Data

#### `match_data`

The `match_data` function fetches match data for a specified tournament, season, and matchweek.

Example Usage:

```python
match_df = match_data(
    tournament_id=52,
    season_id=63814,
    week_number=21,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(match_df)

uefa_match_df = match_data(
    tournament_id=7,
    season_id=61644,
    week_number=5,
    tournament_type="uefa",
    tournament_stage="round_of_16",
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_match_df)
```

Parameters:

* `tournament_id` (int): The unique identifier for the tournament.
* `season_id` (int): The unique identifier for the season.
* `week_number` (int): The matchweek number within the season. The applicable week numbers depend on the tournament and stage, as outlined below for the 2024/25 season:
  * UCL, UEL, UECL, and UNL:
    * `qualification_round`: 1, 2, 3
    * `qualification_playoff`: 636
    * `group_stage_week`: 1, 2, 3, ..., 8 (for UNL, up to 6)
    * `playoff_round`: 636
    * `round_of_16`: 5
    * `quarterfinals`: 27
    * `semifinals`: 28
    * `final`: 29
  * Domestic Leagues:
    * Use the corresponding matchweek number (e.g., for the 10th week of the season, enter `week_number=10`).
* `tournament_type` (str, optional): The tournament type (`uefa`). If `None`, assumes league format.
* `tournament_stage` (str, optional): The specific stage of the tournament. Available options for UEFA tournaments:
  * `preliminary_final`
  * `preliminary_final`
  * `qualification_round`
  * `qualification_playoff`
  * `group_stage_week`
  * `playoff_round`
  * `round_of_16`
  * `quarterfinals`
  * `semifinals`
  * `match_for_3rd_place`
  * `final`
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `match_odds_data` function fetches betting odds data for each match in the provided match dataset.

Example Usage:

```python
match_odds_df = match_odds_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(match_odds_df)

uefa_match_odds_df = match_odds_data(
    match_df=uefa_match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_match_odds_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `match_stats_data` function fetches statistical data for each match in the provided match dataset.

Example Usage:

```python
match_stats_df = match_stats_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(match_stats_df)

uefa_match_stats_df = match_stats_data(
    match_df=uefa_match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_match_stats_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `momentum_data` function fetches momentum data for each match in the provided match dataset.

Example Usage:

```python
momentum_df = momentum_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(momentum_df)

uefa_momentum_df = momentum_data(
    match_df=uefa_match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_momentum_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

#### `past_matches_data`

The `past_matches_data` function fetches past match data for a specified tournament, season, and week number.

Example Usage:

```python
past_matches_df = past_matches_data(
    tournament_id=52,
    season_id=63814,
    week_number=21,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(past_matches_df)

uefa_past_matches_df = past_matches_data(
    tournament_id=7,
    season_id=61644,
    week_number=5,
    tournament_type="uefa",
    tournament_stage="round_of_16",
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_past_matches_df)
```

Parameters:

* `tournament_id` (int): The unique identifier for the tournament.
* `season_id` (int): The unique identifier for the season.
* `week_number` (int): The matchweek number within the season. The applicable week numbers depend on the tournament and stage, as outlined below for the 2024/25 season:
  * UCL, UEL, UECL, and UNL:
    * `qualification_round`: 1, 2, 3
    * `qualification_playoff`: 636
    * `group_stage_week`: 1, 2, 3, ..., 8 (for UNL, up to 6)
    * `playoff_round`: 636
    * `round_of_16`: 5
    * `quarterfinals`: 27
    * `semifinals`: 28
    * `final`: 29
  * Domestic Leagues:
    * Use the corresponding matchweek number (e.g., for the 10th week of the season, enter `week_number=10`).
* `tournament_type` (str, optional): The tournament type (`uefa`). If `None`, assumes league format.
* `tournament_stage` (str, optional): The specific stage of the tournament. Available options for UEFA tournaments:
  * `preliminary_final`
  * `preliminary_final`
  * `qualification_round`
  * `qualification_playoff`
  * `group_stage_week`
  * `playoff_round`
  * `round_of_16`
  * `quarterfinals`
  * `semifinals`
  * `match_for_3rd_place`
  * `final`
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

### Player Data

#### `lineups_data`

The `lineups_data` function fetches lineup data for each match in the provided match dataset.

Example Usage:

```python
lineups_df = lineups_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(lineups_df)

uefa_lineups_df = lineups_data(
    match_df=uefa_match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_lineups_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `coordinates_data` function fetches coordinate data for each player in the provided lineup dataset.

Example Usage:

```python
coordinates_df = coordinates_data(
    lineups_df=lineups_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(coordinates_df)

uefa_coordinates_df = coordinates_data(
    lineups_df=uefa_lineups_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_coordinates_df)
```

Parameters:

* `lineups_df` (pd.DataFrame): A DataFrame containing player and match metadata, which should be generated by the `lineups_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `substitutions_data` function fetches substitution data for each match in the provided match dataset.

Example Usage:

```python
substitutions_df = substitutions_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(substitutions_df)

uefa_substitutions_df = substitutions_data(
    match_df=uefa_match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_substitutions_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `goal_networks_data` function fetches goal network data for each match in the provided match dataset.

Example Usage:

```python
goal_networks_df = goal_networks_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(goal_networks_df)

uefa_goal_networks_df = goal_networks_data(
    match_df=uefa_match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_goal_networks_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `shots_data` function fetches shot data for each match in the provided match dataset.

Example Usage:

```python
shots_df = shots_data(
    match_df=match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(shots_df)

uefa_shots_df = shots_data(
    match_df=uefa_match_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_shots_df)
```

Parameters:

* `match_df` (pd.DataFrame): A DataFrame containing match metadata, which should be generated by the `match_data` function.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

The `standings_data` function fetches league standings for a specific tournament and season.

Example Usage:

```python
standings_df = standings_data(
    tournament_id=52,
    season_id=63814,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(standings_df)

uefa_standings_df = standings_data(
    tournament_id=7,
    season_id=61644,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(uefa_standings_df)
```

Parameters:

* `tournament_id` (int): The unique identifier for the tournament.
* `season_id` (int): The unique identifier for the season.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `sofascore`.
* `element_load_timeout` (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
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

### Team Statistics Data

#### `team_stats_data`

The `team_stats_data` function fetches detailed statistical data for each team in a given tournament and season, based on the team list provided by `standings_data`.

Note: This function requires the output of `standings_data` and only processes rows where `category == 'Total'`.

Example Usage:

```python
standings_df = standings_data(
    tournament_id=52,
    season_id=63814,
    data_source="sofascore"
)

team_stats_df = team_stats_data(
    standings_df=standings_df,
    tournament_id=52,
    season_id=63814,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(team_stats_df)
```

Parameters:

* `standings_df` (pd.DataFrame): A DataFrame with metadata on each team, typically returned by standings_data.
* `tournament_id` (int): The unique identifier for the tournament.
* `season_id` (int): The unique identifier for the season.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `"sofascore"`.
* `element_load_timeout` (int): Maximum time (in seconds) to wait for the API response. Defaults to `10`.
* `enable_json_export` (bool): If `True`, exports the data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `team_name`: The name of the team.
* `team_id`: The unique identifier of the team.
* `stat`: The name of the statistic.
* `value`: The value of the statistic.

Dependencies:

* Requires `standings_data` output as `standings_df`.

### Player Statistics Data

#### `player_stats_data`

The `player_stats_data` function fetches top player statistics for each team in the given standings dataset. It processes player-level metrics like goals, assists, duels won, and more.

Note: This function requires the output of `standings_data`, and filters for rows where `category == 'Total'`.

Example Usage:

```python
standings_df = standings_data(
    tournament_id=52,
    season_id=63814,
    data_source="sofascore"
)

player_stats_df = player_stats_data(
    standings_df=standings_df,
    tournament_id=52,
    season_id=63814,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(player_stats_df)
```

Parameters:

* `standings_df` (pd.DataFrame): A DataFrame with metadata on teams, returned by standings_data.
* `tournament_id` (int): The unique identifier for the tournament.
* `season_id` (int): The unique identifier for the season.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `"sofascore"`.
* `element_load_timeout` (int): Maximum time (in seconds) to wait for the API response. Defaults to `10`.
* `enable_json_export` (bool): If `True`, exports the data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `team_name`: The name of the team.
* `team_id`: The unique identifier of the team.
* `player_name`: The name of the player.
* `player_id`: The unique identifier of the player.
* `position`: The player’s position.
* `stat_name`: The name of the statistic.
* `stat_value`: The value of the statistic.

Dependencies:

* Requires `standings_data` output as `standings_df`.

### Squad Data

#### `squad_data`

The `squad_data` function fetches detailed squad (roster) information for each team listed in the provided standings dataset. It includes player bio data such as age, height, position, market value, and contract info.

Note: This function requires the output of `standings_data`, and only processes rows where `category == 'Total'`.

Example Usage:

```python
standings_df = standings_data(
    tournament_id=52,
    season_id=63814,
    data_source="sofascore"
)

squad_df = squad_data(
    standings_df=standings_df,
    data_source="sofascore",
    enable_json_export=True,
    enable_excel_export=True
)

print(squad_df)
```

Parameters:

* `standings_df` (pd.DataFrame): A DataFrame with team metadata, returned by standings_data.
* `data_source` (str): The data source (`sofavpn` or `sofascore`). Defaults to `"sofascore"`.
* `element_load_timeout` (int): Maximum time (in seconds) to wait for the API response. Defaults to `10`.
* `enable_json_export` (bool): If `True`, exports the data as a JSON file. Defaults to `False`.
* `enable_excel_export` (bool): If `True`, exports the data as an Excel file. Defaults to `False`.

Data Structure:

The returned DataFrame includes the following columns:

* `country`: The country where the tournament is held.
* `tournament`: The name of the tournament.
* `team_name`: The name of the team.
* `team_id`: The unique identifier of the team.
* `player_name`: The name of the player.
* `player_id`: The unique identifier of the player.
* `age`: The date of birth timestamp (UNIX format).
* `height`: The height of the player.
* `player_country`: The nationality of the player.
* `position`: The position of the player.
* `preferred_foot`: The preferred foot of the player.
* `contract_until`: The contract end date (UNIX timestamp).
* `market_value`: The market value of the player.
* `market_currency`: The currency used for the market value.

Dependencies:

* Requires `standings_data` output as `standings_df`.

## Changelog

* v1.5.0
  * Added `team_stats_data` function to retrieve detailed per-team statistics using `standings_data`.
  * Added `player_stats_data` function to retrieve player-level top stats per team.
  * Added `squad_data` function to fetch full squad information including bio and market value.

* v1.4.0
  * Added `tournament_type` and `tournament_stage` parameters to `match_data` and `past_matches_data` functions.
  * Extended support for UEFA tournaments, including UEFA Champions League (UCL), UEFA Europa League (UEL), UEFA Europa Conference League (UECL), and UEFA Nations League (UNL), allowing seamless data fetching across multiple competitions.

* v1.3.0
  * Added `past_matches_data` function to fetch historical match data.

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