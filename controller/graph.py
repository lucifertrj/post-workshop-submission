"""
LangGraph Reasoning Graph — defines the cyclic ReAct agent graph.
Nodes are composed from controller/nodes/. Routing is determined by policies.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from controller.state import AgentState


def _route_after_arbitrator(state: AgentState) -> str:
    """Route to act if not terminated, else terminate."""
    if state.is_terminated:
        return "terminate"
    return "act"


def _route_after_arbitrator_post(state: AgentState) -> str:
    """Route to verifier if not terminated, else terminate."""
    if state.is_terminated:
        return "terminate"
    return "verifier"


def _should_terminate(state: AgentState) -> str:
    """Edge router: determines next node from current state."""
    if state.is_terminated:
        return "terminate"
    return "reason"


def build_graph() -> StateGraph:
    """
    Construct the base ATTCO ReAct reasoning graph.
    Node implementations are imported lazily to maintain boundary isolation.
    """
    from controller.nodes.reason import reason_node
    from controller.nodes.act import act_node
    from controller.nodes.observe import observe_node
    from controller.nodes.terminate import terminate_node
    from controller.nodes.difficulty import difficulty_node
    from controller.nodes.allocator import allocator_node
    from controller.nodes.arbitrator import arbitrator_node
    from controller.nodes.verifier import verifier_node
    from controller.nodes.compressor import compressor_node
    from controller.nodes.calibrator import calibrator_node

    graph = StateGraph(AgentState)

    graph.add_node("difficulty", difficulty_node)
    graph.add_node("allocator", allocator_node)
    graph.add_node("calibrator", calibrator_node)
    graph.add_node("reason", reason_node)
    graph.add_node("arbitrator", arbitrator_node)
    graph.add_node("act", act_node)
    graph.add_node("observe", observe_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("compressor", compressor_node)
    graph.add_node("terminate", terminate_node)

    graph.set_entry_point("difficulty")
    graph.add_edge("difficulty", "allocator")
    graph.add_edge("allocator", "calibrator")
    graph.add_edge("calibrator", "reason")
    
    # After Reason, run Arbitrator to check for Tool Suppression or Truncation
    graph.add_edge("reason", "arbitrator")
    
    # Conditional route after first arbitrator
    graph.add_conditional_edges(
        "arbitrator",
        _route_after_arbitrator,
        {"act": "act", "terminate": "terminate"}
    )
    
    graph.add_edge("act", "observe")
    
    # After Observe, run Arbitrator again to check for Early Stop or Truncation or Verify
    graph.add_node("arbitrator_post", arbitrator_node)
    graph.add_edge("observe", "arbitrator_post")
    
    # Conditional route after post-arbitrator
    graph.add_conditional_edges(
        "arbitrator_post",
        _route_after_arbitrator_post,
        {"verifier": "verifier", "terminate": "terminate"}
    )
    
    # After verification (or if skipped), run compressor before going back to reason
    graph.add_edge("verifier", "compressor")
    
    graph.add_conditional_edges(
        "compressor",
        _should_terminate,
        {"reason": "reason", "terminate": "terminate"},
    )
    
    # Final step: terminate always leads to END
    graph.add_edge("terminate", END)

    return graph
