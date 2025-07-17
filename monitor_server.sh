#!/bin/bash

# Server Monitoring Script for IPM Application
# This script helps diagnose connectivity issues

echo "=== IPM Server Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Check if Docker containers are running
echo "1. Docker Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(ipm|api)" || echo "No IPM containers found"
echo ""

# Check if the application is responding
echo "2. Application Health Check:"
if curl -s -f http://localhost:8000/healthcheck > /dev/null; then
    echo "✓ Application is responding on localhost:8000"
    response=$(curl -s http://localhost:8000/healthcheck)
    echo "Response: $response"
else
    echo "✗ Application is NOT responding on localhost:8000"
fi
echo ""

# Check if HTTPS is working
echo "3. HTTPS Connectivity Check:"
if curl -s -f https://dev.inqilabgroup.com/healthcheck > /dev/null; then
    echo "✓ HTTPS is working"
    response=$(curl -s https://dev.inqilabgroup.com/healthcheck)
    echo "Response: $response"
else
    echo "✗ HTTPS is NOT working"
fi
echo ""

# Check Nginx status
echo "4. Nginx Status:"
if systemctl is-active --quiet nginx; then
    echo "✓ Nginx is running"
    echo "Nginx processes: $(ps aux | grep nginx | grep -v grep | wc -l)"
else
    echo "✗ Nginx is NOT running"
fi
echo ""

# Check SSL certificate
echo "5. SSL Certificate Check:"
if command -v openssl > /dev/null; then
    cert_info=$(echo | openssl s_client -servername dev.inqilabgroup.com -connect dev.inqilabgroup.com:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✓ SSL Certificate is valid"
        echo "$cert_info"
    else
        echo "✗ SSL Certificate check failed"
    fi
else
    echo "OpenSSL not available for certificate check"
fi
echo ""

# Check port availability
echo "6. Port Availability:"
if netstat -tuln | grep -q ":80 "; then
    echo "✓ Port 80 is listening"
else
    echo "✗ Port 80 is NOT listening"
fi

if netstat -tuln | grep -q ":443 "; then
    echo "✓ Port 443 is listening"
else
    echo "✗ Port 443 is NOT listening"
fi

if netstat -tuln | grep -q ":8000 "; then
    echo "✓ Port 8000 is listening"
else
    echo "✗ Port 8000 is NOT listening"
fi
echo ""

# Check system resources
echo "7. System Resources:"
echo "Memory usage:"
free -h | grep -E "(Mem|Swap)"
echo ""
echo "Disk usage:"
df -h / | tail -1
echo ""
echo "CPU load:"
uptime
echo ""

# Check recent logs for errors
echo "8. Recent Error Logs:"
echo "Nginx errors (last 10 lines):"
if [ -f /var/log/nginx/error.log ]; then
    tail -10 /var/log/nginx/error.log | grep -E "(error|crit|alert|emerg)" || echo "No recent errors"
else
    echo "Nginx error log not found"
fi
echo ""

echo "Application errors (last 10 lines):"
if [ -f ./logs/ipm_errors.log ]; then
    tail -10 ./logs/ipm_errors.log || echo "No recent errors"
else
    echo "Application error log not found"
fi
echo ""

# Check network connectivity
echo "9. Network Connectivity:"
echo "External connectivity test:"
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "✓ Internet connectivity is working"
else
    echo "✗ Internet connectivity issues detected"
fi

echo "Database connectivity test:"
if nc -z 147.93.31.224 5432 2>/dev/null; then
    echo "✓ Database server is reachable"
else
    echo "✗ Database server is NOT reachable"
fi
echo ""

# Check for common issues
echo "10. Common Issue Checks:"

# Check if too many connections
connections=$(netstat -an | grep :443 | grep ESTABLISHED | wc -l)
echo "Active HTTPS connections: $connections"
if [ $connections -gt 100 ]; then
    echo "⚠ High number of connections detected"
fi

# Check if firewall is blocking
if command -v ufw > /dev/null; then
    ufw_status=$(ufw status | head -1)
    echo "Firewall status: $ufw_status"
fi

echo ""
echo "=== End of Health Check ==="
