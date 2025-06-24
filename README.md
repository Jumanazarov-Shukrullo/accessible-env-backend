# 🌍 Accessibility Assessment Platform - Backend

> **Making cities more accessible, one location at a time** 🦽♿

## 🌐 Live Demo & Testing

**👨‍💻 Want to test the backend? Check out the live frontend application:**  
🔗 **[https://access-front.up.railway.app/](https://access-front.up.railway.app/)**

The frontend provides a user-friendly interface to interact with all the backend APIs. You can create accounts, add locations, submit assessments, and explore all features of the platform!

---

Welcome to the backend of our crowdsourced accessibility assessment platform! This API powers a system where community members can evaluate and report on the accessibility of public locations, helping create a more inclusive urban environment for people with disabilities.

## 🎯 What Does This Do?

This platform helps communities:
- 📍 **Map accessible locations** - Restaurants, parks, shops, public buildings
- ⭐ **Rate accessibility features** - Ramps, parking, restrooms, navigation aids  
- 💬 **Share experiences** - Real reviews from people who've been there
- 📊 **Track improvements** - See how accessibility evolves over time
- 🔍 **Find inclusive spaces** - Discover truly accessible places in your city

## ✨ Key Features

### 🏢 Location Management
- Add and manage public locations (restaurants, parks, buildings, etc.)
- Upload multiple photos per location
- Organize by regions, districts, and categories
- Track location status and updates

### 🌟 Assessment System
- Detailed accessibility criteria evaluation
- Star ratings for different accessibility aspects
- Comment system for detailed feedback
- Progress tracking for improvements

### 👥 User & Community Features  
- User registration and authentication (including Google OAuth)
- Role-based permissions (Users, Inspectors, Admins)
- Favorites and personal collections
- Notification system for updates

### 📊 Analytics & Insights
- Accessibility statistics and trends
- Popular and recently evaluated locations
- Performance metrics and reporting
- Data export capabilities

## 🛠️ Tech Stack

**Core Framework:**
- 🚀 **FastAPI** - Modern, fast web framework for APIs
- 🐍 **Python 3.12** - Latest Python with type hints
- 📦 **Pydantic** - Data validation and settings management

**Database & Storage:**
- 🐘 **PostgreSQL** - Robust relational database
- 🗃️ **SQLAlchemy** - Powerful ORM with async support
- 🖼️ **MinIO** - S3-compatible object storage for images
- ⚡ **Redis** - High-performance caching layer

**Authentication & Security:**
- 🔐 **JWT** - Secure token-based authentication
- 🌐 **OAuth2** - Google Social Login integration
- 🛡️ **CORS** - Cross-origin resource sharing
- 🔒 **Bcrypt** - Password hashing

**Monitoring & Quality:**
- 📈 **Prometheus** - Metrics collection
- 📝 **Structured Logging** - Comprehensive request logging
- 🧪 **Pytest** - Comprehensive testing suite
- 🚦 **Rate Limiting** - API protection

## 🚀 Quick Start

### Prerequisites
- 🐍 Python 3.12+
- 🐘 PostgreSQL 14+
- ⚡ Redis 6+
- 🗃️ MinIO or S3-compatible storage

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/accessibility-backend.git
cd accessibility-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup
Create a `.env` file in the project root:

```env
# Database
APP_DATABASE__DATABASE_URL=postgresql://user:password@localhost:5432/accessibility_db
APP_DATABASE__POOL_SIZE=20

# Redis Cache
APP_CACHE__REDIS_URL=redis://localhost:6379/0

# Authentication
APP_SESSION_SECRET_KEY=your-super-secret-session-key
APP_AUTH__SECRET_KEY=your-jwt-secret-key
APP_AUTH__GOOGLE_CLIENT_ID=your-google-client-id
APP_AUTH__GOOGLE_CLIENT_SECRET=your-google-client-secret
APP_AUTH__FRONTEND_BASE_URL=http://localhost:3000

# File Storage (MinIO)
APP_STORAGE__MINIO_ENDPOINT=localhost:9000
APP_STORAGE__MINIO_ACCESS_KEY=your-access-key
APP_STORAGE__MINIO_SECRET_KEY=your-secret-key
APP_STORAGE__MINIO_BUCKET=accessibility-images

# Email (Optional)
APP_SMTP__SENDER_EMAIL=noreply@yourdomain.com
APP_SMTP__SENDER_PASSWORD=your-email-app-password

# App Settings
APP_DEBUG=true
APP_BACKEND_URL=http://localhost:8000
APP_ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. Database Setup
```bash
# Run migrations
alembic upgrade head

# Optional: Load sample data
python -m app.scripts.seed_data
```

### 4. Start the Server
```bash
# Development server
uvicorn app.main:app --reload --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Your API will be running at `http://localhost:8000` 🎉

## 📖 API Documentation

Once the server is running, check out the interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### 🔗 Key Endpoints

```
🏠 Health Check
GET /health

👤 Authentication
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/google

📍 Locations
GET    /api/v1/locations
POST   /api/v1/locations
GET    /api/v1/locations/{id}
PUT    /api/v1/locations/{id}

⭐ Assessments
GET    /api/v1/assessments
POST   /api/v1/assessments
GET    /api/v1/locations/{id}/assessments

🖼️ Images
POST   /api/v1/images/upload
GET    /api/v1/images/{id}

📊 Statistics
GET    /api/v1/statistics/overview
GET    /api/v1/statistics/popular-locations
```

## 🧪 Testing

We believe in quality code! Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_location_service.py

# Run integration tests
pytest tests/e2e/
```

## 🐳 Docker Deployment

### Development with Docker Compose
```bash
# Start all services (includes PostgreSQL, Redis, MinIO)
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Production Docker
```bash
# Build image
docker build -t accessibility-backend .

# Run container
docker run -p 8000:8000 --env-file .env accessibility-backend
```

## ☁️ Railway Deployment

This project is optimized for [Railway](https://railway.app) deployment:

1. **Connect your GitHub repo** to Railway
2. **Add services**: PostgreSQL, Redis, and your backend
3. **Set environment variables** (see `.env` example above)
4. **Deploy automatically** on push to main branch

The `railway.json` and `Dockerfile` are already configured for you!

## 🏗️ Project Structure

```
backend/
├── app/
│   ├── api/v1/routers/          # API route handlers
│   ├── core/                    # Core configuration
│   ├── db/                      # Database setup
│   ├── domain/                  # Business logic & repositories
│   ├── models/                  # SQLAlchemy models
│   ├── schemas/                 # Pydantic schemas
│   ├── services/                # Business services
│   ├── tasks/                   # Background tasks
│   ├── tests/                   # Test suite
│   └── utils/                   # Utility functions
├── migrations/                  # Database migrations
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container configuration
└── docker-compose.yml          # Local development setup
```

## 🤝 Contributing

We'd love your help making cities more accessible! Here's how to contribute:

### 🐛 Found a Bug?
1. Check if it's already reported in [Issues](https://github.com/yourusername/accessibility-backend/issues)
2. If not, create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment details

### 💡 Have an Idea?
1. Open a [Discussion](https://github.com/yourusername/accessibility-backend/discussions) first
2. We'll help you refine the idea
3. Create an issue if we decide to move forward

### 🔧 Want to Code?
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with tests
4. **Commit** with clear messages (`git commit -m 'Add amazing feature'`)
5. **Push** to your branch (`git push origin feature/amazing-feature`)
6. **Open** a Pull Request

### 📋 Development Guidelines
- Write tests for new features
- Follow PEP 8 style guidelines
- Add docstrings to functions
- Update documentation if needed
- Be kind and respectful in discussions

## 📊 Monitoring & Observability

The backend includes built-in monitoring:

- **Metrics**: Prometheus metrics at `/metrics`
- **Health Checks**: Simple health endpoint at `/health`
- **Logging**: Structured JSON logging with request tracing
- **Performance**: Database query monitoring and optimization

## 🔐 Security

We take security seriously:
- 🔒 **Password hashing** with bcrypt
- 🎫 **JWT tokens** for stateless authentication
- 🚦 **Rate limiting** to prevent abuse
- 🛡️ **Input validation** with Pydantic
- 🌐 **CORS** properly configured
- 📝 **Audit logging** for sensitive operations

Found a security issue? Please email shukrullo.jumanazarov@phystech.edu instead of opening a public issue.

## 📈 Performance

Optimized for production:
- ⚡ **Redis caching** for frequently accessed data
- 🏊 **Connection pooling** for database efficiency
- 📦 **Lazy loading** of relationships
- 🗜️ **Response compression** for faster API calls
- 📊 **Database indexing** for quick queries

## 🌐 Localization

Currently supporting:
- 🇺🇸 English

## 🙏 Acknowledgments

- **FastAPI team** for the amazing framework
- **SQLAlchemy** for powerful database tools
- **Contributors** who make this project better
- **Accessibility advocates** who inspire this work
- **Community members** who test and provide feedback

---

**Together, we can build more accessible communities! 🌟**

*Made with ❤️ for accessibility and inclusion*
