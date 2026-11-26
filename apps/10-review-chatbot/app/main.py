"""
필체크 챗봇 — FastAPI 백엔드
============================

두 가지 상담:
  1) 약물 상담  — 우리 4축 엔진 (키 불필요, 항상 작동)
  2) 쇼핑 리뷰  — RAG (Gemini·Pinecone 키 있을 때)

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
    use_dur: bool = False     # True면 식약처 DUR 공식 데이터로 보강(서버에서만 키 사용, 느릴 수 있음)


MAX_DRUGS = 15               # 남용·과도한 외부 호출 방지


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


def _dur_key_present():
    import sys
    sys.path.append(os.path.join(HERE, "..", "shared", "engine"))
    try:
        import dur_api
        return bool(getattr(dur_api, "SERVICE_KEY", ""))
    except Exception:
        return False


@app.get("/dur-status")
def dur_status():
    """식약처 DUR 보강을 쓸 수 있는지(서버에 키가 있는지)만 알려준다. 키 값은 노출하지 않는다."""
    return {"dur_available": _dur_key_present()}


@app.post("/drug-check")
def drug_check(req: DrugCheckRequest):
    """
    약 목록을 받아 상호작용을 검사한다(약 이름 배열).

    use_dur=True면 식약처 DUR 공식 데이터로 보강한다. 이때 서비스키는 **서버 환경변수
    (DUR_SERVICE_KEY)**로만 쓰이며 응답에 노출되지 않는다(프록시). 키가 없거나 조회에
    실패하면 dur.available=False로만 표시하고 로컬 규칙 결과는 그대로 돌려준다.
    DUR 조회는 외부 API 호출이라 수 초 걸릴 수 있다.
    """
    import sys
    sys.path.append(os.path.join(HERE, "..", "shared", "engine"))
    import drug_interaction as engine

    drugs = [d for d in (req.drugs or []) if str(d).strip()][:MAX_DRUGS]
    result = engine.check(drugs, age=req.age, use_dur=req.use_dur)

    resp = {
        "type": "drug",
        "mode": result["mode"],
        "overall_risk": result["overall_risk"],
        "report": engine.format_report(result),
    }
    dur = result.get("dur")
    if dur is not None:
        # 프런트가 직접 렌더링할 수 있도록 구조화된 DUR 결과도 함께 준다(키는 포함 안 됨).
        resp["dur"] = {
            "available": dur.get("available", False),
            "reason": dur.get("reason"),
            "combination_taboo": dur.get("combination_taboo", []),
            "cautions": [
                {"label": p["label"], "item_seq": p["item_seq"],
                 "types": {k: len(v) for k, v in (p.get("cautions") or {}).items() if v}}
                for p in dur.get("profiles", [])
                if p.get("item_seq") and (p.get("taboo_partners") or p.get("cautions"))
            ],
            "unresolved": dur.get("unresolved", []),
        }
    return resp


# 정적 파일(웹 채팅 화면)
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/voice")
    def voice():
        return FileResponse(os.path.join(STATIC_DIR, "voice.html"))
