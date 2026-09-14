"""Model-discoverable capability and action primitives.

This package is intentionally an adapter layer.  It does not replace the
existing runtime capability registry or grant execution authority to models.
"""

from .base import Action, ActionSchema, ApprovalRequirement, Capability, RiskLevel
from .executor import MultiActionExecutor
from .registry import LegacyCapabilityAdapter, MultiActionCapabilityRegistry

__all__ = [
    "Action",
    "ActionSchema",
    "ApprovalRequirement",
    "Capability",
    "RiskLevel",
    "LegacyCapabilityAdapter",
    "MultiActionCapabilityRegistry",
    "MultiActionExecutor",
]
