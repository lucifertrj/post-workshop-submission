"""Scientific Evaluation & Research Analytics Page."""
import streamlit as st
import duckdb
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from research.stats_evaluator import StatsEvaluator

st.set_page_config(page_title="Scientific Evaluation", page_icon="🔬", layout="wide")
st.title("🔬 Scientific Evaluation & Research")
st.caption("Benchmark Analytics, Ablation Studies, and Pareto Efficiency Analysis")

@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    db_path = Path("artifacts/metrics.duckdb")
    if db_path.exists():
        return duckdb.connect(str(db_path), read_only=True)
    return None

conn = get_db_connection()

if conn is None:
    st.info("📊 **Benchmarking Data Unavailable**")
    st.markdown("""
    To generate scientific evaluation artifacts, please execute:
    ```bash
    python scripts/run_benchmark.py
    ```
    This will run the full ablation suite and populate the research telemetry.
    """)
    st.stop()

try:
    from metrics.normalizer import MetricNormalizer
    
    # Check if runtime_profile exists
    cols = [r[1] for r in conn.execute("PRAGMA table_info('metric_events')").fetchall()]
    profile_col = "runtime_profile" if "runtime_profile" in cols else "'unknown'"
    
    # Query aggregated metrics using Canonical Normalization
    df_metrics = conn.execute(f"""
        SELECT 
            experiment_id,
            {profile_col} as runtime_profile,
            {MetricNormalizer.get_sql_aggregation()}
        FROM metric_events
        GROUP BY experiment_id, {profile_col}
    """).df().dropna(subset=['avg_accuracy', 'avg_tokens'])
    
    if df_metrics.empty:
         st.warning("Experiment database found, but no completed records detected.")
         st.stop()

    # Sidebar Filter
    st.sidebar.subheader("Research Filter")
    all_profiles = df_metrics['runtime_profile'].unique().tolist()
    selected_profiles = st.sidebar.multiselect("Runtime Profiles", all_profiles, default=all_profiles)
    
    df_filtered = df_metrics[df_metrics['runtime_profile'].isin(selected_profiles)]

    # --- TOP SECTION: PARETO FRONTIER ---
    st.subheader("1. Adaptive Efficiency Pareto Frontier")
    
    # Points for Pareto
    points = df_filtered.to_dict('records')
    pareto_points = StatsEvaluator.identify_pareto_frontier(
        points, x_metric='avg_tokens', y_metric='avg_accuracy'
    )
    df_pareto = pd.DataFrame(pareto_points)
    
    fig = go.Figure()
    # All points
    for profile in df_filtered['runtime_profile'].unique():
        df_p = df_filtered[df_filtered['runtime_profile'] == profile]
        fig.add_trace(go.Scatter(
            x=df_p['avg_tokens'], y=df_p['avg_accuracy'],
            mode='markers', name=f'Profile: {profile}',
            text=df_p['experiment_id'],
            marker=dict(size=10, line=dict(width=1, color='white'))
        ))
    # Pareto line
    fig.add_trace(go.Scatter(
        x=df_pareto['avg_tokens'], y=df_pareto['avg_accuracy'],
        mode='lines+markers', name='Efficiency Frontier',
        line=dict(color='#10b981', width=3, dash='dash'),
        marker=dict(size=12, color='#10b981', symbol='diamond')
    ))
    
    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Computational Cost (Avg Tokens)",
        yaxis_title="Task Accuracy (Proxy)",
        legend=dict(yanchor="bottom", y=0.01, xanchor="right", x=0.99),
        margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- MID SECTION: ABLATION TABLE ---
    st.divider()
    st.subheader("2. Ablation Performance Matrix")
    
    # Format the table for research presentation
    df_display = df_filtered.copy()
    df_display['avg_accuracy'] = df_display['avg_accuracy'].map('{:.2%}'.format)
    df_display['avg_tokens'] = df_display['avg_tokens'].map('{:.0f}'.format)
    df_display['avg_latency_ms'] = (df_display['avg_latency_ms']/1000).map('{:.2f}s'.format)
    
    st.dataframe(df_display.style.set_properties(**{'background-color': 'rgba(30, 41, 59, 0.3)', 'color': 'white', 'border-color': 'rgba(148, 163, 184, 0.1)'}), use_container_width=True)

    # --- BOTTOM SECTION: OPTIMIZER CONTRIBUTION ---
    st.divider()
    st.subheader("3. Optimizer Contribution Profile")
    
    # Calculate relative savings vs 'baseline' if baseline exists
    baseline_row = df_metrics[df_metrics['experiment_id'].str.contains('baseline', case=False)]
    if not baseline_row.empty:
        b_tokens = baseline_row.iloc[0]['avg_tokens']
        b_acc = baseline_row.iloc[0]['avg_accuracy']
        
        df_contrib = df_metrics[~df_metrics['experiment_id'].str.contains('baseline', case=False)].copy()
        df_contrib['Token Savings (%)'] = (b_tokens - df_contrib['avg_tokens']) / b_tokens * 100
        df_contrib['Accuracy Delta'] = df_contrib['avg_accuracy'] - b_acc
        
        fig_contrib = px.bar(df_contrib, x='experiment_id', y='Token Savings (%)', color='Accuracy Delta',
                             title="Efficiency Gain vs. Correctness Tradeoff",
                             color_continuous_scale='RdYlGn',
                             color_continuous_midpoint=0)
        fig_contrib.update_layout(template="plotly_dark")
        st.plotly_chart(fig_contrib, use_container_width=True)
    else:
        st.info("💡 **Tip**: Name one of your experiments 'baseline' to unlock relative gain analytics.")

except Exception as e:
    st.error(f"Scientific evaluation suite encounterd a telemetry schema mismatch: {str(e)}")
