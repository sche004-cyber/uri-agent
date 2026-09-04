from pathlib import Path

path = Path("test_orchestrator_workflow_resume.py")

text = path.read_text(encoding="utf-8")

text = text.replace(
    "import unittest\n",
    "import os\n"
    "import shutil\n"
    "import unittest\n",
    1
)

text = text.replace(
    """    def setUp(self):

        self.orchestrator = UriOrchestrator()
""",
    """    TEST_STORAGE = "uri_workspace/test_workflow_resume"

    def setUp(self):

        if os.path.exists(
            self.TEST_STORAGE
        ):
            shutil.rmtree(
                self.TEST_STORAGE
            )

        self.orchestrator = UriOrchestrator()

        self.orchestrator.session_manager = (
            __import__(
                "uri_core.core.state",
                fromlist=["SessionManager"]
            ).SessionManager(
                storage_path=self.TEST_STORAGE
            )
        )
""",
    1
)

text = text.replace(
    """    def test_paused_workflow_resumes_after_user_answer(
""",
    """    def tearDown(self):

        if os.path.exists(
            self.TEST_STORAGE
        ):
            shutil.rmtree(
                self.TEST_STORAGE
            )

    def test_paused_workflow_resumes_after_user_answer(
""",
    1
)

path.write_text(
    text,
    encoding="utf-8"
)

print(
    "Resume test isolation repaired successfully."
)
