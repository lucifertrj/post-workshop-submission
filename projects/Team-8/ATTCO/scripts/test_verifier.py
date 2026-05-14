import asyncio
from controller.state import AgentState, ReasoningStep
from controller.nodes.arbitrator import arbitrator_node
from controller.nodes.verifier import verifier_node
from pprint import pprint

async def main():
    # Simulate a state with high risk (volatile confidence)
    state = AgentState(
        experiment_id="test",
        question_id="q1",
        question="What is the square root of 256?",
        metadata={
            "confidence_trajectory": [
                {"stop_confidence": 0.9},
                {"stop_confidence": 0.2}, # Volatility!
                {"stop_confidence": 0.8}
            ]
        }
    )
    
    state.steps = [
        ReasoningStep(step=1, thought="I think it might be 16.", action=None, observation=None)
    ]
    
    print("Initial State Triggered:", state.metadata.get("verification_triggered"))
    
    # 1. Run through Arbitrator to trigger verification
    state = await arbitrator_node(state)
    print("\nAfter Arbitrator - Verification Triggered:", state.metadata.get("verification_triggered"))
    print("Arbitrator Rationale:", state.metadata.get("verification_rationale"))
    
    # 2. Run through Verifier
    state = await verifier_node(state)
    print("\nAfter Verifier - Trigger Cleared:", state.metadata.get("verification_triggered"))
    print("Verification History Count:", len(state.verification_history))
    
    if state.steps and state.steps[-1].thought.startswith("[SELF-VALIDATION"):
        print("\nCritique injected successfully!")
        pprint(state.steps[-1].thought)

if __name__ == "__main__":
    asyncio.run(main())
