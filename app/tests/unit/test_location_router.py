"""Unit tests for LocationRouter - comprehensive testing of location API endpoints."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.v1.routers.location_router import LocationRouter
from app.core.constants import RoleID
from app.models.location_model import Location
from app.models.user_model import User


class TestLocationRouter:
    """Test suite for LocationRouter."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app with the location router."""
        from fastapi import FastAPI

        app = FastAPI()
        location_router = LocationRouter()
        app.include_router(location_router.router, prefix="/api/v1")
        return app

    @pytest.fixture
    def client(self, mock_app):
        """Create test client."""
        return TestClient(mock_app)

    @pytest.fixture
    def sample_location(self):
        """Sample location for testing."""
        return Location(
            location_id=str(uuid4()),
            location_name="Test Location",
            category_id=1,
            region_id=1,
            district_id=1,
            address="123 Test Street",
            latitude=41.2995,
            longitude=69.2401,
            status="active",
        )

    @pytest.fixture
    def admin_user(self):
        """Admin user for testing."""
        return User(
            user_id=str(uuid4()),
            username="admin",
            email="admin@example.com",
            role_id=RoleID.ADMIN.value,
            is_active=True,
        )

    @pytest.fixture
    def regular_user(self):
        """Regular user for testing."""
        return User(
            user_id=str(uuid4()),
            username="user",
            email="user@example.com",
            role_id=RoleID.USER.value,
            is_active=True,
        )

    def test_list_locations_success(self, client):
        """Test successful location listing."""
        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_locations = [
                {
                    "location_id": str(uuid4()),
                    "location_name": "Location 1",
                    "category_id": 1,
                    "region_id": 1,
                },
                {
                    "location_id": str(uuid4()),
                    "location_name": "Location 2",
                    "category_id": 2,
                    "region_id": 1,
                },
            ]

            mock_service.return_value.get_all_locations.return_value = (
                mock_locations
            )

            response = client.get("/api/v1/locations/")

            assert response.status_code == status.HTTP_200_OK
            assert len(response.json()) == 2
            assert response.json()[0]["location_name"] == "Location 1"

    def test_list_locations_with_filters(self, client):
        """Test location listing with filters."""
        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_service.return_value.get_all_locations.return_value = []

            response = client.get(
                "/api/v1/locations/?category_id=1&region_id=2"
            )

            assert response.status_code == status.HTTP_200_OK
            mock_service.return_value.get_all_locations.assert_called_once()

    def test_get_location_success(self, client, sample_location):
        """Test successful location retrieval."""
        location_id = sample_location.location_id

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_service.return_value.get_location.return_value = (
                sample_location.__dict__
            )

            response = client.get(f"/api/v1/locations/{location_id}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["location_name"] == "Test Location"

    def test_get_location_not_found(self, client):
        """Test location retrieval with non-existent ID."""
        location_id = str(uuid4())

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            from app.domain.exceptions import LocationNotFound

            mock_service.return_value.get_location.side_effect = (
                LocationNotFound("Location not found")
            )

            response = client.get(f"/api/v1/locations/{location_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_location_success(self, client, admin_user):
        """Test successful location creation."""
        location_data = {
            "location_name": "New Location",
            "category_id": 1,
            "region_id": 1,
            "district_id": 1,
            "address": "New Address",
            "latitude": 41.2995,
            "longitude": 69.2401,
            "status": "active",
        }

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
            patch("app.api.v1.dependencies.require_roles") as mock_auth,
            patch("app.core.auth.auth_manager.get_current_user") as mock_user,
        ):

            mock_user.return_value = admin_user
            mock_auth.return_value = lambda: admin_user
            mock_service.return_value.create_location.return_value = {
                **location_data,
                "location_id": str(uuid4()),
            }

            response = client.post("/api/v1/locations/", json=location_data)

            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["location_name"] == "New Location"

    def test_create_location_unauthorized(self, client, regular_user):
        """Test location creation without admin privileges."""
        location_data = {
            "location_name": "New Location",
            "category_id": 1,
            "region_id": 1,
        }

        with patch("app.core.auth.auth_manager.get_current_user") as mock_user:
            mock_user.return_value = regular_user

            response = client.post("/api/v1/locations/", json=location_data)

            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_location_success(
        self, client, admin_user, sample_location
    ):
        """Test successful location update."""
        location_id = sample_location.location_id
        update_data = {
            "location_name": "Updated Location",
            "address": "Updated Address",
        }

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
            patch("app.api.v1.dependencies.require_roles") as mock_auth,
            patch("app.core.auth.auth_manager.get_current_user") as mock_user,
        ):

            mock_user.return_value = admin_user
            mock_auth.return_value = lambda: admin_user
            updated_location = {**sample_location.__dict__, **update_data}
            mock_service.return_value.update_location.return_value = (
                updated_location
            )

            response = client.put(
                f"/api/v1/locations/{location_id}", json=update_data
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["location_name"] == "Updated Location"

    def test_get_popular_locations(self, client):
        """Test popular locations endpoint."""
        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_locations = [
                {
                    "location_id": str(uuid4()),
                    "location_name": "Popular Location",
                }
            ]
            mock_service.return_value.get_popular_locations.return_value = (
                mock_locations
            )

            response = client.get("/api/v1/locations/popular?limit=5")

            assert response.status_code == status.HTTP_200_OK
            assert len(response.json()) == 1

    def test_get_recently_rated_locations(self, client):
        """Test recently rated locations endpoint."""
        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_locations = [
                {
                    "location_id": str(uuid4()),
                    "location_name": "Recent Location",
                }
            ]
            mock_service.return_value.get_recently_rated_locations.return_value = (
                mock_locations)

            response = client.get("/api/v1/locations/recently-rated?limit=5")

            assert response.status_code == status.HTTP_200_OK
            assert len(response.json()) == 1

    def test_get_by_category(self, client):
        """Test get locations by category."""
        category_id = 1

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_locations = [
                {"location_id": str(uuid4()), "category_id": category_id}
            ]
            mock_service.return_value.get_by_category.return_value = (
                mock_locations
            )

            response = client.get(
                f"/api/v1/locations/by_category/{category_id}"
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()[0]["category_id"] == category_id

    def test_get_by_region(self, client):
        """Test get locations by region."""
        region_id = 1

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_locations = [
                {"location_id": str(uuid4()), "region_id": region_id}
            ]
            mock_service.return_value.get_by_region.return_value = (
                mock_locations
            )

            response = client.get(f"/api/v1/locations/by_region/{region_id}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json()[0]["region_id"] == region_id

    def test_assign_inspector_success(self, client, admin_user):
        """Test successful inspector assignment."""
        location_id = str(uuid4())
        user_id = str(uuid4())

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
            patch("app.api.v1.dependencies.require_roles") as mock_auth,
            patch("app.core.auth.auth_manager.get_current_user") as mock_user,
        ):

            mock_user.return_value = admin_user
            mock_auth.return_value = lambda: admin_user
            mock_service.return_value.assign_inspector.return_value = None

            response = client.post(
                f"/api/v1/locations/{location_id}/inspectors/{user_id}"
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_remove_inspector_success(self, client, admin_user):
        """Test successful inspector removal."""
        location_id = str(uuid4())
        user_id = str(uuid4())

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
            patch("app.api.v1.dependencies.require_roles") as mock_auth,
            patch("app.core.auth.auth_manager.get_current_user") as mock_user,
        ):

            mock_user.return_value = admin_user
            mock_auth.return_value = lambda: admin_user
            mock_service.return_value.unassign_inspector.return_value = None

            response = client.delete(
                f"/api/v1/locations/{location_id}/inspectors/{user_id}"
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_get_location_stats(self, client):
        """Test location statistics endpoint."""
        location_id = str(uuid4())

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_stats = {
                "total_ratings": 10,
                "average_rating": 4.5,
                "total_favorites": 5,
                "total_comments": 3,
            }
            mock_service.return_value.get_location_stats.return_value = (
                mock_stats
            )

            response = client.get(f"/api/v1/locations/{location_id}/stats")

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["total_ratings"] == 10
            assert response.json()["average_rating"] == 4.5

    def test_validation_errors(self, client):
        """Test validation errors for invalid input."""
        invalid_data = {
            "location_name": "",  # Empty name should fail
            "category_id": -1,  # Invalid category ID
        }

        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch("app.core.auth.auth_manager.get_current_user") as mock_user,
            patch("app.api.v1.dependencies.require_roles") as mock_auth,
        ):

            admin_user = User(user_id=str(uuid4()), role_id=RoleID.ADMIN.value)
            mock_user.return_value = admin_user
            mock_auth.return_value = lambda: admin_user

            response = client.post("/api/v1/locations/", json=invalid_data)

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_server_error_handling(self, client):
        """Test server error handling."""
        with (
            patch("app.api.v1.dependencies.get_uow") as mock_uow,
            patch(
                "app.services.location_service.LocationService"
            ) as mock_service,
        ):

            mock_service.return_value.get_all_locations.side_effect = (
                Exception("Database error")
            )

            response = client.get("/api/v1/locations/")

            assert (
                response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            )
