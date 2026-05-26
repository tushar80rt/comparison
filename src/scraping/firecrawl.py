"""
firecrawl.py - Firecrawl integration logic.
"""

import time
from typing import Tuple, Dict, Any, List, Optional
from firecrawl import Firecrawl

from src.config import FIRECRAWL_API_KEY
from src.logger import get_logger

logger = get_logger(__name__)

# Initialize client
firecrawl_client = Firecrawl(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY else None


def _normalize_firecrawl_response(response: Any) -> Any:
    """Normalize any Firecrawl response to standard Python primitives (dict, list, str)."""
    if response is None:
        return None
    # If it has model_dump (Pydantic v2)
    if hasattr(response, "model_dump") and callable(response.model_dump):
        return response.model_dump()
    # If it has dict (Pydantic v1)
    if hasattr(response, "dict") and callable(response.dict):
        return response.dict()
    # If it is a list, normalize each element
    if isinstance(response, list):
        return [_normalize_firecrawl_response(x) for x in response]
    # If it is a dict, normalize values
    if isinstance(response, dict):
        return {k: _normalize_firecrawl_response(v) for k, v in response.items()}
    # Return primitive directly
    return response


def firecrawl_scrape(url: str) -> Tuple[Any, float]:
    """Run raw Firecrawl scrape to fetch markdown content."""
    logger.debug(f"Initiating raw Firecrawl scrape for {url}")
    start_time = time.perf_counter()
    try:
        if not firecrawl_client:
            raise ValueError("Firecrawl API key is missing.")
        response = firecrawl_client.scrape(url, formats=["markdown"])
        latency = round(time.perf_counter() - start_time, 2)
        
        # Handle dict or object responses to extract markdown directly
        markdown_content = None
        if isinstance(response, dict):
            markdown_content = response.get("markdown")
        elif hasattr(response, "markdown"):
            markdown_content = getattr(response, "markdown")
            
        if markdown_content is not None:
            logger.debug(f"Firecrawl scrape succeeded for {url} in {latency}s")
            return markdown_content, latency
            
        # Fallback to normalized response
        normalized = _normalize_firecrawl_response(response)
        logger.debug(f"Firecrawl scrape returned complex response for {url} in {latency}s")
        return normalized, latency
    except Exception as e:
        logger.error(f"Firecrawl scrape error for {url}: {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)


def firecrawl_extract(url: str, prompt: str, schema: Optional[Dict] = None) -> Tuple[Any, float]:
    """Run Firecrawl LLM extraction using the official SDK signature.

    Official signature (firecrawl-py v2):
        client.extract(urls: List[str], prompt: str, schema: BaseModel | dict | None)
    """
    if not prompt:
        raise ValueError("Prompt is required for firecrawl_extract LLM extraction.")
    logger.debug(f"Initiating Firecrawl LLM extraction for {url} with prompt '{prompt}'")
    start_time = time.perf_counter()
    try:
        if not firecrawl_client:
            raise ValueError("Firecrawl API key is missing.")
        strict_prompt = (
            f"{prompt}\n\n"
            "STRICT EXTRACTION INSTRUCTIONS:\n"
            "1. Extract ONLY facts, figures, and data explicitly visible on the target webpage.\n"
            "2. Do NOT invent, hallucinate, assume, or extrapolate any information.\n"
            "3. If a requested data point or field is missing or not explicitly stated on the page, leave it blank or omit it entirely rather than guessing.\n"
            "4. Complete Extraction: Ensure you extract all instances of the requested data. For lists, tables, links, headings, or multiple items, extract every single one of them completely. Do not summarize, truncate, or omit items using placeholders like '...' or etc."
        )
        # Build kwargs — only include schema if provided
        kwargs: Dict[str, Any] = {"prompt": strict_prompt}
        if schema:
            kwargs["schema"] = schema

        # SDK call: extract(urls, prompt=..., schema=...)
        response = firecrawl_client.extract([url], **kwargs)
        latency = round(time.perf_counter() - start_time, 2)

        # Normalize the response
        normalized = _normalize_firecrawl_response(response)
        if isinstance(normalized, dict):
            if normalized.get("success"):
                logger.debug(f"Firecrawl extract succeeded for {url} in {latency}s")
                return normalized.get("data"), latency
            elif "data" in normalized:
                logger.debug(f"Firecrawl extract succeeded for {url} in {latency}s")
                return normalized.get("data"), latency
                
        logger.debug(f"Firecrawl extract succeeded for {url} in {latency}s")
        return normalized, latency
    except Exception as e:
        logger.error(f"Firecrawl LLM extraction error for {url}: {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)


def firecrawl_search(query: str) -> Tuple[Any, float]:
    """Run Firecrawl web search."""
    logger.debug(f"Initiating Firecrawl web search for query '{query}'")
    start_time = time.perf_counter()
    try:
        if not firecrawl_client:
            raise ValueError("Firecrawl API key is missing.")
        response = firecrawl_client.search(query)
        latency = round(time.perf_counter() - start_time, 2)
        normalized = _normalize_firecrawl_response(response)
        return normalized, latency
    except Exception as e:
        logger.error(f"Firecrawl search error for '{query}': {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)


def firecrawl_crawl(url: str, limit: int = 5) -> Tuple[Any, float]:
    """Run Firecrawl site crawl."""
    start_time = time.perf_counter()
    logger.debug(f"Starting Firecrawl site crawl for {url} with limit={limit}")
    try:
        if not firecrawl_client:
            raise ValueError("Firecrawl API key is missing.")
        response = firecrawl_client.crawl(
            url,
            limit=limit,
            formats=["markdown"],
        )
        latency = round(time.perf_counter() - start_time, 2)
        normalized = _normalize_firecrawl_response(response)
        logger.debug(f"Firecrawl crawl completed for {url} in {latency}s")
        return normalized, latency
    except Exception as e:
        logger.error(f"Firecrawl crawl error for {url}: {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)
