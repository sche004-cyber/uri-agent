"""M22.2 (see URI_M22_ARCHITECTURE.md section 4.4): structural proof
that experience_tier - a zero-authority, user-settable UX preference -
can never influence any authorization decision anywhere in this
codebase's real authorization/execution path.

Standing rule (see URI_M22_ARCHITECTURE.md's M22.2 milestone entry and
the M22.2 task brief): "No authorization path may read experience_tier.
Enforce this with tests." CapabilityResolver does not exist until
M22.4 and there is no /admin/* surface yet, so THIS milestone's
enforceable scope is the real authorization/execution modules that DO
exist today - the exact set test_capability_authority_boundary.py
already treats as the authority boundary (ApprovalGate, ApprovalStore,
ToolDispatcher, CapabilityRegistry, CapabilityPlanner) plus
orchestrator.py, the one place that calls into all of them. None of
these may reference the string "experience_tier" anywhere - not in a
condition, not in a lookup, not even in a comment that could later be
mistaken for real logic.

experience_tier IS allowed to appear in server.py (the client-facing
read/write endpoints - GET /auth/me, POST /auth/experience-tier - see
those endpoints' own docstrings) and in user_accounts.py (where the
field itself is defined and persisted). Neither of those is an
authorization/execution module, so both are deliberately excluded
below - the same "know exactly what's allowed where" precision
test_capability_authority_boundary.py's own docstring already
establishes for its own boundaries.
"""

import os
import unittest

AUTHORIZATION_AND_EXECUTION_MODULES = (
    os.path.join("uri_core", "core", "approval_gate.py"),
    os.path.join("uri_core", "core", "approval_store.py"),
    os.path.join("uri_core", "core", "dispatcher.py"),
    os.path.join("uri_core", "core", "capability_registry.py"),
    os.path.join("uri_core", "core", "capability_planner.py"),
    os.path.join("uri_core", "core", "orchestrator.py"),
)

FORBIDDEN_STRING = "experience_tier"


class ExperienceTierNeverAuthorizesTests(unittest.TestCase):

    def test_no_authorization_or_execution_module_references_experience_tier(
        self,
    ):
        offenders = []

        for relative_path in AUTHORIZATION_AND_EXECUTION_MODULES:

            with open(
                relative_path, "r", encoding="utf-8-sig"
            ) as file:
                source = file.read()

            if FORBIDDEN_STRING in source:
                offenders.append(relative_path)

        self.assertEqual(
            offenders,
            [],
            "experience_tier must never be referenced by any real "
            "authorization/execution module - it is a zero-authority "
            "UX preference (see user_accounts.py's module docstring), "
            "and its only legitimate readers are the client-facing "
            f"endpoints in server.py. Offending files: {offenders}",
        )

    def test_every_scanned_module_actually_exists_and_has_content(self):
        # Guards against the check above being silently vacuous (e.g.
        # a renamed/moved file that would otherwise just be skipped by
        # a broken path, making the "no offenders found" result above
        # meaningless rather than a real pass).
        for relative_path in AUTHORIZATION_AND_EXECUTION_MODULES:
            self.assertTrue(
                os.path.isfile(relative_path), relative_path
            )
            self.assertGreater(
                os.path.getsize(relative_path), 0, relative_path
            )

    def test_detection_itself_catches_a_known_violation(self):
        # A canary proving the substring check above would actually
        # fail on a real violation, not merely on the absence of one -
        # exercised against synthetic content, never against a real
        # source file.
        synthetic_violation = (
            "def _is_allowed(descriptor, user):\n"
            "    if user.experience_tier == 'ADVANCED':\n"
            "        return True\n"
        )
        self.assertIn(FORBIDDEN_STRING, synthetic_violation)

        synthetic_clean = (
            "def _is_allowed(descriptor, user):\n"
            "    if user.role == 'ADMIN':\n"
            "        return True\n"
        )
        self.assertNotIn(FORBIDDEN_STRING, synthetic_clean)


if __name__ == "__main__":
    unittest.main()
