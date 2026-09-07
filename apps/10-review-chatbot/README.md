# 10 · 필체크 챗봇 (완성 코드)

두 가지 상담을 하는 챗봇. **약물 상담**은 키 없이 바로 작동하고,
**쇼핑 리뷰 분석(RAG)**은 키를 넣으면 켜집니다.

## 두 가지 기능

| 기능 | 작동 조건 | 근거 |
| --- | --- | --- |
| **약물 상담** | 항상 (키 불필요) | 4축 엔진 → 식약처 DUR |
| **쇼핑 리뷰 분석 (RAG)** | Pinecone·OpenAI 키 있을 때 | 리뷰 벡터 검색 + LLM |

- 약 이야기("타이레놀이랑 게보린 같이 먹어도 돼?")면 → 약물 상담
- 그 외("실버 혈압계 어때?")면 → 리뷰 RAG (키 있을 때)

## 빠른 실행 (약물 상담만, 키 불필요)

```bash
cd apps/10-review-chatbot
pip install -r requirements.txt
uvicorn app.main:app --reload
```
→ 브라우저에서 http://localhost:8000 열기.

### 약 입력 방식 (일반인이 쓰기 쉽게)

세 가지 방법으로 물어볼 수 있어요:

- **제품 이름**: "타이레놀이랑 게보린 같이 먹어도 돼?"
- **일상어(종류)**: "혈압약이랑 소염진통제 같이 먹어도 돼?"
  (종류는 대략적 안내이고, 정확히는 제품명을 권합니다)
- **약 고르기 버튼**: 타이핑 대신 화면의 '약 고르기'에서 클릭으로 담기

처방약은 약 봉지·처방전의 이름을, 상비약은 제품 이름을 넣으면 가장 정확해요.

## RAG(쇼핑 리뷰) 켜기 (선택 — 책 10장)

1. 키 발급:
   - Pinecone: https://pinecone.io (벡터DB, 무료 티어)
   - OpenAI: https://platform.openai.com (임베딩+LLM, **유료** — 소액)
2. `.env.example`을 복사해 `.env` 만들고 키 입력:
   ```
   PINECONE_API_KEY=...
   OPENAI_API_KEY=...
   ```
3. RAG 패키지 설치:
   ```bash
   pip install -r requirements-rag.txt
   ```
4. 리뷰를 Pinecone에 넣기 (최초 1회):
   ```bash
   python -c "import sys; sys.path.insert(0,'.'); from rag.rag_engine import ingest_reviews; ingest_reviews()"
   ```
5. 서버 재시작 → 이제 "실버 혈압계 어때?" 같은 리뷰 질문에 답합니다.

## 구조

```
10-review-chatbot/
├── app/
│   ├── main.py           # FastAPI (라우팅: 약물 vs 리뷰)
│   └── drug_advisor.py   # 약물 상담 (4축 엔진 래퍼)
├── rag/
│   └── rag_engine.py     # 쇼핑 리뷰 RAG (Pinecone+OpenAI)
├── shared/               # 약물 엔진·데이터 (번들)
│   ├── engine/drug_interaction.py
│   └── data/*.json
├── static/index.html     # 웹 채팅 화면
├── data/reviews.json     # 샘플 리뷰
├── requirements.txt      # 필수 (약물 상담)
└── requirements-rag.txt  # RAG용 추가
```

## 엔드포인트

- `GET /health` — 상태 + RAG 활성 여부
- `POST /chat` — 메시지 → 약물 상담 또는 리뷰 RAG (자동 라우팅)
- `POST /drug-check` — 약 목록 배열 → 상호작용 검사
- `GET /docs` — 자동 생성 API 문서
- `GET /` — 웹 채팅 화면

## 핵심 설계

- **약물 판정은 지어내지 않는다.** 4축 엔진(→식약처 DUR)이 답하고,
  근거·출처·근거수준을 함께 보여줍니다.
- **RAG 답변은 근거 리뷰를 함께 표시**합니다 (RAG의 요점 — 어떤 리뷰를
  근거로 했는지). LLM이 리뷰에 없는 내용을 지어내지 않도록 프롬프트로 제한.
- 위험도는 화면에서 색으로 표시 (높음=빨강, 보통=주황, 낮음=청록).

## 참고

- 약물 상담을 식약처 공식 데이터로 하려면 `.env`에 `DUR_SERVICE_KEY`도 추가.
- 진단·처방이 아니며, 위험 확인 시 약국·병원 상담을 안내합니다.
