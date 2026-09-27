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
    # M33.3-R S6 (D2): under EDGE_ONLY, SUPPRESS/ESCALATE would hand work to the
    # Main Brain; LIMITATION surfaces the limitation/escalation requirement instead.
    LIMITATION = "LIMITATION"


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


def _edge_only_guard(settings: EdgeSettings, evaluation: RoutingEvaluation) -> RoutingEvaluation:
    # D2 / M33.2 section 3: EDGE_ONLY never hands work to the Capable Brain.
    # SUPPRESS and ESCALATE both mean "the Main Brain continues", so under
    # EDGE_ONLY they become an explicit limitation instead.
    if settings.intelligence_mode == "EDGE_ONLY" and evaluation.decision in (
            IntelligenceRoutingDecision.SUPPRESS, IntelligenceRoutingDecision.ESCALATE) \
            and evaluation.reason_codes != ("uri_preflight",):
        return RoutingEvaluation(IntelligenceRoutingDecision.LIMITATION,
                                 evaluation.reason_codes + ("edge_only_capable_forbidden",))
    return evaluation


def evaluate_routing(settings: EdgeSettings, inventory: EdgeRuntimeInventory, request: RoutingInput) -> RoutingEvaluation:
    return _edge_only_guard(settings, _evaluate_routing(settings, inventory, request))


def _evaluate_routing(settings: EdgeSettings, inventory: EdgeRuntimeInventory, request: RoutingInput) -> RoutingEvaluation:
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


# ---------------------------------------------------------------------------
# M33.3-R S6: D2 mode mapping, explicit model selection, Edge OFF, and G2
# supporting-Edge work. Same routing authority as evaluate_routing (M33.2 §6
# amendment G2: "one routing authority: this state machine, extended").
# Pure and deterministic; not wired into any production request path.
# ---------------------------------------------------------------------------

ROUTE_POLICY_VERSION = "m33.3-r.s6.v1"


class WorkRole(str, Enum):
    SUBSTANTIVE = "SUBSTANTIVE"   # reasoning, synthesis, substantive drafting, planning, complex tools
    SUPPORTING = "SUPPORTING"     # reference work, extraction, formatting, clarification wording, assistance


