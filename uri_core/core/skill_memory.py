import json
import os
from datetime import datetime, timezone


# M18: a skill is only ever RECALLED (offered to the Brain as an
# advisory reference) while its confidence stays at or above this floor.
# Confidence is successes / (successes + failures), so a pattern that
# used to work but has since failed repeatedly falls below the floor and
# stops being surfaced - URI can un-learn a formerly-good approach that
# went bad, instead of reinforcing it forever. The skill is never
# deleted (its history stays inspectable); it simply stops being
# recommended. Never authority: even a high-confidence skill is only a
# suggestion the Brain may ignore, and can never override Soul, policy,
# authorization, or a safety boundary.
CONFIDENCE_RECALL_FLOOR = 0.34


class SkillMemory:
    """
    Stores reusable task patterns learned from URI workflows, with an
    honest success/failure record so a pattern can lose confidence and
    stop being recommended when it stops working (M18).

    This is NOT factual evidence memory.

    It answers:
    'How has URI handled this kind of task before, and is that approach
    still working?'
    """

    def __init__(
        self,
        storage_path="uri_workspace/skill_memory.json"
    ):
        self.storage_path = os.path.normpath(
            storage_path
        )

        self._ensure_storage()

    def _ensure_storage(self):

        folder = os.path.dirname(
            self.storage_path
        )

        if folder and not os.path.exists(folder):
            os.makedirs(
                folder,
                exist_ok=True
            )

        if not os.path.exists(
            self.storage_path
        ):

            self._save({
                "skills": []
            })

    def _load(self):

        try:

            with open(
                self.storage_path,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except (
            FileNotFoundError,
            json.JSONDecodeError
        ):

            return {
                "skills": []
            }

    def _save(self, data):

        with open(
            self.storage_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    # ------------------------------------------------------------------
    # Derived signals
    # ------------------------------------------------------------------

    @staticmethod
    def confidence(skill: dict) -> float:
        """successes / (successes + failures). A skill with no recorded
        outcomes at all is treated as fully confident (1.0) so a freshly
        learned success is immediately usable; once any failure is
        recorded, confidence reflects the real ratio."""
        successes = skill.get("success_count", 0)
        failures = skill.get("failure_count", 0)
        total = successes + failures
        if total <= 0:
            return 1.0
        return successes / total

    def _recall_score(self, skill: dict):
        """Ordering key for choosing among matching skills: confidence
        first (a reliable pattern beats a shaky one), then raw success
        count, then recency. A tuple sorted descending."""
        return (
            self.confidence(skill),
            skill.get("success_count", 0),
            skill.get("last_used", ""),
        )

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------

    def find_matching_skill(
        self,
        semantic_result: dict
    ):

        memory = self._load()

        task_type = (
            semantic_result
            .get("task_type", "")
            .strip()
            .lower()
        )

        domain = (
            semantic_result
            .get("domain", "")
            .strip()
            .lower()
        )

        matches = []

        for skill in memory.get(
            "skills",
            []
        ):

            if (
                skill.get(
                    "task_type",
                    ""
                ).lower() == task_type
                and
                skill.get(
                    "domain",
                    ""
                ).lower() == domain
            ):

                # M18: a pattern whose confidence has fallen below the
                # recall floor (it keeps failing) is not recommended.
                if self.confidence(skill) < CONFIDENCE_RECALL_FLOOR:
                    continue

                matches.append(skill)

        if not matches:
            return None

        matches.sort(
            key=self._recall_score,
            reverse=True
        )

        return matches[0]

    # ------------------------------------------------------------------
    # Learning (outcome recording)
    # ------------------------------------------------------------------

    def _find_existing(self, memory, task_type, domain):
        for skill in memory.get("skills", []):
            if (
                skill.get("task_type") == task_type
                and skill.get("domain") == domain
            ):
                return skill
        return None

    def record_outcome(
        self,
        semantic_result: dict,
        success: bool,
        workflow: list = None,
        tool_name=None,
    ):
        """Record that a skill-shaped approach for this task_type/domain
        just succeeded or failed. Successes reinforce (and refresh the
        recorded workflow/tool); failures are counted too, which is what
        lets confidence fall and recall stop. Never raises on a normal
        outcome record."""

        memory = self._load()

        task_type = semantic_result.get("task_type", "")
        domain = semantic_result.get("domain", "")

        now = datetime.now(timezone.utc).isoformat()

        existing = self._find_existing(memory, task_type, domain)

        if existing is not None:
            if success:
                existing["success_count"] = existing.get("success_count", 0) + 1
                # Only a success refreshes the recorded approach - a
                # failure must not overwrite a known-good workflow with
                # the one that just failed.
                if workflow is not None:
                    existing["workflow"] = workflow
                if tool_name is not None:
                    existing["tool_name"] = tool_name
            else:
                existing["failure_count"] = existing.get("failure_count", 0) + 1

            existing["last_used"] = now
            existing["last_outcome"] = "success" if success else "failure"
            existing["confidence"] = self.confidence(existing)

        else:
            skill = {
                "task_type": task_type,
                "domain": domain,
                "workflow": workflow if workflow is not None else [],
                "tool_name": tool_name,
                "success_count": 1 if success else 0,
                "failure_count": 0 if success else 1,
                "last_outcome": "success" if success else "failure",
                "created_at": now,
                "last_used": now,
            }
            skill["confidence"] = self.confidence(skill)
            memory["skills"].append(skill)

        self._save(memory)

    def learn_skill(
        self,
        semantic_result: dict,
        workflow: list,
        tool_name=None
    ):
        """Backwards-compatible success recorder - existing callers that
        only ever recorded successes keep working unchanged."""
        self.record_outcome(
            semantic_result=semantic_result,
            success=True,
            workflow=workflow,
            tool_name=tool_name,
        )

    def record_failure(
        self,
        semantic_result: dict,
        tool_name=None,
    ):
        """Record that a matching approach for this task_type/domain
        failed this time. Counted so confidence can fall; never
        overwrites the known-good workflow."""
        self.record_outcome(
            semantic_result=semantic_result,
            success=False,
            workflow=None,
            tool_name=tool_name,
        )

    def list_skills(self):

        memory = self._load()

        return memory.get(
            "skills",
            []
        )
