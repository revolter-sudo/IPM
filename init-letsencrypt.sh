#!/bin/bash

# This script sets up the initial SSL certificates for your domain
# It should be run once before starting the Docker containers

# Replace these variables with your own values
domains=(dev.inqilabgroup.com)
email="yashbhatt@dezdok.com"  # Adding a valid address is strongly recommended
staging=0  # Set to 1 if you're testing your setup to avoid hitting request limits

# Create required directories
mkdir -p certbot/www
mkdir -p certbot/conf

# Create dummy certificates for Nginx to start
if [ ! -e "certbot/conf/live/$domains" ]; then
  echo "Creating dummy certificate for $domains..."
  mkdir -p "certbot/conf/live/$domains"
  openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
    -keyout "certbot/conf/live/$domains/privkey.pem" \
    -out "certbot/conf/live/$domains/fullchain.pem" \
    -subj "/CN=localhost"
fi

# Update Nginx configuration to use the domain name
sed -i "s/dev.inqilabgroup.com/$domains/g" nginx/nginx.conf

# Start Nginx
echo "Starting Nginx..."
docker-compose up -d nginx

# Wait for Nginx to start
sleep 5

# Request Let's Encrypt certificate
echo "Requesting Let's Encrypt certificate for $domains..."
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

# Select appropriate Let's Encrypt server
if [ $staging != "0" ]; then
  server_arg="--staging"
else
  server_arg="--server https://acme-v02.api.letsencrypt.org/directory"
fi

docker-compose run --rm certbot certonly \
  $server_arg \
  --webroot -w /var/www/certbot \
  $domain_args \
  --email $email \
  --rsa-key-size 4096 \
  --agree-tos \
  --force-renewal \
  --non-interactive

# Reload Nginx to use the new certificate
echo "Reloading Nginx..."
docker-compose exec nginx nginx -s reload

echo "Setup completed!"
