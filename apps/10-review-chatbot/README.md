# 10 · 필체크 챗봇

말하듯 물어보면 답하는 FastAPI 챗봇. 약물 상담은 키 없이 바로 작동하고, 쇼핑 리뷰 분석(RAG)은 키를 넣으면 켜짐.

## 주요 기능

메시지를 보고 자동으로 갈라짐. 약 이야기면 약물 상담, 그 외면 리뷰 RAG.

| 기능 | 작동 조건 | 근거 |
| --- | --- | --- |
| 약물 상담 | 항상 (키 불필요) | 4축 엔진의 자체 규칙. `/drug-check`에 `use_dur`를 켜고 서버에 키가 있으면 식약처 DUR로 보강 |
| 쇼핑 리뷰 분석 (RAG) | Gemini + Pinecone 키 있을 때 | 리뷰 벡터 검색 + LLM |

- 약 이야기: "타이레놀이랑 게보린 같이 먹어도 돼?" → 약물 상담
- 그 외: "실버 혈압계 어때?" → 리뷰 RAG (키 있을 때)

### 약물 상담, 4축 엔진

`packages/shared/engine/drug_interaction.py`의 공용 엔진이 네 가지 축으로 분석함.

1. 병용금기·주의: 함께 쓰면 안 되거나 조심할 약 쌍
2. 효능군(성분) 중복: 같은 성분이 겹쳐 과용량이 되는 위험 (예: 감기약 + 두통약의 아세트아미노펜)
3. 다제약물: 약이 늘수록 상호작용 쌍이 늘어남. 5가지 이상이면 약사 검토 권고
4. 노인·연령 주의: 65세 이상 주의 약물 (Beers Criteria 등 근거 표시)

판정은 `shared`의 규칙 데이터로 하며, 응답의 `mode` 기본값은 `LOCAL_RULES`임.
찾지 못한 약이 있고 발견된 위험이 없으면 종합 위험도는 "판단 불가"로 나옴. 약이 2가지 미만일 때도 "판단 불가"임.

### 식약처 DUR 보강 (`use_dur` 옵션)

- `POST /drug-check`에 `use_dur: true`를 보내면 엔진이 `check(..., use_dur=True)`로 실행됨. 허가정보 API로 약을 품목기준코드로 바꾼 뒤 DUR 병용금기와 품목 단위 주의(노인주의·임부금기 등)를 조회해 응답의 `dur` 항목에 담음.
- 조회에 성공하면 `mode`가 `LOCAL_RULES+DUR`로 바뀌고, 리포트의 근거 줄이 "자체 구축 규칙 + 식약처 DUR 공식 데이터 실시간 조회"로 표시됨.
- DUR 병용금기는 절대 금기만 등재하므로 자체 규칙 판정(4축)을 대체하지 않고 덧붙이기만 함.
- 서버에 키(`DUR_SERVICE_KEY`)가 없거나 조회에 실패하면 `dur.available`이 `false`로만 표시되고 자체 규칙 결과는 그대로 반환됨. 이때 `mode`는 `LOCAL_RULES`임.
- 서비스키는 서버에서만 쓰이고 응답에 포함되지 않음. `GET /dur-status`는 키가 있는지 여부(`dur_available`)만 알려 줌.
- 웹 채팅 화면의 약 고르기에는 서버에 키가 있을 때만 "식약처 DUR 공식 데이터로 확인" 체크박스가 표시됨.
- `POST /chat`(채팅 문장 입력, 음성 화면)은 `use_dur`를 쓰지 않아 항상 자체 규칙으로만 판정함.
- DUR 조회는 외부 API 호출이라 수 초 걸릴 수 있음.

### 입력 방식

약 이름을 정확히 몰라도 입력할 수 있음.

- 제품 이름: "타이레놀이랑 게보린 같이 먹어도 돼?"
- 일상어(종류): "혈압약이랑 소염진통제 같이 먹어도 돼?"
- 약 고르기 버튼: 화면에서 카테고리별(상비약 / 혈압·심장 / 당뇨·콜레스테롤 / 정신건강·수면 / 위장·소화 / 감기·알레르기)로 눌러 담기

### 연계

- 음성 비서: `/voice`로 접속하면 말로 묻고 음성으로 듣는 화면 (`apps/voice-assistant`와 같은 화면)
- 약국 지도: 위험이 확인되면 `apps/11-pharmacy-map`으로 이어져 주변 약국·병원에서 상담

### API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/` | 웹 채팅 화면 |
| `GET` | `/voice` | 음성 비서 화면 |
| `GET` | `/health` | 상태 + RAG 활성 여부 |
| `GET` | `/common-drugs` | '약 고르기' 버튼용 카테고리별 약 목록 |
| `GET` | `/dur-status` | 서버에 DUR 키가 있는지 여부(`dur_available`). 키 값은 반환하지 않음 |
| `POST` | `/chat` | `{ message, age? }`. 자동 라우팅(약물 상담 / 리뷰 RAG) |
| `POST` | `/drug-check` | `{ drugs: [...], age?, use_dur? }`. 약 목록으로 직접 상호작용 검사. 약은 15개까지만 받음(`MAX_DRUGS`). `use_dur` 기본값은 `false` |

