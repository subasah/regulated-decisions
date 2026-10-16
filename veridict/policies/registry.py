"""
Veridict Policy Registry.
Loads, validates, and provides access to computable clinical policies.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from veridict.models.policy import PolicyDefinition, PolicyDomain


class PolicyRegistry:
    def __init__(self, policies_dir: Optional[Path] = None):
        if policies_dir is None:
            policies_dir = Path(__file__).parent
        self.policies_dir = Path(policies_dir)
        self._policies: Dict[str, PolicyDefinition] = {}
        self.reload()

    def reload(self) -> None:
        """Loads and parses all JSON policy definitions."""
        self._policies.clear()
        for filepath in self.policies_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    policy = PolicyDefinition(**data)
                    self._policies[policy.policy_id] = policy
            except Exception as e:
                print(f"[WARN] Failed to load policy from {filepath.name}: {e}")

    def get(self, policy_id: str) -> Optional[PolicyDefinition]:
        return self._policies.get(policy_id)

    def list_all(self) -> List[PolicyDefinition]:
        return list(self._policies.values())

    def list_by_domain(self, domain: PolicyDomain) -> List[PolicyDefinition]:
        return [p for p in self._policies.values() if p.domain == domain]

    def __contains__(self, policy_id: str) -> bool:
        return policy_id in self._policies


# Global default singleton instance
registry = PolicyRegistry()
