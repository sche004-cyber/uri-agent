"""Deterministic tests for scripts/governance/uri_state_validator.py.

No LLM involvement, no network dependency. Positive tests exercise the real
canonical docs/governance/URI_STATE.yaml (never mutated by these tests).
Negative tests use small synthetic YAML-subset fixtures, each proving one
specific DCL-* rule fires for the intended reason.
"""

from __future__ import annotations

import copy

import pytest

from scripts.governance.uri_state_validator import (
    UriStateSchemaError,
    validate_file,
    validate_state,
    validate_text,
)
from scripts.governance.uri_state_yaml import UriStateYamlError, parse_uri_state_yaml

CANONICAL_STATE_PATH = "docs/governance/URI_STATE.yaml"


# ---------------------------------------------------------------------------
# Positive tests (VALID-001..004)
# ---------------------------------------------------------------------------


def test_valid_001_current_canonical_state_passes():
    violations = validate_file(CANONICAL_STATE_PATH)
    assert violations == [], [str(v) for v in violations]


def test_valid_002_m33_2_closed_foundation_to_m33_3_continuation_is_valid():
    state = {
        "product_milestones": [
            {
                "id": "M33.2",
                "status": "CLOSED_VERIFIED",
                "architecture_domain": "edge_second_brain",
                "currently_active": False,
                "mutable": False,
            },
            {
                "id": "M33.3",
                "status": "PLANNING_BASIS_FROZEN",
                "continues_architecture_of": "M33.2",
                "architecture_domain": "edge_second_brain",
                "currently_active": False,
                "mutable": True,
            },
        ]
    }
    assert validate_state(state) == []


def test_valid_003_m35_research_and_m35_companion_product_coexist():
    state = {
        "product_milestones": [
            {"id": "M35", "status": "RESERVED_NOT_STARTED", "currently_active": False}
        ],
        "research_experiments": [
            {
                "id": "EXP-M35-URIV1-A0-A9",
                "status": "CLOSED",
                "promoted_to_production": False,
            }
        ],
        "aliases": [
            {"alias": "M35", "resolves_to": "M35", "resolution_status": "CURRENT"},
            {
                "alias": "EXP-M35-URIV1-A0-A9",
                "resolves_to": "EXP-M35-URIV1-A0-A9",
                "resolution_status": "CURRENT",
            },
        ],
    }
    assert validate_state(state) == []


def test_valid_004_legacy_uri_is_reference_only_and_owns_nothing_active():
    state = {
        "aliases": [
            {
                "alias": "LEGACY_URI",
                "resolves_to": "LEGACY_REFERENCE_ONLY",
                "resolution_status": "LEGACY_REFERENCE_ONLY",
                "legacy": True,
            }
        ],
        "product_milestones": [
            {"id": "M40", "status": "RESERVED_NOT_STARTED", "legacy": False, "currently_active": False}
        ],
    }
    assert validate_state(state) == []


# ---------------------------------------------------------------------------
# Negative tests (INVALID-001..009)
# ---------------------------------------------------------------------------


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


def test_invalid_001_two_active_owners_for_edge_yields_dcl001():
    state = {
        "product_milestones": [
            {
                "id": "M40",
                "status": "PLANNING",
                "architecture_domain": "edge_second_brain",
                "currently_active": True,
            },
            {
                "id": "M41",
                "status": "PLANNING",
                "architecture_domain": "edge_second_brain",
                "currently_active": True,
            },
        ]
    }
    violations = validate_state(state)
    assert "DCL-001" in _codes(violations)


def test_invalid_002_research_claims_production_edge_ownership_yields_dcl005():
    state = {
        "research_experiments": [
            {
                "id": "EXP-EDGE-CLAIM",
                "status": "OPEN",
                "architecture_domain": "edge_second_brain",
                "promoted_to_production": False,
            }
        ]
    }
    violations = validate_state(state)
    assert "DCL-005" in _codes(violations)


def test_invalid_003_incompatible_active_plus_closed_yields_dcl002():
    state = {
        "product_milestones": [
            {"id": "M42", "status": "CLOSED_VERIFIED", "currently_active": True}
        ]
    }
    violations = validate_state(state)
    assert "DCL-002" in _codes(violations)


def test_invalid_004_missing_derived_from_target_yields_dcl003():
    state = {
        "product_milestones": [
            {"id": "M43", "status": "PLANNING", "continues_architecture_of": "M999_DOES_NOT_EXIST"}
        ]
    }
    violations = validate_state(state)
    assert "DCL-003" in _codes(violations)


