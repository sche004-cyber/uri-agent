"""M33.3-R S6: unified router extension (D2 mode mapping, explicit selection, Edge OFF, G2)."""

from __future__ import annotations

from dataclasses import replace
import itertools

import pytest

from uri_core.core.edge import routing_policy as rp
from uri_core.core.edge.routing_policy import (
    IntelligenceRouteRequest, IntelligenceRoutingDecision, RouteTarget, RoutingInput, WordingNeedClass,
    WorkRole, evaluate_intelligence_route, evaluate_routing, route_clarification_wording,
)
from uri_core.core.edge.runtime_inventory import EdgeRuntimeInventory, RuntimeProfile
from uri_core.core.edge.settings import EdgeSettings

INVENTORY = EdgeRuntimeInventory(runtimes={"lmstudio": RuntimeProfile("lmstudio", frozenset({"qwen3.5-2b"}))})
MODES = ("EDGE_ONLY", "HYBRID", "MAIN_BRAIN_PREFERRED")


def settings(mode="HYBRID", enabled=True, configured=True):
    edge = {"runtime_id": "lmstudio", "model_id": "qwen3.5-2b"} if configured else {"runtime_id": None, "model_id": None}
    return EdgeSettings(intelligence_mode=mode, enabled=enabled, edge=edge)


BOOL_FIELDS = ("capable_available", "deterministic_sufficient", "deterministic_fallback_available",
               "edge_role_qualified", "edge_warm", "allow_edge_cold_load", "edge_sufficient", "resource_admitted")


def all_requests():
    for role, explicit, flags in itertools.product(WorkRole, (None, "claude-selected"),
                                                   itertools.product((False, True), repeat=len(BOOL_FIELDS))):
        yield IntelligenceRouteRequest(role, explicit_model_id=explicit, auto_capable_model_id="qwen3.5-9b",
                                       **dict(zip(BOOL_FIELDS, flags)))


GRID = [(mode, enabled, req) for mode in MODES for enabled in (True, False) for req in all_requests()]


@pytest.mark.parametrize("mode", MODES)
def test_edge_only_never_calls_capable_exhaustive(mode):
    for m, enabled, req in GRID:
        if m != mode:
            continue
        route = evaluate_intelligence_route(settings(m, enabled), INVENTORY, req)
        if m == "EDGE_ONLY":
            assert route.target != RouteTarget.CAPABLE, (req, route)
            assert not route.invokes_capable


def test_edge_off_never_invokes_edge_exhaustive():
    for mode, enabled, req in GRID:
        if enabled:
            continue
        route = evaluate_intelligence_route(settings(mode, enabled), INVENTORY, req)
        assert route.target != RouteTarget.EDGE, (mode, req, route)
        # Edge OFF removes Edge inference only: the Capable Brain stays available outside EDGE_ONLY.
        if (mode != "EDGE_ONLY" and req.role == WorkRole.SUBSTANTIVE and req.capable_available
                and not req.deterministic_sufficient):
            assert route.target == RouteTarget.CAPABLE


def test_unconfigured_or_unqualified_edge_is_never_invoked():
    for mode, enabled, req in GRID:
        route = evaluate_intelligence_route(settings(mode, enabled, configured=False), INVENTORY, req)
        assert route.target != RouteTarget.EDGE
        route = evaluate_intelligence_route(settings(mode, enabled), INVENTORY, replace(req, edge_role_qualified=False))
        assert route.target != RouteTarget.EDGE


def test_no_cold_load_unless_explicitly_allowed():
    for mode, enabled, req in GRID:
        if req.edge_warm or req.allow_edge_cold_load:
            continue
        assert evaluate_intelligence_route(settings(mode, enabled), INVENTORY, req).target != RouteTarget.EDGE


def test_explicit_selection_is_capable_for_substantive_and_never_downgraded():
    for mode, enabled, req in GRID:
        if req.role != WorkRole.SUBSTANTIVE or not req.explicit_model_id or req.deterministic_sufficient:
            continue
        route = evaluate_intelligence_route(settings(mode, enabled), INVENTORY, req)
        assert route.target != RouteTarget.EDGE
        if mode != "EDGE_ONLY" and req.capable_available:
            assert route.target == RouteTarget.CAPABLE and route.model_id == "claude-selected"


def test_g2_supporting_edge_stays_permitted_with_explicit_selection_and_mbp():
    for mode in MODES:
        for explicit in (None, "claude-selected"):
            req = IntelligenceRouteRequest(WorkRole.SUPPORTING, explicit_model_id=explicit, capable_available=True,
                                           edge_role_qualified=True, edge_warm=True, resource_admitted=True)
            assert evaluate_intelligence_route(settings(mode), INVENTORY, req).target == RouteTarget.EDGE


D2_TABLE = [
    # mode, explicit, edge_enabled, edge_sufficient, capable_available, expected target
    ("HYBRID", None, True, True, True, RouteTarget.EDGE),
    ("HYBRID", None, True, False, True, RouteTarget.CAPABLE),
    ("HYBRID", None, False, True, True, RouteTarget.CAPABLE),
    ("HYBRID", None, True, False, False, RouteTarget.LIMITATION),
    ("MAIN_BRAIN_PREFERRED", None, True, True, True, RouteTarget.CAPABLE),
    ("MAIN_BRAIN_PREFERRED", None, True, True, False, RouteTarget.EDGE),
    ("MAIN_BRAIN_PREFERRED", None, False, True, False, RouteTarget.LIMITATION),
    ("HYBRID", "sel", True, True, True, RouteTarget.CAPABLE),
    ("MAIN_BRAIN_PREFERRED", "sel", True, True, True, RouteTarget.CAPABLE),
    ("HYBRID", "sel", True, True, False, RouteTarget.LIMITATION),
    ("EDGE_ONLY", None, True, True, True, RouteTarget.EDGE),
    ("EDGE_ONLY", None, True, False, True, RouteTarget.LIMITATION),
    ("EDGE_ONLY", None, False, True, True, RouteTarget.LIMITATION),
    ("EDGE_ONLY", "sel", True, True, True, RouteTarget.LIMITATION),
]


