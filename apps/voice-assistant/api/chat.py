"""
/chat — 음성 비서용 서버리스 함수 (Vercel Python Runtime)

10-review-chatbot의 FastAPI `@app.post("/chat")` 라우팅을 그대로 옮긴 것이다.
약 이야기면 약물 상담, 아니면 리뷰 RAG 폴백 문구를 돌려준다.

[왜 엔진 복사본(_bundle/)이 여기에 있는가]
--------------------------------------------------
저장소 규칙(CLAUDE.md)은 약물 엔진을 새로 만들지 말고
`packages/shared/engine/drug_interaction.py`를 쓰라고 한다. 이 원칙은 유효하다.
다만 Vercel 서버리스 함수는 **자기 프로젝트 Root Directory 바깥의 파일을
번들에 포함하지 못한다.** 이 프로젝트의 Root Directory는 `apps/voice-assistant`
이므로 `packages/shared/`나 `apps/10-review-chatbot/shared/`를 그대로 참조할 수
없다. 그래서 배포 번들 목적에 한해 사용자 승인을 받아 복사본을 두었다.

`_bundle/` 아래 파일은 **직접 수정하지 말 것.** 원본은
`apps/10-review-chatbot/`이며, 원본이 바뀌면 아래 명령으로 다시 복사한다.

    cp apps/10-review-chatbot/app/drug_advisor.py \
       apps/voice-assistant/api/_bundle/app/
    cp apps/10-review-chatbot/shared/engine/drug_interaction.py \
       apps/voice-assistant/api/_bundle/shared/engine/
    cp apps/10-review-chatbot/shared/data/*.json \
       apps/voice-assistant/api/_bundle/shared/data/

디렉터리 구조를 원본과 똑같이 맞춰 둔 이유도 이것이다. 두 파일 모두 경로를
`__file__` 기준 상대경로로 잡기 때문에, 구조만 같으면 코드를 한 줄도 고치지
않은 채 복사본을 그대로 쓸 수 있고 `diff`로 원본과의 어긋남을 바로 확인할 수 있다.

DUR 클라이언트(`dur_api.py`)는 일부러 번들하지 않았다. 없으면 엔진이
`_DUR_AVAILABLE = False`로 떨어져 키 없이 DEMO 모드로 동작한다.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_bundle", "app"))

import drug_advisor

# rag_engine.answer_review_question()이 키 없을 때 돌려주는 문구를 그대로 옮긴 것.
# 이 배포에는 Gemini·Pinecone 키가 없으므로 리뷰 질문은 항상 이 응답이 된다.
REVIEW_FALLBACK = {
    "type": "review",
    "answer": "쇼핑 리뷰 분석(RAG)은 Gemini·Pinecone 키를 넣으면 켜져요. "
              "지금은 약물 상담을 이용해 주세요. (.env 참고)",
    "sources": [],
}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw or b"{}")
            text = str(payload.get("message") or "").strip()
            age = payload.get("age")

            # 10-review-chatbot main.py의 chat()과 동일한 라우팅
            if drug_advisor.is_drug_question(text):
                body = drug_advisor.answer_drug_question(text, age=age)
            else:
                body = REVIEW_FALLBACK

            self._respond(200, body)
        except Exception:
            self._respond(500, {
                "type": "error",
                "answer": "잠시 문제가 생겼어요. 다시 말씀해 주세요.",
            })

    def _respond(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
