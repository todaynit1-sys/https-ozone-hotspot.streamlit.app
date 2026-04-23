"""
visualize.py — Output figures for a single-day diagnosis

Two core figures:
  1. Hotspot spatial map (replicates Fig. 1 of the paper)
  2. VOC priority bar chart (SHAP-based top-N)
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FormatStrFormatter

from .loader import LoadedData
from .classifier import ClassificationResult
from .interpret import InterpretationResult


# Shared color map (matches the paper)
_OZONE_CMAP = LinearSegmentedColormap.from_list(
    "ozone",
    [
        (0.00, "#1565C0"),
        (0.25, "#4FC3F7"),
        (0.50, "#FFEB3B"),
        (0.75, "#FB8C00"),
        (1.00, "#B71C1C"),
    ],
    N=256,
)


# ---------------------------------------------------------------------------
# Figure 1 — Hotspot spatial map
# ---------------------------------------------------------------------------
def plot_hotspot_map(
    data: LoadedData,
    result: ClassificationResult,
    threshold: float,
    out_path: str | Path,
    title: Optional[str] = None,
    use_ai_score: bool = False,
) -> Path:
    """
    Create a hotspot spatial map.

    Parameters
    ----------
    use_ai_score : bool
        If False, color = observed O3 (ppb).
        If True, color = model P(hotspot).  Useful to visualize where the AI
        sees 'hotspot-like VOC pattern' regardless of measured O3.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = data.df
    o3 = df[data.o3_col].values
    lat = df[data.lat_col].values
    lon = df[data.lon_col].values

    if use_ai_score:
        color_values = result.y_pred_proba
        cbar_label = "P(hotspot) from AI"
        vmin, vmax = 0.0, 1.0
        threshold_on_cbar = 0.5
    else:
        color_values = o3
        cbar_label = r"$O_3$ (ppb)"
        vmin, vmax = float(o3.min()), float(o3.max())
        threshold_on_cbar = threshold

    is_hot = df["is_hotspot"].values.astype(bool)
    n_hot = int(is_hot.sum())

    fig, ax = plt.subplots(figsize=(10, 8), dpi=140)
    ax.set_facecolor("#FAFAF5")

    # Path line
    ax.plot(lon, lat, "-", color="white", lw=3.2, alpha=0.95, zorder=1)
    ax.plot(lon, lat, "-", color="#BDBDBD", lw=1.0, alpha=0.7, zorder=2)

    # Non-hotspot points
    cold = ~is_hot
    ax.scatter(lon[cold], lat[cold],
               c=color_values[cold], cmap=_OZONE_CMAP,
               vmin=vmin, vmax=vmax,
               s=22, alpha=0.75, edgecolors="white", linewidths=0.4, zorder=3)

    # Hotspot glow
    ax.scatter(lon[is_hot], lat[is_hot],
               s=320, color="#FFEB3B", alpha=0.2, edgecolors="none", zorder=4)

    # Hotspot body
    sc = ax.scatter(lon[is_hot], lat[is_hot],
                     c=color_values[is_hot], cmap=_OZONE_CMAP,
                     vmin=vmin, vmax=vmax,
                     s=100, alpha=0.95, edgecolors="#1F1F1F", linewidths=0.9, zorder=5)

    # Top 3 peaks (by observed O3, regardless of color mode)
    top3_idx = np.argsort(o3)[-3:][::-1]
    for i, idx in enumerate(top3_idx):
        ax.scatter(lon[idx], lat[idx],
                   s=380, marker="*",
                   color="#FFEB3B", edgecolors="#B71C1C", linewidths=2, zorder=7)
    # Label only the #1 — position it away from info box (top-right)
    i1 = top3_idx[0]
    # Info box is at top-right (0.98, 0.98), so put Max label to the bottom-left of the star
    ax.annotate(f"Max: {o3[i1]:.0f} ppb",
                 xy=(lon[i1], lat[i1]),
                 xytext=(-55, -25), textcoords="offset points",
                 fontsize=10.5, fontweight="bold", color="#B71C1C",
                 ha="right",
                 bbox=dict(boxstyle="round,pad=0.35",
                           facecolor="white", edgecolor="#B71C1C",
                           alpha=0.95, linewidth=1.5),
                 arrowprops=dict(arrowstyle="->", color="#B71C1C", lw=1.1, alpha=0.8),
                 zorder=8)

    # Colorbar
    cbar = fig.colorbar(sc, ax=ax, shrink=0.72, pad=0.02, aspect=18)
    cbar.set_label(cbar_label, fontsize=11, fontweight="bold")
    cbar.ax.tick_params(labelsize=9)
    cbar.ax.axhline(threshold_on_cbar, color="#1F1F1F", linewidth=2.5)
    cbar.ax.axhline(threshold_on_cbar, color="white", linewidth=1, linestyle="--")

    # Axes
    ax.set_xlabel("Longitude (°E)", fontsize=10.5)
    ax.set_ylabel("Latitude (°N)", fontsize=10.5)
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.3f"))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.3f"))
    ax.grid(True, alpha=0.25, linestyle=":", color="#888")
    ax.set_aspect("equal", adjustable="box")

    # Title (sanitize non-ASCII chars since DejaVu Sans doesn't have Korean glyphs)
    if title is None:
        title = Path(data.source_path).stem
    # Replace any non-ASCII run with [korean]  → or just strip
    import re
    title_safe = re.sub(r'[^\x00-\x7F]+', '', title).strip('_ ')
    if not title_safe:
        title_safe = "Site-day"
    ax.set_title(title_safe, fontsize=13, fontweight="bold", color="#1F3A63", loc="left", pad=8)

    # Info box — place in the corner farthest from the Max star to avoid overlap
    o3_mean = float(o3.mean())
    o3_std = float(o3.std(ddof=1))
    info = (f"n = {len(df)} points\n"
            f"Hotspots: {n_hot}\n"
            f"Threshold: {threshold:.1f} ppb\n"
            f"Range: {o3.min():.0f}–{o3.max():.0f} ppb\n"
            f"Mean±SD: {o3_mean:.1f}±{o3_std:.1f}\n"
            f"AUROC: {result.auroc:.3f}")

    # Determine Max star's fractional position in axes coords
    max_lon, max_lat = lon[i1], lat[i1]
    lon_min, lon_max = lon.min(), lon.max()
    lat_min, lat_max = lat.min(), lat.max()
    x_frac = (max_lon - lon_min) / max(1e-9, (lon_max - lon_min))
    y_frac = (max_lat - lat_min) / max(1e-9, (lat_max - lat_min))
    # Pick the far corner
    if x_frac >= 0.5:
        box_x, ha = 0.02, "left"
    else:
        box_x, ha = 0.98, "right"
    if y_frac >= 0.5:
        box_y, va = 0.02, "bottom"
    else:
        box_y, va = 0.98, "top"

    ax.text(box_x, box_y, info, transform=ax.transAxes, fontsize=9,
            va=va, ha=ha, family="monospace",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="#1F3A63", alpha=0.95, linewidth=1.2))

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Figure 2 — VOC priority bar chart
# ---------------------------------------------------------------------------
# OVOC membership for highlighting (matches the paper's definition)
_OVOC_KEYS = ("methanol", "acetone", "ethyl acetate", "butanone", "2-propanol",
              "propanol", "ethanol", "acetaldehyde", "formaldehyde", "propanal")


