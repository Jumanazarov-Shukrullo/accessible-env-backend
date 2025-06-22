"""Unit tests for LocationService - comprehensive testing of location management."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.domain.exceptions import LocationNotFound, ValidationError
from app.models.location_model import Location
from app.schemas.location_schema import LocationCreate, LocationUpdate
from app.services.location_service import LocationService


class TestLocationService:
    """Test suite for LocationService."""

    @pytest.fixture
    def mock_uow(self):
        """Mock Unit of Work."""
        uow = Mock()
        uow.locations = Mock()
        uow.commit = Mock()
        uow.rollback = Mock()
        uow.__enter__ = Mock(return_value=uow)
        uow.__exit__ = Mock(return_value=None)
        return uow

    @pytest.fixture
    def location_service(self, mock_uow):
        """Create LocationService instance with mocked dependencies."""
        return LocationService(uow=mock_uow)

    @pytest.fixture
    def sample_location(self):
        """Sample location for testing."""
        return Location(
            location_id=str(uuid4()),
            location_name="Test Library",
            address="123 Test Street",
            latitude=41.2995,
            longitude=69.2401,
            category_id=1,
            region_id=1,
            district_id=1,
            city_id=1,
            status="active",
            created_at=datetime.now(timezone.utc),
        )

    def test_create_location_success(self, location_service, mock_uow):
        """Test successful location creation."""
        location_data = LocationCreate(
            location_name="New Library",
            address="456 New Street",
            latitude=41.3000,
            longitude=69.2500,
            category_id=1,
            region_id=1,
            district_id=1,
            city_id=1,
            contact_info="+998901234567",
            website_url="https://example.com",
            description="A new public library",
        )

        created_location = Location(
            location_id=str(uuid4()),
            location_name=location_data.location_name,
            address=location_data.address,
            latitude=location_data.latitude,
            longitude=location_data.longitude,
            category_id=location_data.category_id,
            region_id=location_data.region_id,
            district_id=location_data.district_id,
            city_id=location_data.city_id,
        )

        mock_uow.locations.create.return_value = created_location

        result = location_service.create_location(location_data)

        assert result.location_name == location_data.location_name
        assert result.address == location_data.address
        mock_uow.locations.create.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_create_location_invalid_coordinates(self, location_service):
        """Test location creation with invalid coordinates."""
        location_data = LocationCreate(
            location_name="Invalid Location",
            address="Invalid Address",
            latitude=100.0,  # Invalid latitude
            longitude=200.0,  # Invalid longitude
            category_id=1,
            region_id=1,
            district_id=1,
            city_id=1,
        )

        with pytest.raises(ValidationError):
            location_service.create_location(location_data)

    def test_get_location_success(
        self, location_service, mock_uow, sample_location
    ):
        """Test successful location retrieval."""
        mock_uow.locations.get_by_id.return_value = sample_location

        result = location_service.get_location(sample_location.location_id)

        assert result.location_id == sample_location.location_id
        assert result.location_name == sample_location.location_name
        mock_uow.locations.get_by_id.assert_called_once_with(
            sample_location.location_id
        )

    def test_get_location_not_found(self, location_service, mock_uow):
        """Test location retrieval when location doesn't exist."""
        location_id = str(uuid4())
        mock_uow.locations.get_by_id.return_value = None

        with pytest.raises(LocationNotFound):
            location_service.get_location(location_id)

    def test_update_location_success(
        self, location_service, mock_uow, sample_location
    ):
        """Test successful location update."""
        update_data = LocationUpdate(
            location_name="Updated Library", description="Updated description"
        )

        mock_uow.locations.get_by_id.return_value = sample_location
        mock_uow.locations.update.return_value = sample_location

        result = location_service.update_location(
            sample_location.location_id, update_data
        )

        assert result is not None
        mock_uow.locations.update.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_delete_location_success(
        self, location_service, mock_uow, sample_location
    ):
        """Test successful location deletion."""
        mock_uow.locations.get_by_id.return_value = sample_location
        mock_uow.locations.delete.return_value = True

        result = location_service.delete_location(sample_location.location_id)

        assert result is True
        mock_uow.locations.delete.assert_called_once_with(
            sample_location.location_id
        )
        mock_uow.commit.assert_called_once()

    def test_search_locations(self, location_service, mock_uow):
        """Test location search functionality."""
        search_query = "library"
        mock_locations = [Mock(), Mock(), Mock()]
        mock_uow.locations.search.return_value = mock_locations

        results = location_service.search_locations(search_query)

        assert len(results) == 3
        mock_uow.locations.search.assert_called_once_with(search_query)

    def test_filter_by_category(self, location_service, mock_uow):
        """Test filtering locations by category."""
        category_id = 1
        mock_locations = [Mock(), Mock()]
        mock_uow.locations.filter_by_category.return_value = mock_locations

        results = location_service.filter_by_category(category_id)

        assert len(results) == 2
        mock_uow.locations.filter_by_category.assert_called_once_with(
            category_id
        )

    def test_filter_by_region(self, location_service, mock_uow):
        """Test filtering locations by region."""
        region_id = 1
        mock_locations = [Mock(), Mock(), Mock()]
        mock_uow.locations.filter_by_region.return_value = mock_locations

        results = location_service.filter_by_region(region_id)

        assert len(results) == 3
        mock_uow.locations.filter_by_region.assert_called_once_with(region_id)

    def test_get_nearby_locations(self, location_service, mock_uow):
        """Test getting nearby locations."""
        latitude = 41.2995
        longitude = 69.2401
        radius_km = 5.0
        mock_locations = [Mock()]
        mock_uow.locations.get_nearby.return_value = mock_locations

        results = location_service.get_nearby_locations(
            latitude, longitude, radius_km
        )

        assert len(results) == 1
        mock_uow.locations.get_nearby.assert_called_once_with(
            latitude, longitude, radius_km
        )

    def test_get_location_statistics(self, location_service, mock_uow):
        """Test getting location statistics."""
        mock_stats = {
            "total_locations": 100,
            "active_locations": 85,
            "by_category": {"Library": 20, "Hospital": 15},
            "by_region": {"Tashkent": 50, "Samarkand": 30},
        }
        mock_uow.locations.get_statistics.return_value = mock_stats

        results = location_service.get_location_statistics()

        assert results["total_locations"] == 100
        assert results["active_locations"] == 85
        mock_uow.locations.get_statistics.assert_called_once()

    def test_bulk_update_status(self, location_service, mock_uow):
        """Test bulk status update for multiple locations."""
        location_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        new_status = "inactive"

        mock_uow.locations.bulk_update_status.return_value = 3

        result = location_service.bulk_update_status(location_ids, new_status)

        assert result == 3
        mock_uow.locations.bulk_update_status.assert_called_once_with(
            location_ids, new_status
        )
        mock_uow.commit.assert_called_once()

    @patch("app.services.location_service.cache")
    def test_caching_integration(self, mock_cache, location_service, mock_uow):
        """Test cache invalidation on location operations."""
        location_data = LocationCreate(
            location_name="Cached Location",
            address="Cache Street",
            latitude=41.2995,
            longitude=69.2401,
            category_id=1,
            region_id=1,
            district_id=1,
            city_id=1,
        )

        created_location = Location(
            location_id=str(uuid4()), **location_data.dict()
        )
        mock_uow.locations.create.return_value = created_location

        location_service.create_location(location_data)

        mock_cache.invalidate.assert_called_with("locations:")

    def test_validate_coordinates(self, location_service):
        """Test coordinate validation."""
        # Valid coordinates
        assert location_service._validate_coordinates(41.2995, 69.2401) is True

        # Invalid latitude
        with pytest.raises(ValidationError):
            location_service._validate_coordinates(100.0, 69.2401)

        # Invalid longitude
        with pytest.raises(ValidationError):
            location_service._validate_coordinates(41.2995, 200.0)

    def test_get_paginated_locations(self, location_service, mock_uow):
        """Test paginated location retrieval."""
        mock_locations = [Mock() for _ in range(10)]
        total_count = 100
        mock_uow.locations.get_paginated.return_value = (
            mock_locations,
            total_count,
        )

        results, total = location_service.get_paginated_locations(
            limit=10, offset=0
        )

        assert len(results) == 10
        assert total == 100
        mock_uow.locations.get_paginated.assert_called_once_with(
            limit=10, offset=0
        )

    def test_error_handling_database_failure(self, location_service, mock_uow):
        """Test error handling when database operations fail."""
        location_data = LocationCreate(
            location_name="Error Location",
            address="Error Street",
            latitude=41.2995,
            longitude=69.2401,
            category_id=1,
            region_id=1,
            district_id=1,
            city_id=1,
        )

        mock_uow.locations.create.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            location_service.create_location(location_data)

        mock_uow.rollback.assert_called_once()
