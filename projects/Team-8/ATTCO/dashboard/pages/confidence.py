"""Confidence Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Confidence Analytics", page_icon="🎯", layout="wide")
st.title("🎯 Confidence & Early Stopping")
st.caption("Adaptive Termination Governance — Efficiency vs. Correctness Tradeoffs")

@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    db_path = Path("artifacts/metrics.duckdb")
    if db_path.exists():
        return duckdb.connect(str(db_path), read_only=True)
    return None

conn = get_db_connection()

if conn is None:
    st.info("💡 **Benchmark data not found.** Run `python scripts/run_benchmark.py` to populate confidence analytics.")
    st.stop()

try:
    from metrics.normalizer import MetricNormalizer
    df_raw = conn.execute("SELECT * FROM metric_events").df()
    df_raw['canonical_name'] = df_raw['metric_name'].apply(MetricNormalizer.normalize_name)

    df_early = df_raw[df_raw['canonical_name'] == 'early_stop_rate']
    df_trunc = df_raw[df_raw['canonical_name'] == 'truncation_rate']
    df_conf = df_raw[df_raw['canonical_name'] == 'avg_stop_confidence']
    
    if df_early.empty:
        st.info("No early-stopping events recorded yet.")
        st.stop()

    total_early_stops = df_early['value'].sum()
    total_truncations = df_trunc['value'].sum() if not df_trunc.empty else 0
    total_runs = len(df_early)
    normal_stops = total_runs - total_early_stops - total_truncations
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Early Stops", int(total_early_stops))
    col2.metric("Forced Stops", int(total_truncations))
    col3.metric("Standard Stops", int(normal_stops))
    
    st.divider()
    
    col4, col5 = st.columns(2)
    with col4:
        fig_outcomes = px.pie(
            names=["Early (Confidence)", "Forced (Ceiling)", "Standard"],
            values=[total_early_stops, total_truncations, normal_stops],
            title="Termination Dynamics",
            color_discrete_sequence=['#10b981', '#ef4444', '#60a5fa']
        )
        fig_outcomes.update_layout(template="plotly_dark")
        st.plotly_chart(fig_outcomes, use_container_width=True)
        
    with col5:
        if not df_conf.empty:
            fig_conf = px.histogram(
                df_conf, x='value', nbins=20, 
                title="Stop Confidence Distribution",
                color_discrete_sequence=['#f59e0b']
            )
            fig_conf.update_layout(template="plotly_dark")
            st.plotly_chart(fig_conf, use_container_width=True)
            
    st.markdown("""
    ### 🔬 Early Stopping Mechanism
    ATTCO monitors the **Incremental Confidence Score** at each reasoning step. 
    If the probability of the current best-guess answer exceeds the **Adaptive Stop Threshold**, 
    inference terminates immediately to preserve tokens.
    """)
                
except Exception as e:
    st.error(f"Confidence analytics offline: {str(e)}")
