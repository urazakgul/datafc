from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS, WWW_URLS
from datafc.utils._validate import validate_source, build_tournament_url
from datafc.sofascore._core import past_match_record_from_event, export_df
from datafc.exceptions import DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def past_matches_data(
    tournament_id: int,
    season_id: int,
    week_number: Optional[int] = None,
    tournament_type: Optional[str] = None,
    tournament_stage: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches historical head-to-head match data for teams in the specified round."""
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
            all_matches.extend(past_match_record_from_event(ev) for ev in h2h_events)

    if not all_matches:
        raise DataNotAvailableError(
            f"No H2H match data found for tournament_id={tournament_id}, "
            f"season_id={season_id}, week_number={week_number}."
        )

    result_df = pd.DataFrame(all_matches)

    export_df(
        result_df, fn_name="past_matches_data", data_source=data_source,
        output_dir=output_dir,
        country=fn_country, tournament=fn_tournament, season=fn_season,
        week_number=week_number,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df
