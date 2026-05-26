"""
components.py - Reusable Streamlit UI components.
"""

import json
from datetime import datetime
from typing import Dict, Any

import streamlit as st

from src.core.database import set_winner
from src.config import LLM_MODEL

def render_metrics(sg_m: Dict[str, Any], fc_m: Dict[str, Any]) -> None:
    rows = [
        ("Scrape Latency",  f"{sg_m.get('scrape_latency', '—')}s", f"{fc_m.get('scrape_latency', '—')}s"),
        ("RAG Latency",     f"{sg_m.get('rag_latency', '—')}s",    f"{fc_m.get('rag_latency', '—')}s"),
        ("Total Latency",   f"{sg_m.get('total_latency', '—')}s",  f"{fc_m.get('total_latency', '—')}s"),
        ("Word Count",      sg_m.get("word_count", "—"),            fc_m.get("word_count", "—")),
        ("Field Count",     sg_m.get("field_count", "—"),           fc_m.get("field_count", "—")),
        ("JSON Depth",      sg_m.get("json_depth", "—"),            fc_m.get("json_depth", "—")),
    ]
    cols = st.columns(3)
    for i, (label, sg_val, fc_val) in enumerate(rows):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{label}</div>
                <div style="display:flex;justify-content:space-around;margin-top:6px;">
                    <div>
                        <div style="font-size:.68rem;color:#34d399;font-weight:600;margin-bottom:2px;">ScrapeGraph</div>
                        <div class="value" style="font-size:1.2rem;">{sg_val}</div>
                    </div>
                    <div style="width:1px;background:#334155;"></div>
                    <div>
                        <div style="font-size:.68rem;color:#f97316;font-weight:600;margin-bottom:2px;">Firecrawl</div>
                        <div class="value" style="font-size:1.2rem;">{fc_val}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        if i == 2:
            st.markdown("<br>", unsafe_allow_html=True)
            cols = st.columns(3)


