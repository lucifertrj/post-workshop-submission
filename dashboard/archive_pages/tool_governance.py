"""Adaptive Tool Governance Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Tool Governance", page_icon="🛠️", layout="wide")
st.title("🛠️ Adaptive Tool Invocation Governance")

@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    db_path = Path("artifacts/metrics.duckdb")
    if db_path.exists():
        return duckdb.connect(str(db_path), read_only=True)
    return None

conn = get_db_connection()

if conn is None:
    st.warning("No metrics database found. Run a benchmark to generate data.")
    st.stop()

st.subheader("External Compute Optimization")

try:
    df_suppressed = conn.execute("SELECT * FROM metric_events WHERE metric_name = 'tools_suppressed_count'").df()
    df_latency = conn.execute("SELECT * FROM metric_events WHERE metric_name = 'tool_latency_saved_ms'").df()
    
    if not df_suppressed.empty:
        total_suppressed = df_suppressed['value'].sum()
        total_latency_saved = df_latency['value'].sum() / 1000.0 if not df_latency.empty else 0.0
        queries_with_suppression = len(df_suppressed[df_suppressed['value'] > 0])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tool Calls Suppressed", int(total_suppressed))
        col2.metric("Latency Saved (Seconds)", f"{total_latency_saved:.1f}s")
        col3.metric("Queries with Optimization", queries_with_suppression)
        
        st.markdown("---")
        
        col4, col5 = st.columns(2)
        with col4:
            fig_sup = px.histogram(
                df_suppressed, x='value', 
                title="Suppressed Tools per Query",
                labels={'value': 'Number of Suppressed Tools'}
            )
            st.plotly_chart(fig_sup, use_container_width=True)
            
        with col5:
            if not df_latency.empty:
                df_latency['seconds'] = df_latency['value'] / 1000.0
                fig_lat = px.box(
                    df_latency, y='seconds',
                    title="Latency Saved per Query",
                    labels={'seconds': 'Seconds Saved'}
                )
                st.plotly_chart(fig_lat, use_container_width=True)
                
except Exception as e:
    st.error(f"Could not load tool governance analytics: {e}")
