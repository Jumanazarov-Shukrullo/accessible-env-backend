# Backend Dockerfile - Railway-optimized with all required dependencies
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies including WeasyPrint requirements
RUN apt-get update && apt-get install -y \
    # Build tools
    gcc \
    g++ \
    make \
    pkg-config \
    # Database libraries
    libpq-dev \
    # Network utilities
    curl \
    # WeasyPrint core dependencies
    libglib2.0-0 \
    libglib2.0-dev \
    libgobject-2.0-0 \
    libgobject-2.0-dev \
    libgirepository1.0-dev \
    libcairo2 \
    libcairo2-dev \
    libcairo-gobject2 \
    # Pango (text rendering)
    libpango-1.0-0 \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    # GDK Pixbuf (image handling)
    libgdk-pixbuf2.0-0 \
    libgdk-pixbuf2.0-dev \
    # Additional dependencies
    libffi-dev \
    libffi8 \
    shared-mime-info \
    # Font libraries
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto \
    # Image processing libraries
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    # XML processing
    libxml2-dev \
    libxslt1-dev \
    # Additional runtime libraries
    libharfbuzz0b \
    libfribidi0 \
    libthai0 \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Start command - Railway compatible
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

# Development stage
FROM python:3.12-slim as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dev dependencies if file exists
COPY requirements-dev.txt* ./
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Copy application code
COPY . .


# Expose port
EXPOSE 8000

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]