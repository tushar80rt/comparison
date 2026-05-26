"""
pipeline.py - Orchestrates the data gathering pipeline for comparison arena.
"""

from typing import Dict, Any, Optional

from src.logger import get_logger
from src.scraping.scrapegraph import (
    scrapegraph_scrape,
    scrapegraph_extract,
    scrapegraph_search,
    scrapegraph_crawl,
)
from src.scraping.firecrawl import (
    firecrawl_scrape,
    firecrawl_extract,
    firecrawl_search,
    firecrawl_crawl,
)
from src.rag.vector_store import create_vectorstore
from src.rag.qa_chain import get_llm
from src.utils.helpers import calculate_metrics

logger = get_logger(__name__)

def execute_comparison_pipeline(url: str, question: str, schema: Optional[dict] = None, mode: str = "Targeted Extraction") -> Dict[str, Any]:
    """Run data gathering stage for comparison arena. Builds collections."""
    logger.debug(f"Executing comparison pipeline mode: {mode}")
    
    llm = get_llm()
    
    if mode == "Raw Scrape":
        scrapegraph_data, scrapegraph_latency = scrapegraph_scrape(url)
        firecrawl_data, firecrawl_latency = firecrawl_scrape(url)
    elif mode == "Site Crawl":
        scrapegraph_data, scrapegraph_latency = scrapegraph_crawl(url, limit=5)
        firecrawl_data, firecrawl_latency = firecrawl_crawl(url, limit=5)
    elif mode == "Web Search":
        query = question if question else url
        scrapegraph_data, scrapegraph_latency = scrapegraph_search(query)
        firecrawl_data, firecrawl_latency = firecrawl_search(query)
    else:  # Targeted Extraction
        scrapegraph_data, scrapegraph_latency = scrapegraph_extract(url, question, schema)
        firecrawl_data, firecrawl_latency = firecrawl_extract(url, question, schema)

    logger.debug(f"Pipeline completed: ScrapeGraph latency {scrapegraph_latency}s, Firecrawl latency {firecrawl_latency}s")

    scrapegraph_metrics = calculate_metrics(scrapegraph_data)
    scrapegraph_metrics["scrape_latency"] = scrapegraph_latency

    firecrawl_metrics = calculate_metrics(firecrawl_data)
    firecrawl_metrics["scrape_latency"] = firecrawl_latency

    return {
        "llm": llm,
        "sg_data": scrapegraph_data,
        "fc_data": firecrawl_data,
        "sg_vectordb": create_vectorstore(scrapegraph_data, "scrapegraph_collection"),
        "fc_vectordb": create_vectorstore(firecrawl_data, "firecrawl_collection"),
        "sg_metrics": scrapegraph_metrics,
        "fc_metrics": firecrawl_metrics,
    }
