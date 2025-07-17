#!/bin/bash

# Production Fix Script for dashboard.inqilabgroup.com
# This script applies the connectivity fixes to your production server

echo "=== IPM Production Connectivity Fix ==="
echo "Timestamp: $(date)"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo privileges"
    echo "Usage: sudo ./production_fix.sh"
    exit 1
fi

# Backup current nginx configuration
echo "1. Backing up current nginx configuration..."
cp /etc/nginx/sites-available/dashboard.inqilabgroup.com /etc/nginx/sites-available/dashboard.inqilabgroup.com.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backup created"

# Apply the new nginx configuration
echo ""
echo "2. Applying new nginx configuration..."

# Create the improved configuration
cat > /etc/nginx/sites-available/dashboard.inqilabgroup.com << 'EOF'
server {
    server_name dashboard.inqilabgroup.com;

    # SSL session settings for better performance
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Client connection settings
    client_max_body_size 100M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    
    # Keep-alive settings
    keepalive_timeout 65s;
    keepalive_requests 100;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Connection and timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Keep-alive settings
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # Handle client disconnections gracefully
        proxy_ignore_client_abort off;
        
        # Buffer settings for better performance
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    location /uploads/ {
        alias /root/IPM/uploads/;
        autoindex off;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
        add_header Content-Disposition "inline";
        try_files $uri $uri/ =404;
    }

    location /static/ {
        alias /root/IPM/src/app/static/;
        autoindex off;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
        try_files $uri $uri/ =404;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/dashboard.inqilabgroup.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/dashboard.inqilabgroup.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = dashboard.inqilabgroup.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    server_name dashboard.inqilabgroup.com;
    listen 80;
    return 404; # managed by Certbot
}
EOF

echo "✓ New configuration applied"

# Test nginx configuration
echo ""
echo "3. Testing nginx configuration..."
if nginx -t; then
    echo "✓ Nginx configuration test passed"
else
    echo "✗ Nginx configuration test failed!"
    echo "Restoring backup..."
    cp /etc/nginx/sites-available/dashboard.inqilabgroup.com.backup.* /etc/nginx/sites-available/dashboard.inqilabgroup.com
    exit 1
fi

# Reload nginx
echo ""
echo "4. Reloading nginx..."
if systemctl reload nginx; then
    echo "✓ Nginx reloaded successfully"
else
    echo "✗ Nginx reload failed!"
    exit 1
fi

# Check nginx status
echo ""
echo "5. Checking nginx status..."
systemctl status nginx --no-pager -l

echo ""
echo "6. Testing connectivity..."
echo -n "Local health check: "
if curl -s -f http://localhost:8000/healthcheck > /dev/null; then
    echo "✓ Success"
else
    echo "✗ Failed"
fi

echo -n "HTTPS health check: "
if curl -s -f https://dashboard.inqilabgroup.com/healthcheck > /dev/null; then
    echo "✓ Success"
else
    echo "✗ Failed"
fi

echo ""
echo "7. Current connection status:"
echo "Active HTTPS connections: $(netstat -an | grep :443 | grep ESTABLISHED | wc -l)"
echo "Active HTTP connections: $(netstat -an | grep :80 | grep ESTABLISHED | wc -l)"

echo ""
echo "=== Fix Applied Successfully ==="
echo "The following improvements have been made:"
echo "- Added proper proxy timeouts (60s)"
echo "- Enabled SSL session caching"
echo "- Improved connection handling"
echo "- Added keep-alive settings"
echo "- Enhanced buffer management"
echo ""
echo "Monitor your application for improved connectivity!"
echo "Users should experience fewer timeout issues when switching networks."
