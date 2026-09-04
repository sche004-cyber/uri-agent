from uri_core.core.state import SessionState
from uri_core.core.facts import Fact
from uri_core.core.fact_manager import (
    update_fact,
    update_evidence_fact
)


print("=" * 65)
print("URI FACT MANAGER + EVIDENCE TEST")
print("=" * 65)


# --------------------------------------------------
# CREATE SESSION
# --------------------------------------------------

session = SessionState(
    session_id="evidence-test"
)


# --------------------------------------------------
# TEST 1
# CREATE A PROVISIONAL USER FACT
# --------------------------------------------------

print("\nTEST 1: CREATE PROVISIONAL FACT")

user_fact = Fact(
    name="insurer",
    value="SBI General Insurance",
    status="PROVISIONAL",
    source="User"
)

result = update_fact(
    session,
    user_fact
)

print("Action:", result["action"])
print(
    "Current insurer:",
    session.current_facts["insurer"].value
)
print(
    "Status:",
    session.current_facts["insurer"].status
)


# --------------------------------------------------
# TEST 2
# EVIDENCE CONFIRMS SAME FACT
# --------------------------------------------------

print("\nTEST 2: VERIFY SAME FACT FROM DOCUMENT")

evidence_fact = {
    "name": "insurer",
    "value": "SBI General Insurance",
    "status": "VERIFIED",
    "source": {
        "type": "gmail_attachment",
        "filename": "FINAL RATE QUOTE NIT SIKKIM.pdf"
    }
}

result = update_evidence_fact(
    session,
    evidence_fact
)

print("Action:", result["action"])

print(
    "Current insurer:",
    session.current_facts["insurer"].value
)

print(
    "Status:",
    session.current_facts["insurer"].status
)


# --------------------------------------------------
# TEST 3
# NEW EVIDENCE CHANGES FACT
# --------------------------------------------------

print("\nTEST 3: SUPERSEDE OLD FACT")

new_evidence_fact = {
    "name": "insurer",
    "value": "New India Assurance",
    "status": "VERIFIED",
    "source": {
        "type": "office_order",
        "filename": "New Insurance Approval.pdf"
    }
}

result = update_evidence_fact(
    session,
    new_evidence_fact
)

print("Action:", result["action"])


# --------------------------------------------------
# CURRENT FACT
# --------------------------------------------------

print("\nCURRENT FACT:")

current = session.current_facts["insurer"]

print("Value:", current.value)
print("Status:", current.status)
print("Source:", current.source)


# --------------------------------------------------
# HISTORICAL FACT
# --------------------------------------------------

print("\nHISTORICAL FACT:")

historical = session.historical_facts.get(
    "insurer"
)

if historical:

    print("Value:", historical.value)
    print("Status:", historical.status)
    print("Source:", historical.source)

else:

    print("No historical fact found.")


# --------------------------------------------------
# FINAL STATE
# --------------------------------------------------

print("\n" + "=" * 65)
print("FINAL URI MEMORY STATE")
print("=" * 65)


print("\nCURRENT FACTS:")

for name, fact in session.current_facts.items():

    print(
        f"{name} -> {fact.value} "
        f"[{fact.status}]"
    )


print("\nHISTORICAL FACTS:")

for name, fact in session.historical_facts.items():

    print(
        f"{name} -> {fact.value} "
        f"[{fact.status}]"
    )


print("\n" + "=" * 65)
print("TEST COMPLETE")
print("=" * 65)