"""
metrics.py - Evaluation logic using DeepEval and Groq.
"""

from typing import Dict, Any
from deepeval.test_case import LLMTestCase
from deepeval.metrics import HallucinationMetric, AnswerRelevancyMetric
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_groq import ChatGroq

from src.logger import get_logger
logger = get_logger(__name__)

class GroqDeepEvalModel(DeepEvalBaseLLM):
    """DeepEval wrapper for LangChain's ChatGroq."""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        
    def load_model(self):
        return self.llm
        
    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
        
    async def a_generate(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content
        
    def get_model_name(self):
        return self.llm.model_name


def evaluate_answer_quality(question: str, context: str, answer: str, language_model: ChatGroq) -> Dict[str, Any]:
    """Evaluate response using DeepEval metrics using Groq."""
    
    # Check if we have valid inputs to prevent DeepEval from throwing errors on empty text
    if not answer or not context:
        logger.warning("Empty answer or context provided to evaluate_answer_quality. Skipping evaluation.")
        return {
            "faithfulness": {"score": 0.0, "reasoning": "No answer or context to evaluate."},
            "answer_relevance": {"score": 0.0, "reasoning": "No answer to evaluate."},
            "context_relevance": {"score": 0.0, "reasoning": "No context to evaluate."},
        }
        
    groq_llm = GroqDeepEvalModel(language_model)
    test_case = LLMTestCase(input=question, actual_output=answer, context=[context])
    
    halluc_metric = HallucinationMetric(model=groq_llm)
    try:
        halluc_metric.measure(test_case)
        # In DeepEval, hallucination score 0 means no hallucination (so faithfulness is 1 - halluc_score)
        faithfulness_score = max(0.0, 1.0 - getattr(halluc_metric, "score", 1.0))
        faithfulness_reason = getattr(halluc_metric, "reason", "No reasoning provided.")
    except Exception as e:
        logger.error(f"Hallucination metric failed: {e}")
        faithfulness_score = 0.0
        faithfulness_reason = f"Evaluation failed: {str(e)}"
        
    answer_rel_metric = AnswerRelevancyMetric(model=groq_llm)
    try:
        answer_rel_metric.measure(test_case)
        answer_rel_score = getattr(answer_rel_metric, "score", 0.0)
        answer_rel_reason = getattr(answer_rel_metric, "reason", "No reasoning provided.")
    except Exception as e:
        logger.error(f"Answer relevancy metric failed: {e}")
        answer_rel_score = 0.0
        answer_rel_reason = f"Evaluation failed: {str(e)}"
        
    return {
        "faithfulness": {
            "score": float(faithfulness_score), 
            "reasoning": faithfulness_reason
        },
        "answer_relevance": {
            "score": float(answer_rel_score), 
            "reasoning": answer_rel_reason
        },
        # We don't have a reliable ContextRelevancyMetric without ground truth in DeepEval easily,
        # so for this arena, we fallback or just omit it, but we can return it as 0.0 or a heuristic.
        "context_relevance": {
            "score": 0.0, 
            "reasoning": "Not measured in DeepEval without expected output."
        },
    }


def compute_completeness_score(m: dict) -> float:
    """Derive a completeness score from word count, field count, and JSON depth.
    
    Weights:
    - 70% word count  (capped at 1000 words = 1.0) — rewards rich text/markdown equally
    - 15% field count (capped at 10 fields = 1.0)
    - 15% JSON depth  (capped at 5 levels = 1.0)
    """
    word_score  = min(m.get("word_count",  0) / 1000, 1.0)  # 1000 words = full score
    field_score = min(m.get("field_count", 0) / 10,   1.0)  # 10 fields  = full score
    depth_score = min(m.get("json_depth",  0) / 5,    1.0)  # depth 5    = full score
    return round(0.70 * word_score + 0.15 * field_score + 0.15 * depth_score, 4)

