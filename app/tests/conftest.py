from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import security_manager
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.category_model import Category
from app.models.city_model import City
from app.models.district_model import District
from app.models.location_model import Location, LocationDetails, LocationStats
from app.models.region_model import Region
from app.models.role_model import Role
from app.models.user_model import User, UserProfile, UserSecurity


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_role(db_session: Session) -> Role:
    """Create a sample role for testing."""
    role = Role(
        role_name="test_user", description="Test user role", is_active=True
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def admin_role(db_session: Session) -> Role:
    """Create an admin role for testing."""
    role = Role(
        role_name="admin", description="Administrator role", is_active=True
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def sample_user(db_session: Session, sample_role: Role) -> User:
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=security_manager.get_password_hash("testpass123"),
        role_id=sample_role.role_id,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    db_session.flush()

    # Create user profile
    profile = UserProfile(
        user_id=user.user_id,
        first_name="Test",
        surname="User",
        full_name="Test User",
        language_preference="en",
    )
    db_session.add(profile)

    # Create user security
    security = UserSecurity(
        user_id=user.user_id, failed_login_attempts=0, two_factor_enabled=False
    )
    db_session.add(security)

    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session, admin_role: Role) -> User:
    """Create an admin user for testing."""
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=security_manager.get_password_hash("adminpass123"),
        role_id=admin_role.role_id,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    db_session.flush()

    # Create user profile
    profile = UserProfile(
        user_id=user.user_id,
        first_name="Admin",
        surname="User",
        full_name="Admin User",
        language_preference="en",
    )
    db_session.add(profile)

    # Create user security
    security = UserSecurity(
        user_id=user.user_id, failed_login_attempts=0, two_factor_enabled=False
    )
    db_session.add(security)

    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_category(db_session: Session) -> Category:
    """Create a sample category for testing."""
    category = Category(
        category_name="Test Category",
        slug="test-category",
        description="A test category",
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def sample_region(db_session: Session) -> Region:
    """Create a sample region for testing."""
    region = Region(
        region_name="Test Region",
        region_code="TR",
        description="A test region",
    )
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)
    return region


@pytest.fixture
def sample_district(db_session: Session, sample_region: Region) -> District:
    """Create a sample district for testing."""
    district = District(
        district_name="Test District",
        district_code="TD",
        region_id=sample_region.region_id,
        description="A test district",
    )
    db_session.add(district)
    db_session.commit()
    db_session.refresh(district)
    return district


@pytest.fixture
def sample_city(
    db_session: Session, sample_region: Region, sample_district: District
) -> City:
    """Create a sample city for testing."""
    city = City(
        city_name="Test City",
        city_code="TC",
        region_id=sample_region.region_id,
        district_id=sample_district.district_id,
    )
    db_session.add(city)
    db_session.commit()
    db_session.refresh(city)
    return city


@pytest.fixture
def sample_location(
    db_session: Session,
    sample_category: Category,
    sample_region: Region,
    sample_district: District,
    sample_city: City,
) -> Location:
    """Create a sample location for testing."""
    location = Location(
        location_name="Test Location",
        address="123 Test Street, Test City",
        latitude=40.7128,
        longitude=-74.0060,
        category_id=sample_category.category_id,
        region_id=sample_region.region_id,
        district_id=sample_district.district_id,
        city_id=sample_city.city_id,
        status="active",
    )
    db_session.add(location)
    db_session.flush()

    # Create location details
    details = LocationDetails(
        location_id=location.location_id,
        contact_info="555-0123",
        website_url="https://testlocation.com",
        description="A test location",
    )
    db_session.add(details)

    # Create location stats
    stats = LocationStats(
        location_id=location.location_id,
        accessibility_score=7.5,
        total_reviews=0,
        total_ratings=0,
    )
    db_session.add(stats)

    db_session.commit()
    db_session.refresh(location)
    return location


@pytest.fixture
def auth_headers(sample_user: User) -> dict:
    """Create authentication headers for testing."""
    token = security_manager.create_access_token(
        data={"sub": sample_user.username, "user_id": sample_user.user_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict:
    """Create admin authentication headers for testing."""
    token = security_manager.create_access_token(
        data={"sub": admin_user.username, "user_id": admin_user.user_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_minio():
    """Mock MinIO storage for testing."""
    with patch("app.utils.external_storage.MinioClient") as mock:
        mock_instance = mock.return_value
        mock_instance.upload_file.return_value = "test-object-name"
        mock_instance.presigned_get_url.return_value = (
            "https://test.minio.url/test-object"
        )
        yield mock_instance


@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    with patch("app.services.email_service.EmailService") as mock:
        mock_instance = mock.return_value
        mock_instance.send_email.return_value = True
        yield mock_instance
