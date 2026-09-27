"""Provider-neutral renderer port and adapters (Plan A §12.5, §5).

Every adapter receives only the slot-keyed `RenderRequest` (no candidate IDs,
no RAR internals, no history) and returns raw text. Validation, fallback and
option order stay with URI. No model-specific logic lives outside adapters.

The LM Studio adapter uses provider-native constrained decoding
(`response_format: json_schema`, enforced by llama.cpp grammar sampling for
GGUF) and never triggers a JIT cold load unless the caller allows it: it reads
the model's load state first and refuses to call a model that is not loaded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Callable, Optional, Protocol, Tuple
import urllib.error
import urllib.request

from uri_v1.reference_clarification.render_contracts import RenderRequest
from uri_v1.reference_clarification.render_validator import _ALLOW
from uri_v1.reference_clarification.template_renderer import render_template
from uri_v1.turn.rar_clarification_contract import ClarificationContract, ClarificationKind

# v1 (exploratory round 1) told CHOOSE_ATTRIBUTE rounds to "ask which value of
# the axis matches"; models echoed the words "value of the axis" and "user".
# v2 names the real axis, addresses the reader as "you", and forbids slot keys.
# v3: identical wording to v2; the allowlist note now lists the S1-A1 widened
# validator allowlist (it is generated from the validator itself).
PROMPT_VERSION = "m33.3-r.s5.prompt.v3"

SYSTEM_PROMPT = (
    "You word one short clarification question, addressed to the reader as \"you\". Use only the facts given. "
    "Return JSON with \"question\" and \"labels\". \"labels\" has exactly one short label for each slot key "
    "given, with the same keys; each label must name what makes that option different from the others. "
    "Do not add, remove, merge, or rank options. Do not choose for the reader or say which one is likely. "
    "Do not mention slot keys or anything that is not in the facts or the reference."
)
ALLOWLIST_NOTE = ("Use only words that appear in the facts or the reference, plus these words: "
                  + ", ".join(sorted(_ALLOW)) + ".")
_KIND_HINT = {
    ClarificationKind.CHOOSE_ONE: "Ask which option you mean.",
    ClarificationKind.CONFIRM_ONE: "Ask whether this single option is the one you mean.",
    ClarificationKind.CHOOSE_ATTRIBUTE: "Ask which value of the axis matches; each slot is an attribute value.",
    ClarificationKind.FREE_INPUT_ONLY: "Nothing matched. Ask what you mean. labels must be an empty object.",
}


@dataclass(frozen=True)
class RenderAttempt:
    arm: str
    raw_text: Optional[str]
    latency_ms: float
    invoked_model: Optional[str] = None
    error: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    model_state_before: Optional[str] = None
    model_state_after: Optional[str] = None
    decoding: Optional[str] = None
    prompt_variant: Optional[str] = None

    @property
    def cold_load_observed(self) -> bool:
        return self.model_state_before not in (None, "loaded") and self.model_state_after == "loaded"


class RendererPort(Protocol):
    arm: str

    def render(self, request: RenderRequest, contract: ClarificationContract) -> RenderAttempt: ...


def request_payload(request: RenderRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": request.kind.value, "reference": request.reference,
                               "slots": {key: dict(facts) for key, facts in request.slots}}
    if request.overflow:
        payload["overflow"] = request.overflow
    if request.axis:
        payload["axis"] = request.axis
    return payload


def output_schema(request: RenderRequest) -> dict[str, Any]:
    keys = [key for key, _ in request.slots]
    return {"type": "object", "additionalProperties": False, "required": ["question", "labels"],
            "properties": {
                "question": {"type": "string", "maxLength": 300},
                "labels": {"type": "object", "additionalProperties": False, "required": keys,
                           "properties": {k: {"type": "string", "maxLength": 180} for k in keys}}}}


def build_prompt(request: RenderRequest, *, allowlist: bool) -> Tuple[str, str]:
    system = SYSTEM_PROMPT + (" " + ALLOWLIST_NOTE if allowlist else "")
    hint = (f"Ask which {request.axis} you mean; each slot is one {request.axis}."
            if request.kind == ClarificationKind.CHOOSE_ATTRIBUTE and request.axis else _KIND_HINT[request.kind])
    user = hint + "\n" + json.dumps(request_payload(request), ensure_ascii=False, sort_keys=True)
    return system, user


class TemplateRenderer:
    arm = "template"

    def render(self, request: RenderRequest, contract: ClarificationContract) -> RenderAttempt:
        start = time.perf_counter()
        output = render_template(contract)
        text = json.dumps({"question": output.question, "labels": dict(output.labels)}, ensure_ascii=False)
        return RenderAttempt(self.arm, text, (time.perf_counter() - start) * 1000.0)


@dataclass
class LMStudioRenderer:
    """Local LM Studio adapter over its OpenAI-compatible completions endpoint."""
    arm: str
    model_id: str
    base_url: str = "http://127.0.0.1:1234"
    constrained: bool = True
    allowlist_prompt: bool = False
    allow_cold_load: bool = False
    timeout_s: float = 60.0
    max_tokens: int = 400
    opener: Callable[..., Any] = field(default=urllib.request.urlopen, repr=False)

    def model_state(self) -> Optional[str]:
        try:
            with self.opener(f"{self.base_url}/api/v0/models/{self.model_id}", timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8")).get("state")
        except Exception:
            return None

    def render(self, request: RenderRequest, contract: ClarificationContract) -> RenderAttempt:
        decoding = "constrained" if self.constrained else "unconstrained"
        variant = "allowlist" if self.allowlist_prompt else "natural"
        before = self.model_state()
        if before != "loaded" and not self.allow_cold_load:
            return RenderAttempt(self.arm, None, 0.0, None, "model_not_warm_no_cold_load",
                                 model_state_before=before, model_state_after=before,
                                 decoding=decoding, prompt_variant=variant)
        system, user = build_prompt(request, allowlist=self.allowlist_prompt)
        prompt = (f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n"
                  f"<|im_start|>assistant\n<think>\n</think>\n")
        payload: dict[str, Any] = {"model": self.model_id, "prompt": prompt, "temperature": 0.0,
                                   "max_tokens": self.max_tokens, "stop": ["<|im_end|>"]}
        if self.constrained:
            payload["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "clarification_render", "strict": True, "schema": output_schema(request)}}
        req = urllib.request.Request(f"{self.base_url}/v1/completions", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        start = time.perf_counter()
        try:
            with self.opener(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            latency = (time.perf_counter() - start) * 1000.0
            return RenderAttempt(self.arm, None, latency, self.model_id, f"provider_error:{type(exc).__name__}",
                                 model_state_before=before, model_state_after=self.model_state(),
                                 decoding=decoding, prompt_variant=variant)
        latency = (time.perf_counter() - start) * 1000.0
        usage = body.get("usage") or {}
        text = (body.get("choices") or [{}])[0].get("text") or ""  # untruncated, unmodified
        return RenderAttempt(self.arm, text, latency, self.model_id, None, usage.get("prompt_tokens"),
                             usage.get("completion_tokens"), before, self.model_state(), decoding, variant)
