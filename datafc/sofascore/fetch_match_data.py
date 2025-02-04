import json
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datafc.utils._setup_webdriver import setup_webdriver
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import ALLOWED_SOURCES, API_BASE_URLS

def match_data(
    tournament_id: int,
    season_id: int,
    week_number: int,
    data_source: str = "sofascore",
    element_load_timeout: int = 10,
    enable_json_export: bool = False,
    enable_excel_export: bool = False
) -> pd.DataFrame:
    """
    Fetches match data for a specified tournament, season, and matchweek.

    Args:
        tournament_id (int): The unique identifier for the tournament.
        season_id (int): The unique identifier for the season.
        week_number (int): The matchweek number within the season.
        data_source (str): The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        element_load_timeout (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
        enable_json_export (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
        enable_excel_export (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.
    """
    if data_source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid data source: {data_source}. Must be one of {ALLOWED_SOURCES}")

    api_request_url = f"{API_BASE_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}"

    try:
        webdriver_instance = setup_webdriver()
        webdriver_instance.get(api_request_url)

        response_element = WebDriverWait(webdriver_instance, element_load_timeout).until(
            EC.visibility_of_element_located((By.TAG_NAME, "pre"))
        )
        response_text = response_element.text.strip()
        if not response_text:
            raise RuntimeError("API response is empty.")

        api_response_data = json.loads(response_text)
        if "events" not in api_response_data or not isinstance(api_response_data["events"], list):
            raise ValueError("Invalid API response format: 'events' key is missing or not a list.")

        events_df = pd.DataFrame(api_response_data.get("events", []))
        if events_df.empty:
            raise ValueError("No match data found for the specified parameters.")

        match_data_df = pd.DataFrame({
            "country": events_df["tournament"].apply(lambda x: x.get("category", {}).get("name", "")),
            "tournament": events_df["tournament"].apply(lambda x: x.get("name", "")),
            "season": events_df["season"].apply(lambda x: x.get("year", "")),
            "week": events_df["roundInfo"].apply(lambda x: x.get("round", "")),
            "game_id": events_df["id"],
            "home_team": events_df["homeTeam"].apply(lambda x: x.get("name", "")),
            "home_team_id": events_df["homeTeam"].apply(lambda x: x.get("id", "")),
            "away_team": events_df["awayTeam"].apply(lambda x: x.get("name", "")),
            "away_team_id": events_df["awayTeam"].apply(lambda x: x.get("id", "")),
            "injury_time_1": events_df["time"].apply(lambda x: x.get("injuryTime1", "")),
            "injury_time_2": events_df["time"].apply(lambda x: x.get("injuryTime2", "")),
            "start_timestamp": events_df["startTimestamp"],
            "status": events_df["status"].apply(lambda x: x.get("description", ""))
        })

        if enable_json_export or enable_excel_export:
            first_row = match_data_df.iloc[0]

            if enable_json_export:
                save_json(
                    data=match_data_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=first_row["season"],
                    week_number=first_row["week"]
                )

            if enable_excel_export:
                save_excel(
                    data=match_data_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=first_row["season"],
                    week_number=first_row["week"]
                )

        return match_data_df

    except TimeoutException:
        raise RuntimeError("Timeout occurred while waiting for the page or API response.")
    except WebDriverException as e:
        raise RuntimeError(f"Selenium WebDriver error: {str(e)}")
    except json.JSONDecodeError:
        raise RuntimeError("Failed to decode API response as JSON.")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching match data: {e.__class__.__name__} - {e}")

    finally:
        if webdriver_instance:
            webdriver_instance.quit()