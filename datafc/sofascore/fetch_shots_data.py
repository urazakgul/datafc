import json
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datafc.utils._setup_webdriver import setup_webdriver
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import ALLOWED_SOURCES, API_BASE_URLS

def shots_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    element_load_timeout: int = 10,
    enable_json_export: bool = False,
    enable_excel_export: bool = False
) -> pd.DataFrame:
    """
    Fetches shot data for each match in the provided match dataset.

    Args:
        match_df (pd.DataFrame): A DataFrame containing match metadata,
            which should be generated by the `match_data` function.
        data_source (str): The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        element_load_timeout (int): The maximum time (in seconds) to wait for the API response. Defaults to 10.
        enable_json_export (bool): If `True`, saves the fetched shot data as a JSON file. Defaults to `False`.
        enable_excel_export (bool): If `True`, saves the fetched shot data as an Excel file. Defaults to `False`.
    """
    if data_source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid data source: {data_source}. Must be one of {ALLOWED_SOURCES}")

    if match_df is None or match_df.empty:
        raise ValueError("Match dataframe must be provided and cannot be empty.")

    try:
        webdriver_instance = setup_webdriver()
        shotmap_list = []

        def safe_get(data, *keys, default=None):
            for key in keys:
                if isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    return default
            return data

        for _, row in match_df.iterrows():
            country, tournament, season, week, game_id = row[
                ["country", "tournament", "season", "week", "game_id"]
            ]

            api_request_url = f"{API_BASE_URLS[data_source]}/api/v1/event/{game_id}/shotmap"
            webdriver_instance.get(api_request_url)

            try:
                response_element = WebDriverWait(webdriver_instance, element_load_timeout).until(
                    EC.visibility_of_element_located((By.TAG_NAME, "pre"))
                )
                shotmap_json_data = json.loads(response_element.text).get("shotmap", [])

                for shot in shotmap_json_data:
                    shotmap_list.append({
                        "country": country,
                        "tournament": tournament,
                        "season": season,
                        "week": week,
                        "game_id": game_id,
                        "player_name": safe_get(shot, "player", "name"),
                        "player_id": safe_get(shot, "player", "id"),
                        "player_position": safe_get(shot, "player", "position"),
                        "is_home": shot.get("isHome"),
                        "incident_type": shot.get("incidentType"),
                        "shot_type": shot.get("shotType"),
                        "body_part": shot.get("bodyPart"),
                        "goal_type": shot.get("goalType"),
                        "situation": shot.get("situation"),
                        "goal_mouth_location": shot.get("goalMouthLocation"),
                        "xg": shot.get("xg"),
                        "xgot": shot.get("xgot"),
                        "player_coordinates_x": safe_get(shot, "playerCoordinates", "x"),
                        "player_coordinates_y": safe_get(shot, "playerCoordinates", "y"),
                        "player_coordinates_z": safe_get(shot, "playerCoordinates", "z"),
                        "goal_mouth_coordinates_x": safe_get(shot, "goalMouthCoordinates", "x"),
                        "goal_mouth_coordinates_y": safe_get(shot, "goalMouthCoordinates", "y"),
                        "goal_mouth_coordinates_z": safe_get(shot, "goalMouthCoordinates", "z"),
                        "draw_start_x": safe_get(shot, "draw", "start", "x"),
                        "draw_start_y": safe_get(shot, "draw", "start", "y"),
                        "draw_end_x": safe_get(shot, "draw", "end", "x"),
                        "draw_end_y": safe_get(shot, "draw", "end", "y"),
                        "draw_goal_x": safe_get(shot, "draw", "goal", "x"),
                        "draw_goal_y": safe_get(shot, "draw", "goal", "y"),
                        "block_coordinates_x": safe_get(shot, "blockCoordinates", "x"),
                        "block_coordinates_y": safe_get(shot, "blockCoordinates", "y"),
                        "block_coordinates_z": safe_get(shot, "blockCoordinates", "z"),
                        "time": shot.get("time"),
                        "time_seconds": shot.get("timeSeconds"),
                        "added_time": int(shot.get("addedTime", 0) if pd.notna(shot.get("addedTime", 0)) else 0)
                    })

            except TimeoutException:
                raise RuntimeError(f"Timeout while fetching shot data for game {game_id}.")
            except json.JSONDecodeError:
                raise RuntimeError(f"Failed to decode shot data for game {game_id}.")

        shotmap_df = pd.DataFrame(shotmap_list)

        if shotmap_df.empty:
            raise ValueError("No shot data found for the specified parameters.")

        if enable_json_export or enable_excel_export:
            first_row = shotmap_df.iloc[0]

            if enable_json_export:
                save_json(
                    data=shotmap_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=first_row["season"],
                    week_number=first_row["week"]
                )

            if enable_excel_export:
                save_excel(
                    data=shotmap_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=first_row["season"],
                    week_number=first_row["week"]
                )

        return shotmap_df

    except WebDriverException as e:
        raise RuntimeError(f"Selenium WebDriver error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching shot data: {e.__class__.__name__} - {e}")

    finally:
        if webdriver_instance:
            webdriver_instance.quit()