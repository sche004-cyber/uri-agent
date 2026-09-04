# URI MODEL ↔ RUNTIME CONTRACT
## Version 1.0

**Date:** 3 September 2026
**Status:** ACCEPTED

The model reasons and proposes.

The URI runtime validates, authorizes, executes, persists, audits, and reports.

## 1. Model Response Envelope

```json
{
  "intent": {},
  "facts": [],
  "evidence_assessment": {},
  "decision": {},
  "clarification": null,
  "workflow": null,
  "action": null,
  "draft": null,
  "review": {},
  "confidence": 0.0
}
```

Fields may be omitted when irrelevant.

## 2. Intent

```json
{
  "task_type": "string",
  "goal": "string",
  "requested_output": "string",
  "domain": "string"
}
```

The task type describes the user's objective and is not required to match a predefined task list.

## 3. Facts

```json
{
  "name": "string",
  "value": "any",
  "status": "CONFIRMED",
  "source": "string",
  "source_reference": "string"
}
```

Allowed status values:

- CONFIRMED
- PROVISIONAL
- HISTORICAL
- SUPERSEDED
- EXPIRED

The runtime may reject invalid status values.

## 4. Clarification

```json
{
  "required": true,
  "required_field": "string",
  "question": "string"
}
```

Only one essential question should normally be returned at a time.

## 5. Capability Proposal

```json
{
  "capability": "registered_capability_name",
  "arguments": {},
  "reason": "string"
}
```

The runtime verifies that the capability is registered.

The model must never invent capability names.

## 6. Dynamic Workflow Proposal

```json
{
  "goal": "string",
  "steps": [
    {
      "step_id": "string",
      "capability": "registered_capability_name",
      "depends_on": [],
      "requires_user_input": false
    }
  ]
}
```

The model may create a novel workflow by composing registered capabilities.

The runtime validates capability registration, dependency integrity, schema validity, authorization, and execution safety.

## 7. Missing Capability

```json
{
  "decision": {
    "status": "capability_unavailable",
    "required_capability": "string",
    "reason": "string"
  }
}
```

The model must not invent a replacement capability.

## 8. Action Proposal

```json
{
  "type": "string",
  "capability": "registered_capability_name",
  "arguments": {},
  "approval_required": true
}
```

The runtime may override or enforce approval requirements.

The model cannot disable runtime approval policy.

## 9. Evidence Assessment

```json
{
  "sufficient": true,
  "conflicts": [],
  "uncertainties": [],
  "current_sources": [],
  "historical_sources": []
}
```

The model must distinguish direct evidence, inference, historical precedent, and unresolved uncertainty.

## 10. Draft

```json
{
  "document_type": "noting",
  "content": "string",
  "status": "draft",
  "review_required": true
}
```

## 11. Review

```json
{
  "passed": true,
  "issues": [],
  "unsupported_claims": [],
  "missing_information": []
}
```

## 12. Execution Result

The runtime reports actual execution separately:

```json
{
  "status": "success",
  "capability": "string",
  "output": {},
  "side_effect": false
}
```

The model must not claim successful execution before receiving this result.

## 13. Security Boundary

The runtime has final authority over capability registration, permissions, authentication, authorization, approval, external actions, file writes, persistence, audit, and security policy.

Model output is untrusted input to these controls.

## 14. Generalization Requirement

The contract allows the model to describe tasks that URI developers did not explicitly anticipate.

The runtime validates proposed primitives rather than requiring every possible task to have a pre-written workflow.

## 15. Compatibility Strategy

The existing URI workflow engine remains supported during migration.

The new model contract initially operates alongside existing deterministic logic.

Only after tests establish equivalent or better behaviour should deterministic reasoning be reduced.

## 16. Design Goal

The contract allows cloud models, local models, future model routing, mobile clients, remote deployments, and novel task composition.

The model can become more capable without requiring the URI runtime to grow proportionally.

The runtime remains small because it does not need to understand every task.

It only needs to safely validate and execute permitted capabilities.
