"""
styles.py - UI CSS strings for Streamlit.
"""

# The core styling shared across the application.
APP_CSS = """
<style>
.stApp { background-color: #0E1117; color: #FAFAFA; }
.main-header { font-size: 2.8rem; color: #00D4B1; text-align: center; font-weight: 800; margin-bottom: 0.2rem; letter-spacing: -0.5px; }
.sub-header { text-align: center; color: #888; margin-bottom: 2.5rem; font-size: 1.1rem; }
.stButton>button { width: 100%; background-color: #555555; color: #FAFAFA; border: none; padding: 0.8rem 1rem; border-radius: 8px; font-weight: 600; font-size: 1rem; margin-top: 1rem; }
.stButton>button:hover { background-color: #777777; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
.stTextInput>div>div>input { background-color: #262730; color: #FAFAFA; border: 1px solid #393946; border-radius: 8px; padding: 0.8rem; }
.stTextInput>div>div>input:focus { border-color: #00D4B1; box-shadow: 0 0 0 2px rgba(0, 212, 177, 0.2); }
.css-1d391kg, .css-1d391kg>div { background-color: #0E1117 !important; border-right: 1px solid #262730; }
.css-1d391kg h1,h2,h3,h4,h5,h6,p,label { color: #FAFAFA !important; }
.stProgress > div > div > div > div { background-color: #00D4B1; }
.streamlit-expanderHeader { background-color: #262730; color: #FAFAFA; border-radius: 8px; font-weight: 600; }
.streamlit-expanderContent { background-color: #1A1D25; border-radius: 0 0 8px 8px; }
.card { background-color: #262730; padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem; border-left: 4px solid #00D4B1; }
.stRadio > div { background-color: #262730; padding: 1rem; border-radius: 8px; }
label { font-weight: 600 !important; margin-bottom: 0.5rem; display: block; color: #CCC !important; }
.main-title { font-size: 40px; font-weight: bold; display: flex; align-items: center; }
.main-title img { height: 50px; margin-left: 20px; vertical-align: middle; }
.subtitle { font-size: 20px; color: #AAAAAA; }

/* Custom elements added via markdown */
.metric-card { background-color: #262730; border-radius: 12px; padding: 1.5rem; text-align: center; }
.metric-card .label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #AAAAAA; margin-bottom: 8px; }
.custom-divider { border: none; border-top: 1px solid #262730; margin: 24px 0; }
.section-label { font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.1px; color: #AAAAAA; margin-bottom: 8px; display: block; }
.result-card { background-color: #1A1D25; border-radius: 12px; padding: 1.5rem; font-size: 0.95rem; line-height: 1.6; border-left: 4px solid #475569; margin-bottom: 1rem; }
.judge-card { background-color: #1E293B; border-radius: 12px; padding: 1.5rem; border-left: 5px solid #a855f7; margin-bottom: 1rem; }
.judge-title { font-size: 1.4rem; font-weight: 700; color: #a855f7; margin-bottom: 0.5rem; }

/* Analytics specifics */
.hero-small { background-color: #262730; border-left: 4px solid #00D4B1; border-radius: 12px; padding: 24px 36px; margin-bottom: 24px; }
.hero-small h1 { font-size: 1.6rem; font-weight: 700; color: #FAFAFA; margin: 0 0 4px 0; }
.hero-small p  { font-size: 0.9rem; color: #AAAAAA; margin: 0; }
.stat-card { background-color: #262730; border-radius: 12px; padding: 20px; text-align: center; }
.stat-card .label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #AAAAAA; margin-bottom: 6px; }
.stat-card .value { font-size: 2rem; font-weight: 700; color: #00D4B1; }
.stat-card .sub   { font-size: 0.8rem; color: #888; margin-top: 4px; }
.stDataFrame { background: #262730 !important; border-radius: 10px !important; }
</style>
"""
