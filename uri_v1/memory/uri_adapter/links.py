"""Read-only S1 binding capture and S7/S11 links."""
from uri_v1.turn.rar_clarification_contract import BindingState
from ..contracts import BoundReference, _BINDING_AUTHORITY


def capture_binding(service, binding_result, retrieval, sources, ref_key):
    bid = binding_result.binding_id
    binding = service.store.bindings.get(bid)
    if (not binding or binding.state not in (BindingState.CONFIRMED,BindingState.TENTATIVE)
            or binding.superseded_by or binding.session_id != retrieval.query.session_id
            or binding.candidate_id != binding_result.candidate_id): raise ValueError("S1_BOUND_STATE_REQUIRED")
    candidate = next((c for c in retrieval.candidates if c.source.source_id == binding.candidate_id),None)
    if not candidate or not sources.verify_source(candidate.source.source_id,candidate.source.content_sha256,retrieval.collision if retrieval.collision and retrieval.collision.complete else None): raise ValueError("BINDING_SOURCE_CHANGED")
    return BoundReference(ref_key,candidate.source,binding.state.value,bid,retrieval.query.user_id,binding.session_id,_BINDING_AUTHORITY)


def record_derivative(recorder, ledger, version, task_id, *, derived_from, derivative_kind, session_id, trace_id):
    versions = ledger.versions(version.result_id)
    if not any(v == version for v in versions): raise ValueError("S11_VERSION_REQUIRED")
    return recorder.derivative(task_id,result_id=version.result_id,result_version=version.version,
        content_sha256=version.content_sha256,derived_from=derived_from,derivative_kind=derivative_kind,
        session_id=session_id,trace_id=trace_id)


def correction_event_id(store, event):
    if not any(e == event for e in store.session_events(event.session_id)): raise ValueError("S7_EVENT_REQUIRED")
    if event.event_type.value not in ("CHANGE","EDIT_CORRECTION"): raise ValueError("S7_CORRECTION_EVENT_REQUIRED")
    return event.event_id
