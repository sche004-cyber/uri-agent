"""The sole S1 owner of clarification responses and Change/rebind authority."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Callable

from uri_v1.turn.rar_clarification_contract import (
    BindingState, ClarificationKind, ClarificationResponse, ResponseKind,
    WrongBindingImpact, CandidateFact,
)
from uri_v1.turn.rar_contracts import (
    RARDeterministicAnchor, RARDriverRule, RAROutcome, RARQuery,
    resolve_rar_deterministically, validate_rar_resolution,
)
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended
from .attribute_narrowing import normalized
from .authority import AuthorityClass, classify_authority
from .builder import BuildResult, build_clarification
from .fingerprints import candidate_fingerprint, candidate_set_fingerprint
from .session_adjunct import SessionEvidence
from .safeguards import ClarificationSafeguards
from .store import BindingRecord, InMemoryClarificationStore, StoredRound


@dataclass(frozen=True)
class BindingResult:
    state: BindingState
    candidate_id: str | None = None
    next_contract_id: str | None = None
    reason: str | None = None
    binding_id: str | None = None


class BindingService:
    def __init__(self, store: InMemoryClarificationStore | None = None,
                 safeguards: ClarificationSafeguards | None = None) -> None:
        self.store = store or InMemoryClarificationStore()
        self.session_evidence: dict[str, SessionEvidence] = {}
        self.safeguards = safeguards

    def _charge(self, record: StoredRound, *, made_progress: bool) -> bool:
        if self.safeguards is None or self.safeguards.charge(made_progress=made_progress):
            return True
        record.state = BindingState.REJECTED
        return False

    def register(self, built: BuildResult, query: RARQuery) -> BindingResult:
        if built.contract:
            self.store.add_round(built.contract, query, built.state)
            return BindingResult(built.state, next_contract_id=built.contract.ambiguity_id)
        if built.candidate_id and built.binding_id and built.session_id:
            candidate = query.get_candidate(built.candidate_id)
            if candidate is None:
                raise ValueError("binding candidate missing")
            self.store.bindings[built.binding_id] = BindingRecord(built.binding_id, built.session_id,
                built.candidate_id, built.state, candidate_fingerprint(candidate))
            self.store.binding_queries[built.binding_id] = query
            return BindingResult(built.state, built.candidate_id, binding_id=built.binding_id)
        return BindingResult(built.state, built.candidate_id)

    def _reject(self, record: StoredRound | None, reason: str) -> BindingResult:
        if record is not None and not record.used:
            record.state = BindingState.REJECTED
        return BindingResult(BindingState.REJECTED, reason=reason)

    def _current(self, query: RARQuery, scope: tuple[str, ...]) -> tuple:
        return tuple(query.get_candidate(cid) for cid in scope)

    def _fresh(self, record: StoredRound, query: RARQuery, candidate_ids: tuple[str, ...]) -> bool:
        stored = dict(record.contract.scope_fingerprints)
        return all((candidate := query.get_candidate(cid)) is not None and
                   stored.get(cid) == candidate_fingerprint(candidate) for cid in candidate_ids)

    def _binding(self, record: StoredRound, candidate_id: str, query: RARQuery,
                 *, change: bool = False,
                 current_candidate_locators: dict[str, str] | None = None) -> BindingResult:
        contract = record.contract
        if change:
            prior = self.store.bindings.get(contract.change_of or "")
            if prior is None or prior.state not in (BindingState.TENTATIVE, BindingState.TENTATIVE_APPLIED) or prior.session_id != contract.session_id:
                return self._reject(record, "change source is not tentative")
            if candidate_id == prior.candidate_id:
                record.used = True
                record.state = BindingState.CHANGE_ABANDONED
                return BindingResult(BindingState.CHANGE_ABANDONED, prior.candidate_id)
            if prior.state == BindingState.TENTATIVE_APPLIED and not prior.applied_result_exists:
                return self._reject(record, "original result missing")
        candidate = query.get_candidate(candidate_id)
        if candidate is None or not self._fresh(record, query, (candidate_id,)):
            return self._reject(record, "candidate stale or absent")
        if contract.provenance_required and (
            dict(contract.candidate_locators).get(candidate_id) != contract.parent_locator or
            (current_candidate_locators or {}).get(candidate_id) != contract.parent_locator
        ):
            return self._reject(record, "candidate provenance does not match parent")
        after_execution = change and prior.state == BindingState.TENTATIVE_APPLIED
        binding = BindingRecord(contract.ambiguity_id, contract.session_id, candidate_id,
                                BindingState.CONFIRMED, candidate_fingerprint(candidate),
                                from_change=after_execution,
                                prior_binding_id=contract.change_of)
        self.store.bindings[contract.ambiguity_id] = binding
        self.store.binding_queries[contract.ambiguity_id] = query
        record.used = True
        record.state = BindingState.CONFIRMED
        self.session_evidence.setdefault(contract.session_id, SessionEvidence(contract.session_id)).record_selection(candidate_id)
        if change:
            self.session_evidence[contract.session_id].record_correction(prior.candidate_id, candidate_id)
        return BindingResult(BindingState.CONFIRMED, candidate_id, binding_id=contract.ambiguity_id)

    def respond(self, session_id: str, response: ClarificationResponse, current_query: RARQuery,
                *, wrong_binding_impact: WrongBindingImpact | str | None = None,
                impact_reader: Callable[[], WrongBindingImpact | str | None] | None = None,
                current_candidate_locators: dict[str, str] | None = None,
                current_extra_facts: dict[str, tuple[CandidateFact, ...]] | None = None,
                now: datetime | None = None) -> BindingResult:
        record = self.store.rounds.get(response.ambiguity_id)
        if record is None:
            return BindingResult(BindingState.REJECTED, reason="unknown ambiguity ID")
        contract = record.contract
        if contract.session_id != session_id:
            return BindingResult(BindingState.REJECTED, reason="wrong session")
        if record.used or record.state not in (BindingState.PENDING, BindingState.CHANGE_PENDING):
            return self._reject(record, "round already answered or closed")
        instant = now or datetime.now(timezone.utc)
        if instant >= datetime.fromisoformat(contract.expires_at):
            record.state = BindingState.CHANGE_ABANDONED if contract.change_of else BindingState.EXPIRED
            return BindingResult(record.state, reason="round expired")
        if not isinstance(response.response_kind, ResponseKind):
            return self._reject(record, "invalid response kind")
        change = contract.change_of is not None
        impact = impact_reader() if impact_reader else wrong_binding_impact
        if change and impact not in (WrongBindingImpact.NONE, WrongBindingImpact.RECOVERABLE, "NONE", "RECOVERABLE"):
            return self._reject(record, "change impact is consequential or undeclared")
        if response.response_kind == ResponseKind.CANDIDATE:
            if response.option_key is not None or response.text is not None or response.axis is not None or response.value is not None:
                return self._reject(record, "invalid candidate payload")
            if contract.kind not in (ClarificationKind.CHOOSE_ONE, ClarificationKind.CONFIRM_ONE):
                return self._reject(record, "candidate response to non-candidate contract")
            if response.candidate_set_fingerprint != contract.candidate_set_fingerprint:
                return self._reject(record, "stale candidate-set fingerprint")
            if response.candidate_id not in {c.candidate_id for c in contract.candidates}:
                return self._reject(record, "candidate not displayed")
            candidate_id = response.candidate_id
            # Preserve other deterministic anchors. Level-0 override must fail closed.
            old_anchor = record.query.deterministic_anchor or RARDeterministicAnchor()
            rerun_query = replace(record.query, candidates=tuple(current_query.get_candidate(cid) for cid in contract.scope_candidate_ids),
                                  deterministic_anchor=replace(old_anchor, selected_ui_id=candidate_id))
            if any(c is None for c in rerun_query.candidates):
                return self._reject(record, "candidate scope changed")
            result = resolve_rar_deterministic_extended(rerun_query).resolution
            if not (result.outcome == RAROutcome.RESOLVED and result.rule_used == RARDriverRule.ACTIVE_UI
                    and result.candidate_id == candidate_id):
                return self._reject(record, "click did not resolve through ACTIVE_UI")
            return self._binding(record, candidate_id, current_query, change=change,
                                 current_candidate_locators=current_candidate_locators)
        if response.response_kind == ResponseKind.ATTRIBUTE:
            if contract.kind != ClarificationKind.CHOOSE_ATTRIBUTE or response.candidate_id is not None or response.text is not None:
                return self._reject(record, "invalid attribute payload")
            if response.candidate_set_fingerprint != contract.candidate_set_fingerprint:
                return self._reject(record, "stale candidate-set fingerprint")
            option = next((o for o in contract.attribute_options if o.option_key == response.option_key), None)
            if option is None or (response.axis is not None and response.axis != option.axis) or (response.value is not None and response.value != option.value):
                return self._reject(record, "invalid attribute option")
            if not self._fresh(record, current_query, option.member_candidate_ids):
                return self._reject(record, "attribute member stale")
            if not set(option.member_candidate_ids) <= set(current_query.candidate_ids):
                return self._reject(record, "attribute member absent")
            if not self._charge(record, made_progress=True):
                return BindingResult(BindingState.REJECTED, reason="clarification budget exhausted")
            self.session_evidence.setdefault(session_id, SessionEvidence(session_id)).record_clue(option.axis, option.value)
            narrowed = tuple(current_query.get_candidate(cid) for cid in option.member_candidate_ids)
            old_anchor = record.query.deterministic_anchor
            anchor = replace(old_anchor, selected_ui_id=None) if old_anchor else None
            rerun_query = replace(record.query, candidates=narrowed, deterministic_anchor=anchor)
            resolution = resolve_rar_deterministic_extended(rerun_query).resolution
            record.used = True
            built = build_clarification(rerun_query, resolution, session_id=session_id, turn_id=contract.turn_id,
                wrong_binding_impact=impact, round_index=contract.round_index + 1,
                answered_axes=contract.answered_axes + (option.axis,), attribute_narrowed=True,
                change_of=contract.change_of, current_binding_id=contract.current_binding_id,
                provenance_required=contract.provenance_required, parent_locator=contract.parent_locator,
                candidate_locators=dict(contract.candidate_locators), extra_facts=current_extra_facts)
            if built.state == BindingState.TENTATIVE and not change:
                candidate = rerun_query.get_candidate(built.candidate_id)
                self.store.bindings[contract.ambiguity_id] = BindingRecord(contract.ambiguity_id, session_id,
                    built.candidate_id, BindingState.TENTATIVE, candidate_fingerprint(candidate))
                record.state = BindingState.TENTATIVE
                return BindingResult(BindingState.TENTATIVE, built.candidate_id)
            if built.contract:
                self.store.add_round(built.contract, rerun_query, built.state)
                record.state = BindingState.REBIND_CHECK if change else BindingState.REJECTED
                return BindingResult(built.state, next_contract_id=built.contract.ambiguity_id)
            return self._reject(record, "attribute narrowing did not yield a safe next round")
        if response.response_kind == ResponseKind.FREE_INPUT:
            if not response.text or not response.text.strip() or response.candidate_id is not None or response.option_key is not None or response.axis is not None or response.value is not None:
                return self._reject(record, "invalid free input")
            if change:
                prior = self.store.bindings.get(contract.change_of or "")
                prior_query = self.store.binding_queries.get(contract.change_of or "")
                prior_candidate = prior_query.get_candidate(prior.candidate_id) if prior and prior_query else None
                if prior_candidate and normalized(response.text) in {
                    normalized(prior_candidate.id), normalized(prior_candidate.title),
                    *(normalized(alias) for alias in prior_candidate.exact_aliases),
                }:
                    record.used = True
                    record.state = BindingState.CHANGE_ABANDONED
                    return BindingResult(BindingState.CHANGE_ABANDONED, prior.candidate_id)
            if contract.kind == ClarificationKind.CHOOSE_ATTRIBUTE:
                matches = [o for o in contract.attribute_options if normalized(o.value) == normalized(response.text)]
                if len(matches) == 1:
                    return self.respond(session_id, ClarificationResponse(contract.ambiguity_id, ResponseKind.ATTRIBUTE,
                        option_key=matches[0].option_key, candidate_set_fingerprint=contract.candidate_set_fingerprint),
                        current_query, wrong_binding_impact=impact, impact_reader=impact_reader,
                        current_candidate_locators=current_candidate_locators,
                        current_extra_facts=current_extra_facts, now=instant)
            scope = contract.scope_candidate_ids
            scoped = tuple(current_query.get_candidate(cid) for cid in scope)
            if any(c is None for c in scoped):
                return self._reject(record, "candidate scope changed")
            old_anchor = record.query.deterministic_anchor
            anchor = replace(old_anchor, selected_ui_id=None) if old_anchor else None
            rerun_query = replace(record.query, reference_expression=response.text,
                                  candidates=scoped, deterministic_anchor=anchor)
            resolution = resolve_rar_deterministic_extended(rerun_query).resolution
            validate_rar_resolution(resolution, scoped)
            made_progress = (resolution.outcome == RAROutcome.RESOLVED or
                             resolution.outcome == RAROutcome.AMBIGUOUS and
                             len(resolution.ambiguous_candidate_ids) < len(scope))
            if not self._charge(record, made_progress=made_progress):
                return BindingResult(BindingState.REJECTED, reason="clarification budget exhausted")
            if resolution.outcome == RAROutcome.RESOLVED:
                cid = resolution.candidate_id
                if not self._fresh(record, current_query, (cid,)):
                    return self._reject(record, "resolved candidate stale")
                if classify_authority(resolution, rerun_query) == AuthorityClass.CERTAINTY:
                    return self._binding(record, cid, current_query, change=change,
                                         current_candidate_locators=current_candidate_locators)
            record.used = True
            built = build_clarification(rerun_query, resolution, session_id=session_id, turn_id=contract.turn_id,
                wrong_binding_impact=impact, round_index=contract.round_index + 1,
                change_of=contract.change_of, current_binding_id=contract.current_binding_id,
                answered_axes=contract.answered_axes,
                provenance_required=contract.provenance_required, parent_locator=contract.parent_locator,
                candidate_locators=dict(contract.candidate_locators), extra_facts=current_extra_facts)
            if built.state == BindingState.TENTATIVE and not change:
                candidate = rerun_query.get_candidate(built.candidate_id)
                self.store.bindings[contract.ambiguity_id] = BindingRecord(contract.ambiguity_id, session_id,
                    built.candidate_id, BindingState.TENTATIVE, candidate_fingerprint(candidate))
                record.state = BindingState.TENTATIVE
                return BindingResult(BindingState.TENTATIVE, built.candidate_id)
            if built.contract:
                self.store.add_round(built.contract, rerun_query, built.state)
                record.state = BindingState.REBIND_CHECK if change else BindingState.REJECTED
                return BindingResult(built.state, next_contract_id=built.contract.ambiguity_id)
            return self._reject(record, "free input unresolved")
        return self._reject(record, "unrecognized response")

    def record_execution(self, ambiguity_id: str, *, applied_result_exists: bool = True) -> BindingState:
        binding = self.store.bindings[ambiguity_id]
        if binding.state == BindingState.TENTATIVE:
            binding.state = BindingState.TENTATIVE_APPLIED
        elif binding.state == BindingState.CONFIRMED and not binding.from_change:
            binding.state = BindingState.APPLIED
        else:
            raise ValueError("execution event not admissible")
        binding.applied_result_exists = applied_result_exists
        return binding.state

    def rebuild_rejected(self, ambiguity_id: str, fresh_query: RARQuery) -> BindingResult:
        """Use caller-supplied fresh evidence after a rejected/stale round.

        A failed response never turns into an automatic binding during rebuild.
        """
        old = self.store.rounds[ambiguity_id]
        if old.state not in (BindingState.REJECTED, BindingState.EXPIRED):
            raise ValueError("only a closed rejected round can be rebuilt")
        result = resolve_rar_deterministic_extended(fresh_query).resolution
        built = build_clarification(fresh_query, result, session_id=old.contract.session_id,
            turn_id=old.contract.turn_id, wrong_binding_impact=None,
            round_index=old.contract.round_index, attribute_narrowed=True,
            change_of=old.contract.change_of, current_binding_id=old.contract.current_binding_id,
            answered_axes=old.contract.answered_axes,
            provenance_required=old.contract.provenance_required,
            parent_locator=old.contract.parent_locator,
            candidate_locators=dict(old.contract.candidate_locators))
        return self.register(built, fresh_query)

    def close_round(self, ambiguity_id: str, *, session_id: str) -> BindingState:
        """Expire an initial round or abandon an open Change on cancel/turn change."""
        record = self.store.rounds[ambiguity_id]
        if record.contract.session_id != session_id or record.used or record.state not in (
                BindingState.PENDING, BindingState.CHANGE_PENDING):
            raise ValueError("round cannot be closed")
        record.used = True
        record.state = (BindingState.CHANGE_ABANDONED if record.contract.change_of
                        else BindingState.EXPIRED)
        return record.state

    def open_change(self, ambiguity_id: str, query: RARQuery, resolution, *,
                    impact_reader: Callable[[], WrongBindingImpact | str | None], turn_id: str) -> BindingResult:
        validate_rar_resolution(resolution, query.candidates)
        prior = self.store.bindings[ambiguity_id]
        if prior.state not in (BindingState.TENTATIVE, BindingState.TENTATIVE_APPLIED):
            return BindingResult(BindingState.REJECTED, reason="change source is terminal")
        if prior.state == BindingState.TENTATIVE_APPLIED and impact_reader() not in (
                WrongBindingImpact.NONE, WrongBindingImpact.RECOVERABLE, "NONE", "RECOVERABLE"):
            return BindingResult(BindingState.REJECTED, reason="change impact is consequential or undeclared")
        remaining = tuple(c for c in query.candidates if c.id != prior.candidate_id)
        change_query = replace(query, candidates=remaining,
                               deterministic_anchor=None)
        fresh = resolve_rar_deterministic_extended(change_query).resolution
        built = build_clarification(change_query, fresh, session_id=prior.session_id, turn_id=turn_id,
            wrong_binding_impact=impact_reader(), change_of=ambiguity_id,
            current_binding_id=prior.candidate_id, attribute_narrowed=len(remaining) == 1)
        return self.register(built, change_query)

    def authorize_redo(self, ambiguity_id: str, *, fresh_authorized: bool,
                       edited_result_status: str) -> BindingState:
        binding = self.store.bindings[ambiguity_id]
        if not binding.from_change or binding.state != BindingState.CONFIRMED:
            raise ValueError("redo requires confirmed Change rebind")
        if edited_result_status == "UNEDITED" and fresh_authorized:
            # An injected authorization decision may be recorded, but S1 has no redo executor.
            binding.state = BindingState.REDO_AUTHORIZED
            return binding.state
        binding.state = BindingState.REDO_NOT_EXECUTED
        binding.redo_reason = ("result-version owner (S11) required" if edited_result_status != "UNEDITED"
                               else "fresh authorization declined")
        return binding.state
