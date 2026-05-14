"""Verification & Correctness Governance Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Correctness Governance", page_icon="🛡️", layout="wide")
st.title("🛡️ Correctness Governance")
st.caption("Verification Cycles and Self-Validation Metrics")

@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    db_path = Path("artifacts/metrics.duckdb")
    if db_path.exists():
        return duckdb.connect(str(db_path), read_only=True)
    return None

conn = get_db_connection()

if conn is None:
    st.info("💡 **Benchmark data not found.** Run `python scripts/run_benchmark.py` to see verification results.")
    st.stop()

try:
    df_triggers = conn.execute("SELECT * FROM metric_events WHERE metric_name = 'verification_trigger_count'").df()
    df_failures = conn.execute("SELECT * FROM metric_events WHERE metric_name = 'verification_failure_count'").df()
    
    if df_triggers.empty:
        st.info("No verification events recorded yet.")
        st.stop()

    total_triggers = df_triggers['value'].sum()
    total_failures = df_failures['value'].sum() if not df_failures.empty else 0
    total_runs = len(df_triggers)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Verification Triggers", int(total_triggers))
    col2.metric("Failures Detected", int(total_failures))
    col3.metric("Trigger Rate", f"{(total_triggers / total_runs):.1%}")
    
    st.divider()
    
    col4, col5 = st.columns(2)
    with col4:
        fig_outcomes = px.pie(
            names=["Valid (Pass)", "Invalid (Fail)"],
            values=[total_triggers - total_failures, total_failures],
            title="Self-Validation Outcomes",
            color_discrete_sequence=['#34d399', '#f87171']
        )
        fig_outcomes.update_layout(template="plotly_dark")
        st.plotly_chart(fig_outcomes, use_container_width=True)
        
    with col5:
        # Distribution of triggers per query
        fig_dist = px.histogram(
            df_triggers, x='value', 
            title="Verification Density",
            color_discrete_sequence=['#6366f1']
        )
        fig_dist.update_layout(template="plotly_dark")
        st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("""
    ### 🔬 Correctness Governance
    The **Verification Layer** triggers high-fidelity self-validation when predicted 
    uncertainty exceeds the **Risk Threshold**. 
    
    If an answer fails validation, the arbitrator injects a **Critique Step** 
    into the trace, forcing the agent to re-evaluate its reasoning before proceeding.
    """)

except Exception as e:
    st.error(f"Verification analytics offline: {str(e)}")
