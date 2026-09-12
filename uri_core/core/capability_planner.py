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

        # M19 (audit finding #8): "document drafting"/"document
        # generation" task_type used to award draft_institutional_note
        # +100 on its own, so ANY drafting request - a project
        # proposal, a presentation, a spreadsheet - was routed straight
        # to the institutional-note tool regardless of what was
        # actually asked for. A document type/purpose signal is now
        # REQUIRED for each drafting tool to score at all; the bare
        # task_type alone is never enough. See generate_document below
        # for the generic (non-institutional-note/order) destination
        # such requests should reach instead.
        note_signal = (
            "office note" in requested_output
            or "noting" in requested_output
            or "office note" in entities_text
            or "noting" in entities_text
            or "note" in goal
            or "noting" in goal
        )

        order_signal = (
            "office order" in requested_output
            or "office order" in entities_text
            or "office order" in goal
            or "order" in goal
        )

        # A generic document/file request: the requested output or goal
        # names a FORMAT or a generic document genre, but not an
        # institutional note/order specifically.
        format_hint = any(
            keyword in requested_output or keyword in goal
            for keyword in (
                "presentation", "powerpoint", "slide", "slides", "slideshow",
                "spreadsheet", "excel", "workbook",
                "pdf",
                "proposal", "report", "document", "docx", "word document",
            )
        )

        if tool_name == "draft_institutional_note":

            if note_signal:

                if "office note" in requested_output or "noting" in requested_output:
                    score += 100

                if "office note" in entities_text or "noting" in entities_text:
                    score += 80

                if "note" in goal or "noting" in goal:
                    score += 40

                if "document drafting" in task_type:
                    score += 20

                if "administrative" in domain:
                    score += 10

        elif tool_name == "draft_institutional_order":

            if order_signal:

                if "document drafting" in task_type:
                    score += 20

                if "document generation" in task_type:
                    score += 20

                if "office order" in requested_output:
                    score += 100

                if "office order" in entities_text:
                    score += 100

                if "office order" in goal:
                    score += 60

                elif "order" in goal:
                    score += 20

        elif tool_name == "system_performance":

            performance_phrases = (
                "pc performance", "computer performance", "system performance",
                "cpu usage", "memory usage", "disk usage", "how is my pc",
                "how is my computer", "system metrics", "performance metric",
            )
            if any(
                phrase in goal or phrase in requested_output
                for phrase in performance_phrases
            ):
                score += 100

        elif tool_name == "remember_fact":

            # 2026-09-12 (User directive): a request to save/add
            # something to the user's profile was previously
            # unscored (0), so it lost to whatever else scored
            # anything at all - including, concretely, draft_
            # institutional_order/note whenever the semantic
            # interpreter's own paraphrase of "add this to my
            # profile" happened to contain a word like "order"
            # (see order_signal's bare substring match above).
            # Scored decisively high so an explicit save/remember
            # request always wins that competition.
            remember_phrases = (
                "add this to my profile", "add that to my profile",
                "add to my profile", "save to my profile",
                "save this to my profile", "remember that", "remember this",
                "save this to memory", "update my profile",
            )
            if any(
                phrase in goal or phrase in requested_output
                for phrase in remember_phrases
            ):
                score += 150

        elif tool_name == "recall_memory":

            # semantic_result's "goal" is the interpreter's own
            # paraphrase, not the user's raw words, so this matches
            # concepts rather than an exact phrase - kept narrow by
            # requiring a compound signal (a self/name/identity
            # reference together with a recall/question-ish word),
            # never a bare mention of "name" alone (which could just as
            # easily appear inside "draft a letter with my name on it").
            self_reference = any(
                keyword in goal or keyword in requested_output
                for keyword in ("my name", "user's name", "who i am", "who am i")
            )
            recall_signal = any(
                keyword in goal or keyword in requested_output
                for keyword in ("recall", "remember", "retrieve", "what do you know")
            )
            if self_reference or (recall_signal and "user" in goal):
                score += 100

        elif tool_name == "generate_document":

            # M19: the generic destination for a document/file request
            # that is NOT an institutional note or order - a project
            # proposal, a presentation, a spreadsheet, a PDF report.
            # Never competes with fetch_drive_spreadsheet's job of
            # reading an EXISTING Drive spreadsheet (see that tool's
            # own scoring below, which requires an explicit fetch/read
            # signal) - "prepare an excel sheet of X" with no such
            # signal is a creation request, not a read.
            if not note_signal and not order_signal:

                if (
                    "document drafting" in task_type
                    or "document generation" in task_type
                ):
                    score += 40

                if any(
                    keyword in requested_output
                    for keyword in ("presentation", "powerpoint", "slide", "slides")
                ):
                    score += 100

                if any(
                    keyword in goal
                    for keyword in ("presentation", "powerpoint", "slide", "slides")
                ):
                    score += 60

                if any(
                    keyword in requested_output
                    for keyword in ("spreadsheet", "excel", "workbook")
                ):
                    score += 80

                if any(
                    keyword in goal
                    for keyword in ("spreadsheet", "excel", "workbook")
                ):
                    score += 50

                if "pdf" in requested_output or "pdf" in goal:
                    score += 70

                if any(
                    keyword in requested_output
                    for keyword in ("proposal", "report", "document", "docx", "word document")
                ):
                    score += 60

                if any(
                    keyword in goal
                    for keyword in ("proposal", "report")
                ):
                    score += 30

                if format_hint and "document drafting" in task_type:
                    score += 20

        elif tool_name == "convert_document":

            # Narrow and specific on purpose (2026-09-12 lesson from
            # web_search's own over-broad keyword regression): only
            # "convert" itself, combined with a target format word,
            # ever scores here - never a bare format word alone, which
            # would also match a from-scratch generate_document request.
            if "convert" in goal or "convert" in requested_output:
                if any(
                    keyword in goal or keyword in requested_output
                    for keyword in ("word", "docx", ".doc")
                ):
                    score += 100

        elif tool_name == "gmail_search":

            # 2026-09-12 (User directive): previously unscored entirely
            # (always 0), so a real, connected Gmail request like "how
            # many unread emails" had nothing to compete with
            # web_search's own broad keyword match on "search" and
            # fell through to a generic web search for the literal
            # word "gmail" instead of ever querying the account. "mail"
            # bare is deliberately excluded (too generic - postal mail,
            # "email me the report", etc.); "gmail"/"inbox"/"unread
            # email(s)" are specific enough to stay narrow.
            gmail_keywords = ("gmail", "inbox", "unread email", "unread message")
            if any(
                keyword in goal or keyword in requested_output or keyword in entities_text
                for keyword in gmail_keywords
            ):
                score += 100

        elif tool_name == "web_search":

            web_keywords = (
                "search", "web", "website", "online", "internet", "google",
                "look through", "find information", "latest", "portal", "nit sikkim",
            )

            if "web search" in task_type or "information retrieval" in task_type:
                score += 50

            if any(
                keyword in goal
                or keyword in requested_output
                or keyword in entities_text
                for keyword in web_keywords
            ):
                score += 60

            if (
                "website" in goal
                or "website" in requested_output
                or "nit sikkim" in goal
            ):
                score += 50

        elif tool_name == "fetch_url":

            if (
                "http://" in goal
                or "https://" in goal
                or "http://" in requested_output
                or "https://" in requested_output
            ):
                score += 100

            if "fetch" in goal and any(
                keyword in goal for keyword in ("url", "page", "link")
            ):
                score += 70

        elif tool_name == "read_attached_file":

            if any(
                keyword in goal for keyword in ("attachment", "attached", "upload")
            ):
                score += 100

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

            # M19: this tool READS an EXISTING Google Sheet - it must
            # not win for a request to CREATE a new spreadsheet (that
            # is generate_document's job). Requires an explicit
            # fetch/read signal, or an explicit reference to a
            # spreadsheet that already exists (a Google/Drive sheet, or
            # an id), not just the bare word "spreadsheet"/"sheet".
            fetch_verbs = (
                "fetch", "read", "pull", "retrieve", "open", "load",
                "sync", "get", "check", "look up", "find",
            )
            has_fetch_verb = any(
                verb in goal or verb in requested_output
                for verb in fetch_verbs
            )
            existing_sheet_reference = (
                "google sheet" in entities_text
                or "google sheet" in goal
                or "drive spreadsheet" in entities_text
                or "spreadsheet_id" in entities_text
                or "spreadsheet id" in entities_text
            )

            if existing_sheet_reference:
                score += 100

            if "data retrieval" in task_type and (
                has_fetch_verb or existing_sheet_reference
            ):
                score += 50

            if has_fetch_verb and (
                "spreadsheet" in requested_output or "sheet" in requested_output
            ):
                score += 60

            if has_fetch_verb and (
                "spreadsheet" in goal or "sheet" in goal
            ):
                score += 40

            if any(
                token in entities_text
                for token in [
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
                # "not_implemented" (no execution adapter exists at
                # all) vs "unavailable_runtime" (an adapter exists but
                # this runtime can't use it right now) - see
                # CapabilityDescriptor.gap_reason. The response-
                # narrative path treats these very differently: only
                # the former forbids implying that more detail/
                # authorization would make it executable.
                "reason": gap.gap_reason,
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
