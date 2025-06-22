# tests/unit/test_user_service.py
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.models.user_model import User
from app.services.user_service import UserService


class TestUserService(unittest.TestCase):
    def setUp(self):
        # Create a mock repository
        self.mock_repo = MagicMock()
        # Initialize the service with the mock repo
        self.service = UserService(db=None)
        self.service.repo = self.mock_repo

    def test_register_user_success(self):
        # mock_repo.get_by_username and get_by_email both return None => user
        # is new
        self.mock_repo.get_by_username.return_value = None
        self.mock_repo.get_by_email.return_value = None

        # mock_repo.create returns a User object
        created_mock_user = User(username="testservice")
        self.mock_repo.create.return_value = created_mock_user

        user_in = {
            "username": "testservice",
            "full_name": "Service Test",
            "email": "testservice@example.com",
            "password": "Plaintext123",
        }

        result = self.service.register_user(user_in)
        self.assertEqual(result.username, "testservice")

    def test_register_user_existing_username(self):
        # If user with that username exists, service should raise 400
        existing_user = User(username="existing")
        self.mock_repo.get_by_username.return_value = existing_user

        user_in = {
            "username": "existing",
            "full_name": "Already",
            "email": "already@example.com",
            "password": "pass",
        }
        with self.assertRaises(HTTPException) as cm:
            self.service.register_user(user_in)
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Username already exists", cm.exception.detail)

    def test_change_role_superadmin(self):
        # current user is superadmin
        current_user = User(role_id=1)
        target_user = User(user_id="123", role_id=3)
        self.mock_repo.get_by_id.return_value = target_user

        updated_user = User(user_id="123", role_id=2)
        self.mock_repo.update.return_value = updated_user

        result = self.service.change_role(current_user, "123", "2")
        self.assertEqual(result.role_id, 2)
        self.mock_repo.update.assert_called_once()

    def test_change_role_insufficient_permissions(self):
        # current user is just normal (role_id=3)
        current_user = User(role_id=3)
        target_user = User(user_id="abc", role_id=3)
        self.mock_repo.get_by_id.return_value = target_user

        with self.assertRaises(HTTPException) as cm:
            self.service.change_role(current_user, "abc", "2")
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("Insufficient permissions", cm.exception.detail)
