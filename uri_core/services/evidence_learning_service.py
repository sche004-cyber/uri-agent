from uri_core.services.evidence_fact_extractor import (
    EvidenceFactExtractor
)

from uri_core.core.fact_manager import (
    update_evidence_fact
)


class EvidenceLearningService:
    """
    Connects extracted documentary evidence with
    URI's Fact Manager.
    """

    def __init__(self):

        self.extractor = EvidenceFactExtractor()


    def learn_from_evidence(
        self,
        session,
        text,
        source
    ):
        """
        Extract facts from documentary evidence and
        safely store them in URI memory.
        """

        extracted_facts = self.extractor.extract(
            text=text,
            source=source
        )

        learning_results = []

        for evidence_fact in extracted_facts:

            result = update_evidence_fact(
                session=session,
                evidence_fact=evidence_fact
            )

            learning_results.append(
                {
                    "name": evidence_fact["name"],
                    "value": evidence_fact["value"],
                    "status": evidence_fact.get(
                        "status",
                        "VERIFIED"
                    ),
                    "action": result["action"]
                }
            )

        return {
            "success": True,
            "facts_found": len(extracted_facts),
            "learning_results": learning_results
        }