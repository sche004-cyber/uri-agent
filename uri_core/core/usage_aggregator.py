"""Dashboard fold over local usage and static catalogue metadata only."""

from typing import Any, Dict, Optional

from uri_core.core.provider_registry import PROVIDER_CATALOGUE
from uri_core.core.usage_ceiling_store import UsageCeilingStore
from uri_core.core.usage_meter import current_month, known_tokens, month_records


def _totals() -> Dict[str, Any]:
    return {"calls": 0, "prompt_tokens": 0, "eval_tokens": 0,
            "duration_seconds": 0.0, "known_total_tokens": 0,
            "unavailable_records": 0, "outcomes": {"success": 0, "unreachable": 0}}


def aggregate_month(user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
    """Partial measurements retain their known fields; ceiling totals require both tokens.

    unavailable_records counts calls with any unavailable numeric field, including
    estimated_cost (always unavailable in M22.7). No monetary totals are invented.
    """
    month = current_month() if month is None else month
    totals, roles, providers = _totals(), {}, {}
    catalogue = {p.provider_id: p.display_name for p in PROVIDER_CATALOGUE}
    for record in month_records(user_id, month):
        role = record["role"]
        pid = record.get("provider_id") or "unreachable"
        role_totals = roles.setdefault(role, _totals())
        if pid not in providers:
            providers[pid] = {**_totals(), "display_name": catalogue.get(pid, pid)}
        for bucket in (totals, role_totals, providers[pid]):
            bucket["calls"] += 1
            outcome = record["outcome"]
            bucket["outcomes"][outcome] = bucket["outcomes"].get(outcome, 0) + 1
            bucket["known_total_tokens"] += known_tokens(record)
            for name in ("prompt_tokens", "eval_tokens", "duration_seconds"):
                field = record.get(name, {})
                if field.get("confidence") == "KNOWN" and field.get("value") is not None:
                    bucket[name] += field["value"]
            if any(record.get(name, {}).get("confidence") != "KNOWN" for name in
                   ("prompt_tokens", "eval_tokens", "duration_seconds", "estimated_cost")):
                bucket["unavailable_records"] += 1
    store = UsageCeilingStore(user_id)
    ceiling, ratio = store.get_ceiling(), store.get_warn_threshold_ratio()
    used = totals["known_total_tokens"]
    return {"month": month, "totals": totals, "by_role": roles, "by_provider": providers,
            "limits": {"monthly_token_ceiling": ceiling, "warn_threshold_ratio": ratio,
                       "warning": ceiling is not None and used >= ceiling * ratio,
                       "ceiling_reached": ceiling is not None and used >= ceiling}}
