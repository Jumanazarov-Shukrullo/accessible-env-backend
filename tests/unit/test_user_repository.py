import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.domain.repositories.user_repository import UserRepository


DATABASE_URL = "sqlite:///:memory:"


class TestUserRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary in-memory DB for all tests in this class
        cls.engine = create_engine(DATABASE_URL, future=True)
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(
            bind=cls.engine,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )

    @classmethod
    def tearDownClass(cls):
        # Drop all tables after the tests
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self):
        # Create a new session before each test
        self.db = self.SessionLocal()
        self.repo = UserRepository(self.db)

    def tearDown(self):
        # Close session after each test
        self.db.close()

    def test_create_user(self):
        user_data = {
            "username": "repo_test_user",
            "full_name": "Repo Test",
            "email": "repo_test@example.com",
            "password_hash": "hashedpass",
            "role_id": 3,
        }
        created_user = self.repo.create(user_data)
        self.assertIsNotNone(created_user.user_id)
        self.assertEqual(created_user.username, "repo_test_user")

        fetched = self.repo.get_by_username("repo_test_user")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.email, "repo_test@example.com")

    def test_update_user(self):
        # Create first
        user_data = {
            "username": "update_me",
            "full_name": "Update Me",
            "email": "update@example.com",
            "password_hash": "somepass",
        }
        user = self.repo.create(user_data)
        user.full_name = "Updated Name"
        updated = self.repo.update(user)
        self.assertEqual(updated.full_name, "Updated Name")

    def test_delete_user(self):
        user_data = {
            "username": "delete_me",
            "full_name": "Delete Me",
            "email": "delete_me@example.com",
            "password_hash": "pass",
        }
        user = self.repo.create(user_data)
        user_id = user.user_id

        self.repo.delete(user)
        self.db.commit()

        self.assertIsNone(self.repo.get_by_id(user_id))


# Similarly, you can create TestRoleRepository, TestPermissionRepository
# classes with the same structure: setUpClass, setUp, tearDown, etc.
