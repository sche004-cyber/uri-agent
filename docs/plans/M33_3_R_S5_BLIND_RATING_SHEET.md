# M33.3-R S5 — Blind Wording Comparison (exploratory round 2)

Each item shows two wordings, **A** and **B**, for the same clarification. One is the deterministic template; the other is a model (Edge `qwen3.5-2b` or Capable `qwen3.5-9b`). Which is which is hidden (key: `M33_3_R_S5_EXPLORATORY_BLIND_KEY.json` — please do not open it before rating).

Set **valid** = the model wording passed the frozen S1 validator (a user could see it today). Set **shadow** = the model wording was rejected *only* for common words such as "or", "of", "is" (a user could see it only if the validator allowlist were widened). The last option, *None of these / Enter something else*, is always added by URI and is omitted here.

For each item reply with one of: `A`, `B`, `=` (no noticeable difference), `X` (both unacceptable). Optionally add `!` when the better one is worth ~1 s extra wait (e.g. `12 A!`).

### 1. “the policy version”  (EXPLAIN, valid)
- **A:** which recency you mean
    - recency 0
    - recency 1
    - recency 2
- **B:** Which recency matches "the policy version"?
    - recency 0
    - recency 1
    - recency 2

### 2. “the policy version”  (EXPLAIN, valid)
- **A:** Which recency do you mean?
    - recency 0
    - recency 1
    - recency 2
    - recency 3
- **B:** Which recency matches "the policy version"?
    - recency 0
    - recency 1
    - recency 2
    - recency 3

### 3. “that thread with Dana”  (EXPLAIN, valid)
- **A:** Which recency matches "that thread with Dana"?
    - recency 0
    - recency 1
- **B:** Which recency do you mean?
    - recency 0
    - recency 1

### 4. “the attachment”  (SIMPLE, shadow)
- **A:** which option you mean.
    - attachment title is attachment 1.pdf
    - attachment title is attachment 2.pdf
    - attachment title is attachment 3.pdf
    - attachment title is attachment 4.pdf
- **B:** Which item do you mean by "the attachment"?
    - Attachment 1.pdf · recency 0 · document
    - Attachment 2.pdf · recency 0 · document
    - Attachment 3.pdf · recency 0 · document
    - Attachment 4.pdf · recency 0 · document

### 5. “unknown attachment”  (SIMPLE, shadow)
- **A:** I could not find what "unknown attachment" refers to. What should I use?
- **B:** What is the title of the document?

### 6. “the attachment”  (SIMPLE, shadow)
- **A:** which option you mean.
    - signed_contract.pdf
    - contract_redline.docx
- **B:** Which item do you mean by "the attachment"?
    - signed_contract.pdf · recency 0 · attached to Contract renewal email · document
    - contract_redline.docx · recency 0 · attached to Contract renewal email · document

### 7. “Sam”  (SIMPLE, shadow)
- **A:** Which option you mean.
    - Finance owner
    - Legal owner
- **B:** Which item do you mean by "Sam"?
    - Sam Patel · Finance · recency 0 · person
    - Sam Okoro · Legal · recency 0 · person

### 8. “the other invoice”  (EXPLAIN, shadow)
- **A:** Which item do you mean by "the other invoice"?
    - Invoice INV-2240.pdf · Vendor B · recency 0 · document
    - Invoice INV-2252.pdf · Vendor C · recency 0 · document
- **B:** Which invoice should you choose?
    - Vendor B
    - Vendor C

### 9. “the proposal”  (EXPLAIN, shadow)
- **A:** Which owner does the proposal refer to?
    - Procurement
    - R&D
    - Facilities
    - HR
    - Finance
- **B:** Which owner matches "the proposal"?
    - Procurement
    - R&D
    - Facilities
    - HR
    - Finance

### 10. “the agenda”  (EXPLAIN, shadow)
- **A:** which document should you use for the meeting?
    - owner is PMO and title is Team meeting agenda.docx
    - owner is Secretariat and title is AGM agenda.pdf
- **B:** Which item do you mean by "the agenda"?
    - Team meeting agenda.docx · PMO · recency 0 · document
    - AGM agenda.pdf · Secretariat · recency 1 · document

### 11. “the form”  (EXPLAIN, shadow)
- **A:** which option you mean.
    - HR owner
    - Finance owner
    - IT Support owner
    - Procurement owner
    - PMO owner
- **B:** Which item do you mean by "the form"?
    - Leave request form.docx · HR · recency 0 · document
    - Expense claim form.xlsx · Finance · recency 1 · document
    - Access request form.pdf · IT Support · recency 2 · document
    - Purchase request form.docx · Procurement · recency 3 · document
    - Feedback form.docx · PMO · recency 4 · document

### 12. “the contract”  (REASONING, shadow)
- **A:** Which document should you select?
    - Document with recency 0
    - Document with recency 1
- **B:** Which item do you mean by "the contract"?
    - Supplier contract - Acme.pdf · Legal · recency 0 · document
    - Supplier contract - Birch.pdf · Legal · recency 1 · document

### 13. “first”  (SIMPLE, valid)
- **A:** Which item do you mean by "first"?
    - Minute 1.pdf · recency 0 · document
    - Minute 2.pdf · recency 1 · document
    - Minute 3.pdf · recency 2 · document
    - Minute 4.pdf · recency 3 · document
- **B:** Which item do you mean?
    - recency 0
    - recency 1
    - recency 2
    - recency 3

