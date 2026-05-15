import asyncio
from controller.state import AgentState, ReasoningStep
from controller.nodes.compressor import compressor_node
from pprint import pprint

async def main():
    # Simulate a long trace with redundant steps
    state = AgentState(
        experiment_id="test",
        question_id="q1",
        question="What is the capital of France?"
    )
    
    # 6 steps (exceeds threshold of 5)
    state.steps = [
        ReasoningStep(step=1, thought="I need to search for France.", action="search", observation="France..."),
        ReasoningStep(step=2, thought="Thinking about France capital.", action=None, observation=None),
        ReasoningStep(step=3, thought="Searching for Paris.", action="search", observation="Paris is capital."),
        ReasoningStep(step=4, thought="Thinking more about Paris.", action=None, observation=None),
        ReasoningStep(step=5, thought="I am very sure it is Paris.", action=None, observation=None),
        ReasoningStep(step=6, thought="Let me double check.", action=None, observation=None),
    ]
    
    print(f"Initial Steps Count: {len(state.steps)}")
    
    # Run through Compressor
    state = await compressor_node(state)
    
    print(f"\nAfter Compressor Steps Count: {len(state.steps)}")
    print(f"Full History Count (Backup): {len(state.full_history)}")
    
    print("\nCompressed Steps View:")
    for s in state.steps:
        print(f"Step {s.step}: {s.thought}")
        
    print("\nCompression Metadata:")
    pprint(state.compression_history[-1])

if __name__ == "__main__":
    asyncio.run(main())
