"""Baseline Agent wrapping the static ReAct Graph."""
from __future__ import annotations
from typing import Any
from controller.graph import build_graph
from controller.state import AgentState

class BaselineAgent:
    def __init__(self, experiment_id: str, max_steps: int = 10, ablation_toggles: dict[str, bool] | None = None) -> None:
        self._experiment_id = experiment_id
        self._max_steps = max_steps
        self._ablation_toggles = ablation_toggles or {}
        self._graph = build_graph().compile()

    async def run(self, question_id: str, question: str) -> AgentState:
        """Run the agent on a specific question."""
        # Ensure the tracer drain loop is running so events reach W&B/LangSmith
        from tracing.tracer import global_tracer
        if not global_tracer._running:
            await global_tracer.start()

        initial_state = AgentState(
            experiment_id=self._experiment_id,
            question_id=question_id,
            question=question,
            metadata={"ablation_toggles": self._ablation_toggles}
        )
        # LangGraph graph execution loop with aggressive recursion limit
        result_state = await self._graph.ainvoke(
            initial_state,
            config={"recursion_limit": 500}
        )
        from controller.utils import validate_runtime_state
        validate_runtime_state(result_state)

        # Flush tracer to ensure all events are dispatched to backends (W&B, local, etc.)
        try:
            await global_tracer.flush()
        except Exception:
            pass  # Telemetry failure must never crash the runtime

        return result_state
