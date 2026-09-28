"""S4-envelope lineage; A2 completeness and A3/A4 raw-input admission."""
from __future__ import annotations

from dataclasses import dataclass
import re

from uri_v1.turn.rar_contracts import RARQuery, RARCandidate, RAREvidence, RARDeterministicAnchor
from uri_v1.turn.rar_clarification_contract import ClarificationResponse, ResponseKind, BindingState
from uri_v1.reference_clarification.binding import BindingResult
from ..contracts import (TrustedInput, _INTAKE_AUTHORITY, IdentityStatus as I, require_trace_id,
                         RetrievalResult, canonical, AttachmentManifest, _ATTACHMENT_AUTHORITY, authorized_attachments,
                         negated)
from ..retrieval import raw_span, exact_name, TYPE_WORDS, words


class URIIntake:
    """Called by trusted intake/qualification driver before model processing."""
    def capture(self, user_id, session_id, turn_id, trace_id, raw_text, *, spans, round_id=None):
        require_trace_id(trace_id)
        if not isinstance(raw_text,str) or not raw_text or len(raw_text)>2000: raise ValueError("invalid raw input")
        entries = tuple((key,a,b) for key,(a,b) in spans.items())
        if any(type(a) is not int or type(b) is not int or not 0 <= a < b <= len(raw_text) for _,a,b in entries): raise ValueError("invalid intake span")
        if not session_id or not turn_id: raise ValueError("missing intake identity")
        return TrustedInput(user_id,session_id,turn_id,trace_id,raw_text,entries,round_id,_INTAKE_AUTHORITY)

    def capture_attachments(self,intake,source_ids,*,media_classes=()):
        """Trusted ingestion callback only; no decoder-provided membership flags."""
        if not isinstance(intake,TrustedInput) or not intake.trusted: raise ValueError("TRUSTED_INGESTION_REQUIRED")
        if len(set(source_ids))!=len(source_ids): raise ValueError("duplicate attachment IDs")
        return AttachmentManifest(intake.user_id,intake.session_id,intake.turn_id,tuple(source_ids),tuple(media_classes),_ATTACHMENT_AUTHORITY)


@dataclass(frozen=True)
class ExpressionGrounding:
    turn_id: str
    trace_id: str
    ref_key: str
    offsets: tuple[int,int] | None
    status: str
    raw_expression: str | None


@dataclass(frozen=True)
class Projection:
    query: RARQuery | None
    grounding: ExpressionGrounding | None
    degraded: str | None = None


def _boundary(text, a, b):
    delimiters = "\"'`“”‘’()[]{} ,;:!?"
    left = a == 0 or text[a-1].isspace() or text[a-1] in delimiters
    right = b == len(text) or text[b].isspace() or text[b] in delimiters
    if not right and text[b] == ".": right = b+1 == len(text) or text[b+1].isspace()
    return left and right


def ground(intake, ref_key, proposed, *, whole_answer=False):
    if not isinstance(intake,TrustedInput) or not intake.trusted: return None
    spans = [(a,b) for key,a,b in intake.spans if key == ref_key]
    if len(spans)!=1: return None
    start,end = spans[0]; raw = intake.raw_text
    if not 0 <= start < end <= len(raw): return None
    span = raw[start:end]
    # Conservative A4-1 guard: a decoder cannot elide a negation into positive
    # certainty. The whole trusted turn is checked, so a span that crops the
    # cue away cannot hide it (audit F-1).
    if negated(raw):
        return ExpressionGrounding(intake.turn_id,intake.trace_id,ref_key,None,"NEGATED_REFERENCE",None)
    comparison = proposed.strip().casefold()
    possible = []
    for a in range(start,end):
        if a != start and not (raw[a-1].isspace() or raw[a-1] in "\"'`“”‘’()[]{} ,;:!?"): continue
        for b in range(a+1,end+1):
            if raw[a:b].strip().casefold() == comparison and _boundary(raw,a,b): possible.append((a,b))
    # Strip boundary whitespace by retaining original offsets/characters.
    unique = set()
    for a,b in possible:
        while a<b and raw[a].isspace(): a+=1
        while b>a and raw[b-1].isspace(): b-=1
        unique.add((a,b))
    if len(unique)!=1: return ExpressionGrounding(intake.turn_id,intake.trace_id,ref_key,None,"UNESTABLISHED",None)
    a,b = next(iter(unique))
    return ExpressionGrounding(intake.turn_id,intake.trace_id,ref_key,(a,b),"RAW_VERBATIM",raw[a:b])


