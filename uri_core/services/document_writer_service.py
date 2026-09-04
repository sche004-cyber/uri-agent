import os
try:
    from docx import Document
except ImportError:
    raise ImportError("Please run 'pip install python-docx' in your terminal.")

class DocumentWriterService:
    """
    Takes the finalized draft text from Hermes, parses markdown elements,
    and outputs clean, professionally formatted Microsoft Word documents (.docx).
    """
    def __init__(self, workspace_path=None):
        if workspace_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.workspace_path = os.path.join(project_root, "uri_workspace")
        else:
            self.workspace_path = workspace_path
        
        os.makedirs(self.workspace_path, exist_ok=True)

    def save_draft_to_docx(self, filename: str, draft_text: str) -> str:
        """Parses draft text and builds native Word tables where markdown tables appear."""
        file_path = os.path.join(self.workspace_path, filename)
        
        try:
            doc = Document()
            lines = draft_text.split("\n")
            
            table_buffer = []
            in_table = False

            for line in lines:
                stripped = line.strip()
                
                # Detect markdown table rows
                if stripped.startswith("|") and stripped.endswith("|"):
                    # Skip markdown separator rows like |---|---|
                    if "---" in stripped:
                        continue
                    
                    in_table = True
                    cells = [c.strip() for c in stripped.split("|")[1:-1]]
                    table_buffer.append(cells)
                else:
                    # If we just finished a table block, render it into Word natively
                    if in_table:
                        self._add_table_to_doc(doc, table_buffer)
                        table_buffer = []
                        in_table = False
                    
                    # Handle normal paragraphs
                    if stripped:
                        doc.add_paragraph(stripped)
                    else:
                        doc.add_paragraph()

            # Catch any table left at the end of the text
            if in_table and table_buffer:
                self._add_table_to_doc(doc, table_buffer)
                    
            doc.save(file_path)
            return file_path
        except Exception as e:
            return f"[ERROR] Could not save document: {str(e)}"

    def _add_table_to_doc(self, doc, table_data):
        """Helper method to construct native Word tables with clean borders."""
        if not table_data:
            return
            
        num_rows = len(table_data)
        num_cols = max(len(row) for row in table_data)
        
        table = doc.add_table(rows=num_rows, cols=num_cols)
        table.style = 'Table Grid'
        
        for r_idx, row_values in enumerate(table_data):
            for c_idx, val in enumerate(row_values):
                if c_idx < num_cols:
                    cell = table.cell(r_idx, c_idx)
                    cell.text = val
        
        # Add spacing after table
        doc.add_paragraph()
