import uuid

import pytest


class TestRoleAPI:
    @pytest.mark.usefixtures("client")
    def test_create_role(self, client):
        """
        Example: POST /lib/v1/users/roles
        Suppose your RoleCreate schema includes 'role_name' and 'description'
        """
        unique_role = f"role_{uuid.uuid4().hex[:6]}"
        role_data = {
            "role_name": unique_role,
            "description": "E2E Created Role",
        }
        resp = client.post("/lib/v1/users/roles", json=role_data)
        assert resp.status_code == 200, resp.text
        role_json = resp.json()
        assert "role_id" in role_json
        assert role_json["role_name"] == unique_role

    @pytest.mark.usefixtures("client")
    def test_assign_permission(self, client):
        """
        Example:
        - Create a role
        - Create a permission
        - Assign the permission to the role
        """
        # 1) Create role
        role_data = {"role_name": "test_role", "description": "Test Role"}
        role_resp = client.post("/lib/v1/users/roles", json=role_data)
        assert role_resp.status_code == 200
        role_id = role_resp.json()["role_id"]

        # 2) Create permission
        perm_data = {
            "permission_name": "can_edit",
            "description": "Can edit records",
        }
        perm_resp = client.post("/lib/v1/users/permissions", json=perm_data)
        assert perm_resp.status_code == 200
        perm_id = perm_resp.json()["permission_id"]

        # 3) Assign permission to role
        assign_resp = client.post(
            f"/lib/v1/users/roles/{role_id}/assign_permission/{perm_id}"
        )
        assert assign_resp.status_code == 200, assign_resp.text
        assignment_data = assign_resp.json()
        assert assignment_data["role_id"] == role_id
        assert assignment_data["permission_id"] == perm_id
        assert (
            "granted_at" in assignment_data
        )  # or whatever fields your API returns
