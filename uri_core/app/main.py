from uri_core.services.reference_format_service import ReferenceFormatService
from uri_core.services.hermes_service import HermesService
from uri_core.services.document_writer_service import DocumentWriterService

def main():
    print("=" * 60)
    print("URI CORE 1.0 - HIGH-FIDELITY DRAFTING TEST")
    print("=" * 60)

    format_service = ReferenceFormatService()
    hermes = HermesService(use_local=False)
    writer = DocumentWriterService()

    # We are giving URI a much richer set of facts to work with!
    verified_facts = {
        "Subject": "Proposal for Extension of the Institute Group Insurance Policy",
        "Background_History": "The current group insurance policy for students provided by New India Assurance is expiring on September 15, 2026.",
        "Proposed_Action": "Extend the existing policy for a duration of exactly three months, from September 16, 2026, to December 15, 2026.",
        "Reason": "To ensure uninterrupted insurance coverage for the student body while the new annual contract is being tendered and finalized.",
        "Total_Students_Covered": 4,
        "Student_Database": """
| Name | Roll Number | DoB | Email ID | Phone Number |
|---|---|---|---|---|
| Aarav Patel | B23CS001 | 14-05-2003 | aarav.p@nitsikkim.ac.in | 9876543210 |
| Priya Sharma | B23EC015 | 22-11-2002 | priya.s@nitsikkim.ac.in | 8765432109 |
| Rohan Gupta | B23EE042 | 08-01-2004 | rohan.g@nitsikkim.ac.in | 7654321098 |
| Tenzin Bhutia | B23ME011 | 30-08-2003 | tenzin.b@nitsikkim.ac.in | 6543210987 |
"""
    }

    print("\n[1] Python Controller: Extracting Noting Stencil and Injecting Rich Facts...")
    hermes_prompt = format_service.build_drafter_prompt("01_Noting", "Noting.docx", verified_facts)

    print("\n[2] Hermes: Reading stencil and drafting final document...")
    final_draft = hermes.draft_document(hermes_prompt)

    print("\n[3] Document Writer: Saving final output to workspace...")
    output_filename = "Detailed_Noting_Draft.docx"
    saved_path = writer.save_draft_to_docx(output_filename, final_draft)

    print("\n" + "=" * 60)
    print(f"SUCCESS! FILE WRITTEN TO DESK:")
    print(f"{saved_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
