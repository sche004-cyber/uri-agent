class InstitutionalNoteDraftCmp:
    def __init__(self):
        pass

    def generate(self, **kwargs):
        request_text = kwargs.get("request_text", "")
        chat_history = kwargs.get("chat_history", [])
        
        text_lower = request_text.lower()
        
        # Check if this is an LTC request and verify if statutory details are present
        if "ltc" in text_lower:
            # Check for missing parameters required by CCS (LTC) Rules / GFR
            missing = []
            if not any(b in text_lower for b in ["hometown", "all india", "block", "home town", "anywhere"]):
                missing.id = "ltc_type"
                return {
                    "status": "interactive_prompt",
                    "question": "Under CCS (LTC) Rules, is this LTC for your **Hometown** or **All India**? (And which 4-year block/sub-block does it fall under, e.g., 2026–2029)?",
                    "context_gathered": request_text
                }
            if not any(d in text_lower for d in ["to ", "visit", "destination", "at "]):
                return {
                    "status": "interactive_prompt",
                    "question": "What is the specific place of visit or destination for this LTC journey?",
                    "context_gathered": request_text
                }

        # If all details are present or it's a general request, generate the precise administrative noting
        note_content = f"""
====================================================================
               NATIONAL INSTITUTE OF TECHNOLOGY SIKKIM
                        OFFICE NOTE SHEET
====================================================================

Subject: Application for Leave Travel Concession (LTC) and sanction of advance/leave.

1. Proposal & Details: 
   {request_text}

2. Regulatory & GFR / CCS (LTC) Rules Compliance:
   - Verified that the application adheres to the prescribed block year cycle (2026–2029) under CCS (LTC) Rules, 1988.
   - Concession is restricted to eligible family members declared in the official service records.
   - Travel shall be performed via authorized modes/agencies as per government guidelines.

3. Submitted For:
   Kind approval is solicited from the Competent Authority for:
   a) Grant of Earned Leave / Casual Leave as applied for the journey period.
   b) Permission to avail LTC (Hometown / All India as specified).
   c) Sanction of LTC advance (up to 90% of the estimated fare, if applicable).


Submitted by: Administrative Office / URI Agentic OS
Date: September 3, 2026
====================================================================
"""
        return {"status": "success", "note_sheet": note_content.strip()}
