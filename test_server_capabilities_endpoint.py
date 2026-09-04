"""Tests for GET /capabilities: URI's self-knowledge surface (Milestone
6). No Ollama or network involved - _model_provider.describe() is
exercised against a fake requests.get, same pattern as
test_ollama_provider.py."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.capability_registry import CapabilityRegistry


class CapabilitiesEndpointTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_capability_registry = server._capability_registry

        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )

        import json

        with open(registry_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "active_tools": {
                        "draft_note": {
                            "file_path": "x.py",
                            "class_name": "X",
                            "method": "run",
                            "description": "Draft a note.",
                            "status": "implemented",
                            "availability": "available",
                        }
                    },
                    "planned_capabilities": {
                        "pc_system_optimization": {
                            "description": "Optimize the PC.",
                            "status": "not_implemented",
                            "risk": "high",
                        }
                    },
                },
                file,
            )

        server._capability_registry = CapabilityRegistry(
            registry_path=registry_path
        )

        self.client = TestClient(server.app)

    def tearDown(self):
        server._capability_registry = self._original_capability_registry
        self.temp_dir.cleanup()

    def test_returns_model_and_capabilities_sections(self):
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=MagicMock(status_code=200),
        ):
            response = self.client.get("/capabilities")

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertIn("model", body)
        self.assertIn("capabilities", body)

        self.assertTrue(body["model"]["available"])
        self.assertEqual(body["model"]["provider_name"], "ollama")

        ids = {c["id"] for c in body["capabilities"]}
        self.assertIn("draft_note", ids)
        self.assertIn("pc_system_optimization", ids)

    def test_unreachable_model_reports_unavailable_not_an_error(self):
        import requests

        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            side_effect=requests.exceptions.ConnectionError(),
        ):
            response = self.client.get("/capabilities")

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertFalse(body["model"]["available"])
        self.assertIsNotNone(body["model"]["detail"])
        # The capability section must be unaffected by the model
        # backend being down.
        self.assertTrue(len(body["capabilities"]) >= 1)

    def test_not_implemented_capability_is_clearly_distinguished(self):
        with patch(
            "uri_core.core.model_providers.ollama_provider.requests.get",
            return_value=MagicMock(status_code=200),
        ):
            response = self.client.get("/capabilities")

        body = response.json()
        by_id = {c["id"]: c for c in body["capabilities"]}

        self.assertEqual(by_id["draft_note"]["status"], "implemented")
        self.assertEqual(
            by_id["pc_system_optimization"]["status"], "not_implemented"
        )
        self.assertEqual(
            by_id["pc_system_optimization"]["risk"], "high"
        )


if __name__ == "__main__":
    unittest.main()
