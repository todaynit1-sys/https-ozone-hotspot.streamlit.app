# 🚀 ozone_hotspot 설치 및 테스트 가이드

**수도권대기환경청 내부 실무자용 매뉴얼**
버전 1.1.0 · 2025년

---

## 📋 목차

1. [사전 준비](#1-사전-준비)
2. [설치](#2-설치)
3. [첫 실행 테스트](#3-첫-실행-테스트)
4. [실무 사용](#4-실무-사용)
5. [웹 대시보드 (권장)](#5-웹-대시보드-권장)
6. [문제 해결](#6-문제-해결)
7. [결과 해석](#7-결과-해석)

---

## 1. 사전 준비

### 1.1 시스템 요구사항
- **Python**: 3.9 이상 (권장: 3.10 또는 3.11)
- **OS**: Windows / macOS / Linux 모두 가능
- **디스크**: 약 500 MB (패키지 + 의존성)
- **메모리**: 2 GB 이상 권장 (대용량 CSV 처리 시 4 GB+)

### 1.2 Python 설치 확인

**Windows (cmd 또는 PowerShell)**:
```cmd
python --version
```

**macOS/Linux (Terminal)**:
```bash
python3 --version
```

`Python 3.9.x` 이상이 표시되지 않으면 [python.org](https://www.python.org/downloads/) 에서 다운로드 후 설치.

### 1.3 CSV 파일 구조 확인

이동측정 CSV는 다음 컬럼을 포함해야 합니다:

| 필수 컬럼 | 허용되는 이름 |
|----------|--------------|
| **O₃** | `O3`, `O3 (ppb)`, `ozone`, `오존` |
| **위도** | `Latitude`, `위도`, `lat` |
| **경도** | `Longitude`, `Longtitude`(오타 허용), `경도`, `lon` |
| **VOC** | `(ppb)` 접미사 붙은 모든 컬럼 (최소 5종, 권장 30종 이상) |

`NOx` 컬럼이 있어도 괜찮지만, 분석에는 사용되지 않습니다 (논문 VOC-only 설계).

---

## 2. 설치

### 2.1 패키지 파일 받기

제공받은 `ozone_hotspot_package.zip`을 원하는 폴더에 압축 해제:

```
C:\Users\홍길동\ozone_pkg\    ← Windows 예시
~/ozone_pkg/                     ← macOS/Linux 예시
```

### 2.2 의존성 설치

해당 폴더로 이동 후:

```bash
cd ozone_pkg
pip install -r requirements.txt
```

설치되는 패키지:
- `pandas`, `numpy` — 데이터 처리
- `scikit-learn` — Gradient Boosting 분류기
- `matplotlib` — 지도/차트
- `shap` — AI 해석 (선택이지만 강력 권장)
- `streamlit` — 웹 대시보드 (선택)

**네트워크 문제로 설치 실패 시**: 사내망에서 pip proxy 설정이 필요할 수 있습니다. IT 부서 문의.

### 2.3 설치 검증

```bash
python -c "import ozone_hotspot; print('v', ozone_hotspot.__version__)"
```

출력: `v 1.1.0` 이 표시되면 성공.

---

## 3. 첫 실행 테스트

### 3.1 명령줄 테스트

제공된 샘플 데이터 (또는 본인의 CSV)로:

```bash
python -m ozone_hotspot --input 250618_시화산업단지.csv --output ./results --html
```

성공 시 출력 예:
```
============================================================
  Ozone Hotspot Diagnosis — 1 file(s)
  Site profile: auto-detect from filename
============================================================

========== Sihwa_2025-06-18 ==========
Source: 250618_시화산업단지.csv
  Raw rows: 438  |  Valid: 406
  VOC species: 41
  ...

Hotspot threshold: 71.88 ppb (top 25%)
  Features used: 41 VOCs (NOx and O3 excluded)
  AUROC (out-of-fold):  0.847
  Per-fold AUROCs:      0.899  0.833  0.864  0.865  0.808
  Hotspots: 102 / 406

  Top 10 VOC contributors (method: shap):
     1.  methanol (ppb)                                 1.1808
     2.  ethylbenzene+xylene (ppb)                      0.4693
     ...

  Site profile: 시화국가산업단지
  (Mixed heavy/light industrial (comprehensive))
    Expected VOCs found in Top 10:  4
    ...

  -> Saved to: results/Sihwa_2025-06-18/
  -> HTML report: results/Sihwa_2025-06-18/report.html
```

### 3.2 결과 확인

`results/Sihwa_2025-06-18/` 폴더에 다음 파일들이 생성됨:

```
Sihwa_2025-06-18/
├── hotspot_map.png       ← 관측 O₃ 공간 분포
├── ai_score_map.png      ← AI P(hotspot) 공간 분포
├── voc_priority.png      ← SHAP 기반 Top 15 VOC
├── per_point.csv         ← 개별 측정점 P(hotspot)
├── voc_ranking.csv       ← VOC 순위 × OFP 비교
├── summary.txt           ← 사람이 읽을 요약
├── summary.json          ← 프로그램이 읽을 JSON
└── report.html           ← 종합 리포트 (브라우저에서 열기)
```

**가장 먼저 열어볼 것**: `report.html` — 브라우저(Chrome/Edge/Safari)로 열면 모든 결과를 한눈에.

---

## 4. 실무 사용

### 4.1 여러 일자 동시 분석

```bash
python -m ozone_hotspot \
  --input \
    250618_시화.csv \
    250619_시화.csv \
    250801_시화.csv \
    20250725_화성.csv \
  --output ./campaign_2025_summer \
  --html
```

각 일자별로 독립 폴더가 생성됩니다.

### 4.2 산단 프로파일 지정

**자동 감지** (기본, 파일명에서 추정):
```bash
python -m ozone_hotspot --input data.csv --site auto
```

**명시적 지정** (파일명에 산단 정보 없을 때):
```bash
python -m ozone_hotspot --input data.csv --site sihwa    # 시화
python -m ozone_hotspot --input data.csv --site hwaseong_biovalley   # 화성바이오밸리
python -m ozone_hotspot --input data.csv --site banwol   # 반월
python -m ozone_hotspot --input data.csv --site ulsan    # 울산
```

**프로파일 비활성화** (순수 데이터 기반만):
```bash
python -m ozone_hotspot --input data.csv --site none
```

### 4.3 핫스팟 임계값 조정

기본은 상위 25% (논문 값). 상위 10%만 핫스팟으로 보고 싶다면:

```bash
python -m ozone_hotspot --input data.csv --quantile 0.9
```

### 4.4 Python 스크립트에서 사용

```python
from ozone_hotspot import diagnose

# 기본 사용
result = diagnose("250618_시화.csv")

# 결과 접근
print(f"AUROC: {result.classification.auroc:.3f}")
print(f"Top 5 VOCs: {result.interpretation.top_n(5)}")

# 개별 측정점 점수
point_df = result.per_point_table()
print(point_df.head())

# 전체 저장
result.save_all("output/")

# 산단 명시
from ozone_hotspot import SIHWA
result = diagnose("data.csv", site_profile=SIHWA)
```

---

## 5. 웹 대시보드 (권장)

**가장 쉬운 사용 방법** — 브라우저로 파일 드래그&드롭.

### 5.1 대시보드 실행

```bash
cd ozone_pkg
streamlit run app.py
```

출력:
```
  You can now view your Streamlit app in your browser.
  Local URL:  http://localhost:8501
```

브라우저가 자동으로 열립니다. (열리지 않으면 위 URL을 수동으로 입력)

### 5.2 대시보드 사용

1. **좌측 사이드바** → "CSV 업로드" → 파일 드래그&드롭 (여러 개 가능)
2. "🚀 분석 시작" 버튼 클릭
3. 일자별 탭으로 결과 확인
4. "📦 전체 결과 ZIP 다운로드" 로 저장

### 5.3 대시보드 장점

- ✅ 명령줄 안 써도 됨
- ✅ 여러 파일 한 번에 비교 (탭 전환)
- ✅ 지도·차트를 브라우저에서 바로 확인
- ✅ 측정점 테이블을 인터랙티브하게 탐색
- ✅ ZIP으로 전체 결과 다운로드

---

## 6. 문제 해결

### 6.1 자주 발생하는 오류

#### 오류 1: `ModuleNotFoundError: No module named 'ozone_hotspot'`

**원인**: 패키지 폴더가 아닌 곳에서 실행.

**해결**: `cd ozone_pkg` 후 다시 실행.

---

#### 오류 2: `UnicodeDecodeError` (한글 CSV 로드 실패)

**원인**: CSV 파일 인코딩 문제 (cp949 or 다른 인코딩).

**해결**: loader가 자동으로 `utf-8-sig` → `cp949` 순으로 시도합니다. 그래도 실패하면 CSV를 UTF-8로 저장:
- Excel에서: **다른 이름으로 저장** → **CSV UTF-8 (쉼표로 분리) (*.csv)**

---

#### 오류 3: `ValueError: Required columns not found`

**원인**: 컬럼명이 자동 인식되지 않음.

**해결**: CSV 헤더를 확인하세요. 필수 컬럼 이름:
- O₃: `O3` 또는 `O3 (ppb)`
- GPS: `Latitude`, `Longtitude` (or `Longitude`)
- VOC: 각 물질명 + `(ppb)` 접미사

---

#### 오류 4: `ValueError: Too few valid measurement points`

**원인**: QC 후 남은 측정점이 50개 미만.

**해결**: 원인 CSV에서 결측값이 너무 많음. 데이터 수집 품질을 확인하세요.

---

#### 오류 5: SHAP 설치 실패 (C++ 컴파일러 필요 등)

**영향**: 경미. SHAP 없으면 GB 내장 importance로 자동 fallback.

**해결**: SHAP 설치 건너뛰어도 기능 동작. 순위가 약간 달라질 수 있으나 Top VOC들은 대체로 일치.

### 6.2 성능 이슈

- **대용량 파일 (>10,000 측정점)**: 5-fold CV에 수 분 소요. 정상.
- **SHAP 계산 오래 걸림**: 측정점 수 × VOC 수 에 비례. 10,000점 × 41 VOC = 약 2~5분.

### 6.3 결과가 논문과 다를 때

정상입니다. 다음 요인으로 약간씩 달라집니다:
- **QC 적용**: 이 패키지는 정차점 제거를 포함 (논문은 raw). 측정점 수 ↓, AUROC 약간 ↑ 또는 ↓.
- **SHAP 버전**: SHAP 라이브러리 버전 차이로 소수점 3째 자리 변동.
- **Random seed**: 모두 `seed=42`로 고정되어 있어 재현 가능.

---

## 7. 결과 해석

### 7.1 AUROC 해석

| AUROC | 등급 | 해석 |
|-------|------|------|
| ≥ 0.85 | Excellent | 핫스팟 식별 매우 안정적 |
| 0.75–0.85 | Good | 실용적 사용 가능 |
| 0.65–0.75 | Fair | 참고용으로만 |
| < 0.65 | Poor | VOC 패턴으로 핫스팟 식별 어려움 — 기상 등 외부 요인 우세 |

**중요**: AUROC는 **순위 매김 능력**이지 **"85% 맞춘다"가 아님**.

### 7.2 VOC 우선순위 해석

- **SHAP 기반 Top 10** = AI가 "이 VOC 농도가 핫스팟 여부 결정에 중요"로 판단한 물질들
- **OVOC (Oxygenated VOC)** 가 Top에 많으면 → 용제·도료·화학공정 배출원 의심
- **Aromatic** (toluene, xylene) 가 Top에 많으면 → 도료·접착제·연료 배출원
- **Alkane** (hexane 등) 이 Top에 많으면 → 용제·석유화학 공정

### 7.3 Site profile 비교 해석

- **Matched VOCs**: AI 결과가 산단 업종 특성과 부합
- **Unexpected high**: AI가 지목했으나 사전 예상에 없던 VOC → **주목할 가치**. 숨겨진 배출원 또는 이차 생성 가능성
- **Missing expected**: 예상했으나 AI가 못 잡은 VOC → 해당 날은 그 VOC 농도가 낮았거나 공간 변동이 작았을 가능성

### 7.4 AI 점수 지도 vs 관측 O₃ 지도

두 지도가 **유사하게 나오면** → AI가 공간 패턴을 잘 학습함.

두 지도가 **크게 다르면** → 
- 빨간 영역이 AI 지도에만 있음: VOC 패턴은 핫스팟인데 실제 O₃는 낮음 (예: 기상·혼합·이류로 인한 희석)
- 빨간 영역이 관측 지도에만 있음: O₃는 높은데 VOC 패턴이 평범 → 외부 유입·원거리 수송 가능성

### 7.5 원칙: Site-specific 도구

- ✅ **같은 날 측정 데이터로 그 날 핫스팟 진단** — 안정적
- ❌ **과거 데이터로 학습해서 오늘 핫스팟 예측** — 논문 LODO 증거상 불가능
- 🔄 **매 campaign마다 새로 분석**하는 것이 원칙

---

## 📞 문의

- 논문 저자 또는 개발 담당자
- 보고된 이슈는 저자 이메일로

---

## 📚 관련 문서

- **README.md** — 요약 개요
- **논문** — 분석 원리 및 검증 근거
- **발표 대본 v5** — 연구 개요 및 FAQ
