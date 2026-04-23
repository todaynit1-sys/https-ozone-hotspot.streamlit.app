# 산단별 커스터마이징 가이드 (Site Profiles)

각 산업단지는 업종 구성이 다르기 때문에 **예상되는 주요 VOC 패턴**도 다릅니다.  
본 패키지는 산단별 프로파일을 통해:

- ✅ AI 결과(SHAP Top N)를 **예상 VOC 리스트와 자동 비교**
- ✅ 매칭 / 예상 외 / 누락 VOC를 리포트에 자동 출력
- ✅ 파일명만 보고 **자동으로 올바른 프로파일 선택**

---

## 기본 제공 프로파일

| 프로파일 키 | 산단 | 업종 특성 | 예상 주요 VOC |
|------------|------|-----------|---------------|
| `sihwa` | 시화국가산업단지 | 종합산단 (석유화학·염색·기계·전기전자 등 9,600개 업체) | methanol, acetone, butanone, ethyl acetate, toluene, xylene, n-hexane, isopropanol |
| `hwaseong` | 화성바이오밸리 | 바이오·제약·화장품·식품·실험실 | ethanol, isopropanol, acetone, methanol, ethyl acetate, cyclohexane, toluene |
| `banwol` | 반월국가산업단지 | 종합산단 (시화 유사) | methanol, acetone, toluene, xylene, butanone, n-hexane |
| `ulsan` | 울산국가산업단지 | 석유화학 중심 | ethene, propene, butane, pentane, benzene, toluene, xylene, 1,3-butadiene |
| `generic` | 일반 산업단지 | 미지정 | (없음 — 순수 데이터 기반 분석) |

---

## 사용법

### 1. 자동 감지 (기본값)

파일명에 산단 키워드가 포함되어 있으면 자동으로 올바른 프로파일 적용:

```bash
# 파일명에 "시화"가 있으므로 sihwa 프로파일이 자동 감지됨
python -m ozone_hotspot --input 250618_시화산업단지_.csv --output ./results

# 파일명에 "화성"/"바이오" 있으므로 hwaseong 프로파일 자동 감지
python -m ozone_hotspot --input 20250725_화성바이오밸리_산단.csv --output ./results
```

감지 키워드:
- `sihwa` ← `시화` 또는 `sihwa`
- `hwaseong` ← `화성`, `바이오`, `hwaseong`, `biovalley`
- `banwol` ← `반월` 또는 `banwol`
- `ulsan` ← `울산` 또는 `ulsan`

### 2. 명시적 지정

파일명으로 판단 어려운 경우 또는 다른 프로파일을 강제하고 싶을 때:

```bash
python -m ozone_hotspot --input my_data.csv --site sihwa --output ./results
```

### 3. 프로파일 비활성화

순수 데이터 기반 분석만 하고 싶을 때:

```bash
python -m ozone_hotspot --input my_data.csv --site none --output ./results
```

### 4. Python 라이브러리로 사용

```python
from ozone_hotspot import diagnose, PROFILES

# 자동 감지 (기본)
result = diagnose("250618_시화.csv")
print(result.site_profile.display_name)  # "시화국가산업단지"

# 명시적 지정
result = diagnose("my_data.csv", site_profile=PROFILES["sihwa"])

# 비활성화
result = diagnose("my_data.csv", auto_detect_site=False)
```

---

## 리포트 출력 예시

프로파일이 적용되면 `summary.txt`에 다음 섹션이 자동 추가됩니다:

```
  Site profile: 시화국가산업단지
  (Mixed heavy/light industrial (comprehensive))
    Expected VOCs found in Top 10:  4
      methanol, ethylbenzene+xylene, n-hexane, ethyltoluene+...
    Unexpected VOCs in Top 10:
      n-octane, dimethylbutane+methylpentane, 2-propanol, ...
    Expected VOCs missing from Top 10:
      acetone, butanone, ethyl acetate, isopropanol
```

### 해석 방법

- **Expected found (매칭)**: 산업계 지식과 AI 결과가 일치 → 분석 신뢰도 ↑
- **Unexpected high**: 예상치 못한 VOC가 Top에 등장 → **새로운 배출원 가능성**, 현장 조사 검토
- **Missing expected**: 예상했는데 Top에 안 나옴 → 해당 업종 활동이 낮거나 VOC 특성 변화

