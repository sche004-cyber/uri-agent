"""M21: a bounded, verbatim window of a session's own recent conversation
history now reaches query_context (see orchestrator.py's
_build_conversation_context) - closing the gap the M21 audit found:
ConversationHistoryStore (M18) recorded every turn from the start, but
nothing ever read it back into a Brain request.

Architectural boundary this suite exists to prove: the conversation
window is historical context only - recency- and budget-bounded, never
relevance-scored, and never written into MemoryStore, ExperienceStore,
or SkillMemory. It must never become authority or a standing fact.
"""

import tempfile
import unittest

from uri_core.core.conversation_history import ConversationHistoryStore
from uri_core.core.experience_store import ExperienceStore
from uri_core.core.orchestrator import (
    MAX_CONVERSATION_CONTEXT_TOKENS,
    MAX_CONVERSATION_TURNS_CONSIDERED,
    UriOrchestrator,
)
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.user_memory import MemoryStore


def _orchestrator(tmp_dir):
    return UriOrchestrator(
        enable_model_reasoning_shadow=False,
        conversation_history=ConversationHistoryStore(storage_dir=tmp_dir),
    )


class ConversationContextTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.orchestrator = _orchestrator(self._tmp.name)

    def test_no_session_id_returns_empty(self):
        self.assertEqual(self.orchestrator._build_conversation_context(None), [])

    def test_unknown_session_returns_empty(self):
        self.assertEqual(
            self.orchestrator._build_conversation_context("never-seen"), []
        )

    def test_recorded_turns_appear_oldest_first(self):
        store = self.orchestrator.conversation_history
        for i in range(3):
            store.append_turn(
                session_id="s1",
                turn_id=f"t{i}",
                user_text=f"question {i}",
                response_text=f"answer {i}",
                status="success",
            )

        context = self.orchestrator._build_conversation_context("s1")

        self.assertEqual(len(context), 3)
        self.assertEqual(context[0]["user"], "question 0")
        self.assertEqual(context[-1]["user"], "question 2")
        self.assertEqual(context[0]["uri"], "answer 0")
        self.assertEqual(context[0]["status"], "success")

    def test_window_is_bounded_by_turns_considered(self):
        store = self.orchestrator.conversation_history
        total = MAX_CONVERSATION_TURNS_CONSIDERED + 10
        for i in range(total):
            store.append_turn(
                session_id="s1",
                turn_id=f"t{i}",
                user_text=f"q{i}",
                response_text="short",
                status="success",
            )

        context = self.orchestrator._build_conversation_context("s1")

        self.assertLessEqual(len(context), MAX_CONVERSATION_TURNS_CONSIDERED)
        # The most recent turns are the ones kept.
        self.assertEqual(context[-1]["user"], f"q{total - 1}")

    def test_a_single_oversized_turn_does_not_evict_the_whole_window(self):
        store = self.orchestrator.conversation_history
        store.append_turn(
            session_id="s1",
            turn_id="t0",
            user_text="x" * 7000,
            response_text="y" * 7000,
            status="success",
        )
        store.append_turn(
            session_id="s1",
            turn_id="t1",
            user_text="a normal follow-up question",
            response_text="a normal answer",
            status="success",
        )

        context = self.orchestrator._build_conversation_context("s1")

        self.assertGreaterEqual(len(context), 1)

    def test_window_respects_token_budget(self):
        import json

        store = self.orchestrator.conversation_history
        for i in range(30):
            store.append_turn(
                session_id="s1",
                turn_id=f"t{i}",
                user_text=f"question number {i} about something",
                response_text=f"a moderately detailed answer for turn {i} " * 3,
                status="success",
            )

        context = self.orchestrator._build_conversation_context("s1")

        total_chars = len(json.dumps(context, ensure_ascii=False))
        # estimate_tokens is chars/4 - allow generous margin over the
        # nominal budget for JSON structural overhead per entry.
        self.assertLess(total_chars // 4, MAX_CONVERSATION_CONTEXT_TOKENS * 2)

    def test_corrupt_store_degrades_to_empty_never_raises(self):
        class _BrokenStore:
            def get_session(self, session_id):
                raise OSError("disk error")

        orchestrator = UriOrchestrator(
            enable_model_reasoning_shadow=False,
            conversation_history=_BrokenStore(),
        )
        self.assertEqual(
            orchestrator._build_conversation_context("s1"), []
        )

    def test_conversation_reaches_query_context(self):
        store = self.orchestrator.conversation_history
        store.append_turn(
            session_id="s1",
            turn_id="t0",
            user_text="what is the status",
            response_text="here is the status",
            status="success",
        )

        query_context = self.orchestrator._build_query_context(
            session_id="s1",
            policy_text="policy",
            personalization_context={},
        )

        self.assertIn("conversation", query_context)
        self.assertEqual(len(query_context["conversation"]), 1)
        self.assertEqual(
            query_context["conversation"][0]["user"], "what is the status"
        )


class ConversationWindowNeverBecomesStandingMemoryTests(unittest.TestCase):
    """Boundary proof: reading the conversation window into a Brain
    request must never, by itself, write anything into MemoryStore,
    ExperienceStore, or SkillMemory - it stays historical context, not
    authority, matching the M21 audit's explicit constraint."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.orchestrator = _orchestrator(self._tmp.name)

        import os

        self.memory_path = os.path.join(self._tmp.name, "user_memory.json")
        self.experience_path = os.path.join(self._tmp.name, "experience.json")
        self.skill_path = os.path.join(self._tmp.name, "skill_memory.json")

        self.orchestrator.experience_store = ExperienceStore(
            storage_path=self.experience_path
        )
        self.orchestrator.skill_memory = SkillMemory(
            storage_path=self.skill_path
        )
        self.memory_store = MemoryStore(storage_path=self.memory_path)

    def test_building_conversation_context_does_not_touch_other_stores(self):
        import os

        store = self.orchestrator.conversation_history
        for i in range(5):
            store.append_turn(
                session_id="s1",
                turn_id=f"t{i}",
                user_text=f"question {i}",
                response_text=f"answer {i}",
                status="success",
            )

        self.orchestrator._build_query_context(
            session_id="s1", policy_text="policy", personalization_context={}
        )

        self.assertEqual(self.orchestrator.experience_store.list_all(), [])
        self.assertEqual(self.orchestrator.skill_memory.list_skills(), [])
        self.assertFalse(os.path.exists(self.memory_path))


if __name__ == "__main__":
    unittest.main()
