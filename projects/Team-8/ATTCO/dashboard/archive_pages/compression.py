"""Context Optimization & Trace Compression Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Context Optimization", page_icon="📉", layout="wide")
st.title("📉 Reasoning Trace Compression & Context Optimization")

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

st.subheader("Adaptive Memory Governance")

try:
    df_ratio = conn.execute("SELECT * FROM metric_events WHERE metric_name = 'avg_compression_ratio'").df()
    df_saved = conn.execute("SELECT * FROM metric_events WHERE metric_name = 'total_tokens_saved'").df()
    
    if not df_ratio.empty:
        avg_overall_ratio = df_ratio['value'].mean()
        total_tokens_saved = df_saved['value'].sum() if not df_saved.empty else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Compression Ratio", f"{avg_overall_ratio:.1%}")
        col2.metric("Total Context Tokens Saved", int(total_tokens_saved))
        col3.metric("Context Efficiency Gain", f"{((1 - avg_overall_ratio) * 100):.1f}%")
        
        st.markdown("---")
        
        col4, col5 = st.columns(2)
        with col4:
            fig_ratio = px.histogram(
                df_ratio, x='value', nbins=20, 
                title="Compression Ratio Distribution",
                labels={'value': 'Compression Ratio (0-1)'}
            )
            st.plotly_chart(fig_ratio, use_container_width=True)
            
        with col5:
            if not df_saved.empty:
                fig_saved = px.box(
                    df_saved, y='value', 
                    title="Token Savings per Query",
                    labels={'value': 'Tokens Saved'}
                )
                st.plotly_chart(fig_saved, use_container_width=True)

    st.subheader("Replay & Reconstruction Integrity")
    st.info("Full reasoning history is preserved in telemetry. Active context is optimized for prompt efficiency.")

except Exception as e:
    st.error(f"Could not load compression analytics: {e}")
