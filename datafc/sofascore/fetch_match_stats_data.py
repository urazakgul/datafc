import json
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datafc.utils._setup_webdriver import setup_webdriver
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import ALLOWED_SOURCES, API_BASE_URLS

def match_stats_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    element_load_timeout: int = 10,
    enable_json_export: bool = False,
    enable_excel_export: bool = False
) -> pd.DataFrame:
    """
    Fetches statistical data for each match in the provided match dataset.

    Args:
        match_df (pd.DataFrame): A DataFrame containing match metadata,
            which should be generated by the `match_data` function.
        data_source (str): The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        element_load_timeout (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
        enable_json_export (bool): If `True`, saves the fetched match statistics data as a JSON file. Defaults to `False`.
        enable_excel_export (bool): If `True`, saves the fetched match statistics data as an Excel file. Defaults to `False`.
    """
    if data_source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid data source: {data_source}. Must be one of {ALLOWED_SOURCES}")

    if match_df is None or match_df.empty:
        raise ValueError("Match dataframe must be provided and cannot be empty.")

    try:
        webdriver_instance = setup_webdriver()
        statistics_list = []

        for _, row in match_df.iterrows():
            country, tournament, season, week, game_id = row[
                ["country", "tournament", "season", "week", "game_id"]
            ]

            api_request_url = f"{API_BASE_URLS[data_source]}/api/v1/event/{game_id}/statistics"
            webdriver_instance.get(api_request_url)

            try:
                response_element = WebDriverWait(webdriver_instance, element_load_timeout).until(
                    EC.visibility_of_element_located((By.TAG_NAME, "pre"))
                )
                statistics = json.loads(response_element.text).get("statistics", [])

                for period_data in statistics:
                    for group in period_data.get("groups", []):
                        for item in group.get("statisticsItems", []):
                            statistics_list.append({
                                "country": country,
                                "tournament": tournament,
                                "season": season,
                                "week": week,
                                "game_id": game_id,
                                "period": period_data.get("period"),
                                "group_name": group.get("groupName"),
                                "stat_name": item.get("name"),
                                "home_team_stat": item.get("home"),
                                "away_team_stat": item.get("away"),
                            })

            except TimeoutException:
                raise RuntimeError(f"Timeout while fetching match statistics for game {game_id}.")
            except json.JSONDecodeError:
                raise RuntimeError(f"Failed to decode match statistics for game {game_id}.")

        game_statistics_df = pd.DataFrame(statistics_list)

        if game_statistics_df.empty:
            raise ValueError("No match statistics data found for the specified parameters.")

        if enable_json_export or enable_excel_export:
            first_row = game_statistics_df.iloc[0]

            if enable_json_export:
                save_json(
                    data=game_statistics_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=first_row["season"],
                    week_number=first_row["week"]
                )

            if enable_excel_export:
                save_excel(
                    data=game_statistics_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=first_row["season"],
                    week_number=first_row["week"]
                )

        return game_statistics_df

    except WebDriverException as e:
        raise RuntimeError(f"Selenium WebDriver error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching match statistics data: {e.__class__.__name__} - {e}")

    finally:
        if webdriver_instance:
            webdriver_instance.quit()