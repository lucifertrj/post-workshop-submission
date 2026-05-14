"""
Statistical Evaluator — computes significance, confidence intervals, and Pareto frontiers.
"""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Any, Tuple

class StatsEvaluator:
    """Scientific evaluation engine for benchmark results."""
    
    @staticmethod
    def compute_confidence_intervals(data: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate bootstrap confidence intervals for a metric."""
        if not data:
            return (0.0, 0.0)
        
        # Simple bootstrap approximation
        boot_means = []
        for _ in range(1000):
            sample = np.random.choice(data, size=len(data), replace=True)
            boot_means.append(np.mean(sample))
            
        lower = np.percentile(boot_means, (1 - confidence) / 2 * 100)
        upper = np.percentile(boot_means, (1 + confidence) / 2 * 100)
        return float(lower), float(upper)

    @staticmethod
    def identify_pareto_frontier(points: List[Dict[str, float]], x_metric: str, y_metric: str, x_minimize: bool = True, y_maximize: bool = True) -> List[Dict[str, float]]:
        """Identify non-dominated points in the Accuracy vs Cost tradeoff space."""
        if not points:
            return []
            
        pareto_points = []
        for i, p1 in enumerate(points):
            is_dominated = False
            for j, p2 in enumerate(points):
                if i == j: continue
                
                # Check if p2 dominates p1
                x1, x2 = p1[x_metric], p2[x_metric]
                y1, y2 = p1[y_metric], p2[y_metric]
                
                # p2 dominates p1 if it's better or equal in both, and strictly better in at least one
                better_x = x2 < x1 if x_minimize else x2 > x1
                better_y = y2 > y1 if y_maximize else y2 < y1
                equal_x = x2 == x1
                equal_y = y2 == y1
                
                if (better_x or equal_x) and (better_y or equal_y) and (better_x or better_y):
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto_points.append(p1)
                
        return sorted(pareto_points, key=lambda x: x[x_metric])
