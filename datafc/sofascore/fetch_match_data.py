import json
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datafc.utils._setup_webdriver import setup_webdriver
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import ALLOWED_SOURCES, API_BASE_URLS, TOURNAMENT_URL_PATTERNS

def match_data(
    tournament_id: int,
    season_id: int,
    week_number: int,
    tournament_type: str = None,
    tournament_stage: str = None,
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
        tournament_type (str, optional): The tournament type ('uefa'). If `None`, assumes league format.
            - 'uefa' is used for UEFA competitions such as 'ucl' (Champions League), 'uel' (Europa League), 'uecl' (Europa Conference League), or 'unl' (Nations League).
        tournament_stage (str, optional): The specific stage of the tournament (e.g., 'qualification_round', 'group_stage_week', 'round_of_16', etc.).
        data_source (str): The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        element_load_timeout (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
        enable_json_export (bool): If `True`, exports the fetched data as a JSON file. Defaults to `False`.
        enable_excel_export (bool): If `True`, exports the fetched data as an Excel file. Defaults to `False`.
    """
    if data_source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid data source: {data_source}. Must be one of {ALLOWED_SOURCES}")

    base_url = API_BASE_URLS[data_source]

    if tournament_type and tournament_type in TOURNAMENT_URL_PATTERNS:
        if tournament_type == "uefa":
            if not tournament_stage:
                raise ValueError("Please specify 'tournament_stage' (e.g., 'qualification_round', 'group_stage_week', 'round_of_16', etc.).")

            tournament_patterns = TOURNAMENT_URL_PATTERNS[tournament_type]

            if tournament_stage in tournament_patterns:
                if not week_number:
                    raise ValueError(f"Please provide 'week_number' for tournament stage '{tournament_stage}'.")

                url_template = tournament_patterns[tournament_stage]
                api_request_url = url_template.format(
                    base_url=base_url,
                    tournament_id=tournament_id,
                    season_id=season_id,
                    week_number=week_number
                )
            else:
                raise ValueError(f"Invalid tournament_stage '{tournament_stage}' for UEFA tournaments.")
        else:
            raise ValueError("Invalid tournament_type: Only 'uefa' is supported.")
    else:
        if not week_number:
            raise ValueError("Please provide 'week_number' for default tournament URL.")

        api_request_url = TOURNAMENT_URL_PATTERNS["default"].format(
            base_url=base_url,
            tournament_id=tournament_id,
            season_id=season_id,
            week_number=week_number
        )

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
            "status": events_df["status"].apply(lambda x: x.get("description", "")),
            "home_score_current": events_df["homeScore"].apply(lambda x: x.get("current", "")),
            "home_score_display": events_df["homeScore"].apply(lambda x: x.get("display", "")),
            "home_score_period1": events_df["homeScore"].apply(lambda x: x.get("period1", "")),
            "home_score_period2": events_df["homeScore"].apply(lambda x: x.get("period2", "")),
            "home_score_normaltime": events_df["homeScore"].apply(lambda x: x.get("normaltime", "")),
            "away_score_current": events_df["awayScore"].apply(lambda x: x.get("current", "")),
            "away_score_display": events_df["awayScore"].apply(lambda x: x.get("display", "")),
            "away_score_period1": events_df["awayScore"].apply(lambda x: x.get("period1", "")),
            "away_score_period2": events_df["awayScore"].apply(lambda x: x.get("period2", "")),
            "away_score_normaltime": events_df["awayScore"].apply(lambda x: x.get("normaltime", ""))
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