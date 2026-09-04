from PyQt6.QtCore import QThread, pyqtSignal
import time

class ExecutionWorker(QThread):
    status_update = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, orchestrator, session_id, user_text):
        super().__init__()
        self.orchestrator = orchestrator
        self.session_id = session_id
        self.user_text = user_text

    def run(self):
        try:
            self.status_update.emit("[Processing: Evaluating Request...]")
            
            # Temporary simulated orchestrator bypass until Phase 2 is built
            if self.orchestrator:
                result = self.orchestrator.process_user_input(self.session_id, self.user_text)
            else:
                time.sleep(1.5)  # Simulate API latency
                result = {"status": "success", "response": f"Processed: {self.user_text}"}
                
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e), "status": "failed"})


class SkillForgeWorker(QThread):
    status_update = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, tool_name, failure_context):
        super().__init__()
        self.tool_name = tool_name
        self.failure_context = failure_context

    def run(self):
        try:
            self.status_update.emit(f"[Processing: Forging Skill '{self.tool_name}'...]")
            time.sleep(2)  # Simulate Hermes sandbox build time
            
            result = {
                "tool_name": self.tool_name,
                "status": "forged_in_sandbox",
                "message": "Dry-Run verification completed. Pending human approval."
            }
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e), "status": "failed"})
