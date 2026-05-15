"""Compute Budget Allocation Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px
import ast

st.set_page_config(page_title="Budget Allocation", page_icon="⚖️", layout="wide")
st.title("⚖️ Compute Budget Allocation Analytics")

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
    df_alloc = conn.execute("SELECT * FROM metric_events WHERE metric_name LIKE 'allocated_%'").df()
except Exception:
    df_alloc = pd.DataFrame()

if df_alloc.empty:
    st.info("No budget allocation data found in metric events.")
else:
    def extract_budget_class(tag_str):
        try:
            return ast.literal_eval(tag_str).get("budget_class", "unknown")
        except:
            return "unknown"

    df_alloc['budget_class'] = df_alloc['tags'].apply(extract_budget_class)
    
    st.subheader("Compute Budget Allocations")
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart of budget classes
        class_counts = df_alloc.drop_duplicates(subset=['question_id'])['budget_class'].value_counts().reset_index()
        class_counts.columns = ['Budget Class', 'Count']
        fig_class = px.pie(class_counts, names='Budget Class', values='Count', title="Queries by Budget Class")
        st.plotly_chart(fig_class, use_container_width=True)
        
    with col2:
        # Token Budget distribution
        df_tokens = df_alloc[df_alloc['metric_name'] == 'allocated_token_budget']
        fig_tokens = px.histogram(df_tokens, x='value', color='budget_class', title="Allocated Token Budgets", labels={'value': 'Tokens'})
        st.plotly_chart(fig_tokens, use_container_width=True)

    st.subheader("Allocation Ceilings")
    col3, col4 = st.columns(2)
    
    with col3:
        df_max_depth = df_alloc[df_alloc['metric_name'] == 'allocated_max_depth']
        fig_max_depth = px.box(df_max_depth, x='budget_class', y='value', title="Hard Reasoning Ceilings (Max Depth)", labels={'value': 'Max Steps'})
        st.plotly_chart(fig_max_depth, use_container_width=True)
        
    with col4:
        df_soft_budget = df_alloc[df_alloc['metric_name'] == 'allocated_soft_budget']
        fig_soft_budget = px.box(df_soft_budget, x='budget_class', y='value', title="Soft Reasoning Budgets (Expected Depth)", labels={'value': 'Expected Steps'})
        st.plotly_chart(fig_soft_budget, use_container_width=True)
        
    st.subheader("Budget Calibration Analytics")
    st.markdown("This section compares actual utilized compute against the allocated limits to evaluate utilization efficiency.")
    
    # Extract total tokens used
    try:
        df_actual_tokens = conn.execute("SELECT question_id, value as actual_tokens FROM metric_events WHERE metric_name = 'total_tokens'").df()
        if not df_actual_tokens.empty:
            df_merged = pd.merge(df_tokens, df_actual_tokens, on='question_id', how='inner')
            if not df_merged.empty:
                fig_util = px.scatter(df_merged, x='actual_tokens', y='value', color='budget_class', 
                                      title="Actual vs Allocated Tokens", 
                                      labels={'actual_tokens': 'Actual Usage', 'value': 'Allocated Budget'})
                
                # Add parity line
                max_val = max(df_merged['actual_tokens'].max(), df_merged['value'].max())
                fig_util.add_shape(type='line', x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color='white', dash='dash'))
                st.plotly_chart(fig_util, use_container_width=True)
            else:
                st.info("Insufficient data for calibration.")
    except Exception as e:
        st.warning(f"Could not load calibration data: {e}")
