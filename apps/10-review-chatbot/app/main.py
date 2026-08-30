"""
필체크 챗봇 — FastAPI 백엔드
============================

두 가지 상담:
  1) 약물 상담  — 우리 4축 엔진 (키 불필요, 항상 작동)
  2) 쇼핑 리뷰  — RAG (Pinecone·OpenAI 키 있을 때)

메시지를 보고 자동으로 라우팅한다. 약 이야기면 약물 상담, 아니면 리뷰 RAG.

실행: uvicorn app.main:app --reload
문서: http://localhost:8000/docs
화면: http://localhost:8000/
"""

import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# .env 로드 (있으면)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from app.drug_advisor import is_drug_question, answer_drug_question
from rag.rag_engine import answer_review_question, rag_available

app = FastAPI(title="필체크 챗봇")

HERE = os.path.dirname(__file__)
STATIC_DIR = os.path.join(HERE, "..", "static")


class ChatRequest(BaseModel):
    message: str
    age: int | None = None


class DrugCheckRequest(BaseModel):
    drugs: list[str]
    age: int | None = None


@app.get("/common-drugs")
def common_drugs():
    """화면의 '약 고르기' 버튼용 — 흔한 약을 카테고리별로."""
    return {
        "카테고리": [
            {"이름": "상비약", "약": ["타이레놀", "게보린", "부루펜", "판피린", "이지엔6"]},
            {"이름": "혈압/심장", "약": ["혈압약", "노바스크", "디오반", "혈전약"]},
            {"이름": "당뇨/콜레스테롤", "약": ["당뇨약", "콜레스테롤약", "리피토"]},
            {"이름": "정신건강/수면", "약": ["우울증약", "신경안정제", "수면제"]},
            {"이름": "위장/소화", "약": ["위장약", "제산제", "소화제"]},
            {"이름": "감기/알레르기", "약": ["감기약", "알레르기약", "편두통약"]},
        ]
    }


@app.get("/health")
def health():
    return {"status": "ok", "rag_enabled": rag_available()}


@app.post("/chat")
def chat(req: ChatRequest):
    """메시지를 받아 약물 상담 또는 리뷰 RAG로 라우팅."""
    text = req.message.strip()

    # 약 이야기면 약물 상담, 아니면 리뷰 RAG
    if is_drug_question(text):
        return answer_drug_question(text, age=req.age)
    else:
        return answer_review_question(text)


@app.post("/drug-check")
def drug_check(req: DrugCheckRequest):
    """약 목록을 직접 받아 상호작용 검사 (약 이름 배열)."""
    import sys
    sys.path.append(os.path.join(HERE, "..", "shared", "engine"))
    import drug_interaction as engine

    result = engine.check(req.drugs, age=req.age)
    return {
        "type": "drug",
        "mode": result["mode"],
        "overall_risk": result["overall_risk"],
        "report": engine.format_report(result),
    }


# 정적 파일(웹 채팅 화면)
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/voice")
    def voice():
        return FileResponse(os.path.join(STATIC_DIR, "voice.html"))
