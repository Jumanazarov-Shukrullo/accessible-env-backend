"""Unit tests for AssessmentService - comprehensive testing of assessment management."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from uuid import uuid4

from app.services.assessment_service import AssessmentService
from app.models.assessment_model import LocationSetAssessment, AssessmentSet, AccessibilityCriteria
from app.models.user_model import User
from app.schemas.assessment_schema import AssessmentCreate, AssessmentUpdate
from app.domain.exceptions import AssessmentNotFound, ValidationError, UnauthorizedOperation
from app.core.constants import RoleID


class TestAssessmentService:
    """Test suite for AssessmentService."""

    @pytest.fixture
    def mock_uow(self):
        """Mock Unit of Work."""
        uow = Mock()
        uow.assessments = Mock()
        uow.assessment_sets = Mock()
        uow.criteria = Mock()
        uow.commit = Mock()
        uow.rollback = Mock()
        uow.__enter__ = Mock(return_value=uow)
        uow.__exit__ = Mock(return_value=None)
        return uow

    @pytest.fixture
    def assessment_service(self, mock_uow):
        """Create AssessmentService instance with mocked dependencies."""
        return AssessmentService(uow=mock_uow)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            user_id=str(uuid4()),
            username="inspector",
            email="inspector@test.com",
            role_id=RoleID.INSPECTOR.value,
            is_active=True
        )

    @pytest.fixture
    def sample_assessment(self):
        """Sample assessment for testing."""
        return LocationSetAssessment(
            assessment_id=str(uuid4()),
            location_id=str(uuid4()),
            assessment_set_id=1,
            assessor_id=str(uuid4()),
            status="draft",
            created_at=datetime.now(timezone.utc)
        )

    def test_create_assessment_success(self, assessment_service, mock_uow, sample_user):
        """Test successful assessment creation."""
        assessment_data = AssessmentCreate(
            location_id=str(uuid4()),
            assessment_set_id=1,
            notes="Initial assessment"
        )

        created_assessment = LocationSetAssessment(
            assessment_id=str(uuid4()),
            location_id=assessment_data.location_id,
            assessment_set_id=assessment_data.assessment_set_id,
            assessor_id=sample_user.user_id,
            status="draft"
        )

        mock_uow.assessments.create.return_value = created_assessment

        result = assessment_service.create_assessment(assessment_data, sample_user)

        assert result.location_id == assessment_data.location_id
        assert result.assessor_id == sample_user.user_id
        assert result.status == "draft"
        mock_uow.assessments.create.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_create_assessment_unauthorized_role(self, assessment_service, mock_uow):
        """Test assessment creation with unauthorized user role."""
        user = User(
            user_id=str(uuid4()),
            username="regular_user",
            email="user@test.com",
            role_id=RoleID.USER.value,
            is_active=True
        )

        assessment_data = AssessmentCreate(
            location_id=str(uuid4()),
            assessment_set_id=1
        )

        with pytest.raises(UnauthorizedOperation):
            assessment_service.create_assessment(assessment_data, user)

    def test_get_assessment_success(self, assessment_service, mock_uow, sample_assessment):
        """Test successful assessment retrieval."""
        mock_uow.assessments.get_by_id.return_value = sample_assessment

        result = assessment_service.get_assessment(sample_assessment.assessment_id)

        assert result.assessment_id == sample_assessment.assessment_id
        mock_uow.assessments.get_by_id.assert_called_once_with(sample_assessment.assessment_id)

    def test_get_assessment_not_found(self, assessment_service, mock_uow):
        """Test assessment retrieval when assessment doesn't exist."""
        assessment_id = str(uuid4())
        mock_uow.assessments.get_by_id.return_value = None

        with pytest.raises(AssessmentNotFound):
            assessment_service.get_assessment(assessment_id)

    def test_update_assessment_success(self, assessment_service, mock_uow, sample_assessment, sample_user):
        """Test successful assessment update."""
        update_data = AssessmentUpdate(
            notes="Updated notes",
            status="in_progress"
        )

        mock_uow.assessments.get_by_id.return_value = sample_assessment
        mock_uow.assessments.update.return_value = sample_assessment

        result = assessment_service.update_assessment(
            sample_assessment.assessment_id, 
            update_data, 
            sample_user
        )

        assert result is not None
        mock_uow.assessments.update.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_update_assessment_unauthorized_user(self, assessment_service, mock_uow, sample_assessment):
        """Test assessment update by unauthorized user."""
        unauthorized_user = User(
            user_id=str(uuid4()),
            username="other_user",
            email="other@test.com",
            role_id=RoleID.INSPECTOR.value,
            is_active=True
        )

        update_data = AssessmentUpdate(notes="Unauthorized update")
        mock_uow.assessments.get_by_id.return_value = sample_assessment

        with pytest.raises(UnauthorizedOperation):
            assessment_service.update_assessment(
                sample_assessment.assessment_id,
                update_data,
                unauthorized_user
            )

    def test_submit_assessment_success(self, assessment_service, mock_uow, sample_assessment, sample_user):
        """Test successful assessment submission."""
        # Make user the owner of the assessment
        sample_assessment.assessor_id = sample_user.user_id
        mock_uow.assessments.get_by_id.return_value = sample_assessment
        mock_uow.assessments.update.return_value = sample_assessment

        result = assessment_service.submit_assessment(sample_assessment.assessment_id, sample_user)

        assert result is not None
        mock_uow.assessments.update.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_submit_assessment_wrong_status(self, assessment_service, mock_uow, sample_user):
        """Test assessment submission with wrong status."""
        submitted_assessment = LocationSetAssessment(
            assessment_id=str(uuid4()),
            assessor_id=sample_user.user_id,
            status="submitted"
        )

        mock_uow.assessments.get_by_id.return_value = submitted_assessment

        with pytest.raises(ValidationError):
            assessment_service.submit_assessment(submitted_assessment.assessment_id, sample_user)

    def test_verify_assessment_success(self, assessment_service, mock_uow, sample_assessment):
        """Test successful assessment verification by admin."""
        admin_user = User(
            user_id=str(uuid4()),
            username="admin",
            email="admin@test.com",
            role_id=RoleID.ADMIN.value,
            is_active=True
        )

        sample_assessment.status = "submitted"
        mock_uow.assessments.get_by_id.return_value = sample_assessment
        mock_uow.assessments.update.return_value = sample_assessment

        result = assessment_service.verify_assessment(
            sample_assessment.assessment_id, 
            admin_user, 
            True, 
            "Assessment approved"
        )

        assert result is not None
        mock_uow.assessments.update.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_verify_assessment_unauthorized(self, assessment_service, mock_uow, sample_assessment, sample_user):
        """Test assessment verification by unauthorized user."""
        sample_assessment.status = "submitted"
        mock_uow.assessments.get_by_id.return_value = sample_assessment

        with pytest.raises(UnauthorizedOperation):
            assessment_service.verify_assessment(
                sample_assessment.assessment_id,
                sample_user,
                True,
                "Unauthorized verification"
            )

    def test_delete_assessment_success(self, assessment_service, mock_uow, sample_assessment, sample_user):
        """Test successful assessment deletion."""
        sample_assessment.assessor_id = sample_user.user_id
        mock_uow.assessments.get_by_id.return_value = sample_assessment
        mock_uow.assessments.delete.return_value = True

        result = assessment_service.delete_assessment(sample_assessment.assessment_id, sample_user)

        assert result is True
        mock_uow.assessments.delete.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_delete_assessment_submitted_status(self, assessment_service, mock_uow, sample_user):
        """Test assessment deletion when status is submitted (should fail)."""
        submitted_assessment = LocationSetAssessment(
            assessment_id=str(uuid4()),
            assessor_id=sample_user.user_id,
            status="submitted"
        )

        mock_uow.assessments.get_by_id.return_value = submitted_assessment

        with pytest.raises(ValidationError):
            assessment_service.delete_assessment(submitted_assessment.assessment_id, sample_user)

    def test_get_assessments_by_location(self, assessment_service, mock_uow):
        """Test getting assessments for a specific location."""
        location_id = str(uuid4())
        mock_assessments = [Mock(), Mock()]
        mock_uow.assessments.get_by_location.return_value = mock_assessments

        results = assessment_service.get_assessments_by_location(location_id)

        assert len(results) == 2
        mock_uow.assessments.get_by_location.assert_called_once_with(location_id)

    def test_get_assessments_by_assessor(self, assessment_service, mock_uow, sample_user):
        """Test getting assessments by specific assessor."""
        mock_assessments = [Mock(), Mock(), Mock()]
        mock_uow.assessments.get_by_assessor.return_value = mock_assessments

        results = assessment_service.get_assessments_by_assessor(sample_user.user_id)

        assert len(results) == 3
        mock_uow.assessments.get_by_assessor.assert_called_once_with(sample_user.user_id)

    def test_get_assessments_by_status(self, assessment_service, mock_uow):
        """Test getting assessments by status."""
        status = "submitted"
        mock_assessments = [Mock() for _ in range(5)]
        mock_uow.assessments.get_by_status.return_value = mock_assessments

        results = assessment_service.get_assessments_by_status(status)

        assert len(results) == 5
        mock_uow.assessments.get_by_status.assert_called_once_with(status)

    def test_get_assessment_statistics(self, assessment_service, mock_uow):
        """Test getting assessment statistics."""
        mock_stats = {
            'total_assessments': 150,
            'by_status': {'draft': 50, 'submitted': 75, 'verified': 25},
            'by_assessor': {'inspector1': 60, 'inspector2': 90},
            'completion_rate': 83.3
        }
        mock_uow.assessments.get_statistics.return_value = mock_stats

        results = assessment_service.get_assessment_statistics()

        assert results['total_assessments'] == 150
        assert results['completion_rate'] == 83.3
        mock_uow.assessments.get_statistics.assert_called_once()

    def test_bulk_update_status(self, assessment_service, mock_uow):
        """Test bulk status update for multiple assessments."""
        assessment_ids = [str(uuid4()) for _ in range(3)]
        new_status = "archived"
        admin_user = User(
            user_id=str(uuid4()),
            role_id=RoleID.ADMIN.value,
            is_active=True
        )

        mock_uow.assessments.bulk_update_status.return_value = 3

        result = assessment_service.bulk_update_status(assessment_ids, new_status, admin_user)

        assert result == 3
        mock_uow.assessments.bulk_update_status.assert_called_once_with(assessment_ids, new_status)
        mock_uow.commit.assert_called_once()

    def test_bulk_update_status_unauthorized(self, assessment_service, mock_uow, sample_user):
        """Test bulk status update by unauthorized user."""
        assessment_ids = [str(uuid4()) for _ in range(3)]
        new_status = "archived"

        with pytest.raises(UnauthorizedOperation):
            assessment_service.bulk_update_status(assessment_ids, new_status, sample_user)

    @patch('app.services.assessment_service.cache')
    def test_caching_integration(self, mock_cache, assessment_service, mock_uow, sample_user):
        """Test cache invalidation on assessment operations."""
        assessment_data = AssessmentCreate(
            location_id=str(uuid4()),
            assessment_set_id=1
        )

        created_assessment = LocationSetAssessment(
            assessment_id=str(uuid4()),
            **assessment_data.dict(),
            assessor_id=sample_user.user_id
        )
        mock_uow.assessments.create.return_value = created_assessment

        assessment_service.create_assessment(assessment_data, sample_user)

        mock_cache.invalidate.assert_called_with('assessments:')

    def test_error_handling_database_failure(self, assessment_service, mock_uow, sample_user):
        """Test error handling when database operations fail."""
        assessment_data = AssessmentCreate(
            location_id=str(uuid4()),
            assessment_set_id=1
        )

        mock_uow.assessments.create.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            assessment_service.create_assessment(assessment_data, sample_user)

        mock_uow.rollback.assert_called_once() 