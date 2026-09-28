"""Session-first, structured task/time retrieval. No learned or semantic ranking."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
import re
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .contracts import (MemoryQuery, RetrievedCandidate, RetrievalResult, CollisionReceipt,
                        TrustedInput, RecordKind as K, IdentityStatus as I, Freshness as F,
                        canonical, timestamp, authorized_attachments)

TYPE_WORDS = {"spreadsheet":"spreadsheet","workbook":"spreadsheet","script":"script","document":"document"}
STOPWORDS = set("the a an from of in on my task tasks file files this that yesterday today last week resume continue paused".split()) | set(TYPE_WORDS)


def words(text):
    text = re.sub(r"['’]s\b", "", text.casefold())
    return set(re.findall(r"\w+",text))


def raw_span(query):
    intake = query.intake
    if not isinstance(intake,TrustedInput) or not intake.trusted or (intake.user_id,intake.session_id) != (query.user_id,query.session_id): return None
    spans = [(a,b) for key,a,b in intake.spans if key == query.ref_key]
    if len(spans) != 1: return None
    a,b = spans[0]
    if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(intake.raw_text): return None
    return intake.raw_text[a:b]


def stem_title(title):
    # Lineage: frozen uri_v1/turn/rar_deterministic.py stem_title; no import.
    stem = re.sub(r"\.(pdf|docx|xlsx|csv|txt|mp4|mov|zip|json|mp3|wav|m4a|ogg|html|pptx)$", "", title,flags=re.I)
    stem = re.sub(r"[_\-]", " ", stem)
    return " ".join(stem.lower().split())


def exact_name(expression, title):
    return expression.strip().lower() in (title.strip().lower(),stem_title(title))


def selectors(query):
    span = raw_span(query)
    if span is None: raise ValueError("EXPRESSION_GROUNDING_UNESTABLISHED")
    w = words(span); classes = {TYPE_WORDS[x] for x in w if x in TYPE_WORDS}
    if len(classes)>1: raise ValueError("AMBIGUOUS_SOURCE_CLASS")
    temporal = [x for x in ("today","yesterday","last week") if re.search(r"\b"+x+r"\b",re.sub(r"['’]s\b","",span.casefold()))]
    if len(temporal)>1 or w & {"recently","tomorrow","earlier","ago","month"}: raise ValueError("UNSUPPORTED_TEMPORAL_SELECTOR")
    window = None
    if temporal:
        try: z = ZoneInfo(query.user_timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError): raise ValueError("TIMEZONE_REQUIRED")
        now = timestamp(query.now_utc).astimezone(z)
        date = now.date()
        if temporal[0] == "yesterday": date -= timedelta(days=1)
        elif temporal[0] == "last week": date -= timedelta(days=date.weekday()+7)
        start = datetime.combine(date,datetime.min.time(),z)
        end = start + timedelta(days=7 if temporal[0] == "last week" else 1)
        window = (start.astimezone(timezone.utc).isoformat(),end.astimezone(timezone.utc).isoformat())
    return span, (next(iter(classes)) if classes else None),window,w-STOPWORDS


class Retriever:
    def __init__(self, log, sources, telemetry=None):
        self.log,self.sources,self.telemetry = log,sources,telemetry

    def retrieve(self, query: MemoryQuery):
        start = time.perf_counter_ns()
        if query.user_id != self.log.user_id: raise ValueError("CROSS_USER_QUERY")
        stats = {"durable_reads":0,"skip_reason":None,"quarantine_count":0,"tier_counts":{},"candidates_returned":0}
        def finish(candidates=(),collision=None,stale=(),degraded=None):
            stats["retrieval_us"] = (time.perf_counter_ns()-start)//1000
            stats["candidates_returned"] = len(candidates)
            result = RetrievalResult(query,tuple(candidates),collision,tuple(stale),degraded,stats)
            if self.telemetry: self.telemetry.query(result)
            return result
        try: span,source_class,window,tokens = selectors(query)
        except ValueError as e: return finish(degraded=str(e))
        scan = self.sources.scan(); locators = {l.source_id:l for l in scan.locators}
        # Exact names always use the full authorized collision scope, independent of filters.
        expressions = {query.reference_expression.strip(), span.strip()}
        collision_ids = tuple(sorted(l.source_id for l in scan.locators if any(exact_name(e,PurePosixPath(l.relpath).name) for e in expressions)))
        receipt = CollisionReceipt(scan.root_ids,scan.snapshot_digest,collision_ids,scan.complete,scan.reason)
        found, stale = {}, []
        def add(sid,tier,used,task_ids=(),baseline=None):
            if sid not in locators:
                if baseline: stale.append({"source_id":sid,"freshness":F.SOURCE_MISSING,"authority":"AUTHORITATIVE_SOURCE"})
                return
            try: live = self.sources.fingerprint(locators[sid],observed_at=query.now_utc)
            except (OSError,ValueError):
                stale.append({"source_id":sid,"freshness":F.UNKNOWN,"identity_status":I.UNSAFE_IDENTITY,"authority":"AUTHORITATIVE_SOURCE"}); return
            if live is None: return
            if baseline and (not baseline.get("content_sha256") or baseline["content_sha256"] != live.content_sha256):
                stale.append({"source_id":sid,"freshness":F.STALE_SOURCE if baseline.get("content_sha256") and live.content_sha256 else F.UNKNOWN,"authority":"AUTHORITATIVE_SOURCE"})
            locator = f"file:{live.root_id}/{live.relpath}@{(live.content_sha256 or 'UNKNOWN')[:12]}"
            previous = found.get(sid)
            if previous:
                if task_ids: found[sid] = RetrievedCandidate(previous.source,previous.tier,max(previous.last_used_at,used),previous.locator,tuple(sorted(set(previous.task_ids)|set(task_ids))))
                return
            found[sid] = RetrievedCandidate(live,tier,used,locator,tuple(task_ids))
        for sid in authorized_attachments(query)+tuple(query.session_source_ids): add(sid,"SESSION",query.now_utc)
        if query.session_confirmed and found:
            stats["skip_reason"] = "SKIPPED_SESSION_CONFIRMED"
        else:
            try:
                before = time.perf_counter_ns(); index = self.log.load(); stats["load_us"] = (time.perf_counter_ns()-before)//1000
                stats["durable_reads"] = 1; stats["quarantine_count"] = len(index.recovery_ids)
            except (OSError,ValueError):
                return finish(tuple(found.values()),receipt,degraded="STORE_UNAVAILABLE")
            if len(index.openings) > query.max_tasks: return finish(collision=receipt,degraded="BUDGET_EXCEEDED")
            task_search = bool(words(span)&{"task","tasks","resume","continue"}) or window is not None
            resume = bool(words(span)&{"resume","continue"})
            matched_tasks = []
            for tid,opening_id in index.openings.items():
                state = index.task(tid)
                if not state: continue
                opening = index.records[opening_id]
                if query.task_id and tid != query.task_id: continue
                if resume and state.payload["status"] not in (("PAUSED",) if "paused" in words(span) else ("OPEN","PAUSED","WAITING_USER")): continue
                current_refs = {x["source_id"]:x["content_sha256"] for x in state.payload["references"]}
                used_at = {}
                previous = {}
                for historical in index.history(state.record_id):
                    refs = {x["source_id"]:x["content_sha256"] for x in historical.payload["references"]}
                    for sid,sha in refs.items():
                        if sid in current_refs and current_refs[sid] == sha and previous.get(sid) != sha:
                            used_at[sid] = historical.recorded_at
                    previous = refs
                for outcome in index.current(K.OUTCOME,tid):
                    if outcome.provenance != "EXECUTION_OUTCOME": continue
                    for link in outcome.payload["inputs"]:
                        sid = link["source_id"]
                        if sid in current_refs and current_refs[sid] == link["content_sha256"]:
                            used_at[sid] = max(used_at.get(sid,opening.recorded_at),outcome.recorded_at)
                stamp = (state.recorded_at if "updated" in words(span) else
                         max(used_at.values(),default=opening.recorded_at) if "used" in words(span) else opening.recorded_at)
                if window and not timestamp(window[0]) <= timestamp(stamp) < timestamp(window[1]): continue
                labels = words(opening.payload["objective_label"])
                for label in opening.payload.get("explicit_user_labels",()): labels |= words(label)
                label_tokens = tokens - {"updated","used"}
                if task_search and label_tokens and not labels.intersection(label_tokens): continue
                matched_tasks.append(tid)
                for ref in state.payload["references"]:
                    l = locators.get(ref["source_id"])
                    if source_class and (not l or l.media_type != source_class): continue
                    if not task_search and not query.task_id and tokens and (not l or not tokens.intersection(words(l.relpath))): continue
                    add(ref["source_id"],"TASK" if query.task_id else "HISTORY",used_at.get(ref["source_id"],opening.recorded_at),(tid,),ref)
                for r in index.current(K.OUTCOME,tid):
                    if any(x["source_id"] not in current_refs or x["content_sha256"] != current_refs[x["source_id"]] for x in r.payload["inputs"]): continue
                    for link in r.payload["outputs"]:
                        if "source_id" not in link: continue
                        l = locators.get(link["source_id"])
                        if source_class and (not l or l.media_type != source_class): continue
                        add(link["source_id"],"TASK" if query.task_id else "HISTORY",r.recorded_at,(tid,),link)
            stats["matching_tasks"] = len(matched_tasks)
            if index.conflicts: stats["conflict_count"] = len(index.conflicts)
            if index.pending_corrections: stats["pending_corrections"] = len(index.pending_corrections)
        if not found:
            for l in scan.locators:
                if source_class and l.media_type != source_class: continue
                if tokens and not tokens.intersection(words(l.relpath)): continue
                if window or query.task_id or words(span)&{"resume","continue"}: continue
                add(l.source_id,"REGISTRY",query.now_utc)
        for sid in collision_ids: add(sid,"REGISTRY",query.now_utc)
        if query.reference_expression.strip() in locators: add(query.reference_expression.strip(),"REGISTRY",query.now_utc)
        order = {"SESSION":0,"TASK":1,"HISTORY":2,"REGISTRY":3}
        candidates = sorted(found.values(),key=lambda c:c.source.source_id)
        candidates.sort(key=lambda c:c.last_used_at,reverse=True)
        candidates.sort(key=lambda c:order[c.tier])
        for c in candidates: stats["tier_counts"][c.tier] = stats["tier_counts"].get(c.tier,0)+1
        if len(candidates)>query.max_candidates or len(canonical(candidates))>query.max_bytes:
            return finish(collision=receipt,stale=stale,degraded="BUDGET_EXCEEDED")
        degraded = "COLLISION_SCOPE_INCOMPLETE" if collision_ids and not receipt.complete else None
        return finish(candidates,receipt,stale,degraded)
