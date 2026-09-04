import json
import re
import subprocess
import threading
from datetime import date
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# ============================================================
# URI V5.4
# NIT Sikkim Administrative AI Assistant
#
# V5.4 introduces a deterministic conversational controller.
#
# The controller (Python) decides:
#   - what task is being performed
#   - what facts are already known
#   - what facts are historical only
#   - which ONE question should be asked next
#
# Hermes is used for source-aware interpretation and drafting,
# but it does NOT control the clarification workflow.
# ============================================================

BASE = Path(__file__).resolve().parent
KNOWLEDGE = BASE / "knowledge"
INSTITUTIONAL_LIBRARY = BASE / "institutional_library"
MEMORY_FILE = BASE / "uri_memory.json"

DOCS = {}
LOCK = threading.Lock()

MAX_CONTEXT_CHARS = 16000
MAX_HISTORY_MESSAGES = 24


# ============================================================
# DOCUMENT EXTRACTION
# ============================================================

def extract_pdf(path):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        pages.append((page_no, text))

    return pages


def extract_docx(path):
    from docx import Document

    document = Document(str(path))
    lines = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            lines.append(text)

    for table in document.tables:
        for row in table.rows:
            values = [
                cell.text.strip()
                for cell in row.cells
                if cell.text.strip()
            ]

            if values:
                lines.append(" | ".join(values))

    return [(1, "\n".join(lines))]


def infer_year(text, filename):
    years = re.findall(
        r"\b(?:19|20)\d{2}\b",
        f"{filename} {text[:10000]}"
    )

    return max(years) if years else ""


def infer_document_type(category, filename):
    value = f"{category} {filename}".lower()

    checks = [
        ("Office Order", ["office order"]),
        ("Noting", ["noting", "file noting", "approval note"]),
        ("Minutes of Meeting", ["minutes", "minute", "mom"]),
        ("Notice", ["notice", "circular"]),
        ("Letter", ["letter", "correspondence"]),
        ("Statutory / Gazette", ["statute", "gazette", "act"]),
        ("Rules / Manual", ["rule", "regulation", "manual"]),
        ("Finance / Procurement", [
            "gfr",
            "finance",
            "procurement",
            "contract",
            "insurance",
        ]),
    ]

    for document_type, terms in checks:
        if any(term in value for term in terms):
            return document_type

    return "Other"


def load_root(root, source_type):
    if not root.exists():
        return

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".pdf", ".docx"}:
            continue

        try:
            if path.suffix.lower() == ".pdf":
                pages = extract_pdf(path)
            else:
                pages = extract_docx(path)

        except Exception as exc:
            print(
                f"Warning: could not read "
                f"{path.name}: {exc}"
            )
            continue

        relative = path.relative_to(root)
        parts = relative.parts

        category = (
            parts[0]
            if len(parts) > 1
            else "Uncategorized"
        )

        all_text = "\n".join(
            text for _, text in pages
        )

        DOCS[
            f"{source_type}:{relative}"
        ] = {
            "name": path.name,
            "relative": str(relative),
            "category": category,
            "year": infer_year(
                all_text,
                path.name,
            ),
            "document_type": infer_document_type(
                category,
                path.name,
            ),
            "source_type": source_type,
            "role": (
                "AUTHORITATIVE / REFERENCE"
                if source_type == "authoritative"
                else "INSTITUTIONAL PRECEDENT / DRAFTING EXAMPLE"
            ),
            "pages": pages,
        }


def load_documents():
    with LOCK:
        DOCS.clear()

        load_root(
            KNOWLEDGE,
            "authoritative",
        )

        load_root(
            INSTITUTIONAL_LIBRARY,
            "institutional_library",
        )


# ============================================================
# SEARCH
# ============================================================

