"""
Runtime State Utilities — provides canonical serialization and mutation helpers for AgentState.
Ensures consistency between Pydantic objects and LangGraph dict-based state propagation.
"""
from __future__ import annotations
from typing import Any, List, Dict
from controller.state import AgentState, ReasoningStep, ToolCall

def get_steps(state: Any) -> List[ReasoningStep]:
    """
    Retrieves reasoning steps from state and ensures they are hydrated as ReasoningStep objects.
    Handles both dict-based and object-based state.
    """
    raw_steps = state.get("steps", []) if isinstance(state, dict) else getattr(state, "steps", [])
    hydrated = []
    for s in raw_steps:
        if isinstance(s, dict):
            hydrated.append(ReasoningStep.model_validate(s))
        else:
            hydrated.append(s)
    return hydrated

def get_last_step(state: Any) -> ReasoningStep | None:
    """Retrieves the last reasoning step hydrated as an object."""
    steps = get_steps(state)
    return steps[-1] if steps else None

def add_step(state: Any, step_obj: ReasoningStep) -> None:
    """
    Appends a reasoning step to the state in canonical dictionary format.
    Also updates the reasoning_history for frontend visibility.
    """
    step_dict = step_obj.model_dump()
    
    # Update steps (canonical runtime trajectory)
    if isinstance(state, dict):
        if "steps" not in state: state["steps"] = []
        state["steps"].append(step_dict)
    else:
        state.steps.append(step_dict) # Store as dict even in object
        
    # Update reasoning_history (uncompressed visualization trajectory)
    # This is always a list of dicts
    history = state.get("reasoning_history", []) if isinstance(state, dict) else getattr(state, "reasoning_history", [])
    history.append(step_dict)
    
    if isinstance(state, dict):
        state["reasoning_history"] = history
    else:
        state.reasoning_history = history

def update_last_step(state: Any, **kwargs) -> None:
    """
    Updates the last reasoning step with new fields.
    Kwargs can be: action, observation, tool_calls, etc.
    """
    if isinstance(state, dict):
        if not state.get("steps"): return
        last_step = state["steps"][-1]
        for k, v in kwargs.items():
            if k == "tool_calls" and isinstance(v, list):
                last_step[k] = [t.model_dump() if hasattr(t, "model_dump") else t for t in v]
            else:
                last_step[k] = v
        
        # Sync with reasoning_history
        if state.get("reasoning_history"):
            state["reasoning_history"][-1].update(last_step)
    else:
        if not state.steps: return
        last_step = state.steps[-1]
        # last_step is likely a dict now
        if isinstance(last_step, dict):
            for k, v in kwargs.items():
                if k == "tool_calls" and isinstance(v, list):
                    last_step[k] = [t.model_dump() if hasattr(t, "model_dump") else t for t in v]
                else:
                    last_step[k] = v
        
        # Sync with reasoning_history
        if state.reasoning_history:
            state.reasoning_history[-1].update(last_step if isinstance(last_step, dict) else last_step.model_dump())

def add_intervention(state: Any, action: str, rationale: str, optimizer: str, step_num: int) -> None:
    """Injects an optimizer intervention into the latest history entry."""
    history = state.get("reasoning_history", []) if isinstance(state, dict) else getattr(state, "reasoning_history", [])
    if not history: return
    
    last_entry = history[-1]
    if "interventions" not in last_entry:
        last_entry["interventions"] = []
        
    last_entry["interventions"].append({
        "action": action,
        "rationale": rationale,
        "optimizer": optimizer,
        "step": step_num
    })

def add_verification(state: Any, outcome: Dict[str, Any]) -> None:
    """Injects verification outcome into the history."""
    history = state.get("reasoning_history", []) if isinstance(state, dict) else getattr(state, "reasoning_history", [])
    if not history: return
    history[-1]["verification_outcome"] = outcome

def validate_runtime_state(state: Any) -> None:
    """
    Performs a sanity check on the runtime state to detect schema drift or corruption.
    Raises ValueError if critical inconsistencies are found.
    """
    steps = state.get("steps", []) if isinstance(state, dict) else getattr(state, "steps", [])
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
             # Force conversion if possible, or fail if completely malformed
             if hasattr(s, "model_dump"):
                 steps[i] = s.model_dump()
             else:
                 raise ValueError(f"Schema corruption detected at step {i}: Expected dict, got {type(s)}")

    history = state.get("reasoning_history", []) if isinstance(state, dict) else getattr(state, "reasoning_history", [])
    if len(history) < len(steps):
         # This indicates a persistence failure, though not necessarily fatal for logic
         pass
