from datetime import datetime, timezone
from typing import Callable, Optional
import pandas as pd


def _ts_to_age(timestamp: Optional[int]) -> Optional[int]:
    if not timestamp:
        return None
    birth = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    today = datetime.now(tz=timezone.utc)
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _safe_apply(df: pd.DataFrame, col: str, func: Optional[Callable] = None):
    """Return df[col].apply(func) if col exists, else None (column filled with NaN)."""
    if col not in df.columns:
        return None
    return df[col].apply(func) if func is not None else df[col]


def _cast_int_cols(df: pd.DataFrame, *cols: str) -> pd.DataFrame:
    """Cast nullable ID columns to Int64 so they stay integer even when NaN is present."""
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype("Int64")
    return df