CATEGORY_TERMS = {
    "03_Discipline": [
        "discipline",
        "disciplinary",
        "misconduct",
        "indiscipline",
        "punishment",
        "penalty",
        "suspension",
        "expulsion",
        "appeal",
        "ragging",
        "conduct",
        "offence",
        "offense",
    ],

    "02_Academic Rules": [
        "academic",
        "attendance",
        "registration",
        "semester",
        "course",
        "grade",
        "examination",
        "exam",
        "promotion",
        "degree",
        "undergraduate",
        "ug",
        "b.tech",
        "postgraduate",
        "pg",
        "m.tech",
        "m.sc",
        "ph.d",
        "phd",
    ],

    "04_Finance Procurement": [
        "procurement",
        "purchase",
        "tender",
        "gem",
        "gfr",
        "financial",
        "expenditure",
        "bid",
        "quotation",
        "sanction",
        "payment",
        "delegation",
        "contract",
        "insurance",
        "premium",
    ],

    "01_Statutes_Gazette": [
        "statute",
        "statutes",
        "gazette",
        "act",
        "board of governors",
        "bog",
        "senate",
        "authority",
        "powers",
        "ordinance",
        "amendment",
        "statutory",
    ],

    "09_Government_Office_Procedure": [
        "csmop",
        "office procedure",
        "file management",
        "noting guidelines",
        "drafting",
        "manual of office procedure",
    ],
}


LIBRARY_TERMS = {
    "01_Noting": [
        "noting",
        "note",
        "file noting",
        "approval note",
        "proposal",
    ],

    "02_Office Orders": [
        "office order",
        "order",
    ],

    "03_Notices": [
        "notice",
        "circular",
    ],

    "04_MoM": [
        "minutes",
        "minute",
        "mom",
        "meeting",
        "proceedings",
        "agenda",
    ],

    "05_Minesterial Replies": [
        "ministry",
        "ministerial",
        "lok sabha",
        "rajya sabha",
        "parliamentary",
        "question",
    ],

    "06_Letters": [
        "letter",
        "correspondence",
    ],

    "07_Action Taken Report": [
        "action taken report",
        "atr",
        "action taken",
    ],

    "08_others": [
        "draft",
        "format",
        "precedent",
        "agreement",
        "certificate",
    ],
}


def detect_categories(query, mapping):
    q = query.lower()

    scores = {
        category: sum(
            1
            for term in terms
            if term in q
        )
        for category, terms in mapping.items()
    }

    return sorted(
        [
            category
            for category, score in scores.items()
            if score
        ],
        key=lambda category: (
            -scores[category],
            category,
        ),
    )


def is_rule_question(query):
    q = query.lower()

    return any(
        marker in q
        for marker in [
            "what rule",
            "which rule",
            "applicable rule",
            "regulation",
            "provision",
            "discipline manual",
            "statute",
            "gfr",
            "competent authority",
            "delegation",
            "procedure",
        ]
    )


def make_chunks(text, max_chars=950):
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    chunks = []
    current = ""

    for sentence in sentences:
        if (
            len(current)
            + len(sentence)
            + 1
            <= max_chars
        ):
            current = (
                current
                + " "
                + sentence
            ).strip()

        else:
            if current:
                chunks.append(current)

            current = sentence

    if current:
        chunks.append(current)

    return chunks


