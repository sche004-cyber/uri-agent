import json
import os

from uri_core.core.capability_registry import CapabilityRegistry


class CapabilityPlanner:
    """
    Selects the most appropriate registered capability using
    structured semantic information.

    URI never invents tool names.
    Weak incidental matches are rejected so that URI does not
    execute an unrelated capability.
    """

    MIN_CONFIDENCE_SCORE = 50

    def __init__(
        self,
        registry_path="uri_workspace/capabilities_registry.json"
    ):
        self.registry_path = os.path.normpath(registry_path)
        self.capability_registry = CapabilityRegistry(
            registry_path=self.registry_path
        )

    def _load_tools(self):
        try:
            with open(
                self.registry_path,
                "r",
                encoding="utf-8-sig"
            ) as f:
                registry = json.load(f)

            return registry.get("active_tools", {})

        except (
            FileNotFoundError,
            json.JSONDecodeError
        ):
            return {}

    def _score_tool(
        self,
        tool_name: str,
        semantic_result: dict
    ) -> int:

        task_type = str(
            semantic_result.get("task_type", "")
        ).lower()

        domain = str(
            semantic_result.get("domain", "")
        ).lower()

        goal = str(
            semantic_result.get("goal", "")
        ).lower()

        requested_output = str(
            semantic_result.get("requested_output", "")
        ).lower()

        entities = semantic_result.get("entities", [])

        if not isinstance(entities, list):
            entities = []

        entities_text = " ".join(
            str(entity).lower()
            for entity in entities
        )

        score = 0

        if tool_name == "draft_institutional_note":

            if "document drafting" in task_type:
                score += 100

            if "office note" in requested_output:
                score += 80

            if "office note" in entities_text:
                score += 80

            if "note" in goal:
                score += 30

            if "administrative" in domain:
                score += 10

        elif tool_name == "draft_institutional_order":

            if "document drafting" in task_type:
                score += 40

            if "document generation" in task_type:
                score += 40

            if "office order" in requested_output:
                score += 100

            if "office order" in entities_text:
                score += 100

            if "office order" in goal:
                score += 60

            elif "order" in goal:
                score += 20

        elif tool_name == "extract_student_records":

            if "data retrieval" in task_type:
                score += 50

            if "academic records" in domain:
                score += 80

            if "cgpa" in requested_output:
                score += 100

            if "cgpa" in goal:
                score += 80

            if "academic record" in requested_output:
                score += 80

            if any(
                token in entities_text
                for token in [
                    "btech",
                    "roll number",
                    "student id"
                ]
            ):
                score += 20

        elif tool_name == "fetch_drive_spreadsheet":

            if "data retrieval" in task_type:
                score += 30

            if "spreadsheet" in requested_output:
                score += 100

            if "spreadsheet" in goal:
                score += 80

            if "sheet" in requested_output:
                score += 50

            if "sheet" in goal:
                score += 40

            if any(
                token in entities_text
                for token in [
                    "spreadsheet",
                    "worksheet",
                    "google sheet",
                    "table"
                ]
            ):
                score += 40

        return score

    def _known_gaps(self) -> list:
        """Informational only - never used for selection (see
        CapabilityDescriptor.is_executable, which excludes every entry
        this returns). A capability_registry read failure must never
        break planning, so this degrades to an empty list rather than
        raising, matching this codebase's existing
        never-break-the-live-request discipline."""

        try:
            gaps = self.capability_registry.known_gaps()

        except Exception:
            return []

        return [
            {
                "id": gap.id,
                "description": gap.description,
                "status": gap.status,
                "limitations": gap.limitations,
            }
            for gap in gaps
        ]

    def plan(
        self,
        semantic_result: dict
    ) -> dict:

        tools = self._load_tools()

        if not tools:

            return {
                "status": "planning_required",
                "tool_name": None,
                "reason":
                    "No registered capabilities are available.",
                "known_gaps": self._known_gaps()
            }

        candidates = []

        for tool_name in tools:

            score = self._score_tool(
                tool_name,
                semantic_result
            )

            if score >= self.MIN_CONFIDENCE_SCORE:

                candidates.append(
                    {
                        "tool_name": tool_name,
                        "score": score
                    }
                )

        if not candidates:

            return {
                "status": "planning_required",
                "tool_name": None,
                "reason":
                    "URI understands the task but no registered capability confidently matches the required work.",
                "known_gaps": self._known_gaps()
            }

        candidates.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        best = candidates[0]

        return {
            "status": "capability_selected",
            "tool_name": best["tool_name"],
            "reason":
                "Selected the highest-confidence registered capability based on structured semantic understanding.",
            "confidence_score": best["score"]
        }
