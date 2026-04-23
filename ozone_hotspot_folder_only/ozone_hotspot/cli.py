"""
cli.py — Command-line interface

Usage:
    python -m ozone_hotspot --input file1.csv [file2.csv ...] [--output DIR]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from .diagnose import diagnose, diagnose_many
from .report import render_report
from .site_profile import PROFILES


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="ozone_hotspot",
        description=(
            "Mobile-measurement Ozone Hotspot AI Diagnosis\n"
            "Input: CSV files with VOC (ppb) columns + Latitude/Longitude + O3.\n"
            "Output: per-day hotspot maps, VOC priority ranking, and HTML report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i", nargs="+", required=True, metavar="CSV",
        help="One or more mobile measurement CSV files.",
    )
    parser.add_argument(
        "--output", "-o", default="./ozone_output", metavar="DIR",
        help="Output directory (default: ./ozone_output).",
    )
    parser.add_argument(
        "--quantile", "-q", type=float, default=0.75,
        help="Quantile cutoff for hotspot label (default: 0.75 = top 25%%).",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Also generate a self-contained HTML report per day.",
    )
    parser.add_argument(
        "--site", choices=list(PROFILES.keys()) + ["auto", "none"], default="auto",
        help=(
            "Site profile for industry-specific cross-check. "
            f"Options: auto (detect from filename, default), none (disable), "
            f"or explicit: {', '.join(PROFILES.keys())}."
        ),
    )
    parser.add_argument(
        "--validate-only", action="store_true",
        help=(
            "Only validate input file format; do not run analysis. "
            "Useful to pre-check your CSV before committing to a full run."
        ),
    )
    parser.add_argument(
        "--filter-stationary", action="store_true",
        help=(
            "Remove stationary (vehicle-parked) points. OFF by default, which "
            "matches the paper's published AUROCs. Enable only if your raw data "
            "contains parked segments that were not already pre-cleaned."
        ),
    )
    args = parser.parse_args(argv)

    # --- Validate-only mode: run format check and exit ---
    if args.validate_only:
        from .validate import validate_csv
        print()
        all_valid = True
        for f in args.input:
            report = validate_csv(f)
            print(report.summary())
            print()
            if not report.is_valid:
                all_valid = False
        return 0 if all_valid else 1

    # Resolve site profile
    site_profile = None
    auto_detect = False
    if args.site == "auto":
        auto_detect = True
    elif args.site == "none":
        auto_detect = False
    else:
        site_profile = PROFILES[args.site]

    out_root = Path(args.output)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Ozone Hotspot Diagnosis — {len(args.input)} file(s)")
    if site_profile:
        print(f"  Site profile: {site_profile.display_name} (forced)")
    elif auto_detect:
        print(f"  Site profile: auto-detect from filename")
    print(f"{'='*60}")

    results = diagnose_many(
        args.input, hotspot_quantile=args.quantile,
        site_profile=site_profile, auto_detect_site=auto_detect,
        apply_stationary_filter=args.filter_stationary,
    )

    if not results:
        print("\n[error] No files successfully processed.")
        return 1

    for r in results:
        print("\n" + r.summary())
        paths = r.save_all(out_root)
        print(f"  -> Saved to: {out_root / r.site_day}/")

        if args.html:
            html_path = out_root / r.site_day / "report.html"
            render_report(r, html_path, figures=paths)
            print(f"  -> HTML report: {html_path}")

    print(f"\n{'='*60}")
    print(f"  Done. {len(results)}/{len(args.input)} files processed.")
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
