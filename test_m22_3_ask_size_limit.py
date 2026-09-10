"""M22.3 (Decision 6): /ask request-size protection - a 64 KB field-level
bound on AskRequest.text plus a lower-level Content-Length precheck (see
docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md sections 5.6/6.5). The
precheck exists specifically to reject an oversized body before it is
ever read into memory / parsed by Pydantic - proven here by sending a
genuinely oversized raw body, not a header claim.
"""

import json
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, server


class AskSizeLimitTests(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(server.app)

    def test_text_at_exactly_the_boundary_is_accepted(self):
        text = "a" * edge.ASK_MAX_TEXT_BYTES

        response = self.client.post(
            "/ask", json={"session_id": "size-boundary", "text": text}
        )

        self.assertEqual(response.status_code, 200, response.text)

    def test_text_one_byte_over_the_boundary_is_rejected(self):
        text = "a" * (edge.ASK_MAX_TEXT_BYTES + 1)

        response = self.client.post(
            "/ask", json={"session_id": "size-boundary", "text": text}
        )

        self.assertEqual(response.status_code, 422, response.text)

    def test_a_body_over_the_content_length_ceiling_is_rejected_413(self):
        # Genuinely large raw bytes, not merely a claimed header - this
        # also exceeds the 64KB field bound, but the Content-Length
        # precheck must reject it first, before Pydantic ever runs.
        oversized_text = "a" * (edge.ASK_MAX_CONTENT_LENGTH_BYTES + 1024)
        body = json.dumps(
            {"session_id": "oversized", "text": oversized_text}
        ).encode("utf-8")

        response = self.client.post(
            "/ask",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 413, response.text)

    def test_a_body_within_the_content_length_ceiling_is_not_413(self):
        # Between the 64KB field bound and the 1MB Content-Length
        # ceiling: must fail field validation (422), never the
        # Content-Length precheck (413) - the two limits are distinct
        # and this proves the precheck isn't simply reusing the field
        # bound.
        mid_sized_text = "a" * (edge.ASK_MAX_TEXT_BYTES + 1000)

        response = self.client.post(
            "/ask", json={"session_id": "mid-sized", "text": mid_sized_text}
        )

        self.assertEqual(response.status_code, 422, response.text)

    def test_normal_sized_request_is_unaffected(self):
        response = self.client.post(
            "/ask", json={"session_id": "normal", "text": "draft a note"}
        )

        self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
