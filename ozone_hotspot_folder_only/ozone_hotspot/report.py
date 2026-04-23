"""
report.py — Self-contained HTML diagnostic report

Generates a single HTML file that a non-technical user can open in any
browser and see everything:
  - Day summary
  - Hotspot map (embedded)
  - AI score map (embedded)
  - VOC priority chart (embedded)
  - Top-15 VOC ranking table
  - Per-fold AUROCs
"""
from __future__ import annotations
from pathlib import Path
from typing import List
import base64
import datetime as dt
import pandas as pd

from .diagnose import DiagnosisResult


def _embed_image(img_path: Path) -> str:
    """Return a data: URI so the HTML is fully self-contained."""
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


_CSS = """
* { box-sizing: border-box; }
body {
  font-family: 'Malgun Gothic', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #F5F8FB;
  color: #1E293B;
  margin: 0; padding: 40px 20px;
}
.container { max-width: 1200px; margin: 0 auto; }
header {
  background: linear-gradient(135deg, #1A3A5C 0%, #2CA8A0 100%);
  color: white; padding: 36px 32px; border-radius: 12px;
  margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
header h1 { margin: 0 0 8px 0; font-size: 28px; }
header .subtitle { opacity: 0.85; font-size: 14px; }
.card {
  background: white; border-radius: 10px; padding: 28px;
  margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.card h2 {
  color: #1A3A5C; margin: 0 0 18px 0; padding-bottom: 10px;
  border-bottom: 2px solid #2CA8A0; font-size: 20px;
}
.metrics {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px; margin-bottom: 8px;
}
.metric {
  background: #F5F8FB; padding: 16px 18px; border-radius: 8px;
  border-left: 4px solid #2CA8A0;
}
.metric .label { font-size: 12px; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; }
.metric .value { font-size: 22px; font-weight: 700; color: #1A3A5C; margin-top: 4px; }
.metric .value.ok { color: #2E7D32; }
.metric .value.warn { color: #D97706; }
img.figure { width: 100%; height: auto; display: block; border-radius: 6px; margin-top: 6px; }
table {
  width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 14px;
}
th {
  background: #1A3A5C; color: white; padding: 10px; text-align: left;
  font-weight: 600;
}
td { padding: 9px 10px; border-bottom: 1px solid #E2E8F0; }
tr.ovoc { background: #E8F5E9; }
tr.ovoc td:nth-child(2) { color: #2E7D32; font-weight: 600; }
.caveat {
  background: #FFF8E1; border: 1.5px solid #E8A02F;
  padding: 14px 18px; border-radius: 8px;
  font-size: 14px; color: #8B6E00; margin-top: 14px;
}
footer {
  text-align: center; color: #64748B; font-size: 12px;
  margin-top: 30px; padding-top: 20px; border-top: 1px solid #E2E8F0;
}
"""


def _auroc_interpretation(auroc: float) -> tuple[str, str]:
    """Return (qualitative label, CSS class)."""
    if auroc >= 0.85:
        return "Excellent", "ok"
    if auroc >= 0.75:
        return "Good", "ok"
    if auroc >= 0.65:
        return "Fair", "warn"
    return "Poor", "warn"


