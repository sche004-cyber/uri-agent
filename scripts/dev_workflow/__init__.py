"""URI Development Automation Workflow Package (AO-4).

Development-only tooling for multi-agent coordination (Claude Code, Gemma 4 12B, Antigravity).
"""

from scripts.dev_workflow.state_machine import (
    WorkflowActor,
    WorkflowState,
    validate_transition,
    WorkflowException,
    InvalidTransitionError,
    AuthorityViolationError,
    InvariantViolationError,
)
from scripts.dev_workflow.state_manager import (
    MilestoneStateRecord,
    StateFileManager,
    GemmaReturnReport,
    AntigravityAuditReport,
    ClaudeVerificationDecision,
)
from scripts.dev_workflow.claude_verifier import (
    ClaudeBridgeVerifier,
    VerificationResult,
)
from scripts.dev_workflow.file_authority import (
    FileWriteAuthorizer,
    FileWriteOperation,
    WriteAuthorizationResult,
)

__all__ = [
    "WorkflowState",
    "WorkflowActor",
    "validate_transition",
    "WorkflowException",
    "InvalidTransitionError",
    "AuthorityViolationError",
    "InvariantViolationError",
    "MilestoneStateRecord",
    "StateFileManager",
    "GemmaReturnReport",
    "AntigravityAuditReport",
    "ClaudeVerificationDecision",
    "ClaudeBridgeVerifier",
    "VerificationResult",
    "FileWriteAuthorizer",
    "FileWriteOperation",
    "WriteAuthorizationResult",
]