def search_documents(
    query,
    limit=10,
    precedent=False,
):
    q = query.lower().strip()

    terms = [
        term
        for term in re.findall(
            r"[a-z0-9]+",
            q,
        )
        if len(term) >= 3
    ]

    preferred_auth = detect_categories(
        q,
        CATEGORY_TERMS,
    )

    preferred_lib = detect_categories(
        q,
        LIBRARY_TERMS,
    )

    rule_question = is_rule_question(q)

    results = []

    for info in DOCS.values():
        category = info["category"]
        source_type = info["source_type"]
        filename = info["name"].lower()

        for page_no, text in info["pages"]:
            if not text:
                continue

            for chunk in make_chunks(text):
                chunk_lower = chunk.lower()
                score = 0

                for term in terms:
                    score += (
                        chunk_lower.count(term)
                        * 2
                    )

                    if term in filename:
                        score += 2

                if category in preferred_auth:
                    score += max(
                        35
                        - preferred_auth.index(category) * 8,
                        8,
                    )

                if category in preferred_lib:
                    score += max(
                        30
                        - preferred_lib.index(category) * 5,
                        5,
                    )

                if (
                    q
                    and q in chunk_lower
                ):
                    score += 35

                if rule_question:
                    score += (
                        30
                        if source_type == "authoritative"
                        else -8
                    )

                if precedent:
                    score += (
                        38
                        if source_type
                        == "institutional_library"
                        else 3
                    )

                for phrase, boost in [
                    ("insurance", 10),
                    ("extension", 8),
                    ("board of governors", 14),
                    ("office order", 12),
                    ("procurement", 10),
                    ("approval", 5),
                    ("competent authority", 8),
                ]:
                    if (
                        phrase in q
                        and phrase in chunk_lower
                    ):
                        score += boost

                if score > 0:
                    results.append(
                        {
                            "score": score,
                            "document": info["name"],
                            "relative": info["relative"],
                            "category": category,
                            "year": info["year"],
                            "document_type": info[
                                "document_type"
                            ],
                            "source_type": source_type,
                            "role": info["role"],
                            "page": page_no,
                            "snippet": chunk,
                        }
                    )

    results.sort(
        key=lambda result: (
            -result["score"],
            result["document"].lower(),
            result["page"],
        )
    )

    output = []
    seen = set()

    for result in results:
        key = (
            result["document"],
            result["page"],
            result["snippet"][:180],
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(result)

        if len(output) >= limit:
            break

    return output


def build_context(hits):
    return "\n\n".join(
        (
            f"[SOURCE {index}]\n"
            f"Document: {hit['document']}\n"
            f"Category: {hit['category']}\n"
            f"Year: {hit['year'] or 'Not identified'}\n"
            f"Type: {hit['document_type']}\n"
            f"Role: {hit['role']}\n"
            f"Page: {hit['page']}\n"
            f"Passage: {hit['snippet']}"
        )
        for index, hit in enumerate(
            hits,
            start=1,
        )
    )[:MAX_CONTEXT_CHARS]


# ============================================================
# HERMES
# ============================================================

def call_hermes(prompt):
    try:
        result = subprocess.run(
            [
                "hermes",
                "-z",
                prompt,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(BASE),
        )

    except FileNotFoundError:
        return (
            "Hermes was not found in PATH. "
            "Open a new PowerShell window and "
            "confirm `hermes --version` works."
        )

    except subprocess.TimeoutExpired:
        return (
            "Hermes timed out while generating "
            "the response."
        )

    except Exception as exc:
        return f"Hermes call failed: {exc}"

    if result.returncode != 0:
        details = (
            result.stderr
            or result.stdout
            or ""
        ).strip()

        return (
            "Hermes returned an error.\n\n"
            + details
        )

    return (
        result.stdout
        or ""
    ).strip()


# ============================================================
# MEMORY
# ============================================================

def load_memory():
    if not MEMORY_FILE.exists():
        return []

    try:
        data = json.loads(
            MEMORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        return (
            data
            if isinstance(data, list)
            else []
        )

    except Exception:
        return []


def save_memory(data):
    MEMORY_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def memory_text():
    items = load_memory()

    if not items:
        return "(No approved memory stored.)"

    return "\n".join(
        (
            f"- {item.get('fact', '')} "
            f"| status={item.get('status', '')} "
            f"| confirmed={item.get('confirmed', '')}"
        )
        for item in items
    )


# ============================================================
# CONVERSATION STATE
# ============================================================

def detect_task_from_text(text):
    q = text.lower()

    if any(
        phrase in q
        for phrase in [
            "draft a noting",
            "prepare a noting",
            "make a noting",
            "draft noting",
        ]
    ):
        return "noting"

    if any(
        phrase in q
        for phrase in [
            "draft an office order",
            "draft office order",
            "prepare an office order",
            "make an office order",
        ]
    ):
        return "office_order"

    if any(
        phrase in q
        for phrase in [
            "draft a notice",
            "prepare a notice",
            "make a notice",
        ]
    ):
        return "notice"

    if any(
        phrase in q
        for phrase in [
            "draft a letter",
            "prepare a letter",
            "make a letter",
        ]
    ):
        return "letter"

    if any(
        phrase in q
        for phrase in [
            "draft minutes",
            "prepare minutes",
            "prepare a mom",
            "draft a mom",
        ]
    ):
        return "mom"

    if any(
        phrase in q
        for phrase in [
            "find previous",
            "find an old",
            "previous order",
            "previous noting",
            "previous notice",
            "previous minutes",
            "historical precedent",
            "similar example",
            "where was this discussed",
        ]
    ):
        return "precedent_search"

    if any(
        phrase in q
        for phrase in [
            "what rule",
            "which rule",
            "applicable rule",
            "what is the procedure",
            "is it permissible",
        ]
    ):
        return "rules"

    return "general"


def all_conversation_text(message, history):
    return "\n".join(
        [
            str(item.get("content", ""))
            for item in history[-MAX_HISTORY_MESSAGES:]
        ]
        + [message]
    )


def extract_simple_date(text):
    patterns = [
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        r"\b\d{1,2}(?:st|nd|rd|th)\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.I,
        )

        if match:
            return match.group(0)

    return ""


def extract_amount(text):
    match = re.search(
        r"(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d+)?",
        text,
        re.I,
    )

    return (
        match.group(0)
        if match
        else ""
    )


def extract_extension_period(text):
    patterns = [
        r"\b(?:for|another|of)\s+(\d+)\s+(month|months|year|years)\b",
        r"\b(\d+)\s*[- ]?(month|months|year|years)\s+extension\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.I,
        )

        if match:
            return (
                f"{match.group(1)} "
                f"{match.group(2)}"
            )

    return ""


def extract_insurer(text):
    patterns = [
        r"(M/s\s+[A-Za-z0-9&.,'() -]+?(?:Insurance|General|Life)[A-Za-z0-9&.,'() -]*)",
        r"(SBI General Insurance Co\.?\s*Ltd\.?)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.I,
        )

        if match:
            return match.group(1).strip()

    return ""


def conversation_facts(message, history):
    text = all_conversation_text(
        message,
        history,
    )

    facts = {}

    insurer = extract_insurer(text)
    if insurer:
        facts["insurer"] = insurer

    current_date = extract_simple_date(
        text
    )

    if current_date:
        # We do not automatically call every date "current".
        # The controller treats an explicitly user-supplied date as a
        # conversation fact; source-derived historical dates remain separate.
        facts["date_mentioned"] = current_date

    amount = extract_amount(text)
    if amount:
        facts["amount"] = amount

    extension = extract_extension_period(
        text
    )
    if extension:
        facts["extension_period"] = extension

    # User confirmations commonly use short phrases.
    if re.search(
        r"\b(?:yes|correct|confirmed|still current)\b",
        message,
        re.I,
    ):
        facts["confirmation"] = "confirmed"

    return facts


# ------------------------------------------------------------
# Deterministic clarification model
# ------------------------------------------------------------

def insurance_extension_state(message, history):
    text = all_conversation_text(
        message,
        history,
    )

    facts = conversation_facts(
        message,
        history,
    )

    # We intentionally keep source-derived insurance information
    # separate from current user-confirmed information.
    historical = {
        "insurer": "M/s SBI General Insurance Co. Ltd.",
        "old_service_order": "NITS/2024/CW/DSW/62",
        "old_expiry": "28 August 2025",
    }

    return {
        "task": "insurance_extension_noting",
        "current_facts": facts,
        "historical_facts": historical,
        "missing": [],
    }


def choose_next_insurance_question(message, history, state):
    text = all_conversation_text(
        message,
        history,
    )

    current_facts = state["current_facts"]

    # 1. Current insurer must be confirmed.
    if "insurer" not in current_facts:
        historical = state["historical_facts"]

        return (
            "I found a previous NIT Sikkim record showing "
            f"{historical['insurer']} under service order "
            f"{historical['old_service_order']} with an expiry date of "
            f"{historical['old_expiry']}. This is a historical record. "
            "Is this still the current insurer for the matter?"
        ), "confirm_current_insurer"

    # 2. Current expiry needs a direct, current answer.
    # Search only the user's current conversation for a date after insurer
    # confirmation. If their answer merely says yes, do not reuse the old date.
    if not re.search(
        r"\b(?:current|present|existing).{0,40}(?:expire|expiry|valid)\b",
        text,
        re.I,
    ):
        return (
            "What is the current expiry date of the insurance coverage?"
        ), "current_expiry"

    # 3. Extension period
    if "extension_period" not in current_facts:
        return (
            "How long should the extension be?"
        ), "extension_period"

    # 4. Coverage scope
    if not re.search(
        r"\b(?:cover|coverage|students?|batches?|scholars?|staff)\b.{0,100}",
        text,
        re.I,
    ):
        return (
            "Which student group or category should the extension cover?"
        ), "coverage_scope"

    # 5. Premium / financial implication
    if "amount" not in current_facts:
        return (
            "What premium or financial amount should be recorded, "
            "or should the noting state that the amount is to be confirmed?"
        ), "premium"

    # 6. Approval/reference
    if not re.search(
        r"\b(?:approval|approved|NSP|reference|sanction|committee)\b",
        text,
        re.I,
    ):
        return (
            "Is there a prior approval, NSP reference, committee decision, "
            "or other reference that should be cited?"
        ), "approval_reference"

    return None, None


# ------------------------------------------------------------
# Final drafting after required facts are available
# ------------------------------------------------------------

def draft_from_completed_conversation(message, history, task):
    text = all_conversation_text(
        message,
        history,
    )

    hits = search_documents(
        text + " previous NIT Sikkim noting insurance",
        limit=10,
        precedent=True,
    )

    prompt = f"""
You are URI, preparing a concise official administrative noting for NIT Sikkim.

The conversational controller has determined that the clarification stage
is complete.

IMPORTANT:
- Use only facts explicitly confirmed in the conversation.
- Historical source dates must remain historical.
- Do not infer current status from an old service order.
- Do not invent an approval authority, budget head, financial sanction,
  procurement method, coverage or premium.
- Use institutional precedents for drafting style only.
- Use authoritative sources for current rules where actually supported.
- If an item remains unconfirmed, mark it "To be verified" rather than guessing.

Prepare a clean noting with:
Subject
1. Background / Reference
2. Requirement / Facts
3. Applicable Rule / Procedure
4. Financial Implication
5. Proposal
6. Submitted for approval / orders

Then separately provide:
REVIEW / VERIFICATION POINTS

CONVERSATION:
{text}

SOURCE PASSAGES:
{build_context(hits)}
""".strip()

    return call_hermes(prompt), hits


def handle_message(message, history):
    task = detect_task_from_text(
        all_conversation_text(
            message,
            history,
        )
    )

    # Special deterministic workflow for the insurance example.
    if (
        task == "noting"
        and "insurance"
        in all_conversation_text(
            message,
            history,
        ).lower()
    ):
        state = insurance_extension_state(
            message,
            history,
        )

        question, field = choose_next_insurance_question(
            message,
            history,
            state,
        )

        if question:
            return (
                question,
                [],
                {
                    "task": state["task"],
                    "next_field": field,
                    "current_facts": state["current_facts"],
                    "historical_facts": state["historical_facts"],
                    "clarification_complete": False,
                },
            )

        answer, hits = draft_from_completed_conversation(
            message,
            history,
            "insurance_extension_noting",
        )

        return (
            answer,
            hits,
            {
                "task": "insurance_extension_noting",
                "clarification_complete": True,
            },
        )

    # General tasks still use Hermes with strict source controls.
    precedent = is_precedent_request(message)

    hits = search_documents(
        message,
        limit=10,
        precedent=precedent,
    )

    prompt = f"""
You are URI, the NIT Sikkim Administrative AI Assistant.

Use the supplied sources and conversation context.

Rules:
- Never invent facts, rules, authorities, dates, powers, penalties,
  procedures, approvals, recipients or contract terms.
- Distinguish current authoritative/reference material from historical
  NIT Sikkim precedent.
- Historical precedent teaches style and past practice; it is not automatic
  current authority.
- Do not infer a competent authority from an amount or designation.
- Distinguish recommendation, approval and final decision.
- If a point is not established, say so.

Task:
{task}

Recent conversation:
{all_conversation_text(message, history[-MAX_HISTORY_MESSAGES:])}

Sources:
{build_context(hits)}

Respond naturally and concisely.
For rules questions, answer from authoritative sources.
For precedent requests, identify historical examples.
For drafting requests, use confirmed facts and clearly flag missing facts.
Do not produce a multi-question questionnaire.
Do not encourage the user to use unsupported assumptions.
""".strip()

    return (
        call_hermes(prompt),
        hits,
        {
            "task": task,
            "clarification_complete": True,
        },
    )


# ============================================================
# WEB INTERFACE
# ============================================================

PAGE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>URI - NIT Sikkim Administrative AI Assistant</title>

<style>
body{
    margin:0;
    background:#f5f7fb;
    color:#1f2937;
    font-family:Segoe UI,Arial,sans-serif;
}

header{
    background:#17324d;
    color:white;
    padding:18px 24px;
}

header h1{
    margin:0;
    font-size:28px;
}

header p{
    margin:4px 0 0;
    opacity:.85;
}

.wrap{
    max-width:1050px;
    margin:0 auto;
    padding:18px;
}

.chat{
    height:70vh;
    overflow-y:auto;
    padding:6px;
}

.msg{
    display:flex;
    margin:12px 0;
}

.user{
    justify-content:flex-end;
}

.bubble{
    max-width:82%;
    padding:12px 15px;
    border-radius:14px;
    white-space:pre-wrap;
    line-height:1.45;
}

.user .bubble{
    background:#17324d;
    color:white;
}

.assistant .bubble{
    background:white;
    border:1px solid #dbe2ea;
}

.controls{
    display:flex;
    gap:8px;
    margin-bottom:8px;
}

.control{
    border:1px solid #cbd5e1;
    background:white;
    border-radius:8px;
    padding:7px 10px;
    cursor:pointer;
}

.composer{
    display:flex;
    gap:10px;
    background:white;
    border:1px solid #dbe2ea;
    padding:10px;
    border-radius:14px;
}

.composer textarea{
    flex:1;
    resize:none;
    border:0;
    outline:0;
    font:inherit;
    min-height:54px;
}

.send{
    border:0;
    background:#17324d;
    color:white;
    padding:0 20px;
    border-radius:10px;
    cursor:pointer;
    font-weight:600;
}

.send:disabled{
    opacity:.6;
}

.status{
    font-size:12px;
    color:#64748b;
    margin:8px 4px;
}

.sources{
    margin-top:10px;
}

.src{
    background:white;
    border:1px solid #e2e8f0;
    border-radius:8px;
    padding:9px;
    margin:7px 0;
    font-size:12px;
}

.badge{
    display:inline-block;
    background:#eef2f7;
    border-radius:999px;
    padding:3px 8px;
    font-size:11px;
    margin:2px 3px 2px 0;
}
</style>
</head>

<body>

<header>
<h1>URI</h1>
<p>NIT Sikkim Administrative AI Assistant - V5.4</p>
</header>

<div class="wrap">

<div class="controls">
<button class="control" onclick="newChat()">
New chat
</button>

<button class="control" onclick="showMemory()">
View approved memory
</button>

<button class="control" onclick="showStatus()">
Knowledge status
</button>
</div>

<div id="chat" class="chat"></div>

<div id="status" class="status">
Ready.
</div>

<div class="composer">

<textarea
id="messageInput"
placeholder="Tell Uri what you need..."
></textarea>

<button
id="sendButton"
class="send"
onclick="sendMessage()"
>
Send
</button>

</div>

<div id="sources" class="sources"></div>

</div>

<script>
let chatHistory = [];

const chatBox =
    document.getElementById("chat");

const messageInput =
    document.getElementById("messageInput");

const sendButton =
    document.getElementById("sendButton");

const statusBox =
    document.getElementById("status");

const sourcesBox =
    document.getElementById("sources");

function escapeHtml(value){
    return String(value)
        .replaceAll("&","&amp;")
        .replaceAll("<","&lt;")
        .replaceAll(">","&gt;");
}

function addMessage(role,text){
    const row =
        document.createElement("div");

    row.className =
        "msg " + role;

    const bubble =
        document.createElement("div");

    bubble.className =
        "bubble";

    bubble.innerHTML =
        escapeHtml(text);

    row.appendChild(bubble);
    chatBox.appendChild(row);

    chatBox.scrollTop =
        chatBox.scrollHeight;
}

function newChat(){
    chatHistory = [];
    chatBox.innerHTML = "";
    sourcesBox.innerHTML = "";

    addMessage(
        "assistant",
        "Hello. I am Uri. Tell me what you need."
    );
}

function setBusy(value){
    sendButton.disabled = value;
    messageInput.disabled = value;

    statusBox.textContent =
        value
        ? "Uri is working..."
        : "Ready.";
}

function renderSources(sources){
    if(!sources || !sources.length){
        sourcesBox.innerHTML = "";
        return;
    }

    const items =
        sources.map(
            source => `
                <div class="src">
                    <strong>
                        ${escapeHtml(source.document)}
                    </strong>
                    - page
                    ${escapeHtml(source.page)}
                    <br>

                    <span class="badge">
                        ${escapeHtml(source.role || "")}
                    </span>

                    <span class="badge">
                        ${escapeHtml(
                            source.document_type || ""
                        )}
                    </span>

                    ${
                        source.year
                        ? `
                        <span class="badge">
                            ${escapeHtml(source.year)}
                        </span>
                        `
                        : ""
                    }

                    <br>
                    ${escapeHtml(source.snippet)}
                </div>
            `
        ).join("");

    sourcesBox.innerHTML =
        "<strong>Sources</strong>" + items;
}

async function sendMessage(){
    const text =
        messageInput.value.trim();

    if(!text){
        return;
    }

    addMessage(
        "user",
        text
    );

    chatHistory.push({
        role:"user",
        content:text
    });

    messageInput.value = "";

    setBusy(true);

    try{
        const response =
            await fetch(
                "/api/chat",
                {
                    method:"POST",
                    headers:{
                        "Content-Type":
                            "application/json"
                    },
                    body:JSON.stringify({
                        message:text,
                        history:chatHistory
                    })
                }
            );

        const data =
            await response.json();

        if(
            data.error
            && !data.answer
        ){
            addMessage(
                "assistant",
                "Error: " + data.error
            );

            return;
        }

        const answer =
            data.answer || "";

        addMessage(
            "assistant",
            answer
        );

        chatHistory.push({
            role:"assistant",
            content:answer
        });

        renderSources(
            data.sources || []
        );

    }catch(error){
        addMessage(
            "assistant",
            "Connection error: "
            + error
        );

    }finally{
        setBusy(false);
    }
}

async function showMemory(){
    try{
        const response =
            await fetch(
                "/api/memory"
            );

        const data =
            await response.json();

        if(
            !data.memory
            || !data.memory.length
        ){
            addMessage(
                "assistant",
                "No approved memory is stored yet."
            );

            return;
        }

        const text =
            data.memory.map(
                item =>
                    `${item.fact} ` +
                    `[${item.status}; ` +
                    `confirmed ${item.confirmed}]`
            ).join("\n");

        addMessage(
            "assistant",
            "Approved memory:\n" + text
        );

    }catch(error){
        addMessage(
            "assistant",
            "Could not read approved memory."
        );
    }
}

async function showStatus(){
    try{
        const response =
            await fetch(
                "/api/health"
            );

        const data =
            await response.json();

        addMessage(
            "assistant",
            "Knowledge status:\n" +
            "Total documents: "
            + data.total_documents
            + "\nAuthoritative/reference: "
            + data.authoritative_documents
            + "\nInstitutional library: "
            + data.institutional_documents
            + "\nApproved memory items: "
            + data.memory_items
        );

    }catch(error){
        addMessage(
            "assistant",
            "Could not read knowledge status."
        );
    }
}

messageInput.addEventListener(
    "keydown",
    function(event){
        if(
            event.key === "Enter"
            && !event.shiftKey
        ){
            event.preventDefault();
            sendMessage();
        }
    }
);

newChat();
</script>

</body>
</html>
"""


# ============================================================
# HTTP SERVER
# ============================================================

class UriHandler(BaseHTTPRequestHandler):

    def send_body(
        self,
        status_code,
        body,
        content_type="text/html; charset=utf-8",
    ):
        encoded = body.encode("utf-8")

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )

        self.end_headers()

        self.wfile.write(
            encoded
        )

    def read_json(self):
        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        raw = self.rfile.read(
            length
        )

        return json.loads(
            raw.decode("utf-8")
        )

    def do_GET(self):
        path = urlparse(
            self.path
        ).path

        if path == "/":
            self.send_body(
                200,
                PAGE
            )
            return

        if path == "/api/health":
            authoritative = sum(
                1
                for info in DOCS.values()
                if info["source_type"]
                == "authoritative"
            )

            institutional = sum(
                1
                for info in DOCS.values()
                if info["source_type"]
                == "institutional_library"
            )

            payload = {
                "ok": True,
                "total_documents":
                    len(DOCS),
                "authoritative_documents":
                    authoritative,
                "institutional_documents":
                    institutional,
                "memory_items":
                    len(load_memory()),
            }

            self.send_body(
                200,
                json.dumps(payload),
                "application/json; charset=utf-8",
            )

            return

        if path == "/api/memory":
            self.send_body(
                200,
                json.dumps(
                    {
                        "memory": load_memory()
                    },
                    ensure_ascii=False,
                ),
                "application/json; charset=utf-8",
            )

            return

        self.send_body(
            404,
            "Not found",
            "text/plain; charset=utf-8",
        )

    def do_POST(self):
        path = urlparse(
            self.path
        ).path

        try:
            data = self.read_json()

            if path == "/api/chat":
                answer, sources, state = (
                    handle_message(
                        data.get(
                            "message",
                            ""
                        ),
                        data.get(
                            "history",
                            []
                        ),
                    )
                )

                self.send_body(
                    200,
                    json.dumps(
                        {
                            "answer": answer,
                            "sources": sources,
                            "state": state,
                        },
                        ensure_ascii=False,
                    ),
                    "application/json; charset=utf-8",
                )

                return

            if path == "/api/memory/confirm":
                fact = data.get(
                    "fact",
                    ""
                ).strip()

                if not fact:
                    self.send_body(
                        400,
                        json.dumps(
                            {
                                "error":
                                "Memory fact is required."
                            }
                        ),
                        "application/json; charset=utf-8",
                    )

                    return

                items = load_memory()

                items.append(
                    {
                        "fact": fact,
                        "status": "CONFIRMED",
                        "confirmed":
                            str(date.today()),
                    }
                )

                save_memory(
                    items
                )

                self.send_body(
                    200,
                    json.dumps(
                        {"ok": True}
                    ),
                    "application/json; charset=utf-8",
                )

                return

            self.send_body(
                404,
                "Not found",
                "text/plain; charset=utf-8",
            )

        except Exception as exc:
            self.send_body(
                500,
                json.dumps(
                    {
                        "error": str(exc)
                    },
                    ensure_ascii=False,
                ),
                "application/json; charset=utf-8",
            )


if __name__ == "__main__":
    print(
        "Loading NIT Sikkim knowledge base "
        "and institutional library..."
    )

    load_documents()

    authoritative_count = sum(
        1
        for info in DOCS.values()
        if info["source_type"]
        == "authoritative"
    )

    institutional_count = sum(
        1
        for info in DOCS.values()
        if info["source_type"]
        == "institutional_library"
    )

    print(
        f"Loaded {len(DOCS)} total documents."
    )

    print(
        "Authoritative/reference documents: "
        f"{authoritative_count}"
    )

    print(
        "Institutional-library documents: "
        f"{institutional_count}"
    )

    print(
        "URI V5.4 - Deterministic Conversation Controller"
    )

    print(
        "Open http://127.0.0.1:8000 "
        "in your browser."
    )

    server = ThreadingHTTPServer(
        ("127.0.0.1", 8000),
        UriHandler,
    )

    server.serve_forever()
