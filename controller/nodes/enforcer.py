"""
Enforcer Node — Governs adaptive execution ceilings.
"""
from __future__ import annotations
from controller.state import AgentState
from optimizer.modules.depth_controller import DepthController

async def enforcer_node(state: AgentState) -> AgentState:
    """
    Apply runtime governance constraints (e.g. max depth truncation).
    """
    return await DepthController.enforce(state)