def test_invalid_005_one_current_alias_resolves_to_two_ids_yields_dcl007():
    state = {
        "aliases": [
            {"alias": "M35", "resolves_to": "M35", "resolution_status": "CURRENT"},
            {
                "alias": "M35",
                "resolves_to": "EXP-M35-URIV1-A0-A9",
                "resolution_status": "CURRENT",
            },
        ]
    }
    violations = validate_state(state)
    assert "DCL-007" in _codes(violations)


def test_invalid_006_legacy_uri_claims_active_edge_ownership_yields_dcl009():
    state = {
        "product_milestones": [
            {
                "id": "M44",
                "status": "PLANNING",
                "architecture_domain": "edge_second_brain",
                "legacy": True,
                "currently_active": True,
            }
        ]
    }
    violations = validate_state(state)
    assert "DCL-009" in _codes(violations)


def test_invalid_007_integration_references_nonexistent_component_yields_dcl010():
    state = {
        "integration_events": [
            {"id": "INT-001", "target_component": "URI-DOES-NOT-EXIST"}
        ]
    }
    violations = validate_state(state)
    assert "DCL-010" in _codes(violations)


def test_invalid_008_new_work_uses_forbidden_a3_1_identity_yields_dcl012():
    state = {
        "aliases": [
            {
                "alias": "A3.1",
                "resolves_to": None,
                "resolution_status": "HISTORICAL_FORBIDDEN",
                "forbidden_for_new_work": True,
            }
        ],
        "product_milestones": [{"id": "A3.1", "status": "PLANNING"}],
    }
    violations = validate_state(state)
    assert "DCL-012" in _codes(violations)


def test_invalid_009_product_research_namespace_collision_yields_dcl011():
    state = {
        "product_milestones": [{"id": "M50", "status": "PLANNING"}],
        "research_experiments": [{"id": "M50", "status": "OPEN"}],
    }
    violations = validate_state(state)
    assert "DCL-011" in _codes(violations)


# ---------------------------------------------------------------------------
# Parser round-trip sanity (proves validate_text works on raw YAML-subset
# text, not only on already-parsed dicts — used by INVALID fixtures above
# indirectly via validate_state, and directly here for the text entrypoint).
# ---------------------------------------------------------------------------


def test_validate_text_parses_and_validates_a_minimal_document():
    text = """
product_milestones:
  - id: "M1"
    status: "CLOSED_VERIFIED"
    currently_active: false
"""
    assert validate_text(text) == []


def test_canonical_state_is_never_mutated_by_this_test_module():
    # Defensive: load twice and confirm parsing is pure / side-effect-free.
    from scripts.governance.uri_state_yaml import load_uri_state_yaml

    first = load_uri_state_yaml(CANONICAL_STATE_PATH)
    second = load_uri_state_yaml(CANONICAL_STATE_PATH)
    assert first == second
    # Mutating a returned copy must never affect a fresh reload.
    mutated = copy.deepcopy(first)
    mutated["product_milestones"] = []
    third = load_uri_state_yaml(CANONICAL_STATE_PATH)
    assert third["product_milestones"] != []


# ---------------------------------------------------------------------------
# Audit-regression tests (INVALID-010..020).
#
# Added 2026-09-25 after an independent audit (CONTROL_LAYER_REPAIR_REQUIRED)
# ran adversarial in-memory mutations against the first version of this
# validator/parser and found each of the following passed when it should
# have failed. Each test below reproduces the audit's specific mutation and
# asserts the fix now catches it.
# ---------------------------------------------------------------------------


def test_invalid_010_new_active_claimant_against_closed_sole_owner_yields_dcl001():
    # Reproduces: "a new active claimant to edge_second_brain passed while
    # the closed M33.2 entry still asserted sole architecture ownership."
    state = {
        "product_milestones": [
            {
                "id": "M33.2",
                "status": "CLOSED_VERIFIED",
                "architecture_domain": "edge_second_brain",
                "currently_active": False,
            },
            {
                "id": "M33.3",
                "status": "PLANNING_BASIS_FROZEN",
                "continues_architecture_of": "M33.2",
                "architecture_domain": "edge_second_brain",
                "currently_active": False,
            },
            {
                # Unrelated new claimant, NOT connected via continues_architecture_of.
                "id": "M40",
                "status": "PLANNING",
                "architecture_domain": "edge_second_brain",
                "currently_active": True,
            },
        ]
    }
    violations = validate_state(state)
    assert "DCL-001" in _codes(violations)


def test_invalid_011_current_bare_arn_alias_yields_dcl007():
    # Reproduces: "adding a current ARN -> ARN.1 alias passed" despite the
    # AMBIGUOUS_BARE_ALIAS_FORBIDDEN collision guard on the same alias string.
    state = {
        "aliases": [
            {
                "alias": "ARN",
                "resolves_to": None,
                "resolution_status": "AMBIGUOUS_BARE_ALIAS_FORBIDDEN",
            },
            {
                "alias": "ARN",
                "resolves_to": "ARN.1",
                "resolution_status": "CURRENT",
            },
        ],
        "product_milestones": [{"id": "ARN.1", "status": "CLOSED_VERIFIED"}],
    }
    violations = validate_state(state)
    assert "DCL-007" in _codes(violations)