class MemoryAdapter:
    def __init__(self, sources):
        self.sources = sources

    def _ground(self, result, expression):
        q = result.query
        receipt = ground(q.intake,q.ref_key,expression)
        if receipt and receipt.status == "RAW_VERBATIM": return receipt
        span = raw_span(q)
        if span and receipt and receipt.status != "NEGATED_REFERENCE": return ground(q.intake,q.ref_key,span)
        return receipt

    def _safe(self, result, expression, *, ids=None):
        if result.collision and not result.collision.complete: return "COLLISION_SCOPE_INCOMPLETE"
        candidates = result.candidates
        ids = set(ids if ids is not None else (c.source.source_id for c in candidates))
        exact_ids = [c.source.source_id for c in candidates if expression.strip().casefold() == c.source.source_id]
        exact_titles = [c.source.source_id for c in candidates if exact_name(expression,c.source.relpath.split("/")[-1])]
        if exact_titles:
            scan = self.sources.scan()
            all_matches = tuple(sorted(l.source_id for l in scan.locators if exact_name(expression,l.relpath.split("/")[-1])))
            hidden_match = any(exact_name(expression,name) for name in scan.hidden_names)
            if not scan.complete or hidden_match or not set(all_matches)<=ids: return "COLLISION_SCOPE_INCOMPLETE"
            if result.collision and scan.snapshot_digest != result.collision.snapshot_digest: return "SNAPSHOT_INVALIDATED"
        if any(c.source.identity_status != I.HASH_VERIFIED for c in candidates): return "HASH_IDENTITY_DEGRADED"
        for c in candidates:
            if not self.sources.verify_source(c.source.source_id,c.source.content_sha256): return "SNAPSHOT_INVALIDATED"
        if result.collision:
            scan = self.sources.scan()
            if scan.snapshot_digest != result.collision.snapshot_digest: return "SNAPSHOT_INVALIDATED"
        if exact_ids and not set(exact_ids)<=ids: return "UNAUTHORIZED_IDENTIFIER"
        return None

    def project(self, result: RetrievalResult, *, local_evidence=None, slot_count=1, distinct_files=False):
        if result.degraded: return Projection(None,None,result.degraded)
        grounding = self._ground(result,result.query.reference_expression)
        if not grounding or grounding.status != "RAW_VERBATIM": return Projection(None,grounding,"EXPRESSION_GROUNDING_UNESTABLISHED")
        expression = grounding.raw_expression
        failure = self._safe(result,expression)
        if failure: return Projection(None,grounding,failure)
        q = result.query
        attachments=authorized_attachments(q)
        candidates = tuple(RARCandidate(c.source.source_id,c.source.relpath.split("/")[-1],c.source.media_type,
                           recency_rank=n,is_attachment=c.source.source_id in attachments,
                           exact_aliases=()) for n,c in enumerate(result.candidates))
        anchor = None
        if len(attachments)==1:
            attached = next((c for c in candidates if c.id==attachments[0]),None)
            classes = {TYPE_WORDS[w] for w in words(raw_span(q) or "") if w in TYPE_WORDS}
            explicit_conflict = any(expression.strip().casefold() in (c.id,c.title.casefold()) and c.id != (attached.id if attached else None) for c in candidates)
            # Raw type guard also applied in single-slot cases when type words exist.
            eligible = attached and not explicit_conflict and (not classes or classes=={attached.candidate_type})
            if slot_count>1: eligible = eligible and classes=={attached.candidate_type} and not distinct_files
            supplied = local_evidence or RAREvidence()
            if supplied.target_type_hint and attached and supplied.target_type_hint != attached.candidate_type: eligible=False
            trusted_classes=dict(q.attachment_manifest.media_classes)
            if attached and attached.id in trusted_classes and trusted_classes[attached.id]!=attached.candidate_type: eligible=False
            if eligible: anchor = RARDeterministicAnchor(current_attachment_id=attached.id)
        # Model evidence cannot furnish recency/type/negation certainty. Derive from raw.
        evidence = RAREvidence(clause_text=expression)
        projected = RARQuery(expression,candidates,evidence,anchor)
        if len(candidates)>q.max_candidates or len(canonical(projected))>q.max_bytes: return Projection(None,grounding,"BUDGET_EXCEEDED")
        return Projection(projected,grounding)

    def candidate_fact_sources(self, result):
        return {c.source.source_id:{axis:c.locator for axis in ("title","type","owner","recency")} for c in result.candidates}

    def register(self, service, built, result, frozen_query):
        failure = self._safe(result,frozen_query.reference_expression)
        if failure: return BindingResult(BindingState.PENDING,reason=failure)
        return service.register(built,frozen_query)

    def respond_selection(self, service, result, frozen_query, response, *, user_selection,
                          wrong_binding_impact="CONSEQUENTIAL"):
        """Explicit UI selections are supplied by trusted UI event intake only."""
        if (not isinstance(user_selection,TrustedInput) or not user_selection.trusted
                or user_selection.round_id != response.ambiguity_id
                or (user_selection.user_id,user_selection.session_id) != (result.query.user_id,result.query.session_id)
                or response.response_kind not in (ResponseKind.CANDIDATE,ResponseKind.ATTRIBUTE)):
            return BindingResult(BindingState.PENDING,reason="USER_SELECTION_REQUIRED")
        pending=service.store.rounds.get(response.ambiguity_id)
        if not pending: return BindingResult(BindingState.PENDING,reason="UNKNOWN_ROUND")
        # UI event payload must be the selected option, never a model text rewrite.
        selected=response.candidate_id if response.response_kind==ResponseKind.CANDIDATE else response.option_key
        if user_selection.raw_text != selected: return BindingResult(BindingState.PENDING,reason="UI_SELECTION_MISMATCH")
        failure=self._safe(result,frozen_query.reference_expression)
        if failure: return BindingResult(BindingState.PENDING,reason=failure)
        return service.respond(result.query.session_id,response,frozen_query,wrong_binding_impact=wrong_binding_impact)

    def respond_free_input(self, service, result, frozen_query, round_id, answer_intake, *, proposed_text=None,
                           proposed_offsets=None, wrong_binding_impact="CONSEQUENTIAL"):
        q = result.query
        pending = service.store.rounds.get(round_id)
        if (not pending or not isinstance(answer_intake,TrustedInput) or not answer_intake.trusted
                or (answer_intake.user_id,answer_intake.session_id) != (q.user_id,q.session_id)
                or answer_intake.round_id != round_id or answer_intake.turn_id == q.intake.turn_id
                or answer_intake.trace_id == q.intake.trace_id):
            return BindingResult(BindingState.PENDING,reason="ANSWER_GROUNDING_UNESTABLISHED")
        if pending.contract.session_id != q.session_id: return BindingResult(BindingState.PENDING,reason="ANSWER_ASSOCIATION_MISMATCH")
        # Never forward proposed_text. Whole trusted raw answer is the conservative fallback.
        expression = answer_intake.raw_text
        if proposed_offsets is not None:
            try:
                a,b = proposed_offsets
                if not 0 <= a < b <= len(expression): raise ValueError()
                receipt = ground(answer_intake,q.ref_key,expression[a:b],whole_answer=True)
            except (ValueError,TypeError): receipt=None
        else: receipt = ground(answer_intake,q.ref_key,expression,whole_answer=True)
        if not receipt or receipt.status != "RAW_VERBATIM": return BindingResult(BindingState.PENDING,reason="ANSWER_GROUNDING_UNESTABLISHED")
        expression = receipt.raw_expression
        failure = self._safe(result,expression,ids=pending.contract.scope_candidate_ids)
        if failure: return BindingResult(BindingState.PENDING,reason=failure)
        response = ClarificationResponse(round_id,ResponseKind.FREE_INPUT,text=expression)
        return service.respond(q.session_id,response,frozen_query,wrong_binding_impact=wrong_binding_impact)
