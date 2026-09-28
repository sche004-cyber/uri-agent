"""Best-effort ids/enums/counts only; telemetry cannot fail a Memory write."""
from datetime import datetime, timezone
from uri_v1.user_storage import locked_append
from .contracts import canonical, require_trace_id


class Telemetry:
    def __init__(self,log): self.log=log

    def query(self,result):
        intake=result.query.intake
        if intake is None or not getattr(intake,"trusted",False): return False
        data={"trace_id":require_trace_id(intake.trace_id),"event":"RETRIEVAL",**dict(result.telemetry),"degraded":result.degraded}
        return self._append(data)

    def write(self,result,trace_id):
        return self._append({"trace_id":require_trace_id(trace_id),"event":"WRITE","persisted":result.persisted,
                             "record_ids":result.record_ids,"per_record":result.per_record,"recovery_ids":result.recovery_ids})

    def _append(self,data):
        try:
            p=self.log.path / ("telemetry-"+datetime.now(timezone.utc).strftime("%Y-%m")+".jsonl")
            with locked_append(str(p)) as stream: stream.write(canonical(data)+b"\n")
            return True
        except (OSError,ValueError): return False
