\---



name: uri-development

description: Use when planning, implementing, reviewing, repairing, or continuing URI development. Explore deeply before plan freeze, implement the frozen plan precisely, and review against the plan and actual behaviour.

\----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------



\# URI Development



\## Core Rule



\*\*Explore freely before the plan is frozen. After freeze, implement precisely. Review against the frozen plan and actual behaviour.\*\*



\## Development Pattern



\*\*Explore → Plan → Freeze → Implement → Review → Repair → Validate → Close\*\*



Use only as much process as the work actually needs.



\---



\## 1. Explore



Before finalising a milestone, understand the real problem and intended URI experience.



Use whatever materially improves understanding, including:



\* repository and architecture inspection;

\* relevant project history and decisions;

\* research into current tools, APIs, models, techniques, or standards;

\* relevant skills or development tools;

\* disposable prototypes or competing approaches;

\* tests of uncertain assumptions;

\* identification of dependencies, edge cases, missing prerequisites, and likely failure modes.



\### Vision Check



For major product, UX, architecture, or capability milestones, perform a short `/grill-me` style vision session with the User before plan freeze when useful.



The purpose is to discover requirements that repository inspection alone cannot reveal, such as:



\* what the User actually expects the feature to feel or behave like;

\* what would make a technically correct result still disappointing;

\* missing workflows or expectations not represented in existing designs;

\* important product trade-offs;

\* what should deliberately remain outside the milestone.



Do not ask the User questions that can be answered through repository inspection, research, testing, or normal engineering judgement.



The planning stage may challenge earlier assumptions and improve or replace the proposed approach.



\---



\## 2. Plan



Produce an implementation-ready milestone plan.



The plan should be clear enough that a coding-focused model can implement it without rediscovering the architecture or repeating the planning research.



Include, where relevant:



\* intended outcome;

\* important decisions and discoveries;

\* URI components and architecture to reuse;

\* required behaviour and data flow;

\* affected areas or files where reasonably known;

\* implementation sequence;

\* important edge and failure cases;

\* tests or runtime checks;

\* acceptance criteria.



Resolve important ambiguity before implementation.



Do not prescribe unnecessary coding detail.



\---



\## 3. Freeze



After independent review and any required corrections, produce one \*\*Frozen Implementation Blueprint\*\*.



The frozen blueprint becomes the implementation contract.



After freeze:



\* intended behaviour and architecture are settled;

\* normal research and redesign stop;

\* earlier drafts become historical;

\* implementation should not silently substitute another architecture;

\* genuine contradictions or blockers should be reported rather than worked around invisibly.



\---



\## 4. Implement



Implement the Frozen Blueprint faithfully in the actual URI repository.



Focus on:



\* complete implementation;

\* correct integration with existing URI structure;

\* reuse of established components;

\* required tests and runtime evidence;

\* avoiding shortcuts, fake functionality, mocks, or partial substitutes unless explicitly permitted.



Normal coding judgement remains free.



Settled architectural decisions do not.



\---



\## 5. Review



Review the implementation against the Frozen Blueprint and actual URI behaviour.



Ask:



1\. \*\*Was the blueprint implemented completely?\*\*

2\. \*\*Does the resulting behaviour satisfy its acceptance criteria?\*\*



Report concrete defects, omissions, regressions, or deviations.



Do not reopen architecture merely because another implementation is possible or preferable.



\---



\## 6. Repair



Repair concrete review findings and rerun the relevant validation.



Do not restart planning unless implementation evidence demonstrates that the Frozen Blueprint itself is materially wrong.



Repeated failure on the same implementation problem should be escalated to a more capable implementation model rather than creating an endless review loop.



\---



\## 7. Validate and Close



Use whatever evidence best matches the milestone:



\* automated tests;

\* runtime checks;

\* integration probes;

\* visual comparison;

\* prototype verification;

\* User live acceptance.



When the blueprint is implemented and its acceptance criteria are satisfied, close the milestone and move forward.



\---



\## URI Development Principle



\*\*Spend intelligence before coding.

Spend precision during coding.

Spend scrutiny after coding.\*\*



