import asyncio
from controller.state import AgentState, ReasoningStep
from optimizer.modules.confidence import ConfidenceExtractor, EarlyStoppingPolicy
from pprint import pprint

async def main():
    # Simulate a state that is looping on the same action without getting new info
    state = AgentState(
        experiment_id="test",
        question_id="q1",
        question="What is the capital of France?"
    )
    
    # Adding repetitive steps
    state.steps = [
        ReasoningStep(step=1, thought="I need to search for France capital", action="search", observation="Paris"),
        ReasoningStep(step=2, thought="Let me double check the capital of France", action="search", observation="Paris"),
        ReasoningStep(step=3, thought="I should search one more time to be sure", action="search", observation="Paris")
    ]
    
    extractor = ConfidenceExtractor()
    policy = EarlyStoppingPolicy(stop_threshold=0.80, min_steps=2)
    
    score = await extractor.estimate(state)
    print("Confidence Score:")
    pprint(score.model_dump())
    
    decision = policy.evaluate(state, score)
    print("\nStop Decision:")
    pprint(decision.model_dump())

if __name__ == "__main__":
    asyncio.run(main())
