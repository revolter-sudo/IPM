# Use an official Python runtime as a base image
FROM python:3.10

# Install netcat (for checking PostgreSQL readiness)
RUN apt-get update && apt-get install -y  netcat-openbsd

# Set the working directory inside the container
WORKDIR /app

# Copy the application code to the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the FastAPI default port
EXPOSE 8000

# Set the startup script
ENTRYPOINT ["/entrypoint.sh"]
