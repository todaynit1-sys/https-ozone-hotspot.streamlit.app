"""
validate.py — Pre-flight CSV format check

Before running the full diagnosis, users can call this to confirm that
their CSV file will be parsed correctly.  Returns a structured report
of what was detected and any issues.

Usage:
    from ozone_hotspot.validate import validate_csv
    report = validate_csv("my_data.csv")
    print(report.summary())
    if report.is_valid:
        from ozone_hotspot import diagnose
        diagnose("my_data.csv")
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd

from .loader import (
    _O3_CANDIDATES, _NOX_CANDIDATES,
    _LAT_CANDIDATES, _LON_CANDIDATES, _TIME_CANDIDATES,
    _find_first, _discover_voc_cols,
)


@dataclass
class ValidationReport:
    """Pre-flight check result."""
    file_path: str
    is_valid: bool
    n_rows: int
    n_columns: int

    # Detected columns
    o3_col: Optional[str]
    nox_col: Optional[str]
    no_col: Optional[str]
    no2_col: Optional[str]
    lat_col: Optional[str]
    lon_col: Optional[str]
    time_col: Optional[str]
    voc_cols: List[str] = field(default_factory=list)

    # Issues
    errors: List[str] = field(default_factory=list)   # Must fix — cannot run
    warnings: List[str] = field(default_factory=list) # Should check — will run
    notes: List[str] = field(default_factory=list)    # FYI

    def summary(self) -> str:
        lines = []
        status = "✓ VALID" if self.is_valid else "✗ INVALID"
        lines.append(f"{'=' * 70}")
        lines.append(f"  Format validation — {status}")
        lines.append(f"{'=' * 70}")
        lines.append(f"  File: {self.file_path}")
        lines.append(f"  Rows: {self.n_rows}  |  Columns: {self.n_columns}")
        lines.append("")
        lines.append("  Column detection:")
        lines.append(f"    O3        : {self.o3_col or '(NOT FOUND)'}")
        lines.append(f"    NOx       : {self.nox_col or '(not found)'}")
        lines.append(f"    NO        : {self.no_col or '(not found)'}")
        lines.append(f"    NO2       : {self.no2_col or '(not found)'}")
        lines.append(f"    Latitude  : {self.lat_col or '(NOT FOUND)'}")
        lines.append(f"    Longitude : {self.lon_col or '(NOT FOUND)'}")
        lines.append(f"    Time      : {self.time_col or '(not found — OK, optional)'}")
        lines.append(f"    VOC count : {len(self.voc_cols)}  (columns with '(ppb)' suffix)")

        if self.errors:
            lines.append("")
            lines.append("  ❌ ERRORS (must fix):")
            for e in self.errors:
                lines.append(f"     • {e}")
        if self.warnings:
            lines.append("")
            lines.append("  ⚠️  WARNINGS (should check):")
            for w in self.warnings:
                lines.append(f"     • {w}")
        if self.notes:
            lines.append("")
            lines.append("  💡 NOTES:")
            for n in self.notes:
                lines.append(f"     • {n}")

        lines.append("")
        if self.is_valid:
            lines.append("  → Ready for diagnose()")
        else:
            lines.append("  → Fix errors above before running diagnose()")
        lines.append(f"{'=' * 70}")
        return "\n".join(lines)


# Additional candidate lists for NO, NO2 (not used as inputs but good to report)
_NO_CANDIDATES = ["NO (ppb)", "NO", "일산화질소"]
_NO2_CANDIDATES = ["NO2 (ppb)", "NO₂ (ppb)", "NO2", "이산화질소"]


def validate_csv(path: str | Path, encoding: str = "utf-8-sig") -> ValidationReport:
    """
    Check if a CSV has all fields needed for diagnosis, without actually running it.

    Produces a human-readable report and flags anything unusual.
    """
    path = Path(path)
    report = ValidationReport(
        file_path=str(path),
        is_valid=False,
        n_rows=0,
        n_columns=0,
        o3_col=None, nox_col=None, no_col=None, no2_col=None,
        lat_col=None, lon_col=None, time_col=None,
    )

    # --- File exists ---
    if not path.exists():
        report.errors.append(f"File not found: {path}")
        return report

    # --- Readable as CSV ---
    try:
        df = pd.read_csv(path, encoding=encoding)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(path, encoding="cp949")
            report.notes.append("File read with cp949 encoding (older Korean Windows format).")
        except Exception as e:
            report.errors.append(f"Cannot read CSV: {e}")
            return report
    except Exception as e:
        report.errors.append(f"Cannot read CSV: {e}")
        return report

    report.n_rows = len(df)
    report.n_columns = len(df.columns)
    cols = list(df.columns)

    # --- Detect columns ---
    report.o3_col = _find_first(cols, _O3_CANDIDATES)
    report.nox_col = _find_first(cols, _NOX_CANDIDATES)
    report.no_col = _find_first(cols, _NO_CANDIDATES)
    report.no2_col = _find_first(cols, _NO2_CANDIDATES)
    report.lat_col = _find_first(cols, _LAT_CANDIDATES)
    report.lon_col = _find_first(cols, _LON_CANDIDATES)
    report.time_col = _find_first(cols, _TIME_CANDIDATES)
    report.voc_cols = _discover_voc_cols(cols, report.o3_col, report.nox_col)

    # --- Required checks ---
    if report.o3_col is None:
        report.errors.append(
            f"O3 column not found. Expected one of: {', '.join(_O3_CANDIDATES[:4])}."
        )
    if report.lat_col is None:
        report.errors.append(
            f"Latitude column not found. Expected one of: {', '.join(_LAT_CANDIDATES[:4])}."
        )
    if report.lon_col is None:
        report.errors.append(
            f"Longitude column not found. Expected one of: {', '.join(_LON_CANDIDATES[:4])}. "
            "Note: the typo 'Longtitude' is supported."
        )
    if len(report.voc_cols) < 5:
        report.errors.append(
            f"Too few VOC columns found ({len(report.voc_cols)}). Expected >=5. "
            "VOC columns must end in '(ppb)'."
        )

    # --- Nice-to-have checks ---
    if report.nox_col is None:
        if report.no_col or report.no2_col:
            report.warnings.append(
                "NOx column not found, but NO or NO2 detected. "
                "This is OK for analysis (NOx is not used as AI input), "
                "but consider adding a NOx column for VOC/NOx regime analysis."
            )
        else:
            report.notes.append(
                "No NOx/NO/NO2 columns found. "
                "Not required for hotspot identification (VOC-only design)."
            )

    if report.time_col is None:
        report.notes.append(
            "Time column not found. Not required, but useful for time-series views."
        )

    # --- Data quality checks (if we can) ---
    if report.o3_col and report.o3_col in df.columns:
        o3_numeric = pd.to_numeric(df[report.o3_col], errors="coerce")
        n_o3_valid = o3_numeric.notna().sum()
        n_o3_missing = len(df) - n_o3_valid
        if n_o3_missing > 0:
            pct = 100 * n_o3_missing / len(df)
            if pct > 20:
                report.warnings.append(
                    f"O3 has {n_o3_missing} missing/invalid values ({pct:.1f}%). "
                    "These rows will be dropped."
                )
            else:
                report.notes.append(
                    f"O3 has {n_o3_missing} missing values ({pct:.1f}%) — will be dropped."
                )

        if n_o3_valid > 0:
            o3_range = (o3_numeric.min(), o3_numeric.max())
            # Typical tropospheric O3 is 10–150 ppb. Flag if way outside.
            if o3_range[1] > 300:
                report.warnings.append(
                    f"O3 max is {o3_range[1]:.1f} — unusually high. "
                    "Verify units are ppb (not μg/m³, which would be ~2x higher)."
                )
            elif o3_range[1] < 20:
                report.warnings.append(
                    f"O3 max is only {o3_range[1]:.1f} — unusually low for a mobile "
                    "measurement campaign. Verify column is the right one."
                )
            report.notes.append(
                f"O3 range: {o3_range[0]:.1f}–{o3_range[1]:.1f} ppb (valid rows: {n_o3_valid})."
            )

    if report.lat_col and report.lon_col:
        lat = pd.to_numeric(df[report.lat_col], errors="coerce")
        lon = pd.to_numeric(df[report.lon_col], errors="coerce")
        n_gps_valid = (lat.notna() & lon.notna()).sum()
        if n_gps_valid < len(df):
            pct = 100 * (len(df) - n_gps_valid) / len(df)
            msg = f"GPS missing for {len(df) - n_gps_valid} rows ({pct:.1f}%) — will be dropped."
            if pct > 20:
                report.warnings.append(msg)
            else:
                report.notes.append(msg)
        # Korean peninsula sanity bounds
        valid_mask = lat.between(33, 39) & lon.between(124, 132)
        n_outside = n_gps_valid - valid_mask.sum()
        if n_outside > 0:
            pct = 100 * n_outside / max(1, n_gps_valid)
            report.warnings.append(
                f"{n_outside} GPS points ({pct:.1f}%) are outside Korea's bounding box. "
                "Check for swapped lat/lon, or drift. These rows will be filtered."
            )

    if len(report.voc_cols) > 0:
        # Count rows with at least one missing VOC
        voc_df = df[report.voc_cols].apply(pd.to_numeric, errors="coerce")
        n_any_missing = voc_df.isna().any(axis=1).sum()
        if n_any_missing > 0:
            pct = 100 * n_any_missing / len(df)
            if pct > 30:
                report.warnings.append(
                    f"{n_any_missing} rows ({pct:.1f}%) have at least one missing VOC. "
                    "These will be dropped — result may have few points left."
                )
            else:
                report.notes.append(
                    f"{n_any_missing} rows ({pct:.1f}%) have missing VOCs — will be dropped."
                )

    # --- Final valid flag ---
    report.is_valid = len(report.errors) == 0
    return report


def validate_files(paths: List[str | Path]) -> List[ValidationReport]:
    """Validate multiple files, return list of reports."""
    return [validate_csv(p) for p in paths]
