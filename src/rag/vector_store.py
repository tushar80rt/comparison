"""
vector_store.py - Vector store (ChromaDB) logic.
"""

import os
import json
import time
import uuid
import chromadb
from typing import Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import CHROMA_DIR, EMBED_MODEL
from src.logger import get_logger

logger = get_logger(__name__)


def to_rag_text(data: Any) -> str:
    """Convert any scrape/crawl data to a text format suitable for RAG chunking, preserving extra fields."""
    if hasattr(data, "model_dump"):
        try:
            return json.dumps(data.model_dump(exclude_none=True), default=str, indent=2)
        except Exception:
            return str(data)
    elif isinstance(data, (dict, list)):
        return json.dumps(data, default=str, indent=2)
    return str(data)


def create_vectorstore(data: Any, collection_name: str) -> Chroma:
    """
    Chunk data, embed it in a persistent Chroma instance so vectors survive across runs.
    Generates a unique collection name per invocation.
    """
    # Ensure persistence directory exists
    os.makedirs(CHROMA_DIR, exist_ok=True)
    
    # Persistent client stores vectors under CHROMA_DIR
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    # Create a unique collection name using timestamp and uuid
    unique_name = f"{collection_name}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    docs = [Document(page_content=to_rag_text(data))]
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = splitter.split_documents(docs)
    
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    
    logger.debug(f"Creating vectorstore collection: {unique_name} with {len(split_docs)} chunks")
    
    return Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        collection_name=unique_name,
        client=client,
    )
