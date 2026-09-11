"""Composes a document body by asking the Brain to write it (M17).

This is the piece that makes URI's drafting genuinely Brain-centric.
The old tools emitted a finished body from Python (a hardcoded order
f-string; a fixed section-builder for notings). Here, the actual
document is authored by the same reasoning model ("the Brain") the rest
of the codebase already calls through ModelProvider - given the
drafting brief (rules, conventions, suggested-not-mandatory structure),
the request, the evidence, and the user's preferences - and URI's only
jobs are to hand that guidance over faithfully, validate the model's
words (document_validation.py), and, if the model is unreachable or its
draft fails validation, fall back to a plain, honest, purpose-neutral
rendering that is explicitly NOT an institutional template.

There is exactly one drafting path in URI after M17: this one. The
narrative path in response_drafting.py is a different concern (it
explains an outcome, it does not author documents) and is untouched.
"""

import json
import re
from typing import Any, Dict, Optional

from uri_core.core.document_validation import validate_drafted_document
from uri_core.core.model_providers import ModelProvider, ProviderError
from uri_core.config.model_roles import (
    ROLE_DOCUMENT_COMPOSITION,
    UnknownModelProviderError,
    build_provider,
)
from uri_core.core.model_router import get_router


# Strips a leading drafting instruction so the remainder is the subject
# matter, used ONLY by the deterministic fallback (the Brain gets the
# raw request and needs no such stripping). Mirrors the intent of the
# old note tool's extractor without any of its template behaviour.
_LEADING_COMMAND_RE = re.compile(
    r"^\s*(?:please\s+)?(?:draft|prepare|write|create|generate|issue|make)\s+"
    r"(?:a|an|the)?\s*(?:office\s+)?(?:noting|note|order|office\s+order|"
    r"notice|letter|document)s?\s*"
    r"(?:regarding|about|for|on|concerning|to)?\s*",
    re.IGNORECASE,
)


def _fallback_subject(request_text: str) -> str:
    text = (request_text or "").strip()
    if not text:
        return "Administrative Matter"
    stripped = _LEADING_COMMAND_RE.sub("", text).strip().rstrip(".")
    subject = stripped or text
    if not subject:
        return "Administrative Matter"
    return subject[0].upper() + subject[1:]


