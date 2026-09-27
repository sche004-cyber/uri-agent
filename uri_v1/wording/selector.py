"""Policy-mode clarification wording: need class -> unified router -> tier ->
RenderValidator -> fail-closed template fallback (Plan A R2.5, §6; M33.2 G1).

The single routing authority is `uri_core.core.edge.routing_policy`
(`route_clarification_wording`). `uri_v1` never imports `uri_core`, so the
caller injects the router as `route_wording(need_class, edge_warm)`; this
module only interprets the returned route's target. The result carries a
response `trace_id` (S7) so Change/feedback events can attach to the exact
wording shown.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Optional, Tuple

from uri_v1.evaluation.trace_context import new_trace_id, require_trace_id
from uri_v1.reference_clarification.render_contracts import RenderOutput, make_render_request
from uri_v1.reference_clarification.render_validator import validate_render
from uri_v1.reference_clarification.template_renderer import presented_options, render_template
from uri_v1.turn.rar_clarification_contract import ClarificationContract

from .need_class import NEED_CLASS_POLICY_VERSION, classify_need
from .renderer_port import RenderAttempt, RendererPort

RouteWording = Callable[[str, bool], Any]  # (need_class, edge_warm) -> route with .target


def route_target(route: Any) -> str:
    target = getattr(route, "target", None)
    return str(getattr(target, "value", target))


@dataclass(frozen=True)
class WordingResult:
    trace_id: str
    need_class: str
    route: Any
    route_target: str                     # DETERMINISTIC | EDGE | CAPABLE | LIMITATION
    tier_used: str                        # template | edge | capable
    question: str
    options: Tuple[Tuple[str, str], ...]  # URI order, escape appended by URI
    limitation: bool
    fallback_reason: Optional[str]
    model_flags: Tuple[str, ...]
    attempt: Optional[RenderAttempt]
    edge_invoked: bool
    capable_invoked: bool
    need_class_policy_version: str = NEED_CLASS_POLICY_VERSION


def validated_output(contract: ClarificationContract, raw_text: Optional[str]) -> Tuple[Optional[RenderOutput], Tuple[str, ...]]:
    """Return the model output in URI slot order if the S1 validator accepts it."""
    if raw_text is None:
        return None, ("NO_OUTPUT",)
    result = validate_render(contract, raw_text)
    if not result.valid:
        return None, result.flags
    data = json.loads(raw_text)
    # S5 addition (stricter than the S1 validator, which accepts an empty or
    # whitespace-only question/label): shown text must be non-empty.
    if not data["question"].strip() or any(not str(v).strip() for v in data["labels"].values()):
        return None, result.flags + ("S5-EMPTY-TEXT",)
    order = [key for key, _ in make_render_request(contract).slots]
    return RenderOutput(data["question"], tuple((k, data["labels"][k]) for k in order)), result.flags


def select_wording(contract: ClarificationContract, *, route_wording: RouteWording,
                   edge_renderer: Optional[RendererPort], capable_renderer: Optional[RendererPort],
                   trace_id: Optional[str] = None) -> WordingResult:
    trace = require_trace_id(trace_id) if trace_id is not None else new_trace_id()
    need = classify_need(contract)
    edge_warm = bool(edge_renderer is not None and getattr(edge_renderer, "model_state", lambda: None)() == "loaded")
    route = route_wording(need, edge_warm)
    target = route_target(route)
    template = render_template(contract)
    attempt: Optional[RenderAttempt] = None
    flags: Tuple[str, ...] = ()
    fallback: Optional[str] = None
    chosen, tier = template, "template"
    renderer = {"EDGE": edge_renderer, "CAPABLE": capable_renderer}.get(target)
    if target in ("EDGE", "CAPABLE") and renderer is None:
        fallback = "renderer_unavailable"
    if renderer is not None:
        attempt = renderer.render(make_render_request(contract), contract)
        output, flags = validated_output(contract, attempt.raw_text)
        if output is not None:
            chosen, tier = output, target.lower()
        else:
            fallback = attempt.error or "validator_reject"
    # Fail closed: whatever is shown must pass the validator.
    if not validate_render(contract, chosen).valid:
        chosen, tier, fallback = template, "template", "presented_output_invalid"
    invoked = bool(attempt and attempt.invoked_model)
    return WordingResult(trace, need, route, target, tier, chosen.question, presented_options(contract, chosen),
                         target == "LIMITATION", fallback, flags, attempt,
                         edge_invoked=invoked and target == "EDGE", capable_invoked=invoked and target == "CAPABLE")
