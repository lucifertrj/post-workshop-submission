import asyncio
from controller.state import AgentState, ReasoningStep
from controller.nodes.tool_gater import tool_gater_node
from pprint import pprint

async def main():
    # Simulate a state with high reasoning sufficiency where the tool is no longer useful
    state = AgentState(
        experiment_id="test",
        question_id="q1",
        question="What is 5 + 5?"
    )
    
    # Adding steps to make sufficiency high
    state.steps = [
        ReasoningStep(step=1, thought="It's arithmetic", action="calculator[5+5]", observation="10"),
        ReasoningStep(step=2, thought="I know the answer is 10, but let me search for the meaning of 5+5", action="search[5+5]", observation=""),
    ]
    
    # Run through gater
    print("Before Gater Action:", state.steps[-1].action)
    print("Before Gater ToolCalls Count:", len(state.steps[-1].tool_calls))
    
    state = await tool_gater_node(state)
    
    print("\nAfter Gater Action:", state.steps[-1].action)
    print("After Gater ToolCalls Count:", len(state.steps[-1].tool_calls))
    
    if state.steps[-1].tool_calls:
        print("Suppression Error Reason:", state.steps[-1].tool_calls[0].error)
        
    print("\nTrajectory metadata recorded:")
    pprint(state.metadata.get("tool_necessity_trajectory"))

if __name__ == "__main__":
    asyncio.run(main())
