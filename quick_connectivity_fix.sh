#!/bin/bash

# Quick Connectivity Fix Script
# Addresses common DNS and connectivity issues

echo "=== Quick Connectivity Fix ==="
echo "Timestamp: $(date)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo privileges"
    echo "Usage: sudo ./quick_connectivity_fix.sh"
    exit 1
fi

echo "1. Checking current status..."

# Check if application is running
if curl -s -f http://localhost:8000/healthcheck > /dev/null; then
    echo "✓ Application is running locally"
else
    echo "✗ Application is NOT running locally"
    echo "  Attempting to restart Docker containers..."
    cd /root/IPM 2>/dev/null || cd /home/*/IPM 2>/dev/null || echo "Could not find IPM directory"
    docker-compose restart
    sleep 10
    if curl -s -f http://localhost:8000/healthcheck > /dev/null; then
        echo "✓ Application restarted successfully"
    else
        echo "✗ Application restart failed"
    fi
fi

echo ""
echo "2. Checking DNS resolution..."

# Check if server can resolve its own domain
if ! nslookup dashboard.inqilabgroup.com > /dev/null 2>&1; then
    echo "✗ DNS resolution failing - adding local hosts entry"
    
    # Get the server's public IP
    public_ip=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "127.0.0.1")
    
    # Add to hosts file if not already present
    if ! grep -q "dashboard.inqilabgroup.com" /etc/hosts; then
        echo "$public_ip dashboard.inqilabgroup.com" >> /etc/hosts
        echo "✓ Added dashboard.inqilabgroup.com to /etc/hosts"
    else
        echo "✓ dashboard.inqilabgroup.com already in /etc/hosts"
    fi
else
    echo "✓ DNS resolution working"
fi

echo ""
echo "3. Checking and fixing nginx configuration..."

# Ensure nginx is running
if ! systemctl is-active --quiet nginx; then
    echo "✗ Nginx is not running - starting it"
    systemctl start nginx
    sleep 2
    if systemctl is-active --quiet nginx; then
        echo "✓ Nginx started successfully"
    else
        echo "✗ Failed to start nginx"
    fi
else
    echo "✓ Nginx is running"
fi

# Test nginx configuration
if nginx -t > /dev/null 2>&1; then
    echo "✓ Nginx configuration is valid"
else
    echo "✗ Nginx configuration has errors"
    echo "  Nginx configuration test output:"
    nginx -t 2>&1 | sed 's/^/    /'
fi

echo ""
echo "4. Checking SSL certificate..."

# Check SSL certificate
if echo | openssl s_client -connect dashboard.inqilabgroup.com:443 -servername dashboard.inqilabgroup.com > /dev/null 2>&1; then
    echo "✓ SSL certificate is accessible"
else
    echo "✗ SSL certificate is not accessible"
    echo "  This could be due to firewall or DNS issues"
fi

echo ""
echo "5. Checking firewall settings..."

# Check if UFW is blocking connections
if command -v ufw > /dev/null; then
    ufw_status=$(ufw status | head -1)
    echo "UFW Status: $ufw_status"
    
    if ufw status | grep -q "Status: active"; then
        echo "Checking if HTTP/HTTPS ports are allowed..."
        if ufw status | grep -q "80\|443\|Nginx"; then
            echo "✓ HTTP/HTTPS ports are allowed in UFW"
        else
            echo "✗ HTTP/HTTPS ports may be blocked"
            echo "  Adding UFW rules for HTTP/HTTPS..."
            ufw allow 'Nginx Full'
            echo "✓ Added Nginx Full rule to UFW"
        fi
    fi
fi

echo ""
echo "6. Checking system resources..."

# Check disk space
disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$disk_usage" -gt 90 ]; then
    echo "⚠ WARNING: Disk usage is ${disk_usage}% - this could cause issues"
else
    echo "✓ Disk usage is acceptable (${disk_usage}%)"
fi

# Check memory usage
mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$mem_usage" -gt 90 ]; then
    echo "⚠ WARNING: Memory usage is ${mem_usage}% - this could cause issues"
else
    echo "✓ Memory usage is acceptable (${mem_usage}%)"
fi

echo ""
echo "7. Final connectivity test..."

# Wait a moment for services to stabilize
sleep 5

# Test local connectivity
echo -n "Local health check: "
if curl -s -f http://localhost:8000/healthcheck > /dev/null; then
    echo "✓ Success"
else
    echo "✗ Failed"
fi

# Test external connectivity
echo -n "External health check: "
if curl -s -f https://dashboard.inqilabgroup.com/healthcheck > /dev/null; then
    echo "✓ Success"
else
    echo "✗ Failed"
fi

echo ""
echo "8. Connection statistics..."
echo "Active HTTPS connections: $(netstat -an | grep :443 | grep ESTABLISHED | wc -l)"
echo "Active HTTP connections: $(netstat -an | grep :80 | grep ESTABLISHED | wc -l)"

echo ""
echo "=== Fix Complete ==="
echo ""
echo "If users are still experiencing issues, the problem might be:"
echo "1. Client-side DNS caching - users should clear their DNS cache"
echo "2. ISP-level DNS issues - users should try different DNS servers (8.8.8.8, 1.1.1.1)"
echo "3. CDN or proxy issues - check if you're using any CDN services"
echo "4. Geographic DNS propagation - DNS changes can take 24-48 hours to propagate globally"
echo ""
echo "For immediate testing, users can try:"
echo "- Using incognito/private browsing mode"
echo "- Clearing browser cache and cookies"
echo "- Using a different device or network"
echo "- Using a VPN to test from different locations"
