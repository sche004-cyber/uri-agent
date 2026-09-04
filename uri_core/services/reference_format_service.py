import os
try:
    from docx import Document
except ImportError:
    raise ImportError("Please run 'pip install python-docx' in your terminal.")

class ReferenceFormatService:
    """
    Extracts text structures (stencils) from reference Word documents
    and builds strict, fact-injected prompts for the Hermes drafting engine.
    """
    def __init__(self, templates_path=None):
        if templates_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.templates_path = os.path.join(project_root, "uri_templates")
        else:
            self.templates_path = templates_path

    def extract_stencil_text(self, filename: str) -> str:
        """Reads a reference docx file and extracts its text structure."""
        file_path = os.path.join(self.templates_path, filename)
        try:
            doc = Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            return "\n".join(full_text)
        except Exception as e:
            return f"[ERROR] Could not read template: {str(e)}"

    def build_drafter_prompt(self, template_category: str, filename: str, verified_facts: dict) -> str:
        """
        Dynamically injects verified facts while locking the document type,
        prohibiting invented numbering, and enforcing Indian English.
        """
        stencil_text = self.extract_stencil_text(filename)
        
        facts_block = ""
        for key, value in verified_facts.items():
            formatted_key = key.replace("_", " ")
            facts_block += f"- {formatted_key}: {value}\n"

        prompt = f"""
You are the official administrative drafter for NIT Sikkim. 
Your task is to draft an official administrative document following the exact tone, structure, and formatting of the provided Stencil.

CRITICAL DRAFTING RULES:
1. INDIAN ENGLISH CONVENTIONS: Use British/Indian English spelling and lexical conventions exclusively (e.g., programme, committee, ageing, licence, enrolment, utilise, candidature). Avoid American spelling variants (e.g., program, aging, enrollment, utilize).
2. PRESERVE DOCUMENT TYPE: Maintain internal file NOTING structure (hierarchical sign-offs like Chief Warden / Dean Student Welfare at the end). Do NOT convert it into an outgoing formal letter.
3. NO INVENTED NUMBERING: DO NOT add numerical paragraph indices (e.g., 1., 2., 3.) unless explicitly present in the reference Stencil text. Use clean, continuous prose paragraphs separated by blank lines.
4. FACT INCLUSION: You MUST incorporate all the Verified Facts and Data Tables provided below naturally and accurately into the text.
5. Output ONLY the final drafted text without any conversational filler or markdown code blocks around the whole text.

=== REFERENCE STENCIL STRUCTURE ===
{stencil_text}
===================================

=== VERIFIED FACTS & DATA TO INCLUDE ===
{facts_block}
========================================
"""
        return prompt.strip()
