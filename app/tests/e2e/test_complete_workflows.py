"""End-to-end tests for complete user workflows."""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.db.session import get_db
from app.models.user_model import User
from app.models.location_model import Location
from app.models.assessment_model import LocationSetAssessment, AssessmentSet
from app.core.constants import RoleID


class TestCompleteWorkflows:
    """End-to-end tests for complete application workflows."""

    @pytest.fixture(scope="class")
    def test_client(self):
        """Create test client for the application."""
        return TestClient(app)

    @pytest.fixture
    def admin_token(self, test_client):
        """Get authentication token for admin user."""
        # Create admin user first
        admin_data = {
            "username": "testadmin",
            "email": "admin@test.com",
            "password": "adminpassword123",
            "first_name": "Test",
            "surname": "Admin"
        }
        
        # Register admin (assuming first user becomes admin)
        response = test_client.post("/api/v1/users/register", json=admin_data)
        assert response.status_code == 201
        
        # Login to get token
        login_data = {
            "username": "testadmin",
            "password": "adminpassword123"
        }
        response = test_client.post("/api/v1/users/login", data=login_data)
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture
    def inspector_token(self, test_client, admin_token):
        """Create inspector user and get token."""
        # Admin creates inspector
        inspector_data = {
            "username": "inspector1",
            "email": "inspector@test.com",
            "first_name": "Test",
            "surname": "Inspector",
            "role_id": RoleID.INSPECTOR.value
        }
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = test_client.post(
            "/api/v1/users/invite", 
            json=inspector_data, 
            headers=headers
        )
        assert response.status_code == 201
        
        # Inspector logs in with temp password
        temp_password = response.json()["temp_password"]
        login_data = {
            "username": "inspector1",
            "password": temp_password
        }
        response = test_client.post("/api/v1/users/login", data=login_data)
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture
    def user_token(self, test_client):
        """Create regular user and get token."""
        user_data = {
            "username": "testuser",
            "email": "user@test.com",
            "password": "userpassword123",
            "first_name": "Test",
            "surname": "User"
        }
        
        response = test_client.post("/api/v1/users/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username": "testuser",
            "password": "userpassword123"
        }
        response = test_client.post("/api/v1/users/login", data=login_data)
        assert response.status_code == 200
        return response.json()["access_token"]

    def test_complete_user_registration_flow(self, test_client):
        """Test complete user registration and verification flow."""
        # Step 1: Register user
        user_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "password123",
            "first_name": "New",
            "surname": "User"
        }
        
        response = test_client.post("/api/v1/users/register", json=user_data)
        assert response.status_code == 201
        user_result = response.json()
        
        assert user_result["username"] == user_data["username"]
        assert user_result["email"] == user_data["email"]
        assert "verification_link" in user_result
        
        # Step 2: Verify email (mock the token verification)
        with patch('app.services.user_service.UserService.verify_email') as mock_verify:
            mock_verify.return_value = User(
                user_id="test_id",
                username=user_data["username"],
                email=user_data["email"],
                email_verified=True
            )
            
            response = test_client.get("/api/v1/users/verify_email?token=test_token")
            assert response.status_code == 200
        
        # Step 3: Login with verified user
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        response = test_client.post("/api/v1/users/login", data=login_data)
        assert response.status_code == 200
        
        token_result = response.json()
        assert "access_token" in token_result
        assert token_result["token_type"] == "bearer"

    def test_complete_location_management_flow(self, test_client, admin_token):
        """Test complete location creation and management flow."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Step 1: Create category first
        category_data = {
            "category_name": "Test Category",
            "description": "Test category for locations"
        }
        response = test_client.post(
            "/api/v1/categories/", 
            json=category_data, 
            headers=headers
        )
        assert response.status_code == 201
        category_id = response.json()["category_id"]
        
        # Step 2: Create geographical entities
        region_data = {
            "region_name": "Test Region",
            "region_code": "TR"
        }
        response = test_client.post(
            "/api/v1/geo/regions/", 
            json=region_data, 
            headers=headers
        )
        assert response.status_code == 201
        region_id = response.json()["region_id"]
        
        district_data = {
            "district_name": "Test District",
            "district_code": "TD",
            "region_id": region_id
        }
        response = test_client.post(
            "/api/v1/geo/districts/", 
            json=district_data, 
            headers=headers
        )
        assert response.status_code == 201
        district_id = response.json()["district_id"]
        
        # Step 3: Create location
        location_data = {
            "location_name": "Test Location",
            "address": "123 Test Street",
            "latitude": 41.2995,
            "longitude": 69.2401,
            "contact_info": "+998901234567",
            "category_id": category_id,
            "region_id": region_id,
            "district_id": district_id,
            "status": "active"
        }
        
        response = test_client.post(
            "/api/v1/locations/", 
            json=location_data, 
            headers=headers
        )
        assert response.status_code == 201
        location_result = response.json()
        location_id = location_result["location_id"]
        
        assert location_result["location_name"] == location_data["location_name"]
        assert location_result["category_id"] == category_id
        
        # Step 4: Update location
        update_data = {
            "description": "Updated test location description"
        }
        response = test_client.put(
            f"/api/v1/locations/{location_id}", 
            json=update_data, 
            headers=headers
        )
        assert response.status_code == 200
        
        # Step 5: Get location details
        response = test_client.get(f"/api/v1/locations/{location_id}")
        assert response.status_code == 200
        location_details = response.json()
        assert location_details["description"] == update_data["description"]
        
        # Step 6: List locations with filters
        response = test_client.get(
            "/api/v1/locations/", 
            params={"category_id": category_id}
        )
        assert response.status_code == 200
        locations_list = response.json()
        assert len(locations_list) > 0
        assert any(loc["location_id"] == location_id for loc in locations_list)

    def test_complete_assessment_workflow(self, test_client, admin_token, inspector_token):
        """Test complete assessment creation and submission workflow."""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        inspector_headers = {"Authorization": f"Bearer {inspector_token}"}
        
        # Step 1: Admin creates assessment criteria
        criteria_data = {
            "criterion_name": "Entrance Accessibility",
            "description": "Wheelchair accessible entrance",
            "max_score": 10,
            "unit": "points"
        }
        response = test_client.post(
            "/api/v1/assessments/criteria/", 
            json=criteria_data, 
            headers=admin_headers
        )
        assert response.status_code == 201
        criterion_id = response.json()["criterion_id"]
        
        # Step 2: Admin creates assessment set
        assessment_set_data = {
            "assessment_set_name": "Basic Accessibility",
            "description": "Basic accessibility assessment"
        }
        response = test_client.post(
            "/api/v1/assessments/sets/", 
            json=assessment_set_data, 
            headers=admin_headers
        )
        assert response.status_code == 201
        set_id = response.json()["assessment_set_id"]
        
        # Step 3: Add criteria to set
        set_criteria_data = {
            "assessment_set_id": set_id,
            "criterion_id": criterion_id,
            "is_required": True,
            "weight": 1.0
        }
        response = test_client.post(
            "/api/v1/assessments/sets/criteria/", 
            json=set_criteria_data, 
            headers=admin_headers
        )
        assert response.status_code == 201
        
        # Step 4: Create location for assessment (simplified)
        with patch('app.services.location_service.LocationService.create') as mock_create:
            mock_location = Location(
                location_id="test_location_id",
                location_name="Test Location",
                category_id=1,
                region_id=1,
                district_id=1
            )
            mock_create.return_value = mock_location
            
            # Step 5: Inspector creates assessment
            assessment_data = {
                "location_id": "test_location_id",
                "assessment_set_id": set_id
            }
            response = test_client.post(
                "/api/v1/assessments/", 
                json=assessment_data, 
                headers=inspector_headers
            )
            assert response.status_code == 201
            assessment_id = response.json()["assessment_id"]
            
            # Step 6: Add assessment details
            detail_data = {
                "location_set_assessment_id": assessment_id,
                "criterion_id": criterion_id,
                "score": 8,
                "comment": "Good accessibility with minor issues",
                "condition": "good"
            }
            response = test_client.post(
                "/api/v1/assessment-details/", 
                json=detail_data, 
                headers=inspector_headers
            )
            assert response.status_code == 201
            
            # Step 7: Submit assessment
            response = test_client.post(
                f"/api/v1/assessments/{assessment_id}/submit", 
                headers=inspector_headers
            )
            assert response.status_code == 200
            
            # Step 8: Admin verifies assessment
            verification_data = {
                "location_set_assessment_id": assessment_id,
                "is_verified": True,
                "comment": "Assessment verified and approved"
            }
            response = test_client.post(
                "/api/v1/assessments/verifications/", 
                json=verification_data, 
                headers=admin_headers
            )
            assert response.status_code == 201

    def test_user_interaction_workflow(self, test_client, user_token):
        """Test complete user interaction workflow with locations."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Mock location for testing
        location_id = "test_location_id"
        
        # Step 1: User views location
        with patch('app.services.location_service.LocationService.get') as mock_get:
            mock_location = Location(
                location_id=location_id,
                location_name="Test Location",
                address="Test Address",
                latitude=41.2995,
                longitude=69.2401
            )
            mock_get.return_value = mock_location
            
            response = test_client.get(f"/api/v1/locations/{location_id}")
            assert response.status_code == 200
        
        # Step 2: User adds location to favorites
        response = test_client.post(
            f"/api/v1/interactions/locations/{location_id}/favorite", 
            headers=headers
        )
        assert response.status_code == 200
        
        # Step 3: User rates location
        rating_data = {"rating": 4}
        response = test_client.post(
            f"/api/v1/interactions/locations/{location_id}/rate", 
            json=rating_data, 
            headers=headers
        )
        assert response.status_code == 200
        
        # Step 4: User adds comment
        comment_data = {"comment": "Great accessibility features!"}
        response = test_client.post(
            f"/api/v1/interactions/locations/{location_id}/comment", 
            json=comment_data, 
            headers=headers
        )
        assert response.status_code == 201
        
        # Step 5: User views favorites
        response = test_client.get(
            "/api/v1/interactions/favorites", 
            headers=headers
        )
        assert response.status_code == 200
        favorites = response.json()
        assert any(fav["location_id"] == location_id for fav in favorites)

    def test_search_and_filter_workflow(self, test_client):
        """Test comprehensive search and filtering workflow."""
        # Step 1: Search locations by name
        response = test_client.get(
            "/api/v1/locations/", 
            params={"search": "test"}
        )
        assert response.status_code == 200
        
        # Step 2: Filter by category
        response = test_client.get(
            "/api/v1/locations/", 
            params={"category_id": 1}
        )
        assert response.status_code == 200
        
        # Step 3: Filter by geographical location
        response = test_client.get(
            "/api/v1/locations/", 
            params={"region_id": 1, "district_id": 1}
        )
        assert response.status_code == 200
        
        # Step 4: Complex filtering
        response = test_client.get(
            "/api/v1/locations/", 
            params={
                "category_id": 1,
                "region_id": 1,
                "status": "active"
            }
        )
        assert response.status_code == 200

    def test_admin_management_workflow(self, test_client, admin_token):
        """Test complete admin management workflow."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Step 1: Admin views dashboard statistics
        response = test_client.get(
            "/api/v1/statistics/dashboard", 
            headers=headers
        )
        assert response.status_code == 200
        dashboard_data = response.json()
        assert "total_locations" in dashboard_data
        assert "total_assessments" in dashboard_data
        
        # Step 2: Admin manages users
        response = test_client.get(
            "/api/v1/users/", 
            headers=headers,
            params={"limit": 10, "offset": 0}
        )
        assert response.status_code == 200
        
        # Step 3: Admin exports data
        response = test_client.get(
            "/api/v1/statistics/export", 
            headers=headers,
            params={"format": "csv"}
        )
        assert response.status_code == 200
        
        # Step 4: Admin views system health
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"

    def test_error_handling_and_validation_workflow(self, test_client, user_token):
        """Test error handling and validation across workflows."""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Test invalid data validation
        invalid_user_data = {
            "username": "",  # Empty username
            "email": "invalid_email",  # Invalid email format
            "password": "123"  # Too short password
        }
        response = test_client.post("/api/v1/users/register", json=invalid_user_data)
        assert response.status_code == 422  # Validation error
        
        # Test unauthorized access
        response = test_client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 403  # Forbidden - user not admin
        
        # Test not found resources
        response = test_client.get("/api/v1/locations/nonexistent_id")
        assert response.status_code == 404
        
        # Test duplicate creation
        duplicate_user_data = {
            "username": "testuser",  # Existing username
            "email": "newemail@test.com",
            "password": "password123",
            "first_name": "Test",
            "surname": "User"
        }
        response = test_client.post("/api/v1/users/register", json=duplicate_user_data)
        assert response.status_code == 400  # Bad request - duplicate

    def test_performance_and_pagination_workflow(self, test_client):
        """Test performance-related features and pagination."""
        # Test pagination
        response = test_client.get(
            "/api/v1/locations/", 
            params={"limit": 5, "offset": 0}
        )
        assert response.status_code == 200
        locations = response.json()
        assert len(locations) <= 5
        
        # Test sorting
        response = test_client.get(
            "/api/v1/locations/", 
            params={"sort_by": "created_at", "sort_order": "desc"}
        )
        assert response.status_code == 200
        
        # Test caching headers
        response = test_client.get("/api/v1/categories/")
        assert response.status_code == 200
        # Cache-related headers should be present for cacheable endpoints
        
        # Test rate limiting (if implemented)
        # Multiple rapid requests should trigger rate limiting
        for _ in range(20):
            response = test_client.get("/api/v1/locations/")
            if response.status_code == 429:  # Too Many Requests
                break

    @pytest.mark.asyncio
    async def test_concurrent_operations_workflow(self):
        """Test concurrent operations and race conditions."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Simulate concurrent user registrations
            tasks = []
            for i in range(5):
                user_data = {
                    "username": f"concurrent_user_{i}",
                    "email": f"user{i}@concurrent.com",
                    "password": "password123",
                    "first_name": "Concurrent",
                    "surname": f"User{i}"
                }
                task = client.post("/api/v1/users/register", json=user_data)
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check that most requests succeeded
            successful_requests = sum(
                1 for response in responses 
                if hasattr(response, 'status_code') and response.status_code == 201
            )
            assert successful_requests >= 4  # Allow for some potential conflicts

    def test_data_consistency_workflow(self, test_client, admin_token):
        """Test data consistency across related operations."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create related entities and verify relationships
        # This would involve creating categories, locations, assessments
        # and verifying that all relationships are maintained correctly
        
        # Step 1: Create category
        category_data = {"category_name": "Test Consistency", "description": "Test"}
        response = test_client.post("/api/v1/categories/", json=category_data, headers=headers)
        assert response.status_code == 201
        category_id = response.json()["category_id"]
        
        # Step 2: Verify category exists in listing
        response = test_client.get("/api/v1/categories/")
        assert response.status_code == 200
        categories = response.json()
        assert any(cat["category_id"] == category_id for cat in categories)
        
        # Step 3: Delete category
        response = test_client.delete(f"/api/v1/categories/{category_id}", headers=headers)
        assert response.status_code == 204
        
        # Step 4: Verify category no longer exists
        response = test_client.get(f"/api/v1/categories/{category_id}")
        assert response.status_code == 404 