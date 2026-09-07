"""M18 tests: per-user memory/learning isolation, conversation history,
self-correcting skill memory, Brain-proposed memory confirmation, and
the safe skill-install foundation.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.conversation_history import ConversationHistoryStore
from uri_core.core.skill_memory import SkillMemory, CONFIDENCE_RECALL_FLOOR
from uri_core.core.user_memory import MemoryStore, is_eligible_for_personalization
from uri_core.skills.skill_installer import (
    SkillInstaller,
    SkillValidator,
    STATUS_QUARANTINED,
    STATUS_ENABLED,
    STATUS_DISABLED,
)


class ConversationHistoryTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = ConversationHistoryStore(storage_dir=os.path.join(self.dir, "hist"))

    def test_append_and_read_back(self):
        self.store.append_turn(
            session_id="s1", turn_id="t1", user_text="hello", response_text="hi"
        )
        self.store.append_turn(
            session_id="s1", turn_id="t2", user_text="draft a note",
            response_text="OFFICE NOTE", status="success", capability="draft_institutional_note",
        )
        turns = self.store.get_session("s1")
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0]["user_text"], "hello")
        self.assertEqual(turns[1]["capability"], "draft_institutional_note")

    def test_list_and_delete(self):
        self.store.append_turn(session_id="s1", turn_id="t1", user_text="a", response_text="b")
        self.store.append_turn(session_id="s2", turn_id="t1", user_text="c", response_text="d")
        sessions = self.store.list_sessions()
        self.assertEqual({s["session_id"] for s in sessions}, {"s1", "s2"})
        self.assertTrue(self.store.delete_session("s1"))
        self.assertEqual(self.store.get_session("s1"), [])

    def test_session_id_traversal_is_refused(self):
        # A hostile session id can never escape the store directory.
        ok = self.store.append_turn(
            session_id="../../etc/passwd", turn_id="t", user_text="x", response_text="y"
        )
        # It is either refused (False) or safely basename'd - never a
        # file written outside the store dir.
        outside = os.path.join(self.dir, "etc")
        self.assertFalse(os.path.exists(outside))

    def test_per_session_files_are_separate(self):
        # Two stores pointed at different dirs never see each other's data
        # (this is what makes per-user isolation in the server real).
        other = ConversationHistoryStore(storage_dir=os.path.join(self.dir, "other"))
        self.store.append_turn(session_id="s1", turn_id="t1", user_text="mine", response_text="r")
        self.assertEqual(other.get_session("s1"), [])


class SelfCorrectingSkillMemoryTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.sm = SkillMemory(storage_path=os.path.join(self.dir, "sk.json"))
        self.sr = {"task_type": "Document Drafting", "domain": "Administrative"}

    def test_success_makes_skill_recallable(self):
        self.sm.learn_skill(self.sr, ["a", "b"], tool_name="draft_institutional_note")
        self.assertIsNotNone(self.sm.find_matching_skill(self.sr))

    def test_repeated_failure_demotes_below_recall_floor(self):
        self.sm.learn_skill(self.sr, ["a"], tool_name="t")
        for _ in range(4):
            self.sm.record_failure(self.sr, tool_name="t")
        skill = self.sm.list_skills()[0]
        self.assertLess(SkillMemory.confidence(skill), CONFIDENCE_RECALL_FLOOR)
        # A demoted skill is not recalled, but is not deleted either.
        self.assertIsNone(self.sm.find_matching_skill(self.sr))
        self.assertEqual(len(self.sm.list_skills()), 1)

    def test_failure_does_not_overwrite_known_good_workflow(self):
        self.sm.learn_skill(self.sr, ["good", "workflow"], tool_name="t")
        self.sm.record_failure(self.sr, tool_name="t")
        skill = self.sm.list_skills()[0]
        self.assertEqual(skill["workflow"], ["good", "workflow"])

    def test_recovery_restores_recall(self):
        self.sm.learn_skill(self.sr, ["a"], tool_name="t")
        for _ in range(4):
            self.sm.record_failure(self.sr, tool_name="t")
        self.assertIsNone(self.sm.find_matching_skill(self.sr))
        for _ in range(4):
            self.sm.learn_skill(self.sr, ["a"], tool_name="t")
        self.assertIsNotNone(self.sm.find_matching_skill(self.sr))


class BrainProposedMemoryTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = MemoryStore(storage_path=os.path.join(self.dir, "mem.json"))

    def test_proposed_memory_is_not_personalization_eligible_until_confirmed(self):
        proposed = self.store.propose(category="preference", content="likes serif fonts")
        self.assertEqual(proposed.consent, "pending_confirmation")
        self.assertFalse(is_eligible_for_personalization(proposed))

        confirmed = self.store.confirm(proposed.memory_id)
        self.assertEqual(confirmed.consent, "user_confirmed")
        self.assertTrue(is_eligible_for_personalization(confirmed))

    def test_confirm_can_correct_content(self):
        proposed = self.store.propose(category="preference", content="likes serif")
        confirmed = self.store.confirm(proposed.memory_id, content="likes Times New Roman 12pt")
        self.assertEqual(confirmed.fact.value, "likes Times New Roman 12pt")
        self.assertEqual(confirmed.consent, "user_confirmed")

    def test_reject_removes_the_proposal(self):
        proposed = self.store.propose(category="preference", content="x")
        self.assertTrue(self.store.delete(proposed.memory_id))
        self.assertIsNone(self.store.get(proposed.memory_id))

    def test_confirm_unknown_id_returns_none(self):
        self.assertIsNone(self.store.confirm("does-not-exist"))


class SkillInstallerTests(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.installer = SkillInstaller(
            store=__import__(
                "uri_core.skills.skill_installer", fromlist=["InstalledSkillStore"]
            ).InstalledSkillStore(storage_path=os.path.join(self.dir, "installed.json"))
        )

    def _make_package(self, name="demo_skill", version="1.0.0", entry="main.py",
                      capabilities=None, deps=None, write_entry=True):
        pkg = tempfile.mkdtemp()
        manifest = {
            "name": name,
            "version": version,
            "entrypoint": entry,
            "capabilities": capabilities if capabilities is not None else ["demo_capability"],
            "dependencies": deps if deps is not None else [],
        }
        with open(os.path.join(pkg, "skill.json"), "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        if write_entry:
            with open(os.path.join(pkg, entry), "w", encoding="utf-8") as handle:
                handle.write("# skill code - never imported by the installer\n")
        return pkg

    def test_valid_skill_installs_quarantined(self):
        pkg = self._make_package()
        result = self.installer.install_from_path(pkg, source="https://github.com/x/demo")
        self.assertTrue(result.ok)
        self.assertEqual(result.status, STATUS_QUARANTINED)
        record = self.installer.store.get("demo_skill")
        self.assertEqual(record["source"], "https://github.com/x/demo")
        self.assertEqual(record["capabilities"], ["demo_capability"])
        self.assertIn("digest", record)

    def test_missing_manifest_is_rejected_with_reason(self):
        empty = tempfile.mkdtemp()
        result = self.installer.install_from_path(empty)
        self.assertFalse(result.ok)
        self.assertTrue(any("manifest" in r.lower() for r in result.validation["reasons"]))
        # Nothing was installed.
        self.assertEqual(self.installer.list_installed(), [])

    def test_missing_required_field_is_rejected(self):
        pkg = tempfile.mkdtemp()
        with open(os.path.join(pkg, "skill.json"), "w", encoding="utf-8") as handle:
            json.dump({"name": "x"}, handle)  # missing version/entrypoint/capabilities
        result = self.installer.install_from_path(pkg)
        self.assertFalse(result.ok)

    def test_entrypoint_escape_is_rejected(self):
        pkg = self._make_package(entry="../../evil.py", write_entry=False)
        result = self.installer.install_from_path(pkg)
        self.assertFalse(result.ok)
        self.assertTrue(any("inside the package" in r or "outside" in r for r in result.validation["reasons"]))

    def test_missing_entrypoint_file_is_rejected(self):
        pkg = self._make_package(write_entry=False)
        result = self.installer.install_from_path(pkg)
        self.assertFalse(result.ok)

    def test_lifecycle_enable_disable_remove(self):
        pkg = self._make_package()
        self.installer.install_from_path(pkg)
        self.assertEqual(self.installer.enable("demo_skill").status, STATUS_ENABLED)
        self.assertEqual(self.installer.disable("demo_skill").status, STATUS_DISABLED)
        self.assertTrue(self.installer.remove("demo_skill").ok)
        self.assertIsNone(self.installer.store.get("demo_skill"))

    def test_update_detects_unchanged_vs_changed(self):
        pkg = self._make_package(version="1.0.0")
        self.installer.install_from_path(pkg)
        self.installer.enable("demo_skill")

        # Same content -> reported unchanged, status preserved.
        same = self.installer.update_from_path(pkg)
        self.assertTrue(same.ok)
        self.assertIn("unchanged", same.detail.lower())
        self.assertEqual(self.installer.store.get("demo_skill")["status"], STATUS_ENABLED)

        # Change a file -> update recorded, new version tracked.
        with open(os.path.join(pkg, "main.py"), "a", encoding="utf-8") as handle:
            handle.write("# changed\n")
        with open(os.path.join(pkg, "skill.json"), "r+", encoding="utf-8") as handle:
            m = json.load(handle)
            m["version"] = "1.1.0"
            handle.seek(0)
            handle.truncate()
            json.dump(m, handle)
        changed = self.installer.update_from_path(pkg)
        self.assertTrue(changed.ok)
        self.assertEqual(self.installer.store.get("demo_skill")["version"], "1.1.0")

    def test_installer_never_imports_skill_code(self):
        # The entrypoint contains code that would raise on import; if the
        # installer imported it, install would blow up. It must not.
        pkg = self._make_package()
        with open(os.path.join(pkg, "main.py"), "w", encoding="utf-8") as handle:
            handle.write("raise RuntimeError('this should never be imported')\n")
        result = self.installer.install_from_path(pkg)
        self.assertTrue(result.ok)  # installed fine, code never executed


if __name__ == "__main__":
    unittest.main()
