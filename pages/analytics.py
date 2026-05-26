import streamlit as st
import json
import pandas as pd

from src.core.database import get_all_runs, init_db
from src.ui.styles import APP_CSS

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Analytics — SEA",
    page_icon="📈",
    layout="wide",
)

init_db()

# =====================================================
# CUSTOM CSS
# =====================================================
st.markdown(APP_CSS, unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="hero-small">
    <h1>📈 Analytics Dashboard</h1>
    <p>Historical performance across all comparison runs.</p>
</div>
""", unsafe_allow_html=True)

# =====================================================
# LOAD DATA
# =====================================================

rows = get_all_runs()

if not rows:
    st.info("No runs found. Go back to the main page and run a comparison first.")
    st.markdown("[⬅️ Back to Arena](/)")
    st.stop()

# Parse rows
# columns: id, url, prompt, timestamp, model, winner, sg_metrics, fc_metrics
runs = []
for r in rows:
    sg_m = json.loads(r[6]) if r[6] else {}
    fc_m = json.loads(r[7]) if r[7] else {}
    runs.append({
        "id":        r[0],
        "url":       r[1],
        "prompt":    r[2][:60] + ("…" if len(r[2]) > 60 else ""),
        "timestamp": r[3],
        "model":     r[4] or "—",
        "winner":    r[5] or "—",
        "sg_scrape": sg_m.get("scrape_latency"),
        "fc_scrape": fc_m.get("scrape_latency"),
        "sg_rag":    sg_m.get("rag_latency"),
        "fc_rag":    fc_m.get("rag_latency"),
        "sg_total":  sg_m.get("total_latency"),
        "fc_total":  fc_m.get("total_latency"),
        "sg_words":  sg_m.get("word_count"),
        "fc_words":  fc_m.get("word_count"),
        "sg_faith":  sg_m.get("faithfulness_score"),
        "fc_faith":  fc_m.get("faithfulness_score"),
        "sg_rel":    sg_m.get("answer_relevance_score"),
        "fc_rel":    fc_m.get("answer_relevance_score"),
        "sg_ctx":    sg_m.get("context_relevance_score"),
        "fc_ctx":    fc_m.get("context_relevance_score"),
        "sg_comp":   sg_m.get("completeness_score"),
        "fc_comp":   fc_m.get("completeness_score"),
    })

total_runs = len(runs)
sg_wins    = sum(1 for r in runs if r["winner"] == "scrapegraph")
fc_wins    = sum(1 for r in runs if r["winner"] == "firecrawl")
unmarked   = total_runs - sg_wins - fc_wins

# latency averages (filter None)
def avg(lst):
    vals = [x for x in lst if x is not None]
    return round(sum(vals) / len(vals), 2) if vals else None

avg_sg_total = avg([r["sg_total"] for r in runs])
avg_fc_total = avg([r["fc_total"] for r in runs])

avg_sg_faith = avg([r["sg_faith"] for r in runs])
avg_fc_faith = avg([r["fc_faith"] for r in runs])

avg_sg_rel = avg([r["sg_rel"] for r in runs])
avg_fc_rel = avg([r["fc_rel"] for r in runs])

avg_sg_ctx = avg([r["sg_ctx"] for r in runs])
avg_fc_ctx = avg([r["fc_ctx"] for r in runs])

avg_sg_comp = avg([r["sg_comp"] for r in runs])
avg_fc_comp = avg([r["fc_comp"] for r in runs])

# =====================================================
# STAT CARDS
# =====================================================

c1, c2, c3, c4, c5 = st.columns(5)

def stat_card(col, label, value, sub=""):
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

stat_card(c1, "Total Runs", total_runs, "comparisons made")
stat_card(c2, "🕷 SG Wins",  sg_wins, f"{round(sg_wins/total_runs*100) if total_runs else 0}% win rate")
stat_card(c3, "🔥 FC Wins",  fc_wins, f"{round(fc_wins/total_runs*100) if total_runs else 0}% win rate")
stat_card(c4, "Avg SG Time", f"{avg_sg_total}s" if avg_sg_total else "—", "total pipeline")
stat_card(c5, "Avg FC Time", f"{avg_fc_total}s" if avg_fc_total else "—", "total pipeline")

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

st.markdown('<div class="section-label">Semantic Quality Averages</div>', unsafe_allow_html=True)
q_col1, q_col2, q_col3, q_col4 = st.columns(4)

def quality_card(col, metric_name, sg_val, fc_val):
    sg_pct = f"{round(sg_val * 100)}%" if sg_val is not None else "—"
    fc_pct = f"{round(fc_val * 100)}%" if fc_val is not None else "—"
    with col:
        st.markdown(f"""
        <div style="background-color: #262730; border-radius: 12px; padding: 1.5rem; text-align: center; border-left: 4px solid #00D4B1;">
            <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #AAAAAA; margin-bottom: 8px;">{metric_name}</div>
            <div style="display: flex; justify-content: space-around; align-items: center; margin-top: 10px;">
                <div>
                    <div style="font-size: 0.65rem; color: #34d399; font-weight: 600; margin-bottom: 2px;">ScrapeGraph</div>
                    <div style="font-size: 1.6rem; font-weight: 700; color: #34d399;">{sg_pct}</div>
                </div>
                <div style="width: 1px; height: 35px; background: #334155;"></div>
                <div>
                    <div style="font-size: 0.65rem; color: #f97316; font-weight: 600; margin-bottom: 2px;">Firecrawl</div>
                    <div style="font-size: 1.6rem; font-weight: 700; color: #f97316;">{fc_pct}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

quality_card(q_col1, "Faithfulness", avg_sg_faith, avg_fc_faith)
quality_card(q_col2, "Answer Relevance", avg_sg_rel, avg_fc_rel)
quality_card(q_col3, "Context Relevance", avg_sg_ctx, avg_fc_ctx)
quality_card(q_col4, "Completeness", avg_sg_comp, avg_fc_comp)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# =====================================================
# LATENCY CHART
# =====================================================

latency_runs = [r for r in runs if r["sg_total"] and r["fc_total"]]
if latency_runs:
    st.markdown('<div class="section-label">Total Latency Per Run (seconds)</div>', unsafe_allow_html=True)

    chart_data = {
        "Run":           [f"#{r['id']}" for r in latency_runs],
        "ScrapeGraphAI": [r["sg_total"] for r in latency_runs],
        "Firecrawl":     [r["fc_total"] for r in latency_runs],
    }
    df_chart = pd.DataFrame(chart_data).set_index("Run")
    st.bar_chart(df_chart, color=["#34d399", "#f97316"])

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# =====================================================
# WORD COUNT CHART
# =====================================================

word_runs = [r for r in runs if r["sg_words"] and r["fc_words"]]
if word_runs:
    st.markdown('<div class="section-label">Extracted Content Size — Word Count Per Run</div>', unsafe_allow_html=True)
    df_words = pd.DataFrame({
        "Run":           [f"#{r['id']}" for r in word_runs],
        "ScrapeGraphAI": [r["sg_words"] for r in word_runs],
        "Firecrawl":     [r["fc_words"] for r in word_runs],
    }).set_index("Run")
    st.bar_chart(df_words, color=["#818cf8", "#fb923c"])

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# =====================================================
# HISTORY TABLE
# =====================================================

st.markdown('<div class="section-label">All Runs</div>', unsafe_allow_html=True)

df_table = pd.DataFrame([
    {
        "ID":        r["id"],
        "Timestamp": r["timestamp"],
        "URL":       r["url"][:45] + ("…" if len(r["url"]) > 45 else ""),
        "Prompt":    r["prompt"],
        "Model":     r["model"].split("/")[-1] if "/" in r["model"] else r["model"],
        "Winner":    (
            "🕷 ScrapeGraphAI" if r["winner"] == "scrapegraph"
            else "🔥 Firecrawl" if r["winner"] == "firecrawl"
            else "—"
        ),
        "SG Quality": (
            f"{round((r['sg_faith'] + r['sg_rel'] + r['sg_ctx'] + (r['sg_comp'] or 0.0)) / 4 * 100)}%"
            if r["sg_faith"] is not None else "—"
        ),
        "FC Quality": (
            f"{round((r['fc_faith'] + r['fc_rel'] + r['fc_ctx'] + (r['fc_comp'] or 0.0)) / 4 * 100)}%"
            if r["fc_faith"] is not None else "—"
        ),
        "SG Total (s)": r["sg_total"] or "—",
        "FC Total (s)": r["fc_total"] or "—",
    }
    for r in runs
])

st.dataframe(
    df_table,
    use_container_width=True,
    hide_index=True,
)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("[⬅️ Back to Arena](/)")
