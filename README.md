# ozone_hotspot

**Mobile-measurement Ozone Hotspot AI Diagnosis** — 이동측정 VOC 자료로부터 산업단지 오존 핫스팟을 식별하고 기여 VOC를 규명하는 Python 도구.

> 이 패키지는 논문 *"산업단지 오존 핫스팟의 AI 기반 식별"* (2025)에서 검증된 분석 파이프라인을 구현한 것입니다. 논문 그대로의 하이퍼파라미터와 처리 순서를 따릅니다.

---

## ⚠️ 중요 — 적용 범위와 한계

- ✅ **당일 진단**: 이동측정 CSV 1일분을 입력하면 당일 핫스팟 지도 + VOC 우선순위를 산출합니다. 논문 검증 AUROC 평균 0.849.
- ❌ **미래 예측 불가**: 다른 날짜·산단으로의 전이는 논문 Section 3.4.3에서 AUROC 0.51 (무작위 수준)로 실증되었습니다. **매 측정마다 재학습**해야 합니다.
- 이 도구는 **현장 진단 보조 도구**이지 **예측 모델이 아닙니다**.

---

## 설치

```bash
# 의존성
pip install -r requirements.txt

# 패키지 자체는 pip install로 설치하거나, 폴더 그대로 쓸 수 있습니다
pip install -e .   # 개발 모드
```

**필수 패키지**: `pandas`, `numpy`, `scikit-learn`, `matplotlib`
**권장 패키지**: `shap` (없으면 GB 내장 importance로 자동 fallback)

---

## 빠른 시작

### 방법 1: 명령줄 (가장 쉬움)

```bash
# 파일 형식 먼저 검증 (선택, 문제 있으면 바로 안내)
python -m ozone_hotspot --input 250618_시화.csv --validate-only

# 단일 CSV
python -m ozone_hotspot --input 250618_시화.csv --output ./results --html

# 여러 CSV 한 번에
python -m ozone_hotspot \
    --input day1.csv day2.csv day3.csv \
    --output ./results \
    --html
```

### 방법 2: Python 라이브러리

```python
from ozone_hotspot import validate_csv, diagnose

# 형식 검증 (선택)
report = validate_csv("250618_시화.csv")
print(report.summary())
# → ✓ VALID, VOC 41종, O3 범위: 27.4–79.2 ppb

# 분석 실행
result = diagnose("250618_시화.csv")
print(result.summary())

# 산출물 모두 저장
result.save_all("./results/")

# 개별 접근
print(result.classification.auroc)          # 0.847
print(result.interpretation.top_n(10))      # Top 10 VOC
df = result.per_point_table()               # 개별 측정점 P(hotspot)
```

---

## 입력 CSV 요구사항

다음 컬럼들이 있어야 합니다 (자동 감지 포함):

| 종류 | 지원되는 컬럼명 |
|------|----------------|
| **O₃** | `O3`, `O3 (ppb)`, `ozone`, `오존` |
| **GPS** | `Latitude`, `Longtitude` (typo OK), `Longitude`, `위도`, `경도` |
| **VOC** | `(ppb)` 접미사가 붙은 모든 컬럼 (최소 5종) |
| NOx (선택) | `NOx`, `NOx (ppb)` — 분석에는 사용되지 않음 |

---

## 출력 구조

```
results/
└── Sihwa_2025-06-18/
    ├── hotspot_map.png        # 관측 O₃ 공간 지도
    ├── ai_score_map.png       # AI P(hotspot) 공간 지도
    ├── voc_priority.png       # SHAP 기반 Top 15 VOC 막대 차트
    ├── per_point.csv          # 측정점별 lat/lon/O3/is_hotspot/p_hotspot
    ├── voc_ranking.csv        # VOC × SHAP 순위 × OFP 순위 비교
    ├── summary.txt            # 사람이 읽기 쉬운 요약
    ├── summary.json           # 기계 판독용 요약
    └── report.html            # 종합 리포트 (self-contained)
```

---

## 파이프라인 개요

입력 CSV → QC (GPS·정차점 필터, 일자별 centering)
→ 핫스팟 라벨링 (일별 상위 25%)
→ Gradient Boosting (n=150, depth=4, lr=0.05, 5-fold Stratified CV, seed=42)
→ SHAP TreeExplainer (Global importance)
→ 산출물 (지도 + 우선순위 + 리포트)

논문의 핵심 설계 원칙이 그대로 반영됩니다:
- **VOC 41종만** AI 입력 (NOx는 data leakage 방지 위해 제외)
- **5-fold Stratified CV**로 out-of-fold 예측 → 모든 측정점이 "학습에서 보지 않은" P(hotspot) 값을 받음

---

## FAQ

**Q: AUROC 0.85가 "85% 정확도"인가요?**
A: 아닙니다. AUROC 0.85는 "핫스팟 지점이 비핫스팟 지점보다 더 높은 점수를 받을 확률이 85%"입니다. 순위 매김 능력이며, 절대 분류 정확도가 아닙니다.

**Q: 다른 날짜로 학습해서 이 날짜를 예측할 수 있나요?**
A: 강력히 비권장. 논문에서 Leave-One-Day-Out AUROC가 0.51 (무작위)였습니다. 매 측정 campaign마다 그 날 데이터로 재학습하는 것이 원칙입니다.

**Q: SHAP 설치가 어렵습니다.**
A: 없어도 됩니다. 자동으로 GradientBoosting의 내장 feature_importances_로 fallback합니다. SHAP이 더 정확하지만, 순위는 대체로 비슷합니다.

**Q: 핫스팟 임계값을 바꿀 수 있나요?**
A: `--quantile 0.9` 옵션으로 상위 10%로 설정 가능. 기본은 0.75 (상위 25%, 논문 값).

---

## 📚 문서

| 문서 | 용도 | 대상 |
|------|------|------|
| `README.md` (이 파일) | 개요 + 빠른 시작 | 모두 |
| `INSTALL_GUIDE.md` | 설치부터 검증까지 단계별 가이드 | 실무자 |
| `WEB_DEPLOY.md` | 웹/서버 배포 3가지 방법 | 실무자 |
| `PROFILES.md` | 산단별 커스터마이징 설명 | 실무자·개발자 |
| `quickstart.py` | 최소 예제 스크립트 | 개발자 |

---

## 🌐 웹으로 사용하기

세 가지 옵션 중 선택:

- **방법 A** (가장 쉬움): `start_server.bat` (Windows) 또는 `./start_server.sh` (Mac/Linux) → 같은 Wi-Fi 안에서 공유
- **방법 B** (원격 가능): `start_public_tunnel.bat` / `.sh` → 임시 공개 URL로 어디서든 접속
- **방법 C** (영구 URL): GitHub + Streamlit Community Cloud → `https://your-app.streamlit.app`

자세한 세팅 방법은 **`WEB_DEPLOY.md`** 참조.

---

## 인용

이 도구를 사용하신 경우 원 논문을 인용해주세요:

> 신현준, 서현정, 강천웅 (2025). 산업단지 오존 핫스팟의 AI 기반 식별 — 이동측정 VOC 자료와 해석 가능한 기계학습의 결합.

---

## 라이선스

MIT License. 자세한 내용은 LICENSE 파일 참조.
