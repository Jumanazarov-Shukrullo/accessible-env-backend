from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain.unit_of_work import UnitOfWork
from app.models.location_model import (
    Favourite,
    Location,
    LocationDetails,
    LocationStats,
)
from app.models.rating_model import LocationRating
from app.schemas.location_schema import (
    LocationCreate,
    LocationDetailsUpdate,
    LocationFilter,
    LocationSearch,
    LocationUpdate,
)
from app.services.location_service import LocationService


class TestLocationService:
    """Test suite for LocationService class."""

    @pytest.fixture
    def mock_uow(self):
        """Create a mock unit of work."""
        mock_uow = Mock(spec=UnitOfWork)
        mock_uow.session = Mock(spec=Session)
        mock_uow.commit = Mock()
        mock_uow.rollback = Mock()
        return mock_uow

    @pytest.fixture
    def location_service(self, mock_uow):
        """Create LocationService instance with mocked dependencies."""
        return LocationService(mock_uow)

    def test_create_location_success(
        self,
        location_service,
        mock_uow,
        sample_user,
        sample_category,
        sample_region,
        sample_district,
        sample_city,
    ):
        """Test successful location creation."""
        # Arrange
        location_data = LocationCreate(
            location_name="Test Location",
            address="123 Test Street",
            latitude=Decimal("40.7128"),
            longitude=Decimal("-74.0060"),
            category_id=sample_category.category_id,
            region_id=sample_region.region_id,
            district_id=sample_district.district_id,
            city_id=sample_city.city_id,
            contact_info="555-0123",
            website_url="https://testlocation.com",
            description="A test location",
        )

        mock_location = Mock(spec=Location)
        mock_location.location_id = "test-id"

        with patch.object(
            location_service, "get_location_with_details"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = location_service.create_location(
                location_data, sample_user
            )

            # Assert
            assert result is not None
            mock_uow.session.add.assert_called()
            mock_uow.commit.assert_called()

    def test_get_location_with_details_success(
        self, location_service, mock_uow, sample_location
    ):
        """Test successful location retrieval with details."""
        # Arrange
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            sample_location)

        # Act
        result = location_service.get_location_with_details(
            sample_location.location_id
        )

        # Assert
        assert result is not None
        mock_uow.session.query.assert_called()

    def test_get_location_with_details_not_found(
        self, location_service, mock_uow
    ):
        """Test location retrieval returns None when not found."""
        # Arrange
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            None)

        # Act
        result = location_service.get_location_with_details("nonexistent-id")

        # Assert
        assert result is None

    def test_get_location_detail_success(
        self, location_service, mock_uow, sample_location
    ):
        """Test successful detailed location retrieval."""
        # Arrange
        mock_location = Mock(spec=Location)
        mock_location.location_id = sample_location.location_id
        mock_location.location_name = "Test Location"
        mock_location.address = "123 Test Street"
        mock_location.latitude = Decimal("40.7128")
        mock_location.longitude = Decimal("-74.0060")
        mock_location.category_id = 1
        mock_location.region_id = 1
        mock_location.district_id = 1
        mock_location.city_id = 1
        mock_location.status = "active"
        mock_location.created_at = "2023-01-01"
        mock_location.updated_at = "2023-01-01"
        mock_location.details = Mock()
        mock_location.stats = Mock()
        mock_location.images = []
        mock_location.category = Mock()
        mock_location.category.category_name = "Test Category"
        mock_location.region = Mock()
        mock_location.region.region_name = "Test Region"
        mock_location.district = Mock()
        mock_location.district.district_name = "Test District"
        mock_location.city = Mock()
        mock_location.city.city_name = "Test City"

        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_location)

        # Act
        result = location_service.get_location_detail(
            sample_location.location_id
        )

        # Assert
        assert result is not None
        assert result.location_name == "Test Location"

    def test_update_location_core_success(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test successful core location update."""
        # Arrange
        location_update = LocationUpdate(
            location_name="Updated Location", address="456 Updated Street"
        )
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            sample_location)

        with patch.object(
            location_service, "get_location_with_details"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = location_service.update_location_core(
                sample_location.location_id, location_update, sample_user
            )

            # Assert
            assert result is not None
            mock_uow.commit.assert_called()

    def test_update_location_core_not_found(
        self, location_service, mock_uow, sample_user
    ):
        """Test location update fails when location not found."""
        # Arrange
        location_update = LocationUpdate(location_name="Updated Location")
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise HTTPException
            location_service.update_location_core(
                "nonexistent-id", location_update, sample_user
            )

    def test_update_location_details_success(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test successful location details update."""
        # Arrange
        details_update = LocationDetailsUpdate(
            contact_info="555-9999", website_url="https://updated.com"
        )
        mock_details = Mock(spec=LocationDetails)
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_details)

        with patch.object(
            location_service, "get_location_with_details"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = location_service.update_location_details(
                sample_location.location_id, details_update, sample_user
            )

            # Assert
            assert result is not None
            mock_uow.commit.assert_called()

    def test_update_location_details_creates_new(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test location details update creates new details if none exist."""
        # Arrange
        details_update = LocationDetailsUpdate(contact_info="555-1234")
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        with patch.object(
            location_service, "get_location_with_details"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            location_service.update_location_details(
                sample_location.location_id, details_update, sample_user
            )

            # Assert
            mock_uow.session.add.assert_called()
            mock_uow.commit.assert_called()

    def test_search_locations_success(self, location_service, mock_uow):
        """Test successful location search."""
        # Arrange
        search = LocationSearch(
            query="test",
            center_lat=Decimal("40.7128"),
            center_lng=Decimal("-74.0060"),
            radius_km=10,
            limit=10,
            offset=0,
        )

        mock_locations = [Mock(spec=Location) for _ in range(3)]
        for i, loc in enumerate(mock_locations):
            loc.location_id = f"loc_{i}"
            loc.location_name = f"Location {i}"
            loc.address = f"Address {i}"
            loc.latitude = Decimal("40.7128")
            loc.longitude = Decimal("-74.0060")
            loc.stats = Mock()
            loc.stats.accessibility_score = Decimal("7.5")
            loc.stats.average_rating = Decimal("4.0")
            loc.category = Mock()
            loc.category.category_name = "Test Category"
            loc.images = []

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_locations

        mock_uow.session.query.return_value = mock_query

        # Act
        results, total = location_service.search_locations(search)

        # Assert
        assert len(results) == 3
        assert total == 3

    def test_get_locations_paginated_success(self, location_service, mock_uow):
        """Test successful paginated location retrieval."""
        # Arrange
        filters = LocationFilter(category_id=1, status="active")

        mock_locations = [Mock(spec=Location) for _ in range(5)]
        for i, loc in enumerate(mock_locations):
            loc.location_id = f"loc_{i}"
            loc.location_name = f"Location {i}"
            loc.address = f"Address {i}"
            loc.latitude = Decimal("40.7128")
            loc.longitude = Decimal("-74.0060")
            loc.status = "active"
            loc.stats = Mock()
            loc.stats.accessibility_score = Decimal("7.5")
            loc.stats.average_rating = Decimal("4.0")
            loc.stats.total_reviews = 10
            loc.category = Mock()
            loc.category.category_name = "Test Category"
            loc.region = Mock()
            loc.region.region_name = "Test Region"
            loc.images = []

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.count.return_value = 5
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_locations

        mock_uow.session.query.return_value = mock_query

        # Act
        result = location_service.get_locations_paginated(
            page=1, size=10, filters=filters
        )

        # Assert
        assert len(result.items) == 5
        assert result.total == 5
        assert result.page == 1
        assert result.size == 10

    def test_add_location_to_favourites_success(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test successful addition to favourites."""
        # Arrange
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None  # Not already in favourites
        )

        # Act
        result = location_service.add_location_to_favourites(
            sample_location.location_id, sample_user.user_id
        )

        # Assert
        assert result is True
        mock_uow.session.add.assert_called()
        mock_uow.commit.assert_called()

    def test_add_location_to_favourites_already_exists(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test adding to favourites when already in favourites."""
        # Arrange
        existing_favourite = Mock(spec=Favourite)
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            existing_favourite)

        # Act
        result = location_service.add_location_to_favourites(
            sample_location.location_id, sample_user.user_id
        )

        # Assert
        assert result is False

    def test_remove_location_from_favourites_success(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test successful removal from favourites."""
        # Arrange
        existing_favourite = Mock(spec=Favourite)
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            existing_favourite)

        # Act
        result = location_service.remove_location_from_favourites(
            sample_location.location_id, sample_user.user_id
        )

        # Assert
        assert result is True
        mock_uow.session.delete.assert_called_with(existing_favourite)
        mock_uow.commit.assert_called()

    def test_remove_location_from_favourites_not_exists(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test removing from favourites when not in favourites."""
        # Arrange
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        # Act
        result = location_service.remove_location_from_favourites(
            sample_location.location_id, sample_user.user_id
        )

        # Assert
        assert result is False

    def test_rate_location_new_rating(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test rating a location for the first time."""
        # Arrange
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None  # No existing rating
        )

        # Mock stats setup: Mock(spec=LocationStats)
        mock_ratings = [(8,), (7,), (9,)]  # Mock rating values

        with patch.object(
            location_service, "_update_location_rating_stats"
        ) as mock_update:
            mock_uow.session.query.return_value.filter.return_value.all.return_value = (
                mock_ratings)

            # Act
            result = location_service.rate_location(
                sample_location.location_id, sample_user.user_id, 8
            )

            # Assert
            assert result is True
            mock_uow.session.add.assert_called()
            mock_uow.commit.assert_called()

    def test_rate_location_update_existing(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test updating an existing rating."""
        # Arrange
        existing_rating = Mock(spec=LocationRating)
        existing_rating.rating_value = 7
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            existing_rating)

        with patch.object(
            location_service, "_update_location_rating_stats"
        ) as mock_update:
            # Act
            result = location_service.rate_location(
                sample_location.location_id, sample_user.user_id, 9
            )

            # Assert
            assert result is True
            assert existing_rating.rating_value == 9
            mock_uow.commit.assert_called()

    def test_bulk_update_location_status_success(
        self, location_service, mock_uow, sample_user
    ):
        """Test successful bulk status update."""
        # Arrange
        location_ids = ["id1", "id2", "id3"]
        status = "inactive"

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.update.return_value = 3
        mock_uow.session.query.return_value = mock_query

        # Act
        result = location_service.bulk_update_location_status(
            location_ids, status, sample_user
        )

        # Assert
        assert result == 3
        mock_uow.commit.assert_called()

    def test_delete_location_success(
        self, location_service, mock_uow, sample_location, sample_user
    ):
        """Test successful location deletion."""
        # Arrange
        mock_location = Mock(spec=Location)
        mock_location.location_name = "Test Location"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_location)

        # Act
        result = location_service.delete_location(
            sample_location.location_id, sample_user
        )

        # Assert
        assert result is True
        mock_uow.session.delete.assert_called_with(mock_location)
        mock_uow.commit.assert_called()

    def test_delete_location_not_found(
        self, location_service, mock_uow, sample_user
    ):
        """Test location deletion fails when location not found."""
        # Arrange
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise HTTPException
            location_service.delete_location("nonexistent-id", sample_user)

    def test_get_user_favourites_success(
        self, location_service, mock_uow, sample_user
    ):
        """Test successful retrieval of user's favourite locations."""
        # Arrange
        mock_locations = [Mock(spec=Location) for _ in range(3)]
        for i, loc in enumerate(mock_locations):
            loc.location_id = f"fav_{i}"
            loc.location_name = f"Favourite {i}"
            loc.address = f"Fav Address {i}"
            loc.latitude = Decimal("40.7128")
            loc.longitude = Decimal("-74.0060")
            loc.status = "active"
            loc.stats = Mock()
            loc.stats.accessibility_score = Decimal("8.0")
            loc.stats.average_rating = Decimal("4.5")
            loc.stats.total_reviews = 15
            loc.category = Mock()
            loc.category.category_name = "Favourite Category"
            loc.region = Mock()
            loc.region.region_name = "Favourite Region"
            loc.images = []

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_locations

        mock_uow.session.query.return_value = mock_query

        # Act
        result = location_service.get_user_favourites(
            sample_user.user_id, page=1, size=10
        )

        # Assert
        assert len(result.items) == 3
        assert result.total == 3

    def test_update_location_rating_stats(
        self, location_service, mock_uow, sample_location
    ):
        """Test location rating statistics update."""
        # Arrange
        # Mock stats setup: Mock(spec=LocationStats)
        mock_uow.session.query.return_value.filter.return_value.first.return_value = ()
            None  # Mock stats placeholder)

        # Mock ratings query
        mock_ratings = [(8,), (7,), (9,), (6,)]
        rating_query = Mock()
        rating_query.filter.return_value = rating_query
        rating_query.all.return_value = mock_ratings

        mock_uow.session.query.side_effect = [Mock(), rating_query]

        # Act
        location_service._update_location_rating_stats(
            sample_location.location_id, 8
        )

        # Assert
        assert None  # Mock stats placeholder.total_ratings == 4
        assert None  # Mock stats placeholder.average_rating == 7.5  # (8+7+9+6)/4

    def test_update_location_rating_stats_no_stats(
        self, location_service, mock_uow, sample_location
    ):
        """Test rating stats update when no stats record exists."""
        # Arrange
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        # Act
        location_service._update_location_rating_stats(
            sample_location.location_id, 8
        )

        # Assert - Should not raise an error, just return early

    def test_location_search_with_filters(self, location_service, mock_uow):
        """Test location search with various filters."""
        # Arrange
        search = LocationSearch(
            filters=LocationFilter(
                category_id=1,
                region_id=2,
                status="active",
                min_accessibility_score=7.0,
                max_accessibility_score=9.0,
            ),
            limit=20,
            offset=0,
        )

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [Mock(), Mock()]

        mock_uow.session.query.return_value = mock_query

        # Act
        results, total = location_service.search_locations(search)

        # Assert
        assert len(results) == 2
        assert total == 2
        # Verify filter calls were made
        assert mock_query.filter.call_count >= 4  # Multiple filter calls

    def test_location_search_with_text_query(self, location_service, mock_uow):
        """Test location search with text query."""
        # Arrange
        search = LocationSearch(query="test location", limit=10, offset=0)

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [Mock()]

        mock_uow.session.query.return_value = mock_query

        # Act
        results, total = location_service.search_locations(search)

        # Assert
        assert len(results) == 1
        assert total == 1
