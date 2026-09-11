"""M22.5: Provider registry catalogue tests.

1. Every numeric field in the static catalogue carries KNOWN|ESTIMATED|UNAVAILABLE
   confidence - never a bare, unlabelled number.
2. UnknownModelProviderError still raised for unregistered provider string
   (M21 no-silent-substitution guarantee, unchanged).
3. ConfidenceValue invariants: UNAVAILABLE requires value=None.
4. build_provider backward-compatibility: all existing callers with no
   principal still get an OllamaProvider.
"""

import unittest

from uri_core.core.provider_registry import (
    CATALOGUE_BY_ID,
    PROVIDER_CATALOGUE,
    ConfidenceValue,
    ModelDescriptor,
    ProviderDescriptor,
    KNOWN,
    ESTIMATED,
    UNAVAILABLE,
)
from uri_core.config.model_roles import (
    UnknownModelProviderError,
    build_provider,
    ROLE_SEMANTIC_INTERPRETATION,
    ROLE_REASONING,
    ROLE_DRAFTING,
    ROLE_DOCUMENT_COMPOSITION,
    ROLE_DIAGNOSTICS,
    ROLE_BACKGROUND,
)
from uri_core.core.model_providers import OllamaProvider


class TestConfidenceValue(unittest.TestCase):
    def test_known_with_value(self):
        cv = ConfidenceValue(value=128000, confidence=KNOWN)
        self.assertEqual(cv.value, 128000)
        self.assertEqual(cv.confidence, KNOWN)

    def test_unavailable_requires_none_value(self):
        with self.assertRaises(ValueError):
            ConfidenceValue(value=100, confidence=UNAVAILABLE)

    def test_unavailable_with_none_is_valid(self):
        cv = ConfidenceValue(value=None, confidence=UNAVAILABLE)
        self.assertIsNone(cv.value)

    def test_invalid_confidence_raises(self):
        with self.assertRaises(ValueError):
            ConfidenceValue(value=100, confidence="MAYBE")

    def test_estimated_with_value(self):
        cv = ConfidenceValue(value=0.001, confidence=ESTIMATED)
        self.assertAlmostEqual(cv.value, 0.001)


class TestCatalogueConfidenceLabelling(unittest.TestCase):
    """Every numeric field in the catalogue must carry a confidence label."""

    def test_all_entries_have_confidence_value(self):
        for descriptor in PROVIDER_CATALOGUE:
            for model in descriptor.models:
                self.assertIsInstance(
                    model.context_tokens,
                    ConfidenceValue,
                    msg=f"{descriptor.provider_id}/{model.model_id}: "
                        f"context_tokens must be ConfidenceValue, "
                        f"got {type(model.context_tokens)}",
                )
                self.assertIsInstance(
                    model.pricing_per_1k_tokens,
                    ConfidenceValue,
                    msg=f"{descriptor.provider_id}/{model.model_id}: "
                        f"pricing_per_1k_tokens must be ConfidenceValue",
                )
                self.assertIn(
                    model.context_tokens.confidence,
                    (KNOWN, ESTIMATED, UNAVAILABLE),
                    msg=f"Invalid confidence: {model.context_tokens.confidence}",
                )

    def test_unavailable_context_tokens_have_none_value(self):
        for descriptor in PROVIDER_CATALOGUE:
            for model in descriptor.models:
                if model.context_tokens.confidence == UNAVAILABLE:
                    self.assertIsNone(
                        model.context_tokens.value,
                        msg=f"{descriptor.provider_id}/{model.model_id}: "
                            "UNAVAILABLE confidence requires value=None",
                    )

    def test_catalogue_by_id_is_consistent(self):
        for pid, descriptor in CATALOGUE_BY_ID.items():
            self.assertEqual(pid, descriptor.provider_id)


class TestUnknownModelProviderError(unittest.TestCase):
    """M21 guarantee: UnknownModelProviderError still raised for unknown adapter."""

    def test_unregistered_provider_raises(self):
        """Configuring a role to an unknown provider still raises immediately."""
        import tempfile, json, os
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"reasoning": {"provider": "gopher"}}, f)
            tmp = f.name
        try:
            with self.assertRaises(UnknownModelProviderError):
                build_provider("reasoning", principal=None, roles_path=tmp)
        finally:
            os.unlink(tmp)

    def test_ollama_provider_no_principal(self):
        """All existing ROLE_* constants still return OllamaProvider when
        principal is None (zero-behaviour-change for existing callers)."""
        for role in (
            ROLE_SEMANTIC_INTERPRETATION,
            ROLE_REASONING,
            ROLE_DRAFTING,
            ROLE_DOCUMENT_COMPOSITION,
            ROLE_DIAGNOSTICS,
            ROLE_BACKGROUND,
        ):
            provider = build_provider(role, principal=None)
            self.assertIsInstance(
                provider,
                OllamaProvider,
                msg=f"Role {role!r} with principal=None must return OllamaProvider",
            )


if __name__ == "__main__":
    unittest.main()