class DocumentComposer:
    """Brain-backed document authoring. Provider is injectable so tests
    can drive it with a fake; the default resolves via the process-wide
    ModelRouter on every call (M22.6 per-call resolution — §0.1)."""

    def __init__(
        self,
        provider: Optional[ModelProvider] = None,
        principal: Optional[object] = None,
    ) -> None:
        self._provider = provider
        self._principal = principal

    def _get_provider(self) -> ModelProvider:
        """Backward-compatible inspection method for existing tests.
        Returns explicit provider or builds default via role factory."""
        if self._provider is not None:
            return self._provider
        return build_provider(ROLE_DOCUMENT_COMPOSITION)

    def compose(
        self,
        *,
        brief: Dict[str, Any],
        request_text: str,
        evidence: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None,
        soul_text: str = "",
        principal: Optional[object] = None,
    ) -> Dict[str, Any]:
        """Returns {"status", "body", "composed_by", "detail"}.
        composed_by is "brain" when the model authored an accepted draft,
        "fallback" when URI used its plain rendering instead. status is
        always "success" (a document is always produced); detail explains
        a fallback."""

        system_prompt = self._build_system_prompt(brief, soul_text)
        user_prompt = self._build_user_prompt(
            brief=brief,
            request_text=request_text,
            evidence=evidence or brief.get("evidence") or {},
            preferences=preferences or brief.get("user_preferences") or {},
        )

        effective_principal = principal if principal is not None else self._principal

        try:
            complete_kwargs = dict(
                system=system_prompt,
                user=user_prompt,
                temperature=0.2,
            )
            if self._provider is not None:
                # Explicit provider injected (test path) — bypass router.
                response = self._provider.complete(**complete_kwargs)
            else:
                # M22.6: per-call router resolution.
                response = get_router().attempt(
                    ROLE_DOCUMENT_COMPOSITION,
                    effective_principal,
                    **complete_kwargs,
                )
            body = (response.content or "").strip()
            verdict = validate_drafted_document(body, brief)

            if verdict["valid"]:
                return {
                    "status": "success",
                    "body": body,
                    "composed_by": "brain",
                    "detail": None,
                }

            return {
                "status": "success",
                "body": self._fallback_document(brief, request_text),
                "composed_by": "fallback",
                "detail": (
                    "The Brain's draft did not pass document validation "
                    f"({verdict['reason']}); a plain draft was produced "
                    "instead."
                ),
            }

        except (ProviderError, UnknownModelProviderError) as error:
            return {
                "status": "success",
                "body": self._fallback_document(brief, request_text),
                "composed_by": "fallback",
                "detail": (
                    "The reasoning model was unreachable, so URI produced "
                    f"a plain draft to work from ({error})."
                ),
            }

    # -----------------------------------------------------------------
    # Prompt construction
    # -----------------------------------------------------------------

    def _build_system_prompt(self, brief: Dict[str, Any], soul_text: str) -> str:
        institutional = json.dumps(brief.get("institutional_rules", {}), indent=2)
        suggested = brief.get("suggested_sections", [])
        suggested_text = "\n".join(f"  - {section}" for section in suggested)
        policy_rules = brief.get("policy_rules", "").strip()

        parts = []

        if soul_text.strip():
            parts.append(soul_text.strip())

        parts.append(
            "You are composing a real institutional document on behalf of "
            "URI. Write the DOCUMENT ITSELF - not an explanation of it, not "
            "a chat reply about it. Do not open with 'Sure', 'Here is', 'I "
            "have drafted', or any assistant preamble; output only the "
            "document text."
        )

        if policy_rules:
            parts.append(
                "The institution's drafting and review rules (authoritative "
                "- follow them):\n" + policy_rules
            )

        parts.append(
            "Institutional conventions to observe (these are data about the "
            "institution - apply them, and never substitute a different "
            "institution's names, offices, or formats):\n" + institutional
        )

        parts.append(
            "Document kind: "
            f"{brief.get('document_type', 'noting')}. "
            f"Purpose: {brief.get('purpose', 'general')}. "
            f"Urgent: {brief.get('is_urgent', False)}. "
            f"Tone: {brief.get('tone', 'formal_administrative')}."
        )

        # M19 (generate_document.py): only set for a generic generated
        # file, never for a note/order draft - additive, so existing
        # drafting behaviour is completely unchanged when absent.
        output_format = brief.get("output_format")
        if output_format == "xlsx":
            parts.append(
                "Output shape: this will be rendered into a real Excel "
                "spreadsheet. Express the data as ONE markdown table: a "
                "header row, then a '|---|---|...' separator row, then one "
                "data row per line, using '|' to separate cells - exactly "
                "like GitHub-flavoured markdown tables. Do not include any "
                "prose outside the table."
            )
        elif output_format == "pptx":
            parts.append(
                "Output shape: this will be rendered into a real "
                "PowerPoint presentation. Structure it as one '# Slide "
                "Title' markdown heading per slide, followed by that "
                "slide's bullet points as '- point' lines. Keep each "
                "bullet short (one line)."
            )

        if suggested_text:
            parts.append(
                "Suggested elements you MAY use, drawn from institutional "
                "convention and the document's purpose. These are a starting "
                "point to ADAPT to this specific request - not a mandatory "
                "checklist, not a fixed order. Add, omit, reorder, rename, or "
                "restructure as the request and purpose actually require; a "
                "cancellation, an appointment, a recommendation and an "
                "approval should each be structured differently:\n"
                + suggested_text
            )

        parts.append(
            "Factual discipline: use ONLY the facts given to you below. Do "
            "not invent authorities, reference numbers, dates, names, "
            "figures, or precedents. Where a reference number or date is "
            "conventionally required but not supplied, leave a clear "
            "placeholder (e.g. 'No. ____' or 'Dated: ____') rather than "
            "inventing one."
        )

        return "\n\n".join(parts)

    def _build_user_prompt(
        self,
        *,
        brief: Dict[str, Any],
        request_text: str,
        evidence: Dict[str, Any],
        preferences: Dict[str, Any],
    ) -> str:
        payload = {
            "request": request_text,
            "purpose": brief.get("purpose", "general"),
            "document_type": brief.get("document_type", "noting"),
            "is_urgent": brief.get("is_urgent", False),
            "evidence": evidence,
            "user_preferences": preferences,
            "writing_preferences": brief.get("writing_preferences", {}),
        }
        return (
            "Compose the document for this request. The JSON below is your "
            "only source of facts and preferences:\n\n"
            + json.dumps(payload, indent=2, default=str)
            + "\n\nOutput only the finished document text."
        )

    # -----------------------------------------------------------------
    # Deterministic fallback
    # -----------------------------------------------------------------

    def _fallback_document(self, brief: Dict[str, Any], request_text: str) -> str:
        """A plain, honest, purpose-neutral rendering used ONLY when the
        Brain could not produce an accepted draft. Deliberately NOT an
        institutional template: it carries no fixed institution banner,
        no invented reference number, no fabricated signatory - just the
        real subject and the real request content, so a human always has
        a truthful starting point rather than a confidently-wrong
        template. It echoes the request (which is where any stated
        justification lives) and never adds a reason that was not
        stated."""

        subject = _fallback_subject(request_text)
        purpose = brief.get("purpose", "general")
        doc_type = brief.get("document_type", "noting")

        lines = [
            f"DRAFT ({doc_type.replace('_', ' ').upper()})",
            "",
            f"Subject: {subject}",
        ]

        if purpose and purpose != "general":
            lines.append(f"Purpose: {purpose}")

        request_body = (request_text or "").strip()
        if request_body:
            lines.append("")
            lines.append(request_body)

        lines.append("")
        lines.append(
            "[This is an unpolished draft prepared without the reasoning "
            "model; review and complete before use.]"
        )

        return "\n".join(lines)
