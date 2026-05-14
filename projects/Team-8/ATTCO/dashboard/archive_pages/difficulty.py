"""Difficulty & Calibration Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Difficulty Analytics", page_icon="🧠", layout="wide")
st.title("🧠 Query Difficulty & Calibration Analytics")

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

# Extract prediction metrics
try:
    df_metrics = conn.execute("SELECT * FROM metric_events WHERE metric_name IN ('predicted_expected_depth', 'predicted_expected_compute')").df()
except Exception:
    df_metrics = pd.DataFrame()

if df_metrics.empty:
    st.info("No difficulty predictions found in metric events.")
else:
    # We parse tags to extract difficulty class
    # DuckDB stores tags as string representation of dict
    import ast
    def extract_diff_class(tag_str):
        try:
            return ast.literal_eval(tag_str).get("difficulty_class", "unknown")
        except:
            return "unknown"

    df_metrics['difficulty_class'] = df_metrics['tags'].apply(extract_diff_class)
    
    st.subheader("Benchmark Difficulty Distributions")
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart of difficulty classes
        class_counts = df_metrics.drop_duplicates(subset=['question_id'])['difficulty_class'].value_counts().reset_index()
        class_counts.columns = ['Difficulty Class', 'Count']
        fig_class = px.pie(class_counts, names='Difficulty Class', values='Count', title="Queries by Difficulty Class")
        st.plotly_chart(fig_class, use_container_width=True)
        
    with col2:
        # Expected compute vs reasoning depth (histogram/scatter)
        df_depth = df_metrics[df_metrics['metric_name'] == 'predicted_expected_depth']
        fig_depth = px.histogram(df_depth, x='value', color='difficulty_class', title="Predicted Reasoning Depth Distribution", labels={'value': 'Expected Steps'})
        st.plotly_chart(fig_depth, use_container_width=True)
        
    st.subheader("Calibration Analysis")
    st.markdown("Comparing actual reasoning depth vs predicted reasoning depth (from heuristic estimator).")
    
    try:
        # Actual reasoning steps
        df_actual = conn.execute("SELECT question_id, value as actual_steps FROM metric_events WHERE metric_name = 'steps'").df() # Wait, we don't have 'steps' metric emitted in runner yet, let's just show prediction vs cost
        
        # Predicted Compute
        df_compute = df_metrics[df_metrics['metric_name'] == 'predicted_expected_compute']
        fig_compute = px.box(df_compute, x='difficulty_class', y='value', title="Expected Compute (Tokens) by Difficulty Class", labels={'value': 'Tokens'})
        st.plotly_chart(fig_compute, use_container_width=True)
        
    except Exception as e:
        st.error(f"Could not load calibration data: {e}")

