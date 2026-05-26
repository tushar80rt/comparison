"""
state.py - Streamlit session state management.
"""

import streamlit as st
from typing import Optional, Dict, Any

def init_session_state() -> None:
    """Initialize necessary Streamlit session state variables."""
    default_states: Dict[str, Any] = {
        "result": None,
        "run_id": None,
        "winner": None,
    }
    
    for key, default_value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def clear_current_run() -> None:
    """Clear the currently loaded run from session state."""
    st.session_state.result = None
    st.session_state.run_id = None
    st.session_state.winner = None
