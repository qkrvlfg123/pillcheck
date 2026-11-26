# packages/shared: 약물 상호작용 엔진 (필체크 공용 엔진)

필체크(PillCheck)의 공용 엔진. 여러 약을 함께 복용할 때의 위험을 4개 축으로
분석함. 챗봇(10)과 음성 앱이 이 엔진의 사본을 쓰고, 약국·병원 지도(11)는 챗봇의 판정 결과에서 이어짐.

## 4개 분석 축

| 축 | 내용 | 근거 |
| --- | --- | --- |
| 1. 병용금기·주의 | 두 약을 함께 쓰면 안 되거나 조심할 조합 | 자체 구축 규칙 23건 (약학정보원·식약처 자료 근거). `use_dur` 옵션으로 식약처 DUR 병용금기 보강 |
| 2. 효능군·성분 중복 | 같은 계열·성분이 겹쳐 과용량이 되는 위험 | 성분 태그 |
| 3. 다제약물 | 약이 3·4개 이상으로 늘수록 상호작용 쌍이 늘어남 | 조합 수 계산(nC2) |
| 4. 노인·연령 주의 | 특정 연령대에 주의가 필요한 약 | 효능군별 주의 문구 (Beers Criteria 2023) |

## 판정 원칙

- 기본 판정은 이 폴더의 규칙 데이터(`data/drug_drug_interactions_demo.json`)로 함. 이때 결과에는 "자체 구축 규칙 23건 기준 (식약처 DUR API는 이번 조회에 사용되지 않음 · 참고용)"이라고 표시됨.
- `check(..., use_dur=True)`를 주면 식약처 DUR 공식 데이터(`dur_client/`)로 보강함(네트워크와 서비스키 필요). 허가정보 API로 약을 품목기준코드로 바꾼 뒤 DUR 병용금기·노인주의·임부금기 등을 조회해 `result["dur"]`에 담고, `mode`가 `LOCAL_RULES+DUR`로 바뀜. 기본값은 `use_dur=False`임.
- DUR 병용금기는 절대 금기만 등재하므로 자체 규칙을 대체하지 않고 보강만 함. 키가 없거나 조회에 실패하면 `dur.available=False`로만 표시하고 자체 규칙 판정은 그대로 유지함.
- 약 이름은 정확히 일치할 때만 해석함. 찾지 못한 약이 있고 발견된 위험이 없으면 "낮음"이 아니라 "판단 불가"로 답함.
- 이 엔진은 스스로 의학적 판단을 만들지 않음.
- 시너지(약을 조합해 효과를 높임)는 다루지 않음. 처방 영역이기 때문임.
  위험(금기·주의·중복·다제)만 안내함.

## 실행

```bash
cd engine
python3 drug_interaction.py       # 4축 분석 데모 (키 불필요, 저장된 출력은 demo_output.txt)
python3 nutrition_guide.py        # 영양 안내 데모 (nutrition_demo.txt)
python3 symptom_guide.py          # 증상별 약 계열·임부 주의 데모 (symptom_demo.txt)
python3 verify_evidence.py        # 근거 완비 여부 검증 + EVIDENCE_LEDGER.md 생성
```

효능군 중복 탐지 예시:
- 감기약 + 진통제 → 아세트아미노펜/진통 성분 중복 경고
- SSRI + 트립탄 → 세로토닌 작용 중복 (세로토닌증후군 주의)
- 벤조디아제핀 + 수면제 → 중추억제 중복 (과진정 주의)

다제약물 예시:
- 약 3개 → 3쌍 검사, 4개 → 6쌍, 5개 이상 → 다제약물 위험 경고

## 제품명 입력

계열명(성분)뿐 아니라 실제 제품명으로 입력할 수 있음.
게보린, 타이레놀, 이지엔6에이스, 판피린큐, 펜잘큐, 은교산 등 흔한 제품을
성분으로 변환해 분석함(제품 매핑 40종).

아세트아미노펜 중복 탐지 예시:
- 게보린 + 타이레놀 → 둘 다 아세트아미노펜 함유 → 간독성 위험 경고
- 감기약(판피린큐) + 두통약(타이레놀) → 아세트아미노펜 중복

같은 브랜드도 종류별 성분이 다름(이지엔6에이스=아세트아미노펜,
이지엔6프로=덱시부프로펜). 제품 매핑에 없는 제품은 서비스키(`DUR_SERVICE_KEY`)가 있을 때 식약처 e약은요 API로
조회함. 근거는 `SOURCES.md` 참조.

## 위험도 표시 방식

점수(숫자)를 쓰지 않음. 규칙 기반 레벨(낮음/보통/높음/판단 불가)을 쓰고,
그 레벨이 나온 이유를 함께 보여 줌.

