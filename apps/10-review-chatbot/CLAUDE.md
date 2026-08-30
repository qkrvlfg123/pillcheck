# CLAUDE.md — 10 리뷰·약물 상담 챗봇

## 이 앱의 목표
근거를 제시하는 RAG 챗봇. (1) 쇼핑 리뷰 분석 (2) 약물 상호작용 상담.

## 스택
- FastAPI (파이썬)
- 임베딩 + 랭체인 + Pinecone (벡터DB)
- 약물 상담 백엔드: ../../packages/shared/engine/drug_interaction.py

## 핵심 규칙
- **답변에는 근거를 함께 표시한다.** RAG의 요점 — 어떤 문서/리뷰/규칙을
  근거로 했는지 보여줄 것.
- **약물 상호작용 판정은 식약처 DUR이 한다.** 임의로 판단하지 말 것.
  `check()`를 호출하면 DUR 우선·데모 폴백으로 동작하며, 결과의 mode가
  DUR_OFFICIAL인지 DEMO_UNVERIFIED인지 사용자에게 그대로 표시할 것.
- 약 상담 답변은 단정하지 않는다. "주의 필요, 약사 상의" 톤. "의료기기 아님" 고지.
- DB 미등재가 안전을 의미하지 않는다는 안내를 포함할 것.
- API 키(Pinecone, LLM, DUR)는 전부 .env, git 금지.

## 엔드포인트
- `/health` : 상태 확인
- `/chat` : 질문 → RAG 답변 (약 질문이면 /drug-check로 라우팅)
- `/drug-check` : 약 목록 → 상호작용 검사 결과

## 명령어
- `uvicorn main:app --reload` : 로컬 실행
- 실행 전 `pip install -r requirements.txt`
