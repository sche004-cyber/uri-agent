from pathlib import Path

path = Path("uri_core/core/orchestrator.py")
text = path.read_text(encoding="utf-8")

# Add imports
old_import = "from uri_core.services.evidence_processor import EvidenceProcessor\n"

new_import = """from uri_core.services.evidence_processor import EvidenceProcessor
from uri_core.services.student_query_service import StudentQueryService

import re
"""

assert old_import in text, "EvidenceProcessor import anchor not found"

text = text.replace(old_import, new_import, 1)

# Add service initialization
old_init = """        self.evidence_processor = (
            EvidenceProcessor()
        )
"""

new_init = """        self.evidence_processor = (
            EvidenceProcessor()
        )

        self.student_query_service = (
            StudentQueryService()
        )
"""

assert old_init in text, "EvidenceProcessor initialization anchor not found"

text = text.replace(old_init, new_init, 1)

# Insert roll-number handling immediately after GET SESSION block
anchor = """        session = (
            self.session_manager.get_session(
                session_id
            )
        )


        # =================================================
        # DETECT INTENT
"""

replacement = """        session = (
            self.session_manager.get_session(
                session_id
            )
        )


        # =================================================
        # STUDENT RECORD QUERY DETECTION
        # =================================================

        roll_match = re.search(
            r"\\b[A-Z]\\d{6,}[A-Z]{1,4}\\b",
            message.upper()
        )

        if roll_match:

            roll_number = roll_match.group(0)

            student_result = (
                self.student_query_service
                .answer_student_query(
                    roll_number
                )
            )

            return {
                "session_id": session.session_id,
                "task": "student_query",
                "detected_task": "student_query",
                "task_switched": False,
                "message": message,
                "student_query": student_result,
                "answer": student_result.get("answer"),
                "next_question": None,
                "ready_to_draft": False,
                "missing_fields": [],
                "clarification_complete": True,
            }


        # =================================================
        # DETECT INTENT
"""

assert anchor in text, "process_message session anchor not found"

text = text.replace(anchor, replacement, 1)

path.write_text(text, encoding="utf-8")

print("ORCHESTRATOR STUDENT QUERY INTEGRATION COMPLETE")