실무에서 가장 주목할 것은 **Unexpected high** 항목입니다. 예를 들어:
- `trichloroethylene`이 Top 10에 예상 외로 등장 → 금속 탈지 작업 현장 확인 필요
- `chloroform`이 Top 10에 들어옴 → 화학 공정 폐기물 확인

---

## 새 산단 프로파일 추가하기

본인이 담당하는 새 산단이 있다면 `ozone_hotspot/site_profile.py`에 추가:

```python
# site_profile.py 끝에 추가
MY_NEW_SITE = SiteProfile(
    site_id="my_site",
    display_name="우리 산단",
    site_type="Mixed manufacturing",
    dominant_industries=[
        "automotive parts",
        "surface coating",
        "rubber",
    ],
    expected_top_vocs=[
        # 해당 산단에서 기대되는 주요 VOC 10종 이내
        "toluene", "xylene", "methyl ethyl ketone",
        "n-hexane", "1,3-butadiene",
    ],
    notes=(
        "자동차 부품·도장 공정 위주. "
        "BTX와 MEK 우세 예상, 고무 공정으로 인한 1,3-butadiene 주시."
    ),
)

# PROFILES 딕셔너리에 등록
PROFILES["my_site"] = MY_NEW_SITE

# 파일명 자동 감지 추가
def guess_profile_from_filename(path: str) -> SiteProfile:
    low = path.lower()
    if "시화" in path or "sihwa" in low: return SIHWA
    # ... 기존 조건들 ...
    if "우리산단" in path or "my_site" in low: return MY_NEW_SITE  # 추가
    return GENERIC
```

**예상 VOC 목록 결정 방법**:

1. **배출량 인벤토리 확인** — 지방환경청의 PRTR(화학물질 배출·이동량 정보)
2. **선행 연구** — 국립환경과학원 보고서, 학술 논문
3. **현장 조사** — 산단 관리공단 업종 분포 자료
4. **실측 데이터** — 2~3회 이동측정 후 상위 VOC를 관찰하여 업데이트

**주의**: 프로파일은 **교차 검증용**일 뿐이며 AI 분석 자체에 영향을 주지 않습니다. 예상 VOC 목록이 틀려도 AI 결과는 변하지 않습니다.

---

## 프로파일이 하지 않는 것

다음 사항들은 프로파일과 관계없이 **항상 동일**합니다:

- ❌ AI 모델의 입력 특성 (항상 VOC 41종, NOx는 제외)
- ❌ 하이퍼파라미터 (항상 n=150, depth=4, lr=0.05)
- ❌ 핫스팟 라벨링 방법 (항상 상위 25%)
- ❌ 교차검증 방식 (항상 5-fold Stratified, seed=42)

즉, 프로파일은 **분석 결과의 해석·검증·리포팅**을 돕는 도구이며, **분석 자체의 재현성을 해치지 않습니다**.

---

## 자주 묻는 질문

**Q: 프로파일의 예상 VOC 목록과 완전히 달라요. 문제인가요?**
A: 경우에 따라 다릅니다:
- AUROC가 0.80+이면 AI 분석 자체는 신뢰 가능. 예상 목록이 현재 산단 상황과 안 맞을 수 있음 (계절·가동률 변화).
- AUROC가 0.70 이하라면 데이터 문제일 수 있음. 측정 품질 점검 권장.

**Q: 어떤 프로파일을 써야 할지 모르겠어요.**
A: `--site generic` 또는 `--site none` 으로 시작. 3~5회 측정 후 상위 VOC 경향이 정착되면 본인의 프로파일 작성.

**Q: 자동 감지가 틀린 프로파일을 고르면?**
A: `--site` 옵션으로 명시적 지정하면 자동 감지를 무시합니다.

**Q: 프로파일끼리 비교하고 싶어요.**
A: 같은 파일을 두 프로파일로 각각 돌려서 리포트를 비교하세요:
```bash
python -m ozone_hotspot --input data.csv --site sihwa --output ./result_sihwa_profile
python -m ozone_hotspot --input data.csv --site banwol --output ./result_banwol_profile
```
