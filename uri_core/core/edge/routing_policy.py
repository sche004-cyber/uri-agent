"""Pure deterministic routing policy. It has no execution dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Tuple

from .runtime_inventory import EdgeRuntimeInventory
from .settings import EdgeSettings


class IntelligenceRoutingDecision(str, Enum):
    SUPPRESS = "SUPPRESS"
    CONFIRM = "CONFIRM"
    EDGE_REPLY = "EDGE_REPLY"
    EXECUTE_PROPOSAL = "EXECUTE_PROPOSAL"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class RoutingInput:
    explicit_main_brain: bool = False
    uri_preflight_available: bool = False
    input_requires_confirmation: bool = False
    task_complex: bool = False
    proposal_valid: bool = False
    reply_valid: bool = False
    calibrated_confidence: Optional[float] = None
    calibration_current: bool = False
    resource_admitted: bool = False


@dataclass(frozen=True)
class RoutingEvaluation:
    decision: IntelligenceRoutingDecision
    reason_codes: Tuple[str, ...]


def _percent_half_up(score: float) -> int:
    return int((Decimal(str(score)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def evaluate_routing(settings: EdgeSettings, inventory: EdgeRuntimeInventory, request: RoutingInput) -> RoutingEvaluation:
    if request.uri_preflight_available:
        return RoutingEvaluation(IntelligenceRoutingDecision.SUPPRESS, ("uri_preflight",))
    if request.explicit_main_brain or settings.intelligence_mode == "MAIN_BRAIN_PREFERRED":
        return RoutingEvaluation(IntelligenceRoutingDecision.SUPPRESS, ("main_brain_bypass",))
    if not settings.enabled:
        return RoutingEvaluation(IntelligenceRoutingDecision.SUPPRESS, ("edge_disabled_by_user",))
    status = inventory.selection_status(settings.edge["runtime_id"], settings.edge["model_id"])
    if status != "ready":
        return RoutingEvaluation(IntelligenceRoutingDecision.SUPPRESS, (status,))
    if not request.resource_admitted:
        return RoutingEvaluation(IntelligenceRoutingDecision.ESCALATE, ("resource_limited",))
    if request.input_requires_confirmation:
        return RoutingEvaluation(IntelligenceRoutingDecision.CONFIRM, ("confirmation_required",))
    if request.task_complex:
        return RoutingEvaluation(IntelligenceRoutingDecision.ESCALATE, ("complex_task",))
    if request.proposal_valid:
        return RoutingEvaluation(IntelligenceRoutingDecision.EXECUTE_PROPOSAL, ("proposal_valid",))
    if request.reply_valid and request.calibration_current and request.calibrated_confidence is not None and 0 <= request.calibrated_confidence <= 1 and _percent_half_up(request.calibrated_confidence) >= settings.reply_confidence_threshold_percent:
        return RoutingEvaluation(IntelligenceRoutingDecision.EDGE_REPLY, ("reply_threshold_met",))
    return RoutingEvaluation(IntelligenceRoutingDecision.ESCALATE, ("edge_reply_ineligible",))
