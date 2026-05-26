"""
qa_chain.py - RAG pipeline logic.
"""

from typing import Generator
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_community.vectorstores import Chroma

from src.config import GROQ_API_KEY, LLM_MODEL
from src.logger import get_logger

logger = get_logger(__name__)

_RAG_SYSTEM_PROMPT = (
    "You are a strict research extraction assistant. Your ONLY job is to extract and present "
    "information that is EXPLICITLY present in the Context provided below.\n\n"
    "ABSOLUTE RULES — violating any of these is a critical failure:\n\n"
    "1. DATA ALREADY COLLECTED: A web scrape, crawl, or search has ALREADY been completed. "
    "The full page content, including code snippets, headings, links, and tables, is provided "
    "in the Context below. Do NOT say you cannot access the internet or cannot crawl/scrape.\n\n"
    "2. ZERO HALLUCINATION: Do NOT add ANY information that is not word-for-word present in the "
    "Context. No guessing. No extrapolation. No 'typically', 'usually', or 'generally' statements. "
    "If something is not in the Context, say exactly: 'Not found in the extracted content.'\n\n"
    "3. CODE SNIPPETS — COPY VERBATIM: If the Context contains code snippets (Python, bash, JSON, "
    "etc.), you MUST reproduce them EXACTLY as they appear using markdown code blocks (```language). "
    "Do NOT paraphrase, summarize, or rewrite code. Do NOT invent code that is not in the Context.\n\n"
    "4. COMPLETE EXTRACTION: Extract ALL relevant instances — every framework, every link, every "
    "heading, every code block — that answers the user's question. Do not skip or truncate items.\n\n"
    "5. NO INVENTED TABLES: Only create comparison tables if the data to fill them is explicitly "
    "present in the Context. Do NOT create table rows with 'Not provided', 'N/A', or '-' for data "
    "you simply don't have — omit those rows entirely.\n\n"
    "6. STRUCTURE: Use clean Markdown — headings, bullet lists, numbered lists, and fenced code "
    "blocks. Start directly with the content, no preamble like 'Based on the context...'.\n\n"
    "Context:\n{context}"
)


def get_llm() -> ChatGroq:
    """Return a streaming Llama-4 LLM instance."""
    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name=LLM_MODEL,
        streaming=True,
        temperature=0.0,
        max_tokens=8192,
    )
    logger.debug(f"Initialized LLM with model {LLM_MODEL}")
    return llm


def _build_rag_chain(vectordb: Chroma, llm: ChatGroq):
    """Build a Retrieval-QA LangChain retrieval chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _RAG_SYSTEM_PROMPT),
        ("human", "{input}"),
    ])
    # k=12 — fetch more chunks so all models/items reach the LLM context
    retriever = vectordb.as_retriever(search_kwargs={"k": 12})
    return create_retrieval_chain(
        retriever,
        create_stuff_documents_chain(llm, prompt),
    )


def stream_rag_answer(vectordb: Chroma, question: str, llm: ChatGroq) -> Generator[str, None, None]:
    """Stream RAG answer - yields text chunks."""
    for chunk in _build_rag_chain(vectordb, llm).stream({"input": question}):
        if "answer" in chunk:
            yield chunk["answer"]


def generate_rag_answer(vectordb: Chroma, question: str, llm: ChatGroq) -> str:
    """Invoke RAG chain and return the answer string."""
    return _build_rag_chain(vectordb, llm).invoke({"input": question})["answer"]
