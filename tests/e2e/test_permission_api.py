import uuid

import pytest


class TestPermissionAPI:
    @pytest.mark.usefixtures("client")
    def test_create_permission(self, client):
        """
        Example: POST /lib/v1/users/permissions
        Suppose your endpoint expects 'permission_name' and 'description'
        """
        perm_name = f"perm_{uuid.uuid4().hex[:6]}"
        perm_data = {
            "permission_name": perm_name,
            "description": "Permission for testing",
        }
        resp = client.post("/lib/v1/users/permissions", json=perm_data)
        assert resp.status_code == 200, resp.text
        perm_json = resp.json()
        assert "permission_id" in perm_json
        assert perm_json["permission_name"] == perm_name

    @pytest.mark.usefixtures("client")
    def test_delete_permission(self, client):
        """
        Example: DELETE /lib/v1/users/permissions/{permission_id}
        If you have a delete endpoint for permissions
        """
        perm_data = {
            "permission_name": "delete_this_perm",
            "description": "To be removed",
        }
        create_resp = client.post("/lib/v1/users/permissions", json=perm_data)
        assert create_resp.status_code == 200
        perm_id = create_resp.json()["permission_id"]

        delete_resp = client.delete(f"/lib/v1/users/permissions/{perm_id}")
        assert delete_resp.status_code == 200
        assert (
            "Permission deleted" in delete_resp.text
        )  # or some success message
