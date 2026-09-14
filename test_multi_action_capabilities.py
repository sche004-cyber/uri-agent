from __future__ import annotations

from typing import Any

import pytest

from uri_core.capabilities import (
    Action,
    ActionSchema,
    ApprovalRequirement,
    Capability,
    LegacyCapabilityAdapter,
    MultiActionCapabilityRegistry,
    MultiActionExecutor,
    RiskLevel,
)
from uri_core.capabilities.context_resolver import CapabilityContextResolver
from uri_core.capabilities.discovery import CapabilityDiscoveryEngine
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.state import SessionManager


class FakeGmailService:
    """Contract fake: every method is an existing GmailService primitive or
    the documented optional convenience primitive the adapter prefers."""

    def __init__(self, connected=True):
        self.service = object() if connected else None
        self.drafts = []

    def get_connection_status(self):
        return {"connected": self.service is not None}

    def search_evidence(self, queries):
        return {
            "success": True,
            "results": [{
                "query": queries[0],
                "messages": [{
                    "message_id": "m-1",
                    "thread_id": "t-1",
                    "subject": "Insurance renewal",
                    "from": "agent@example.test",
                    "date": "2026-09-12",
                    "snippet": "Please see the attached policy.",
                    "attachments": [{"filename": "policy.pdf", "attachment_id": "a-1", "mime_type": "application/pdf"}],
                }],
            }],
        }

    def get_message_metadata(self, message_id):
        return {
            "success": True,
            "message": {
                "message_id": message_id,
                "thread_id": "t-1",
                "subject": "Insurance renewal",
                "from": "agent@example.test",
                "body": "Policy attached.",
                "attachments": [{"filename": "policy.pdf", "attachment_id": "a-1", "message_id": message_id}],
            },
        }

    def get_thread(self, thread_id):
        return {"success": True, "thread_id": thread_id, "messages": [self.get_message_metadata("m-1")["message"]]}

    def build_attachment_inventory(self, message_id):
        return [{"filename": "policy.pdf", "attachment_id": "a-1", "message_id": message_id}]

    def download_attachment(self, message_id, attachment_id, filename):
        return {"success": True, "message_id": message_id, "attachment_id": attachment_id, "filename": filename, "file_path": "temp_evidence/policy.pdf", "temporary": True}

    def create_draft(self, to, subject, body):
        self.drafts.append({"to": to, "subject": subject, "body": body})
        return {"success": True, "draft_id": "d-1"}


class _Execute:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class _LabelResource:
    def list(self, **_):
        return _Execute({"labels": [{"id": "INBOX", "name": "INBOX"}, {"id": "UNREAD", "name": "UNREAD"}]})

    def get(self, *, id, **_):
        counts = {"INBOX": (20, 3), "UNREAD": (3, 3)}[id]
        return _Execute({"id": id, "name": id, "messagesTotal": counts[0], "messagesUnread": counts[1]})


class _LabelClient:
    def users(self):
        return self

    def labels(self):
        return _LabelResource()


def gmail_registry(service=None):
    return MultiActionCapabilityRegistry([GmailCapability(service or FakeGmailService())])


def test_progressive_discovery_keeps_action_schemas_out_of_initial_summary():
    registry = gmail_registry()
    summary = registry.capability_summaries()
    assert summary == [{
        "name": "Gmail",
        "description": summary[0]["description"],
        "category": "communication",
        "preconditions": ["gmail_connected"],
        "actions": ["list_labels", "search_messages", "read_message", "read_thread", "read_attachment", "create_draft", "apply_label", "archive_message"],
    }]
    assert "parameters" not in summary[0]
    detail = registry.describe_capability("Gmail")
    assert detail and detail["actions"][0]["parameters"] == {}
    assert {action["name"] for action in detail["actions"]} >= {"search_messages", "create_draft"}


def test_discovery_uses_registered_affordances_not_a_unread_intent_table():
    discovery = CapabilityDiscoveryEngine(gmail_registry())
    found = discovery.discover("How many unread emails do I have?")
    gmail = next(item for item in found["capabilities"] if item["capability"] == "Gmail")
    assert gmail["matched_affordances"]
    assert gmail["actions"][0]["action"] == "list_labels"
    assert "unread" in gmail["actions"][0]["matched_affordances"]
    actions = discovery.discover_actions("Gmail", "Find the latest insurance email, check the attachment, and prepare a reply")
    assert {item["action"] for item in actions} >= {"search_messages", "read_attachment", "create_draft"}


