import json
import os
from datetime import datetime


class SkillMemory:
    """
    Stores reusable task patterns learned from
    successful URI workflows.

    This is NOT factual evidence memory.

    It answers:
    'How has URI successfully handled this kind
    of task before?'
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

                matches.append(skill)

        if not matches:
            return None

        matches.sort(
            key=lambda skill: (
                skill.get(
                    "success_count",
                    0
                ),
                skill.get(
                    "last_used",
                    ""
                )
            ),
            reverse=True
        )

        return matches[0]

    def learn_skill(
        self,
        semantic_result: dict,
        workflow: list,
        tool_name=None
    ):

        memory = self._load()

        task_type = semantic_result.get(
            "task_type",
            ""
        )

        domain = semantic_result.get(
            "domain",
            ""
        )

        existing = None

        for skill in memory.get(
            "skills",
            []
        ):

            if (
                skill.get(
                    "task_type"
                ) == task_type
                and
                skill.get(
                    "domain"
                ) == domain
            ):

                existing = skill
                break

        now = datetime.now().isoformat()

        if existing:

            existing[
                "success_count"
            ] = (
                existing.get(
                    "success_count",
                    0
                )
                + 1
            )

            existing[
                "workflow"
            ] = workflow

            existing[
                "tool_name"
            ] = tool_name

            existing[
                "last_used"
            ] = now

        else:

            new_skill = {

                "task_type":
                    task_type,

                "domain":
                    domain,

                "workflow":
                    workflow,

                "tool_name":
                    tool_name,

                "success_count":
                    1,

                "created_at":
                    now,

                "last_used":
                    now
            }

            memory[
                "skills"
            ].append(
                new_skill
            )

        self._save(memory)

    def list_skills(self):

        memory = self._load()

        return memory.get(
            "skills",
            []
        )
