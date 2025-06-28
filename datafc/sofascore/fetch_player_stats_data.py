import json
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datafc.utils._setup_webdriver import setup_webdriver
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import ALLOWED_SOURCES, API_BASE_URLS

def player_stats_data(
    standings_df: pd.DataFrame,
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    element_load_timeout: int = 10,
    enable_json_export: bool = False,
    enable_excel_export: bool = False
) -> pd.DataFrame:
    """
    Fetches player statistics data for each team in the provided standings dataset.

    Args:
        standings_df (pd.DataFrame): A DataFrame containing team metadata, including team_id.
        tournament_id (int): The unique identifier for the tournament.
        season_id (int): The unique identifier for the season.
        data_source (str): The data source ('sofascore'). Defaults to 'sofascore'.
        element_load_timeout (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
        enable_json_export (bool): If `True`, saves the fetched data as a JSON file. Defaults to `False`.
        enable_excel_export (bool): If `True`, saves the fetched data as an Excel file. Defaults to `False`.

    Returns:
        pd.DataFrame: A DataFrame containing statistical information for each player.
    """
    if data_source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid data source: {data_source}. Must be one of {ALLOWED_SOURCES}")

    if standings_df is None or standings_df.empty:
        raise ValueError("Standings dataframe must be provided and cannot be empty.")

    webdriver_instance = None
    try:
        webdriver_instance = setup_webdriver()
        stats_data_list = []

        standings_df = standings_df[standings_df["category"] == "Total"]
        for _, row in standings_df.iterrows():
            country = row["country"]
            tournament = row["tournament"]
            team_name = row["team_name"]
            team_id = row["team_id"]

            url = f"{API_BASE_URLS[data_source + '2']}/api/v1/team/{team_id}/unique-tournament/{tournament_id}/season/{season_id}/top-players/overall"
            webdriver_instance.get(url)

            try:
                pre_tag = WebDriverWait(webdriver_instance, element_load_timeout).until(
                    EC.visibility_of_element_located((By.TAG_NAME, "pre"))
                )

                stats_json = json.loads(pre_tag.text)
                top_players = stats_json.get("topPlayers", {})

                for category, players in top_players.items():
                    for player_data in players:
                        player = player_data.get("player", {})
                        player_id = player.get("id")
                        statistics = player_data.get("statistics", {})

                        for stat, value in statistics.items():
                            if stat in ["id", "type"]:
                                continue

                            log_entry = {
                                "country": country,
                                "tournament": tournament,
                                "team_name": team_name,
                                "team_id": team_id,
                                "player_name": player.get("name"),
                                "player_id": player_id,
                                "position": player.get("position"),
                                "stat_name": stat,
                                "stat_value": value
                            }
                            if log_entry not in stats_data_list:
                                stats_data_list.append(log_entry)
            except TimeoutException:
                print(f"Timeout while fetching player stats data for team_id {team_id}.")
            except json.JSONDecodeError:
                print(f"Failed to decode player stats data for team_id {team_id}.")
            except WebDriverException as e:
                print(f"Selenium WebDriver error while fetching player stats data for team_id {team_id}: {str(e)}")
            except Exception as e:
                print(f"Unexpected error while fetching player stats data for team_id {team_id}: {e.__class__.__name__} - {e}")

        stats_data_df = pd.DataFrame(stats_data_list).drop_duplicates()

        if stats_data_df.empty:
            raise ValueError("No player statistics data found for the specified teams.")

        if enable_json_export or enable_excel_export:
            first_row = stats_data_df.iloc[0]

            if enable_json_export:
                save_json(
                    data=stats_data_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=None,
                    week_number=None
                )

            if enable_excel_export:
                save_excel(
                    data=stats_data_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=None,
                    week_number=None
                )

        return stats_data_df

    except WebDriverException as e:
        raise RuntimeError(f"Selenium WebDriver error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching player stats data: {e.__class__.__name__} - {e}")
    finally:
        if webdriver_instance:
            webdriver_instance.quit()