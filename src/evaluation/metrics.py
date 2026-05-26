"""
metrics.py - Evaluation logic using DeepEval and Groq.
"""

import json
import re
from typing import Dict, Any, Optional
from deepeval.test_case import LLMTestCase
from deepeval.metrics import HallucinationMetric, AnswerRelevancyMetric
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_groq import ChatGroq

from src.logger import get_logger
logger = get_logger(__name__)

# Sentinel value stored in metrics dicts to flag an eval crash
_EVAL_FAILED = "__eval_failed__"

class GroqDeepEvalModel(DeepEvalBaseLLM):
    """DeepEval wrapper for LangChain's ChatGroq."""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        
    def load_model(self):
        return self.llm
        
    def _clean_json_output(self, text: str) -> str:
        """Extract and validate JSON from LLM output to prevent DeepEval crashes."""
        text = text.strip()
        
        # 1. Try extracting from markdown code block
        match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
        extracted = match.group(1) if match else text
        
        # 2. If no code block, try finding the outermost braces
        if not match:
            start_idx = extracted.find('{')
            end_idx = extracted.rfind('}')
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                extracted = extracted[start_idx:end_idx + 1]
                
        # 3. Validate JSON
        try:
            json.loads(extracted)
            return extracted
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON output. Error: {e}. Raw text: {text}")
            # Return extracted anyway; DeepEval will likely fail, but we've logged exactly why
            return extracted

    def generate(self, prompt: str) -> str:
        # Append instruction to enforce strict JSON
        strict_prompt = prompt + "\n\nCRITICAL INSTRUCTION: Output strictly valid JSON. Do not include markdown formatting like ```json or any conversational text before or after the JSON."
        response = self.llm.invoke(strict_prompt)
        cleaned = self._clean_json_output(response.content)
        logger.debug(f"DeepEval LLM Output (Cleaned): {cleaned}")
        return cleaned
        
    async def a_generate(self, prompt: str) -> str:
        strict_prompt = prompt + "\n\nCRITICAL INSTRUCTION: Output strictly valid JSON. Do not include markdown formatting like ```json or any conversational text before or after the JSON."
        response = await self.llm.ainvoke(strict_prompt)
        cleaned = self._clean_json_output(response.content)
        logger.debug(f"DeepEval Async LLM Output (Cleaned): {cleaned}")
        return cleaned
        
    def get_model_name(self):
        return self.llm.model_name


def evaluate_answer_quality(question: str, context: str, answer: str, language_model: ChatGroq) -> Dict[str, Any]:
    """Evaluate response using DeepEval metrics via Groq.

    On metric failure (e.g. LLM returns invalid JSON), the score is set to
    ``None`` and ``eval_failed=True`` is included so callers can surface a
    warning instead of a misleading 0%.
    """

    # Guard: skip evaluation when inputs are empty
    if not answer or not context:
        logger.warning("Empty answer or context — skipping evaluation.")
        return {
            "faithfulness":     {"score": 0.0, "reasoning": "No answer or context to evaluate.", "eval_failed": False},
            "answer_relevance": {"score": 0.0, "reasoning": "No answer to evaluate.",            "eval_failed": False},
            "context_relevance":{"score": 0.0, "reasoning": "No context to evaluate.",           "eval_failed": False},
        }

    groq_llm  = GroqDeepEvalModel(language_model)
    test_case = LLMTestCase(input=question, actual_output=answer, context=[context])

    # ── Faithfulness (HallucinationMetric) ──────────────────────────────────
    halluc_metric = HallucinationMetric(model=groq_llm)
    faithfulness_failed = False
    try:
        halluc_metric.measure(test_case)
        # DeepEval: hallucination_score=0 → no hallucination → faithfulness=1
        faithfulness_score  = max(0.0, 1.0 - getattr(halluc_metric, "score", 1.0))
        faithfulness_reason = getattr(halluc_metric, "reason", "No reasoning provided.")
    except Exception as e:
        logger.error(f"Hallucination metric failed: {e}")
        faithfulness_score  = None
        faithfulness_reason = f"Evaluation failed: {e}"
        faithfulness_failed = True

    # ── Answer Relevancy ────────────────────────────────────────────────────
    answer_rel_metric  = AnswerRelevancyMetric(model=groq_llm)
    answer_rel_failed  = False
    try:
        answer_rel_metric.measure(test_case)
        answer_rel_score  = getattr(answer_rel_metric, "score", 0.0)
        answer_rel_reason = getattr(answer_rel_metric, "reason", "No reasoning provided.")
    except Exception as e:
        logger.error(f"Answer relevancy metric failed: {e}")
        answer_rel_score  = None
        answer_rel_reason = f"Evaluation failed: {e}"
        answer_rel_failed = True

    return {
        "faithfulness": {
            "score":      None if faithfulness_failed else float(faithfulness_score),
            "reasoning":  faithfulness_reason,
            "eval_failed": faithfulness_failed,
        },
        "answer_relevance": {
            "score":      None if answer_rel_failed else float(answer_rel_score),
            "reasoning":  answer_rel_reason,
            "eval_failed": answer_rel_failed,
        },
        # Context relevance requires ground-truth; not available in this arena
        "context_relevance": {
            "score":      0.0,
            "reasoning":  "Not measured in DeepEval without expected output.",
            "eval_failed": False,
        },
    }


def compute_completeness_score(m: dict) -> float:
    """Derive a completeness score from word count, field count, and JSON depth.

    Scoring adapts to the data type:

    Plain-text / Markdown  (field_count=0, json_depth=0)
        → 100% weight on word count  (cap: 1 000 words)

    Structured JSON / dict / list  (field_count > 0 or json_depth > 0)
        → 70% word count  (cap: 1 000 words)
        → 15% field count (cap: 10 fields)
        → 15% JSON depth  (cap: 5 levels)

    This prevents plain-markdown scrapes from being penalised with
    zero structure scores and producing artificially low results.
    """
    word_count  = m.get("word_count",  0)
    field_count = m.get("field_count", 0)
    json_depth  = m.get("json_depth",  0)

    word_score  = min(word_count  / 1000, 1.0)
    field_score = min(field_count / 10,   1.0)
    depth_score = min(json_depth  / 5,    1.0)

    is_plain_text = (field_count == 0 and json_depth == 0)

    if is_plain_text:
        # Pure text/markdown — word richness is the only signal
        return round(word_score, 4)
    else:
        # Structured data — blend all three signals
        return round(0.70 * word_score + 0.15 * field_score + 0.15 * depth_score, 4)

