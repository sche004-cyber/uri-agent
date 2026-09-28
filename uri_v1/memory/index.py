"""Validated logical history. Task heads follow causal edges, never timestamps."""
from __future__ import annotations

from .contracts import RecordKind as K, Provenance as P, TaskStatus as S, VerificationStatus as V, canonical, digest

_TERMINAL = {S.COMPLETED, S.FAILED, S.ABANDONED}
_TRANSITIONS = {
    S.OPEN: {S.PAUSED, S.WAITING_USER, S.COMPLETED, S.FAILED, S.ABANDONED},
    S.WAITING_USER: {S.OPEN, S.PAUSED, S.COMPLETED, S.FAILED, S.ABANDONED},
    S.PAUSED: {S.OPEN, S.COMPLETED, S.FAILED, S.ABANDONED},
}


class MemoryIndex:
    def __init__(self, user_id, protected):
        self.user_id = user_id
        self.protected = protected
        self.records = {}
        self.superseded = set()
        self.hidden = set()
        self.openings = {}
        self.state_heads = {}
        self.source_refs = {}
        self.recovery_ids = ()

    @property
    def pending_corrections(self):
        paired = {r.payload.get("correction_record_id") for r in self.records.values() if r.kind == K.TASK_STATE}
        return tuple(r.record_id for r in self.records.values() if r.kind == K.CORRECTION and r.record_id not in paired)

    @property
    def conflicts(self):
        return {task: tuple(sorted(heads)) for task, heads in self.state_heads.items() if len(heads) > 1}

    def task(self, task_id):
        heads = self.state_heads.get(task_id, set()) - self.hidden
        if len(heads) != 1 or self.openings.get(task_id) in self.hidden: return None
        return self.records[next(iter(heads))]

    def current(self, kind=None, task_id=None):
        pending = set(self.pending_corrections)
        return tuple(r for rid,r in self.records.items() if rid not in self.superseded | self.hidden | pending
                     and (kind is None or r.kind == kind) and (task_id is None or r.task_id == task_id)
                     and (r.task_id is None or self.openings.get(r.task_id) not in self.hidden))

    def history(self, record_id):
        visited = set()
        def walk(rid):
            if rid in visited: return []
            visited.add(rid); r = self.records[rid]
            return [x for parent in r.supersedes for x in walk(parent)] + [r]
        return tuple(walk(record_id))

    def _events(self, r):
        ids = r.payload.get("transition_evidence_ids", ())
        if not ids: raise ValueError("TRUSTED_EVENT_REQUIRED")
        result = []
        for eid in ids:
            e = self.protected("events", eid)
            if (not e or e.get("user_id") != self.user_id or e.get("task_id") != r.task_id
                    or e.get("trace_id") != r.trace_id or e.get("session_id") != r.session_id):
                raise ValueError("INVALID_TRANSITION_EVIDENCE")
            if e.get("record_ids") is None or r.record_id not in e["record_ids"]: raise ValueError("EVENT_RECORD_MISMATCH")
            if e.get("record_digests", {}).get(r.record_id) != digest(r.to_dict()): raise ValueError("EVENT_PAYLOAD_MISMATCH")
            result.append(e)
        return result

    def accept(self, r, *, writing=False):
        if r.user_id != self.user_id: raise ValueError("CROSS_USER_RECORD")
        if r.record_id in self.records:
            if canonical(r.to_dict()) != canonical(self.records[r.record_id].to_dict()): raise ValueError("ID_CONFLICT")
            return
        parents = []
        for rid in r.supersedes:
            if rid not in self.records or rid in self.hidden: raise ValueError("INVALID_SUPERSESSION_TARGET")
            parent = self.records[rid]
            if parent.task_id != r.task_id: raise ValueError("CROSS_TASK_SUPERSESSION")
            parents.append(parent)
        events = []
        if r.kind in (K.TASK_OPENED, K.TASK_STATE, K.CORRECTION, K.TOMBSTONE): events = self._events(r)
        if r.kind == K.TASK_OPENED:
            if r.supersedes or r.task_id in self.openings or r.payload["origin_turn_trace_id"] != r.trace_id:
                raise ValueError("INVALID_TASK_OPENING")
            if not all(e["actor"] == "USER" and e["action"] == "OPEN" for e in events): raise ValueError("USER_TASK_REQUEST_REQUIRED")
        elif r.kind == K.TASK_STATE:
            opening = self.records.get(r.payload["opening_record_id"])
            if not opening or opening.kind != K.TASK_OPENED or opening.task_id != r.task_id: raise ValueError("INVALID_OPENING_LINK")
            heads = self.state_heads.get(r.task_id, set())
            if not parents:
                if heads or r.payload["status"] != S.OPEN: raise ValueError("INVALID_INITIAL_STATE")
            else:
                if len(parents) != 1 or parents[0].kind != K.TASK_STATE: raise ValueError("STATE_NEEDS_ONE_PARENT")
                parent = parents[0]
                if writing and heads != {parent.record_id}: raise ValueError("CONFLICT")
                old, new = S(parent.payload["status"]), S(r.payload["status"])
                correction = r.payload.get("correction_record_id")
                if correction:
                    c = self.records.get(correction)
                    if (not c or c.kind != K.CORRECTION or c.task_id != r.task_id
                            or c.payload["prior_task_state_record_id"] != parent.record_id
                            or c.payload["correction_operation_id"] != r.payload.get("correction_operation_id")
                            or r.provenance != P.USER_CORRECTION): raise ValueError("INVALID_CORRECTION_PAIR")
                    refs = list(parent.payload["references"])
                    target = c.payload["target"]
                    if isinstance(target, str):
                        if target != parent.record_id or not c.payload.get("note") or r.payload["references"] != parent.payload["references"]: raise ValueError("INVALID_STATE_CORRECTION")
                    else:
                        key = target["ref_key"]
                        replacement = next((x for x in r.payload["references"] if x["ref_key"] == key), None)
                        prior = next((x for x in refs if x["ref_key"] == key), None)
                        if (not prior or not replacement or prior["source_id"] != c.payload["wrong_source_id"]
                                or replacement["source_id"] != c.payload["right_source_id"]
                                or replacement["content_sha256"] != c.payload["new_source_ref"]["content_sha256"]
                                or replacement["binding_id"] != c.payload["new_binding_id"]
                                or replacement["binding_tier"] != c.payload["new_binding_tier"]
                                or old != new): raise ValueError("INVALID_REFERENCE_CORRECTION")
                        expected = tuple(replacement if x["ref_key"] == key else x for x in refs)
                        if expected != r.payload["references"]: raise ValueError("CORRECTION_CHANGED_OTHER_SLOTS")
                else:
                    if old != new and (old in _TERMINAL or new not in _TRANSITIONS.get(old, ())): raise ValueError("INVALID_TRANSITION")
                    old_refs = {x["ref_key"]:x for x in parent.payload["references"]}
                    if any(key not in {x["ref_key"] for x in r.payload["references"]} for key in old_refs): raise ValueError("REFERENCE_REMOVAL_NEEDS_CORRECTION")
                    for ref in r.payload["references"]:
                        if ref["ref_key"] in old_refs and ref != old_refs[ref["ref_key"]]: raise ValueError("REFERENCE_REPLACEMENT_NEEDS_CORRECTION")
                actor = events[0]["actor"]; action = events[0]["action"]
                if r.provenance in (P.USER_PROVIDED, P.USER_CORRECTION) and actor != "USER": raise ValueError("USER_EVIDENCE_REQUIRED")
                if old != new and not correction:
                    required = {S.PAUSED:{"PAUSE","INTERRUPTION"},S.OPEN:{"RESUME"},S.WAITING_USER:{"CLARIFICATION"},
                                S.COMPLETED:{"COMPLETE","VERIFIED_COMPLETE"},S.FAILED:{"FAILURE","FAILED"},S.ABANDONED:{"CANCEL"}}[new]
                    if action not in required: raise ValueError("TRANSITION_ACTION_MISMATCH")
                    if new == S.ABANDONED and actor != "USER": raise ValueError("USER_CANCEL_REQUIRED")
                    if new == S.COMPLETED and r.provenance == P.URI_RECORDED:
                        verdict = self.records.get(r.payload.get("last_outcome_record_id"))
                        links = {(x["source_id"],x["content_sha256"]) for x in r.payload["references"]}
                        if (not verdict or verdict.task_id != r.task_id or verdict.provenance != P.VERIFIER_RESULT
                                or verdict.payload["verification_status"] != V.VERIFIED
                                or not links <= {(x["source_id"],x["content_sha256"]) for x in verdict.payload["inputs"]}): raise ValueError("VERIFIED_CURRENT_REFERENCES_REQUIRED")
            if "last_outcome_record_id" in r.payload:
                outcome = self.records.get(r.payload["last_outcome_record_id"])
                if not outcome or outcome.kind != K.OUTCOME or outcome.task_id != r.task_id: raise ValueError("INVALID_OUTCOME_LINK")
        elif r.kind == K.OUTCOME:
            if r.task_id not in self.openings: raise ValueError("UNKNOWN_TASK")
            if r.provenance == P.EXECUTION_OUTCOME:
                if r.supersedes or any(k.startswith("verifier_") or k in ("attestation_ref","assessed_outcome_record_id","invocation_id","acceptance_evidence_ref","acceptance_evidence_digest") for k in r.payload): raise ValueError("CLAIM_CANNOT_ATTEST")
            else:
                from .recorder import _VERIFIERS
                registered = _VERIFIERS.get(r.payload.get("verifier_id"))
                if not registered or registered[:2] != (r.payload.get("verifier_type"),r.payload.get("verifier_version")): raise ValueError("UNREGISTERED_VERIFIER")
                assessed = self.records.get(r.payload.get("assessed_outcome_record_id"))
                if (not assessed or assessed.kind != K.OUTCOME or assessed.provenance != P.EXECUTION_OUTCOME
                        or assessed.task_id != r.task_id or assessed.payload["attempt_id"] != r.payload["attempt_id"]
                        or assessed.payload["inputs"] != r.payload["inputs"] or assessed.payload["outputs"] != r.payload["outputs"]
                        or not r.payload["evidence_ids"]): raise ValueError("INVALID_ASSESSMENT_LINK")
                receipt = self.protected("attestations", r.payload.get("attestation_ref", ""))
                if not receipt or receipt.get("record_digest") != digest(r.to_dict()) or receipt.get("producer") != r.payload["verifier_id"]: raise ValueError("INVALID_ATTESTATION")
                if len(parents) != 1 or parents[0].kind != K.OUTCOME: raise ValueError("VERDICT_NEEDS_ASSESSMENT_PARENT")
                if parents[0].record_id != assessed.record_id and parents[0].payload.get("assessed_outcome_record_id") != assessed.record_id: raise ValueError("VERDICT_ATTEMPT_MISMATCH")
        elif r.kind == K.CORRECTION:
            head = self.task(r.task_id)
            prior = self.records.get(r.payload["prior_task_state_record_id"])
            if not prior or prior.kind != K.TASK_STATE or prior.task_id != r.task_id: raise ValueError("INVALID_CORRECTION_HEAD")
            if writing and (not head or head.record_id != prior.record_id): raise ValueError("CONFLICT")
            if not all(e["actor"] == "USER" and e["action"] == "CORRECT" for e in events): raise ValueError("USER_CORRECTION_REQUIRED")
            if any(p.kind != K.CORRECTION or p.payload["target"] != r.payload["target"] for p in parents): raise ValueError("INCOMPATIBLE_CORRECTION")
        elif r.kind == K.TOMBSTONE:
            if r.supersedes or any(t not in self.records for t in r.payload["target_record_ids"]): raise ValueError("INVALID_HIDE_TARGET")
            if not all(e["actor"] == "USER" and e["action"] == "FORGET" for e in events): raise ValueError("USER_FORGET_REQUIRED")
        elif r.kind == K.DERIVATIVE:
            if r.supersedes or r.task_id not in self.openings: raise ValueError("INVALID_DERIVATIVE")
        elif r.supersedes: raise ValueError("SUPERSESSION_NOT_ALLOWED")
        self.records[r.record_id] = r
        if r.kind != K.CORRECTION: self.superseded.update(r.supersedes)
        if r.kind == K.TASK_OPENED: self.openings[r.task_id] = r.record_id
        if r.kind == K.TASK_STATE:
            if r.payload.get("correction_record_id"):
                self.superseded.update(self.records[r.payload["correction_record_id"]].supersedes)
            heads = self.state_heads.setdefault(r.task_id, set())
            heads.difference_update(r.supersedes); heads.add(r.record_id)
        if r.kind == K.SOURCE_OBSERVED:
            for ref in r.source_refs: self.source_refs[ref.source_id] = ref
        if r.kind == K.TOMBSTONE: self.hidden.update(r.payload["target_record_ids"])

    def open_tasks(self, *, statuses=(S.OPEN, S.WAITING_USER, S.PAUSED), time_window=None, label_tokens=(), source_class=None, max_tasks=10000):
        result = []
        for task_id in self.openings:
            state = self.task(task_id)
            if not state or state.payload["status"] not in statuses: continue
            opening = self.records[self.openings[task_id]]
            from .contracts import timestamp
            if time_window and not timestamp(time_window[0]) <= timestamp(opening.recorded_at) < timestamp(time_window[1]): continue
            import re
            words = set(re.findall(r"\w+", opening.payload["objective_label"].casefold()))
            for label in opening.payload.get("explicit_user_labels", ()): words.update(re.findall(r"\w+", label.casefold()))
            if label_tokens and not words.intersection(label_tokens): continue
            ids = tuple(x["source_id"] for x in state.payload["references"])
            if source_class and not any(self.source_refs.get(i) and self.source_refs[i].media_type == source_class for i in ids): continue
            result.append({"task_id":task_id,"objective_label":opening.payload["objective_label"],"opened_at":opening.recorded_at,
                           "last_state_at":state.recorded_at,"status":state.payload["status"],"source_ids":ids,"binding_authority":"HISTORICAL_BINDING"})
        result.sort(key=lambda x:x["task_id"])
        result.sort(key=lambda x:x["last_state_at"],reverse=True)
        if len(result) > max_tasks: raise ValueError("BUDGET_EXCEEDED")
        return tuple(result)