def test_invalid_012_current_alias_target_absent_from_any_section_yields_dcl003():
    # Reproduces: "A current alias aimed at a nonexistent ID passed."
    state = {
        "aliases": [
            {
                "alias": "EXP-GHOST",
                "resolves_to": "EXP-GHOST",
                "resolution_status": "CURRENT",
            }
        ]
    }
    violations = validate_state(state)
    assert "DCL-003" in _codes(violations)


def test_invalid_013_targetless_integration_event_yields_dcl010():
    # Reproduces: "an authorized event with no target passes."
    state = {"integration_events": [{"id": "INT-001"}]}
    violations = validate_state(state)
    assert "DCL-010" in _codes(violations)


def test_invalid_014_bare_qualification_override_without_justification_yields_dcl010():
    # Reproduces: "a bare qualification_override: true bypasses ineligibility."
    state = {
        "reusable_components": [{"id": "URI-Ghost", "status": "NOT_STARTED"}],
        "integration_events": [
            {
                "id": "INT-002",
                "target_component": "URI-Ghost",
                "qualification_override": True,
            }
        ],
    }
    violations = validate_state(state)
    assert "DCL-010" in _codes(violations)


def test_invalid_015_legacy_continuation_of_active_work_yields_dcl009():
    # Reproduces: "legacy as active continuation passes."
    state = {
        "product_milestones": [
            {"id": "M50", "status": "PLANNING", "legacy": True},
            {
                "id": "M51",
                "status": "PLANNING",
                "currently_active": True,
                "continues_architecture_of": "M50",
            },
        ]
    }
    violations = validate_state(state)
    assert "DCL-009" in _codes(violations)


def test_invalid_016_legacy_domain_claim_without_currently_active_yields_dcl009():
    # Reproduces: "legacy ownership without currently_active: true... passes."
    state = {
        "product_milestones": [
            {
                "id": "M52",
                "status": "PLANNING",
                "legacy": True,
                "architecture_domain": "some_domain",
                "currently_active": False,
            }
        ]
    }
    violations = validate_state(state)
    assert "DCL-009" in _codes(violations)


def test_invalid_017_distributable_without_portability_evidence_yields_dcl005():
    # Reproduces: "changing a component to DISTRIBUTABLE without portability
    # evidence passed."
    state = {
        "reusable_components": [
            {
                "id": "URI-Ghost",
                "status": "DISTRIBUTABLE",
                "cross_agent_portable": False,
                "portability_validated_via": None,
            }
        ]
    }
    violations = validate_state(state)
    assert "DCL-005" in _codes(violations)


def test_invalid_018_a3_1_current_alias_reuse_yields_dcl012():
    # Reproduces: "an added current alias named A3.1 passed."
    state = {
        "aliases": [
            {
                "alias": "A3.1",
                "resolves_to": None,
                "resolution_status": "HISTORICAL_FORBIDDEN",
                "forbidden_for_new_work": True,
            },
            {
                "alias": "A3.1",
                "resolves_to": "M60",
                "resolution_status": "CURRENT",
            },
        ],
        "product_milestones": [{"id": "M60", "status": "PLANNING"}],
    }
    violations = validate_state(state)
    assert "DCL-012" in _codes(violations)


def test_invalid_019_arbitrary_m_prefixed_id_yields_dcl011():
    # Reproduces: "Namespace validation also accepts an arbitrary product ID
    # such as Mwhatever because it checks only the initial M."
    state = {"product_milestones": [{"id": "Mwhatever", "status": "PLANNING"}]}
    violations = validate_state(state)
    assert "DCL-011" in _codes(violations)


def test_invalid_020_self_declared_promotion_without_integration_evidence_yields_dcl005():
    # Reproduces: "a self-declared promoted_to_production: true is not tied
    # to an integration authorization."
    state = {
        "research_experiments": [
            {
                "id": "EXP-GHOST-PROMOTED",
                "status": "OPEN",
                "promoted_to_production": True,
                # No integration_event_ref, and no matching integration_events entry.
            }
        ]
    }
    violations = validate_state(state)
    assert "DCL-005" in _codes(violations)


# ---------------------------------------------------------------------------
# Parser/schema fail-closed regression tests.
# ---------------------------------------------------------------------------


def test_duplicate_top_level_key_fails_closed():
    text = """
product_milestones:
  - id: "M1"
    status: "PLANNING"
product_milestones:
  - id: "M2"
    status: "PLANNING"
"""
    with pytest.raises(UriStateYamlError):
        parse_uri_state_yaml(text)


