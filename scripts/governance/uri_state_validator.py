"""Deterministic validator for docs/governance/URI_STATE.yaml.

No LLM. No network dependency. Dependency-light: uses only
uri_state_yaml.py (a hand-rolled parser for the restricted YAML subset this
file uses), never a third-party YAML library.

Usage:
    python scripts/governance/uri_state_validator.py [path/to/URI_STATE.yaml]

Exit status 0 = valid (no DCL violations). Exit status 1 = invalid (one or
more DCL violations printed, one per line, as "DCL-NNN: <message>"), or a
STATE_ERROR (parse failure or wrong-typed section) printed to stderr.

Each rule function takes the fully parsed state dict and returns a list of
Violation objects (empty if the rule is satisfied). This module intentionally
validates only clearly defined, machine-checkable current-state fields — it
does not attempt to parse or evaluate free-text prose/history sections.

REPAIR NOTE (2026-09-25, after independent audit CONTROL_LAYER_REPAIR_REQUIRED):
the original version of this module was fail-open in several ways an
adversarial in-memory mutation test exposed: a non-list section silently
validated as empty, DCL-001 counted only `currently_active` claimants and
missed a new active claimant conflicting with a closed sole-owner entry,
DCL-003/007/012 did not validate alias resolution targets or catch a
forbidden alias reused as a live current resolution, DCL-005 accepted a
self-declared `promoted_to_production: true` with no integration evidence,
DCL-006 did not inspect the nested `rar_identity_map.research_lines` frozen
markers, DCL-009 missed a legacy entry claiming a domain while not
`currently_active` and missed legacy-as-continuation-target, DCL-010 let an
integration event with no target pass and let a bare `qualification_override`
bypass ineligibility without justification, and DCL-011 accepted any
`M`-prefixed string as a valid product-milestone id. All of these are fixed
below; see tests/governance/test_uri_state_validator.py's INVALID-010..020
fixtures for one regression test per fixed defect.

REPAIR NOTE 2 (2026-09-25, same day, second independent audit, again
CONTROL_LAYER_REPAIR_REQUIRED): the round-1 repair above still had three
blocking gaps: DCL-001 rejected a disconnected active claimant but still
allowed two `currently_active: true` entries within one *connected*
lineage (e.g. M33.2 and M33.3 both active at once) — cardinality (at most
one active owner per domain) was not enforced independently of
connectivity; DCL-003 did not reject a `CURRENT` alias whose `resolves_to`
is null; DCL-005 accepted an `integration_event_ref` that resolved to a
real `integration_events` entry but did not verify that entry actually
authorized *this* experiment (it could cite an unrelated event). All three
are fixed below: DCL-001 now checks active-count-per-domain independently
of the connected-component check; DCL-003 now rejects a `CURRENT` alias
with a null/empty `resolves_to`; DCL-005 now requires the cited integration
event's `target_experiment` to equal the promoted experiment's own id. See
tests/governance/test_uri_state_validator.py's INVALID-021..023 fixtures.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uri_state_yaml import UriStateYamlError, load_uri_state_yaml, parse_uri_state_yaml  # noqa: E402


class UriStateSchemaError(ValueError):
    """Raised when a section of the parsed document has the wrong type.

    Fails closed: a section that exists but is not a list (e.g. a duplicate
    top-level key error the parser already rejects, or a hand-edited
    mapping where a list was required) must never be silently treated as an
    empty, passing section.
    """


@dataclass(frozen=True)
class Violation:
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


# ---------------------------------------------------------------------------
# Section / namespace configuration
# ---------------------------------------------------------------------------

SECTION_PREFIXES = {
    "product_milestones": "M",
    "research_experiments": "EXP-",
    "integration_events": "INT-",
    "reusable_components": "URI-",
}

# Governed identities that are legitimately not Mxx-numbered but still live
# in product_milestones (e.g. a batch under a paused parent milestone).
PRODUCT_NAMESPACE_EXCEPTIONS = {"ARN.1"}

# Strict Mxx syntax: "M" + digits, optionally ".digits" up to two levels
# (e.g. "M33", "M33.2", "M32.1.1"). Rejects "Mwhatever".
_PRODUCT_ID_RE = re.compile(r"^M\d+(\.\d+){0,2}$")

INTEGRATION_INELIGIBLE_COMPONENT_STATUSES = {"NOT_STARTED"}

# Alias resolution statuses that mean "this alias must never be a live
# current resolution" — used by both the DCL-007 collision-guard check and
# the DCL-012 forbidden-reuse check, each guarding a distinct failure mode.
_BARE_COLLISION_GUARD_STATUS = "AMBIGUOUS_BARE_ALIAS_FORBIDDEN"
_HISTORICAL_FORBIDDEN_STATUS = "HISTORICAL_FORBIDDEN"

_COMMIT_LIKE_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)


def _is_closed_like_status(status: str) -> bool:
    """True for a status that represents genuinely closed/frozen-immutable work.

    Deliberately narrow: matches 'CLOSED*' and a bare/leading 'FROZEN'
    status, but NOT a status like 'PLANNING_BASIS_FROZEN' where 'FROZEN'
    describes a frozen *plan* for work that has not started and remains
    mutable (e.g. M33.3) rather than closed/immutable production work.
    """

    upper = status.upper()
    return upper.startswith("CLOSED") or upper == "FROZEN" or upper.startswith("FROZEN_")


def _entries(state: dict, section: str) -> list[dict]:
    """Fail closed: a present-but-wrong-typed section is a schema error,
    never a silently empty (and therefore always-passing) section."""

    value = state.get(section)
    if value is None:
        return []
    if not isinstance(value, list):
        raise UriStateSchemaError(
            f"Section '{section}' must be a list, got {type(value).__name__}: {value!r}"
        )
    for item in value:
        if not isinstance(item, dict):
            raise UriStateSchemaError(
                f"Section '{section}' must contain only mapping entries, "
                f"found {type(item).__name__}: {item!r}"
            )
    return value


def _all_known_ids(state: dict) -> set[str]:
    ids: set[str] = set()
    for section in SECTION_PREFIXES:
        for entry in _entries(state, section):
            eid = entry.get("id")
            if eid:
                ids.add(eid)
    return ids


_RELATIONSHIP_FIELDS = (
    "continues_architecture_of",
    "derived_from",
    "supersedes",
    "feeds_into",
)


# ---------------------------------------------------------------------------
# DCL-001 — Multiple active production owners
#
# A domain must resolve to a single connected lineage (via the relationship
# fields). It is a violation for a currently_active claimant to exist in a
# domain that also has ANY other claimant (active or not — e.g. a closed
# sole-owner predecessor) outside that claimant's own connected component.
# ---------------------------------------------------------------------------

def check_dcl001(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    claimants: list[dict] = []
    for section in ("product_milestones", "reusable_components"):
        for entry in _entries(state, section):
            if entry.get("architecture_domain"):
                claimants.append(entry)

    by_domain: dict[str, list[dict]] = {}
    for entry in claimants:
        by_domain.setdefault(entry["architecture_domain"], []).append(entry)

    for domain, entries in by_domain.items():
        id_to_entry = {e.get("id"): e for e in entries if e.get("id")}

        # Failure mode A: more than one simultaneously active owner in the
        # SAME domain, even within one connected lineage. "Only one current
        # production owner may govern a given architecture domain" is an
        # absolute cardinality rule, not merely a disconnection rule — a
        # continuation transition must close the predecessor's
        # currently_active flag before opening its own, not run both
        # active at once.
        active_ids = sorted(i for i, e in id_to_entry.items() if e.get("currently_active") is True)
        if len(active_ids) > 1:
            violations.append(
                Violation(
                    "DCL-001",
                    f"architecture domain '{domain}' has {len(active_ids)} simultaneously "
                    f"active production owners: {active_ids} — only one current production "
                    f"owner may govern a domain at a time, even within a connected lineage",
                )
            )

        adjacency: dict[str, set[str]] = {eid: set() for eid in id_to_entry}
        for eid, entry in id_to_entry.items():
            for field in _RELATIONSHIP_FIELDS:
                target = entry.get(field)
                if target in id_to_entry:
                    adjacency[eid].add(target)
                    adjacency[target].add(eid)

        components: list[set[str]] = []
        visited: set[str] = set()
        for eid in id_to_entry:
            if eid in visited:
                continue
            component: set[str] = set()
            stack = [eid]
            while stack:
                cur = stack.pop()
                if cur in component:
                    continue
                component.add(cur)
                visited.add(cur)
                stack.extend(adjacency.get(cur, ()) - component)
            components.append(component)

        if len(components) <= 1:
            continue

        active_components = [
            c for c in components if any(id_to_entry[i].get("currently_active") is True for i in c)
        ]
        if active_components:
            violations.append(
                Violation(
                    "DCL-001",
                    f"architecture domain '{domain}' has {len(components)} disconnected "
                    f"claimant lineage(s) and at least one is currently_active: "
                    + "; ".join(
                        f"[{', '.join(sorted(c))}]" for c in sorted(components, key=lambda c: sorted(c))
                    ),
                )
            )
    return violations


# ---------------------------------------------------------------------------
# DCL-002 — Active/closed contradiction
# ---------------------------------------------------------------------------

def check_dcl002(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    for section in ("product_milestones", "research_experiments", "reusable_components"):
        for entry in _entries(state, section):
            status = str(entry.get("status") or "")
            if _is_closed_like_status(status) and entry.get("currently_active") is True:
                violations.append(
                    Violation(
                        "DCL-002",
                        f"'{entry.get('id', '<unknown>')}' has status '{status}' "
                        f"(closed/frozen) but is also marked currently_active: true",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# DCL-003 — Missing relationship target
#
# Covers both entity relationship fields (continues_architecture_of, etc.)
# and CURRENT alias resolution targets ("or similar canonical references").
# ---------------------------------------------------------------------------

def check_dcl003(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    known_ids = _all_known_ids(state)
    for section in SECTION_PREFIXES:
        for entry in _entries(state, section):
            for field in _RELATIONSHIP_FIELDS:
                target = entry.get(field)
                if target and target not in known_ids:
                    violations.append(
                        Violation(
                            "DCL-003",
                            f"'{entry.get('id', '<unknown>')}'.{field} references "
                            f"'{target}', which does not resolve to any known canonical id",
                        )
                    )
    for entry in _entries(state, "aliases"):
        if entry.get("resolution_status") != "CURRENT":
            continue
        target = entry.get("resolves_to")
        alias_name = entry.get("alias", "<unknown>")
        if not target:
            violations.append(
                Violation(
                    "DCL-003",
                    f"alias '{alias_name}' has resolution_status: CURRENT but resolves_to "
                    f"is null/empty — a CURRENT alias must name a real target",
                )
            )
        elif target not in known_ids:
            violations.append(
                Violation(
                    "DCL-003",
                    f"alias '{alias_name}' (resolution_status: CURRENT) "
                    f"resolves_to '{target}', which does not resolve to any known canonical id",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# DCL-004 — Duplicate canonical identity (within a section)
# ---------------------------------------------------------------------------

def check_dcl004(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    for section in SECTION_PREFIXES:
        seen: dict[str, int] = {}
        for entry in _entries(state, section):
            eid = entry.get("id")
            if not eid:
                continue
            seen[eid] = seen.get(eid, 0) + 1
        for eid, count in seen.items():
            if count > 1:
                violations.append(
                    Violation(
                        "DCL-004",
                        f"canonical id '{eid}' appears {count} times in section '{section}'",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# DCL-005 — Research claiming production authority
#
# Also covers the same "claiming a stronger status than evidence supports"
# family for reusable components: DISTRIBUTABLE without portability evidence.
# ---------------------------------------------------------------------------

def check_dcl005(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    integration_events_by_id = {
        e.get("id"): e for e in _entries(state, "integration_events") if e.get("id")
    }

    for entry in _entries(state, "research_experiments"):
        eid = entry.get("id", "<unknown>")
        domain = entry.get("architecture_domain")
        promoted = entry.get("promoted_to_production") is True
        if domain and not promoted:
            violations.append(
                Violation(
                    "DCL-005",
                    f"research experiment '{eid}' claims architecture_domain "
                    f"'{domain}' without promoted_to_production: true",
                )
            )
        if promoted:
            ref = entry.get("integration_event_ref")
            event = integration_events_by_id.get(ref) if ref else None
            if not ref or event is None:
                violations.append(
                    Violation(
                        "DCL-005",
                        f"research experiment '{eid}' declares promoted_to_production: "
                        f"true without a resolving integration_event_ref — a self-declared "
                        f"promotion is not integration authorization evidence",
                    )
                )
            elif event.get("target_experiment") != eid:
                violations.append(
                    Violation(
                        "DCL-005",
                        f"research experiment '{eid}' cites integration_event_ref '{ref}', "
                        f"but that integration event's target_experiment is "
                        f"'{event.get('target_experiment')}', not '{eid}' — citing an "
                        f"unrelated integration event is not valid authorization for this "
                        f"experiment's promotion",
                    )
                )

    for entry in _entries(state, "reusable_components"):
        if entry.get("status") == "DISTRIBUTABLE":
            if entry.get("cross_agent_portable") is not True or not entry.get(
                "portability_validated_via"
            ):
                violations.append(
                    Violation(
                        "DCL-005",
                        f"component '{entry.get('id', '<unknown>')}' claims status "
                        f"DISTRIBUTABLE without cross_agent_portable: true and a "
                        f"portability_validated_via non-URI adapter/harness",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# DCL-006 — Frozen work treated as mutable
# ---------------------------------------------------------------------------

def _mutable_conflict(entry: dict) -> bool:
    status = str(entry.get("status") or "")
    closed_like = _is_closed_like_status(status)
    frozen_flag = entry.get("frozen") is True
    return (closed_like or frozen_flag) and entry.get("mutable") is True


def check_dcl006(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    for section in SECTION_PREFIXES:
        for entry in _entries(state, section):
            if _mutable_conflict(entry):
                violations.append(
                    Violation(
                        "DCL-006",
                        f"'{entry.get('id', '<unknown>')}' has status "
                        f"'{entry.get('status')}' (closed/frozen) but is also marked "
                        f"mutable: true",
                    )
                )

    rar_map = state.get("rar_identity_map")
    if rar_map is not None:
        if not isinstance(rar_map, dict):
            raise UriStateSchemaError(
                f"'rar_identity_map' must be a mapping, got {type(rar_map).__name__}"
            )
        research_lines = rar_map.get("research_lines") or []
        if not isinstance(research_lines, list):
            raise UriStateSchemaError("'rar_identity_map.research_lines' must be a list")
        for entry in research_lines:
            if not isinstance(entry, dict):
                raise UriStateSchemaError(
                    "'rar_identity_map.research_lines' must contain only mapping entries"
                )
            if _mutable_conflict(entry):
                violations.append(
                    Violation(
                        "DCL-006",
                        f"rar_identity_map research line '{entry.get('id', '<unknown>')}' "
                        f"has status '{entry.get('status')}' but is marked mutable: true",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# DCL-007 — Ambiguous current alias
#
# Two failure modes: (a) one alias string resolving to two different CURRENT
# canonical identities; (b) an alias string carrying an
# AMBIGUOUS_BARE_ALIAS_FORBIDDEN collision-guard entry that nonetheless
# co-exists with a CURRENT resolution for the same alias string.
# ---------------------------------------------------------------------------

def check_dcl007(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    aliases = _entries(state, "aliases")
    by_alias: dict[str, list[dict]] = {}
    for entry in aliases:
        alias = entry.get("alias")
        if alias:
            by_alias.setdefault(alias, []).append(entry)

    for alias, group in by_alias.items():
        current_targets = {
            e.get("resolves_to") for e in group if e.get("resolution_status") == "CURRENT"
        }
        if len(current_targets) > 1:
            violations.append(
                Violation(
                    "DCL-007",
                    f"alias '{alias}' resolves to {len(current_targets)} different "
                    f"CURRENT canonical identities: {sorted(current_targets)}",
                )
            )

        has_bare_guard = any(
            e.get("resolution_status") == _BARE_COLLISION_GUARD_STATUS for e in group
        )
        has_current = any(e.get("resolution_status") == "CURRENT" for e in group)
        if has_bare_guard and has_current:
            violations.append(
                Violation(
                    "DCL-007",
                    f"alias '{alias}' is guarded as AMBIGUOUS_BARE_ALIAS_FORBIDDEN but "
                    f"also has a CURRENT resolution entry for the same alias string — "
                    f"the collision guard is broken",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# DCL-008 — Human-readable current-state conflict
#
# A reconciled: true claim must carry a commit-like superseding_commit as
# machine-checkable evidence, not a bare self-attested boolean.
# ---------------------------------------------------------------------------

def check_dcl008(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    for section in SECTION_PREFIXES:
        for entry in _entries(state, section):
            pointer = entry.get("human_readable_pointer")
            if not isinstance(pointer, dict):
                continue
            eid = entry.get("id", "<unknown>")
            if pointer.get("reconciled") is False:
                violations.append(
                    Violation(
                        "DCL-008",
                        f"'{eid}' has an unreconciled human_readable_pointer to "
                        f"{pointer.get('file', '<unknown file>')}",
                    )
                )
            elif pointer.get("reconciled") is True:
                commit = pointer.get("superseding_commit")
                if not commit or not _COMMIT_LIKE_RE.match(str(commit)):
                    violations.append(
                        Violation(
                            "DCL-008",
                            f"'{eid}' claims human_readable_pointer.reconciled: true "
                            f"without a valid superseding_commit as evidence",
                        )
                    )
    return violations


# ---------------------------------------------------------------------------
# DCL-009 — Legacy architecture ownership
# ---------------------------------------------------------------------------

def check_dcl009(state: dict) -> list[Violation]:
    violations: list[Violation] = []

    for entry in _entries(state, "aliases"):
        if entry.get("legacy") is True:
            resolves_to = entry.get("resolves_to")
            resolution_status = entry.get("resolution_status")
            if resolves_to != "LEGACY_REFERENCE_ONLY" or resolution_status != "LEGACY_REFERENCE_ONLY":
                violations.append(
                    Violation(
                        "DCL-009",
                        f"alias '{entry.get('alias', '<unknown>')}' is marked legacy "
                        f"but does not resolve to LEGACY_REFERENCE_ONLY",
                    )
                )

    entity_sections = ("product_milestones", "reusable_components", "research_experiments")
    legacy_ids: set[str] = set()
    for section in entity_sections:
        for entry in _entries(state, section):
            if entry.get("legacy") is True and entry.get("id"):
                legacy_ids.add(entry["id"])

    for section in entity_sections:
        for entry in _entries(state, section):
            eid = entry.get("id", "<unknown>")
            if entry.get("legacy") is True:
                if entry.get("currently_active") is True:
                    violations.append(
                        Violation(
                            "DCL-009",
                            f"'{eid}' is marked legacy but also currently_active: true — "
                            f"legacy URI may not claim current product/architecture ownership",
                        )
                    )
                if entry.get("architecture_domain"):
                    violations.append(
                        Violation(
                            "DCL-009",
                            f"'{eid}' is marked legacy but declares architecture_domain "
                            f"'{entry.get('architecture_domain')}' — legacy URI may not claim "
                            f"architecture ownership even while not currently_active",
                        )
                    )
            if entry.get("currently_active") is True:
                for field in _RELATIONSHIP_FIELDS:
                    target = entry.get(field)
                    if target in legacy_ids:
                        violations.append(
                            Violation(
                                "DCL-009",
                                f"'{eid}' is currently_active and its {field} references "
                                f"legacy-flagged identity '{target}' — current active work "
                                f"may not treat legacy URI as its architecture continuation",
                            )
                        )
    return violations


# ---------------------------------------------------------------------------
# DCL-010 — Invalid integration target
# ---------------------------------------------------------------------------

def check_dcl010(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    component_by_id = {e.get("id"): e for e in _entries(state, "reusable_components")}
    milestone_ids = {e.get("id") for e in _entries(state, "product_milestones")}

    for entry in _entries(state, "integration_events"):
        eid = entry.get("id", "<unknown>")
        target_component = entry.get("target_component")

        if not target_component:
            violations.append(
                Violation(
                    "DCL-010",
                    f"integration event '{eid}' has no target_component — every "
                    f"integration event must name the component it authorizes",
                )
            )
        elif target_component not in component_by_id:
            violations.append(
                Violation(
                    "DCL-010",
                    f"integration event '{eid}' references nonexistent component "
                    f"'{target_component}'",
                )
            )
        else:
            comp_status = component_by_id[target_component].get("status")
            if comp_status in INTEGRATION_INELIGIBLE_COMPONENT_STATUSES:
                override = entry.get("qualification_override") is True
                justification = entry.get("override_justification")
                if not override:
                    violations.append(
                        Violation(
                            "DCL-010",
                            f"integration event '{eid}' targets component "
                            f"'{target_component}' whose status '{comp_status}' is "
                            f"ineligible for integration without qualification_override: true",
                        )
                    )
                elif not justification:
                    violations.append(
                        Violation(
                            "DCL-010",
                            f"integration event '{eid}' sets qualification_override: true "
                            f"for ineligible component '{target_component}' without a "
                            f"non-empty override_justification — a bare override is not "
                            f"sufficient authorization",
                        )
                    )

        target_milestone = entry.get("target_milestone")
        if target_milestone is not None and target_milestone not in milestone_ids:
            violations.append(
                Violation(
                    "DCL-010",
                    f"integration event '{eid}' references nonexistent milestone "
                    f"'{target_milestone}'",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# DCL-011 — Namespace collision
# ---------------------------------------------------------------------------

def check_dcl011(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    id_to_sections: dict[str, list[str]] = {}
    for section, prefix in SECTION_PREFIXES.items():
        for entry in _entries(state, section):
            eid = entry.get("id")
            if not eid:
                continue
            id_to_sections.setdefault(eid, []).append(section)

            if section == "product_milestones" and eid in PRODUCT_NAMESPACE_EXCEPTIONS:
                continue
            if section == "product_milestones":
                if not _PRODUCT_ID_RE.match(eid):
                    violations.append(
                        Violation(
                            "DCL-011",
                            f"'{eid}' in section 'product_milestones' does not match the "
                            f"required Mxx syntax ({_PRODUCT_ID_RE.pattern})",
                        )
                    )
            elif not eid.startswith(prefix):
                violations.append(
                    Violation(
                        "DCL-011",
                        f"'{eid}' in section '{section}' does not match the required "
                        f"namespace prefix '{prefix}'",
                    )
                )

    for eid, sections in id_to_sections.items():
        if len(set(sections)) > 1:
            violations.append(
                Violation(
                    "DCL-011",
                    f"canonical id '{eid}' is used across multiple namespaces: "
                    f"{', '.join(sorted(set(sections)))}",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# DCL-012 — Forbidden historical alias reuse
#
# Two failure modes: (a) a forbidden alias string used directly as a live
# canonical id elsewhere; (b) a forbidden alias string that nonetheless
# gains a CURRENT resolution entry for the same alias string.
# ---------------------------------------------------------------------------

def check_dcl012(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    aliases = _entries(state, "aliases")

    forbidden_aliases = {
        e.get("alias")
        for e in aliases
        if e.get("forbidden_for_new_work") is True
        or e.get("resolution_status") == _HISTORICAL_FORBIDDEN_STATUS
    }
    if forbidden_aliases:
        known_ids = _all_known_ids(state)
        for alias in forbidden_aliases:
            if alias in known_ids:
                violations.append(
                    Violation(
                        "DCL-012",
                        f"'{alias}' is marked forbidden-for-new-work but is used as an "
                        f"active canonical id elsewhere in the state file",
                    )
                )

    by_alias: dict[str, list[dict]] = {}
    for entry in aliases:
        alias = entry.get("alias")
        if alias:
            by_alias.setdefault(alias, []).append(entry)
    for alias, group in by_alias.items():
        has_forbidden = any(
            e.get("forbidden_for_new_work") is True
            or e.get("resolution_status") == _HISTORICAL_FORBIDDEN_STATUS
            for e in group
        )
        has_current = any(e.get("resolution_status") == "CURRENT" for e in group)
        if has_forbidden and has_current:
            violations.append(
                Violation(
                    "DCL-012",
                    f"alias '{alias}' is marked forbidden-for-new-work/HISTORICAL_FORBIDDEN "
                    f"but also has a CURRENT resolution entry for the same alias string",
                )
            )
    return violations


ALL_RULES = (
    check_dcl001,
    check_dcl002,
    check_dcl003,
    check_dcl004,
    check_dcl005,
    check_dcl006,
    check_dcl007,
    check_dcl008,
    check_dcl009,
    check_dcl010,
    check_dcl011,
    check_dcl012,
)


def validate_state(state: dict) -> list[Violation]:
    violations: list[Violation] = []
    for rule in ALL_RULES:
        violations.extend(rule(state))
    return violations


def validate_text(text: str) -> list[Violation]:
    state = parse_uri_state_yaml(text)
    return validate_state(state)


def validate_file(path: str) -> list[Violation]:
    state = load_uri_state_yaml(path)
    return validate_state(state)


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else "docs/governance/URI_STATE.yaml"
    try:
        violations = validate_file(path)
    except (UriStateYamlError, UriStateSchemaError) as exc:
        print(f"STATE_ERROR: {exc}", file=sys.stderr)
        return 1
    if not violations:
        print(f"VALID: {path} — no DCL violations found.")
        return 0
    print(f"INVALID: {path} — {len(violations)} violation(s) found.", file=sys.stderr)
    for v in violations:
        print(str(v), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