class RouteTarget(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    EDGE = "EDGE"
    CAPABLE = "CAPABLE"
    LIMITATION = "LIMITATION"     # honest limitation / escalation requirement; no model is called


class WordingNeedClass(str, Enum):
    SIMPLE = "SIMPLE"
    EXPLAIN = "EXPLAIN"
    REASONING = "REASONING"


@dataclass(frozen=True)
class IntelligenceRouteRequest:
    role: WorkRole
    explicit_model_id: Optional[str] = None      # None = AUTO
    auto_capable_model_id: Optional[str] = None  # the Capable Brain the AUTO path would use
    capable_available: bool = False
    deterministic_sufficient: bool = False
    deterministic_fallback_available: bool = False
    edge_role_qualified: bool = False             # the Edge role is independently qualified for this task class
    edge_warm: bool = False                       # the Edge model is already resident
    allow_edge_cold_load: bool = False
    edge_sufficient: bool = False                 # substantive work fits the Edge envelope
    resource_admitted: bool = False


@dataclass(frozen=True)
class IntelligenceRoute:
    target: RouteTarget
    model_id: Optional[str]
    reason_codes: Tuple[str, ...]
    policy_version: str = ROUTE_POLICY_VERSION

    @property
    def invokes_edge(self) -> bool:
        return self.target == RouteTarget.EDGE

    @property
    def invokes_capable(self) -> bool:
        return self.target == RouteTarget.CAPABLE


def edge_eligibility(settings: EdgeSettings, inventory: EdgeRuntimeInventory,
                     request: IntelligenceRouteRequest) -> Tuple[bool, str]:
    """Return whether an Edge call is admissible; unknown is ineligible (M33.2 §3)."""
    if not settings.enabled:
        return False, "edge_disabled_by_user"
    status = inventory.selection_status(settings.edge["runtime_id"], settings.edge["model_id"])
    if status != "ready":
        return False, status
    if not request.edge_role_qualified:
        return False, "edge_role_unqualified"
    if not request.resource_admitted:
        return False, "resource_limited"
    if not request.edge_warm and not request.allow_edge_cold_load:
        return False, "edge_not_warm_no_cold_load"
    return True, "edge_eligible"


def evaluate_intelligence_route(settings: EdgeSettings, inventory: EdgeRuntimeInventory,
                                request: IntelligenceRouteRequest) -> IntelligenceRoute:
    if not isinstance(request.role, WorkRole):
        raise ValueError("role must be a WorkRole")
    mode = settings.intelligence_mode
    edge_ok, edge_reason = edge_eligibility(settings, inventory, request)
    edge_model = settings.edge.get("model_id") if edge_ok else None
    explicit = request.explicit_model_id
    capable_model = explicit or request.auto_capable_model_id
    choice = "explicit_model" if explicit else "auto"
    if request.deterministic_sufficient:
        return IntelligenceRoute(RouteTarget.DETERMINISTIC, None, ("deterministic_sufficient", choice))

    def limitation(*reasons: str) -> IntelligenceRoute:
        return IntelligenceRoute(RouteTarget.LIMITATION, None, reasons + (edge_reason, choice))

    def capable(reason: str) -> IntelligenceRoute:
        if mode == "EDGE_ONLY":
            return limitation("edge_only_capable_forbidden")
        if not request.capable_available or not capable_model:
            return limitation("capable_unavailable")
        return IntelligenceRoute(RouteTarget.CAPABLE, capable_model, (reason, choice))

    if request.role == WorkRole.SUPPORTING:
        # G2: qualified supporting Edge work stays permitted in every mode and
        # with an explicit selection; it never replaces substantive work.
        if edge_ok:
            return IntelligenceRoute(RouteTarget.EDGE, edge_model, ("supporting_edge", choice))
        if request.deterministic_fallback_available:
            return IntelligenceRoute(RouteTarget.DETERMINISTIC, None,
                                     ("deterministic_fallback", edge_reason, choice))
        return capable("supporting_capable")

    # Substantive work.
    if mode == "EDGE_ONLY":
        if edge_ok and request.edge_sufficient and not explicit:
            return IntelligenceRoute(RouteTarget.EDGE, edge_model, ("edge_only_substantive",))
        return limitation("edge_only_capable_forbidden",
                          "explicit_model_not_callable_under_edge_only" if explicit else "edge_insufficient")
    if explicit:
        # G2: the selected model is the Capable Brain for substantive work; Edge never downgrades it.
        return capable("explicit_selected_model")
    if mode == "HYBRID":
        if edge_ok and request.edge_sufficient:
            return IntelligenceRoute(RouteTarget.EDGE, edge_model, ("hybrid_edge_efficiency_first",))
        return capable("hybrid_capable_escalation")
    if mode == "MAIN_BRAIN_PREFERRED":
        if request.capable_available and capable_model:
            return IntelligenceRoute(RouteTarget.CAPABLE, capable_model, ("main_brain_preferred", choice))
        if edge_ok and request.edge_sufficient:
            # M33.2 §3: Edge is reserved for Main-Brain-unavailable recovery.
            return IntelligenceRoute(RouteTarget.EDGE, edge_model, ("main_brain_unavailable_edge_recovery",))
        return limitation("capable_unavailable")
    raise ValueError("invalid intelligence_mode")


def route_clarification_wording(settings: EdgeSettings, inventory: EdgeRuntimeInventory,
                                need_class: WordingNeedClass, *, edge_wording_qualified: bool,
                                edge_warm: bool, resource_admitted: bool, capable_available: bool,
                                explicit_model_id: Optional[str] = None,
                                auto_capable_model_id: Optional[str] = None) -> IntelligenceRoute:
    """Plan A R2.5 wording table as a projection of the single router.

    SIMPLE -> validated template. EXPLAIN -> Edge wording role when eligible and
    already warm, else template (never cold-load). REASONING -> Capable Brain
    when the mode permits it; under EDGE_ONLY a template limitation statement.
    """
    need = WordingNeedClass(need_class)
    if need == WordingNeedClass.SIMPLE:
        return evaluate_intelligence_route(settings, inventory, IntelligenceRouteRequest(
            WorkRole.SUPPORTING, deterministic_sufficient=True))
    if need == WordingNeedClass.EXPLAIN:
        return evaluate_intelligence_route(settings, inventory, IntelligenceRouteRequest(
            WorkRole.SUPPORTING, explicit_model_id=explicit_model_id,
            auto_capable_model_id=auto_capable_model_id, capable_available=capable_available,
            deterministic_fallback_available=True, edge_role_qualified=edge_wording_qualified,
            edge_warm=edge_warm, allow_edge_cold_load=False, resource_admitted=resource_admitted))
    return evaluate_intelligence_route(settings, inventory, IntelligenceRouteRequest(
        WorkRole.SUBSTANTIVE, explicit_model_id=explicit_model_id,
        auto_capable_model_id=auto_capable_model_id, capable_available=capable_available,
        edge_role_qualified=False, edge_warm=edge_warm, resource_admitted=resource_admitted))
