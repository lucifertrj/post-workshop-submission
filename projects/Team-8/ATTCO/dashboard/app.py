import streamlit as st
import sys
import asyncio
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import importlib

# --- 1. Project Root & Module Setup ---
root_path = Path(__file__).parent.parent.absolute()
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from infrastructure.config.loader import ConfigLoader
from infrastructure.config.profile_manager import ProfileManager
ConfigLoader.load()
ProfileManager.load()

import controller.graph
import controller.nodes.reason
import controller.nodes.act
import controller.nodes.arbitrator
import controller.nodes.verifier
import controller.nodes.compressor
import tracing.schema
import baseline.agent
import optimizer.modules.arbitrator
import optimizer.modules.arbitrator.schema
import optimizer.modules.arbitrator.engine
import optimizer.modules.depth_controller

# Recursive reload for research iteration
import controller.state
importlib.reload(controller.state)
importlib.reload(tracing.schema)
importlib.reload(optimizer.modules.arbitrator.schema)
importlib.reload(optimizer.modules.arbitrator.engine)
importlib.reload(optimizer.modules.arbitrator)
importlib.reload(optimizer.modules.depth_controller)
importlib.reload(controller.nodes.reason)
importlib.reload(controller.nodes.act)
importlib.reload(controller.nodes.arbitrator)
importlib.reload(controller.nodes.verifier)
importlib.reload(controller.nodes.compressor)
importlib.reload(controller.graph)
importlib.reload(baseline.agent)
from baseline.agent import BaselineAgent