### 14. “missing report”  (SIMPLE, valid)
- **A:** What do you mean by missing report?
- **B:** I could not find what "missing report" refers to. What should I use?

### 15. “which file”  (SIMPLE, valid)
- **A:** Which item do you mean by "which file"?
    - First.pdf · recency 0 · document
    - Second.pdf · recency 0 · document
- **B:** Which file do you mean?
    - First.pdf
    - Second.pdf

### 16. “which file”  (SIMPLE, valid)
- **A:** Which item do you mean by "which file"?
    - One.pdf · recency 0 · document
    - Two.pdf · recency 0 · document
- **B:** Which file do you mean?
    - One.pdf
    - Two.pdf

### 17. “the policy version”  (EXPLAIN, valid)
- **A:** Which recency matches "the policy version"?
    - recency 0
    - recency 1
    - recency 2
    - recency 3
- **B:** which recency do you mean
    - recency 0
    - recency 1
    - recency 2
    - recency 3

### 18. “one of many”  (EXPLAIN, valid)
- **A:** Which file do you mean?
    - File 0.pdf
    - File 1.pdf
    - File 2.pdf
    - File 3.pdf
    - File 4.pdf
- **B:** Which item do you mean by "one of many"? There are 3 other matches; you can enter one.
    - File 0.pdf · recency 0 · document
    - File 1.pdf · recency 0 · document
    - File 2.pdf · recency 0 · document
    - File 3.pdf · recency 0 · document
    - File 4.pdf · recency 0 · document

### 19. “the other file”  (EXPLAIN, valid)
- **A:** Which item do you mean by "the other file"?
    - One.pdf · recency 0 · document
    - Two.pdf · recency 0 · document
- **B:** Which file do you mean?
    - One.pdf
    - Two.pdf

### 20. “the other invoice”  (EXPLAIN, valid)
- **A:** Which item do you mean by "the other invoice"?
    - Invoice INV-2240.pdf · Vendor B · recency 0 · document
    - Invoice INV-2252.pdf · Vendor C · recency 0 · document
- **B:** Which invoice do you mean?
    - owner Vendor B
    - owner Vendor C

### 21. “earlier”  (SIMPLE, shadow)
- **A:** Which item matches recency 0, recency 1, or recency 2?
    - recency 0
    - recency 1
    - recency 2
- **B:** Which item do you mean by "earlier"?
    - Minute 1.pdf · recency 0 · document
    - Minute 2.pdf · recency 1 · document
    - Minute 3.pdf · recency 2 · document

### 22. “one of five”  (SIMPLE, shadow)
- **A:** Which option do you mean?
    - File 0.pdf
    - File 1.pdf
    - File 2.pdf
    - File 3.pdf
    - File 4.pdf
- **B:** Which item do you mean by "one of five"?
    - File 0.pdf · recency 0 · document
    - File 1.pdf · recency 0 · document
    - File 2.pdf · recency 0 · document
    - File 3.pdf · recency 0 · document
    - File 4.pdf · recency 0 · document

### 23. “one of five”  (SIMPLE, shadow)
- **A:** Which item do you mean by "one of five"?
    - File 0.pdf · recency 0 · document
    - File 1.pdf · recency 0 · document
    - File 2.pdf · recency 0 · document
    - File 3.pdf · recency 0 · document
    - File 4.pdf · recency 0 · document
- **B:** Which option do you mean?
    - File 0.pdf
    - File 1.pdf
    - File 2.pdf
    - File 3.pdf
    - File 4.pdf

### 24. “which file”  (SIMPLE, shadow)
- **A:** Which item do you mean by "which file"?
    - First.pdf · recency 0 · document
    - Second.pdf · recency 0 · document
- **B:** Do you mean First.pdf or Second.pdf?
    - First.pdf
    - Second.pdf

### 25. “record”  (EXPLAIN, shadow)
- **A:** Which owner do you mean, North or South?
    - North
    - South
- **B:** Which owner matches "record"?
    - North
    - South

### 26. “that thread with Dana”  (EXPLAIN, shadow)
- **A:** Which recency matches "that thread with Dana"?
    - recency 0
    - recency 1
- **B:** Which recency do you mean: that thread with Dana at recency 0 or that thread with Dana at recency 1?
    - recency 0
    - recency 1

### 27. “the other invoice”  (EXPLAIN, shadow)
- **A:** Which invoice do you mean?
    - from Vendor B
    - from Vendor C
- **B:** Which item do you mean by "the other invoice"?
    - Invoice INV-2240.pdf · Vendor B · recency 0 · document
    - Invoice INV-2252.pdf · Vendor C · recency 0 · document

### 28. “Maria's report”  (EXPLAIN, shadow)
- **A:** Which owner matches "Maria's report"?
    - Maria Chen
    - Maria Santos
- **B:** Which owner do you mean, Maria Chen or Maria Santos?
    - Maria Chen
    - Maria Santos

### 29. “the budget”  (REASONING, shadow)
- **A:** Which item matches the budget?
    - Finance owner with recency 0 and title Q3 Budget.xlsx
    - Finance owner with recency 1 and title Q3 Budget - board copy.xlsx
- **B:** Which item do you mean by "the budget"?
    - Q3 Budget.xlsx · Finance · recency 0 · v3 · document
    - Q3 Budget - board copy.xlsx · Finance · recency 1 · v3 · document
