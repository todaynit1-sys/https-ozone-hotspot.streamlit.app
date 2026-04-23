"""
loader.py — Mobile measurement CSV loader with automatic column detection

Handles:
- Korean headers and the common 'Longtitude' typo (used in-house)
- Variable O3 column names ('O3', 'O3 (ppb)')
- Variable NOx column names
- VOC column auto-discovery (any column with '(ppb)' suffix)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import pandas as pd
import numpy as np


@dataclass
class LoadedData:
    """Container for a single day's mobile measurement data."""
    df: pd.DataFrame
    voc_cols: List[str]
    o3_col: str
    nox_col: Optional[str]
    lat_col: str
    lon_col: str
    time_col: Optional[str]
    source_path: str
    n_raw: int
    n_valid: int

    def summary(self) -> str:
        return (
            f"Source: {self.source_path}\n"
            f"  Raw rows: {self.n_raw}  |  Valid: {self.n_valid}\n"
            f"  VOC species: {len(self.voc_cols)}\n"
            f"  O3 column: {self.o3_col}\n"
            f"  NOx column: {self.nox_col or '(not found)'}\n"
            f"  GPS: ({self.lat_col}, {self.lon_col})"
        )


# ---------------------------------------------------------------------------
# Column detection heuristics
# ---------------------------------------------------------------------------
_O3_CANDIDATES = ["O3 (ppb)", "O3", "O₃", "ozone (ppb)", "ozone", "오존"]
_NOX_CANDIDATES = ["NOx (ppb)", "NOx", "NOX", "NOx (ppb) ", "질소산화물"]
_LAT_CANDIDATES = ["Latitude", "lat", "LAT", "위도", "latitude"]
# Note: 'Longtitude' (typo) is used in in-house CSVs — handled first
_LON_CANDIDATES = ["Longtitude", "Longitude", "lon", "LON", "경도", "longitude"]
_TIME_CANDIDATES = ["측정 시간", "측정시간", "time", "Time", "DateTime", "timestamp"]


def _find_first(columns, candidates) -> Optional[str]:
    """Return the first candidate that exists in columns (case-sensitive first, then ci)."""
    col_set = set(columns)
    for c in candidates:
        if c in col_set:
            return c
    col_lower_map = {c.lower().strip(): c for c in columns}
    for c in candidates:
        key = c.lower().strip()
        if key in col_lower_map:
            return col_lower_map[key]
    return None


def _discover_voc_cols(columns, o3_col, nox_col) -> List[str]:
    """Return all columns with '(ppb)' suffix that are NOT O3 or NOx."""
    excluded = {o3_col, nox_col}
    excluded.discard(None)
    out = []
    for c in columns:
        if "(ppb)" not in c:
            continue
        if c in excluded:
            continue
        # Exclude anything that looks like an ozone/NOx/NO/NO2 column
        lower = c.lower()
        if any(tag in lower for tag in ["o3 ", "o3(", "ozone", "nox", "no2", "no "]):
            continue
        out.append(c)
    return out


def load_csv(
    path: str | Path,
    encoding: str = "utf-8-sig",
    require_nox: bool = False,
) -> LoadedData:
    """
    Load a mobile measurement CSV and auto-detect columns.

    Parameters
    ----------
    path : str or Path
        Path to the CSV file.
    encoding : str
        Text encoding (default 'utf-8-sig' handles Korean files with BOM).
    require_nox : bool
        If True, raises when NOx column cannot be found. Default False
        because NOx is not used as an AI input (VOC-only design).

    Returns
    -------
    LoadedData
        Container with cleaned DataFrame and detected column names.

    Raises
    ------
    FileNotFoundError : if path does not exist.
    ValueError : if required columns (O3, GPS, any VOC) are missing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    try:
        df_raw = pd.read_csv(path, encoding=encoding)
    except UnicodeDecodeError:
        # Retry with cp949 (older Korean Windows encoding)
        df_raw = pd.read_csv(path, encoding="cp949")

    cols = list(df_raw.columns)
    n_raw = len(df_raw)

    # Detect key columns
    o3_col = _find_first(cols, _O3_CANDIDATES)
    nox_col = _find_first(cols, _NOX_CANDIDATES)
    lat_col = _find_first(cols, _LAT_CANDIDATES)
    lon_col = _find_first(cols, _LON_CANDIDATES)
    time_col = _find_first(cols, _TIME_CANDIDATES)

    # Validate required
    missing = []
    if o3_col is None:
        missing.append(f"O3 column (tried: {_O3_CANDIDATES})")
    if lat_col is None:
        missing.append(f"Latitude column (tried: {_LAT_CANDIDATES})")
    if lon_col is None:
        missing.append(f"Longitude column (tried: {_LON_CANDIDATES})")
    if require_nox and nox_col is None:
        missing.append(f"NOx column (tried: {_NOX_CANDIDATES})")
    if missing:
        raise ValueError(
            f"Required columns not found in {path.name}:\n  - "
            + "\n  - ".join(missing)
            + f"\n\nAvailable columns: {cols[:10]}..."
        )

    # Discover VOC columns
    voc_cols = _discover_voc_cols(cols, o3_col, nox_col)
    if len(voc_cols) < 5:
        raise ValueError(
            f"Too few VOC columns discovered ({len(voc_cols)}) in {path.name}. "
            "Expected columns with '(ppb)' suffix. Check the CSV header."
        )

    # Build clean DataFrame
    keep_cols = [o3_col, lat_col, lon_col] + voc_cols
    if nox_col:
        keep_cols.append(nox_col)
    if time_col:
        keep_cols.append(time_col)
    df = df_raw[keep_cols].copy()

    # Coerce numerics
    numeric_cols = [o3_col, lat_col, lon_col] + voc_cols
    if nox_col:
        numeric_cols.append(nox_col)
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows missing O3 / GPS / any VOC
    required_numeric = [o3_col, lat_col, lon_col] + voc_cols
    df = df.dropna(subset=required_numeric).reset_index(drop=True)

    n_valid = len(df)
    if n_valid < 50:
        raise ValueError(
            f"Too few valid measurement points after cleaning ({n_valid} < 50) in {path.name}. "
            "Check for data quality issues."
        )

    return LoadedData(
        df=df,
        voc_cols=voc_cols,
        o3_col=o3_col,
        nox_col=nox_col,
        lat_col=lat_col,
        lon_col=lon_col,
        time_col=time_col,
        source_path=str(path),
        n_raw=n_raw,
        n_valid=n_valid,
    )
