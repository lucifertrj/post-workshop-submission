import asyncio
from optimizer.modules.arbitrator import ArbitrationEngine, OptimizerProposal, OptimizerAction
from pprint import pprint

async def test_arbitration():
    engine = ArbitrationEngine()
    
    # Scenario: Conflict between Confidence (Stop) and Tool (Suppress)
    # Priority: STOP (80) vs SUPPRESS_TOOL (50)
    proposals = [
        OptimizerProposal(
            optimizer_name="confidence_runtime",
            action=OptimizerAction.STOP,
            confidence=0.9,
            reason="High confidence answer detected."
        ),
        OptimizerProposal(
            optimizer_name="tool_governance",
            action=OptimizerAction.SUPPRESS_TOOL,
            confidence=0.8,
            reason="Redundant tool call detected."
        )
    ]
    
    print("Scenario 1: STOP vs SUPPRESS_TOOL")
    decision = await engine.arbitrate("test_exp", "q1", proposals)
    pprint(decision.model_dump())
    
    # Scenario: Conflict between Truncate (Hard Ceiling) and Stop (Early Stop)
    # Priority: TRUNCATE (100) vs STOP (80)
    proposals2 = [
        OptimizerProposal(
            optimizer_name="depth_controller",
            action=OptimizerAction.TRUNCATE,
            confidence=1.0,
            reason="Max depth reached."
        ),
        OptimizerProposal(
            optimizer_name="confidence_runtime",
            action=OptimizerAction.STOP,
            confidence=0.9,
            reason="High confidence answer detected."
        )
    ]
    
    print("\nScenario 2: TRUNCATE vs STOP")
    decision2 = await engine.arbitrate("test_exp", "q1", proposals2)
    pprint(decision2.model_dump())

if __name__ == "__main__":
    asyncio.run(test_arbitration())