API 문서: http://localhost:8000/docs

## 실행 방법

### 기본: 약물 상담만 (키 불필요)

```bash
cd apps/10-review-chatbot
pip install -r requirements.txt
uvicorn app.main:app --reload
```

http://localhost:8000 (음성 화면은 http://localhost:8000/voice)

### 선택 1: 식약처 DUR 보강 켜기

1. [data.go.kr](https://www.data.go.kr)에서 DUR품목정보(`DURPrdlstInfoService03`, 15059486)와 의약품 제품 허가정보(`DrugPrdtPrmsnInfoService08`, 15095677)를 활용 신청 (무료, 개발계정 자동승인)
2. `.env.example`을 `.env`로 복사하고 `DUR_SERVICE_KEY`에 발급받은 키를 입력
3. `/drug-check`에 `use_dur: true`를 보내거나, 웹 화면의 약 고르기에서 "식약처 DUR 공식 데이터로 확인"을 체크

DUR·허가정보 조회는 표준 라이브러리(`urllib`)로 하므로 추가 설치가 필요 없음. 키가 있으면 사전에 없는 제품명을 e약은요 API로 조회하는 경로(`shared/dur_client/edrug_api.py`)도 열리는데, 이 경로만 `requests`가 필요함(`pip install requests`). `requests`가 없으면 이 조회는 건너뜀.

`.env`는 `python-dotenv`가 설치돼 있을 때만 읽힘(`requirements-rag.txt`에 포함). 설치하지 않았다면 `DUR_SERVICE_KEY`를 환경변수로 넣거나 `shared/dur_client/.env`에 넣어야 함(`dur_api.py`가 직접 읽음).

### 선택 2: 쇼핑 리뷰 RAG 켜기

```bash
pip install -r requirements-rag.txt
```

`.env`에 두 키를 넣음.

```
GEMINI_API_KEY=        # https://aistudio.google.com/apikey (무료)
PINECONE_API_KEY=      # https://pinecone.io (무료 티어)
```

`/health`의 `rag_enabled`가 `true`면 켜진 것임. 답변에는 어떤 리뷰를 근거로 했는지 함께 표시됨.

## 기술 스택

| 항목 | 내용 |
| --- | --- |
| 백엔드 | FastAPI + Uvicorn, Pydantic v2 |
| 언어 | Python (표준 라이브러리 우선) |
| 약물 판정 | 자체 4축 엔진. 옵션으로 식약처 DUR OpenAPI(`DURPrdlstInfoService03`) 보강 |
| RAG | LangChain + Pinecone(벡터DB) + Gemini(`gemini-embedding-001` 768차원, `gemini-2.0-flash`) |
| 프런트 | 정적 HTML/CSS/JS (`static/index.html`, `static/voice.html`) |
| 필요한 키 | 약물 상담은 불필요. DUR·RAG는 선택 |

### 파일 구성

```
app/main.py             FastAPI 앱, 라우팅, 정적 화면 서빙
app/drug_advisor.py     메시지에서 약 이름 추출, 약물 상담 답변 생성
rag/rag_engine.py       리뷰 RAG (키 없으면 자동 비활성)
shared/engine/          4축 상호작용 엔진 (packages/shared 공용 엔진의 사본)
shared/dur_client/      식약처 DUR·허가정보·e약은요 API 클라이언트, 제품명 해석
shared/data/            일상어 사전, 성분 매핑, 근거 출처 등 데이터셋
data/reviews.json       RAG용 데모 리뷰 (합성 데이터, 12건)
static/index.html       웹 채팅 화면
static/voice.html       음성 비서 화면 (/voice)
```

> `shared/`는 `packages/shared`의 엔진(`drug_interaction.py`)·DUR 클라이언트·데이터를 배포용으로 복사한 사본임. 일상어 사전(`shared/data/colloquial_drugs.json`)은 이 앱에만 있음. 사본이 원본과 같은지는 `tests/test_engine.py`가 확인함.
> 상호작용 검사가 필요하면 `drug_interaction.py`의 `check(drug_queries, age=None, use_dur=False)`를 쓰고, 새로 만들지 않음.

## 주의사항

- 이 서비스는 의료기기가 아님. 진단·처방을 하지 않으며, 출력은 모두 "주의 안내"임. 최종 판단은 의사·약사가 함.
- 기본 판정 근거는 직접 구축한 규칙 데이터(`LOCAL_RULES`)이며 식약처 DUR 공식 판정이 아님. `use_dur`를 켜도 DUR 결과는 자체 규칙에 덧붙는 참고 정보임. 실제 복약 판단에 사용하지 말 것.
- DB에 없다고 해서 안전한 것은 아님. 등재되지 않은 위험이 있을 수 있음.
- 엔진은 스스로 의학적 판단을 만들지 않음. 규칙 데이터와 조회한 식약처 데이터를 정리해 전달함.
- `data/reviews.json`은 합성 데이터임. 실제 구매 후기가 아니며 실제 개인정보를 넣지 말 것.
- `.env`는 git에 올리지 말 것(`.gitignore` 처리됨).
