import uuid
import pytest


class TestUserAPI:
    """
    Class-based tests for user-related endpoints.
    """

    @pytest.mark.usefixtures("client")
    def test_register_and_login_user(self, client):
        """
        1) RegisterPage a user
        2) LoginPage with correct credentials
        3) Attempt login with bad password
        """
        # 1. RegisterPage
        unique_suffix = uuid.uuid4().hex[:6]
        user_payload = {
            "full_name": f"Test User {unique_suffix}",
            "username": f"testuser_{unique_suffix}",
            "email": f"testuser_{unique_suffix}@example.com",
            "password": "CorrectPassword123",
            "role_id": 3,
        }

        register_response = client.post("/lib/v1/users/register", json=user_payload)
        assert register_response.status_code == 200, register_response.text
        data = register_response.json()
        assert "user_id" in data
        user_id = data["user_id"]

        # 2. LoginPage with correct credentials
        login_data = {"username": user_payload["username"], "password": user_payload["password"]}
        login_response = client.post("/lib/v1/users/token", data=login_data)
        assert login_response.status_code == 200, login_response.text
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # 3. Bad login
        wrong_pass_data = {"username": user_payload["username"], "password": "WrongPassword"}
        wrong_login_resp = client.post("/lib/v1/users/token", data=wrong_pass_data)
        assert wrong_login_resp.status_code == 401  # Unauthorized
        assert "access_token" not in wrong_login_resp.json()

    @pytest.mark.usefixtures("client")
    def test_email_verification(self, client):
        """
        If your system has an endpoint like: /lib/v1/users/verify_email?token=...
        This test demonstrates calling it with a mock or generated token.
        """
        # Example: we have a user with known email "some_registered@example.com"
        # Hypothetically, we generate or mock an email verification token:
        token = "FAKE_JWT_EMAIL_TOKEN_EXAMPLE"

        resp = client.get(f"/lib/v1/users/verify_email?token={token}")
        if resp.status_code == 200:
            user_data = resp.json()
            assert user_data["email_verified"] is True
        else:
            # Could be 400 or 404 if token is invalid or user not found
            print("verify_email response:", resp.json())
            assert resp.status_code in [200, 400, 404]

    @pytest.mark.usefixtures("client")
    def test_role_changes_and_banning(self, client):
        """
        Tests:
        - Admin promotes normal user to admin
        - Admin cannot promote user to superadmin
        - Non-admin cannot change roles or ban
        """
        # 1. Create a normal user
        normal_suffix = uuid.uuid4().hex[:6]
        normal_user = {
            "full_name": f"Normal {normal_suffix}",
            "username": f"normal_{normal_suffix}",
            "email": f"normal_{normal_suffix}@example.com",
            "password": "NormalPass123",
            "role_id": 3,
        }
        reg_normal = client.post("/lib/v1/users/register", json=normal_user)
        normal_id = reg_normal.json()["user_id"]
        assert reg_normal.status_code == 200

        # 2. Create an admin user
        admin_suffix = uuid.uuid4().hex[:6]
        admin_user = {
            "full_name": f"Admin {admin_suffix}",
            "username": f"admin_{admin_suffix}",
            "email": f"admin_{admin_suffix}@example.com",
            "password": "AdminPass123",
            "role_id": 2,
        }
        reg_admin = client.post("/lib/v1/users/register", json=admin_user)
        admin_id = reg_admin.json()["user_id"]
        assert reg_admin.status_code == 200

        # 3. LoginPage as admin
        admin_login_data = {"username": admin_user["username"], "password": admin_user["password"]}
        admin_login_resp = client.post("/lib/v1/users/token", data=admin_login_data)
        assert admin_login_resp.status_code == 200
        admin_token = admin_login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 4. Admin promotes normal user to admin
        promote_resp = client.put(f"/lib/v1/users/{normal_id}/role?new_role=2", headers=headers)
        assert promote_resp.status_code == 200, promote_resp.text
        updated_user = promote_resp.json()
        assert updated_user["role_id"] == 2

        # 5. Admin tries to promote user to superadmin
        promote_superadmin = client.put(f"/lib/v1/users/{normal_id}/role?new_role=1", headers=headers)
        assert promote_superadmin.status_code == 403

        # 6. Admin bans the now-admin user
        ban_resp = client.put(f"/lib/v1/users/{normal_id}/ban", headers=headers)
        assert ban_resp.status_code == 200
        banned_user = ban_resp.json()
        assert banned_user["is_active"] is False

        # 7. New normal user tries to do role changes => 403
        normal2_suffix = uuid.uuid4().hex[:6]
        normal2 = {
            "full_name": f"Normal2 {normal2_suffix}",
            "username": f"normal2_{normal2_suffix}",
            "email": f"normal2_{normal2_suffix}@example.com",
            "password": "NormalPass456",
            "role_id": 3,
        }
        reg_normal2 = client.post("/lib/v1/users/register", json=normal2)
        normal2_id = reg_normal2.json()["user_id"]
        assert reg_normal2.status_code == 200

        login_normal2 = client.post(
            "/lib/v1/users/token", data={"username": normal2["username"], "password": normal2["password"]}
        )
        assert login_normal2.status_code == 200
        normal2_token = login_normal2.json()["access_token"]
        normal2_headers = {"Authorization": f"Bearer {normal2_token}"}

        # 8. normal2 tries to promote (banned) user => 403
        fail_resp = client.put(f"/lib/v1/users/{normal_id}/role?new_role=2", headers=normal2_headers)
        assert fail_resp.status_code == 403

        # 9. normal2 tries to ban someone => 403
        fail_ban = client.put(f"/lib/v1/users/{admin_id}/ban", headers=normal2_headers)
        assert fail_ban.status_code == 403
