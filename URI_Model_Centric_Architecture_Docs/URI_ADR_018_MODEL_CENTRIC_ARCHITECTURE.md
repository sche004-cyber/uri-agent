# ADR-018 — Model-Centric Intelligence / Lightweight URI Runtime

**Date:** 3 September 2026
**Status:** ACCEPTED

## Decision

URI will use a model-centric intelligence architecture.

The AI model performs the majority of reasoning, interpretation, planning, clarification, evidence interpretation, drafting, review, and recovery reasoning.

The local URI runtime remains a lightweight deterministic control and execution layer.

## Core Architectural Principle

> URI must be task-general rather than task-hard-coded.

URI must adapt to new user objectives, questions, phrasing, and combinations of tasks without requiring developers to hard-code every individual task or workflow.

Developers primarily provide reusable capabilities and safe primitives. The model reasons about and composes those capabilities into new workflows.

Hard-coded logic is reserved primarily for security, authorization, capability boundaries, institutional safety, state integrity, approval enforcement, persistence, execution control, and other deterministic controls.

## Model Responsibilities

- intent interpretation
- task classification
- workflow planning
- dependency planning
- clarification
- evidence interpretation
- current versus historical reasoning
- conflict identification
- decision-context preparation
- administrative drafting
- drafting-style adaptation
- output review
- recovery reasoning
- registered capability selection
- composition of capabilities into novel workflows

## Runtime Responsibilities

- authentication
- authorization
- capability allow-lists
- actual capability execution
- file and external operations
- session identity
- persistence
- audit
- approval gates
- destructive or side-effecting actions
- structured-output validation
- security boundaries
- prevention of unauthorized or duplicate side effects

## Authority Principle

The model may propose an action.

The runtime decides whether the action is permitted and executes it only when deterministic controls are satisfied.

The model is never the final authority for security, authorization, institutional approval, or execution permission.

## Current vs Historical Information

Historical institutional documents may be used for drafting style, vocabulary, structure, precedent, and understanding previous practice.

Historical information must not automatically become current authority.

Current authoritative information takes priority. Material conflicts must not be silently resolved.

## Memory

The model may identify information that appears useful for future continuity.

The memory/runtime layer remains responsible for applying URI memory policy, including explicit permission where required.

## Approval

The model may identify that approval is required.

The runtime remains responsible for enforcing the approval gate.

The model cannot grant institutional approval.

## Lightweight Runtime Objective

URI should avoid reproducing complex reasoning in deterministic Python when the same reasoning can safely be delegated to the model.

The local runtime should remain small enough to support:

- desktop deployment
- mobile deployment
- remote deployment
- cloud model usage
- local model usage
- future model routing

## Migration Principle

Existing Python reasoning components must not be deleted immediately.

Each component will first be classified as:

1. MODEL INTELLIGENCE
2. RUNTIME CONTROL
3. SHARED / TRANSITIONAL

Only after equivalent model behaviour has been tested should unnecessary deterministic reasoning be reduced.

## Compatibility

The existing workflow engine and its tests remain the regression baseline.

The migration must preserve existing behaviour while moving intelligence into the model.

## Objective

> Powerful general-purpose AI reasoning with a small, secure, deterministic execution core.
