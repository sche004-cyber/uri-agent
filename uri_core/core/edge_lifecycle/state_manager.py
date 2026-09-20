"""Lazy runtime state machine using the frozen architecture vocabulary."""
from __future__ import annotations

from enum import Enum
from typing import Callable, List, Optional

from .telemetry import record_lifecycle_event


class RuntimeLifecycleState(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    NOT_LOADED = "NOT_LOADED"
    LOADING = "LOADING"
    RESIDENT = "RESIDENT"
    ON_DEMAND = "ON_DEMAND"
    SUSPENDED = "SUSPENDED"
    UNLOADING = "UNLOADING"
    FAILED = "FAILED"


class InvalidLifecycleTransition(RuntimeError):
    pass


class LazyRuntimeStateManager:
    def __init__(
        self, runtime_id: str, model_id: str,
        initial_state: RuntimeLifecycleState = RuntimeLifecycleState.NOT_LOADED,
    ):
        self.runtime_id = runtime_id
        self.model_id = model_id
        self._state = RuntimeLifecycleState(initial_state)
        self._history: List[RuntimeLifecycleState] = [self._state]

    @property
    def state(self) -> RuntimeLifecycleState:
        return self._state

    @property
    def history(self):
        return tuple(self._history)

    def _transition(self, state: RuntimeLifecycleState) -> None:
        self._state = state
        self._history.append(state)
        record_lifecycle_event(
            "runtime_state_transition", state.value,
            runtime_id=self.runtime_id, model_id=self.model_id,
        )

    def load(self, loader: Optional[Callable[[], None]] = None, *, on_demand: bool = False) -> RuntimeLifecycleState:
        if self.state is not RuntimeLifecycleState.NOT_LOADED:
            raise InvalidLifecycleTransition(f"cannot load from {self.state.value}")
        self._transition(RuntimeLifecycleState.LOADING)
        try:
            if loader:
                loader()
        except Exception:
            self._transition(RuntimeLifecycleState.FAILED)
            raise
        self._transition(RuntimeLifecycleState.ON_DEMAND if on_demand else RuntimeLifecycleState.RESIDENT)
        return self.state

    def unload(self, unloader: Optional[Callable[[], None]] = None) -> RuntimeLifecycleState:
        if self.state not in {RuntimeLifecycleState.RESIDENT, RuntimeLifecycleState.ON_DEMAND, RuntimeLifecycleState.SUSPENDED}:
            raise InvalidLifecycleTransition(f"cannot unload from {self.state.value}")
        self._transition(RuntimeLifecycleState.UNLOADING)
        try:
            if unloader:
                unloader()
        except Exception:
            self._transition(RuntimeLifecycleState.FAILED)
            raise
        self._transition(RuntimeLifecycleState.NOT_LOADED)
        return self.state

    def suspend(self) -> RuntimeLifecycleState:
        if self.state not in {RuntimeLifecycleState.RESIDENT, RuntimeLifecycleState.ON_DEMAND}:
            raise InvalidLifecycleTransition(f"cannot suspend from {self.state.value}")
        self._transition(RuntimeLifecycleState.SUSPENDED)
        return self.state

    def mark_unavailable(self) -> RuntimeLifecycleState:
        self._transition(RuntimeLifecycleState.UNAVAILABLE)
        return self.state
