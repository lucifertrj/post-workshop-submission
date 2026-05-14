"""Dataset loader interface."""
from __future__ import annotations
import abc
from typing import Any, Dict, List
from datasets import load_dataset

class DatasetLoader(abc.ABC):
    @abc.abstractmethod
    def load(self, split: str, max_samples: int | None = None) -> List[Dict[str, Any]]:
        pass

class GSM8KLoader(DatasetLoader):
    def load(self, split: str = "test", max_samples: int | None = None) -> List[Dict[str, Any]]:
        ds = load_dataset("gsm8k", "main", split=split)
        if max_samples:
            ds = ds.select(range(min(max_samples, len(ds))))
        
        results = []
        for i, row in enumerate(ds):
            results.append({
                "id": f"gsm8k_{split}_{i}",
                "question": row["question"],
                "answer": row["answer"],
                "dataset": "gsm8k"
            })
        return results

class HotpotQALoader(DatasetLoader):
    def load(self, split: str = "validation", max_samples: int | None = None) -> List[Dict[str, Any]]:
        ds = load_dataset("hotpot_qa", "fullwiki", split=split)
        if max_samples:
            ds = ds.select(range(min(max_samples, len(ds))))
            
        results = []
        for i, row in enumerate(ds):
            results.append({
                "id": row.get("id", f"hotpotqa_{split}_{i}"),
                "question": row["question"],
                "answer": row["answer"],
                "dataset": "hotpot_qa"
            })
        return results

def get_loader(dataset_name: str) -> DatasetLoader:
    if dataset_name.lower() == "gsm8k":
        return GSM8KLoader()
    elif dataset_name.lower() == "hotpotqa":
        return HotpotQALoader()
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")
