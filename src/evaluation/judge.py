"""
judge.py - LLM judge comparison logic.
"""

from typing import Generator
from langchain_groq import ChatGroq

from src.logger import get_logger

logger = get_logger(__name__)

def stream_judge_verdict(question: str, scrapegraph_answer: str, firecrawl_answer: str, sg_m: dict, fc_m: dict, language_model: ChatGroq) -> Generator[str, None, None]:
    """Stream comparative judge verdict - yields text chunks with RateLimit handling."""
    
    def _fmt(val):
        return f"{val:.2f}" if isinstance(val, (int, float)) else "N/A"
        
    judge_prompt = f"""You are an expert AI benchmarking judge. Evaluate two RAG answers with strict objectivity.

## CRITICAL RULE — BLIND JUDGE PROTOCOL
You are a BLIND judge. You have NO access to external knowledge, the internet, or your own training data about the world.
- Do NOT use your knowledge of product releases, company news, or real-world facts to verify or dispute the answers.
- Do NOT say any data "seems future", "seems rumored", or "seems incorrect" based on what YOU know.
- Your ONLY job is to compare: (a) how well each answer addresses the question, and (b) how completely and faithfully each answer presents its scraped data.
- Treat both answers as sourced from a live web scrape done JUST NOW. Accept all data as-is.

---

## Benchmarking Request
**Question:** {question}

---

## ScrapeGraphAI Answer
{scrapegraph_answer}

**Metrics:**
- Faithfulness: {_fmt(sg_m.get('faithfulness_score'))} | Answer Relevance: {_fmt(sg_m.get('answer_relevance_score'))} | Completeness: {_fmt(sg_m.get('completeness_score'))}
- Word Count: {sg_m.get('word_count', 0)} | Scrape Latency: {sg_m.get('scrape_latency', 0)}s

---

## Firecrawl Answer
{firecrawl_answer}

**Metrics:**
- Faithfulness: {_fmt(fc_m.get('faithfulness_score'))} | Answer Relevance: {_fmt(fc_m.get('answer_relevance_score'))} | Completeness: {_fmt(fc_m.get('completeness_score'))}
- Word Count: {fc_m.get('word_count', 0)} | Scrape Latency: {fc_m.get('scrape_latency', 0)}s

---

## Your Evaluation Instructions

**1. Content Quality Analysis**
- Does the answer actually contain the requested data (models, prices, features, links, code snippets, etc.)?
- Are code snippets reproduced verbatim (GOOD) or invented/paraphrased (BAD)?
- Are there table rows or entries filled with "Not provided" / "N/A" / "-" for data not found (PENALIZE)?
- Does the answer add generic filler content not from the scraped page (PENALIZE)?
- Which answer gave MORE real, specific extracted data?

**2. Completeness**
- Which answer extracted MORE of what was asked?
- A longer answer with more real extracted items beats a shorter one.
- A short, grounded, precise answer beats a long answer padded with empty rows.

**3. Evaluation Summary Table**
| Criteria | ScrapeGraphAI | Firecrawl |
|---|---|---|
| Faithfulness | {_fmt(sg_m.get('faithfulness_score'))} | {_fmt(fc_m.get('faithfulness_score'))} |
| Answer Relevance | {_fmt(sg_m.get('answer_relevance_score'))} | {_fmt(fc_m.get('answer_relevance_score'))} |
| Completeness | {_fmt(sg_m.get('completeness_score'))} | {_fmt(fc_m.get('completeness_score'))} |
| Real Code Snippets | (assess from answer) | (assess from answer) |
| Empty/Invented Rows | (assess from answer) | (assess from answer) |
| Word Count | {sg_m.get('word_count', 0)} | {fc_m.get('word_count', 0)} |

**4. Winner Declaration**
Declare ONE winner: **ScrapeGraphAI**, **Firecrawl**, or **Tie**.
- Base your decision ONLY on which answer is more complete, grounded, and useful.
- DO NOT penalize based on your own world knowledge — only on what the answers contain vs. what was asked.
- DO NOT award winner based on metrics alone — read and compare the actual answer content.

Format your response in professional markdown with clear headings.
"""
    
    logger.debug("Streaming judge verdict")
    for chunk in language_model.stream(judge_prompt):
        yield chunk.content
