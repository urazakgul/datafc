import json
import pandas as pd
import inspect

def save_json(data: pd.DataFrame, data_source: str,  country: str, tournament: int, season: int = None, week_number: int = None) -> None:
    calling_function = inspect.stack()[1].function

    country = country.lower().replace(" ", "_")
    tournament = tournament.lower().replace(" ", "_")

    if season is not None:
        if isinstance(season, str) and "/" in season:
            season = season.replace("/", "")

    if season is not None and week_number is not None:
        file_name = f"{data_source}_{country}_{tournament}_{season}_{week_number}_{calling_function}.json"
    elif season is not None:
        file_name = f"{data_source}_{country}_{tournament}_{season}_{calling_function}.json"
    else:
        file_name = f"{data_source}_{country}_{tournament}_{calling_function}.json"

    try:
        with open(file_name, "w", encoding="utf-8") as json_file:
            json.dump(data.to_dict(orient="records"), json_file, ensure_ascii=False, indent=4)
        print(f"JSON file saved: {file_name}")
    except Exception as e:
        print(f"Error saving JSON: {e}")

def save_excel(data: pd.DataFrame, data_source: str, country: str, tournament: int, season: int = None, week_number: int = None) -> None:
    calling_function = inspect.stack()[1].function

    country = country.lower().replace(" ", "_")
    tournament = tournament.lower().replace(" ", "_")

    if season is not None:
        if isinstance(season, str) and "/" in season:
            season = season.replace("/", "")

    if season is not None and week_number is not None:
        file_name = f"{data_source}_{country}_{tournament}_{season}_{week_number}_{calling_function}.xlsx"
    elif season is not None:
        file_name = f"{data_source}_{country}_{tournament}_{season}_{calling_function}.xlsx"
    else:
        file_name = f"{data_source}_{country}_{tournament}_{calling_function}.xlsx"

    try:
        data.to_excel(file_name, index=False)
        print(f"Excel file saved: {file_name}")
    except Exception as e:
        print(f"Error saving Excel: {e}")