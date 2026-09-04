"""
Skill Router V1 — deterministic policy/decision layer.

Pipeline position
------------------
User Request -> ContextBudget -> Skill Evaluator -> Skill Router -> (future)
Model Reasoning Gateway -> Orchestrator -> URI authorization/approval -> execution

Contract
--------
* Consumes Skill Evaluator results (and optional ContextBudget metadata).
* Applies URI policy before any capability can be forwarded.
* Distinguishes URI-native capabilities from approved Hermes skills.
* Rejects unapproved Hermes skills, never forwards them downstream.
* Applies relevance and confidence thresholds.
* Produces deterministic, side-effect-free routing decisions.
* Supports one of:
    - single selected capability
    - ordered candidates (multi-candidate ranking)
    - clarification_required (ask the user)
    - no_suitable_capability (capability gap)
* Never executes tools, never invokes Hermes, never calls external APIs/models,
  and never grants authorization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------

# URI-owned capability sources that bypass the Hermes allow-list.
URI_NATIVE_SOURCES = frozenset({
    "uri_tool",
    "uri_core",
    "uri_builtin",
})

# Categories that represent URI-owned capabilities.
URI_NATIVE_CAPABILITY_CATEGORIES = frozenset({
    "uri_core_capability",
})

# Categories that may come from Hermes and therefore require allow-list
# approval unless the source is explicitly URI-native.
# (on_demand_skill, integration, development, skill_optimization can all
# be either URI-owned or Hermes-owned depending on their source.)
HERTES_FACING_CATEGORIES = frozenset({
    "on_demand_skill",
    "integration",
    "development",
    "skill_optimization",
})

# Default policy knobs.
DEFAULT_MIN_CONFIDENCE = 0.25          # minimum routing confidence to forward
DEFAULT_MIN_EVAL_SCORE = 10.0          # minimum evaluator score to consider
DEFAULT_PREFER_URI_NATIVE = True       # URI-native preference flag
DEFAULT_REQUIRE_HERMES_ALLOWLIST = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_uri_native(item: Dict[str, Any]) -> bool:
    """True when the capability is owned by URI and bypasses Hermes policy."""
    source = item.get("source", "")
    category = item.get("category", "")
    return source in URI_NATIVE_SOURCES or category in URI_NATIVE_CAPABILITY_CATEGORIES


def _confidence_from_eval_score(
    eval_score: float,
    best_possible: float = 100.0,
) -> float:
    """Round-trip evaluator score into a 0..1 confidence for policy decisions."""
    if best_possible <= 0:
        return 0.0
    return max(0.0, min(1.0, eval_score / best_possible))


def _preferred_reason(name: str, uri_native: bool, prefer_uri_native: bool) -> str:
    """Reason fragment explaining URI-native preference status."""
    if uri_native and prefer_uri_native:
        return f"URI-native capability '{name}' (preferred)"
    elif uri_native:
        return f"URI-native capability '{name}'"
    elif prefer_uri_native:
        return f"Hermes/optional capability '{name}' (lower URI preference)"
    else:
        return f"Capability '{name}'"


def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow defensive copy with a normalized name key."""
    if not isinstance(item, dict):
        return {}
    return {
        "name": (item.get("name") or "").strip() or "<unknown>",
        "normalized_name": (item.get("normalized_name") or "").strip().lower(),
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "purpose": item.get("purpose", ""),
        "execution_risk": item.get("execution_risk", "unknown"),
        "runtime_facing": bool(item.get("runtime_facing", False)),
        "model_facing": bool(item.get("model_facing", False)),
        "invocation_conditions": list(item.get("invocation_conditions") or []),
        "integration_status": item.get("integration_status", ""),
        "hermes_should_handle": bool(item.get("hermes_should_handle", False)),
        "_eval_score": float(item.get("_eval_score", 0.0)),
        # Distinguishes "the Skill Evaluator explicitly scored this 0.0"
        # from "the Skill Evaluator never annotated an _eval_score at
        # all" (e.g. SkillEvaluatorV1.evaluate_from_context_budget()
        # does not currently annotate it). Both currently score 0.0
        # here, but they are not the same condition: the latter is an
        # upstream contract gap, not a relevance judgement, and should
        # be visible in the routing decision rather than silently
        # indistinguishable from a genuinely low score.
        "_eval_score_present": "_eval_score" in item,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class SkillRouterV1:
    """
    Deterministic skill router that consumes Skill Evaluator output and
    produces a policy-bound routing decision.

    It is a pure decision layer: it does not execute, authorize, or contact
    any external system. Downstream consumers (Orchestrator, approval, etc.)
    retain all authority.
    """

    def __init__(
        self,
        *,
        hermes_allowlist: Optional[List[str]] = None,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        min_eval_score: float = DEFAULT_MIN_EVAL_SCORE,
        prefer_uri_native: bool = DEFAULT_PREFER_URI_NATIVE,
        require_hermes_allowlist: bool = DEFAULT_REQUIRE_HERMES_ALLOWLIST,
        max_candidates_returned: int = 20,
        confidence_scale_best_score: float = 100.0,
    ):
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be in [0, 1]")
        if min_eval_score < 0:
            raise ValueError("min_eval_score must be >= 0")
        if max_candidates_returned < 1:
            raise ValueError("max_candidates_returned must be >= 1")

        self.hermes_allowlist = list(hermes_allowlist or [])
        self.min_confidence = float(min_confidence)
        self.min_eval_score = float(min_eval_score)
        self.prefer_uri_native = bool(prefer_uri_native)
        self.require_hermes_allowlist = bool(require_hermes_allowlist)
        self.max_candidates_returned = int(max_candidates_returned)
        self.confidence_scale_best_score = float(confidence_scale_best_score)

    # ------------------------------------------------------------------
    # Primary routing entrypoint
    # ------------------------------------------------------------------

    def route(
        self,
        evaluator_result: Dict[str, Any],
        *,
        context_budget_output: Optional[Dict[str, Any]] = None,
        user_request: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Route a single user request through URI policy.

        Parameters
        ----------
        evaluator_result:
            Output from SkillEvaluatorV1.evaluate(...) (or equivalent).
        context_budget_output:
            Optional original ContextBudget output used for diagnostics only.
        user_request:
            Original user request string, propagated into the decision for
            traceability.

        Returns
        -------
        Dict with routing_state in one of:
            selected, ordered_candidates, clarification_required,
            no_suitable_capability
        """
        if not isinstance(evaluator_result, dict):
            return self._no_suitable_capability("Invalid evaluator_result: not a dict.")

        candidates = self._extract_candidates(evaluator_result)
        request_text = self._extract_request_text(evaluator_result, user_request)

        # Pass normalized copy so downstream helpers cannot mutate originals.
        scored = self._score_candidates(candidates, evaluator_result)

        accepted = []
        rejected = []
        decisions = []

        for item, meta in scored:
            explain = self._evaluate_candidate(item, meta, evaluator_result)
            decisions.append(explain)
            if explain["accepted"]:
                accepted.append((item, explain))
            else:
                rejected.append((item, explain))

        routing_state, selected, primary_reason = self._choose_routing_state(
            accepted=accepted,
            rejected=rejected,
            request_text=request_text,
        )

        eval_score_missing_count = sum(
            1 for explain in decisions if explain.get("eval_score_missing")
        )

        return {
            "routing_state": routing_state,
            "decision_at": self._utc_now(),
            "request": {
                "user_request": request_text,
                "candidate_count": len(candidates),
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
            },
            "eval_score_missing_count": eval_score_missing_count,
            "selected_candidates": selected,
            "selected": selected[0] if selected else None,
            "reason": primary_reason,
            "policy_applied": {
                "min_confidence": self.min_confidence,
                "min_eval_score": self.min_eval_score,
                "prefer_uri_native": self.prefer_uri_native,
                "require_hermes_allowlist": self.require_hermes_allowlist,
                "uri_native_sources": sorted(URI_NATIVE_SOURCES),
                "uri_native_categories": sorted(URI_NATIVE_CAPABILITY_CATEGORIES),
                "hermes_allowlist": sorted(self.hermes_allowlist),
            },
            "uri_native_allowlist_applied": True,
            "hermes_allowlist_applied": True,
            "decisions": decisions,
            "rejected": [
                {"candidate": item, "explain": explain}
                for item, explain in rejected
            ],
            "context_used": {
                "evaluator_result_keys": sorted(evaluator_result.keys()),
                "context_budget_present": isinstance(context_budget_output, dict),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_candidates(self, evaluator_result: Dict[str, Any]) -> List[Dict]:
        raw = evaluator_result.get("candidates")
        if not isinstance(raw, list):
            return []
        return [_normalize_item(item) for item in raw if isinstance(item, dict)]

    def _extract_request_text(
        self,
        evaluator_result: Dict[str, Any],
        user_request: Optional[str],
    ) -> str:
        if isinstance(user_request, str) and user_request.strip():
            return user_request.strip()
        req = evaluator_result.get("request")
        if isinstance(req, dict):
            t = req.get("user_request")
            if isinstance(t, str) and t.strip():
                return t.strip()
        return ""

    def _score_candidates(
        self,
        candidates: List[Dict],
        evaluator_result: Dict[str, Any],
    ) -> List[Tuple[Dict, Dict[str, Any]]]:
        """
        Attach per-candidate routing metadata: eval_score, confidence, uri_native.
        Order is preserved from the evaluator (already ranked by relevance).
        """
        out = []
        for item in candidates:
            meta = {
                "eval_score": float(item.get("_eval_score", 0.0)),
                "eval_score_missing": not item.get(
                    "_eval_score_present", True
                ),
                "confidence": _confidence_from_eval_score(
                    item.get("_eval_score", 0.0),
                    self.confidence_scale_best_score,
                ),
                "uri_native": _is_uri_native(item),
                "name": item.get("name", ""),
                "category": item.get("category", ""),
                "source": item.get("source", ""),
            }
            out.append((item, meta))
        return out

    def _evaluate_candidate(
        self,
        item: Dict[str, Any],
        meta: Dict[str, Any],
        evaluator_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply URI policy to a single candidate and return an explanation
        dict including an 'accepted' boolean.
        """
        name = meta["name"] or item.get("name", "<unknown>")
        reasons: List[str] = []
        accepted = True

        # 1) Must have enough evaluator signal.
        if meta["eval_score"] < self.min_eval_score:
            accepted = False
            if meta["eval_score_missing"]:
                reasons.append(
                    f"candidate '{name}' has no _eval_score annotation from "
                    "the Skill Evaluator (treated as 0.0); this indicates an "
                    "upstream evaluator contract gap, not a low-relevance "
                    "judgement"
                )
            else:
                reasons.append(
                    f"eval score {meta['eval_score']:.1f} below min_eval_score {self.min_eval_score:.1f}"
                )

        # 2) Confidence floor.
        if meta["confidence"] < self.min_confidence:
            if accepted:
                accepted = False
            reasons.append(
                f"confidence {meta['confidence']:.2f} below min_confidence {self.min_confidence:.2f}"
            )

        # 3) Hermes allow-list gate.
        hermes_policy_applied = False
        if not meta["uri_native"] and self.require_hermes_allowlist:
            hermes_policy_applied = True
            allowed = name in self.hermes_allowlist or item.get("name", "") in self.hermes_allowlist
            if not allowed:
                accepted = False
                reasons.append(
                    f"Hermes capability '{name}' not in URI-approved allow-list"
                )

        # 4) Build final reason.
        if accepted:
            reason = _preferred_reason(name, meta["uri_native"], self.prefer_uri_native)
            if meta["uri_native"] and self.prefer_uri_native:
                uri_preference_note = "URI-native capability (preferred)"
            elif not meta["uri_native"] and self.prefer_uri_native:
                uri_preference_note = "Hermes/optional capability (lower URI preference)"
            else:
                uri_preference_note = ""
        else:
            reason = "; ".join(reasons) if reasons else f"Capability '{name}' rejected"
            uri_preference_note = ""

        return {
            "candidate": item,
            "name": name,
            "uri_native": meta["uri_native"],
            "eval_score": meta["eval_score"],
            "eval_score_missing": meta["eval_score_missing"],
            "confidence": meta["confidence"],
            "source": meta["source"],
            "category": meta["category"],
            "accepted": bool(accepted),
            "reason": reason,
            "hermes_allowlist_check_applied": hermes_policy_applied,
            "uri_native_preference_applied": bool(uri_preference_note),
            "uri_preference_note": uri_preference_note,
        }

    def _choose_routing_state(
        self,
        accepted: List[Tuple[Dict, Dict[str, Any]]],
        rejected: List[Tuple[Dict, Dict[str, Any]]],
        request_text: str,
    ) -> Tuple[str, List[Dict], str]:
        """
        Decide routing_state and selected candidates from the accepted set.

        States:
          * selected            — one primary capability chosen
          * ordered_candidates  — multiple candidates returned in policy order
          * clarification_required — no acceptable candidate; ask the user
          * no_suitable_capability — no candidates reached the evaluator
        """
        if not accepted:
            # Distinguish: did we even have candidates to consider?
            if not rejected and not accepted:
                return (
                    "no_suitable_capability",
                    [],
                    "No capabilities were provided by the Skill Evaluator for this request.",
                )
            # We had candidates but policy rejected all.
            top_rejected_reason = rejected[0][1]["reason"] if rejected else "No acceptable candidate."
            return (
                "clarification_required",
                [],
                "No capability met URI policy thresholds; user clarification recommended. "
                f"Leading rejection: {top_rejected_reason}",
            )

        # Sort accepted candidates deterministically:
        #  1) uri_native first when prefer_uri_native is on
        #  2) higher confidence
        #  3) higher eval score
        #  4) name (stable tie-breaker)
        def sort_key(p):
            item, explain = p
            uri_pref = 0 if (explain["uri_native"] and self.prefer_uri_native) else 1
            return (
                uri_pref,
                -explain["confidence"],
                -explain["eval_score"],
                (explain["name"] or "").lower(),
            )

        accepted_sorted = sorted(accepted, key=sort_key)
        selected_candidates = [
            {
                "name": explain["name"],
                "uri_native": explain["uri_native"],
                "eval_score": explain["eval_score"],
                "confidence": explain["confidence"],
                "source": explain["source"],
                "category": explain["category"],
                "policy_reason": explain["reason"],
            }
            for _, explain in accepted_sorted[: self.max_candidates_returned]
        ]

        primary = accepted_sorted[0][1]

        if len(selected_candidates) == 1:
            state = "selected"
            reason = (
                f"Selected URI-native capability '{primary['name']}'"
                if primary["uri_native"]
                else f"Selected approved Hermes capability '{primary['name']}'"
            )
            if primary["uri_preference_note"]:
                reason += f" ({primary['uri_preference_note']})"
            reason += f". {primary['reason']}"
            return state, selected_candidates, reason

        # Multiple accepted candidates -> ordered list, still name a primary.
        state = "ordered_candidates"
        reason = (
            f"Multiple capabilities acceptable; primary recommendation "
            f"'{primary['name']}'. {primary['reason']}"
        )
        return state, selected_candidates, reason

    def _no_suitable_capability(self, reason: str) -> Dict[str, Any]:
        return {
            "routing_state": "no_suitable_capability",
            "decision_at": self._utc_now(),
            "request": {"user_request": "", "candidate_count": 0, "accepted_count": 0, "rejected_count": 0},
            "eval_score_missing_count": 0,
            "selected_candidates": [],
            "selected": None,
            "reason": reason,
            "policy_applied": {
                "min_confidence": self.min_confidence,
                "min_eval_score": self.min_eval_score,
                "prefer_uri_native": self.prefer_uri_native,
                "require_hermes_allowlist": self.require_hermes_allowlist,
                "uri_native_sources": sorted(URI_NATIVE_SOURCES),
                "uri_native_categories": sorted(URI_NATIVE_CAPABILITY_CATEGORIES),
                "hermes_allowlist": sorted(self.hermes_allowlist),
            },
            "uri_native_allowlist_applied": True,
            "hermes_allowlist_applied": True,
            "decisions": [],
            "rejected": [],
            "context_used": {"evaluator_result_keys": [], "context_budget_present": False},
        }

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Convenience helpers for consumers
# ---------------------------------------------------------------------------

def is_uri_native(item: Dict[str, Any]) -> bool:
    """Standalone predicate matching SkillRouterV1 internal policy."""
    return _is_uri_native(item)


def hermes_is_approved(
    item: Dict[str, Any],
    allowlist: List[str],
    require_allowlist: bool = True,
) -> bool:
    """
    Return True if a non-URI-native capability would pass the Hermes
    allow-list gate under the router's default policy.
    """
    if not require_allowlist:
        return True
    if _is_uri_native(item):
        return True
    name = (item.get("name") or "").strip()
    return name in allowlist


def routing_state_description(state: str) -> str:
    return {
        "selected": "One capability selected for routing.",
        "ordered_candidates": "Multiple capabilities ordered by policy.",
        "clarification_required": "No capability met policy; ask the user.",
        "no_suitable_capability": "No capabilities were presented or all were rejected.",
    }.get(state, state)


if __name__ == "__main__":
    # Tiny deterministic self-check — not a substitute for the test suite.
    r = SkillRouterV1(hermes_allowlist=["pdf-reader"])
    eval_result = {
        "evaluated_at": "2026-01-01T00:00:00+00:00",
        "request": {"user_request": "read this pdf", "signal_word_count": 2, "intent_present": True},
        "candidates": [
            {
                "name": "pdf-reader",
                "normalized_name": "pdf-reader",
                "source": "hermes_builtin_skill",
                "category": "on_demand_skill",
                "purpose": "read and extract text from PDF files",
                "execution_risk": "variable",
                "model_facing": True,
                "runtime_facing": False,
                "invocation_conditions": [],
                "integration_status": "not_applicable",
                "hermes_should_handle": False,
                "_eval_score": 40.0,
            },
            {
                "name": "draft_institutional_note",
                "normalized_name": "draft_institutional_note",
                "source": "uri_tool",
                "category": "uri_core_capability",
                "purpose": "draft an administrative noting document",
                "execution_risk": "controlled",
                "model_facing": True,
                "runtime_facing": True,
                "invocation_conditions": [],
                "integration_status": "integrated",
                "hermes_should_handle": False,
                "_eval_score": 15.0,
            },
        ],
        "best_match": None,
        "routing_recommendation": {"destination": "hermes", "capability": "pdf-reader"},
        "classification_summary": {},
        "has_suitable_capability": True,
        "capability_gap": False,
    }
    decision = r.route(eval_result, user_request="read this pdf")
    print("routing_state:", decision["routing_state"])
    print("selected:", decision["selected"])
    print("reason:", decision["reason"])
    print("policy_applied:", decision["policy_applied"])
