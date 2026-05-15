"""
Difficulty Intelligence Schema — Defines structured predictions for query complexity.
"""
from __future__ import annotations
import enum
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class DifficultyClass(str, enum.Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXTREME = "extreme"

class ComplexityCategory(str, enum.Enum):
    ARITHMETIC = "arithmetic"
    SYMBOLIC = "symbolic"
    MULTI_HOP = "multi_hop"
    RETRIEVAL_HEAVY = "retrieval_heavy"
    COMPARISON = "comparison"
    COMPOSITIONAL = "compositional"
    AMBIGUOUS = "ambiguous"

class FeatureVector(BaseModel):
    """Extracted features used to estimate difficulty."""
    token_length: int = 0
    entity_density: float = 0.0
    arithmetic_indicators: int = 0
    symbolic_indicators: int = 0
    multi_hop_indicators: int = 0
    temporal_indicators: int = 0
    decomposition_indicators: int = 0
    ambiguity_indicators: int = 0
    comparison_indicators: int = 0
    retrieval_indicators: int = 0

class DifficultyPrediction(BaseModel):
    """The structured output of a difficulty estimator."""
    difficulty_class: DifficultyClass
    complexity_categories: List[ComplexityCategory]
    expected_reasoning_depth: int
    expected_tool_usage: bool
    expected_compute_tokens: int
    confidence: float
    features: FeatureVector
    estimator_name: str
    latency_ms: float