레벨 결정 규칙(위에서부터 먼저 걸리는 것):
- 높음: 병용금기 '위험' 1건 이상, 또는 성분중복 '위험' 1건 이상, 또는 다제약물 5가지 이상
- 보통: '주의' 항목 1건 이상, 또는 다제약물 4가지
- 낮음: 위험·주의 발견 없음
- 판단 불가: 약이 2가지 미만이거나, 찾지 못한 약이 있는데 발견된 위험·주의가 없을 때

예) "높음, 같은 성분이 겹쳐 위험한 중복이 1건 있어요"처럼 결론과 근거를 함께 표시함.

영양소 순위도 '등장 횟수 점수'가 아니라, 어떤 조건(직업·나이) 때문에 관련되는지를
근거로 설명함. 예) "비타민D: 교대근무·오래앉음·30대 3가지 조건에 해당".

## 폴더 구성

```
packages/shared/
├── README.md / SOURCES.md
├── EVIDENCE_LEDGER.md                    # 근거 장부 (verify_evidence.py가 생성)
├── data/
│   ├── drug_dictionary.json              # 약물사전 27종 (효능군·성분태그 포함)
│   ├── drug_drug_interactions_demo.json  # 상호작용 규칙 23건 (근거수준·검증 상태 표시)
│   ├── product_ingredient_map.json       # 제품명→성분 매핑 40종 (게보린·이지엔6 등)
│   ├── evidence_sources.json             # 근거 출처 목록 13건
│   ├── ingredient_tag_basis.json         # 성분 태그 배정 기준
│   ├── nutrition_profiles.json           # 직업·나이별 영양소 정보 (16종)
│   └── symptom_pregnancy_guide.json      # 증상별 약 안내 + 임부주의
├── dur_client/
│   ├── dur_api.py                        # 식약처 DUR 품목정보 API (병용금기·노인주의 등)
│   ├── drug_permit_resolver.py           # 제품명·영문 성분명 → 품목기준코드 (허가정보 API)
│   ├── dur_check.py                      # DUR 조회 통합 진입점 (엔진의 use_dur가 호출)
│   ├── edrug_api.py                      # 식약처 e약은요 API (제품→성분, requests 필요)
│   ├── product_resolver.py               # 제품명 해석 (로컬 매핑 + API)
│   └── requirements.txt
└── engine/
    ├── drug_interaction.py               # 4축 약물 엔진
    ├── nutrition_guide.py                # 영양소 안내 엔진 (약물 연계)
    ├── symptom_guide.py                  # 증상별 약 안내 + 임부주의
    ├── verify_evidence.py                # 근거 검증 + 근거 장부 생성
    └── demo_output.txt / nutrition_demo.txt / symptom_demo.txt
```

## 식약처 DUR 연동 (옵션)

- `dur_client/dur_api.py`가 DUR 품목정보 API(`DURPrdlstInfoService03`)를 조회하고, `drug_permit_resolver.py`가 제품명·영문 성분명을 품목기준코드로 바꾸며, `dur_check.py`가 둘을 묶음. HTTP 호출은 표준 라이브러리 `urllib`를 씀.
- 엔진에는 `check(..., use_dur=True)`로 연결돼 있음. 기본값은 꺼짐이고, 서비스키(`DUR_SERVICE_KEY`, 환경변수 또는 `dur_client/.env`)가 없으면 네트워크 호출 없이 `available=False`로만 표시함.
- DUR 결과는 축 1~4의 자체 규칙 판정을 바꾸지 않고 `result["dur"]`에 따로 담김. 병용금기 쌍(`combination_taboo`)과 품목 단위 주의(`profiles[].cautions`)가 들어 있음.
- 실시간 조회 결과는 저장소에 저장돼 있지 않음. 회귀 테스트는 기본값이 꺼져 있다는 것과 키 없이 오류 없이 동작한다는 것만 확인함.
- 연동 상세는 `SOURCES.md` 참조.

## 다른 모듈에서 사용

```python
import sys
sys.path.append("../../packages/shared/engine")
from drug_interaction import check, format_report

result = check(["와파린", "부루펜", "타이레놀"], age=70)   # use_dur=True 를 주면 DUR 보강
print(format_report(result))
# result["axis1_interactions"], axis2_duplicates, axis3_polypharmacy, axis4_elderly
```

## 한계·고지

- 의료기기가 아니며 진단·처방을 하지 않음.
- 규칙 데이터는 직접 구축한 참고용이며, 식약처 DUR 공식 판정이 아님. 약사·의사의 검토를 거치지 않음.
- DB 미등재가 안전을 의미하지 않음.
- 최종 판단은 의사·약사가 하며, 위험 확인 시 약국·병원 상담을 권함.
