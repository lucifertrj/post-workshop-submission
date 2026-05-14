import asyncio
from controller.state import AgentState
from controller.nodes.calibrator import calibrator_node, global_calibration_manager
from optimizer.modules.calibrator import CalibrationEngine, CalibrationDecision
from pprint import pprint

async def main():
    # 1. Test Parameter Injection
    state = AgentState(
        experiment_id="test",
        question_id="q1",
        question="What is 2+2?"
    )
    
    print("Initial Calibration Context:", state.calibration_context)
    state = await calibrator_node(state)
    print("\nAfter Calibrator Node - Active Parameters:")
    pprint(state.calibration_context)
    
    # 2. Test Calibration Engine Logic
    engine = CalibrationEngine()
    
    # Scenario: Low Accuracy
    low_acc_metrics = [{"accuracy": 0.5, "total_tokens": 500}]
    decision = engine.calculate_adjustment(state.calibration_context, low_acc_metrics)
    print("\nCalibration Decision (Low Accuracy):")
    pprint(decision.model_dump())
    
    # Apply Calibration
    new_snapshot = global_calibration_manager.apply_calibration(decision)
    print(f"\nNew Snapshot Version: {new_snapshot.version_id}")
    
    # 3. Verify Rollback
    print("\nTesting Rollback...")
    prev_snapshot = global_calibration_manager.rollback()
    if prev_snapshot:
        print(f"Rolled back to: {prev_snapshot.version_id}")
        pprint(global_calibration_manager.get_current_parameters())

if __name__ == "__main__":
    asyncio.run(main())
