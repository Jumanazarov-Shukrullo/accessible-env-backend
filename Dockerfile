# Backend Dockerfile - Railway-optimized with correct Debian package names
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for WeasyPrint and other libraries
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
    # Core system libraries for WeasyPrint
    libglib2.0-0 \
    libglib2.0-dev \
    libgirepository-1.0-1 \
    libgirepository1.0-dev \
    # Cairo (2D graphics library)
    libcairo2 \
    libcairo2-dev \
    libcairo-gobject2 \
    # Pango (text rendering)
    libpango-1.0-0 \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    # GDK Pixbuf (image handling)
    libgdk-pixbuf-2.0-0 \
    libgdk-pixbuf2.0-dev \
    # FFI library
    libffi-dev \
    libffi8 \
    # MIME types
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
    # Text processing libraries
    libharfbuzz0b \
    libfribidi0 \
    libthai0 \
    && rm -rf /var/lib/apt/lists/*


# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app files to the working directory
COPY . .

# Clean up apt cache to reduce image size
RUN apt-get remove --purge -y \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Expose the port that FastAPI will run on
EXPOSE 8000


# Command to run the FastAPI app using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]