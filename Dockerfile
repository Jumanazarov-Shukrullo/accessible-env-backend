# Backend Dockerfile - Minimal Railway-optimized build
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools (essential)
    gcc \
    g++ \
    make \
    pkg-config \
    # Database libraries
    libpq-dev \
    # Network utilities
    curl \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app files to the working directory
COPY . .

# Expose the port that FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI app using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]