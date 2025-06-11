# Urban Infrastructure Accessibility Monitoring System

## Overview
A comprehensive web application for monitoring and assessing the accessibility of urban infrastructure. Built with FastAPI backend, React TypeScript frontend, and PostgreSQL database.

## Project Structure

```
diplom/
├── backend/                 # FastAPI backend application
│   ├── app/                # Main application code
│   │   ├── api/           # API routes and endpoints
│   │   ├── core/          # Core configuration and security
│   │   ├── db/            # Database configuration
│   │   ├── domain/        # Domain logic and repositories
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic services
│   │   ├── middlewares/   # Custom middleware
│   │   ├── utils/         # Utility functions
│   │   └── tests/         # Test suites
│   └── requirements.txt   # Python dependencies
├── frontend/               # React TypeScript frontend
│   ├── src/               # Source code
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API services
│   │   ├── context/       # React context
│   │   └── utils/         # Utility functions
│   └── package.json       # Node.js dependencies
├── db_schema/             # Database schema and migrations
│   ├── documentation/     # Schema documentation
│   ├── migrations/        # Database migrations
│   ├── indexes/          # Index definitions
│   ├── triggers/         # Database triggers
│   └── diagrams/         # Schema diagrams
├── Dockerfile             # Docker configuration
├── requirements.txt       # Python dependencies
├── restart_backend.py     # Backend restart utility
├── run_comprehensive_tests.py # Test runner
└── README.md             # This file
```

## Features

### Backend (FastAPI)
- **17+ API routers** with comprehensive endpoints
- **JWT authentication** with role-based access control
- **PostgreSQL database** with 29 normalized tables
- **Assessment workflow** with verification system
- **File upload** with MinIO integration
- **Real-time notifications** with WebSocket support
- **Rate limiting** and security middleware
- **Comprehensive testing** with pytest

### Frontend (React TypeScript)
- **Modern React** with TypeScript
- **Responsive design** with Tailwind CSS
- **Interactive maps** for location visualization
- **Assessment forms** with dynamic criteria
- **User management** with role-based UI
- **Real-time updates** via WebSocket
- **File upload** with drag-and-drop
- **Comprehensive routing** with React Router

### Database (PostgreSQL)
- **29 normalized tables** following 3NF principles
- **User management** with profiles and security tracking
- **Location hierarchy** (regions, districts, cities)
- **Assessment system** with criteria and scoring
- **Media management** for images and files
- **Audit logging** for user activities
- **Performance optimization** with indexes and triggers

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Redis (optional, for caching)

### Backend Setup
```bash
cd backend/app
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Database Setup
```bash
# Apply migrations in order
psql -d your_database -f db_schema/migrations/v1__initial_schema.sql
psql -d your_database -f db_schema/migrations/v2_add_user_triggers.sql
# ... continue with remaining migrations
```

## API Documentation

The backend provides comprehensive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints
- `/api/v1/auth/` - Authentication and user management
- `/api/v1/locations/` - Location management
- `/api/v1/assessments/` - Assessment workflow
- `/api/v1/admin/` - Administrative functions
- `/api/v1/upload/` - File upload services

## Architecture

### Clean Architecture
The backend follows clean architecture principles:
- **Domain Layer**: Business logic and entities
- **Application Layer**: Use cases and services
- **Infrastructure Layer**: Database and external services
- **Presentation Layer**: API controllers and schemas

### Database Design
- **Normalized schema** with 29 tables
- **User normalization**: users, user_profiles, user_security
- **Location normalization**: locations, location_details, location_stats
- **Assessment system** with embedded verification
- **Performance optimization** with strategic indexing

## Testing

### Backend Tests
```bash
cd backend/app
python -m pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Comprehensive Tests
```bash
python run_comprehensive_tests.py
```

## Deployment

### Docker
```bash
docker build -t accessibility-monitor .
docker run -p 8000:8000 accessibility-monitor
```

### Production Considerations
- Use environment variables for configuration
- Set up proper SSL certificates
- Configure database connection pooling
- Set up monitoring and logging
- Use a reverse proxy (nginx/Apache)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is part of a diploma thesis for urban infrastructure accessibility monitoring.

## Documentation

- **Database Schema**: See `db_schema/documentation/tables_overview.md`
- **API Documentation**: Available at `/docs` when running the backend
- **Architecture Report**: See `CLEAN_ARCHITECTURE_REPORT.md`
- **Thesis Report**: See `COMPREHENSIVE_THESIS_REPORT.md`
