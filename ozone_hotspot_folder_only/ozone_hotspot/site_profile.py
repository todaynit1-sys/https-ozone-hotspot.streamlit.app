"""
site_profile.py — Per-industrial-park customization

Each industrial park has different dominant industries and therefore
different expected VOC emission profiles. SiteProfile encodes:

  - expected dominant VOCs (for cross-check against SHAP result)
  - known source types (for report annotation)
  - display name and site info

Users can supply a SiteProfile to diagnose() to enable customized reports.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd


@dataclass
class SiteProfile:
    """Per-site knowledge used to enrich diagnostic output."""
    site_id: str
    display_name: str
    site_type: str = ""
    dominant_industries: List[str] = field(default_factory=list)
    expected_top_vocs: List[str] = field(default_factory=list)
    notes: str = ""

    def check_expected_vs_actual(
        self, shap_top_vocs: List[str], n: int = 10,
    ) -> Dict[str, List[str]]:
        """
        Compare AI-identified top VOCs against expected list for this site.

        Returns dict with:
          - 'matched': expected VOCs that actually appeared in top-N
          - 'unexpected_high': top-N VOCs that were NOT in expected list
          - 'missing_expected': expected VOCs NOT found in top-N
        """
        if not self.expected_top_vocs:
            return {"matched": [], "unexpected_high": [], "missing_expected": []}

        top = [v.lower().replace(" (ppb)", "").strip() for v in shap_top_vocs[:n]]
        expected = [v.lower().strip() for v in self.expected_top_vocs]

        matched, unexpected_high = [], []
        for t in top:
            if any(e in t or t in e for e in expected):
                matched.append(t)
            else:
                unexpected_high.append(t)

        missing_expected = []
        for e in expected:
            if not any(e in t or t in e for t in top):
                missing_expected.append(e)

        return {
            "matched": matched,
            "unexpected_high": unexpected_high,
            "missing_expected": missing_expected,
        }


# ---------------------------------------------------------------------------
# Built-in profiles for parks studied in the paper
# ---------------------------------------------------------------------------
SIHWA = SiteProfile(
    site_id="sihwa",
    display_name="시화국가산업단지",
    site_type="Mixed heavy/light industrial (comprehensive)",
    dominant_industries=[
        "petrochemical", "dyeing & finishing", "machinery",
        "electronics", "plating", "printing",
    ],
    expected_top_vocs=[
        # From the paper's observed SHAP ranking + industry knowledge
        "methanol", "acetone", "butanone", "ethyl acetate",
        "toluene", "xylene", "n-hexane", "isopropanol",
    ],
    notes=(
        "Comprehensive industrial park with ~9,600 member companies. "
        "High mix of solvent-intensive industries (paint, dye, print, adhesive). "
        "Expect OVOC dominance in hotspot contribution."
    ),
)


HWASEONG_BIOVALLEY = SiteProfile(
    site_id="hwaseong_biovalley",
    display_name="화성바이오밸리산업단지",
    site_type="Biotech-focused light industrial",
    dominant_industries=[
        "biotechnology", "pharmaceuticals", "cosmetics",
        "food processing", "lab reagents",
    ],
    expected_top_vocs=[
        "ethanol", "isopropanol", "acetone", "methanol",
        "ethyl acetate", "cyclohexane", "toluene",
    ],
    notes=(
        "Biotech/pharma-oriented smaller industrial park. "
        "Expect high alcohol (ethanol, IPA) and acetone from lab/production solvents. "
        "Aromatic and alkane signatures may be weaker than Sihwa."
    ),
)


BANWOL = SiteProfile(
    site_id="banwol",
    display_name="반월국가산업단지",
    site_type="Mixed heavy/light industrial",
    dominant_industries=[
        "petrochemical", "machinery", "metal fabrication",
        "plating", "electronics",
    ],
    expected_top_vocs=[
        "methanol", "acetone", "toluene", "xylene",
        "butanone", "n-hexane", "ethyl acetate",
    ],
    notes=(
        "Adjacent to Sihwa, similar mixed industrial character. "
        "Profile can be treated as similar to Sihwa unless site-specific "
        "data indicates otherwise."
    ),
)


ULSAN = SiteProfile(
    site_id="ulsan",
    display_name="울산국가산업단지",
    site_type="Heavy petrochemical",
    dominant_industries=[
        "petrochemical", "oil refining", "automotive",
        "shipbuilding", "chemical manufacturing",
    ],
    expected_top_vocs=[
        "ethene", "propene", "butane", "pentane", "benzene",
        "toluene", "xylene", "1,3-butadiene",
    ],
    notes=(
        "Major petrochemical hub. Profile may differ substantially from "
        "Sihwa/Banwol: expect higher alkane and alkene signatures, more aromatic "
        "BTX, and less OVOC dominance than solvent-intensive parks."
    ),
)


GENERIC = SiteProfile(
    site_id="generic",
    display_name="일반 산업단지",
    site_type="Unknown / generic",
    expected_top_vocs=[],
    notes="No site-specific knowledge applied. Pure data-driven diagnosis.",
)


# Registry for easy lookup
PROFILES: Dict[str, SiteProfile] = {
    "sihwa": SIHWA,
    "hwaseong_biovalley": HWASEONG_BIOVALLEY,
    "hwaseong": HWASEONG_BIOVALLEY,
    "banwol": BANWOL,
    "ulsan": ULSAN,
    "generic": GENERIC,
}


def guess_profile_from_filename(path: str) -> SiteProfile:
    """Guess the best-fitting site profile from a file path."""
    low = path.lower()
    if "시화" in path or "sihwa" in low:
        return SIHWA
    if "화성" in path or "바이오" in path or "hwaseong" in low or "biovalley" in low:
        return HWASEONG_BIOVALLEY
    if "반월" in path or "banwol" in low:
        return BANWOL
    if "울산" in path or "ulsan" in low:
        return ULSAN
    return GENERIC
