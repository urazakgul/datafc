from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS, WWW_URLS
from datafc.utils._validate import validate_source, build_tournament_url
from datafc.exceptions import DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def past_matches_data(
    tournament_id: int,
    season_id: int,
    week_number: int,
    tournament_type: Optional[str] = None,
    tournament_stage: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """
    Fetches historical head-to-head match data for teams in the specified round.

    Args:
        tournament_id: The unique identifier for the tournament.
        season_id: The unique identifier for the season.
        week_number: The matchweek number within the season.
        tournament_type: The tournament type ('uefa'). If None, assumes league format.
        tournament_stage: The specific stage of the tournament (e.g., 'group_stage_week', 'round_of_16').
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, saves output as JSON. Defaults to False.
        enable_excel_export: If True, saves output as Excel. Defaults to False.

    Returns:
        Historical match data for the teams playing in the specified round.

    Raises:
        InvalidParameterError: If an invalid data_source, tournament_type, or tournament_stage is given.
        DataNotAvailableError: If no match data is found.
        APIError: On HTTP errors from the Sofascore API.
    """
    validate_source(data_source)
    round_url = build_tournament_url(
        base_url=API_URLS[data_source],
        tournament_id=tournament_id,
        season_id=season_id,
        week_number=week_number,
        tournament_type=tournament_type,
        tournament_stage=tournament_stage,
    )

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        round_data = client.get(round_url)

        events = round_data.get("events")
        if not isinstance(events, list) or not events:
            raise DataNotAvailableError(
                f"No match data found for tournament_id={tournament_id}, "
                f"season_id={season_id}, week_number={week_number}."
            )

        first_event = events[0]
        fn_country = first_event.get("tournament", {}).get("category", {}).get("name", "")
        fn_tournament = first_event.get("tournament", {}).get("name", "")
        fn_season = first_event.get("season", {}).get("year", "")

        events_df = pd.DataFrame(events)
        if "customId" not in events_df.columns:
            raise DataNotAvailableError(
                f"customId field missing in API response for tournament_id={tournament_id}, "
                f"season_id={season_id}, week_number={week_number}."
            )
        custom_ids = events_df["customId"].dropna().tolist()
        all_matches = []

        for custom_id in custom_ids:
            h2h_url = f"{WWW_URLS[data_source]}/api/v1/event/{custom_id}/h2h/events"
            h2h_data = client.get(h2h_url)

            h2h_events = h2h_data.get("events")
            if not isinstance(h2h_events, list):
                continue

            for event in h2h_events:
                all_matches.append({
                    "country": event.get("tournament", {}).get("category", {}).get("name", ""),
                    "tournament": event.get("tournament", {}).get("name", ""),
                    "season": event.get("season", {}).get("year", ""),
                    "week": event.get("roundInfo", {}).get("round", ""),
                    "game_id": event.get("id", ""),
                    "home_team": event.get("homeTeam", {}).get("name", ""),
                    "home_team_id": event.get("homeTeam", {}).get("id", ""),
                    "away_team": event.get("awayTeam", {}).get("name", ""),
                    "away_team_id": event.get("awayTeam", {}).get("id", ""),
                    "injury_time_1": event.get("time", {}).get("injuryTime1", ""),
                    "injury_time_2": event.get("time", {}).get("injuryTime2", ""),
                    "start_timestamp": event.get("startTimestamp", ""),
                    "status": event.get("status", {}).get("description", ""),
                    "home_score_current": event.get("homeScore", {}).get("current", ""),
                    "home_score_display": event.get("homeScore", {}).get("display", ""),
                    "home_score_period1": event.get("homeScore", {}).get("period1", ""),
                    "home_score_period2": event.get("homeScore", {}).get("period2", ""),
                    "home_score_normaltime": event.get("homeScore", {}).get("normaltime", ""),
                    "away_score_current": event.get("awayScore", {}).get("current", ""),
                    "away_score_display": event.get("awayScore", {}).get("display", ""),
                    "away_score_period1": event.get("awayScore", {}).get("period1", ""),
                    "away_score_period2": event.get("awayScore", {}).get("period2", ""),
                    "away_score_normaltime": event.get("awayScore", {}).get("normaltime", ""),
                })

    if not all_matches:
        raise DataNotAvailableError(
            f"No H2H match data found for tournament_id={tournament_id}, "
            f"season_id={season_id}, week_number={week_number}."
        )

    result_df = pd.DataFrame(all_matches)

    if enable_json_export or enable_excel_export:
        kwargs = dict(
            fn_name="past_matches_data",
            data_source=data_source,
            country=fn_country,
            tournament=fn_tournament,
            season=fn_season,
            week_number=week_number,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df
