import asyncio
from controller.state import AgentState
from intelligence.allocator.schema import ComputeBudgetAllocation, BudgetClass, LatencyClass
from optimizer.modules.depth_controller import DepthController
from pprint import pprint

async def main():
    # Create mock state with 5 reasoning steps
    state = AgentState(
        experiment_id="test",
        question_id="q1",
        question="What is the capital of France?",
        metadata={
            "compute_allocation": ComputeBudgetAllocation(
                budget_class=BudgetClass.ULTRA_LOW,
                max_reasoning_depth=3,
                soft_reasoning_budget=1,
                expected_token_budget=500,
                expected_tool_budget=0,
                latency_class=LatencyClass.URGENT,
                confidence=0.9,
                policy_name="test",
                allocation_latency_ms=0.0
            ).model_dump()
        }
    )
    
    # Simulate 3 steps being taken
    state.steps = [{"step": 1, "thought": "t"}, {"step": 2, "thought": "t"}, {"step": 3, "thought": "t"}]
    
    print("State before enforcer:", state.is_terminated, len(state.steps))
    
    # Run through enforcer
    state = await DepthController.enforce(state)
    
    print("State after enforcer:")
    print("is_terminated:", state.is_terminated)
    print("termination_cause:", state.termination_cause)
    print("final_answer:", state.final_answer)

if __name__ == "__main__":
    asyncio.run(main())
