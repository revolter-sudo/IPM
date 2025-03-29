# Use official Python 3.10 as a base image
FROM python:3.10

# Install netcat (for checking PostgreSQL readiness)
RUN apt-get update && apt-get install -y netcat-openbsd

# Set the working directory inside the container
WORKDIR /app

# 1) Copy only requirements.txt first for layer-caching
COPY requirements.txt /app

# 2) Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy the rest of the application code
COPY . .

# 4) Copy the secret file into the container
#    (Ensure 'secret_files/secret_files.json' is in the Docker build context, but .gitignored)
COPY secretfiles/secret_files.json /app/utils/firebase/secret_files.json

# 5) Copy the entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 6) Expose the FastAPI default port
EXPOSE 8000

# 7) Set the startup script
ENTRYPOINT ["/entrypoint.sh"]
