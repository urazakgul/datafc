import json
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datafc.utils._setup_webdriver import setup_webdriver
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import ALLOWED_SOURCES, API_BASE_URLS

def squad_data(
    standings_df: pd.DataFrame,
    data_source: str = "sofascore",
    element_load_timeout: int = 10,
    enable_json_export: bool = False,
    enable_excel_export: bool = False
) -> pd.DataFrame:
    """
    Fetches squad data for each team in the provided standings dataset.

    Args:
        standings_df (pd.DataFrame): A DataFrame containing team metadata, including team_id.
        data_source (str): The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        element_load_timeout (int): The maximum time (in seconds) to wait for the API response. Defaults to `10`.
        enable_json_export (bool): If `True`, saves the fetched data as a JSON file. Defaults to `False`.
        enable_excel_export (bool): If `True`, saves the fetched data as an Excel file. Defaults to `False`.

    Returns:
        pd.DataFrame: A DataFrame containing squad information for each team.
    """
    if data_source not in ALLOWED_SOURCES:
        raise ValueError(f"Invalid data source: {data_source}. Must be one of {ALLOWED_SOURCES}")

    if standings_df is None or standings_df.empty:
        raise ValueError("Standings dataframe must be provided and cannot be empty.")

    webdriver_instance = None
    try:
        webdriver_instance = setup_webdriver()
        squads_data_list = []

        standings_df = standings_df[standings_df["category"] == "Total"]
        for _, row in standings_df.iterrows():
            country = row["country"]
            tournament = row["tournament"]
            team_name = row["team_name"]
            team_id = row["team_id"]

            url = f"{API_BASE_URLS[data_source]}/api/v1/team/{team_id}/players"
            webdriver_instance.get(url)

            try:
                pre_tag = WebDriverWait(webdriver_instance, element_load_timeout).until(
                    EC.visibility_of_element_located((By.TAG_NAME, "pre"))
                )

                squad_json = json.loads(pre_tag.text)

                for player_info in squad_json.get("players", []):
                    player = player_info["player"]
                    squads_data_list.append({
                        "country": country,
                        "tournament": tournament,
                        "team_name": team_name,
                        "team_id": team_id,
                        "player_name": player.get("name"),
                        "player_id": player.get("id"),
                        "age": player.get("dateOfBirthTimestamp"),
                        "height": player.get("height"),
                        "player_country": player.get("country", {}).get("name"),
                        "position": player.get("position"),
                        "preferred_foot": player.get("preferredFoot"),
                        "contract_until": player.get("contractUntilTimestamp"),
                        "market_value": player.get("proposedMarketValueRaw", {}).get("value"),
                        "market_currency": player.get("proposedMarketValueRaw", {}).get("currency")
                    })
            except TimeoutException:
                print(f"Timeout while fetching squad data for team_id {team_id}.")
            except json.JSONDecodeError:
                print(f"Failed to decode squad data for team_id {team_id}.")
            except WebDriverException as e:
                print(f"Selenium WebDriver error while fetching squad data for team_id {team_id}: {str(e)}")
            except Exception as e:
                print(f"Unexpected error while fetching squad data for team_id {team_id}: {e.__class__.__name__} - {e}")

        squads_data_df = pd.DataFrame(squads_data_list)

        if squads_data_df.empty:
            raise ValueError("No squad data found for the specified teams.")

        if enable_json_export or enable_excel_export:
            first_row = squads_data_df.iloc[0]

            if enable_json_export:
                save_json(
                    data=squads_data_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=None,
                    week_number=None
                )

            if enable_excel_export:
                save_excel(
                    data=squads_data_df,
                    data_source=data_source,
                    country=first_row["country"],
                    tournament=first_row["tournament"],
                    season=None,
                    week_number=None
                )

        return squads_data_df

    except WebDriverException as e:
        raise RuntimeError(f"Selenium WebDriver error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while fetching squad data: {e.__class__.__name__} - {e}")

    finally:
        if webdriver_instance:
            webdriver_instance.quit()