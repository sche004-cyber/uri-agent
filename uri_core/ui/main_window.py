import sys
from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QLineEdit, QPushButton, 
    QVBoxLayout, QWidget, QLabel, QApplication
)
from PyQt6.QtCore import Qt
from uri_core.ui.workers import ExecutionWorker
from uri_core.core.orchestrator import UriOrchestrator

class UriMainWindow(QMainWindow):
    def __init__(self, orchestrator=None):
        super().__init__()
        self.orchestrator = orchestrator
        self.session_id = "default_session"
        self.setWindowTitle("URI - Agentic Operating System")
        self.resize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(self.chat_display)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.status_label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter your command or goal...")
        self.input_field.setStyleSheet("font-size: 14px; padding: 8px;")
        self.input_field.returnPressed.connect(self.handle_user_submission)
        layout.addWidget(self.input_field)

        self.submit_button = QPushButton("Execute")
        self.submit_button.setStyleSheet("font-size: 14px; padding: 8px;")
        self.submit_button.clicked.connect(self.handle_user_submission)
        layout.addWidget(self.submit_button)

    def handle_user_submission(self):
        user_text = self.input_field.text().strip()
        if not user_text:
            return

        self.chat_display.append(f"<b>You:</b> {user_text}<br>")
        self.input_field.clear()
        
        self.input_field.setEnabled(False)
        self.submit_button.setEnabled(False)

        self.worker = ExecutionWorker(self.orchestrator, self.session_id, user_text)
        self.worker.status_update.connect(self.update_status)
        self.worker.finished.connect(self.render_response)
        self.worker.start()

    def update_status(self, message: str):
        self.status_label.setText(message)

    def render_response(self, result: dict):
        self.input_field.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.input_field.setFocus()
        self.status_label.setText("Ready.")

        if result.get("status") == "failed":
            error_msg = result.get("error", "Unknown Error")
            self.chat_display.append(f"<b style='color:red;'>URI System Error:</b> {error_msg}<br><br>")
        else:
            response_msg = result.get("response", str(result))
            self.chat_display.append(f"<b style='color:blue;'>URI:</b> {response_msg}<br><br>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # CRITICAL FIX: The Orchestrator is initialized here before the UI loads
    print("Booting URI Orchestrator...")
    active_orchestrator = UriOrchestrator()
    
    window = UriMainWindow(orchestrator=active_orchestrator)
    window.show()
    sys.exit(app.exec())
