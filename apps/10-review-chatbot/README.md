# 10 · 필체크 챗봇

말하듯 물어보면 답하는 FastAPI 챗봇 — **약물 상담**은 키 없이 바로 작동하고, **쇼핑 리뷰 분석(RAG)**은 키를 넣으면 켜집니다.

## 주요 기능

메시지를 보고 자동으로 갈라집니다. 약 이야기면 약물 상담, 그 외면 리뷰 RAG.

| 기능 | 작동 조건 | 근거 |
| --- | --- | --- |
| **약물 상담** | 항상 (키 불필요) | 4축 엔진 → (키 있으면) 식약처 DUR |
| **쇼핑 리뷰 분석 (RAG)** | Gemini + Pinecone 키 있을 때 | 리뷰 벡터 검색 + LLM |

- 약 이야기 — "타이레놀이랑 게보린 같이 먹어도 돼?" → 약물 상담
- 그 외 — "실버 혈압계 어때?" → 리뷰 RAG (키 있을 때)

### 약물 상담 — 4축 엔진

`packages/shared/engine/drug_interaction.py`의 공용 엔진이 네 가지 축으로 봅니다.

1. **병용금기 · 주의** — 함께 쓰면 안 되는/조심할 약 쌍
2. **효능군(성분) 중복** — 같은 성분이 겹쳐 과용량이 되는 위험 (예: 감기약 + 두통약의 아세트아미노펜)
3. **다제약물** — 약이 늘수록 상호작용 쌍이 급증. 5가지 이상이면 약사 검토 권고
4. **노인 · 연령 주의** — 65세 이상 주의 약물 (Beers Criteria 등 근거 표시)

판정 근거는 두 가지 모드로 응답에 함께 표시됩니다.

- `DUR_OFFICIAL` — `DUR_SERVICE_KEY`가 있을 때. **식약처 공식 DUR 데이터**로 판정
- `DEMO_UNVERIFIED` — 키가 없을 때. 동봉된 **데모 데이터** 기반 (학습·시연용, 검증되지 않음)

### 입력 방식 — 약 이름을 몰라도 됩니다

- **제품 이름** — "타이레놀이랑 게보린 같이 먹어도 돼?"
- **일상어(종류)** — "혈압약이랑 소염진통제 같이 먹어도 돼?"
- **약 고르기 버튼** — 화면에서 카테고리별(상비약 / 혈압·심장 / 당뇨·콜레스테롤 / 정신건강·수면 / 위장·소화 / 감기·알레르기)로 눌러 담기

### 연계

- **음성 비서** — `/voice` 로 접속하면 말로 묻고 음성으로 듣는 화면 (`apps/voice-assistant`와 같은 화면)
- **약국 지도** — 위험이 확인되면 `apps/11-pharmacy-map`으로 이어져 주변 약국·병원에서 상담

### API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/` | 웹 채팅 화면 |
| `GET` | `/voice` | 음성 비서 화면 |
| `GET` | `/health` | 상태 + RAG 활성 여부 |
| `GET` | `/common-drugs` | '약 고르기' 버튼용 카테고리별 약 목록 |
| `POST` | `/chat` | `{ message, age? }` — 자동 라우팅(약물 상담 / 리뷰 RAG) |
| `POST` | `/drug-check` | `{ drugs: [...], age? }` — 약 목록으로 직접 상호작용 검사 |

API 문서: http://localhost:8000/docs

## 실행 방법

### 기본 — 약물 상담만 (키 불필요)

```bash
cd apps/10-review-chatbot
pip install -r requirements.txt
uvicorn app.main:app --reload
```

→ http://localhost:8000 (음성 화면은 http://localhost:8000/voice)

### 선택 1 — 식약처 DUR 공식 판정 켜기

1. [data.go.kr](https://www.data.go.kr)에서 **DURPrdlstInfoService03** 활용 신청 (무료, 개발계정 자동승인)
2. `.env.example`을 `.env`로 복사하고 `DUR_SERVICE_KEY`에 발급받은 키를 입력
3. HTTP 호출에 `requests`가 필요합니다: `pip install requests`

키를 넣으면 응답의 근거 모드가 `DEMO_UNVERIFIED` → `DUR_OFFICIAL`로 바뀝니다.

### 선택 2 — 쇼핑 리뷰 RAG 켜기

```bash
pip install -r requirements-rag.txt
```

`.env`에 두 키를 넣습니다.

```
GEMINI_API_KEY=        # https://aistudio.google.com/apikey (무료)
PINECONE_API_KEY=      # https://pinecone.io (무료 티어)
```

`/health`의 `rag_enabled`가 `true`면 켜진 것입니다. 답변에는 **어떤 리뷰를 근거로 했는지** 함께 표시됩니다.

## 기술 스택

| 항목 | 내용 |
| --- | --- |
| 백엔드 | FastAPI + Uvicorn, Pydantic v2 |
| 언어 | Python (표준 라이브러리 우선) |
| 약물 판정 | 자체 4축 엔진 + 식약처 DUR OpenAPI (`DURPrdlstInfoService03`) |
| RAG | LangChain + Pinecone(벡터DB) + Gemini(`gemini-embedding-001` 768차원, `gemini-2.0-flash`) |
| 프런트 | 정적 HTML/CSS/JS (`static/index.html`, `static/voice.html`) |
| 필요한 키 | 약물 상담 **불필요** / DUR·RAG는 선택 |

### 파일 구성

```
app/main.py             FastAPI 앱 · 라우팅 · 정적 화면 서빙
app/drug_advisor.py     메시지에서 약 이름 추출 · 약물 상담 답변 생성
rag/rag_engine.py       리뷰 RAG (키 없으면 자동 비활성)
shared/engine/          4축 상호작용 엔진 (packages/shared 공용 엔진)
shared/dur_client/      식약처 DUR API 클라이언트 · 제품명 해석
shared/data/            일상어 사전 · 성분 매핑 · 근거 출처 등 데이터셋
data/reviews.json       RAG용 데모 리뷰 (합성 데이터)
static/index.html       웹 채팅 화면
static/voice.html       음성 비서 화면 (/voice)
```

> `shared/`는 `packages/shared`의 공용 엔진·데이터셋과 동일한 사본입니다.
> 상호작용 검사가 필요하면 `drug_interaction.py`의 `check(drug_queries, age=None)`을 쓰고, 새로 만들지 않습니다.

## 주의사항

- **이 서비스는 의료기기가 아닙니다.** 진단·처방을 하지 않으며, 출력은 모두 "주의 안내"입니다.
  **최종 판단은 의사·약사가 합니다.**
- 키 없이 실행하면 판정 근거가 `DEMO_UNVERIFIED`(데모 데이터)입니다.
  **시연·학습용이며 실제 복약 판단에 사용하지 마세요.** 실제 안내에는 `DUR_SERVICE_KEY`를 넣어 공식 데이터로 운용하세요.
- **DB에 없다고 해서 안전한 것은 아닙니다.** 등재되지 않은 위험이 있을 수 있습니다.
- 엔진은 임의 판단을 하지 않습니다. 식약처 데이터를 조회해 그대로 전달하는 것이 원칙입니다.
- `data/reviews.json`은 **합성 데이터**입니다. 실제 구매 후기가 아니며 실제 개인정보를 넣지 마세요.
- `.env`는 git에 올리지 마세요(`.gitignore` 처리됨).
