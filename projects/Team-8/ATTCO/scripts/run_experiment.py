"""
Experiment execution launcher.
Usage: python scripts/run_experiment.py experiment=baseline
"""
from __future__ import annotations
import hydra
from omegaconf import DictConfig, OmegaConf

@hydra.main(config_path="../configs", config_name="config", version_base="1.3")
def main(cfg: DictConfig) -> None:
    from experiments.registry import ExperimentRegistry
    registry = ExperimentRegistry()
    record = registry.register(
        name=cfg.experiment.name,
        config=OmegaConf.to_container(cfg, resolve=True),  # type: ignore[arg-type]
    )
    print(f"Experiment registered: {record.experiment_id}")
    print(f"Git SHA: {record.git_sha}")
    print("Experiment runner wiring required — see benchmark runner.")

if __name__ == "__main__":
    main()
