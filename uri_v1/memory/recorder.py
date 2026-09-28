"""Typed trusted writer and bootstrap-only verifier invocation boundary."""
from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
import uuid

from .contracts import (MemoryRecord, RecordKind as K, Provenance as P, TaskStatus as S,
                        VerificationStatus as V, WriteResult, TrustedInput, BoundReference,
                        IdentityStatus as I, canonical, digest, plain, utc_now, negated)

# Populated only by trusted bootstrap in this module; no public registration API.
_VERIFIERS = MappingProxyType({})
_VERIFIER_CAPABILITY = object()
_RUNTIME_CAPABILITY = object()


@dataclass(frozen=True)
class _RuntimeObservation:
    action: str
    session_id: str
    trace_id: str
    capability: object

    def __reduce__(self): raise TypeError("runtime observations cannot be serialized")


def _runtime_observation(intake, action):
    """Trusted URI producer hook, not exposed to model/tool/user dictionaries."""
    if not isinstance(intake,TrustedInput) or not intake.trusted: raise ValueError("TRUSTED_INTAKE_REQUIRED")
    return _RuntimeObservation(action,intake.session_id,intake.trace_id,_RUNTIME_CAPABILITY)


def _bootstrap_verifiers(entries):
    """Trusted application/qualification bootstrap only, never a tool/data API."""
    global _VERIFIERS
    if _VERIFIERS: raise ValueError("VERIFIER_REGISTRY_ALREADY_FROZEN")
    for key, entry in entries.items():
        if not key.startswith("uri.verifier.") or len(entry) != 3 or not callable(entry[2]): raise ValueError("invalid verifier bootstrap")
    _VERIFIERS = MappingProxyType(dict(entries))


