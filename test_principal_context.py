"""Unit tests for uri_core.core.principal_context (M22.2). A plain data
shape - see its own module docstring for why it carries no logic - so
these tests only confirm its contract: role/user_id are None together
for an unauthenticated request, and nothing is guessed or defaulted."""

import unittest

from uri_core.core.principal_context import PrincipalContext


class PrincipalContextTests(unittest.TestCase):

    def test_unauthenticated_principal_has_no_user_id_or_role(self):
        principal = PrincipalContext(
            user_id=None, role=None, device_id=None
        )
        self.assertIsNone(principal.user_id)
        self.assertIsNone(principal.role)

    def test_authenticated_principal_carries_role_and_device_id(self):
        principal = PrincipalContext(
            user_id="u1", role="USER", device_id="phone-1"
        )
        self.assertEqual(principal.user_id, "u1")
        self.assertEqual(principal.role, "USER")
        self.assertEqual(principal.device_id, "phone-1")

    def test_is_frozen(self):
        principal = PrincipalContext(
            user_id="u1", role="USER", device_id=None
        )
        with self.assertRaises(Exception):
            principal.role = "ADMIN"


if __name__ == "__main__":
    unittest.main()