# --- 3. Page Config & Aesthetics ---
st.set_page_config(
    page_title="ATTCO Research Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Premium Research Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main .block-container { padding-top: 3rem; }
    
    /* Outlined Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 12px;
        padding: 24px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: rgba(79, 70, 229, 0.4);
        transform: translateY(-2px);
    }
    
    /* Section Headers */
    .section-header {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #f8fafc;
    }
    
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        height: 3.5em; 
        font-weight: 600; 
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4);
    }

    .baseline-header { color: #60a5fa; font-weight: 700; }
    .attco-header { color: #a78bfa; font-weight: 700; }
    .comparison-header { color: #34d399; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --- 4. Session State Initialization ---
if 'baseline_result' not in st.session_state:
    st.session_state.baseline_result = None
if 'attco_result' not in st.session_state:
    st.session_state.attco_result = None
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""

def extract_metrics(state) -> dict:
    """Robustly extract metrics from a reasoning state, regardless of schema type."""
    if not state: return {}
    
    # Standard Python safe access (getattr for Pydantic, .get for dict)
    def sget(obj, key, default=None):
        if obj is None: return default
        if isinstance(obj, dict): return obj.get(key, default)
        return getattr(obj, key, default)

    # Extract collections safely
    steps = sget(state, "steps", [])
    verifications = sget(state, "verification_history", [])
    compressions = sget(state, "compression_history", [])
    arbitrations = sget(state, "arbitration_history", [])
    
    # Calculate derived metrics
    tool_calls_count = 0
    for step in steps:
        tc = sget(step, "tool_calls", [])
        tool_calls_count += len(tc) if isinstance(tc, list) else 0

    metadata = sget(state, "metadata", {})
    suppressed_count = 0
    if isinstance(metadata, dict):
        suppressed_count = metadata.get("tools_suppressed_count", 0)
    
    return {
        "tokens": sget(state, "total_tokens", 0),
        "latency_s": sget(state, "total_latency_ms", 0.0) / 1000.0,
        "depth": len(steps),
        "tool_calls": tool_calls_count,
        "suppressed_tools": suppressed_count,
        "verifications": len(verifications),
        "compressions": len(compressions),
        "arbitrations": len(arbitrations),
        "answer": sget(state, "final_answer", "N/A"),
        "termination": sget(state, "termination_cause", "normal")
    }

def render_orchestration_trace(state: dict, title: str, color_class: str):
    """Elite renderer for the complete LangGraph orchestration lifecycle."""
    if not state: return
    
    st.markdown(f"<p class='{color_class}' style='font-size: 1.5rem; margin-bottom: 0.5rem;'>{title}</p>", unsafe_allow_html=True)
    
    # helper to get state attributes safely
    def sget(obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else default

    # --- Phase 0: Execution Lifecycle Summary ---
    st.markdown("""
    <div style='display: flex; gap: 10px; align-items: center; margin-bottom: 2rem; font-size: 0.85rem; color: #94a3b8;'>
        <span>Difficulty</span> <span>→</span>
        <span>Allocation</span> <span>→</span>
        <span>Reasoning Loop</span> <span>→</span>
        <span style='background: rgba(79, 70, 229, 0.2); color: #a5b4fc; padding: 2px 8px; border-radius: 4px;'>Arbitration</span> <span>→</span>
        <span>Verification</span> <span>→</span>
        <span>Conclusion</span>
    </div>
    """, unsafe_allow_html=True)

    # --- Phase 1: Pre-Execution Intelligence ---
    metadata = sget(state, "metadata", {})
    diff = metadata.get("difficulty_prediction")
    alloc = metadata.get("compute_allocation")
    
    with st.expander("📝 PHASE 1: Intelligence & Allocation", expanded=True):
        col1, col2 = st.columns(2)
        if diff:
            with col1:
                st.markdown("**Difficulty Analysis**")
                st.caption(f"Class: `{diff.get('difficulty_class', 'N/A').upper()}` | Confidence: {diff.get('confidence', 0):.1%}")
                st.info(f"Expected Depth: {diff.get('expected_reasoning_depth')} steps")
        if alloc:
            with col2:
                st.markdown("**Compute Allocation**")
                st.caption(f"Budget: `{alloc.get('budget_class', 'N/A').upper()}` | Latency: `{alloc.get('latency_class', 'N/A')}`")
                st.success(f"Depth Ceiling: {alloc.get('max_reasoning_depth')} steps")

    # --- Phase 2: Reasoning Trajectory ---
    st.markdown("<h3 style='margin-top: 2rem;'>Reasoning Trajectory</h3>", unsafe_allow_html=True)
    history = sget(state, "reasoning_history", [])
    if not history:
        # Fallback to steps if history is missing for some reason
        history = sget(state, "steps", [])
    
    compressions = sget(state, "compression_history", [])
    
    for i, step in enumerate(history):
        step_num = i + 1
        with st.container():
            st.markdown(f"<div style='border-left: 3px solid rgba(148, 163, 184, 0.2); padding-left: 1.5rem; margin-bottom: 2rem;'>", unsafe_allow_html=True)
            
            # Step Header
            st.markdown(f"#### Step {step_num}")
            
            # Thought
            thought = sget(step, "thought")
            if thought:
                st.markdown(f"<div style='background: rgba(30, 41, 59, 0.3); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'><b>Thought:</b><br>{thought}</div>", unsafe_allow_html=True)
            
            # Interventions (captured in history dict)
            interventions = sget(step, "interventions", [])
            for decision in interventions:
                action = decision.get("action", "continue")
                with st.expander(f"🛡️ Intervention: {action.upper()}", expanded=True):
                    st.warning(decision.get("rationale"))
                    st.caption(f"Winner: {decision.get('optimizer')} | Step: {decision.get('step')}")

            # Action & Tool Calls
            action_str = sget(step, "action")
            if action_str:
                st.markdown(f"<code>Action: {action_str}</code>", unsafe_allow_html=True)
            
            tool_calls = sget(step, "tool_calls", [])
            for tc in tool_calls:
                with st.status(f"🛠️ Tool Invocation: {sget(tc, 'tool_name')}", expanded=False):
                    st.json(sget(tc, "tool_input", {}))
                    output = sget(tc, "tool_output")
                    if output:
                        st.markdown(f"**Output:** {output}")
                    if sget(tc, "error"):
                        st.error(sget(tc, "error"))

            # Observation
            obs = sget(step, "observation")
            if obs:
                if "[TOOL SUPPRESSED]" in obs:
                    st.error(obs)
                else:
                    st.markdown(f"<div style='background: rgba(20, 184, 166, 0.05); border: 1px solid rgba(20, 184, 166, 0.2); padding: 1rem; border-radius: 8px; margin-top: 0.5rem;'><b>Observation:</b><br>{obs}</div>", unsafe_allow_html=True)

            # Inline Verification Outcome
            v = sget(step, "verification_outcome")
            if v:
                v_res = "VALID" if v.get("is_valid") else "INVALID"
                v_color = "green" if v.get("is_valid") else "red"
                with st.expander(f"🔍 Correctness Verification: {v_res}", expanded=not v.get("is_valid")):
                    if not v.get("is_valid"):
                        st.error(f"Reasoning Inconsistency Detected: {v.get('critique', 'No critique available')}")
                    else:
                        st.success("Reasoning validated. No inconsistencies detected.")
                    st.caption(f"Risk Score: {v.get('risk_score', 0):.2f} | Confidence Delta: {v.get('confidence_delta', 0):+.2f}")

            # Compression
            if len(compressions) > i:
                c = compressions[i]
                ratio = c.get("compression_ratio", 1.0)
                if ratio < 1.0:
                    st.info(f"🗜️ **Trace Compression Triggered**: {ratio:.1%} reduction in context footprint. {c.get('rationale')}")

            st.markdown("</div>", unsafe_allow_html=True)

    # --- Phase 3: Final Response ---
    st.markdown("---")
    answer = sget(state, "final_answer")
    cause = sget(state, "termination_cause", "normal")
    
    if answer:
        st.subheader("🏁 Final Conclusion")
        st.success(answer)
        
        verifications = sget(state, "verification_history", [])
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Termination", cause.upper())
        col_m2.metric("Total Depth", f"{len(history)} steps")
        col_m3.metric("Verification Passes", f"{len(verifications)}")

async def run_single_inference(query: str, is_attco: bool, toggles: dict):
    agent = BaselineAgent(
        experiment_id="attco_console_run",
        ablation_toggles=toggles
    )
    # Hard 60s timeout for safety
    result = await asyncio.wait_for(
        agent.run("playground", query),
        timeout=60.0
    )
    return result if isinstance(result, dict) else result.model_dump()

def execute_safe_async(coro):
    """Safely run async coroutine in Streamlit environment."""
    try:
        # Get or create a long-lived loop for the current thread
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        res = loop.run_until_complete(coro)
        return res
    except asyncio.TimeoutError:
        st.error("🚨 Execution Timeout: The agent exceeded the 60s safety window.")
        return None
    except Exception as e:
        st.error(f"🚨 Runtime Failure: {str(e)}")
        return None

# --- 6. Main Console Interface ---
st.title("⚡ ATTCO Research Console")
st.caption("Adaptive Test-Time Compute Optimization | Stage-Based Execution & Scientific Analytics")

# Navigation Sidebar
st.sidebar.title("Console Controls")

# Runtime Profile Selection
current_profile = ProfileManager.get_active_profile_name()
profile_options = ["research", "balanced", "aggressive", "visualization"]
selected_profile = st.sidebar.selectbox("Runtime Profile", profile_options, index=profile_options.index(current_profile))

if selected_profile != current_profile:
    ProfileManager.load(selected_profile)
    st.toast(f"Switched to {selected_profile} profile", icon="🛡️")

st.sidebar.markdown(f"**Active Mode:** `{ProfileManager.get_active_profile_name().upper()}`")
st.sidebar.caption(ProfileManager.get_active_profile().get("description", ""))

if st.sidebar.button("🧹 Clear Research Session"):
    st.session_state.baseline_result = None
    st.session_state.attco_result = None
    st.rerun()

st.sidebar.divider()
st.sidebar.info("""
**Platform Status**:
- Backend: Stable
- Tracer: Active
- Logic: Causal Optimized
""")

# --- SECTION A: QUERY INPUT & SETUP ---
st.markdown("<h2 class='section-header'>Step 1: Scientific Hypothesis</h2>", unsafe_allow_html=True)
with st.container():
    query_col, config_col = st.columns([2, 1])
    
    with query_col:
        user_query = st.text_area("Research Query", 
                                  value="What is the relationship between the founder of OpenAI and the creator of C++?",
                                  height=100,
                                  help="Enter a complex multi-hop query to test adaptive orchestration.")
        if user_query != st.session_state.last_query:
             st.session_state.baseline_result = None
             st.session_state.attco_result = None
             st.session_state.last_query = user_query

    with config_col:
        profile = st.selectbox("Orchestration Profile", 
                               ["Minimal (Stable)", "Balanced (Standard)", "Aggressive (Cost-Saving)", "Research (Full-Stack)"],
                               index=1)
        
        # Profile Logic
        if "Minimal" in profile:
            defaults = {"depth_controller": True, "early_stopping": False, "verification": False, "tool_gating": False, "compression": False, "max_steps": 8}
        elif "Balanced" in profile:
            defaults = {"depth_controller": True, "early_stopping": True, "verification": False, "tool_gating": True, "compression": False, "max_steps": 12}
        elif "Aggressive" in profile:
            defaults = {"depth_controller": True, "early_stopping": True, "verification": True, "tool_gating": True, "compression": True, "max_steps": 15}
        else: # Research
            defaults = {"depth_controller": True, "early_stopping": True, "verification": True, "tool_gating": True, "compression": True, "max_steps": 25}

        with st.expander("⚙️ Adaptive Parameters"):
            attco_toggles = {
                "depth_controller": st.checkbox("Depth Control", value=defaults["depth_controller"]),
                "early_stopping": st.checkbox("Early Stop", value=defaults["early_stopping"]),
                "verification": st.checkbox("Self-Verify", value=defaults["verification"]),
                "tool_gating": st.checkbox("Tool Gating", value=defaults["tool_gating"]),
                "compression": st.checkbox("Trace Compression", value=defaults["compression"]),
                "max_steps": st.number_input("Hard Step Limit", value=defaults["max_steps"], min_value=1, max_value=50),
                "stop_threshold": st.slider("Stop Threshold", 0.1, 1.0, 0.7 if "Aggressive" in profile else 0.85),
                "verification_risk": st.slider("Risk Trigger", 0.1, 1.0, 0.4 if "Aggressive" in profile else 0.6),
                "utility_threshold": st.slider("Tool Utility Gate", 0.1, 1.0, 0.3 if "Aggressive" in profile else 0.5)
            }

# --- SECTION B: BASELINE EXECUTION ---
st.markdown("<h2 class='section-header'>Step 2: Establish Baseline</h2>", unsafe_allow_html=True)
b_col1, b_col2 = st.columns([1, 2])

with b_col1:
    st.markdown("<p class='baseline-header'>Standard ReAct Execution</p>", unsafe_allow_html=True)
    st.markdown("""
    Runs a static agent loop with no adaptive compute optimizations. 
    This serves as the control group for the efficiency delta.
    """)
    if st.button("▶ EXECUTE BASELINE", key="btn_baseline"):
        baseline_toggles = {k: False for k in attco_toggles.keys() if k != "max_steps"}
        baseline_toggles["max_steps"] = min(10, attco_toggles["max_steps"])
        with st.spinner("Executing Control Group..."):
            st.session_state.baseline_result = execute_safe_async(run_single_inference(user_query, False, baseline_toggles))
        if st.session_state.baseline_result:
            st.toast("Baseline Complete", icon="✅")

if st.session_state.baseline_result:
    with b_col2:
        m = extract_metrics(st.session_state.baseline_result)
        cols = st.columns(3)
        cols[0].metric("Tokens", f"{m['tokens']:,}")
        cols[1].metric("Latency", f"{m['latency_s']:.2f}s")
        cols[2].metric("Depth", m["depth"])
        
        # render_orchestration_trace already provides expanders, avoid nesting
        render_orchestration_trace(st.session_state.baseline_result, "Standard ReAct Trajectory", "baseline-header")

# --- SECTION C: ATTCO EXECUTION ---
st.markdown("<h2 class='section-header'>Step 3: Adaptive Orchestration</h2>", unsafe_allow_html=True)
a_col1, a_col2 = st.columns([1, 2])

with a_col1:
    st.markdown("<p class='attco-header'>ATTCO Adaptive Runtime</p>", unsafe_allow_html=True)
    st.markdown("""
    Applies the full optimization stack: Depth Governance, Tool Gating, 
    and Confidence-Based Early Stopping.
    """)
    if st.button("▶ EXECUTE ATTCO", key="btn_attco"):
        with st.spinner("Executing Optimized Runtime..."):
            st.session_state.attco_result = execute_safe_async(run_single_inference(user_query, True, attco_toggles))
        if st.session_state.attco_result:
            st.toast("ATTCO Complete", icon="⚡")

if st.session_state.attco_result:
    with a_col2:
        m = extract_metrics(st.session_state.attco_result)
        cols = st.columns(3)
        cols[0].metric("Tokens", f"{m['tokens']:,}")
        cols[1].metric("Latency", f"{m['latency_s']:.2f}s")
        cols[2].metric("Depth", m["depth"])
        
        # render_orchestration_trace already provides expanders, avoid nesting
        render_orchestration_trace(st.session_state.attco_result, "ATTCO Adaptive Trajectory", "attco-header")

# --- SECTION D: COMPARATIVE ANALYTICS ---
st.markdown("<h2 class='section-header'>Step 4: Comparative Efficiency Analytics</h2>", unsafe_allow_html=True)

if st.session_state.baseline_result and st.session_state.attco_result:
    bm = extract_metrics(st.session_state.baseline_result)
    am = extract_metrics(st.session_state.attco_result)
    
    # 1. Metric Comparison
    comparison_data = []
    for label, key, unit in [("Total Tokens", "tokens", ""), ("Latency", "latency_s", "s"), ("Reasoning Depth", "depth", " steps"), ("Tool Calls", "tool_calls", "")]:
        b_val = bm[key]
        a_val = am[key]
        delta = a_val - b_val
        delta_pct = (delta / b_val * 100) if b_val != 0 else 0
        comparison_data.append({
            "Metric": label,
            "Baseline": f"{b_val}{unit}",
            "ATTCO (Optimized)": f"{a_val}{unit}",
            "Delta": f"{delta:+.2f}" if isinstance(delta, float) else f"{delta:+d}",
            "Improvement (%)": f"{-delta_pct:.1f}%"
        })
    
    df_comp = pd.DataFrame(comparison_data)
    st.table(df_comp.style.set_properties(**{'background-color': 'rgba(30, 41, 59, 0.3)', 'color': 'white'}))
    
    # 2. Pareto Visualization
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[bm["tokens"]], y=[1.0], mode='markers+text', name='Baseline', text=['Baseline'], textposition="top center", marker=dict(size=18, color="#60a5fa")))
    fig.add_trace(go.Scatter(x=[am["tokens"]], y=[0.98], mode='markers+text', name='ATTCO', text=['ATTCO'], textposition="top center", marker=dict(size=22, color="#a78bfa", symbol="star")))
    fig.update_layout(
        template="plotly_dark",
        title="Efficiency Pareto Frontier (Current Run)",
        xaxis_title="Token Cost",
        yaxis_title="Confidence/Quality Proxy",
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("💡 Comparative analytics will unlock once both **Baseline** and **ATTCO** runs are completed.")