@pytest.mark.parametrize("mode,explicit,enabled,sufficient,capable,expected", D2_TABLE)
def test_d2_truth_table_substantive(mode, explicit, enabled, sufficient, capable, expected):
    req = IntelligenceRouteRequest(WorkRole.SUBSTANTIVE, explicit_model_id=explicit, auto_capable_model_id="qwen3.5-9b",
                                   capable_available=capable, edge_role_qualified=True, edge_warm=True,
                                   edge_sufficient=sufficient, resource_admitted=True)
    route = evaluate_intelligence_route(settings(mode, enabled), INVENTORY, req)
    assert route.target == expected, route
    assert route.policy_version == rp.ROUTE_POLICY_VERSION


def test_deterministic_first_in_every_mode():
    for mode, enabled, req in GRID:
        if req.deterministic_sufficient:
            assert evaluate_intelligence_route(settings(mode, enabled), INVENTORY, req).target == RouteTarget.DETERMINISTIC


def test_router_is_pure_and_deterministic():
    for mode, enabled, req in GRID[::97]:
        a = evaluate_intelligence_route(settings(mode, enabled), INVENTORY, req)
        b = evaluate_intelligence_route(settings(mode, enabled), INVENTORY, req)
        assert a == b


def test_invalid_role_rejected():
    with pytest.raises(ValueError):
        evaluate_intelligence_route(settings(), INVENTORY, IntelligenceRouteRequest("SUBSTANTIVE"))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("enabled", (True, False))
def test_wording_table_r2_5(mode, enabled):
    base = dict(edge_wording_qualified=True, edge_warm=True, resource_admitted=True, capable_available=True,
                auto_capable_model_id="qwen3.5-9b")
    simple = route_clarification_wording(settings(mode, enabled), INVENTORY, WordingNeedClass.SIMPLE, **base)
    assert simple.target == RouteTarget.DETERMINISTIC
    explain = route_clarification_wording(settings(mode, enabled), INVENTORY, WordingNeedClass.EXPLAIN, **base)
    assert explain.target == (RouteTarget.EDGE if enabled else RouteTarget.DETERMINISTIC)
    cold = route_clarification_wording(settings(mode, enabled), INVENTORY, WordingNeedClass.EXPLAIN,
                                       **{**base, "edge_warm": False})
    assert cold.target == RouteTarget.DETERMINISTIC  # never cold-load to polish wording
    reasoning = route_clarification_wording(settings(mode, enabled), INVENTORY, WordingNeedClass.REASONING, **base)
    assert reasoning.target == (RouteTarget.LIMITATION if mode == "EDGE_ONLY" else RouteTarget.CAPABLE)


def test_explain_with_explicit_selection_still_uses_supporting_edge_not_capable():
    route = route_clarification_wording(settings("MAIN_BRAIN_PREFERRED"), INVENTORY, WordingNeedClass.EXPLAIN,
                                        edge_wording_qualified=True, edge_warm=True, resource_admitted=True,
                                        capable_available=True, explicit_model_id="sel")
    assert route.target == RouteTarget.EDGE
    route = route_clarification_wording(settings("MAIN_BRAIN_PREFERRED"), INVENTORY, WordingNeedClass.EXPLAIN,
                                        edge_wording_qualified=False, edge_warm=True, resource_admitted=True,
                                        capable_available=True, explicit_model_id="sel")
    assert route.target == RouteTarget.DETERMINISTIC  # Capable Brain is never called for cosmetic wording


# --- M33.2 regression: evaluate_routing -------------------------------------

ROUTING_FIELDS = ("explicit_main_brain", "uri_preflight_available", "input_requires_confirmation", "task_complex",
                  "proposal_valid", "reply_valid", "calibration_current", "resource_admitted")


def routing_inputs():
    for flags in itertools.product((False, True), repeat=len(ROUTING_FIELDS)):
        for confidence in (None, 0.5, 0.95):
            yield RoutingInput(calibrated_confidence=confidence, **dict(zip(ROUTING_FIELDS, flags)))


@pytest.mark.parametrize("mode", ("HYBRID", "MAIN_BRAIN_PREFERRED"))
def test_evaluate_routing_unchanged_outside_edge_only(mode):
    for enabled in (True, False):
        for request in routing_inputs():
            s = settings(mode, enabled)
            assert evaluate_routing(s, INVENTORY, request) == rp._evaluate_routing(s, INVENTORY, request)


def test_evaluate_routing_edge_only_never_hands_to_main_brain():
    for enabled in (True, False):
        for request in routing_inputs():
            result = evaluate_routing(settings("EDGE_ONLY", enabled), INVENTORY, request)
            if result.reason_codes == ("uri_preflight",):
                assert result.decision == IntelligenceRoutingDecision.SUPPRESS  # deterministic preflight continues
                continue
            assert result.decision not in (IntelligenceRoutingDecision.ESCALATE, IntelligenceRoutingDecision.SUPPRESS)
            if result.decision == IntelligenceRoutingDecision.LIMITATION:
                assert "edge_only_capable_forbidden" in result.reason_codes
