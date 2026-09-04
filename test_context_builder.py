from uri_core.core.facts import Fact
from uri_core.core.context_builder import (
    build_task_context,
    get_draft_readiness,
)


def print_section(title):
    print()
    print("=" * 65)
    print(title)
    print("=" * 65)
    print()


def print_context(context):

    print("TASK:")
    print(context["task"])

    print()
    print("TASK FACTS:")

    if not context["task_facts"]:
        print("None")
    else:
        for name, fact in context["task_facts"].items():
            print(
                name,
                "->",
                fact.value,
                "[",
                fact.status,
                "]"
            )

    print()
    print("VERIFIED EVIDENCE:")

    if not context["verified_evidence"]:
        print("None")
    else:
        for name, fact in context[
            "verified_evidence"
        ].items():
            print(
                name,
                "->",
                fact.value,
                "[",
                fact.status,
                "]"
            )

    print()
    print("SATISFIED FIELDS:")

    if not context["satisfied_fields"]:
        print("None")
    else:
        for item in context[
            "satisfied_fields"
        ]:
            print(
                item["field"],
                "->",
                item["source"]
            )

    print()
    print("MISSING FIELDS:")

    if not context["missing_fields"]:
        print("None")
    else:
        for field_name in context[
            "missing_fields"
        ]:
            print("-", field_name)

    print()
    print(
        "READY TO DRAFT:",
        context["ready_to_draft"]
    )


# =========================================================
# VERIFIED EVIDENCE
# =========================================================

relevant_evidence = {

    "institution": Fact(
        name="institution",
        value="NIT Sikkim",
        status="VERIFIED",
        source="Evidence"
    ),

    "academic_year": Fact(
        name="academic_year",
        value="2026-27",
        status="VERIFIED",
        source="Evidence"
    ),

    "insurance_type": Fact(
        name="insurance_type",
        value="Group Medical Insurance",
        status="VERIFIED",
        source="Evidence"
    ),

    "insurer": Fact(
        name="insurer",
        value="SBI General Insurance",
        status="VERIFIED",
        source="Evidence"
    ),

    "approx_total_students": Fact(
        name="approx_total_students",
        value="850",
        status="VERIFIED",
        source="Evidence"
    ),
}


# =========================================================
# START NOTING TASK
# =========================================================

current_facts = {}

print_section(
    "URI CONTEXT BUILDER TEST"
)

print_section(
    "STAGE 1: INITIAL NOTING"
)

context = build_task_context(
    task="noting",
    current_facts=current_facts,
    relevant_evidence=relevant_evidence,
)

print_context(context)


# =========================================================
# USER PROVIDES APPROVAL REQUEST
# =========================================================

current_facts[
    "approval_requested"
] = Fact(
    name="approval_requested",
    value=(
        "Approval for procurement of "
        "Group Medical Insurance."
    ),
    status="PROVISIONAL",
    source="User"
)


print_section(
    "STAGE 2: APPROVAL PROVIDED"
)

context = build_task_context(
    task="noting",
    current_facts=current_facts,
    relevant_evidence=relevant_evidence,
)

print_context(context)


# =========================================================
# USER PROVIDES JUSTIFICATION
# =========================================================

current_facts[
    "justification"
] = Fact(
    name="justification",
    value=(
        "To provide medical insurance coverage "
        "to eligible students for the academic year."
    ),
    status="PROVISIONAL",
    source="User"
)


print_section(
    "STAGE 3: JUSTIFICATION PROVIDED"
)

context = build_task_context(
    task="noting",
    current_facts=current_facts,
    relevant_evidence=relevant_evidence,
)

print_context(context)


# =========================================================
# FINAL READINESS REPORT
# =========================================================

print_section(
    "FINAL DRAFT READINESS REPORT"
)

readiness = get_draft_readiness(
    task="noting",
    current_facts=current_facts,
    relevant_evidence=relevant_evidence,
)

print(
    "Task:",
    readiness["task"]
)

print(
    "Ready To Draft:",
    readiness["ready_to_draft"]
)

print(
    "Missing Fields:",
    readiness["missing_fields"]
)


print()

if readiness["ready_to_draft"]:

    print(
        "PASS: URI HAS ENOUGH CONTEXT "
        "TO BEGIN DRAFTING."
    )

else:

    print(
        "FAIL: URI STILL REQUIRES "
        "ADDITIONAL INFORMATION."
    )


print()
print("=" * 65)
print("TEST COMPLETE")
print("=" * 65)
