"""
diagnose.py — High-level pipeline for single- and multi-day diagnosis

Intended as the primary user entry point:

    from ozone_hotspot import diagnose
    result = diagnose("250618_시화.csv")
    result.save_all("output/")
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import json
import pandas as pd
import numpy as np

from .loader import load_csv, LoadedData
from .preprocess import preprocess
from .classifier import classify, ClassificationResult
from .interpret import interpret, InterpretationResult, ofp_ranking
from .visualize import plot_hotspot_map, plot_voc_priority
from .site_profile import SiteProfile, guess_profile_from_filename


@dataclass
class DiagnosisResult:
    """Per-day diagnosis output."""
    site_day: str                   # human-readable label (from filename)
    data: LoadedData
    threshold: float                # hotspot threshold (ppb)
    classification: ClassificationResult
    interpretation: InterpretationResult
    site_profile: Optional[SiteProfile] = None

    def summary(self) -> str:
        base = (
            f"========== {self.site_day} ==========\n"
            f"{self.data.summary()}\n"
            f"\n"
            f"Hotspot threshold: {self.threshold:.2f} ppb (top 25%)\n"
            f"{self.classification.summary()}\n"
            f"\n"
            f"{self.interpretation.summary(n=10)}\n"
        )

        # If a site profile is attached, add cross-check section
        if self.site_profile and self.site_profile.expected_top_vocs:
            top_vocs = self.interpretation.voc_importance.head(10)["voc"].tolist()
            check = self.site_profile.check_expected_vs_actual(top_vocs, n=10)
            base += (
                f"\n  Site profile: {self.site_profile.display_name}\n"
                f"  ({self.site_profile.site_type})\n"
                f"    Expected VOCs found in Top 10:  {len(check['matched'])}\n"
                f"      {', '.join(check['matched']) if check['matched'] else '(none)'}\n"
                f"    Unexpected VOCs in Top 10:\n"
                f"      {', '.join(check['unexpected_high'][:5]) if check['unexpected_high'] else '(none)'}\n"
                f"    Expected VOCs missing from Top 10:\n"
                f"      {', '.join(check['missing_expected']) if check['missing_expected'] else '(none)'}\n"
            )
        return base

    def per_point_table(self) -> pd.DataFrame:
        """Return a DataFrame with (lat, lon, O3, is_hotspot, P_hotspot)."""
        d = self.data
        out = d.df[[d.lat_col, d.lon_col, d.o3_col, "is_hotspot"]].copy()
        out.columns = ["latitude", "longitude", "o3_ppb", "is_hotspot"]
        out["p_hotspot"] = self.classification.y_pred_proba
        return out

    def voc_ranking_table(self) -> pd.DataFrame:
        """SHAP-based VOC ranking + OFP reference, merged."""
        shap_df = self.interpretation.voc_importance.rename(
            columns={"shap_importance": "shap_value", "rank": "shap_rank"}
        )
        ofp_df = ofp_ranking(self.data.df, self.data.voc_cols).rename(
            columns={"ofp_contribution": "ofp_value", "rank": "ofp_rank"}
        )
        merged = shap_df.merge(ofp_df[["voc", "ofp_value", "mir", "ofp_rank"]],
                                on="voc", how="left")
        return merged

    def shap_vs_ofp_spearman(self, top_n: int = 15) -> dict:
        """
        Spearman rank correlation between SHAP-based and OFP-based VOC rankings.

        Restricts to VOCs appearing in the top-N of either ranking and for which
        a MIR coefficient is available. Matches the paper's Section 3.5 analysis
        (reported ρ = +0.13, p = 0.42, n = 15 across four high-O₃ days).

        Returns a dict with 'rho', 'p_value', 'n', and the subset DataFrame used.
        """
        from scipy.stats import spearmanr
        tbl = self.voc_ranking_table()
        # Consider only VOCs with a defined OFP (MIR available)
        tbl = tbl.dropna(subset=["ofp_rank", "shap_rank"])
        # Restrict to union of top-N from either ranking
        keep = (tbl["shap_rank"] <= top_n) | (tbl["ofp_rank"] <= top_n)
        subset = tbl[keep].copy()
        if len(subset) < 3:
            return {"rho": float("nan"), "p_value": float("nan"),
                    "n": len(subset), "subset": subset}
        rho, pval = spearmanr(subset["shap_rank"], subset["ofp_rank"])
        return {
            "rho": float(rho),
            "p_value": float(pval),
            "n": int(len(subset)),
            "subset": subset[["voc", "shap_rank", "ofp_rank",
                              "shap_value", "ofp_value", "mir"]],
        }

    # --- file outputs --------------------------------------------------------
    def save_all(self, out_dir: str | Path) -> dict:
        """
        Save the complete per-day output bundle:
          - hotspot_map.png
          - ai_score_map.png  (P(hotspot) colored instead of O3)
          - voc_priority.png
          - per_point.csv
          - voc_ranking.csv
          - summary.txt
          - summary.json (for programmatic use)
        Returns a dict mapping logical name -> Path.
        """
        out = Path(out_dir) / self.site_day
        out.mkdir(parents=True, exist_ok=True)
        paths = {}

        # Figures
        paths["hotspot_map"] = plot_hotspot_map(
            self.data, self.classification, self.threshold,
            out / "hotspot_map.png",
            title=f"{self.site_day} — observed O3",
            use_ai_score=False,
        )
        paths["ai_score_map"] = plot_hotspot_map(
            self.data, self.classification, self.threshold,
            out / "ai_score_map.png",
            title=f"{self.site_day} — AI P(hotspot)",
            use_ai_score=True,
        )
        paths["voc_priority"] = plot_voc_priority(
            self.interpretation, out / "voc_priority.png",
            title=f"{self.site_day} — VOC priority (SHAP-based)",
        )

        # Tables
        paths["per_point"] = out / "per_point.csv"
        self.per_point_table().to_csv(paths["per_point"], index=False, encoding="utf-8-sig")

        paths["voc_ranking"] = out / "voc_ranking.csv"
        self.voc_ranking_table().to_csv(paths["voc_ranking"], index=False, encoding="utf-8-sig")

        # Text summaries
        paths["summary_txt"] = out / "summary.txt"
        with open(paths["summary_txt"], "w", encoding="utf-8") as f:
            f.write(self.summary())

        paths["summary_json"] = out / "summary.json"
        meta = {
            "site_day": self.site_day,
            "n_points": self.data.n_valid,
            "n_hotspots": int(self.classification.y_true.sum()),
            "hotspot_threshold_ppb": round(self.threshold, 2),
            "auroc": round(self.classification.auroc, 3),
            "fold_aurocs": [round(a, 3) for a in self.classification.fold_aurocs],
            "top10_voc": self.interpretation.voc_importance.head(10)["voc"].tolist(),
            "interpretation_method": self.interpretation.method,
            "o3_range_ppb": [round(float(self.data.df[self.data.o3_col].min()), 1),
                              round(float(self.data.df[self.data.o3_col].max()), 1)],
            "o3_mean_ppb": round(float(self.data.df[self.data.o3_col].mean()), 2),
        }
        if self.site_profile:
            meta["site_profile"] = {
                "id": self.site_profile.site_id,
                "name": self.site_profile.display_name,
                "type": self.site_profile.site_type,
            }
        with open(paths["summary_json"], "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return {k: str(v) for k, v in paths.items()}


def _site_day_from_path(path: str | Path) -> str:
    """
    Produce a short, filesystem-safe label from a CSV filename.

    Strategy: try to extract a YYYYMMDD or YYMMDD date and optionally
    a recognizable site keyword. Falls back to a sanitized stem.
    """
    import re
    stem = Path(path).stem
    # Try to extract YYMMDD or YYYYMMDD
    m = re.search(r'(\d{8}|\d{6})', stem)
    date_part = m.group(1) if m else ""
    # Normalize to YYYY-MM-DD if possible
    if len(date_part) == 8:
        date_norm = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
    elif len(date_part) == 6:
        date_norm = f"20{date_part[:2]}-{date_part[2:4]}-{date_part[4:]}"
    else:
        date_norm = ""

    # Detect site
    stem_lower = stem.lower()
    site = ""
    if "시화" in stem or "sihwa" in stem_lower:
        site = "Sihwa"
    elif "화성" in stem or "hwaseong" in stem_lower or "바이오" in stem:
        site = "Hwaseong"
    elif "반월" in stem or "banwol" in stem_lower:
        site = "Banwol"
    elif "울산" in stem or "ulsan" in stem_lower:
        site = "Ulsan"

    if date_norm and site:
        return f"{site}_{date_norm}"
    if date_norm:
        return date_norm
    # Fallback: strip non-ASCII
    safe = re.sub(r'[^\x00-\x7F]+', '', stem).strip('_ -')
    return safe if safe else "SiteDay"


def diagnose(
    csv_path: str | Path,
    hotspot_quantile: float = 0.75,
    site_profile: Optional[SiteProfile] = None,
    auto_detect_site: bool = True,
    apply_stationary_filter: bool = False,
) -> DiagnosisResult:
    """
    End-to-end single-day diagnosis.

    Parameters
    ----------
    csv_path : path-like
        Path to a mobile measurement CSV.
    hotspot_quantile : float
        Quantile cutoff for hotspot label. Default 0.75 = top 25% (paper default).
    site_profile : SiteProfile, optional
        Explicit site profile to use (overrides auto-detection).
    auto_detect_site : bool
        If True (default) and site_profile is None, guess profile from filename.
    apply_stationary_filter : bool
        If True, remove stationary points (vehicle parked). Default False, which
        matches the paper's published AUROCs. Set True only if your raw data
        contains parked segments that were not pre-cleaned. See
        preprocess.preprocess() docstring for details.

    Returns
    -------
    DiagnosisResult
    """
    data = load_csv(csv_path)
    data, threshold = preprocess(
        data,
        hotspot_quantile=hotspot_quantile,
        apply_stationary_filter=apply_stationary_filter,
    )
    clf_result = classify(data)
    X = data.df[data.voc_cols].values
    interp_result = interpret(clf_result, X)

    # Site profile resolution
    if site_profile is None and auto_detect_site:
        site_profile = guess_profile_from_filename(str(csv_path))

    return DiagnosisResult(
        site_day=_site_day_from_path(csv_path),
        data=data,
        threshold=threshold,
        classification=clf_result,
        interpretation=interp_result,
        site_profile=site_profile,
    )


def diagnose_many(
    csv_paths: List[str | Path],
    hotspot_quantile: float = 0.75,
    site_profile: Optional[SiteProfile] = None,
    auto_detect_site: bool = True,
    apply_stationary_filter: bool = False,
) -> List[DiagnosisResult]:
    """Run `diagnose()` on multiple files. Failures are reported but don't stop the loop."""
    results = []
    for p in csv_paths:
        try:
            results.append(diagnose(
                p, hotspot_quantile=hotspot_quantile,
                site_profile=site_profile,
                auto_detect_site=auto_detect_site,
                apply_stationary_filter=apply_stationary_filter,
            ))
        except Exception as e:
            print(f"[error] {p}: {e}")
    return results
