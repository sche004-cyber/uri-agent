class InstitutionalOrderDraftCmp:
    def __init__(self):
        pass

    def generate(self, **kwargs):
        request_text = kwargs.get("request_text", "Administrative Order Request")
        
        order_content = f"""
====================================================================
               NATIONAL INSTITUTE OF TECHNOLOGY SIKKIM
                        OFFICE OF THE REGISTRAR / DIRECTOR
====================================================================

No. NITS/2026/Admin/Order/___                              Dated: September 3, 2026

                               OFFICE ORDER

Sanction of the Competent Authority is hereby accorded with respect to the following administrative submission:

{request_text}

All concerned officials are requested to take necessary action accordingly. The expenditure involved is debitable to the appropriate budget head of the Institute.

This is issued with the approval of the Competent Authority.


                                                        Registrar / Dean (Admin)
                                                        NIT Sikkim
====================================================================
"""
        return {"status": "success", "note_sheet": order_content.strip()}
