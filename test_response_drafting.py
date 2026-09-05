import unittest

from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.response_drafting import (
    DraftRequest,
    ResponseDraftingError,
    build_drafting_system_prompt,
    draft_response,
)


class _FakeProvider:
    def __init__(self, content="Here is your answer.", raises=None):
        self.content = content
        self.raises = raises
        self.calls = []

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self.raises:
            raise self.raises
        return ModelResponse(
            content=self.content, model="fake", provider="fake"
        )


class BuildDraftingSystemPromptTests(unittest.TestCase):

    def test_includes_the_supplied_policy_text_verbatim(self):
        prompt = build_drafting_system_prompt(
            "You are URI, the NIT Sikkim Administrative AI Assistant."
        )
        self.assertIn(
            "You are URI, the NIT Sikkim Administrative AI Assistant.",
            prompt,
        )

    def test_includes_drafting_rules(self):
        prompt = build_drafting_system_prompt("policy text")
        self.assertIn("Never claim an outcome different", prompt)


class DraftResponseTests(unittest.TestCase):

    def _request(self, outcome=None, personalization=None):
        return DraftRequest(
            user_text="draft a note",
            outcome=outcome
            or {"execution": {"status": "success"}, "response": {}},
            personalization=personalization,
            policy_text="policy text",
        )

    def test_returns_stripped_provider_content(self):
        provider = _FakeProvider(content="  Here you go.  ")

        result = draft_response(self._request(), provider=provider)

        self.assertEqual(result, "Here you go.")

    def test_passes_outcome_and_personalization_as_json_payload(self):
        provider = _FakeProvider()

        draft_response(
            self._request(personalization={"communication_style": "formal"}),
            provider=provider,
        )

        payload = provider.calls[0]["user"]
        self.assertIn("draft a note", payload)
        self.assertIn("formal", payload)

    def test_uses_the_supplied_policy_text_as_system_prompt_source(self):
        provider = _FakeProvider()

        draft_response(
            DraftRequest(
                user_text="x",
                outcome={"execution": {"status": "success"}},
                personalization=None,
                policy_text="UNIQUE-POLICY-MARKER",
            ),
            provider=provider,
        )

        self.assertIn("UNIQUE-POLICY-MARKER", provider.calls[0]["system"])

    def test_provider_error_raises_response_drafting_error(self):
        provider = _FakeProvider(raises=ConnectionError("no ollama"))

        with self.assertRaises(ResponseDraftingError):
            draft_response(self._request(), provider=provider)

    def test_empty_provider_response_raises_response_drafting_error(
        self,
    ):
        provider = _FakeProvider(content="   ")

        with self.assertRaises(ResponseDraftingError):
            draft_response(self._request(), provider=provider)

    def test_no_personalization_serializes_to_empty_object(self):
        provider = _FakeProvider()

        draft_response(
            self._request(personalization=None), provider=provider
        )

        payload = provider.calls[0]["user"]
        self.assertIn('"personalization": {}', payload)

    def test_omitted_query_context_serializes_to_empty_object(self):
        # Milestone 10A: DraftRequest.query_context is optional and
        # additive - a caller that never sets it (the exact shape
        # every pre-Milestone-10A test/caller in this file uses) still
        # gets a well-formed, empty section rather than a missing key
        # or an error.
        provider = _FakeProvider()

        draft_response(self._request(), provider=provider)

        payload = provider.calls[0]["user"]
        self.assertIn('"query_context": {}', payload)

    def test_supplied_query_context_reaches_the_payload(self):
        provider = _FakeProvider()

        request = DraftRequest(
            user_text="draft a note",
            outcome={"execution": {"status": "success"}, "response": {}},
            personalization=None,
            policy_text="policy text",
            query_context={
                "identity": "policy",
                "personalization": {},
                "session": {"task": "noting"},
                "verified_facts": {},
                "capabilities": [],
            },
        )

        draft_response(request, provider=provider)

        payload = provider.calls[0]["user"]
        self.assertIn("noting", payload)


if __name__ == "__main__":
    unittest.main()