def render_quality_evaluation(sg_m: Dict[str, Any], fc_m: Dict[str, Any]) -> None:
    if "faithfulness_score" not in sg_m and "faithfulness_score" not in fc_m:
        st.info("ℹ️ RAG Quality Evaluation is not available for this legacy run.")
        return

    sg_faith = sg_m.get("faithfulness_score", 0.0)
    sg_rel   = sg_m.get("answer_relevance_score", 0.0)
    sg_ctx   = sg_m.get("context_relevance_score", 0.0)
    sg_comp  = sg_m.get("completeness_score", 0.0)
    sg_overall = round((sg_faith + sg_rel + sg_ctx + sg_comp) / 4 * 100)

    fc_faith = fc_m.get("faithfulness_score", 0.0)
    fc_rel   = fc_m.get("answer_relevance_score", 0.0)
    fc_ctx   = fc_m.get("context_relevance_score", 0.0)
    fc_comp  = fc_m.get("completeness_score", 0.0)
    fc_overall = round((fc_faith + fc_rel + fc_ctx + fc_comp) / 4 * 100)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(f"""
        <div style="background-color:#1E293B; border-radius:12px; padding:1.5rem; border-left:5px solid #34d399; margin-bottom: 1rem;">
            <h4 style="margin-top:0;color:#34d399;">🕷 ScrapeGraphAI Quality</h4>
            <div style="font-size:2rem; font-weight:700; color:#34d399; margin-bottom:0.2rem;">{sg_overall}%</div>
            <div style="font-size:0.8rem;color:#94a3b8;">Overall RAG Quality Score</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"**Faithfulness (Groundedness)**: {round(sg_faith * 100)}%")
        st.progress(sg_faith)
        st.markdown(f"**Answer Relevance**: {round(sg_rel * 100)}%")
        st.progress(sg_rel)
        st.markdown(f"**Context Relevance**: {round(sg_ctx * 100)}%")
        st.progress(sg_ctx)
        st.markdown(f"**Completeness (Data Richness)**: {round(sg_comp * 100)}%")
        st.progress(sg_comp)

    with col2:
        st.markdown(f"""
        <div style="background-color:#1E293B; border-radius:12px; padding:1.5rem; border-left:5px solid #f97316; margin-bottom: 1rem;">
            <h4 style="margin-top:0;color:#f97316;">🔥 Firecrawl Quality</h4>
            <div style="font-size:2rem; font-weight:700; color:#f97316; margin-bottom:0.2rem;">{fc_overall}%</div>
            <div style="font-size:0.8rem;color:#94a3b8;">Overall RAG Quality Score</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"**Faithfulness (Groundedness)**: {round(fc_faith * 100)}%")
        st.progress(fc_faith)
        st.markdown(f"**Answer Relevance**: {round(fc_rel * 100)}%")
        st.progress(fc_rel)
        st.markdown(f"**Context Relevance**: {round(fc_ctx * 100)}%")
        st.progress(fc_ctx)
        st.markdown(f"**Completeness (Data Richness)**: {round(fc_comp * 100)}%")
        st.progress(fc_comp)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔍 Show Detailed Quality Critique"):
        c_sg, c_fc = st.columns(2, gap="large")
        with c_sg:
            st.markdown("### 🕷 ScrapeGraphAI Critique")
            st.markdown(f"**Faithfulness (Groundedness)**:\n{sg_m.get('faithfulness_reason', 'No reasoning available.')}")
            st.markdown(f"**Answer Relevance**:\n{sg_m.get('answer_relevance_reason', 'No reasoning available.')}")
            st.markdown(f"**Context Relevance**:\n{sg_m.get('context_relevance_reason', 'No reasoning available.')}")
            st.markdown(f"**Completeness (Data Richness)**:\n{sg_m.get('completeness_reason', 'No reasoning available.')}")
        with c_fc:
            st.markdown("### 🔥 Firecrawl Critique")
            st.markdown(f"**Faithfulness (Groundedness)**:\n{fc_m.get('faithfulness_reason', 'No reasoning available.')}")
            st.markdown(f"**Answer Relevance**:\n{fc_m.get('answer_relevance_reason', 'No reasoning available.')}")
            st.markdown(f"**Context Relevance**:\n{fc_m.get('context_relevance_reason', 'No reasoning available.')}")
            st.markdown(f"**Completeness (Data Richness)**:\n{fc_m.get('completeness_reason', 'No reasoning available.')}")


def _render_expander_data(data: Any) -> None:
    if isinstance(data, str):
        try:
            # Try parsing as JSON in case it's a JSON-string
            parsed = json.loads(data)
            st.json(parsed)
        except Exception:
            # Render raw markdown/text in a code block
            st.code(data, language="markdown")
    elif isinstance(data, (dict, list)):
        st.json(data)
    else:
        st.write(data)


def render_data_expanders(sg_data: Any, fc_data: Any) -> None:
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.expander("📦 ScrapeGraphAI — Extracted Data", expanded=False):
            _render_expander_data(sg_data)
    with col2:
        with st.expander("📦 Firecrawl — Extracted Data", expanded=False):
            _render_expander_data(fc_data)


