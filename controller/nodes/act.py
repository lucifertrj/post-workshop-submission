"""Act node — tool invocation step."""
from __future__ import annotations
import time
import json
from controller.state import AgentState, ToolCall
from baseline.tools.registry import default_registry

import structlog
logger = structlog.get_logger(__name__)

async def act_node(state: AgentState) -> AgentState:
    """Execute the action parsed from the last thought step."""
    logger.info("act_node_entry", step=state.step_count)
    from controller.utils import get_last_step, update_last_step
    
    last_step = get_last_step(state)
    if not last_step or not last_step.action:
        return state
        
    # Simple parse action heuristic: "ToolName[tool_input]"
    action_str = last_step.action
    tool_name = action_str.split("[")[0].strip()
    tool_input_str = action_str.split("[")[1].replace("]", "").strip() if "[" in action_str else ""
    
    # Try parsing json if needed
    try:
        tool_input = json.loads(tool_input_str) if tool_input_str.startswith("{") else {"query": tool_input_str}
    except Exception:
        tool_input = {"query": tool_input_str}
        
    tc = ToolCall(tool_name=tool_name, tool_input=tool_input)
    start_time = time.perf_counter()
    
    try:
        result = await default_registry.execute(tool_name, **tool_input)
        tc.tool_output = str(result)
    except Exception as e:
        tc.error = str(e)
        
    tc.latency_ms = (time.perf_counter() - start_time) * 1000
    
    # Update state via utility
    tool_calls = last_step.tool_calls + [tc]
    update_last_step(state, tool_calls=tool_calls)
    
    logger.info("act_node_exit", tool=tool_name, success=not tc.error)
    return state
