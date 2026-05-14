import asyncio
import sys
from pathlib import Path

# Add project root to path
root_path = Path(__file__).parent.parent.absolute()
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from infrastructure.config.loader import ConfigLoader
ConfigLoader.load()

from baseline.agent import BaselineAgent

async def run_dual_inference(query: str):
    baseline_agent = BaselineAgent(
        experiment_id="baseline_playground",
        ablation_toggles={"depth_controller": False}
    )
    
    attco_agent = BaselineAgent(
        experiment_id="attco_playground",
        ablation_toggles={"depth_controller": True}
    )
    
    print("Starting dual inference...")
    results = await asyncio.gather(
        baseline_agent.run("playground", query),
        attco_agent.run("playground", query)
    )
    print("Dual inference complete.")
    return results

if __name__ == "__main__":
    query = "What is 2+2?"
    asyncio.run(run_dual_inference(query))
