"""Generic Startup Services lifecycle (docs/plans/
M30_GRAPHIFY_FOUNDATION_PLAN.md §A.5): one service's own failure must
never block another service, or prevent the caller (server startup)
from completing."""

import unittest

from uri_core.core.startup_services import run_startup_services


class _RecordingService:
    def __init__(self, log, name, raises=False):
        self.log = log
        self.name = name
        self.raises = raises

    def start(self):
        self.log.append(self.name)
        if self.raises:
            raise RuntimeError(f"{self.name} failed")


class StartupServicesRunnerTests(unittest.TestCase):
    def test_every_service_runs_in_order(self):
        log = []
        run_startup_services([
            _RecordingService(log, "a"),
            _RecordingService(log, "b"),
            _RecordingService(log, "c"),
        ])
        self.assertEqual(log, ["a", "b", "c"])

    def test_one_services_failure_never_blocks_a_later_service(self):
        log = []
        run_startup_services([
            _RecordingService(log, "a", raises=True),
            _RecordingService(log, "b"),
        ])
        self.assertEqual(log, ["a", "b"])

    def test_empty_service_list_does_not_raise(self):
        run_startup_services([])  # must not raise


if __name__ == "__main__":
    unittest.main()
