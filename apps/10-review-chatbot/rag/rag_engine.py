"""
RAG 엔진 — 쇼핑 리뷰 분석 (책 10장 방식, Gemini 기반)
=====================================================

Pinecone(벡터DB) + Gemini(임베딩·LLM) + LangChain으로 리뷰를 근거로 답한다.

키가 없으면 이 모듈은 '비활성'이며, 챗봇은 약물 상담만 제공한다.
키(GEMINI_API_KEY + PINECONE_API_KEY)를 넣으면 리뷰 검색 기반 답변이 활성화된다.

* 답변에는 어떤 리뷰를 근거로 했는지 함께 표시한다(RAG의 요점).
* Gemini는 무료 티어가 넉넉해 부담이 적다.
"""

import json
import os

HERE = os.path.dirname(__file__)
INDEX_NAME = "pillcheck-reviews"

# Gemini 임베딩 차원 (gemini-embedding-001 기본 3072, 여기선 768로 축소해 저장 효율↑)
EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIM = 768
CHAT_MODEL = "gemini-2.0-flash"


def rag_available() -> bool:
    """RAG에 필요한 키가 모두 있는지."""
    return bool(os.getenv("PINECONE_API_KEY") and os.getenv("GEMINI_API_KEY"))


def _load_reviews():
    path = os.path.join(HERE, "..", "data", "reviews.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(
        model=EMBED_MODEL,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        output_dimensionality=EMBED_DIM,
    )


def ingest_reviews():
    """
    리뷰를 임베딩해서 Pinecone에 저장. (최초 1회, 키 있을 때)
    실행: python -c "import sys; sys.path.insert(0,'.'); from rag.rag_engine import ingest_reviews; ingest_reviews()"
    """
    if not rag_available():
        print("[안내] GEMINI_API_KEY, PINECONE_API_KEY 가 필요합니다.")
        return

    from pinecone import Pinecone, ServerlessSpec
    from langchain_pinecone import PineconeVectorStore
    from langchain_core.documents import Document

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    existing = [i.name for i in pc.list_indexes()]
    if INDEX_NAME not in existing:
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    reviews = _load_reviews()
    docs = [
        Document(page_content=r["review"], metadata={"product": r["product"]})
        for r in reviews
    ]

    store = PineconeVectorStore(index_name=INDEX_NAME, embedding=_embeddings())
    store.add_documents(docs)
    print(f"[완료] 리뷰 {len(docs)}건을 Pinecone에 저장했습니다. (Gemini 임베딩)")


def answer_review_question(question: str) -> dict:
    """리뷰 기반 질문에 답한다 (RAG). 근거 리뷰를 함께 반환."""
    if not rag_available():
        return {
            "type": "review",
            "answer": "쇼핑 리뷰 분석(RAG)은 Gemini·Pinecone 키를 넣으면 켜져요. "
                      "지금은 약물 상담을 이용해 주세요. (.env 참고)",
            "sources": [],
        }

    from langchain_pinecone import PineconeVectorStore
    from langchain_google_genai import ChatGoogleGenerativeAI

    store = PineconeVectorStore(index_name=INDEX_NAME, embedding=_embeddings())
    docs = store.similarity_search(question, k=4)
    context = "\n".join(f"- ({d.metadata.get('product','')}) {d.page_content}" for d in docs)

    llm = ChatGoogleGenerativeAI(
        model=CHAT_MODEL,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )
    prompt = (
        "너는 쇼핑 리뷰를 근거로 답하는 도우미야. 아래 리뷰만 근거로, "
        "질문에 대해 장단점을 요약해줘. 리뷰에 없는 내용은 지어내지 마.\n\n"
        f"[리뷰]\n{context}\n\n[질문] {question}\n\n[답변]"
    )
    resp = llm.invoke(prompt)

    return {
        "type": "review",
        "answer": resp.content,
        "sources": [
            {"product": d.metadata.get("product", ""), "review": d.page_content}
            for d in docs
        ],
    }
