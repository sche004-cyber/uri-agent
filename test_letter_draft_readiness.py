from uri_core.core.clarification import (
    get_next_question
)


def show_question(question):
    if question:
        print(question["question"])
    else:
        print("None")


print("=" * 65)
print("URI LETTER DRAFT READINESS TEST")
print("=" * 65)


current_facts = {}


# =========================================================
# STAGE 1
# =========================================================

print()
print("STAGE 1: EMPTY LETTER CONTEXT")
print()

question = get_next_question(
    task="letter",
    current_facts=current_facts
)

print("Next Question:")
show_question(question)


# =========================================================
# STAGE 2
# =========================================================

print()
print("=" * 65)
print("STAGE 2: RECIPIENT PROVIDED")
print("=" * 65)

current_facts["recipient"] = (
    "The Registrar, NIT Sikkim"
)

question = get_next_question(
    task="letter",
    current_facts=current_facts
)

print()
print("Next Question:")
show_question(question)


# =========================================================
# STAGE 3
# =========================================================

print()
print("=" * 65)
print("STAGE 3: SUBJECT PROVIDED")
print("=" * 65)

current_facts["subject"] = (
    "Student Medical Insurance"
)

question = get_next_question(
    task="letter",
    current_facts=current_facts
)

print()
print("Next Question:")
show_question(question)


# =========================================================
# STAGE 4
# =========================================================

print()
print("=" * 65)
print("STAGE 4: PURPOSE PROVIDED")
print("=" * 65)

current_facts["purpose"] = (
    "To request approval for procurement "
    "of student medical insurance."
)

question = get_next_question(
    task="letter",
    current_facts=current_facts
)

print()
print("Next Question:")
show_question(question)

print()

if question is None:
    print("READY TO DRAFT: True")
    print()
    print(
        "PASS: URI HAS ALL REQUIRED "
        "LETTER INFORMATION."
    )
else:
    print("READY TO DRAFT: False")
    print()
    print(
        "FAIL: URI STILL REQUIRES "
        "ADDITIONAL INFORMATION."
    )


print()
print("=" * 65)
print("TEST COMPLETE")
print("=" * 65)
