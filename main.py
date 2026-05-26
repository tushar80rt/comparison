import os
import sentence_transformers
from langchain_huggingface import HuggingFaceEmbeddings
import re
import time
from datetime import datetime
import streamlit as st

# Setup UI & Styles
from src.ui.styles import APP_CSS
from src.ui.state import init_session_state, clear_current_run
from src.ui.components import (
    render_metrics,
    render_quality_evaluation,
    render_data_expanders,
    render_export,
    render_winner_picker,
    render_full_result
)

# Core imports
from src.config import LLM_MODEL
from src.core.database import init_db, save_run, get_history, get_run_by_id, delete_run
from src.utils.helpers import get_image_base64, calculate_metrics

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
from src.rag.qa_chain import get_llm, stream_rag_answer
from src.evaluation.metrics import evaluate_answer_quality, compute_completeness_score
from src.evaluation.judge import stream_judge_verdict

st.set_page_config(
    page_title="Semantic Extraction Arena",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
init_session_state()

fire_logo_base64 = get_image_base64("assets/fire.svg")

st.markdown(APP_CSS, unsafe_allow_html=True)

st.markdown(
    f"""
<div class="header">
  <div class="main-title">
   product comparison  With
    <img src="https://miro.medium.com/v2/resize:fit:720/format:webp/0*QR3Jl4jUu326U2p2.png" alt="ScrapeGraphAI Logo">
    <span style="margin-left:40px;">&</span>
    <img src="{fire_logo_base64}" alt="Firecrawl Logo">
  </div>
  <div class="subtitle"></div>
  <br>
</div>
""",
    unsafe_allow_html=True,
)


with st.sidebar:
    st.image("./assets/Groq.svg", width=150)
    
    groq_key = st.text_input(
        "Enter your Groq API key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
    )
    smartscrape_key = st.text_input(
        "Smartscrape Key", value=os.getenv("SCRAPEGRAPH_API_KEY", ""), type="password"
    )
    Firecrawl_key = st.text_input(
        "Firecrawl_key", value=os.getenv("FIRECRAWL_API_KEY", ""), type="password"
    )

    if st.button("💾 Save Keys", use_container_width=True):
        st.session_state["GROQ_API_KEY"] = groq_key
        st.session_state["SCRAPEGRAPH_API_KEY"] = smartscrape_key
        st.session_state["FIRECRAWL_API_KEY"] = Firecrawl_key
        
        os.environ["GROQ_API_KEY"] = groq_key
        os.environ["SCRAPEGRAPH_API_KEY"] = smartscrape_key
        os.environ["FIRECRAWL_API_KEY"]=Firecrawl_key
        
        # Force agent re-initialization with new credentials
        if 'agent' in st.session_state:
            del st.session_state['agent']
            
        st.success("Credentials updated! Re-initializing agent...")
        st.rerun()
        
    if groq_key or smartscrape_key or Firecrawl_key:
        st.caption("Credentials loaded for active session.")

    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    comparison_mode = st.selectbox(
        "Comparison Mode",
        options=["Targeted Extraction", "Raw Scrape", "Site Crawl", "Web Search"],
        index=0,
    )
    st.markdown("---")
    
    st.markdown("### 🗂 Run History")

    history = get_history(25)

    if not history:
        st.caption("No runs yet. Run a comparison to build history.")
    else:
        run_labels = [
            f"#{r[0]}  ·  {r[3]}  ·  {r[1][:25]}…"
            for r in history
        ]
        selected_idx = st.selectbox(
            "Select run",
            range(len(run_labels)),
            format_func=lambda i: run_labels[i],
            label_visibility="collapsed",
        )

        col_load, col_del = st.columns(2)
        with col_load:
            if st.button("📂 Load", use_container_width=True):
                loaded = get_run_by_id(history[selected_idx][0])
                if loaded:
                    st.session_state.result = {
                        "url":          loaded["url"],
                        "question":     loaded["prompt"],
                        "sg_data":      loaded["sg_data"],
                        "fc_data":      loaded["fc_data"],
                        "sg_answer":    loaded["sg_answer"],
                        "fc_answer":    loaded["fc_answer"],
                        "judge_result": loaded["judge_result"],
                        "sg_metrics":   loaded["sg_metrics"],
                        "fc_metrics":   loaded["fc_metrics"],
                        "timestamp":    loaded["timestamp"],
                    }
                    st.session_state.run_id = loaded["id"]
                    st.session_state.winner = loaded["winner"]
                    st.rerun()
        with col_del:
            if st.button("🗑 Delete", use_container_width=True):
                delete_run(history[selected_idx][0])
                if st.session_state.run_id == history[selected_idx][0]:
                    clear_current_run()
                st.rerun()

    st.markdown("---")
    st.markdown("[📊 Analytics Dashboard](/analytics)")


def execute_comparison_pipeline(url: str, question: str, mode: str):
    """Executes the scraping and vectorization pipeline."""
    llm = get_llm()
    schema = None

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

    sg_metrics = calculate_metrics(scrapegraph_data)
    sg_metrics["scrape_latency"] = scrapegraph_latency

    fc_metrics = calculate_metrics(firecrawl_data)
    fc_metrics["scrape_latency"] = firecrawl_latency

    return {
        "llm": llm,
        "sg_data": scrapegraph_data,
        "fc_data": firecrawl_data,
        "sg_vectordb": create_vectorstore(scrapegraph_data, "scrapegraph_collection"),
        "fc_vectordb": create_vectorstore(firecrawl_data, "firecrawl_collection"),
        "sg_metrics": sg_metrics,
        "fc_metrics": fc_metrics,
    }


chat_text = st.chat_input("Enter URL and prompt (e.g., 'https://example.com extract pricing plans...')")

if chat_text:
    url_match = re.search(r'(https?://[^\s]+)', chat_text)
    
    if comparison_mode == "Web Search":
        url = ""
        question = chat_text.strip()
    else:
        if not url_match:
            st.warning(f"⚠️  Please include a valid URL (starting with http:// or https://) in your prompt for the '{comparison_mode}' mode.")
            st.stop()
            
        url = url_match.group(1)
        question = chat_text.replace(url, "").strip()
        if not question:
            question = "Extract all useful information."

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    
    if url:
        st.markdown(
            f"""
            <div style="background-color: #1A1D25; padding: 1rem; border-radius: 8px; border-left: 4px solid #00D4B1; margin-bottom: 1.5rem;">
                <div><span style="color: #AAAAAA; font-weight: 600; font-size: 0.8rem; text-transform: uppercase;">Target URL</span><br/><span style="color: #FAFAFA;">{url}</span></div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style="background-color: #1A1D25; padding: 1rem; border-radius: 8px; border-left: 4px solid #00D4B1; margin-bottom: 1.5rem;">
                <div><span style="color: #AAAAAA; font-weight: 600; font-size: 0.8rem; text-transform: uppercase;">Search Query</span><br/><span style="color: #FAFAFA;">{question}</span></div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with st.chat_message("user"):
        st.write(question)

    with st.spinner(f"🔍 Running {comparison_mode} & building knowledge base…"):
        stage = execute_comparison_pipeline(url, question, mode=comparison_mode)

    sg_m = stage["sg_metrics"]
    fc_m = stage["fc_metrics"]

    st.markdown('<div class="section-label">RAG Answers — Live</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")

    t0 = time.perf_counter()
    with col1:
        st.markdown("**🕷 ScrapeGraphAI**")
        sg_answer = st.write_stream(
            stream_rag_answer(stage["sg_vectordb"], question, stage["llm"])
        )
    sg_m["rag_latency"]   = round(time.perf_counter() - t0, 2)
    sg_m["total_latency"] = round(sg_m["scrape_latency"] + sg_m["rag_latency"], 2)

    t0 = time.perf_counter()
    with col2:
        st.markdown("**🔥 Firecrawl**")
        fc_answer = st.write_stream(
            stream_rag_answer(stage["fc_vectordb"], question, stage["llm"])
        )
    fc_m["rag_latency"]   = round(time.perf_counter() - t0, 2)
    fc_m["total_latency"] = round(fc_m["scrape_latency"] + fc_m["rag_latency"], 2)

    # Evaluate RAG quality
    with st.spinner("⚖️ Evaluating response quality using DeepEval criteria..."):
        sg_docs = stage["sg_vectordb"].as_retriever().invoke(question)
        sg_context = "\n\n".join([d.page_content for d in sg_docs])
        
        fc_docs = stage["fc_vectordb"].as_retriever().invoke(question)
        fc_context = "\n\n".join([d.page_content for d in fc_docs])
        
        sg_eval = evaluate_answer_quality(question, sg_context, sg_answer, stage["llm"])
        fc_eval = evaluate_answer_quality(question, fc_context, fc_answer, stage["llm"])

        for metric in ["faithfulness", "answer_relevance", "context_relevance"]:
            result_block = sg_eval.get(metric, {})
            sg_m[f"{metric}_score"]      = result_block.get("score", 0.0)       # None on failure
            sg_m[f"{metric}_reason"]     = result_block.get("reasoning", "")
            sg_m[f"{metric}_eval_failed"] = result_block.get("eval_failed", False)

            result_block = fc_eval.get(metric, {})
            fc_m[f"{metric}_score"]      = result_block.get("score", 0.0)       # None on failure
            fc_m[f"{metric}_reason"]     = result_block.get("reasoning", "")
            fc_m[f"{metric}_eval_failed"] = result_block.get("eval_failed", False)

        sg_m["completeness_score"] = compute_completeness_score(sg_m)
        fc_m["completeness_score"] = compute_completeness_score(fc_m)

        _sg_mode = "plain-text" if sg_m.get("field_count", 0) == 0 and sg_m.get("json_depth", 0) == 0 else "structured"
        _fc_mode = "plain-text" if fc_m.get("field_count", 0) == 0 and fc_m.get("json_depth", 0) == 0 else "structured"
        sg_m["completeness_reason"] = (
            f"Scored in {_sg_mode} mode — word count ({sg_m.get('word_count', 0)}), "
            f"field count ({sg_m.get('field_count', 0)}), JSON depth ({sg_m.get('json_depth', 0)})."
        )
        fc_m["completeness_reason"] = (
            f"Scored in {_fc_mode} mode — word count ({fc_m.get('word_count', 0)}), "
            f"field count ({fc_m.get('field_count', 0)}), JSON depth ({fc_m.get('json_depth', 0)})."
        )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown("""
    <div class="judge-card">
        <div class="judge-title">⚖️ AI Judge Verdict — Live</div>
    </div>
    """, unsafe_allow_html=True)
    
    judge_result = st.write_stream(
        stream_judge_verdict(question, sg_answer, fc_answer, sg_m, fc_m, stage["llm"])
    )

    result = {
        "url":          url,
        "question":     question,
        "sg_data":      stage["sg_data"],
        "fc_data":      stage["fc_data"],
        "sg_answer":    sg_answer,
        "fc_answer":    fc_answer,
        "judge_result": judge_result,
        "sg_metrics":   sg_m,
        "fc_metrics":   fc_m,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    st.session_state.result = result
    st.session_state.winner = None

    run_id = save_run(
        url=url, prompt=question, model=LLM_MODEL,
        sg_answer=sg_answer, fc_answer=fc_answer,
        judge_result=judge_result,
        sg_metrics=sg_m, fc_metrics=fc_m,
        sg_data=stage["sg_data"], fc_data=stage["fc_data"],
    )
    st.session_state.run_id = run_id

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    render_full_result(result, run_id)

elif st.session_state.result:
    result = st.session_state.result
    run_id = st.session_state.run_id

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="background-color: #1A1D25; padding: 1rem; border-radius: 8px; border-left: 4px solid #00D4B1; margin-bottom: 1.5rem;">
            <div><span style="color: #AAAAAA; font-weight: 600; font-size: 0.8rem; text-transform: uppercase;">Target URL</span><br/><span style="color: #FAFAFA;">{result.get("url", "—")}</span></div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    with st.chat_message("user"):
        st.write(result.get("question", "—"))
    
    info_cols = st.columns(2)
    with info_cols[0]:
        st.markdown(
            f'<div class="section-label">Model</div>'
            f'<div style="color:#cbd5e1;font-size:.9rem;">{LLM_MODEL}</div>',
            unsafe_allow_html=True,
        )
    with info_cols[1]:
        st.markdown(
            f'<div class="section-label">Timestamp</div>'
            f'<div style="color:#cbd5e1;font-size:.9rem;">{result.get("timestamp", "—")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    render_full_result(result, run_id)