def test_single_action_execution_and_audit():
    executor = MultiActionExecutor(gmail_registry(), granted_permissions={"gmail.readonly"})
    result = executor.execute("Gmail", "search_messages", {"query": "from:agent@example.test"})
    assert result["status"] == "success"
    assert result["result"]["messages"][0]["message_id"] == "m-1"
    assert executor.audit_log[-1]["action"] == "search_messages"


def test_list_labels_reads_gmail_reported_unread_counts():
    service = FakeGmailService()
    service.service = _LabelClient()
    executor = MultiActionExecutor(gmail_registry(service), granted_permissions={"gmail.readonly"})
    result = executor.execute("Gmail", "list_labels", {})
    assert result["status"] == "success"
    assert result["result"]["labels"] == [
        {"id": "INBOX", "name": "INBOX", "messages_total": 20, "messages_unread": 3, "threads_total": 0, "threads_unread": 0},
        {"id": "UNREAD", "name": "UNREAD", "messages_total": 3, "messages_unread": 3, "threads_total": 0, "threads_unread": 0},
    ]


def test_chain_search_read_attachment_and_user_approved_draft():
    service = FakeGmailService()
    executor = MultiActionExecutor(gmail_registry(service), granted_permissions={"gmail.readonly"})
    result = executor.execute_chain([
        {"id": "search", "capability": "Gmail", "action": "search_messages", "inputs": {"query": "insurance"}},
        {"id": "read", "capability": "Gmail", "action": "read_message", "inputs": {"message_id": {"$from": "search.result.messages[0].message_id"}}},
        {"id": "attachment", "capability": "Gmail", "action": "read_attachment", "inputs": {
            "message_id": {"$from": "read.result.message.message_id"},
            "attachment_id": {"$from": "read.result.message.attachments[0].attachment_id"},
            "filename": {"$from": "read.result.message.attachments[0].filename"},
        }},
        {"id": "draft", "capability": "Gmail", "action": "create_draft", "inputs": {"to": "agent@example.test", "subject": "Re: Insurance renewal", "body": "Thank you."}},
    ], user_approved=True)
    assert result["status"] == "success"
    assert result["steps"]["attachment"]["result"]["file_path"] == "temp_evidence/policy.pdf"
    assert service.drafts == [{"to": "agent@example.test", "subject": "Re: Insurance renewal", "body": "Thank you."}]


def test_mutating_actions_halt_pending_approval_and_never_send():
    service = FakeGmailService()
    executor = MultiActionExecutor(gmail_registry(service), granted_permissions={"gmail.readonly"})
    pending = executor.execute("Gmail", "create_draft", {"to": "x@example.test", "subject": "s", "body": "b"})
    assert pending["status"] == "approval_required"
    assert service.drafts == []
    unsupported = executor.execute("Gmail", "archive_message", {"message_id": "m-1"}, user_approved=True)
    assert unsupported["status"] == "unsupported"
    assert "gmail.modify OAuth scope" in unsupported["result"]["message"]


def test_permission_disconnected_and_schema_enforcement():
    no_permission = MultiActionExecutor(gmail_registry(), granted_permissions=set())
    denied = no_permission.execute("Gmail", "search_messages", {"query": "test"})
    assert denied["status"] == "permission_denied"
    invalid = MultiActionExecutor(gmail_registry(), granted_permissions={"gmail.readonly"}).execute("Gmail", "read_message", {})
    assert invalid["status"] == "invalid_input"
    disconnected = MultiActionExecutor(gmail_registry(FakeGmailService(connected=False)), granted_permissions={"gmail.readonly"}).execute("Gmail", "search_messages", {"query": "test"})
    assert disconnected["status"] == "unavailable"
    assert disconnected["availability"]["missing_preconditions"] == ["gmail_connected"]


def test_context_resolves_grounded_conversational_followups():
    resolver = CapabilityContextResolver()
    resolver.record_action_result("Gmail", "search_messages", FakeGmailService().search_evidence(["insurance"]))
    assert resolver.resolve("read_message", "Read that one") == {"message_id": "m-1"}
    assert resolver.resolve("read_attachment", "Check its attachment") == {
        "message_id": "m-1", "attachment_id": "a-1", "filename": "policy.pdf"
    }
    reply = resolver.resolve("create_draft", "Prepare a reply")
    assert reply["reply_to"] == "agent@example.test"
    assert reply["in_reply_to_thread_id"] == "t-1"


