"""
classifier.py — Gradient Boosting classifier with out-of-fold prediction

Matches the paper's configuration exactly:
  - GradientBoostingClassifier(n_estimators=150, max_depth=4, learning_rate=0.05)
  - 5-fold Stratified CV, seed=42
  - Out-of-fold probabilities are concatenated so every measurement point
    receives a P(hotspot) that the model never saw during training
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

from .loader import LoadedData


@dataclass
class ClassificationResult:
    """Everything produced by `classify()`."""
    voc_cols: List[str]
    y_true: np.ndarray
    y_pred_proba: np.ndarray  # out-of-fold P(hotspot)
    auroc: float
    fold_aurocs: List[float]
    full_model: GradientBoostingClassifier  # fit on ALL data, used for SHAP

    def n_hotspots(self) -> int:
        return int(self.y_true.sum())

    def summary(self) -> str:
        folds = "  ".join(f"{a:.3f}" for a in self.fold_aurocs)
        return (
            f"  Features used: {len(self.voc_cols)} VOCs (NOx and O3 excluded)\n"
            f"  AUROC (out-of-fold):  {self.auroc:.3f}\n"
            f"  Per-fold AUROCs:      {folds}\n"
            f"  Hotspots: {self.n_hotspots()} / {len(self.y_true)}"
        )


def classify(
    data: LoadedData,
    n_estimators: int = 150,
    max_depth: int = 4,
    learning_rate: float = 0.05,
    n_splits: int = 5,
    seed: int = 42,
) -> ClassificationResult:
    """
    Fit a Gradient Boosting hotspot classifier with 5-fold CV.

    Returns the out-of-fold P(hotspot) for every measurement point,
    plus a full-data model used later by SHAP.

    Requires that `data.df` has an 'is_hotspot' column (call preprocess first).
    """
    if "is_hotspot" not in data.df.columns:
        raise ValueError(
            "Data is not labeled. Call preprocess.label_hotspots() or preprocess() first."
        )

    X = data.df[data.voc_cols].values
    y = data.df["is_hotspot"].values

    if len(np.unique(y)) < 2:
        raise ValueError("Only one class present. Cannot train classifier.")

    # Out-of-fold prediction
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    oof = np.zeros(len(y))
    fold_aurocs = []
    for tr_idx, te_idx in skf.split(X, y):
        clf = GradientBoostingClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=seed,
        )
        clf.fit(X[tr_idx], y[tr_idx])
        oof[te_idx] = clf.predict_proba(X[te_idx])[:, 1]
        # Per-fold AUROC (on this fold's test set)
        fold_aurocs.append(
            float(roc_auc_score(y[te_idx], oof[te_idx]))
        )

    auroc = float(roc_auc_score(y, oof))

    # Full-data model for SHAP interpretation
    full_model = GradientBoostingClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        random_state=seed,
    )
    full_model.fit(X, y)

    return ClassificationResult(
        voc_cols=data.voc_cols,
        y_true=y,
        y_pred_proba=oof,
        auroc=auroc,
        fold_aurocs=fold_aurocs,
        full_model=full_model,
    )
