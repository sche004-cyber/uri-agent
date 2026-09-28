"""Task-scoped bounded context; facts retain provenance and historical authority."""
from __future__ import annotations

from dataclasses import dataclass
from .contracts import RecordKind as K, Authority, Freshness as F, canonical, freeze, plain


@dataclass(frozen=True)
class MemoryContextPackage:
    content: object

    def __post_init__(self): object.__setattr__(self,"content",freeze(self.content))

    def to_dict(self): return plain(self.content)


def build_context(index, sources, task_id, *, max_bytes=8192, result_heads=None):
    base = {"schema_version":"m36.context.v1","task":None,"references":[],"recent_outcomes":[],
            "derivatives":[],"corrections":[],"stale":[],"conflicts":[],
            "provenance_legend":{a.value:a.value.replace("_"," ").lower() for a in Authority},"degraded":None}
    state = index.task(task_id)
    if task_id in index.conflicts:
        base["conflicts"] = [{"task_id":task_id,"record_ids":index.conflicts[task_id]}]; base["degraded"]="CONFLICT"
    if not state: return MemoryContextPackage(base)
    opening = index.records[index.openings[task_id]]
    base["task"] = {"task_id":task_id,"objective_label":opening.payload["objective_label"],"status":state.payload["status"],
                    "next_step":plain(state.payload.get("next_step")),"last_outcome_record_id":state.payload.get("last_outcome_record_id"),
                    "authority":state.authority,"provenance":state.provenance}
    current = {x["source_id"]:x["content_sha256"] for x in state.payload["references"]}
    def recorded_ref(sid,sha):
        return next((s for r in reversed(tuple(index.records.values())) if r.task_id in (None,task_id)
                     for s in r.source_refs if s.source_id==sid and s.content_sha256==sha),index.source_refs.get(sid))
    def fresh(sid,sha):
        ref = recorded_ref(sid,sha)
        if not ref: return F.UNKNOWN
        if sha is None: return F.UNKNOWN
        if ref.content_sha256 != sha: return F.STALE_SOURCE
        return sources.freshness(ref)
    for link in state.payload["references"]:
        ref = recorded_ref(link["source_id"],link["content_sha256"])
        f = fresh(link["source_id"],link["content_sha256"])
        item = {**plain(link),"display_name":ref.relpath.split("/")[-1] if ref else "unavailable",
                "freshness":f,"identity_status":ref.identity_status if ref else "SOURCE_MISSING",
                "authority":state.authority,"provenance":state.provenance,"task_id":task_id,
                "binding_authority":"HISTORICAL_BINDING"}
        base["references"].append(item)
        if f != F.CURRENT: base["stale"].append(item)
    def lineage(links,derivative=False):
        if any(x["source_id"] not in current or x["content_sha256"] != current[x["source_id"]] for x in links): return F.SUPERSEDED_REFERENCE
        states = [fresh(x["source_id"],x["content_sha256"]) for x in links]
        if any(f in (F.STALE_SOURCE,F.SOURCE_MISSING) for f in states): return F.DERIVATIVE_STALE if derivative else F.STALE_SOURCE
        if not states or F.UNKNOWN in states: return F.UNKNOWN
        return F.CURRENT
    outcomes = list(index.current(K.OUTCOME,task_id))
    # Preserve the most recent verifier verdict and the checkpoint's linked
    # outcome even when later unverified claims fill the recent window.
    selected = {r.record_id:r for r in outcomes[-3:]}
    attested = [r for r in outcomes if r.authority in (Authority.VERIFIED_OUTCOME,Authority.VERIFIER_ATTESTED)]
    if attested: selected[attested[-1].record_id] = attested[-1]
    linked = state.payload.get("last_outcome_record_id")
    for r in outcomes:
        if r.record_id == linked: selected[r.record_id] = r
    for r in selected.values():
        f = lineage(r.payload["inputs"])
        item = {"record_id":r.record_id,"task_id":task_id,"action_label":r.payload["action_label"],
                "verification_status":r.payload["verification_status"],"authority":r.authority,"provenance":r.provenance,
                "recorded_at":r.recorded_at,"freshness":f,"inputs":plain(r.payload["inputs"]),"outputs":plain(r.payload["outputs"])}
        base["recent_outcomes"].append(item)
        if f!=F.CURRENT: base["stale"].append(item)
    for r in list(index.current(K.DERIVATIVE,task_id))[-3:]:
        f = lineage(r.payload["derived_from"],True)
        if result_heads is not None and result_heads.get(r.payload["result_id"]) != r.payload["result_version"]:
            f = F.SUPERSEDED_REFERENCE
        item = {**plain(r.payload),"record_id":r.record_id,"task_id":task_id,"freshness":f,"authority":r.authority,"provenance":r.provenance}
        base["derivatives"].append(item)
        if f!=F.CURRENT: base["stale"].append(item)
    for r in list(index.current(K.CORRECTION,task_id))[-3:]:
        base["corrections"].append({"record_id":r.record_id,"task_id":task_id,"target":plain(r.payload["target"]),
            "right_source_id":r.payload.get("right_source_id"),"recorded_at":r.recorded_at,"authority":r.authority,"provenance":r.provenance})
    pending = [rid for rid in index.pending_corrections if index.records[rid].task_id == task_id]
    if pending: base["degraded"] = "PENDING_CORRECTION"
    elif index.recovery_ids: base["degraded"] = "QUARANTINED_RECORDS"
    if len(canonical(base))>max_bytes:
        base.update(task=None,references=[],recent_outcomes=[],derivatives=[],corrections=[],stale=[],conflicts=[],degraded="BUDGET_EXCEEDED")
    if len(canonical(base))>max_bytes: raise ValueError("PACKAGE_BUDGET_TOO_SMALL")
    return MemoryContextPackage(base)
