"""Arbitration & Orchestration Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px
import ast

st.set_page_config(page_title="Arbitration Analytics", page_icon="⚖️", layout="wide")
st.title("⚖️ Optimization Arbitration & Orchestration")

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

st.subheader("Global Execution Governance")

try:
    # Fetch arbitration decisions from trace_events (stored in payload)
    # Note: In a production system we'd have a separate table for this, 
    # but for the prototype we parse it from the telemetry.
    df_events = conn.execute("SELECT payload FROM trace_events WHERE event_class = 'ARBITRATION_DECISION'").df()
    
    if not df_events.empty:
        decisions = [ast.literal_eval(p) for p in df_events['payload']]
        df_dec = pd.DataFrame(decisions)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Arbitration Events", len(df_dec))
        col2.metric("Winning Optimizers", df_dec['winning_optimizer'].nunique())
        col3.metric("Avg Arbitration Latency", f"{df_dec['arbitration_latency_ms'].mean():.2f}ms")
        
        st.markdown("---")
        
        col4, col5 = st.columns(2)
        with col4:
            # Distribution of final actions
            fig_actions = px.pie(df_dec, names='final_action', title="Unified Governance Actions")
            st.plotly_chart(fig_actions, use_container_width=True)
            
        with col5:
            # Win rates per optimizer
            fig_wins = px.bar(
                df_dec['winning_optimizer'].value_counts().reset_index(),
                x='index', y='winning_optimizer',
                title="Optimizer Governance Win-Rates",
                labels={'index': 'Optimizer', 'winning_optimizer': 'Wins'}
            )
            st.plotly_chart(fig_wins, use_container_width=True)

        st.subheader("Optimizer Conflict Heatmap")
        # We look at overridden proposals
        overridden_data = []
        for i, row in df_dec.iterrows():
            for p in row['overridden_proposals']:
                overridden_data.append({
                    "winner": row['winning_optimizer'],
                    "overridden": p['optimizer_name'],
                    "winner_action": row['final_action'],
                    "overridden_action": p['action']
                })
        
        if overridden_data:
            df_over = pd.DataFrame(overridden_data)
            fig_conflicts = px.density_heatmap(
                df_over, x='winner', y='overridden',
                title="Cross-Optimizer Policy Conflict Heatmap",
                labels={'winner': 'Winning Optimizer', 'overridden': 'Overridden Optimizer'}
            )
            st.plotly_chart(fig_conflicts, use_container_width=True)
        else:
            st.info("No policy conflicts detected yet.")

except Exception as e:
    st.error(f"Could not load arbitration analytics: {e}")
