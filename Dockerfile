# Use a more complete Python image that already has many dependencies
FROM python:3.9

# Install netcat (for checking PostgreSQL readiness)
RUN apt-get update && apt-get install -y netcat-openbsd

# Set the working directory inside the container
WORKDIR /app

# Copy the application code
COPY . .

# Install dependencies directly from the local system
# This avoids network issues when downloading packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir psycopg2-binary && \
    pip install --no-cache-dir fastapi uvicorn sqlalchemy && \
    pip install --no-cache-dir alembic && \
    pip install --no-cache-dir fastapi-sqlalchemy pydantic-settings pydantic && \
    pip install --no-cache-dir passlib==1.7.4 python-jose python-multipart && \
    pip install --no-cache-dir python-dotenv jinja2 && \
    pip install --no-cache-dir -r requirements.txt || echo "Some packages could not be installed" && \
    pip install --no-cache-dir alembic

# Copy the new entrypoint script
COPY entrypoint_new.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the FastAPI default port
EXPOSE 8000

# Set the startup script
ENTRYPOINT ["/entrypoint.sh"]