class Recorder:
    def __init__(self, log, sources, *, clock=utc_now):
        self.log, self.sources, self.clock = log, sources, clock

    def _trusted(self, intake):
        if not isinstance(intake, TrustedInput) or not intake.trusted or intake.user_id != self.log.user_id:
            raise ValueError("TRUSTED_USER_INPUT_REQUIRED")

    def _record(self, kind, provenance, payload, *, intake=None, task_id=None, session_id=None,
                trace_id=None, supersedes=(), source_refs=(), subject_ids=(), record_id=None):
        args = dict(user_id=self.log.user_id,kind=kind,provenance=provenance,payload=payload,
                    task_id=task_id,session_id=intake.session_id if intake else session_id,
                    trace_id=intake.trace_id if intake else trace_id,recorded_at=self.clock(),
                    supersedes=supersedes,source_refs=source_refs,subject_ids=subject_ids)
        if record_id: args["record_id"] = record_id
        return MemoryRecord(**args)

    def _event(self, records, actor, action, eid):
        r = records[0]
        event = {"user_id":r.user_id,"task_id":r.task_id,"session_id":r.session_id,"trace_id":r.trace_id,
                 "actor":actor,"action":action,"record_ids":[x.record_id for x in records],
                 "record_digests":{x.record_id:digest(x.to_dict()) for x in records}}
        self.log.put_protected("events",eid,event)

    def open_task(self, intake, objective_label, *, explicit_user_labels=(), task_id=None):
        self._trusted(intake)
        if objective_label.casefold() not in intake.raw_text.casefold() or any(x.casefold() not in intake.raw_text.casefold() for x in explicit_user_labels):
            raise ValueError("OBJECTIVE_NOT_USER_PROVIDED")
        task_id = task_id or uuid.uuid4().hex
        eid = uuid.uuid4().hex
        opening = self._record(K.TASK_OPENED,P.USER_PROVIDED,
            {"objective_label":objective_label,"origin_turn_trace_id":intake.trace_id,
             "explicit_user_labels":explicit_user_labels,"transition_evidence_ids":(eid,)},intake=intake,task_id=task_id)
        state = self._record(K.TASK_STATE,P.URI_RECORDED,
            {"status":S.OPEN,"references":(),"opening_record_id":opening.record_id,"transition_evidence_ids":(eid,)},intake=intake,task_id=task_id)
        with self.log.guard():
            if not self.log.durable_enabled(): return task_id,WriteResult(False,"DURABLE_OFF")
            self._event((opening,state),"USER","OPEN",eid)
            return task_id,self.log.append_unlocked((opening,state))

    def observe(self, source, *, session_id, trace_id):
        live = self.sources.fingerprint(source)
        if live is None: return WriteResult(False,"SOURCE_MISSING")
        return self.log.append((self._record(K.SOURCE_OBSERVED,P.SOURCE_OBSERVED,{},session_id=session_id,
                                             trace_id=trace_id,source_refs=(live,),subject_ids=(live.source_id,)),))

    def _binding(self, bound, session_id):
        if (not isinstance(bound,BoundReference) or not bound.trusted or bound.user_id != self.log.user_id
                or bound.session_id != session_id or bound.source.identity_status != I.HASH_VERIFIED
                or not self.sources.verify_source(bound.source.source_id,bound.source.content_sha256)):
            raise ValueError("FRESH_S1_BINDING_REQUIRED")
        return {"ref_key":bound.ref_key,"source_id":bound.source.source_id,"content_sha256":bound.source.content_sha256,
                "binding_tier":bound.binding_tier,"binding_id":bound.binding_id}

    def task_state(self, task_id, expected_head_record_id, *, intake, status=None, bindings=(), next_step=None,
                   last_outcome_record_id=None, runtime_action=None):
        self._trusted(intake)
        with self.log.guard():
            index = self.log.load_unlocked(); head = index.task(task_id)
            if not head or head.record_id != expected_head_record_id: return WriteResult(False,"CONFLICT")
            p = plain(head.payload); p.pop("correction_record_id",None); p.pop("correction_operation_id",None)
            old = S(p["status"]); new = S(status or old); eid = uuid.uuid4().hex
            actor, action, prov = "RUNTIME","CHECKPOINT",P.URI_RECORDED
            if old != new:
                action = {S.PAUSED:"PAUSE",S.OPEN:"RESUME",S.COMPLETED:"COMPLETE",S.FAILED:"FAILED",S.ABANDONED:"CANCEL",S.WAITING_USER:"CLARIFICATION"}[new]
                if runtime_action:
                    if (not isinstance(runtime_action,_RuntimeObservation) or runtime_action.capability is not _RUNTIME_CAPABILITY
                            or (runtime_action.session_id,runtime_action.trace_id)!=(intake.session_id,intake.trace_id)
                            or runtime_action.action not in ("INTERRUPTION","CLARIFICATION","FAILURE","VERIFIED_COMPLETE")): raise ValueError("INVALID_RUNTIME_OBSERVATION")
                    action = runtime_action.action
                else:
                    actor,prov = "USER",P.USER_PROVIDED
                    allowed = {S.PAUSED:("pause",),S.OPEN:("resume","continue"),S.COMPLETED:("complete","completed","done"),
                               S.FAILED:("failed","failure"),S.ABANDONED:("cancel","abandon"),S.WAITING_USER:()}
                    # A negated keyword ("not done yet") is not an explicit declaration (audit F-2).
                    if negated(intake.raw_text) or not set(re.findall(r"\w+",intake.raw_text.casefold())).intersection(allowed[new]):
                        raise ValueError("EXPLICIT_USER_TRANSITION_REQUIRED")
                if new == S.OPEN: prov = P.URI_RECORDED  # URI accepts the user resume event.
            p["status"] = new; p["transition_evidence_ids"] = (eid,)
            refs = list(p["references"])
            for bound in bindings:
                ref = self._binding(bound,intake.session_id)
                existing = next((x for x in refs if x["ref_key"] == ref["ref_key"]),None)
                if existing and existing != ref: return WriteResult(False,"REFERENCE_REPLACEMENT_NEEDS_CORRECTION")
                if not existing: refs.append(ref)
            p["references"] = refs
            if next_step is not None: p["next_step"] = {"text":next_step,"provenance":P.MODEL_DERIVED}
            if last_outcome_record_id is not None: p["last_outcome_record_id"] = last_outcome_record_id
            record = self._record(K.TASK_STATE,prov,p,intake=intake,task_id=task_id,supersedes=(head.record_id,),
                                  source_refs=tuple(b.source for b in bindings))
            if not self.log.durable_enabled(): return WriteResult(False,"DURABLE_OFF")
            self._event((record,),actor,action,eid)
            return self.log.append_unlocked((record,))

    def outcome(self, task_id, *, action_label, inputs, outputs=(), evidence_ids=(), session_id, trace_id,
                failed=False, exit_code=None, attempt_id=None, **untrusted):
        if untrusted: raise ValueError("OUTCOME_AUTHORITY_CANNOT_BE_CALLER_ASSIGNED")
        payload = {"action_label":action_label,"verification_status":V.FAILED if failed else V.CLAIMED_ONLY,
                   "inputs":inputs,"outputs":outputs,"evidence_ids":evidence_ids,"attempt_id":attempt_id or uuid.uuid4().hex}
        if exit_code is not None: payload["exit_code"] = exit_code
        record = self._record(K.OUTCOME,P.EXECUTION_OUTCOME,payload,task_id=task_id,session_id=session_id,trace_id=trace_id)
        return self.log.append((record,))

    def invoke_verifier(self, assessed_outcome_record_id, verifier_id, *, trace_id, session_id):
        """Invoke registered trusted code; never accept a serialized verdict/receipt."""
        registered = _VERIFIERS.get(verifier_id)
        if not registered: raise ValueError("UNREGISTERED_VERIFIER")
        with self.log.guard():
            index = self.log.load_unlocked(); claim = index.records.get(assessed_outcome_record_id)
            if not claim or claim.kind != K.OUTCOME or claim.provenance != P.EXECUTION_OUTCOME: raise ValueError("CLAIM_REQUIRED")
            if not self.log.durable_enabled(): return WriteResult(False,"DURABLE_OFF")
            # Live identity is checked before handing immutable evidence to the producer.
            for link in tuple(claim.payload["inputs"]) + tuple(x for x in claim.payload["outputs"] if "source_id" in x):
                if not self.sources.verify_source(link["source_id"],link["content_sha256"]): return WriteResult(False,"VERIFIER_SOURCE_NOT_CURRENT")
            verdict, evidence_ids, acceptance = registered[2](claim, self.sources)
            status = V(verdict)
            if status == V.CLAIMED_ONLY or not evidence_ids: raise ValueError("INVALID_VERIFIER_VERDICT")
            payload = plain(claim.payload)
            invocation = uuid.uuid4().hex; receipt = uuid.uuid4().hex
            payload.update(verification_status=status,verifier_id=verifier_id,verifier_type=registered[0],verifier_version=registered[1],
                           invocation_id=invocation,assessed_outcome_record_id=claim.record_id,acceptance_evidence_ref=invocation,
                           acceptance_evidence_digest=digest(acceptance),attestation_ref=receipt,evidence_ids=evidence_ids)
            prior = next((r for r in reversed(index.current(K.OUTCOME,claim.task_id)) if r.payload.get("assessed_outcome_record_id") == claim.record_id),claim)
            record = self._record(K.OUTCOME,P.VERIFIER_RESULT,payload,task_id=claim.task_id,session_id=session_id,trace_id=trace_id,supersedes=(prior.record_id,))
            return self._verifier_write(record,registered[2],_VERIFIER_CAPABILITY)

    def _verifier_write(self, record, producer, capability):
        registered = _VERIFIERS.get(record.payload["verifier_id"])
        if capability is not _VERIFIER_CAPABILITY or not registered or registered[2] is not producer: raise ValueError("VERIFIER_CAPABILITY_REQUIRED")
        receipt = {"producer":record.payload["verifier_id"],"record_digest":digest(record.to_dict()),
                   "acceptance_evidence_digest":record.payload["acceptance_evidence_digest"]}
        self.log.put_protected("attestations",record.payload["attestation_ref"],receipt)
        return self.log.append_unlocked((record,))

    def derivative(self, task_id, *, result_id, result_version, content_sha256, derived_from,
                   derivative_kind, session_id, trace_id):
        record = self._record(K.DERIVATIVE,P.MODEL_DERIVED,dict(result_id=result_id,result_version=result_version,
            content_sha256=content_sha256,derived_from=derived_from,derivative_kind=derivative_kind),
            task_id=task_id,session_id=session_id,trace_id=trace_id)
        return self.log.append((record,))

    def correction(self, task_id, ref_key, expected_head_record_id, *, intake, replacement=None,
                   corrected_status=None, note=None, s7_event_id=None, operation_id=None):
        self._trusted(intake)
        op = operation_id or uuid.uuid4().hex
        with self.log.guard():
            index = self.log.load_unlocked(); head = index.task(task_id)
            pending = next((c for c in index.records.values() if c.kind == K.CORRECTION and c.payload["correction_operation_id"] == op),None)
            if pending:
                if replacement and (replacement.source.source_id != pending.payload.get("right_source_id") or replacement.source.content_sha256 != pending.payload.get("new_source_ref",{}).get("content_sha256")):
                    return WriteResult(False,"ID_CONFLICT")
                state_id = uuid.uuid5(uuid.UUID(op),"state").hex
                state_path = self.log.path / "events" / (uuid.uuid5(uuid.UUID(op),"event").hex + ".json")
                if not head or (head.record_id != expected_head_record_id and head.record_id != state_id): return WriteResult(False,"CONFLICT")
                intent = self.log.protected("events",uuid.uuid5(uuid.UUID(op),"event").hex)
                raw = intent.get("pair_state") if intent else None
                if not raw or not state_path.exists(): return WriteResult(False,"PENDING_CORRECTION")
                state = MemoryRecord.from_dict(raw)
                return self.log.append_unlocked((pending,state))
            if not head or head.record_id != expected_head_record_id: return WriteResult(False,"CONFLICT")
            p = plain(head.payload); eid = uuid.uuid5(uuid.UUID(op),"event").hex
            correction_id = uuid.uuid5(uuid.UUID(op),"correction").hex
            state_id = uuid.uuid5(uuid.UUID(op),"state").hex
            p["transition_evidence_ids"] = (eid,)
            cp = {"target":head.record_id if corrected_status else {"task_id":task_id,"ref_key":ref_key},
                  "prior_task_state_record_id":head.record_id,"correction_operation_id":op,"transition_evidence_ids":(eid,)}
            if corrected_status:
                if not note: raise ValueError("STATE_CORRECTION_REASON_REQUIRED")
                if replacement: raise ValueError("STATE_CORRECTION_CANNOT_REPLACE_SOURCE")
                p["status"] = S(corrected_status); cp["note"] = note
            else:
                ref = self._binding(replacement,intake.session_id)
                if ref["ref_key"] != ref_key: raise ValueError("REF_KEY_MISMATCH")
                old = next((x for x in p["references"] if x["ref_key"] == ref_key),None)
                if not old: raise ValueError("UNKNOWN_REF_KEY")
                old_ref = next((s for r in reversed(tuple(index.records.values())) for s in r.source_refs if s.source_id == old["source_id"] and s.content_sha256 == old["content_sha256"]),None)
                if old_ref is None: raise ValueError("MISSING_PRIOR_SOURCE_EVIDENCE")
                cp.update(wrong_source_id=old["source_id"],right_source_id=ref["source_id"],old_source_ref=plain(old_ref),
                          new_source_ref=plain(replacement.source),new_binding_id=ref["binding_id"],new_binding_tier=ref["binding_tier"])
                p["references"] = [ref if x["ref_key"] == ref_key else x for x in p["references"]]
            if s7_event_id: cp["s7_event_id"] = s7_event_id
            prior_c = next((c for c in reversed(index.current(K.CORRECTION,task_id)) if c.payload["target"] == cp["target"]),None)
            correction = self._record(K.CORRECTION,P.USER_CORRECTION,cp,intake=intake,task_id=task_id,
                supersedes=(prior_c.record_id,) if prior_c else (),record_id=correction_id)
            p.update(correction_record_id=correction_id,correction_operation_id=op)
            state = self._record(K.TASK_STATE,P.USER_CORRECTION,p,intake=intake,task_id=task_id,
                supersedes=(head.record_id,),record_id=state_id,source_refs=(replacement.source,) if replacement else ())
            if not self.log.durable_enabled(): return WriteResult(False,"DURABLE_OFF")
            event = {"user_id":state.user_id,"task_id":task_id,"session_id":state.session_id,"trace_id":state.trace_id,"actor":"USER","action":"CORRECT",
                     "record_ids":[correction_id,state_id],"record_digests":{r.record_id:digest(r.to_dict()) for r in (correction,state)},"pair_state":state.to_dict()}
            self.log.put_protected("events",eid,event)
            return self.log.append_unlocked((correction,state))

    def forget(self, record_ids, *, intake):
        self._trusted(intake); eid = uuid.uuid4().hex
        record = self._record(K.TOMBSTONE,P.USER_PROVIDED,{"target_record_ids":tuple(record_ids),"reason":"USER_FORGET","transition_evidence_ids":(eid,)},intake=intake)
        with self.log.guard():
            self._event((record,),"USER","FORGET",eid)
            return self.log.append_unlocked((record,))
