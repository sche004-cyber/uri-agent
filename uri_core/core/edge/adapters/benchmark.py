"""Reproducible Batch-B qualification harness with no network or host execution."""
from __future__ import annotations
import hashlib, json, math, platform, time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

@dataclass(frozen=True)
class BenchmarkCandidate:
    candidate_id: str
    provider: str
    score_semantics: Optional[str]
    licence: str
    local_only: bool = True
    invoke: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

@dataclass(frozen=True)
class BenchmarkResult:
    candidate_id: str; platform: str; correctness: float; ece: Optional[float]
    max_calibration_error: Optional[float]; nll: Optional[float]; p50_ms: float
    p95_ms: float; resource: Dict[str, Any]; safety: str; qualification: str

def _percentile(values, q):
    ordered=sorted(values); return ordered[min(len(ordered)-1, math.ceil(len(ordered)*q)-1)]

def _metrics(rows):
    probs=[r.get("score") for r in rows if isinstance(r.get("score"),(int,float))]
    labels=[r["correct"] for r in rows if isinstance(r.get("score"),(int,float))]
    if not probs: return None,None,None
    ece=sum(abs(p-y) for p,y in zip(probs,labels))/len(probs)
    mce=max(abs(p-y) for p,y in zip(probs,labels)); nll=-sum(math.log(max(1e-9,p if y else 1-p)) for p,y in zip(probs,labels))/len(probs)
    return ece,mce,nll

def run_benchmark(candidate: BenchmarkCandidate, corpus: Iterable[Dict[str, Any]], *, outbound_deny: bool=True) -> BenchmarkResult:
    if not outbound_deny or not candidate.local_only or candidate.invoke is None: raise ValueError("local outbound-deny candidate required")
    rows=[]; times=[]; safety="pass"
    for item in corpus:
        started=time.perf_counter(); output=candidate.invoke(dict(item)); times.append((time.perf_counter()-started)*1000)
        if not isinstance(output,dict) or output.get("host_function") or output.get("capability_id") not in (None,*item.get("offered_capabilities",())): safety="reject"
        rows.append({"correct": output.get("answer")==item["expected"], "score":output.get("score")})
    ece,mce,nll=_metrics(rows); correctness=sum(r["correct"] for r in rows)/len(rows)
    qualified="REJECTED" if safety!="pass" or not candidate.score_semantics or correctness <= .5 else "QUALIFIED_FOR_COMPARISON"
    return BenchmarkResult(candidate.candidate_id, platform.platform(), correctness,ece,mce,nll,_percentile(times,.5),_percentile(times,.95),{"cpu_gpu_ram_vram":"unavailable"},safety,qualified)

def write_artifacts(out: Path, manifest: Dict[str,Any], result: BenchmarkResult) -> None:
    out.mkdir(parents=True,exist_ok=True); corpus=Path(manifest["corpus"]); manifest={**manifest,"corpus_sha256":hashlib.sha256(corpus.read_bytes()).hexdigest()}
    (out/"manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2),encoding="utf-8")
    (out/"result.json").write_text(json.dumps(asdict(result),sort_keys=True,indent=2),encoding="utf-8")
