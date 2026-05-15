"""Observe node — process tool output."""
from __future__ import annotations
from controller.state import AgentState
import structlog
logger = structlog.get_logger(__name__)

async def observe_node(state: AgentState) -> AgentState:
    """Process tool output and update reasoning state."""
    from controller.utils import get_last_step, update_last_step
    
    last_step = get_last_step(state)
    if not last_step:
        return state
        
    if not last_step.tool_calls:
        # If no tool calls were made but an action was specified, maybe it was invalid
        if last_step.action:
            update_last_step(state, observation="Error: Invalid action or tool not found.")
        return state
        
    # Aggregate tool outputs into an observation string
    outputs = []
    for tc in last_step.tool_calls:
        if tc.error:
            outputs.append(f"Tool {tc.tool_name} failed: {tc.error}")
        else:
            outputs.append(f"Tool {tc.tool_name} returned: {tc.tool_output}")
            
    observation = "\n".join(outputs)
    update_last_step(state, observation=observation)
    
    # Check if final answer
    if last_step.action and last_step.action.lower().startswith("finish"):
        state.is_terminated = True
        state.final_answer = last_step.action
        update_last_step(state, is_final=True)
        
    return state
