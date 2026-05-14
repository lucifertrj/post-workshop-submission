import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).parent.absolute()
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from baseline.agent import BaselineAgent
from infrastructure.config.loader import ConfigLoader
from infrastructure.config.profile_manager import ProfileManager

async def test_run():
    print("[START] Initializing ATTCO Test Runtime...")
    ConfigLoader.load()
    # Force visualization profile for maximum trace density
    ProfileManager.load("visualization")
    
    agent = BaselineAgent(
        experiment_id="test_diagnostics",
        ablation_toggles={
            "depth_controller": True,
            "early_stopping": True,
            "verification": True,
            "tool_gating": True,
            "compression": True
        }
    )
    
    query = "What is the capital of France and what is its current population? Summarize the history of the Eiffel Tower in 2 sentences."
    
    print(f"[QUERY] Executing Query: {query}")
    try:
        result = await agent.run("test_q1", query)
        
        print("\n[OK] Execution Complete!")
        print(f"Termination Cause: {result.get('termination_cause')}")
        print(f"Reasoning History Length: {len(result.get('reasoning_history', []))}")
        print(f"Final Answer: {result.get('final_answer')}")
        
        # Verify content presence
        history = result.get('reasoning_history', [])
        if len(history) > 0:
            first_step = history[0]
            print(f"[INFO] Step 1 Thought Sample: {first_step.get('thought', '')[:50]}...")
            if 'interventions' in first_step:
                print(f"[INFO] Step 1 Interventions: {len(first_step['interventions'])}")
        
        final_ans = result.get('final_answer', '')
        if final_ans and len(final_ans) > 20:
            print("[OK] Final Answer Synthesis looks healthy.")
        else:
            print("[WARN] Final Answer seems too short or missing.")
            
    except Exception as e:
        print(f"[ERROR] EXECUTION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_run())
