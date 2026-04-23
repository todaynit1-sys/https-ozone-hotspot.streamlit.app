"""
preprocess.py — Quality control for mobile-measurement data

- GPS filtering: removes points outside a sane lat/lon box
- Stationary-point removal: removes consecutive duplicates when the vehicle is parked
- Hotspot labeling: top-quantile rule (default 25%)
"""
from __future__ import annotations
from typing import Tuple
import numpy as np
import pandas as pd

from .loader import LoadedData


def filter_gps(
    data: LoadedData,
    min_lat: float = 33.0, max_lat: float = 39.0,
    min_lon: float = 124.0, max_lon: float = 132.0,
) -> LoadedData:
    """Remove points with impossible GPS (outside Korean peninsula bounding box)."""
    df = data.df
    mask = (
        df[data.lat_col].between(min_lat, max_lat)
        & df[data.lon_col].between(min_lon, max_lon)
    )
    n_removed = (~mask).sum()
    if n_removed > 0:
        data.df = df[mask].reset_index(drop=True)
        data.n_valid = len(data.df)
    return data


def filter_stationary(data: LoadedData, min_move_m: float = 3.0) -> LoadedData:
    """
    Remove stationary points (vehicle parked).

    A point is stationary if the rolling distance to both neighbors is < min_move_m.
    Uses a simple flat-earth approximation (OK at sub-kilometer scale).
    """
    df = data.df
    if len(df) < 3:
        return data

    lat = df[data.lat_col].values
    lon = df[data.lon_col].values

    # Approx meters per degree (at ~37°N)
    MDEG_LAT = 111_000
    MDEG_LON = 88_500

    dlat = np.diff(lat) * MDEG_LAT
    dlon = np.diff(lon) * MDEG_LON
    step_m = np.sqrt(dlat**2 + dlon**2)

    # A point is "stationary" if both its incoming and outgoing steps are small
    prev_step = np.concatenate([[np.inf], step_m])
    next_step = np.concatenate([step_m, [np.inf]])
    stationary_mask = (prev_step < min_move_m) & (next_step < min_move_m)

    n_removed = stationary_mask.sum()
    if n_removed > 0:
        data.df = df[~stationary_mask].reset_index(drop=True)
        data.n_valid = len(data.df)

    return data


def label_hotspots(
    data: LoadedData,
    quantile: float = 0.75,
) -> Tuple[LoadedData, float]:
    """
    Add 'is_hotspot' boolean column (top `1-quantile` fraction of O3).

    Default quantile=0.75 means top 25% are hotspots (matches the paper).
    Returns (data_with_label, threshold_ppb).
    """
    if not 0.0 < quantile < 1.0:
        raise ValueError(f"quantile must be in (0,1); got {quantile}")
    threshold = data.df[data.o3_col].quantile(quantile)
    data.df["is_hotspot"] = (data.df[data.o3_col] >= threshold).astype(int)
    return data, float(threshold)


def preprocess(
    data: LoadedData,
    hotspot_quantile: float = 0.75,
    apply_stationary_filter: bool = False,
) -> Tuple[LoadedData, float]:
    """
    Apply the full QC pipeline and label hotspots. Returns (data, threshold).

    Parameters
    ----------
    data : LoadedData
        Loaded mobile measurement data.
    hotspot_quantile : float
        Quantile cutoff for hotspot label (default 0.75 = top 25%).
    apply_stationary_filter : bool
        Whether to remove stationary points (default False).

        The paper's published AUROCs (0.864, 0.814, 0.831, 0.888; mean 0.849)
        are reproduced with this filter OFF. Empirical verification showed
        that applying filter_stationary() drops 6–8% of points (e.g.,
        438 → 406 for Sihwa 6/18) and systematically lowers AUROC by
        0.01–0.02, breaking paper reproducibility. The source CSVs provided
        by the measurement team appear to have already been cleaned of
        true stationary segments, so applying the filter again is
        over-aggressive. Set True only if you know your raw data contains
        parked segments.
    """
    data = filter_gps(data)
    if apply_stationary_filter:
        data = filter_stationary(data)
    data, threshold = label_hotspots(data, hotspot_quantile)
    return data, threshold
