import json
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datafc.utils._setup_webdriver import setup_webdriver
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import ALLOWED_SOURCES, API_BASE_URLS

def standings_data(
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    element_load_timeout: int = 10,
    enable_json_export: bool = False,
    enable_excel_export: bool = False
) -> pd.DataFrame:
    """
    Fetches league standings for a specific tournament and season.

    Args:
        tournament_id (int): The unique identifier for the tournament.
        season_id (int): The unique identifier for the season.
        data_source (str): The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        element_load_timeout (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
        enable_json_export (bool): If `True`, saves the fetched standings data as a JSON file. Defaults to `False`.
        enable_excel_export (bool): If `True`, saves the fetched standings data as an Excel file. Defaults to `False`.
    """
    if data_source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid data source: {data_source}. Must be one of {ALLOWED_SOURCES}")

    try:
        webdriver_instance = setup_webdriver()
        points_table_list = []

        def process_standings_data(data, category):
            return [
                {
                    "country": standing["tournament"]["category"]["name"],
                    "tournament": standing["tournament"]["name"],
                    "team_name": row["team"]["name"],
                    "team_id": row["team"]["id"],
                    "position": row["position"],
                    "matches": row["matches"],
                    "wins": row["wins"],
                    "draws": row["draws"],
                    "losses": row["losses"],
                    "scores_for": row["scoresFor"],
                    "scores_against": row["scoresAgainst"],
                    "points": row["points"],
                    "category": category.capitalize()
                }
                for standing in data.get("standings", []) for row in standing.get("rows", [])
            ]

        for category in ["total", "home", "away"]:
            api_request_url = f"{API_BASE_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/standings/{category}"
            webdriver_instance.get(api_request_url)

            try:
                response_element = WebDriverWait(webdriver_instance, element_load_timeout).until(
                    EC.visibility_of_element_located((By.TAG_NAME, "pre"))
                )
                standings_data = json.loads(response_element.text)
                points_table_list.extend(process_standings_data(standings_data, category))

            except TimeoutException:
                raise RuntimeError(f"Timeout while fetching standings data for category {category}.")
            except json.JSONDecodeError:
                raise RuntimeError(f"Failed to decode standings data for category {category}.")

        points_table_dataframe = pd.DataFrame(points_table_list)

        if points_table_dataframe.empty:
            raise ValueError("No standings data found for the specified parameters.")

        if enable_json_export or enable_excel_export:
            first_row = points_table_dataframe.iloc[0]

            if enable_json_export:
                save_json(
                    data=points_table_dataframe,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=None,
                    week_number=None
                )

            if enable_excel_export:
                save_excel(
                    data=points_table_dataframe,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=None,
                    week_number=None
                )

        return points_table_dataframe

    except WebDriverException as e:
        raise RuntimeError(f"Selenium WebDriver error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching standings data: {e.__class__.__name__} - {e}")

    finally:
        if webdriver_instance:
            webdriver_instance.quit()