def _is_ovoc(voc_name: str) -> bool:
    low = voc_name.lower()
    return any(k in low for k in _OVOC_KEYS)


def plot_voc_priority(
    interp: InterpretationResult,
    out_path: str | Path,
    top_n: int = 15,
    title: str = "VOC priority ranking (SHAP-based)",
) -> Path:
    """Horizontal bar chart of top-N VOC importances, with OVOC highlight."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = interp.voc_importance.head(top_n).copy()
    df["is_ovoc"] = df["voc"].apply(_is_ovoc)
    df["label"] = df["voc"].str.replace(" (ppb)", "", regex=False)

    n = len(df)
    fig, ax = plt.subplots(figsize=(11, max(4.5, n * 0.38)), dpi=140)

    y_pos = np.arange(n)[::-1]
    colors = ["#2E7D32" if o else "#5B7A9B" for o in df["is_ovoc"]]
    bars = ax.barh(y_pos, df["shap_importance"].values,
                    color=colors, edgecolor="white", linewidth=0.8)
    for bar, val in zip(bars, df["shap_importance"].values):
        ax.text(val * 1.02, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9, color="#333")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(df["label"].values, fontsize=10)
    ax.set_xlabel("mean |SHAP value|", fontsize=11)
    import re
    title_safe = re.sub(r'[^\x00-\x7F]+', '', title).strip('_ ')
    if not title_safe:
        title_safe = "VOC priority ranking"
    ax.set_title(title_safe, fontsize=13, fontweight="bold", color="#1F3A63", loc="left", pad=10)
    ax.grid(axis="x", alpha=0.3, linestyle=":")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend (green = OVOC, grey = other)
    from matplotlib.patches import Patch
    ax.legend(
        handles=[
            Patch(color="#2E7D32", label="Oxygenated VOC"),
            Patch(color="#5B7A9B", label="Other VOC"),
        ],
        loc="lower right", fontsize=10, frameon=True,
    )

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Paper Figure 1: multi-day grid of hotspot maps
# ---------------------------------------------------------------------------
def plot_multi_day_grid(
    diagnosis_results,
    out_path: str | Path,
    ncols: int = 2,
    suptitle: Optional[str] = None,
) -> Path:
    """
    Replicate the paper's Figure 1 style: one panel per site-day in a grid.

    Parameters
    ----------
    diagnosis_results : list of DiagnosisResult
        From diagnose_many(). Typically the four high-O3 days.
    out_path : Path
        Where to write the combined PNG.
    ncols : int
        Grid columns (default 2 → 2x2 for 4 days).
    """
    import re
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = len(diagnosis_results)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.5*ncols, 6.5*nrows), dpi=140)
    if n == 1:
        axes = np.array([[axes]])
    axes = np.atleast_2d(axes)

    for idx, r in enumerate(diagnosis_results):
        ax = axes[idx // ncols, idx % ncols]
        data = r.data
        clf = r.classification
        threshold = r.threshold
        df = data.df
        o3 = df[data.o3_col].values
        lat = df[data.lat_col].values
        lon = df[data.lon_col].values
        is_hot = df["is_hotspot"].values.astype(bool)

        vmin, vmax = float(o3.min()), float(o3.max())
        ax.set_facecolor("#FAFAF5")
        ax.plot(lon, lat, "-", color="white", lw=2.8, alpha=0.9, zorder=1)
        ax.plot(lon, lat, "-", color="#BDBDBD", lw=0.9, alpha=0.7, zorder=2)

        cold = ~is_hot
        ax.scatter(lon[cold], lat[cold], c=o3[cold], cmap=_OZONE_CMAP,
                   vmin=vmin, vmax=vmax, s=16, alpha=0.75,
                   edgecolors="white", linewidths=0.3, zorder=3)
        ax.scatter(lon[is_hot], lat[is_hot], s=260, color="#FFEB3B",
                   alpha=0.18, edgecolors="none", zorder=4)
        sc = ax.scatter(lon[is_hot], lat[is_hot], c=o3[is_hot], cmap=_OZONE_CMAP,
                        vmin=vmin, vmax=vmax, s=80, alpha=0.95,
                        edgecolors="#1F1F1F", linewidths=0.8, zorder=5)

        # Top 3 peaks
        top3 = np.argsort(o3)[-3:][::-1]
        for i in top3:
            ax.scatter(lon[i], lat[i], s=300, marker="*",
                       color="#FFEB3B", edgecolors="#B71C1C",
                       linewidths=1.8, zorder=7)

        cbar = fig.colorbar(sc, ax=ax, shrink=0.75, pad=0.02, aspect=20)
        cbar.set_label(r"$O_3$ (ppb)", fontsize=10)
        cbar.ax.tick_params(labelsize=8)
        cbar.ax.axhline(threshold, color="#1F1F1F", linewidth=2)
        cbar.ax.axhline(threshold, color="white", linewidth=0.8, linestyle="--")

        title_safe = re.sub(r'[^\x00-\x7F]+', '', r.site_day).strip('_ ') or "Site-day"
        ax.set_title(title_safe, fontsize=12, fontweight="bold",
                     color="#1F3A63", loc="left", pad=6)
        ax.ticklabel_format(useOffset=False, style="plain")
        from matplotlib.ticker import FormatStrFormatter
        ax.xaxis.set_major_formatter(FormatStrFormatter("%.3f"))
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.3f"))
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.2, linestyle=":", color="#888")
        ax.set_aspect("equal", adjustable="box")

        # Bottom-right info box (so it doesn't clash with Max marker)
        info = (f"n={len(df)}  hotspots={int(is_hot.sum())}\n"
                f"threshold={threshold:.1f} ppb\n"
                f"AUROC={clf.auroc:.3f}")
        ax.text(0.98, 0.02, info, transform=ax.transAxes, fontsize=8.5,
                va="bottom", ha="right", family="monospace",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="#1F3A63", alpha=0.92, linewidth=1))

    # Hide unused subplots
    for idx in range(n, nrows * ncols):
        axes[idx // ncols, idx % ncols].axis('off')

    if suptitle:
        fig.suptitle(suptitle, fontsize=14, fontweight="bold",
                     color="#1F3A63", y=1.00)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path
