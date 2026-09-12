"""SystemPerformanceTool (2026-09-12): real, read-only PC metrics."""

import unittest

from uri_core.tools.system_performance import SystemPerformanceTool


class SystemPerformanceToolTests(unittest.TestCase):

    def test_report_returns_real_looking_metrics(self):
        result = SystemPerformanceTool().report()

        self.assertEqual(result["status"], "success")
        self.assertIsInstance(result["cpu"]["percent"], (int, float))
        self.assertGreaterEqual(result["cpu"]["logical_cores"], 1)
        self.assertGreater(result["memory"]["total_bytes"], 0)
        self.assertGreaterEqual(result["memory"]["used_percent"], 0)
        self.assertGreater(result["disk"]["total_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
