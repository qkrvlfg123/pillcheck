# 음성 비서 (Voice Assistant)

10번 챗봇을 말로 쓰는 화면. 마이크 버튼을 누르고 약에 대해 물어보면 음성으로 답함. 타이핑이 어려운 고령자를 위한 입력 화면임.

## 주요 기능

- 음성으로 질문: 큰 마이크 버튼을 누르고 말하면 브라우저 음성 인식(STT)이 한국어(`ko-KR`)로 받아씀
- 음성으로 답변: 답을 브라우저 음성 합성(TTS)으로 읽어 줌. 고령자 배려로 조금 느린 속도(rate 0.95)
- 다시 듣기 / 그만 듣기: 마지막 답변 다시 재생, 읽는 도중 중지
- 긴 리포트는 짧게: 약물 상담 리포트를 다 읽지 않고 위험도, 주요 내용, 상담 안내만 요약해 읽어 줌
- 화면에도 표시: 인식된 말과 답변 전문을 큰 글씨로 함께 보여 줌
- 답변 내용은 10번 챗봇의 `/chat`과 같음. 약물 4축 엔진(병용금기, 성분중복, 다제약물, 노인주의)과 리뷰 RAG

### 작동 흐름

```
말하기 → [브라우저 STT] → 텍스트 → [10 챗봇 /chat] → 답변 → [브라우저 TTS] → 듣기
```

이 구조를 택한 이유:

- 음성 입출력은 브라우저 내장 기능을 씀. 무료, 설치 없음, 한국어 지원, API 키 노출 위험 없음
- 답변 생성은 10 챗봇에 위임함. 판정 로직을 두 곳에 두지 않음

## 실행 방법

이 화면은 10번 챗봇 서버가 함께 서빙함. 별도 서버가 필요 없음.

```bash
cd apps/10-review-chatbot
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 http://localhost:8000/voice 접속

> `apps/voice-assistant/index.html`은 같은 화면의 단독 사본임.
> 따로 띄울 경우 `/chat` 요청이 챗봇 서버에 닿아야 하므로, 파일 안의
> `API_BASE`를 `"http://localhost:8000"`으로 바꾸고 챗봇 쪽 CORS를 허용해야 함.
> `/voice`로 접속하는 방법이 가장 간단함.

### Vercel 배포

공개 배포본(https://voice-assistant-nine-drab.vercel.app)은 `/chat`을 Vercel 서버리스 함수
(`api/chat.py`)가 처리하므로 별도 챗봇 서버 없이 단독으로 동작함.
`vercel.json`의 rewrite가 `/chat` → `/api/chat`을 연결하기 때문에 `index.html`은
고치지 않음(10 챗봇의 `static/voice.html`과 동일하게 유지).

> 엔진은 `apps/10-review-chatbot` 원본을 배포 편의상 `api/_bundle/`에 번들한 사본임.
> Vercel 함수가 Root Directory 바깥 파일을 번들하지 못해 복사했으며, 원본이 바뀌면
> 다시 복사해야 함. 이유와 재복사 명령은 `api/chat.py` 상단 주석에 있음.
> 번들에는 DUR 클라이언트(`shared/dur_client/`)도 들어 있지만 이 함수는 `use_dur` 없이 엔진을 호출하므로 식약처 DUR을 조회하지 않음.
> 리뷰 RAG는 키가 없어 기존 폴백 문구를 그대로 돌려줌(약물 상담은 키 없이 동작).

### 브라우저

음성 인식은 Chrome·Edge에서 가장 잘 동작함. 마이크 권한을 허용해야 함.
(Safari·Firefox는 음성 인식이 제한되거나 동작하지 않을 수 있음.)

## 기술 스택

| 항목 | 내용 |
| --- | --- |
| 구성 | HTML, CSS, 바닐라 JavaScript 파일 하나 (`index.html`, 빌드 없음) |
| 음성 인식 | Web Speech API의 `SpeechRecognition` / `webkitSpeechRecognition` (`ko-KR`) |
| 음성 합성 | Web Speech API의 `speechSynthesis` (`ko-KR`) |
| 백엔드 | `apps/10-review-chatbot`의 `POST /chat`. Vercel 배포본은 `api/chat.py` |
| 필요한 키 | 불필요 (로컬에서는 10 챗봇 서버가 떠 있어야 함) |

## 주의사항

- 이 서비스는 의료기기가 아님. 진단·처방을 하지 않으며 참고용 안내임.
  최종 판단은 의사·약사가 함.
- 음성 답변은 요약본임. 위험도와 주요 내용만 읽어 주므로, 자세한 근거는 화면의 전문이나
  웹 채팅 화면(http://localhost:8000)에서 확인해야 함.
- 음성 인식은 약 이름을 잘못 알아들을 수 있음. 화면에 표시된 인식 결과가 맞는지 확인해야 함.
- 판정 근거는 직접 구축한 규칙 데이터(`LOCAL_RULES`)이며 식약처 DUR 공식 판정이 아님.
  음성 화면이 쓰는 `/chat` 경로는 DUR 보강(`use_dur`)을 쓰지 않음. 실제 복약 판단에 사용하지 말 것.
- 음성은 주변에 들림. 복용 중인 약은 민감한 개인정보이니 공공장소에서는 주의할 것.
