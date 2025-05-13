#!/bin/bash

# This script sets up HTTPS for your application
# Run this script on your VPS

# Set variables
DOMAIN="dev.inqilabgroup.com"  # Your domain
EMAIL="yashbhatt@gmail.com"  # Replace with your email

# Create required directories
echo "Creating required directories..."
mkdir -p nginx
mkdir -p certbot/www
mkdir -p certbot/conf

# Create Nginx configuration
echo "Creating Nginx configuration..."
cat > nginx/nginx.conf << EOF
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;

    # SSL Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name $DOMAIN;

        location / {
            return 301 https://\$host\$request_uri;
        }

        # For Let's Encrypt certificate validation
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
    }

    # HTTPS Server
    server {
        listen 443 ssl;
        server_name $DOMAIN;

        # SSL Certificate
        ssl_certificate /etc/nginx/ssl/live/$DOMAIN/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/live/$DOMAIN/privkey.pem;

        # Proxy headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Proxy timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Proxy to FastAPI
        location / {
            proxy_pass http://api:8000;
        }

        # Static files
        location /uploads/ {
            alias /app/uploads/;
        }

        location /static/ {
            alias /app/static/;
        }
    }
}
EOF

# Update Docker Compose file
echo "Updating Docker Compose file..."
cat > docker-compose.yml << EOF
services:
  api:
    build: .
    restart: always
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql://myuser:200899@147.93.31.224:5432/ipm_new
    # No need to expose port 8000 to the host, only to the internal network
    expose:
      - "8000"
    volumes:
      - ./uploads:/app/uploads
      - /root/secretfiles/secret_files.json:/app/src/app/utils/firebase/secret_files.json
    networks:
      - app-network

  nginx:
    image: nginx:1.25-alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./certbot/www:/var/www/certbot
      - ./certbot/conf:/etc/nginx/ssl
      - ./uploads:/app/uploads:ro
      - ./src/app/static:/app/static:ro
    depends_on:
      - api
    networks:
      - app-network

  certbot:
    image: certbot/certbot:latest
    volumes:
      - ./certbot/www:/var/www/certbot
      - ./certbot/conf:/etc/letsencrypt

networks:
  app-network:
    driver: bridge
EOF

# Create dummy certificates for Nginx to start
echo "Creating dummy certificates..."
mkdir -p "certbot/conf/live/$DOMAIN"
openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
  -keyout "certbot/conf/live/$DOMAIN/privkey.pem" \
  -out "certbot/conf/live/$DOMAIN/fullchain.pem" \
  -subj "/CN=localhost"

# Start Nginx
echo "Starting Nginx..."
docker-compose up -d nginx

# Wait for Nginx to start
echo "Waiting for Nginx to start..."
sleep 5

# Request Let's Encrypt certificate
echo "Requesting Let's Encrypt certificate for $DOMAIN..."
docker-compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d $DOMAIN \
  --email $EMAIL \
  --rsa-key-size 4096 \
  --agree-tos \
  --force-renewal \
  --non-interactive

# Reload Nginx to use the new certificate
echo "Reloading Nginx..."
docker-compose exec nginx nginx -s reload

# Set up automatic renewal
echo "Setting up automatic renewal..."
echo "0 0,12 * * * docker-compose run --rm certbot renew --quiet && docker-compose exec nginx nginx -s reload" | sudo tee -a /etc/crontab > /dev/null

echo "HTTPS setup completed!"
echo "Your application should now be accessible at https://$DOMAIN"
