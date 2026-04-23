"""
ozone_hotspot — Mobile-measurement Ozone Hotspot AI Diagnosis

High-level usage:

    from ozone_hotspot import diagnose
    result = diagnose("250618_시화산업단지.csv")
    print(result.summary())
    result.save_all("output/")

Command-line usage:

    python -m ozone_hotspot --input file1.csv file2.csv --output ./results --html

The pipeline matches the configuration validated in
"산업단지 오존 핫스팟의 AI 기반 식별" (2025):
  - Input: VOC 41 species only (NOx and O3 excluded)
  - Model: Gradient Boosting (n=150, depth=4, lr=0.05)
  - Evaluation: 5-fold Stratified CV, seed=42
  - Interpretation: exact tree SHAP (TreeExplainer)

IMPORTANT: Results are site-specific. Do not reuse a model trained on
one day/site to predict another day/site — Leave-One-Day-Out AUROC was
~0.51 (random) in the paper. Re-train per measurement campaign.
"""
from .loader import load_csv, LoadedData
from .preprocess import preprocess, label_hotspots, filter_gps, filter_stationary
from .classifier import classify, ClassificationResult
from .interpret import interpret, InterpretationResult, ofp_ranking
from .visualize import plot_hotspot_map, plot_voc_priority, plot_multi_day_grid
from .diagnose import diagnose, diagnose_many, DiagnosisResult
from .report import render_report
from .validate import validate_csv, validate_files, ValidationReport
from .site_profile import (
    SiteProfile, PROFILES, guess_profile_from_filename,
    SIHWA, HWASEONG_BIOVALLEY, BANWOL, ULSAN, GENERIC,
)

__version__ = "1.2.1"
__all__ = [
    # High-level
    "diagnose",
    "diagnose_many",
    "DiagnosisResult",
    "render_report",
    # Pre-flight validation
    "validate_csv",
    "validate_files",
    "ValidationReport",
    # Site profiles
    "SiteProfile",
    "PROFILES",
    "guess_profile_from_filename",
    "SIHWA", "HWASEONG_BIOVALLEY", "BANWOL", "ULSAN", "GENERIC",
    # Components
    "load_csv",
    "LoadedData",
    "preprocess",
    "label_hotspots",
    "filter_gps",
    "filter_stationary",
    "classify",
    "ClassificationResult",
    "interpret",
    "InterpretationResult",
    "ofp_ranking",
    "plot_hotspot_map",
    "plot_voc_priority",
    "plot_multi_day_grid",
]
