from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain.unit_of_work import UnitOfWork
from app.models.assessment_model import (
    AccessibilityCriteria,
    AssessmentSet,
    LocationSetAssessment,
)
from app.schemas.assessment_schema import (
    AssessmentCreate,
    AssessmentSetCreate,
    AssessmentUpdate,
)
from app.services.assessment_service import AssessmentService


class TestAssessmentService:
    """Test suite for AssessmentService class."""

    @pytest.fixture
    def mock_uow(self):
        """Create a mock unit of work."""
        mock_uow = Mock(spec=UnitOfWork)
        mock_uow.session = Mock(spec=Session)
        mock_uow.commit = Mock()
        mock_uow.rollback = Mock()
        return mock_uow

    @pytest.fixture
    def assessment_service(self, mock_uow):
        """Create AssessmentService instance with mocked dependencies."""
        return AssessmentService(mock_uow)

    def test_create_assessment_success(
        self, assessment_service, mock_uow, sample_location, sample_user
    ):
        """Test successful assessment creation."""
        # Arrange
        assessment_data = AssessmentCreate(
            location_id=sample_location.location_id,
            set_id=1,
            overall_score=8.5,
            notes="Good accessibility",
            responses=[
                {"criterion_id": 1, "score": 8, "comments": "Good entrance"},
                {
                    "criterion_id": 2,
                    "score": 9,
                    "comments": "Excellent parking",
                },
            ],
        )

        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessment_id = 1

        with patch.object(
            assessment_service, "get_assessment_by_id"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = assessment_service.create_assessment(
                assessment_data, sample_user
            )

            # Assert
            assert result is not None
            mock_uow.session.add.assert_called()
            mock_uow.commit.assert_called()

    def test_get_assessment_by_id_success(self, assessment_service, mock_uow):
        """Test successful assessment retrieval by ID."""
        # Arrange
        assessment_id = 1
        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessment_id = assessment_id
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        # Act
        result = assessment_service.get_assessment_by_id(assessment_id)

        # Assert
        assert result == mock_assessment

    def test_get_assessment_by_id_not_found(
        self, assessment_service, mock_uow
    ):
        """Test assessment retrieval returns None when not found."""
        # Arrange
        assessment_id = 999
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            None)

        # Act
        result = assessment_service.get_assessment_by_id(assessment_id)

        # Assert
        assert result is None

    def test_get_assessments_by_location_success(
        self, assessment_service, mock_uow, sample_location
    ):
        """Test successful retrieval of assessments by location."""
        # Arrange
        mock_assessments = [Mock(spec=LocationSetAssessment) for _ in range(3)]
        for i, assessment in enumerate(mock_assessments):
            assessment.assessment_id = i + 1
            assessment.overall_score = 7.5 + i
            assessment.status = "verified"
            assessment.assessor = Mock()
            assessment.assessor.username = f"assessor_{i}"
            assessment.set = Mock()
            assessment.set.set_name = f"Set {i}"

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_assessments

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.get_assessments_by_location(
            sample_location.location_id, page=1, size=10
        )

        # Assert
        assert len(result.items) == 3
        assert result.total == 3

    def test_get_assessments_by_user_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful retrieval of assessments by user."""
        # Arrange
        mock_assessments = [Mock(spec=LocationSetAssessment) for _ in range(2)]
        for i, assessment in enumerate(mock_assessments):
            assessment.assessment_id = i + 1
            assessment.location_id = f"loc_{i}"
            assessment.overall_score = 8.0 + i
            assessment.status = "submitted"
            assessment.location = Mock()
            assessment.location.location_name = f"Location {i}"

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_assessments

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.get_assessments_by_user(
            sample_user.user_id, page=1, size=10
        )

        # Assert
        assert len(result.items) == 2
        assert result.total == 2

    def test_update_assessment_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful assessment update."""
        # Arrange
        assessment_id = 1
        assessment_update = AssessmentUpdate(
            overall_score=9.0, notes="Updated notes", status="submitted"
        )

        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessment_id = assessment_id
        mock_assessment.assessor_id = sample_user.user_id
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        with patch.object(
            assessment_service, "get_assessment_by_id"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = assessment_service.update_assessment(
                assessment_id, assessment_update, sample_user
            )

            # Assert
            assert result is not None
            assert mock_assessment.overall_score == 9.0
            assert mock_assessment.notes == "Updated notes"
            mock_uow.commit.assert_called()

    def test_update_assessment_unauthorized(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test assessment update fails for unauthorized user."""
        # Arrange
        assessment_id = 1
        assessment_update = AssessmentUpdate(overall_score=9.0)

        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessor_id = "different_user_id"  # Different user
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise HTTPException
            assessment_service.update_assessment(
                assessment_id, assessment_update, sample_user
            )

    def test_submit_assessment_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful assessment submission."""
        # Arrange
        assessment_id = 1
        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessment_id = assessment_id
        mock_assessment.assessor_id = sample_user.user_id
        mock_assessment.status = "draft"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        with patch.object(
            assessment_service, "get_assessment_by_id"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = assessment_service.submit_assessment(
                assessment_id, sample_user
            )

            # Assert
            assert result is True
            assert mock_assessment.status == "submitted"
            mock_uow.commit.assert_called()

    def test_submit_assessment_already_submitted(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test assessment submission fails when already submitted."""
        # Arrange
        assessment_id = 1
        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.status = "submitted"  # Already submitted
        mock_assessment.assessor_id = sample_user.user_id
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise HTTPException
            assessment_service.submit_assessment(assessment_id, sample_user)

    def test_verify_assessment_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful assessment verification."""
        # Arrange
        assessment_id = 1
        verification_comment = "Approved"

        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessment_id = assessment_id
        mock_assessment.status = "submitted"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        with patch.object(
            assessment_service, "get_assessment_by_id"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = assessment_service.verify_assessment(
                assessment_id, verification_comment, sample_user
            )

            # Assert
            assert result is True
            assert mock_assessment.status == "verified"
            assert mock_assessment.is_verified is True
            assert mock_assessment.verified_comment == verification_comment
            assert mock_assessment.verifier_id == sample_user.user_id
            mock_uow.commit.assert_called()

    def test_reject_assessment_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful assessment rejection."""
        # Arrange
        assessment_id = 1
        rejection_reason = "Insufficient data"

        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessment_id = assessment_id
        mock_assessment.status = "submitted"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        with patch.object(
            assessment_service, "get_assessment_by_id"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = assessment_service.reject_assessment(
                assessment_id, rejection_reason, sample_user
            )

            # Assert
            assert result is True
            assert mock_assessment.status == "rejected"
            assert mock_assessment.is_verified is False
            assert mock_assessment.rejection_reason == rejection_reason
            assert mock_assessment.verifier_id == sample_user.user_id
            mock_uow.commit.assert_called()

    def test_delete_assessment_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful assessment deletion."""
        # Arrange
        assessment_id = 1
        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessor_id = sample_user.user_id
        mock_assessment.status = "draft"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        # Act
        result = assessment_service.delete_assessment(
            assessment_id, sample_user
        )

        # Assert
        assert result is True
        mock_uow.session.delete.assert_called_with(mock_assessment)
        mock_uow.commit.assert_called()

    def test_delete_assessment_unauthorized(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test assessment deletion fails for unauthorized user."""
        # Arrange
        assessment_id = 1
        mock_assessment = Mock(spec=LocationSetAssessment)
        mock_assessment.assessor_id = "different_user_id"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_assessment)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise HTTPException
            assessment_service.delete_assessment(assessment_id, sample_user)

    def test_create_assessment_set_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful assessment set creation."""
        # Arrange
        set_data = AssessmentSetCreate(
            set_name="Accessibility Assessment",
            description="Standard accessibility assessment",
            criteria_ids=[1, 2, 3],
        )

        mock_set = Mock(spec=AssessmentSet)
        mock_set.set_id = 1

        with patch.object(
            assessment_service, "get_assessment_set_by_id"
        ) as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = assessment_service.create_assessment_set(
                set_data, sample_user
            )

            # Assert
            assert result is not None
            mock_uow.session.add.assert_called()
            mock_uow.commit.assert_called()

    def test_get_assessment_set_by_id_success(
        self, assessment_service, mock_uow
    ):
        """Test successful assessment set retrieval by ID."""
        # Arrange
        set_id = 1
        mock_set = Mock(spec=AssessmentSet)
        mock_set.set_id = set_id
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_set)

        # Act
        result = assessment_service.get_assessment_set_by_id(set_id)

        # Assert
        assert result == mock_set

    def test_get_all_assessment_sets_success(
        self, assessment_service, mock_uow
    ):
        """Test successful retrieval of all assessment sets."""
        # Arrange
        mock_sets = [Mock(spec=AssessmentSet) for _ in range(3)]
        for i, assessment_set in enumerate(mock_sets):
            assessment_set.set_id = i + 1
            assessment_set.set_name = f"Set {i + 1}"
            assessment_set.is_active = True
            assessment_set.criteria = []

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_sets

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.get_all_assessment_sets()

        # Assert
        assert len(result) == 3

    def test_get_accessibility_criteria_success(
        self, assessment_service, mock_uow
    ):
        """Test successful retrieval of accessibility criteria."""
        # Arrange
        mock_criteria = [Mock(spec=AccessibilityCriteria) for _ in range(5)]
        for i, criterion in enumerate(mock_criteria):
            criterion.criterion_id = i + 1
            criterion.criterion_name = f"Criterion {i + 1}"
            criterion.description = f"Description {i + 1}"
            criterion.is_active = True

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_criteria

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.get_accessibility_criteria()

        # Assert
        assert len(result) == 5

    def test_calculate_location_accessibility_score_success(
        self, assessment_service, mock_uow, sample_location
    ):
        """Test successful calculation of location accessibility score."""
        # Arrange
        mock_assessments = [Mock(spec=LocationSetAssessment) for _ in range(3)]
        for i, assessment in enumerate(mock_assessments):
            assessment.overall_score = 7.0 + i  # Scores: 7.0, 8.0, 9.0
            assessment.status = "verified"

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_assessments

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.calculate_location_accessibility_score(
            sample_location.location_id
        )

        # Assert
        assert result == 8.0  # Average of 7.0, 8.0, 9.0

    def test_calculate_location_accessibility_score_no_assessments(
        self, assessment_service, mock_uow, sample_location
    ):
        """Test accessibility score calculation returns None when no assessments."""
        # Arrange
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.calculate_location_accessibility_score(
            sample_location.location_id
        )

        # Assert
        assert result is None

    def test_get_pending_assessments_success(
        self, assessment_service, mock_uow
    ):
        """Test successful retrieval of pending assessments for verification."""
        # Arrange
        mock_assessments = [Mock(spec=LocationSetAssessment) for _ in range(2)]
        for i, assessment in enumerate(mock_assessments):
            assessment.assessment_id = i + 1
            assessment.status = "submitted"
            assessment.location = Mock()
            assessment.location.location_name = f"Location {i + 1}"
            assessment.assessor = Mock()
            assessment.assessor.username = f"assessor_{i + 1}"

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_assessments

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.get_pending_assessments(page=1, size=10)

        # Assert
        assert len(result.items) == 2
        assert result.total == 2

    def test_get_assessment_statistics_success(
        self, assessment_service, mock_uow
    ):
        """Test successful retrieval of assessment statistics."""
        # Arrange
        # Mock stats setup removed
        "total_assessments": 100,
            "pending_verification": 15,
            "verified_assessments": 75,
            "rejected_assessments": 10,
            "average_score": 7.8,
        }

        # Mock the database queries for statistics
        with patch.object(
            assessment_service, "_get_assessment_count_by_status"
        ) as mock_count:
            mock_count.side_effect = [
                100,
                15,
                75,
                10,
            ]  # Total, pending, verified, rejected

            with patch.object(
                assessment_service, "_get_average_assessment_score"
            ) as mock_avg:
                mock_avg.return_value = 7.8

                # Act
                result = assessment_service.get_assessment_statistics()

                # Assert
                assert result["total_assessments"] == 100
                assert result["pending_verification"] == 15
                assert result["verified_assessments"] == 75
                assert result["rejected_assessments"] == 10
                assert result["average_score"] == 7.8

    def test_bulk_verify_assessments_success(
        self, assessment_service, mock_uow, sample_user
    ):
        """Test successful bulk verification of assessments."""
        # Arrange
        assessment_ids = [1, 2, 3]
        verification_comment = "Bulk approved"

        mock_assessments = [Mock(spec=LocationSetAssessment) for _ in range(3)]
        for i, assessment in enumerate(mock_assessments):
            assessment.assessment_id = i + 1
            assessment.status = "submitted"

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_assessments

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.bulk_verify_assessments(
            assessment_ids, verification_comment, sample_user
        )

        # Assert
        assert result == 3
        for assessment in mock_assessments:
            assert assessment.status == "verified"
            assert assessment.is_verified is True
            assert assessment.verified_comment == verification_comment
        mock_uow.commit.assert_called()

    def test_export_assessments_csv_success(
        self, assessment_service, mock_uow
    ):
        """Test successful export of assessments to CSV."""
        # Arrange
        filters = {"status": "verified", "location_id": "test-location"}

        mock_assessments = [Mock(spec=LocationSetAssessment) for _ in range(2)]
        for i, assessment in enumerate(mock_assessments):
            assessment.assessment_id = i + 1
            assessment.overall_score = 8.0 + i
            assessment.status = "verified"
            assessment.location = Mock()
            assessment.location.location_name = f"Location {i + 1}"
            assessment.assessor = Mock()
            assessment.assessor.username = f"assessor_{i + 1}"
            assessment.assessed_at = "2023-01-01"

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_assessments

        mock_uow.session.query.return_value = mock_query

        # Act
        result = assessment_service.export_assessments_csv(filters)

        # Assert
        assert isinstance(result, str)
        assert "assessment_id" in result  # CSV header
        assert "overall_score" in result