def render_report(result: DiagnosisResult, out_path: str | Path,
                    figures: dict[str, str] | None = None) -> Path:
    """
    Render a standalone HTML report for a single DiagnosisResult.

    `figures` is a dict from `save_all()` (maps figure name -> Path).
    If None, figures are re-generated to a temp dir.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if figures is None:
        # Re-run save_all to a sibling directory
        figures = result.save_all(out_path.parent / "_figures_tmp")

    auroc_label, auroc_class = _auroc_interpretation(result.classification.auroc)

    # VOC ranking table (top 15)
    from .visualize import _is_ovoc
    top15 = result.interpretation.voc_importance.head(15)
    rows_html = []
    for _, row in top15.iterrows():
        ovoc_class = " class='ovoc'" if _is_ovoc(row["voc"]) else ""
        voc_display = row["voc"].replace(" (ppb)", "")
        rows_html.append(
            f"<tr{ovoc_class}>"
            f"<td>{int(row['rank'])}</td>"
            f"<td>{voc_display}</td>"
            f"<td>{row['shap_importance']:.4f}</td>"
            f"</tr>"
        )
    table_html = "\n".join(rows_html)

    n_hot = int(result.classification.y_true.sum())
    n_total = len(result.classification.y_true)
    o3_mean = float(result.data.df[result.data.o3_col].mean())
    o3_std = float(result.data.df[result.data.o3_col].std(ddof=1))

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Ozone Hotspot Diagnosis — {result.site_day}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">

  <header>
    <h1>산업단지 오존 핫스팟 AI 진단 리포트</h1>
    <div class="subtitle">Site-day: <b>{result.site_day}</b> &nbsp;·&nbsp;
      Generated: {dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>
  </header>

  <div class="card">
    <h2>1. 진단 요약</h2>
    <div class="metrics">
      <div class="metric">
        <div class="label">측정점 수</div>
        <div class="value">{n_total}</div>
      </div>
      <div class="metric">
        <div class="label">핫스팟 수 (상위 25%)</div>
        <div class="value">{n_hot}</div>
      </div>
      <div class="metric">
        <div class="label">핫스팟 임계값</div>
        <div class="value">{result.threshold:.1f} ppb</div>
      </div>
      <div class="metric">
        <div class="label">AI 분류 성능 (AUROC)</div>
        <div class="value {auroc_class}">{result.classification.auroc:.3f}</div>
      </div>
      <div class="metric">
        <div class="label">성능 등급</div>
        <div class="value {auroc_class}">{auroc_label}</div>
      </div>
      <div class="metric">
        <div class="label">O₃ 평균 ± 표준편차</div>
        <div class="value">{o3_mean:.1f} ± {o3_std:.1f}</div>
      </div>
    </div>
    <div class="caveat">
      ⚠ <b>참고:</b> AUROC는 분류기가 '핫스팟과 비핫스팟 쌍에서 핫스팟에 더 높은 점수를 줄 확률'입니다.
      본 분석은 <b>당일 측정 데이터 내에서</b> 수행된 site-specific 진단이며,
      다른 일자·산단으로의 전이는 검증되지 않았습니다 (논문 Section 3.4.3 참조).
    </div>
  </div>

  <div class="card">
    <h2>2. 핫스팟 공간 분포 (관측된 O₃)</h2>
    <img class="figure" src="{_embed_image(Path(figures['hotspot_map']))}" alt="Hotspot map">
  </div>

  <div class="card">
    <h2>3. AI P(hotspot) 공간 분포</h2>
    <p style="margin:0 0 10px 0; color:#64748B; font-size:14px;">
      VOC 패턴만으로 AI가 예측한 핫스팟 확률. 관측 O₃ 지도와 비교하여 AI 예측의 공간 일관성을 확인할 수 있습니다.
    </p>
    <img class="figure" src="{_embed_image(Path(figures['ai_score_map']))}" alt="AI score map">
  </div>

  <div class="card">
    <h2>4. VOC 우선순위 (SHAP 기반 Top 15)</h2>
    <img class="figure" src="{_embed_image(Path(figures['voc_priority']))}" alt="VOC priority">
    <table>
      <thead><tr><th>Rank</th><th>VOC</th><th>SHAP importance</th></tr></thead>
      <tbody>{table_html}</tbody>
    </table>
    <p style="font-size:12px; color:#64748B; margin-top:10px;">
      녹색 행 = Oxygenated VOC (OVOC). 논문에서 OVOC이 산단 오존 핫스팟의 지배적 기여 그룹으로 지목됨.
    </p>
  </div>

  <div class="card">
    <h2>5. AI 분류 상세</h2>
    <div class="metrics">
      <div class="metric">
        <div class="label">입력 특성 수</div>
        <div class="value">{len(result.data.voc_cols)} VOCs</div>
      </div>
      <div class="metric">
        <div class="label">Per-fold AUROCs</div>
        <div class="value" style="font-size:14px;">{', '.join(f'{a:.3f}' for a in result.classification.fold_aurocs)}</div>
      </div>
      <div class="metric">
        <div class="label">해석 방법</div>
        <div class="value" style="font-size:14px;">{result.interpretation.method.upper()}</div>
      </div>
    </div>
    <p style="font-size:13px; color:#475569; margin-top:14px;">
      모델: Gradient Boosting (n_estimators=150, max_depth=4, learning_rate=0.05) &nbsp;·&nbsp;
      교차검증: 5-fold Stratified (seed=42)
    </p>
  </div>

  <footer>
    생성 도구: ozone_hotspot &nbsp;·&nbsp; Mobile-measurement Ozone Hotspot AI diagnosis (MOHAI) pipeline
  </footer>

</div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
