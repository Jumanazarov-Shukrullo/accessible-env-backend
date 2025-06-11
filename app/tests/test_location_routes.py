import pytest
import json
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


class TestLocationRoutes:
    """Test suite for location API routes."""

    def test_create_location_success(self, client: TestClient, admin_auth_headers, sample_category, 
                                   sample_region, sample_district, sample_city):
        """Test successful location creation."""
        # Arrange
        location_data = {
            "location_name": "New Location",
            "address": "123 New Street",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "category_id": sample_category.category_id,
            "region_id": sample_region.region_id,
            "district_id": sample_district.district_id,
            "city_id": sample_city.city_id,
            "contact_info": "555-0123",
            "website_url": "https://newlocation.com",
            "description": "A new test location"
        }
        
        # Act
        response = client.post("/api/v1/locations/", json=location_data, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["location_name"] == "New Location"
        assert data["address"] == "123 New Street"

    def test_create_location_unauthorized(self, client: TestClient, auth_headers):
        """Test location creation fails for unauthorized user."""
        # Arrange
        location_data = {
            "location_name": "New Location",
            "address": "123 New Street",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "category_id": 1,
            "region_id": 1,
            "district_id": 1,
            "city_id": 1
        }
        
        # Act
        response = client.post("/api/v1/locations/", json=location_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_create_location_invalid_coordinates(self, client: TestClient, admin_auth_headers):
        """Test location creation fails with invalid coordinates."""
        # Arrange
        location_data = {
            "location_name": "Invalid Location",
            "address": "Invalid Street",
            "latitude": 200.0,  # Invalid latitude
            "longitude": -74.0060,
            "category_id": 1,
            "region_id": 1,
            "district_id": 1,
            "city_id": 1
        }
        
        # Act
        response = client.post("/api/v1/locations/", json=location_data, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 422

    def test_get_location_by_id_success(self, client: TestClient, sample_location):
        """Test successful location retrieval by ID."""
        # Act
        response = client.get(f"/api/v1/locations/{sample_location.location_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["location_id"] == sample_location.location_id
        assert data["location_name"] == sample_location.location_name

    def test_get_location_by_id_not_found(self, client: TestClient):
        """Test location retrieval fails when not found."""
        # Act
        response = client.get("/api/v1/locations/nonexistent-id")
        
        # Assert
        assert response.status_code == 404

    def test_get_locations_success(self, client: TestClient):
        """Test successful locations list retrieval."""
        # Act
        response = client.get("/api/v1/locations/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data

    def test_get_locations_with_pagination(self, client: TestClient):
        """Test locations retrieval with pagination."""
        # Act
        response = client.get("/api/v1/locations/?page=1&size=5")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5

    def test_get_locations_with_filters(self, client: TestClient, sample_category):
        """Test locations retrieval with filters."""
        # Act
        response = client.get(f"/api/v1/locations/?category_id={sample_category.category_id}&status=active")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_search_locations_success(self, client: TestClient):
        """Test successful location search."""
        # Arrange
        search_params = {
            "query": "test",
            "limit": 10,
            "offset": 0
        }
        
        # Act
        response = client.get("/api/v1/locations/search", params=search_params)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data

    def test_search_locations_with_coordinates(self, client: TestClient):
        """Test location search with coordinates and radius."""
        # Arrange
        search_params = {
            "center_lat": 40.7128,
            "center_lng": -74.0060,
            "radius_km": 10,
            "limit": 20
        }
        
        # Act
        response = client.get("/api/v1/locations/search", params=search_params)
        
        # Assert
        assert response.status_code == 200

    def test_update_location_success(self, client: TestClient, admin_auth_headers, sample_location):
        """Test successful location update."""
        # Arrange
        update_data = {
            "location_name": "Updated Location",
            "address": "Updated Address",
            "status": "inactive"
        }
        
        # Act
        response = client.put(f"/api/v1/locations/{sample_location.location_id}", 
                            json=update_data, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["location_name"] == "Updated Location"

    def test_update_location_unauthorized(self, client: TestClient, auth_headers, sample_location):
        """Test location update fails for unauthorized user."""
        # Arrange
        update_data = {"location_name": "Updated Location"}
        
        # Act
        response = client.put(f"/api/v1/locations/{sample_location.location_id}", 
                            json=update_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_update_location_not_found(self, client: TestClient, admin_auth_headers):
        """Test location update fails when location not found."""
        # Arrange
        update_data = {"location_name": "Updated Location"}
        
        # Act
        response = client.put("/api/v1/locations/nonexistent-id", 
                            json=update_data, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 404

    def test_update_location_details_success(self, client: TestClient, admin_auth_headers, sample_location):
        """Test successful location details update."""
        # Arrange
        details_data = {
            "contact_info": "555-9999",
            "website_url": "https://updated.com",
            "description": "Updated description"
        }
        
        # Act
        response = client.put(f"/api/v1/locations/{sample_location.location_id}/details", 
                            json=details_data, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["contact_info"] == "555-9999"

    def test_delete_location_success(self, client: TestClient, admin_auth_headers, sample_location):
        """Test successful location deletion."""
        # Act
        response = client.delete(f"/api/v1/locations/{sample_location.location_id}", 
                               headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Location deleted successfully"

    def test_delete_location_unauthorized(self, client: TestClient, auth_headers, sample_location):
        """Test location deletion fails for unauthorized user."""
        # Act
        response = client.delete(f"/api/v1/locations/{sample_location.location_id}", 
                               headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_delete_location_not_found(self, client: TestClient, admin_auth_headers):
        """Test location deletion fails when location not found."""
        # Act
        response = client.delete("/api/v1/locations/nonexistent-id", 
                               headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 404

    def test_add_location_to_favourites_success(self, client: TestClient, auth_headers, sample_location):
        """Test successful addition to favourites."""
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/favourites", 
                             headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Location added to favourites"

    def test_add_location_to_favourites_unauthorized(self, client: TestClient, sample_location):
        """Test favourite addition fails without authentication."""
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/favourites")
        
        # Assert
        assert response.status_code == 401

    def test_add_location_to_favourites_already_exists(self, client: TestClient, auth_headers, sample_location):
        """Test adding to favourites when already exists."""
        # First add to favourites
        client.post(f"/api/v1/locations/{sample_location.location_id}/favourites", headers=auth_headers)
        
        # Try to add again
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/favourites", 
                             headers=auth_headers)
        
        # Assert
        assert response.status_code == 409

    def test_remove_location_from_favourites_success(self, client: TestClient, auth_headers, sample_location):
        """Test successful removal from favourites."""
        # First add to favourites
        client.post(f"/api/v1/locations/{sample_location.location_id}/favourites", headers=auth_headers)
        
        # Then remove
        response = client.delete(f"/api/v1/locations/{sample_location.location_id}/favourites", 
                               headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Location removed from favourites"

    def test_remove_location_from_favourites_not_exists(self, client: TestClient, auth_headers, sample_location):
        """Test removing from favourites when not in favourites."""
        # Act
        response = client.delete(f"/api/v1/locations/{sample_location.location_id}/favourites", 
                               headers=auth_headers)
        
        # Assert
        assert response.status_code == 404

    def test_rate_location_success(self, client: TestClient, auth_headers, sample_location):
        """Test successful location rating."""
        # Arrange
        rating_data = {"rating_value": 8}
        
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/ratings", 
                             json=rating_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Location rated successfully"

    def test_rate_location_invalid_value(self, client: TestClient, auth_headers, sample_location):
        """Test location rating fails with invalid value."""
        # Arrange
        rating_data = {"rating_value": 15}  # Invalid rating (should be 0-10)
        
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/ratings", 
                             json=rating_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 422

    def test_rate_location_unauthorized(self, client: TestClient, sample_location):
        """Test location rating fails without authentication."""
        # Arrange
        rating_data = {"rating_value": 8}
        
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/ratings", 
                             json=rating_data)
        
        # Assert
        assert response.status_code == 401

    def test_get_user_favourites_success(self, client: TestClient, auth_headers):
        """Test successful retrieval of user favourites."""
        # Act
        response = client.get("/api/v1/locations/favourites", headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_user_favourites_with_pagination(self, client: TestClient, auth_headers):
        """Test user favourites retrieval with pagination."""
        # Act
        response = client.get("/api/v1/locations/favourites?page=1&size=5", headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5

    def test_get_user_favourites_unauthorized(self, client: TestClient):
        """Test favourites retrieval fails without authentication."""
        # Act
        response = client.get("/api/v1/locations/favourites")
        
        # Assert
        assert response.status_code == 401

    def test_upload_location_image_success(self, client: TestClient, admin_auth_headers, 
                                         sample_location, mock_minio):
        """Test successful location image upload."""
        # Arrange
        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}
        data = {"description": "Test image"}
        
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/images", 
                             files=files, data=data, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 201
        result = response.json()
        assert "image_url" in result

    def test_upload_location_image_unauthorized(self, client: TestClient, auth_headers, sample_location):
        """Test location image upload fails for unauthorized user."""
        # Arrange
        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}
        
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/images", 
                             files=files, headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_upload_location_image_invalid_format(self, client: TestClient, admin_auth_headers, sample_location):
        """Test location image upload fails with invalid file format."""
        # Arrange
        files = {"file": ("test.txt", b"not an image", "text/plain")}
        
        # Act
        response = client.post(f"/api/v1/locations/{sample_location.location_id}/images", 
                             files=files, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 400

    def test_get_location_images_success(self, client: TestClient, sample_location):
        """Test successful retrieval of location images."""
        # Act
        response = client.get(f"/api/v1/locations/{sample_location.location_id}/images")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_delete_location_image_success(self, client: TestClient, admin_auth_headers, sample_location):
        """Test successful location image deletion."""
        # Arrange
        image_id = 1
        
        # Act
        response = client.delete(f"/api/v1/locations/{sample_location.location_id}/images/{image_id}", 
                               headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Image deleted successfully"

    def test_delete_location_image_unauthorized(self, client: TestClient, auth_headers, sample_location):
        """Test location image deletion fails for unauthorized user."""
        # Arrange
        image_id = 1
        
        # Act
        response = client.delete(f"/api/v1/locations/{sample_location.location_id}/images/{image_id}", 
                               headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_bulk_update_location_status_success(self, client: TestClient, admin_auth_headers):
        """Test successful bulk location status update."""
        # Arrange
        update_data = {
            "location_ids": ["id1", "id2", "id3"],
            "status": "inactive"
        }
        
        # Act
        response = client.put("/api/v1/locations/bulk-status", 
                            json=update_data, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "updated_count" in data

    def test_bulk_update_location_status_unauthorized(self, client: TestClient, auth_headers):
        """Test bulk status update fails for unauthorized user."""
        # Arrange
        update_data = {
            "location_ids": ["id1", "id2"],
            "status": "inactive"
        }
        
        # Act
        response = client.put("/api/v1/locations/bulk-status", 
                            json=update_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_get_location_statistics_success(self, client: TestClient, sample_location):
        """Test successful location statistics retrieval."""
        # Act
        response = client.get(f"/api/v1/locations/{sample_location.location_id}/statistics")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "accessibility_score" in data
        assert "total_reviews" in data
        assert "average_rating" in data

    def test_get_location_nearby_success(self, client: TestClient, sample_location):
        """Test successful nearby locations retrieval."""
        # Arrange
        params = {
            "latitude": sample_location.latitude,
            "longitude": sample_location.longitude,
            "radius_km": 5,
            "limit": 10
        }
        
        # Act
        response = client.get("/api/v1/locations/nearby", params=params)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_location_nearby_invalid_coordinates(self, client: TestClient):
        """Test nearby locations fails with invalid coordinates."""
        # Arrange
        params = {
            "latitude": 200.0,  # Invalid latitude
            "longitude": -74.0060,
            "radius_km": 5
        }
        
        # Act
        response = client.get("/api/v1/locations/nearby", params=params)
        
        # Assert
        assert response.status_code == 422

    def test_get_locations_by_category_success(self, client: TestClient, sample_category):
        """Test successful locations retrieval by category."""
        # Act
        response = client.get(f"/api/v1/locations/category/{sample_category.category_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_locations_by_region_success(self, client: TestClient, sample_region):
        """Test successful locations retrieval by region."""
        # Act
        response = client.get(f"/api/v1/locations/region/{sample_region.region_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_export_locations_csv_success(self, client: TestClient, admin_auth_headers):
        """Test successful location export as CSV."""
        # Act
        response = client.get("/api/v1/locations/export/csv", headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_export_locations_json_success(self, client: TestClient, admin_auth_headers):
        """Test successful location export as JSON."""
        # Act
        response = client.get("/api/v1/locations/export/json", headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_export_locations_unauthorized(self, client: TestClient, auth_headers):
        """Test location export fails for unauthorized user."""
        # Act
        response = client.get("/api/v1/locations/export/csv", headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_import_locations_success(self, client: TestClient, admin_auth_headers):
        """Test successful location import."""
        # Arrange
        csv_data = "location_name,address,latitude,longitude,category_id,region_id,district_id\nTest,123 St,40.7,-74.0,1,1,1"
        files = {"file": ("locations.csv", csv_data.encode(), "text/csv")}
        
        # Act
        response = client.post("/api/v1/locations/import", 
                             files=files, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "imported_count" in data

    def test_import_locations_unauthorized(self, client: TestClient, auth_headers):
        """Test location import fails for unauthorized user."""
        # Arrange
        csv_data = "location_name,address,latitude,longitude\nTest,123 St,40.7,-74.0"
        files = {"file": ("locations.csv", csv_data.encode(), "text/csv")}
        
        # Act
        response = client.post("/api/v1/locations/import", 
                             files=files, headers=auth_headers)
        
        # Assert
        assert response.status_code == 403

    def test_import_locations_invalid_format(self, client: TestClient, admin_auth_headers):
        """Test location import fails with invalid file format."""
        # Arrange
        files = {"file": ("test.txt", b"not csv content", "text/plain")}
        
        # Act
        response = client.post("/api/v1/locations/import", 
                             files=files, headers=admin_auth_headers)
        
        # Assert
        assert response.status_code == 400 