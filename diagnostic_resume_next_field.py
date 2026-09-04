from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.workflow_executor import WorkflowExecutor

orchestrator = UriOrchestrator()

session_id = "diagnostic-resume-next-field"

session = (
    orchestrator.session_manager
    .get_session(session_id)
)

session.active_workflow = {
    "workflow_id": "next-field",
    "status": "waiting_for_input",
    "steps": [
        {
            "step_id": "step_1",
            "capability": "clarify",
            "status": "waiting_for_input",
            "depends_on": []
        }
    ]
}

session.active_workflow_status = "waiting_for_input"
session.active_workflow_required_field = "subject"

executor = WorkflowExecutor()

def clarify_handler(step, workflow):

    print("\nHANDLER RECEIVED WORKFLOW:")
    print(workflow)

    result = {
        "status": "waiting_for_input",
        "message": "What approval is required?",
        "required_field": "approval_requested"
    }

    print("\nHANDLER RETURNED:")
    print(result)

    return result

executor.register_handler(
    "clarify",
    clarify_handler
)

orchestrator.workflow_executor = executor

print("\n===== BEFORE PROCESS =====")
print("active_workflow_recovered:",
      getattr(session, "active_workflow_recovered", "MISSING"))
print("active_workflow_status:",
      session.active_workflow_status)
print("active_workflow:")
print(session.active_workflow)
print("active_workflow_required_field:",
      session.active_workflow_required_field)
print("current_facts:",
      session.current_facts)

result = orchestrator.process_user_input(
    session_id,
    "Insurance renewal"
)

print("\n===== RESULT =====")
print(result)

print("\n===== AFTER PROCESS =====")
print("active_workflow_recovered:",
      getattr(session, "active_workflow_recovered", "MISSING"))
print("active_workflow_status:",
      session.active_workflow_status)
print("active_workflow:")
print(session.active_workflow)
print("active_workflow_required_field:",
      session.active_workflow_required_field)
print("active_workflow_question:",
      session.active_workflow_question)
print("current_facts:",
      session.current_facts)
