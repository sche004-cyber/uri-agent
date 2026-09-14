# Multi-Action Capability Architecture — Implementer Report

## Scope and concurrency check

This delivery adds an isolated capability adapter package under `uri_core/capabilities/` plus `test_multi_action_capabilities.py`. It does not modify the current runtime registry, dispatcher, approval gate, server, Gmail service, Gmail search service, Gmail tool, or any `uri_ui/` file. Those protected files remain available for Claude's concurrent work. The new layer is therefore not wired into a production execution path until the runtime owner deliberately integrates it through the governing propose → validate → approve → execute chain.

## Architecture findings

- A top-level `Capability` owns a named collection of reusable `Action` instances. This preserves a small initial capability catalogue rather than exposing every action as a flat model-tool list.
- `ActionSchema` makes input validation deterministic and rejects unknown inputs by default. `MultiActionExecutor` applies capability permissions, availability/preconditions, user/admin approval, handler invocation, and a structured audit record in that order.
- Model-facing discovery ranks the registered capability/action descriptions and parameter affordances. It is intentionally a discovery aid rather than a phrase-to-intent switchboard or execution authority.
- The chain engine resolves explicit references from a prior structured result (for example `$search.result.messages[0].message_id`) and halts immediately on an unavailable, invalid, denied, or approval-pending action.
- `CapabilityContextResolver` stores only identifiers and metadata returned by prior Gmail actions. It resolves follow-ups only from that grounded state; it never makes up message, thread, or attachment identifiers.

## Gmail reference capability

`GmailCapability` is constructed with an existing `GmailService` instance. It starts no OAuth flow and adds no sending capability. It exposes:

- `list_labels`, including Gmail's reported total/unread counts;
- `search_messages`, via `GmailService.search_evidence`;
- `read_message`, `read_thread`, and `read_attachment`, preferring documented Gmail service primitives and using the service's already-authenticated API client only where the adapter must retrieve metadata;
- `create_draft`, which is user-approval-gated and creates a draft only;
- `apply_label` and `archive_message`, fully registered and approval-gated but deliberately returning `unsupported` because `gmail.modify` is not granted.

No Gmail OAuth, token, scope, or send logic is duplicated or altered. In particular, `uri_core/services/gmail_service.py` is intentionally untouched.

## Compatibility impact

`LegacyCapabilityAdapter` projects a legacy one-tool descriptor into a single-action capability without mutating the legacy descriptor or replacing the existing capability registry. This permits incremental migration and keeps existing callers stable until an approved runtime integration occurs.

## Files created

- `uri_core/capabilities/__init__.py`
- `uri_core/capabilities/base.py`
- `uri_core/capabilities/registry.py`
- `uri_core/capabilities/executor.py`
- `uri_core/capabilities/discovery.py`
- `uri_core/capabilities/context_resolver.py`
- `uri_core/capabilities/gmail/__init__.py`
- `uri_core/capabilities/gmail/capability.py`
- `test_multi_action_capabilities.py`

## Verification performed

`& .\\.venv\\Scripts\\python.exe -m pytest -q test_multi_action_capabilities.py`

Result: **10 passed**.

Existing Gmail regression check:

`& .\\.venv\\Scripts\\python.exe -m pytest -q test_gmail_search_service.py test_m19_office_readiness.py`

Result: **38 passed**.

`& .\\.venv\\Scripts\\python.exe -m compileall -q uri_core/capabilities`

Result: completed successfully.

`git diff --check -- uri_core/capabilities test_multi_action_capabilities.py`

Result: no whitespace errors.

The focused tests cover progressive discovery, unread-count discovery through registered action wording (not an unread-count intent table), single actions, search → message → attachment → draft chaining, approvals, permissions, disconnection, schema failures, conversational continuity, legacy adaptation, and the absence of a new Gmail sending surface.

## Natural-language examples exercised

- “How many unread emails do I have?” discovers Gmail's `list_labels` action through its `unread email message counts` affordance.
- “Find the latest insurance email, check the attachment, and prepare a reply” discovers Gmail search, attachment, and draft actions through their registered descriptions.
- “Read that one”, “Check its attachment”, and “Prepare a reply” resolve only from the prior search result's message, attachment, sender, subject, and thread metadata.

## Recommended next migration

Google Drive is the natural next capability: it has a coherent resource model (search/list, read metadata/content, download, and explicitly approval-gated write actions) and can reuse this same action/executor boundary without changing the authority model.
