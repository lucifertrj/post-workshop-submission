"""
Feature Extraction Pipeline for Difficulty Estimation.
"""
from __future__ import annotations
import re
from typing import Set
from .schema import FeatureVector

class FeatureExtractor:
    """Extracts surface-level and structural features from queries."""

    # Simple heuristic vocabularies
    ARITHMETIC_TERMS = {"add", "subtract", "multiply", "divide", "sum", "difference", "product", "total", "ratio", "percent", "how many", "calculate"}
    SYMBOLIC_TERMS = {"if", "then", "implies", "therefore", "let", "assume", "suppose", "prove"}
    MULTI_HOP_TERMS = {"who", "where", "which", "that was", "and then"}
    TEMPORAL_TERMS = {"before", "after", "during", "when", "first", "last", "year", "date", "until"}
    DECOMPOSITION_TERMS = {"steps", "firstly", "secondly", "finally", "break down"}
    AMBIGUITY_TERMS = {"might", "could", "maybe", "probably", "possibly", "depends"}
    COMPARISON_TERMS = {"more", "less", "better", "worse", "than", "compare", "tallest", "largest", "most"}
    RETRIEVAL_TERMS = {"who is", "when did", "capital of", "director of", "author of"}

    def __init__(self) -> None:
        pass

    def _count_matches(self, words: Set[str], vocab: Set[str]) -> int:
        return len(words.intersection(vocab))

    def extract(self, query: str) -> FeatureVector:
        # Normalize
        normalized = query.lower()
        words = set(re.findall(r'\b\w+\b', normalized))
        
        # Token length (naive)
        token_length = len(normalized.split())
        
        # Entity density proxy: capitalized words in original query
        capitalized = len(re.findall(r'\b[A-Z][a-z]+\b', query))
        entity_density = capitalized / max(1, token_length)
        
        # Arithmetic: presence of numbers or math terms
        numbers_count = len(re.findall(r'\b\d+\b', query))
        arithmetic_indicators = self._count_matches(words, self.ARITHMETIC_TERMS) + numbers_count
        
        return FeatureVector(
            token_length=token_length,
            entity_density=entity_density,
            arithmetic_indicators=arithmetic_indicators,
            symbolic_indicators=self._count_matches(words, self.SYMBOLIC_TERMS),
            multi_hop_indicators=self._count_matches(words, self.MULTI_HOP_TERMS),
            temporal_indicators=self._count_matches(words, self.TEMPORAL_TERMS),
            decomposition_indicators=self._count_matches(words, self.DECOMPOSITION_TERMS),
            ambiguity_indicators=self._count_matches(words, self.AMBIGUITY_TERMS),
            comparison_indicators=self._count_matches(words, self.COMPARISON_TERMS),
            retrieval_indicators=self._count_matches(words, self.RETRIEVAL_TERMS)
        )