def render_export(result: Dict[str, Any], run_id: int) -> None:
    st.markdown('<div class="section-label">Export Results</div>', unsafe_allow_html=True)

    timestamp = result.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))
    sg_m      = result.get("sg_metrics", {})
    fc_m      = result.get("fc_metrics", {})

    md_report = f"""# ⚡ Semantic Extraction Arena — Report

**Date**: {timestamp}  
**URL**: {result.get("url", "—")}  
**Prompt**: {result.get("question", "—")}  
**Model**: {LLM_MODEL}

---

## 📊 Metrics

| Metric | ScrapeGraphAI | Firecrawl |
|--------|:---:|:---:|
| Faithfulness   | {f'{round(sg_m["faithfulness_score"] * 100)}%' if "faithfulness_score" in sg_m else "—"} | {f'{round(fc_m["faithfulness_score"] * 100)}%' if "faithfulness_score" in fc_m else "—"} |
| Answer Relevance | {f'{round(sg_m["answer_relevance_score"] * 100)}%' if "answer_relevance_score" in sg_m else "—"} | {f'{round(fc_m["answer_relevance_score"] * 100)}%' if "answer_relevance_score" in fc_m else "—"} |
| Context Relevance | {f'{round(sg_m["context_relevance_score"] * 100)}%' if "context_relevance_score" in sg_m else "—"} | {f'{round(fc_m["context_relevance_score"] * 100)}%' if "context_relevance_score" in fc_m else "—"} |
| Completeness Score | {f'{round(sg_m["completeness_score"] * 100)}%' if "completeness_score" in sg_m else "—"} | {f'{round(fc_m["completeness_score"] * 100)}%' if "completeness_score" in fc_m else "—"} |
| Scrape Latency | {sg_m.get("scrape_latency", "—")}s | {fc_m.get("scrape_latency", "—")}s |
| RAG Latency    | {sg_m.get("rag_latency", "—")}s    | {fc_m.get("rag_latency", "—")}s |
| Total Latency  | {sg_m.get("total_latency", "—")}s  | {fc_m.get("total_latency", "—")}s |
| Word Count     | {sg_m.get("word_count", "—")}      | {fc_m.get("word_count", "—")} |

---

## 🕷 ScrapeGraphAI — RAG Answer

{result.get("sg_answer", "")}

---

## 🔥 Firecrawl — RAG Answer

{result.get("fc_answer", "")}

---

## ⚖️ AI Judge Verdict

{result.get("judge_result", "")}
"""
    col_j, col_m, _ = st.columns([1, 1, 3])
    with col_j:
        st.download_button(
            "⬇ JSON",
            data=json.dumps(
                {k: v for k, v in result.items()},
                indent=2, default=str,
            ),
            file_name="sea_result.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_m:
        st.download_button(
            "⬇ Markdown",
            data=md_report,
            file_name="sea_report.md",
            mime="text/markdown",
            use_container_width=True,
        )


def render_winner_picker(run_id: int) -> None:
    st.markdown('<div class="section-label">Mark Winner</div>', unsafe_allow_html=True)
    current = st.session_state.get("winner")

    if current:
        label = "🕷 ScrapeGraphAI" if current == "scrapegraph" else "🔥 Firecrawl"
        st.success(f"Winner marked: **{label}**")
        if st.button("Clear", key="clear_winner"):
            set_winner(run_id, None)
            st.session_state.winner = None
            st.rerun()
    else:
        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            if st.button("✅ ScrapeGraphAI", key="win_sg", use_container_width=True):
                set_winner(run_id, "scrapegraph")
                st.session_state.winner = "scrapegraph"
                st.rerun()
        with c2:
            if st.button("✅ Firecrawl", key="win_fc", use_container_width=True):
                set_winner(run_id, "firecrawl")
                st.session_state.winner = "firecrawl"
                st.rerun()


def render_full_result(result: Dict[str, Any], run_id: int) -> None:
    st.markdown('<div class="section-label">RAG Quality Evaluation</div>', unsafe_allow_html=True)
    render_quality_evaluation(result["sg_metrics"], result["fc_metrics"])
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Performance & Size Metrics</div>', unsafe_allow_html=True)
    render_metrics(result["sg_metrics"], result["fc_metrics"])
    st.markdown("<br>", unsafe_allow_html=True)

    render_data_expanders(result["sg_data"], result["fc_data"])
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown('<div class="section-label">🕷 ScrapeGraphAI — RAG Answer</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="result-card">{result["sg_answer"]}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="section-label">🔥 Firecrawl — RAG Answer</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="result-card">{result["fc_answer"]}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown("""
    <div class="judge-card">
        <div class="judge-title">⚖️ AI Judge Verdict</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(result["judge_result"])

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    if run_id:
        render_winner_picker(run_id)
    st.markdown("<br>", unsafe_allow_html=True)
    render_export(result, run_id)
