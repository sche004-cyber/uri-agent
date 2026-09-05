"""Structural invariant tests for Prototype 2 (Multi-Client + Runtime
Awareness).

Asserts, by inspecting actual import statements (same technique as
test_capability_authority_boundary.py), that client/device identity
(auth_session.py's device_id, identity.py's DeviceIdentityStore) can
never become user-authoritative data:

    - auth_session.py (login tokens + their bound device_id) never
      imports user_memory.py or user_profile.py - a login/connection
      concept must have no path to writing itself into user state.
    - user_memory.py and user_profile.py never import auth_session.py
      or identity.py - user-authoritative stores must stay unaware of
      login sessions and device identity entirely.
"""

import ast
import os
import unittest


def _imported_module_names(file_path: str) -> set:

    with open(file_path, "r", encoding="utf-8-sig") as file:
        tree = ast.parse(file.read(), filename=file_path)

    names = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:
                names.add(alias.name)

        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)

    return names


class ClientIdentityBoundaryTests(unittest.TestCase):

    def test_auth_session_never_imports_user_memory_or_profile(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "auth_session.py")
        )

        offending = {
            name
            for name in imports
            if "user_memory" in name or "user_profile" in name
        }

        self.assertEqual(
            offending,
            set(),
            "auth_session.py must never import user_memory/"
            "user_profile - a login token's device_id must have no "
            "path to becoming user-authoritative state.",
        )

    def test_user_accounts_never_imports_user_memory_or_profile(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "user_accounts.py")
        )

        offending = {
            name
            for name in imports
            if "user_memory" in name or "user_profile" in name
        }

        self.assertEqual(offending, set())

    def test_user_memory_never_imports_auth_session_or_identity(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "user_memory.py")
        )

        offending = {
            name
            for name in imports
            if "auth_session" in name
            or "identity" in name
            or "user_accounts" in name
        }

        self.assertEqual(
            offending,
            set(),
            "user_memory.py must never import auth_session/identity/"
            "user_accounts - user-authoritative memory must stay "
            "unaware of login sessions and device identity.",
        )

    def test_user_profile_never_imports_auth_session_or_identity(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "user_profile.py")
        )

        offending = {
            name
            for name in imports
            if "auth_session" in name
            or "identity" in name
            or "user_accounts" in name
        }

        self.assertEqual(offending, set())


if __name__ == "__main__":
    unittest.main()
