"""Truthful host-capacity observations for pre-install admission checks."""
from __future__ import annotations

import platform
import shutil
from typing import Optional, Tuple

import psutil

from .models import HardwareCapacityRecord
from .storage import storage_root


def _gpu_capacity() -> Tuple[str, object, Optional[str]]:
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        try:
            count = pynvml.nvmlDeviceGetCount()
            if count < 1:
                return "unavailable", "unavailable", "pynvml reported no devices"
            total = 0
            names = []
            for index in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                total += int(pynvml.nvmlDeviceGetMemoryInfo(handle).total)
                name = pynvml.nvmlDeviceGetName(handle)
                names.append(name.decode() if isinstance(name, bytes) else str(name))
            return ", ".join(names), round(total / (1024 * 1024), 2), "pynvml"
        finally:
            pynvml.nvmlShutdown()
    except Exception:
        pass
    try:
        import torch  # type: ignore

        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            total = sum(torch.cuda.get_device_properties(i).total_memory for i in range(torch.cuda.device_count()))
            names = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
            return ", ".join(names), round(total / (1024 * 1024), 2), "torch.cuda"
    except Exception:
        pass
    return "unavailable", "unavailable", "no observable GPU API"


def probe_hardware_capacity() -> HardwareCapacityRecord:
    root = storage_root(create=True)
    memory = psutil.virtual_memory()
    frequency = psutil.cpu_freq()
    gpu, vram, gpu_detail = _gpu_capacity()
    return HardwareCapacityRecord(
        physical_cpu_cores=psutil.cpu_count(logical=False),
        logical_cpu_cores=psutil.cpu_count(logical=True),
        architecture=platform.machine() or "unknown",
        cpu_frequency_mhz=frequency.current if frequency else None,
        total_ram_mib=round(memory.total / (1024 * 1024), 2),
        available_ram_mib=round(memory.available / (1024 * 1024), 2),
        free_disk_mib=round(shutil.disk_usage(root).free / (1024 * 1024), 2),
        gpu=gpu,
        vram_mib=vram,
        gpu_detail=gpu_detail,
    )


def can_host_model(model_bytes: int, est_ram_bytes: int) -> Tuple[bool, str]:
    if type(model_bytes) is not int or type(est_ram_bytes) is not int or model_bytes < 0 or est_ram_bytes < 0:
        return False, "model and RAM requirements must be non-negative integer byte counts"
    capacity = probe_hardware_capacity()
    free_disk = int(capacity.free_disk_mib * 1024 * 1024)
    available_ram = int(capacity.available_ram_mib * 1024 * 1024)
    if model_bytes > free_disk:
        return False, "insufficient free disk space in URI model storage"
    if est_ram_bytes > available_ram:
        return False, "insufficient currently available system memory"
    return True, "capacity requirements satisfied"
