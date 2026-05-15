"""
Metric Normalizer — ensures consistency across legacy and canonical research metrics.
"""
from typing import Dict, List, Any

class MetricNormalizer:
    """Maps heterogeneous metric names into a canonical research schema."""
    
    # Mapping: legacy_name -> canonical_name
    MAPPING = {
        # Tokens
        "tokens": "avg_tokens",
        "total_tokens": "avg_tokens",
        "token_count": "avg_tokens",
        "tokens_consumed": "avg_tokens",
        "total_tokens_saved": "avg_tokens_saved",
        
        # Latency
        "latency": "avg_latency_ms",
        "latency_ms": "avg_latency_ms",
        "total_latency_ms": "avg_latency_ms",
        "tool_latency_saved_ms": "avg_latency_saved_ms",
        
        # Accuracy
        "accuracy": "avg_accuracy",
        "score": "avg_accuracy",
        "exact_match": "avg_exact_match",
        
        # Depth
        "steps": "avg_reasoning_depth",
        "depth": "avg_reasoning_depth",
        "actual_depth_reached": "avg_reasoning_depth",
        
        # Rates/Counts
        "truncation_count": "truncation_rate",
        "early_stop_count": "early_stop_rate",
        "verification_trigger_count": "verification_rate",
        "tools_suppressed_count": "tool_suppression_rate",
        "avg_compression_ratio": "compression_ratio"
    }

    @classmethod
    def normalize_name(cls, name: str) -> str:
        """Map a single metric name to its canonical form."""
        return cls.MAPPING.get(name, name)

    @classmethod
    def get_sql_aggregation(cls) -> str:
        """Generates a DuckDB SQL fragment for canonical aggregation."""
        aggregations = []
        
        # Inverse mapping for SQL (canonical -> [legacy1, legacy2])
        inv_map: Dict[str, List[str]] = {}
        for legacy, canonical in cls.MAPPING.items():
            if canonical not in inv_map: inv_map[canonical] = []
            inv_map[canonical].append(legacy)
            
        for canonical, legacies in inv_map.items():
            # Use CASE WHEN to capture any of the legacy names
            legacy_list = ", ".join([f"'{l}'" for l in legacies])
            # For most metrics we want AVG, for 'rate' we might want AVG of 0/1 markers
            if "rate" in canonical or "ratio" in canonical:
                aggregations.append(f"AVG(CASE WHEN metric_name IN ({legacy_list}) THEN value ELSE 0 END) as {canonical}")
            else:
                aggregations.append(f"AVG(CASE WHEN metric_name IN ({legacy_list}) THEN value END) as {canonical}")
                
        return ",\n            ".join(aggregations)