def test_legacy_adapter_bridges_old_registry_descriptor_without_mutating_it():
    legacy = {"id": "gmail_search", "description": "Search old Gmail tool", "permissions": ["gmail.readonly"], "approval_requirement": "none", "risk": "low", "interface": {"parameters": {"query": {"type": "string", "required": True}}}}
    capability = LegacyCapabilityAdapter.from_descriptor(legacy, handler=lambda query: {"status": "success", "query": query})
    registry = MultiActionCapabilityRegistry([capability])
    result = MultiActionExecutor(registry, granted_permissions={"gmail.readonly"}).execute("gmail_search", "gmail_search", {"query": "hello"})
    assert result["status"] == "success"
    assert legacy["interface"]["parameters"]["query"]["required"] is True


def test_gmail_adapter_reuses_service_and_does_not_add_sending_surface():
    service = FakeGmailService()
    capability = GmailCapability(service)
    assert capability.gmail_service is service
    assert not hasattr(capability, "send_message")
    assert not hasattr(service, "send_message")
    assert GmailCapability.__module__.startswith("uri_core.capabilities.gmail")


class _FixedSemanticInterpreter:
    def interpret(self, _user_text):
        return {
            "goal": "gmail request", "task_type": "request", "domain": "communication",
            "entities": [], "requested_output": "", "requires_evidence": False,
            "requires_clarification": False, "suggested_next_step": "",
        }


class _ScriptedGateway:
    """Returns an untrusted, separately namespaced M27 proposal."""
    def __init__(self, proposals):
        self.proposals = iter(proposals)
        self.contexts = []

    def load_policy(self):
        return ""

    def reason(self, **kwargs):
        self.contexts.append(kwargs["query_context"]["multi_action_capabilities"])
        return {"status": "proposal_ready", "proposal": next(self.proposals)}


def test_orchestrator_live_multi_action_progression_and_grounded_followups(tmp_path):
    service = FakeGmailService()
    dispatch = MultiActionDispatch(
        gmail_registry(service), granted_permissions={"gmail.readonly"}
    )
    gateway = _ScriptedGateway([
        {"selected_capability": "Gmail"},
        {"multi_action": {"capability": "Gmail", "action": "search_messages", "inputs": {"query": "insurance"}}},
        {"multi_action": {"capability": "Gmail", "action": "read_message", "inputs": {}}},
        {"multi_action": {"capability": "Gmail", "action": "read_attachment", "inputs": {}}},
        {"multi_action": {"capability": "Gmail", "action": "create_draft", "inputs": {"body": "Thank you."}}},
    ])
    orchestrator = UriOrchestrator(
        model_reasoning_gateway=gateway,
        semantic_interpreter=_FixedSemanticInterpreter(),
        session_manager=SessionManager(str(tmp_path / "sessions")),
        multi_action_dispatch=dispatch,
        enable_skill_router_shadow=False,
    )

    selection = orchestrator.process_user_input("gmail-session", "Find the insurance email")
    assert selection["execution"]["status"] == "discovery_ready"
    assert gateway.contexts[0]["stage"] == "capability_summaries"
    assert "parameters" not in gateway.contexts[0]["capabilities"][0]

    search = orchestrator.process_user_input("gmail-session", "Search Gmail for insurance")
    assert search["execution"] == {
        "status": "success", "capability": "Gmail", "action": "search_messages", "raw_status": "success"
    }
    assert gateway.contexts[1]["stage"] == "capability_detail"
    assert gateway.contexts[1]["capability"]["actions"][0]["parameters"] == {}

    read = orchestrator.process_user_input("gmail-session", "Read that one")
    assert read["response"]["message"]["message_id"] == "m-1"

    attachment = orchestrator.process_user_input("gmail-session", "Check its attachment")
    assert attachment["response"]["file_path"] == "temp_evidence/policy.pdf"

    draft = orchestrator.process_user_input("gmail-session", "Prepare a reply but do not send it")
    assert draft["execution"]["status"] == "awaiting_approval"
    assert service.drafts == []


def test_dispatch_leaves_legacy_capability_proposals_for_existing_path():
    dispatch = MultiActionDispatch(gmail_registry(), granted_permissions={"gmail.readonly"})
    legacy_proposal = {
        "result": {"proposal": {"action": {"capability": "remember_fact", "arguments": {}}}}
    }
    assert dispatch.dispatch(legacy_proposal, session_id="legacy", user_text="remember this") is None
