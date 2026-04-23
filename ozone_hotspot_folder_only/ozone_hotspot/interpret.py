"""
interpret.py — SHAP-based VOC priority ranking

Produces a ranking of VOC species by their global contribution to the
hotspot classifier decision, using exact tree SHAP (Lundberg et al., 2020).

If SHAP is unavailable, falls back to GB's built-in feature_importances_.

Also exposes a minimal OFP ranking (using hard-coded MIR coefficients for
the VOCs commonly observed in the in-house mobile measurement panel)
so users can reproduce the Spearman independence check from the paper.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np
import pandas as pd

from .classifier import ClassificationResult


@dataclass
class InterpretationResult:
    voc_importance: pd.DataFrame  # columns: voc, shap_importance, rank
    per_point_shap: Optional[np.ndarray]  # (n_points, n_features) or None
    method: str  # 'shap' or 'gb_builtin'

    def top_n(self, n: int = 10) -> pd.DataFrame:
        return self.voc_importance.head(n).copy()

    def summary(self, n: int = 10) -> str:
        rows = [f"  Top {n} VOC contributors (method: {self.method}):"]
        for _, row in self.voc_importance.head(n).iterrows():
            rows.append(f"    {int(row['rank']):>2}.  {row['voc']:<45}  {row['shap_importance']:.4f}")
        return "\n".join(rows)


def interpret(result: ClassificationResult, X: np.ndarray) -> InterpretationResult:
    """
    Compute global VOC importance from the fitted classifier.

    Parameters
    ----------
    result : ClassificationResult
        Output of classify().
    X : np.ndarray
        The same feature matrix (n_points, n_features) used for training.

    Returns
    -------
    InterpretationResult
    """
    per_point = None
    method = "gb_builtin"

    # Try SHAP TreeExplainer first (matches the paper)
    try:
        import shap
        explainer = shap.TreeExplainer(result.full_model)
        shap_values = explainer.shap_values(X)
        # GB binary classifier: shap_values is (n_points, n_features)
        if isinstance(shap_values, list):
            # multiclass fallback — take positive class
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        per_point = shap_values
        importance = np.abs(shap_values).mean(axis=0)
        method = "shap"
    except ImportError:
        # Fallback: GB built-in impurity-based importance
        importance = result.full_model.feature_importances_
    except Exception as e:
        # Any SHAP runtime error — fall back gracefully
        print(f"[warn] SHAP failed ({e}); falling back to GB built-in importance.")
        importance = result.full_model.feature_importances_

    df = pd.DataFrame({
        "voc": result.voc_cols,
        "shap_importance": importance,
    }).sort_values("shap_importance", ascending=False).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)

    return InterpretationResult(
        voc_importance=df,
        per_point_shap=per_point,
        method=method,
    )


# ---------------------------------------------------------------------------
# OFP reference (Carter 2010 SAPRC-07 MIR, partial, g O3 / g VOC)
# ---------------------------------------------------------------------------
# Values are from Carter (2010). Species not in this dict will simply be
# skipped from OFP ranking (not used in AI input anyway).
#
# NOTE on xylene: SAPRC-07 distinguishes o-, m-, p-xylenes with slightly
# different MIRs (7.64–10.61). We use 9.75 as an aggregate for "xylene"
# and the common mixed column "ethylbenzene+xylene".
MIR_COEFFICIENTS: Dict[str, float] = {
    # Alkanes
    "ethane": 0.28, "propane": 0.49, "isobutane": 1.23, "butane": 1.15,
    "isopentane": 1.45, "pentane": 1.31, "n-hexane": 1.24,
    "n-heptane": 0.81, "heptane": 0.81,
    "n-octane": 0.60, "octane": 0.60,
    "n-nonane": 0.54, "nonane": 0.54,
    "n-decane": 0.46, "decane": 0.46,
    "n-undecane": 0.42, "undecane": 0.42,
    "n-dodecane": 0.38, "dodecane": 0.38,
    "cyclopentane": 2.39, "cyclohexane": 1.25,
    "methylcyclopentane": 2.19, "methyl cyclohexane": 1.70,
    # Alkenes
    "ethene": 9.00, "propene": 11.66, "1-butene": 9.73, "butene": 9.73,
    "1-hexene": 5.49, "hexene": 5.49, "pentene": 7.07,
    "isoprene": 10.61, "1,3-butadiene": 12.61, "1.3-butadiene": 12.61,
    # Aromatics
    "benzene": 0.72, "toluene": 4.00, "ethylbenzene": 3.04,
    "xylene": 9.75, "styrene": 1.95,
    "diethylbenzene": 7.10,
    # OVOCs
    "methanol": 0.67, "ethanol": 1.53, "acetone": 0.36,
    "butanone": 1.48, "ethyl acetate": 0.63, "2-propanol": 0.61,
    "isopropanol": 0.61, "2propanol": 0.61,
    "formaldehyde": 9.46, "acetaldehyde": 6.54,
    "propanal": 6.83,
    # Halogenated (very low reactivity, included for completeness)
    "chloroform": 0.03, "dichloromethane": 0.04,
    "trichloroethylene": 0.60, "tetrachloroethylene": 0.04,
    # Others
    "acetylene": 0.95,
}


def _match_mir(voc_name: str) -> Optional[float]:
    """
    Resolve the MIR coefficient for a measured VOC column name.

    Rules, applied in order:
    1. Lowercase + strip '(ppb)'.
    2. Split on '+' (mixed columns like 'ethene+ethane', 'ethylbenzene+xylene')
       and resolve each sub-name independently; return the MAX MIR across
       matched components. This avoids the dict-order bug where
       'ethene+ethane' silently resolved to ethane (MIR 0.28) instead of
       ethene (MIR 9.00) — a 30× error on a reactive alkene.
    3. For each sub-name, find the LONGEST dict key that matches as a
       whole word (not a substring), to prevent 'pentane' matching inside
       'trimethylpentane' or 'dimethylpentane'. Longest-match handles cases
       like 'isobutane' vs 'butane' correctly regardless of dict order.
    """
    import re
    cleaned = voc_name.replace(" (ppb)", "").strip().lower()
    parts = [p.strip() for p in cleaned.split("+") if p.strip()]

    best_mir = None
    for part in parts:
        # Find all dict keys that appear as whole words in `part`
        candidates = []
        for key in MIR_COEFFICIENTS:
            # Word-boundary match. '-' and digits are part of the "word"
            # so 'n-hexane' matches 'n-hexane' but 'pentane' does NOT
            # match 'trimethylpentane' (preceded by 'l', a word char).
            pattern = r'(?:^|[^a-z0-9.\-])' + re.escape(key) + r'(?:[^a-z0-9.\-]|$)'
            if re.search(pattern, part):
                candidates.append(key)
        if not candidates:
            continue
        # Longest match wins (isobutane > butane, n-hexane > hexane, etc.)
        longest = max(candidates, key=len)
        mir_val = MIR_COEFFICIENTS[longest]
        if best_mir is None or mir_val > best_mir:
            best_mir = mir_val
    return best_mir


def ofp_ranking(data_df: pd.DataFrame, voc_cols: List[str]) -> pd.DataFrame:
    """
    Compute OFP-based VOC ranking from mean concentrations.

    OFP_i = mean(C_i) * MIR_i

    For mixed columns (e.g. 'ethene+ethane'), the larger MIR of the
    constituents is used — this is a conservative upper bound that avoids
    under-counting reactive species hidden behind unreactive co-eluting
    compounds.

    Returns a DataFrame with columns: voc, ofp_contribution, mir, rank.
    Species without a known MIR coefficient are assigned NaN.
    """
    rows = []
    for col in voc_cols:
        mir = _match_mir(col)
        if mir is None:
            rows.append({"voc": col, "ofp_contribution": np.nan, "mir": np.nan})
            continue
        mean_conc = float(data_df[col].mean())
        rows.append({
            "voc": col,
            "ofp_contribution": mean_conc * mir,
            "mir": mir,
        })
    df = pd.DataFrame(rows).sort_values(
        "ofp_contribution", ascending=False, na_position="last"
    ).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    return df
