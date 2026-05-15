"""
Registry for Allocation Policies.
"""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAllocationPolicy

class PolicyRegistry:
    def __init__(self) -> None:
        self._policies: Dict[str, BaseAllocationPolicy] = {}

    def register(self, policy: BaseAllocationPolicy) -> None:
        self._policies[policy.name] = policy

    def get_policy(self, name: str) -> Optional[BaseAllocationPolicy]:
        return self._policies.get(name)

default_policy_registry = PolicyRegistry()
