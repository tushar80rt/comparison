"""
scrapegraph.py - ScrapeGraphAI integration logic.
"""

import time
from typing import Tuple, Dict, Any, List, Optional
from scrapegraph_py import ScrapeGraphAI, MarkdownFormatConfig

from src.config import SCRAPEGRAPH_API_KEY
from src.logger import get_logger

logger = get_logger(__name__)

# Initialize client
scrapegraph_client = ScrapeGraphAI(api_key=SCRAPEGRAPH_API_KEY) if SCRAPEGRAPH_API_KEY else None


def scrapegraph_scrape(url: str) -> Tuple[Any, float]:
    """Run raw ScrapeGraphAI scrape to fetch markdown content."""
    logger.debug(f"Initiating raw ScrapeGraphAI scrape for {url}")
    start_time = time.perf_counter()
    try:
        if not scrapegraph_client:
            raise ValueError("ScrapeGraphAI API key is missing.")

        response = scrapegraph_client.scrape(
            url=url,
            formats=[MarkdownFormatConfig()]
        )
        latency = round(time.perf_counter() - start_time, 2)
        
        if response.status == "success":
            md = response.data.results.get("markdown", {}).get("data", [])
            logger.debug(f"ScrapeGraphAI scrape succeeded for {url} in {latency}s")
            return md[0] if md else None, latency
        else:
            logger.error(f"ScrapeGraphAI scrape failed for {url}: {response.error}")
            return {"error": response.error}, latency
    except Exception as e:
        logger.error(f"ScrapeGraphAI scrape exception for {url}: {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)


def scrapegraph_extract(url: str, prompt: str, schema: Optional[Dict] = None) -> Tuple[Any, float]:
    """Run ScrapeGraphAI structured extraction. Returns (data, latency_s)."""
    logger.debug(f"Initiating ScrapeGraphAI extraction for {url}")
    start_time = time.perf_counter()
    
    strict_prompt = (
        f"{prompt}\n\n"
        "STRICT EXTRACTION INSTRUCTIONS:\n"
        "1. Extract ONLY facts, figures, and data explicitly visible on the target webpage.\n"
        "2. Do NOT invent, hallucinate, assume, or extrapolate any information.\n"
        "3. If a requested data point or field is missing or not explicitly stated on the page, leave it blank or omit it entirely rather than guessing.\n"
        "4. Complete Extraction: Ensure you extract all instances of the requested data. For lists, tables, links, headings, or multiple items, extract every single one of them completely. Do not summarize, truncate, or omit items using placeholders like '...' or etc."
    )
    
    kwargs = {
        "prompt": strict_prompt, 
        "url": url,
    }
    if schema:
        kwargs["schema"] = schema
        
    try:
        if not scrapegraph_client:
            raise ValueError("ScrapeGraphAI API key is missing.")

        response = scrapegraph_client.extract(
            **kwargs
        )
        latency = round(time.perf_counter() - start_time, 2)

        if response.status == "success":
            logger.debug(f"ScrapeGraphAI extract succeeded for {url} in {latency}s")
            return response.data.json_data, latency
        else:
            logger.error(f"ScrapeGraphAI extract failed for {url}: {response.error}")
            return {"error": response.error}, latency
    except Exception as e:
        logger.error(f"ScrapeGraphAI extract exception for {url}: {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)


def scrapegraph_search(query: str) -> Tuple[Any, float]:
    """Run ScrapeGraphAI web search.
    
    Returns a rich markdown string built from each SearchResult's
    title, url, and full content — ready for RAG ingestion.
    """
    logger.debug(f"Initiating ScrapeGraphAI search for query '{query}'")
    start_time = time.perf_counter()
    try:
        if not scrapegraph_client:
            raise ValueError("ScrapeGraphAI API key is missing.")

        response = scrapegraph_client.search(
            query,          # positional: required 'query' param
            num_results=10, # fetch top 10 results
            format="markdown",
        )

        latency = round(time.perf_counter() - start_time, 2)

        if hasattr(response, "status") and response.status == "success":
            # Build a rich markdown document from each result's content
            sections: List[str] = []
            for r in response.data.results:
                title   = getattr(r, "title",   "") or ""
                url     = getattr(r, "url",     "") or ""
                content = getattr(r, "content", "") or ""
                sections.append(
                    f"## {title}\n**Source:** {url}\n\n{content}"
                )
            rich_text = "\n\n---\n\n".join(sections) if sections else ""
            logger.debug(
                f"ScrapeGraphAI search succeeded for '{query}' "
                f"— {len(sections)} results in {latency}s"
            )
            return rich_text, latency

        return {"error": getattr(response, "error", "Unknown error")}, latency
    except Exception as e:
        logger.error(f"ScrapeGraphAI search exception for '{query}': {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)


def scrapegraph_crawl(url: str, limit: int = 5) -> Tuple[Any, float]:
    """Run ScrapeGraphAI crawl and poll for completion if asynchronous."""
    start_time = time.perf_counter()
    logger.debug(f"Starting ScrapeGraphAI crawl for {url} with limit={limit}")
    try:
        if not scrapegraph_client:
            raise ValueError("ScrapeGraphAI API key is missing.")
        # Check if crawl is supported
        if not hasattr(scrapegraph_client, "crawl") or not hasattr(scrapegraph_client.crawl, "start"):
            raise NotImplementedError("ScrapeGraphAI crawl method is not available in the installed SDK version.")

        response = scrapegraph_client.crawl.start(
            url=url,
            max_depth=1,
            max_pages=limit
        )
        
        if response.status == "success" and response.data:
            job_id = response.data.id
            status = response.data.status
            logger.debug(f"ScrapeGraphAI crawl started, job_id={job_id}")
            # Poll until the crawl finishes running
            while status == "running":
                time.sleep(2)
                poll_resp = scrapegraph_client.crawl.get(job_id)
                if poll_resp.status == "success" and poll_resp.data:
                    response = poll_resp
                    status = poll_resp.data.status
                    logger.debug(f"ScrapeGraphAI crawl polling, status={status}")
                else:
                    break
        
        latency = round(time.perf_counter() - start_time, 2)
        if hasattr(response, "status") and response.status == "success":
            logger.debug(f"ScrapeGraphAI crawl succeeded for {url} in {latency}s")
            return response.data, latency
            
        err = getattr(response, 'error', 'Unknown error')
        logger.warning(f"ScrapeGraphAI crawl failed for {url}: {err}")
        return {"error": err}, latency
    except Exception as e:
        logger.error(f"ScrapeGraphAI crawl error for {url}: {e}")
        return {"error": str(e)}, round(time.perf_counter() - start_time, 2)