def test_unconsumed_trailing_content_fails_closed():
    # Inconsistent indentation that leaves a line unparsed by the top-level
    # mapping parser must raise, not silently drop content.
    text = """
product_milestones:
  - id: "M1"
    status: "PLANNING"
   stray_bad_indent: "x"
"""
    with pytest.raises(UriStateYamlError):
        parse_uri_state_yaml(text)


def test_malformed_quoted_scalar_fails_closed():
    text = """
product_milestones:
  - id: "M1
    status: "PLANNING"
"""
    with pytest.raises(UriStateYamlError):
        parse_uri_state_yaml(text)


def test_unsupported_flow_collection_fails_closed():
    text = """
product_milestones:
  - id: "M1"
    status: "PLANNING"
    tags: [a, b]
"""
    with pytest.raises(UriStateYamlError):
        parse_uri_state_yaml(text)


def test_empty_flow_list_parses_as_empty_list():
    text = """
integration_events: []
corrections: []
"""
    state = parse_uri_state_yaml(text)
    assert state["integration_events"] == []
    assert state["corrections"] == []
    assert validate_state(state) == []


def test_non_list_section_fails_closed_as_schema_error():
    state = {"product_milestones": "not a list"}
    with pytest.raises(UriStateSchemaError):
        validate_state(state)


def test_non_dict_item_in_section_fails_closed_as_schema_error():
    state = {"product_milestones": ["not a dict"]}
    with pytest.raises(UriStateSchemaError):
        validate_state(state)


# ---------------------------------------------------------------------------
# Round-2 audit-regression tests (INVALID-021..023).
#
# Added 2026-09-25 after a second independent audit again returned
# CONTROL_LAYER_REPAIR_REQUIRED, this time against the round-1 repair, with
# three specific blocking adversarial mutations that still passed. Each
# test below reproduces the exact mutation and asserts the fix now catches
# it.
# ---------------------------------------------------------------------------


def test_invalid_021_two_active_owners_within_one_connected_lineage_yields_dcl001():
    # Reproduces: "I added two active milestones in memory, each in the same
    # Edge lineage; validation returned PASS." Connectivity is not enough —
    # cardinality (at most one currently_active per domain) must hold even
    # within a single connected lineage.
    state = {
        "product_milestones": [
            {
                "id": "M33.2",
                "status": "CLOSED_VERIFIED",
                "architecture_domain": "edge_second_brain",
                "currently_active": True,
            },
            {
                "id": "M33.3",
                "status": "PLANNING_BASIS_FROZEN",
                "continues_architecture_of": "M33.2",
                "architecture_domain": "edge_second_brain",
                "currently_active": True,
            },
        ]
    }
    violations = validate_state(state)
    assert "DCL-001" in _codes(violations)


def test_invalid_022_current_alias_with_null_target_yields_dcl003():
    # Reproduces: '{"alias": "EXP-ORPHAN", "resolution_status": "CURRENT",
    # "resolves_to": null}' returning PASS.
    state = {
        "aliases": [
            {"alias": "EXP-ORPHAN", "resolution_status": "CURRENT", "resolves_to": None}
        ]
    }
    violations = validate_state(state)
    assert "DCL-003" in _codes(violations)


def test_invalid_023_promotion_citing_unrelated_integration_event_yields_dcl005():
    # Reproduces: "research promotion referencing an unrelated INT-* event"
    # passing — the integration event exists and is resolvable, but it
    # authorizes a *different* experiment/component/milestone, not this one.
    state = {
        "research_experiments": [
            {
                "id": "EXP-REAL-WORK",
                "status": "OPEN",
                "promoted_to_production": True,
                "integration_event_ref": "INT-001",
            }
        ],
        "integration_events": [
            {
                "id": "INT-001",
                "target_experiment": "EXP-SOME-OTHER-EXPERIMENT",
                "target_component": "URI-Unrelated",
            }
        ],
    }
    violations = validate_state(state)
    assert "DCL-005" in _codes(violations)


def test_valid_005_lineage_continuation_with_predecessor_deactivated_is_valid():
    # The correct shape of a continuation transition: the predecessor's
    # currently_active flips to false before/when the continuation's flips
    # to true. Only one active owner at a time, connected lineage — passes.
    state = {
        "product_milestones": [
            {
                "id": "M33.2",
                "status": "CLOSED_VERIFIED",
                "architecture_domain": "edge_second_brain",
                "currently_active": False,
            },
            {
                "id": "M33.3",
                "status": "PLANNING_BASIS_FROZEN",
                "continues_architecture_of": "M33.2",
                "architecture_domain": "edge_second_brain",
                "currently_active": True,
            },
        ]
    }
    assert validate_state(state) == []
