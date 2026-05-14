"""Adaptive Optimization Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Optimization Analytics", page_icon="📈", layout="wide")
st.title("📈 Adaptive Optimization")
st.caption("Reasoning Depth Governance and Graph Truncation Analytics")

@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    db_path = Path("artifacts/metrics.duckdb")
    if db_path.exists():
        return duckdb.connect(str(db_path), read_only=True)
    return None

conn = get_db_connection()

if conn is None:
    st.info("💡 **Benchmark data not found.** Run `python scripts/run_benchmark.py` to see optimization metrics.")
    st.stop()

try:
    from metrics.normalizer import MetricNormalizer
    df_raw = conn.execute("SELECT * FROM metric_events").df()
    df_raw['canonical_name'] = df_raw['metric_name'].apply(MetricNormalizer.normalize_name)
    
    df_trunc = df_raw[df_raw['canonical_name'] == 'truncation_rate']
    df_saved = df_raw[df_raw['canonical_name'] == 'avg_depth_saved']
    df_util = df_raw[df_raw['canonical_name'] == 'reasoning_utilization_ratio']
    
    if df_trunc.empty:
        st.info("No optimization events recorded yet.")
        st.stop()

    total_truncations = df_trunc['value'].sum()
    total_depth_saved = df_saved['value'].sum() if not df_saved.empty else 0
    avg_utilization = df_util['value'].mean() if not df_util.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Graph Truncations", int(total_truncations))
    col2.metric("Steps Saved", int(total_depth_saved))
    col3.metric("Budget Utilization", f"{avg_utilization:.1%}")
    
    st.divider()
    
    col4, col5 = st.columns(2)
    with col4:
        fig_trunc = px.pie(
            names=["Truncated", "Normal"],
            values=[total_truncations, len(df_trunc) - total_truncations],
            title="Termination Outcomes",
            color_discrete_sequence=['#ef4444', '#34d399']
        )
        fig_trunc.update_layout(template="plotly_dark")
        st.plotly_chart(fig_trunc, use_container_width=True)
        
    with col5:
        if not df_util.empty:
            fig_util = px.histogram(
                df_util, x='value', nbins=20, 
                title="Reasoning Budget Utilization",
                color_discrete_sequence=['#4f46e5']
            )
            fig_util.update_layout(template="plotly_dark")
            st.plotly_chart(fig_util, use_container_width=True)

    st.markdown("""
    ### 🔬 Governance Logic
    ATTCO enforces dynamic compute ceilings based on predicted query complexity. 
    If the agent exceeds the **Allocated Reasoning Depth**, the graph is truncated 
    and a final answer is synthesized from the current state context.
    """)
                
except Exception as e:
    st.error(f"Optimization analytics offline: {str(e)}")
