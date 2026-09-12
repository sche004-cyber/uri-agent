"""Capability: report real PC performance metrics (2026-09-12, User
directive - "I think PC performance metric should be given in the URI
UI... make a backend capability to add to a future UI").

Backend-only for now, by explicit instruction - no client screen reads
this yet. Read-only: this module only ever observes system state via
psutil, never configures, throttles, or kills anything.
"""

from typing import Any, Dict

import psutil


class SystemPerformanceTool:
    """No constructor state - every call is a fresh, real snapshot."""

    def report(self, **kwargs: Any) -> Dict[str, Any]:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.2)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)

            virtual_memory = psutil.virtual_memory()

            disk_usage = psutil.disk_usage(
                "C:\\" if psutil.WINDOWS else "/"
            )

            boot_time = psutil.boot_time()
        except Exception as exc:
            return {
                "status": "error",
                "message": f"URI could not read system performance metrics: {exc}",
            }

        # Swap/page-file metrics use Windows Performance Counters (PDH)
        # on this platform, which some installs have disabled entirely
        # (a real, machine-specific Windows configuration state, not a
        # code fault) - degrades to "unavailable" rather than failing
        # every other metric this call could otherwise honestly report.
        swap: Dict[str, Any]
        try:
            swap_memory = psutil.swap_memory()
            swap = {
                "total_bytes": swap_memory.total,
                "used_percent": swap_memory.percent,
            }
        except Exception as exc:
            swap = {"available": False, "reason": str(exc)}

        return {
            "status": "success",
            "message": "Current PC performance snapshot.",
            "cpu": {
                "percent": cpu_percent,
                "logical_cores": cpu_count_logical,
                "physical_cores": cpu_count_physical,
            },
            "memory": {
                "total_bytes": virtual_memory.total,
                "available_bytes": virtual_memory.available,
                "used_percent": virtual_memory.percent,
            },
            "swap": swap,
            "disk": {
                "total_bytes": disk_usage.total,
                "free_bytes": disk_usage.free,
                "used_percent": disk_usage.percent,
            },
            "boot_time_epoch_seconds": boot_time,
        }
