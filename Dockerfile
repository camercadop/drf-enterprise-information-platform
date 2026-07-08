# Use slim Python image for smaller footprint and faster builds
FROM python:3.14-slim

WORKDIR /app

# Copy dependency files first for better Docker layer caching
# This ensures pip install only runs when dependencies change, not on every code change
COPY pyproject.toml uv.lock ./

# Install dependencies in development mode with no cache to reduce image size
# Using --no-cache-dir prevents storing pip cache in the image
RUN pip install --no-cache-dir -e .

# Copy entire application code
COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]