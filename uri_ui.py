import sys
import os
import re
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLineEdit, 
                             QFrame)
from PyQt6.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.services.document_writer_service import DocumentWriterService
from uri_core.services.drive_service import DriveService

class GmailSyncThread(QThread):
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, orchestrator, session_id, query):
        super().__init__()
        self.orchestrator = orchestrator
        self.session_id = session_id
        self.query = query
        
    def run(self):
        try:
            res = self.orchestrator.process_evidence(self.session_id, self.query)
            self.finished_signal.emit(res)
        except Exception as e:
            self.finished_signal.emit({"success": False, "error": str(e)})

class DriveSyncThread(QThread):
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, query):
        super().__init__()
        self.query = query
        self.drive = DriveService()
        
    def run(self):
        try:
            res = self.drive.search_drive(self.query, limit=3)
            if not res.get("success"):
                self.finished_signal.emit({"success": False, "error": res.get("reason")})
                return
                
            files = res.get("files", [])
            if not files:
                self.finished_signal.emit({"success": True, "count": 0, "msg": "No files found."})
                return
                
            downloaded = []
            for f in files:
                dl_res = self.drive.download_file(f['id'], f['name'], f['mimeType'])
                if dl_res.get("success"):
                    downloaded.append(dl_res.get('exported_name'))
                    
            self.finished_signal.emit({"success": True, "count": len(downloaded), "files": downloaded})
        except Exception as e:
            self.finished_signal.emit({"success": False, "error": str(e)})

class UriDesktopCompanion(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.orchestrator = UriOrchestrator()
        self.session_id = "chetan_nit_sikkim"
        self.writer = DocumentWriterService()
        self.drive_service = DriveService()
        self.last_generated_text = ""
        self.gmail_thread = None
        self.drive_thread = None

        self.init_ui()
        self.old_pos = self.pos()
        QTimer.singleShot(1000, self.prompt_ready)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.container = QFrame(self)
        self.container.setStyleSheet("QFrame { background-color: #141414; border: 1px solid #262626; border-radius: 12px; }")
        container_layout = QVBoxLayout(self.container)
        
        header_layout = QHBoxLayout()
        self.title_label = QLabel("URI // CORE-SYNCED COPILOT", self)
        self.title_label.setStyleSheet("color: #ff7700; font-weight: bold;")
        
        self.min_button = QPushButton("-", self)
        self.min_button.setStyleSheet("background-color: #5555ff; color: white; border-radius: 4px; padding: 2px 8px; font-weight: bold;")
        self.min_button.clicked.connect(self.showMinimized)
        
        self.close_button = QPushButton("X", self)
        self.close_button.setStyleSheet("background-color: #ff5555; color: white; border-radius: 4px; padding: 2px 8px; font-weight: bold;")
        self.close_button.clicked.connect(QApplication.quit)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.min_button)
        header_layout.addWidget(self.close_button)
        container_layout.addLayout(header_layout)

        self.chat_display = QTextEdit(self)
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #0d0d0d; color: #d4d4d4; font-size: 12px; border: 1px solid #222; padding: 10px;")
        container_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setStyleSheet("background-color: #1a1a1a; color: #fff; border: 1px solid #333; padding: 8px;")
        self.input_field.returnPressed.connect(self.handle_user_message)
        input_layout.addWidget(self.input_field)
        container_layout.addLayout(input_layout)

        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
        self.resize(480, 420)

    def prompt_ready(self):
        self.chat_display.append("<b>URI:</b> Online. Type <b>sync drive for [keyword]</b> or <b>sync gmail</b>.\n")

    def handle_user_message(self):
        user_text = self.input_field.text().strip()
        if not user_text: return
        self.chat_display.append(f"<b>You:</b> {user_text}")
        self.input_field.clear()
        lower_text = user_text.lower()

        # Handle cleanup
        if lower_text in ["clear files", "clear memory", "delete files", "purge"]:
            res = self.drive_service.purge_downloads()
            count = res.get('deleted', 0)
            self.chat_display.append(f"<span style='color: #00ff00;'><b>URI:</b> Secure cleanup complete. Wiped {count} files from local memory.</span>\n")
            return

        # Restore Gmail Sync
        if lower_text == "sync gmail":
            self.chat_display.append("<i>[Background] Scanning Gmail documents...</i>")
            self.gmail_thread = GmailSyncThread(self.orchestrator, self.session_id, "New India Assurance OR insurance policy OR student database")
            self.gmail_thread.finished_signal.connect(self.on_gmail_sync_finished)
            self.gmail_thread.start()
            return

        # Smart Drive Sync
        if lower_text.startswith("sync drive"):
            query = lower_text.replace("sync drive", "").replace("for", "").strip()
            if not query:
                self.chat_display.append("<b>URI:</b> What should I search for? (e.g., type <b>sync drive for hostel</b>)\n")
                return
                
            self.chat_display.append(f"<i>[Background] Searching Drive for '{query}'...</i>")
            self.drive_thread = DriveSyncThread(query)
            self.drive_thread.finished_signal.connect(self.on_drive_sync_finished)
            self.drive_thread.start()
            return
            
        if "generate a file" in lower_text or "export" in lower_text:
            if self.last_generated_text:
                path = self.writer.save_draft_to_docx("Admin_Output.docx", self.last_generated_text)
                self.chat_display.append(f"<b>URI:</b> Saved to: {path}\n")
            return

        try:
            state_result = self.orchestrator.process_message(self.session_id, user_text)
            
            if state_result.get("task") == "student_query":
                self.chat_display.append(f"<b>URI:</b><br>{state_result.get('answer')}")
                self.chat_display.append("<i>Type 'clear files' to securely wipe these records from my local memory if you are done.</i>\n")
                return
            
            task = state_result.get("task", "general")
            if state_result.get("ready_to_draft"):
                self.last_generated_text = f"Draft for Task: {task}\nFacts: {state_result.get('current_facts')}"
                self.chat_display.append(f"<b>URI:</b> Ready to draft! Type 'export' to save.\n")
            elif state_result.get("next_question"):
                self.chat_display.append(f"<b>URI:</b> {state_result.get('next_question')}\n")
        except Exception as e:
            self.chat_display.append(f"<span style='color: #ff5555;'>[ERROR] {str(e)}</span>\n")

    def on_gmail_sync_finished(self, result):
        if result.get('success'):
            count = len(result.get('documents_processed', []))
            self.chat_display.append(f"<b>URI:</b> Gmail Sync complete! Processed {count} documents.\n")
        else:
            self.chat_display.append(f"<b>URI:</b> Gmail Sync failed: {result.get('error')}\n")

    def on_drive_sync_finished(self, result):
        if result.get('success'):
            count = result.get('count', 0)
            if count > 0:
                files_str = ', '.join(result.get('files', []))
                self.chat_display.append(f"<b>URI:</b> Secured {count} files: {files_str}.")
                self.chat_display.append("<i>They are ready to query. When finished, type 'clear files' to wipe them.</i>\n")
            else:
                self.chat_display.append(f"<b>URI:</b> {result.get('msg')}\n")
        else:
            self.chat_display.append(f"<b>URI:</b> Drive Sync failed: {result.get('error')}\n")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if not self.old_pos.isNull():
            self.move(self.pos() + event.globalPosition().toPoint() - self.old_pos)
            self.old_pos = event.globalPosition().toPoint()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = QPoint()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    uri_window = UriDesktopCompanion()
    uri_window.show()
    sys.exit(app.exec())
