from pydantic import BaseModel, field_validator
from typing import List, Optional, Literal

class RunConfig(BaseModel):
    task_name: str
    task_type: Literal["classification", "summarization", "extraction", "judge", "generation"]
    mode: Literal["dataset", "nodataset"]
    base_prompt: str
    scorer: Literal["accuracy", "llm_judge"] = "accuracy"
    max_iterations: int = 8
    early_stop_threshold: float = 0.92
    variants_per_iter: int = 5
    dataset: Optional[List[dict]] = None
    criteria: Optional[List[str]] = None

    @field_validator("base_prompt")
    @classmethod
    def validate_prompt_length(cls, v):
        if len(v) > 16000: raise ValueError("base_prompt exceeds 16000 chars")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v, info):
        if v == "dataset" and not info.data.get("dataset"): raise ValueError("Dataset mode requires 'dataset' array")
        if v == "nodataset" and not info.data.get("criteria"): raise ValueError("No-dataset mode requires 'criteria' list")
        return v

    @field_validator("dataset")
    @classmethod
    def validate_dataset_items(cls, v):
        if v is None: return v
        if len(v) == 0: raise ValueError("Dataset must have ≥1 example")
        for item in v:
            if "input" not in item or "label" not in item: raise ValueError("Each item needs 'input' and 'label'")
        return v