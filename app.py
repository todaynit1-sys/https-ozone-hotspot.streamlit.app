"""
app.py — Streamlit web dashboard for ozone hotspot diagnosis

Run:
    streamlit run app.py

Features:
- Drag-and-drop CSV upload (single or multiple)
- Automatic diagnosis with progress indicator
- Inline map + VOC priority chart display
- Download full result bundle (ZIP) or individual files
- Side-by-side comparison when multiple days are uploaded
"""
from __future__ import annotations
import io
import sys
import tempfile
import zipfile
from pathlib import Path

import streamlit as st
import pandas as pd

# Make local package importable
sys.path.insert(0, str(Path(__file__).parent))

from ozone_hotspot import diagnose, DiagnosisResult, validate_csv
from ozone_hotspot.report import render_report
from ozone_hotspot.visualize import _is_ovoc


# =============================================================================
# Page configuration
# =============================================================================
st.set_page_config(
    page_title="Ozone Hotspot AI Diagnosis",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #1A3A5C 0%, #2CA8A0 100%);
    padding: 24px 32px; border-radius: 10px; color: white;
    margin-bottom: 24px;
}
.main-header h1 { margin: 0; font-size: 26px; }
.main-header p { margin: 6px 0 0 0; opacity: 0.85; font-size: 14px; }
.metric-card {
    background: #F5F8FB; padding: 16px; border-radius: 8px;
    border-left: 4px solid #2CA8A0;
}
.caveat-box {
    background: #FFF8E1; border: 1.5px solid #E8A02F;
    padding: 12px 16px; border-radius: 8px;
    font-size: 13px; color: #8B6E00;
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Header
# =============================================================================
st.markdown("""
<div class="main-header">
  <h1>🌫️ 산업단지 오존 핫스팟 AI 진단</h1>
  <p>이동측정 VOC 자료 업로드 → AI 분석 → 핫스팟 지도 · VOC 우선순위 · 리포트 자동 생성</p>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# Sidebar — upload & options
# =============================================================================
with st.sidebar:
    st.markdown("### 📂 CSV 업로드")
    uploaded_files = st.file_uploader(
        "이동측정 CSV 파일을 선택하세요",
        type=["csv"],
        accept_multiple_files=True,
        help="VOC 열(ppb 접미사) + Latitude/Longtitude + O3 열이 포함된 CSV",
    )

    st.markdown("### ⚙️ 분석 옵션")
    quantile = st.slider(
        "핫스팟 임계값 (상위 %)",
        min_value=10, max_value=40, value=25, step=5,
        help="논문 기본값: 25% (상위 25%를 핫스팟으로 정의)",
    ) / 100.0
    quantile_cutoff = 1.0 - quantile

    run_button = st.button("🚀 분석 시작", type="primary", use_container_width=True,
                             disabled=(len(uploaded_files) == 0))

    st.markdown("---")
    st.markdown("### ℹ️ 사용 안내")
    st.markdown("""
    - **파일 드래그&드롭** 으로 CSV 선택 (여러 개 가능)
    - 분석은 **각 파일별 독립** 수행 (site-specific)
    - 결과: 지도 + VOC 우선순위 + 리포트
    - 전체 결과는 ZIP 다운로드 가능
    """)

    with st.expander("⚠️ 중요: 적용 범위"):
        st.markdown("""
        - ✅ **당일 자료 → 당일 진단**: AUROC ~0.85
        - ❌ **미래 예측 불가**: 다른 날 적용 시 LODO AUROC 0.51 (무작위)
        - 🔄 **매 측정마다 재학습** 원칙
        - 📊 AUROC는 '순위 능력'이지 '절대 분류 정확도' 아님
        """)


# =============================================================================
# Main area
# =============================================================================
if not uploaded_files:
    st.info("👈 좌측 사이드바에서 CSV 파일을 업로드하고 **분석 시작** 버튼을 눌러주세요.")

    st.markdown("### 📋 지원되는 CSV 형식")
    st.markdown("""
    - **O₃ 컬럼**: `O3`, `O3 (ppb)`, `ozone`, `오존`
    - **GPS 컬럼**: `Latitude`, `Longtitude` (오타 허용), `Longitude`, `위도`, `경도`
    - **VOC 컬럼**: `(ppb)` 접미사가 붙은 모든 컬럼 (최소 5종 이상)
    - **NOx 컬럼** (선택): 분석에는 사용되지 않음, VOC-only 설계
    """)

    st.markdown("### 🎯 생성되는 결과물")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**🗺️ 핫스팟 지도**\n\n관측 O₃의 공간 분포")
    with col2:
        st.markdown("**🤖 AI 점수 지도**\n\nP(hotspot) 공간 분포")
    with col3:
        st.markdown("**📊 VOC 우선순위**\n\nSHAP 기반 Top 15")
    with col4:
        st.markdown("**📄 종합 리포트**\n\n브라우저에서 바로 볼 수 있는 HTML")

    st.stop()


# =============================================================================
# Pre-flight validation — show before running diagnosis
# =============================================================================
st.markdown("### 📋 업로드된 파일 검증")

# Validate each uploaded file (fast, no ML)
validation_results = []
with tempfile.TemporaryDirectory() as val_tmp:
    for upf in uploaded_files:
        tmp_csv = Path(val_tmp) / upf.name
        tmp_csv.write_bytes(upf.getvalue())
        try:
            report = validate_csv(tmp_csv)
        except Exception as e:
            from ozone_hotspot.validate import ValidationReport
            report = ValidationReport(
                file_path=str(tmp_csv), is_valid=False,
                n_rows=0, n_columns=0,
                o3_col=None, nox_col=None, no_col=None, no2_col=None,
                lat_col=None, lon_col=None, time_col=None,
            )
            report.errors.append(f"Cannot read file: {e}")
        validation_results.append((upf.name, report))

# Summary metrics
n_valid = sum(1 for _, r in validation_results if r.is_valid)
n_invalid = len(validation_results) - n_valid

val_col1, val_col2, _ = st.columns([1, 1, 2])
val_col1.metric("전체 파일", len(validation_results))
val_col2.metric("유효", n_valid,
                delta=f"-{n_invalid} 오류" if n_invalid else None,
                delta_color="inverse" if n_invalid else "off")

# Per-file detail (expander)
for fname, report in validation_results:
    if report.is_valid:
        label_icon = "✅"
        msg = f"{report.n_rows} rows · VOC {len(report.voc_cols)}종 · O3 {report.o3_col}"
        if report.warnings:
            msg += f"  ·  ⚠️ {len(report.warnings)}개 주의"
    else:
        label_icon = "❌"
        msg = f"오류: {report.errors[0] if report.errors else 'unknown'}"

    with st.expander(f"{label_icon}  {fname}  —  {msg}", expanded=not report.is_valid):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**컬럼 감지 결과**")
            detected = {
                "O3":        report.o3_col or "—",
                "NOx":       report.nox_col or "—",
                "NO":        report.no_col or "—",
                "NO2":       report.no2_col or "—",
                "Latitude":  report.lat_col or "—",
                "Longitude": report.lon_col or "—",
                "Time":      report.time_col or "—",
                "VOC 수":    f"{len(report.voc_cols)} 종",
            }
            for k, v in detected.items():
                st.markdown(f"- **{k}**: `{v}`")

        with c2:
            if report.errors:
                st.error("**❌ 오류 (분석 불가)**\n\n" + "\n".join(f"- {e}" for e in report.errors))
            if report.warnings:
                st.warning("**⚠️ 주의사항**\n\n" + "\n".join(f"- {w}" for w in report.warnings))
            if report.notes:
                st.info("**💡 참고**\n\n" + "\n".join(f"- {n}" for n in report.notes))
            if report.is_valid and not report.warnings and not report.notes:
                st.success("완벽한 형식입니다. 분석 준비 완료!")

# Block diagnosis if any file invalid
if n_invalid > 0:
    st.error(
        f"❌ {n_invalid}개 파일에 형식 오류가 있어 분석을 진행할 수 없습니다. "
        "위 오류를 수정하거나 해당 파일을 제외하고 다시 업로드해주세요."
    )
    st.stop()

st.markdown("---")


# =============================================================================
# Run diagnosis
# =============================================================================
if run_button or st.session_state.get("results"):

    # Cache results across reruns
    if run_button:
        st.session_state["results"] = []
        st.session_state["tmpdir"] = tempfile.mkdtemp(prefix="ozone_")

        progress = st.progress(0, text="분석 준비 중...")

        with tempfile.TemporaryDirectory() as upload_tmp:
            # Save uploaded files to disk (diagnose needs paths)
            for i, upf in enumerate(uploaded_files):
                progress.progress(
                    (i + 0.1) / len(uploaded_files),
                    text=f"[{i+1}/{len(uploaded_files)}] {upf.name} 로드 중..."
                )

                tmp_csv = Path(upload_tmp) / upf.name
                tmp_csv.write_bytes(upf.getvalue())

                try:
                    result = diagnose(tmp_csv, hotspot_quantile=quantile_cutoff)
                    progress.progress(
                        (i + 0.7) / len(uploaded_files),
                        text=f"[{i+1}/{len(uploaded_files)}] {upf.name} AI 분석 중..."
                    )

                    # Save all outputs to persistent temp dir
                    paths = result.save_all(st.session_state["tmpdir"])
                    # Render HTML report
                    html_path = Path(st.session_state["tmpdir"]) / result.site_day / "report.html"
                    render_report(result, html_path, figures=paths)
                    paths["report_html"] = str(html_path)

                    st.session_state["results"].append({
                        "filename": upf.name,
                        "result": result,
                        "paths": paths,
                    })
                except Exception as e:
                    st.error(f"❌ **{upf.name}** 처리 실패: {e}")
                    continue

                progress.progress(
                    (i + 1) / len(uploaded_files),
                    text=f"[{i+1}/{len(uploaded_files)}] {upf.name} 완료"
                )

        progress.empty()

    results = st.session_state["results"]
    if not results:
        st.warning("분석 결과가 없습니다. 파일을 다시 확인해주세요.")
        st.stop()

    # =========================================================================
    # Summary strip (all days)
    # =========================================================================
    st.markdown(f"### ✅ 분석 완료 — {len(results)}개 일자")

    summary_rows = []
    for r in results:
        res: DiagnosisResult = r["result"]
        summary_rows.append({
            "Site-day": res.site_day,
            "측정점": res.data.n_valid,
            "핫스팟 수": int(res.classification.y_true.sum()),
            "임계값 (ppb)": f"{res.threshold:.1f}",
            "AUROC": f"{res.classification.auroc:.3f}",
            "Top 1 VOC": res.interpretation.voc_importance.iloc[0]["voc"].replace(" (ppb)", ""),
        })
    st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

    # Download all as ZIP
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            res = r["result"]
            folder = Path(st.session_state["tmpdir"]) / res.site_day
            for fp in folder.iterdir():
                zf.write(fp, arcname=f"{res.site_day}/{fp.name}")
    zip_buf.seek(0)
    st.download_button(
        "📦 전체 결과 ZIP 다운로드",
        zip_buf.getvalue(),
        file_name="ozone_hotspot_results.zip",
        mime="application/zip",
        use_container_width=True,
    )

    st.markdown("---")

    # =========================================================================
    # Per-day tabs
    # =========================================================================
    tab_labels = [r["result"].site_day for r in results]
    tabs = st.tabs(tab_labels)

    for tab, r in zip(tabs, results):
        with tab:
            res: DiagnosisResult = r["result"]
            paths = r["paths"]

            # Metric strip
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("측정점", f"{res.data.n_valid}")
            with col2:
                st.metric("핫스팟", f"{int(res.classification.y_true.sum())}",
                           delta=f"임계값 {res.threshold:.1f} ppb")
            with col3:
                auroc = res.classification.auroc
                label = "Excellent" if auroc >= 0.85 else ("Good" if auroc >= 0.75 else ("Fair" if auroc >= 0.65 else "Poor"))
                st.metric("AUROC", f"{auroc:.3f}", delta=label, delta_color="off")
            with col4:
                o3 = res.data.df[res.data.o3_col]
                st.metric("O₃ 범위", f"{o3.min():.0f}–{o3.max():.0f} ppb",
                           delta=f"평균 {o3.mean():.1f}")

            st.markdown(
                '<div class="caveat-box">⚠ <b>참고:</b> AUROC는 분류기가 \'핫스팟과 비핫스팟 쌍에서 핫스팟에 더 높은 점수를 줄 확률\'입니다. '
                '본 분석은 <b>당일 측정 데이터 내</b> site-specific 진단이며, 다른 일자·산단으로의 전이는 검증되지 않았습니다.</div>',
                unsafe_allow_html=True,
            )

            # Maps side-by-side
            st.markdown("#### 🗺️ 공간 분포")
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("**관측 O₃ (ppb)**")
                st.image(str(paths["hotspot_map"]), use_container_width=True)
            with mc2:
                st.markdown("**AI P(hotspot)**")
                st.image(str(paths["ai_score_map"]), use_container_width=True)

            # VOC priority
            st.markdown("#### 📊 VOC 우선순위 (SHAP 기반)")
            st.image(str(paths["voc_priority"]), use_container_width=True)

            # Expandable: Top-15 table
            with st.expander("📋 VOC 순위 상세 표 (Top 15)"):
                top15 = res.interpretation.voc_importance.head(15).copy()
                top15["voc_clean"] = top15["voc"].str.replace(" (ppb)", "", regex=False)
                top15["is_OVOC"] = top15["voc"].apply(_is_ovoc)
                display_df = top15[["rank", "voc_clean", "shap_importance", "is_OVOC"]].rename(
                    columns={"rank": "순위", "voc_clean": "VOC", "shap_importance": "SHAP importance", "is_OVOC": "OVOC?"}
                )
                st.dataframe(display_df, hide_index=True, use_container_width=True)

            # Expandable: per-point table
            with st.expander("📍 측정점별 AI 점수 (처음 100개)"):
                pp = res.per_point_table()
                st.dataframe(pp.head(100), hide_index=True, use_container_width=True)
                csv_data = pp.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    f"전체 측정점 CSV 다운로드 ({len(pp)}개)",
                    csv_data, f"{res.site_day}_per_point.csv", "text/csv",
                )

            # Expandable: HTML report
            with st.expander("📄 HTML 리포트 보기"):
                with open(paths["report_html"], "r", encoding="utf-8") as f:
                    html_content = f.read()
                st.download_button(
                    "HTML 리포트 다운로드",
                    html_content,
                    f"{res.site_day}_report.html",
                    "text/html",
                )
                st.components.v1.html(html_content, height=800, scrolling=True)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#888; font-size:12px;">'
    'ozone_hotspot v1.0 · Mobile-measurement Ozone Hotspot AI Diagnosis'
    '</p>', unsafe_allow_html=True,
)
