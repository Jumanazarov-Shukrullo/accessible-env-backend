import unittest
from uuid import uuid4

from app.models.permission_model import Permission
from app.models.role_model import Role
from app.models.user_model import User


class TestUserModel(unittest.TestCase):
    def test_defaults(self):
        user = User(
            user_id=str(uuid4()),
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            password_hash="hashed123",
        )
        self.assertFalse(
            user.email_verified, "Default email_verified should be False"
        )
        self.assertTrue(user.is_active, "Default is_active should be True")
        self.assertEqual(user.failed_login_attempts, 0)

    def test_set_fields(self):
        user = User(username="setfields", password_hash="abc")
        user.email_verified = True
        user.is_active = False
        user.failed_login_attempts = 3
        self.assertTrue(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(user.failed_login_attempts, 3)


class TestRoleModel(unittest.TestCase):
    def test_role_fields(self):
        role = Role(role_name="admin", description="Administrator role")
        self.assertEqual(role.role_name, "admin")
        self.assertEqual(role.description, "Administrator role")


class TestPermissionModel(unittest.TestCase):
    def test_permission_fields(self):
        perm = Permission(
            permission_name="can_edit", description="Edit permission"
        )
        self.assertEqual(perm.permission_name, "can_edit")
        self.assertEqual(perm.description, "Edit permission")
