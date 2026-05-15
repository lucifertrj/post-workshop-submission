"""Self-Calibration & Policy Learning Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Self-Calibration", page_icon="📈", layout="wide")
st.title("📈 Policy Learning & Self-Calibration")

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

st.subheader("Dynamic Threshold Evolution")

try:
    # Fetch calibrated thresholds over time
    metrics = ["calibrated_stop_threshold", "calibrated_verification_threshold", "calibrated_utility_threshold", "calibrated_context_threshold"]
    
    combined_df = pd.DataFrame()
    for metric in metrics:
        df = conn.execute(f"SELECT timestamp, value as {metric} FROM metric_events WHERE metric_name = '{metric}' ORDER BY timestamp").df()
        if not df.empty:
            if combined_df.empty:
                combined_df = df
            else:
                combined_df = pd.merge_asof(combined_df, df, on="timestamp", direction="nearest")
    
    if not combined_df.empty:
        fig_evol = px.line(
            combined_df, x='timestamp', y=metrics,
            title="Threshold Calibration Trajectories",
            labels={'value': 'Threshold Value', 'variable': 'Parameter'}
        )
        st.plotly_chart(fig_evol, use_container_width=True)
        
        st.markdown("---")
        
        st.subheader("Calibration Stability & Convergence")
        # Visualize the delta of changes
        diff_df = combined_df.set_index('timestamp').diff().dropna().reset_index()
        if not diff_df.empty:
            fig_drift = px.bar(
                diff_df, x='timestamp', y=metrics,
                title="Policy Adjustment Volatility (Drift)",
                labels={'value': 'Adjustment Delta'}
            )
            st.plotly_chart(fig_drift, use_container_width=True)

    st.subheader("Self-Optimization Efficiency")
    st.info("The system automatically tunes thresholds based on the accuracy-cost frontier observed in previous benchmark batches.")

except Exception as e:
    st.error(f"Could not load calibration analytics: {e}")
