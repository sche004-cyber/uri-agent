from uri_core.services.evidence_fact_extractor import EvidenceFactExtractor


sample_text = """
National Institute of Technology Sikkim intends to provide
Group Medical Insurance coverage to students for the
academic year 2026-27.

Approximately 850 students will be covered.

Approximately 560-600 students are currently covered
and require renewal.

Approximately 290 newly admitted students require
fresh coverage.

The quotation has been received from SBI General Insurance.
"""


source = {
    "type": "gmail_attachment",
    "filename": "FINAL RATE QUOTE NIT SIKKIM.pdf",
    "message_id": "test_message",
    "thread_id": "test_thread"
}


extractor = EvidenceFactExtractor()

facts = extractor.extract(
    text=sample_text,
    source=source
)


print("=" * 60)
print("URI EVIDENCE FACT EXTRACTION TEST")
print("=" * 60)

print()

for fact in facts:

    print("FACT:")
    print("Name:", fact["name"])
    print("Value:", fact["value"])
    print("Status:", fact["status"])
    print("Source:", fact["source"])
    print()

print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)