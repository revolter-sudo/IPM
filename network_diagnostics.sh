#!/bin/bash

# Network Diagnostics Script for IPM Application
# Helps identify network-related connectivity issues

echo "=== Network Diagnostics for IPM ==="
echo "Timestamp: $(date)"
echo ""

# Function to test connectivity from different perspectives
test_connectivity() {
    local url=$1
    local description=$2
    
    echo "Testing $description ($url):"
    
    # Test with curl
    echo -n "  Curl test: "
    if curl -s -f --max-time 10 "$url" > /dev/null; then
        echo "✓ Success"
    else
        echo "✗ Failed"
    fi
    
    # Test with wget if available
    if command -v wget > /dev/null; then
        echo -n "  Wget test: "
        if wget -q --timeout=10 --tries=1 "$url" -O /dev/null; then
            echo "✓ Success"
        else
            echo "✗ Failed"
        fi
    fi
    
    # Test response time
    echo -n "  Response time: "
    response_time=$(curl -s -w "%{time_total}" -o /dev/null --max-time 10 "$url" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "${response_time}s"
    else
        echo "Failed to measure"
    fi
    
    echo ""
}

# Test different endpoints
echo "1. Connectivity Tests:"
test_connectivity "http://localhost:8000/healthcheck" "Local HTTP"
test_connectivity "https://dev.inqilabgroup.com/healthcheck" "External HTTPS"
test_connectivity "https://dev.inqilabgroup.com/" "Main site"

# DNS resolution test
echo "2. DNS Resolution Test:"
echo -n "Resolving dev.inqilabgroup.com: "
if nslookup dev.inqilabgroup.com > /dev/null 2>&1; then
    ip=$(nslookup dev.inqilabgroup.com | grep -A1 "Name:" | tail -1 | awk '{print $2}')
    echo "✓ Resolved to $ip"
else
    echo "✗ DNS resolution failed"
fi
echo ""

# Port connectivity test
echo "3. Port Connectivity Test:"
ports=(80 443 8000)
for port in "${ports[@]}"; do
    echo -n "Port $port: "
    if nc -z -w5 localhost $port 2>/dev/null; then
        echo "✓ Open"
    else
        echo "✗ Closed/Filtered"
    fi
done
echo ""

# SSL/TLS test
echo "4. SSL/TLS Test:"
echo -n "SSL handshake: "
if echo | openssl s_client -connect dev.inqilabgroup.com:443 -servername dev.inqilabgroup.com > /dev/null 2>&1; then
    echo "✓ Success"
    
    # Check SSL details
    ssl_info=$(echo | openssl s_client -connect dev.inqilabgroup.com:443 -servername dev.inqilabgroup.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null)
    echo "SSL Certificate Details:"
    echo "$ssl_info" | sed 's/^/  /'
else
    echo "✗ Failed"
fi
echo ""

# Network interface test
echo "5. Network Interface Status:"
if command -v ip > /dev/null; then
    echo "Active interfaces:"
    ip addr show | grep -E "(inet|UP)" | sed 's/^/  /'
else
    echo "Network interfaces:"
    ifconfig | grep -E "(inet|UP)" | sed 's/^/  /'
fi
echo ""

# Routing test
echo "6. Routing Test:"
echo "Default gateway:"
if command -v ip > /dev/null; then
    ip route | grep default | sed 's/^/  /'
else
    route -n | grep "^0.0.0.0" | sed 's/^/  /'
fi
echo ""

# Firewall status
echo "7. Firewall Status:"
if command -v ufw > /dev/null; then
    echo "UFW Status:"
    ufw status verbose | sed 's/^/  /'
elif command -v iptables > /dev/null; then
    echo "IPTables rules (INPUT chain):"
    iptables -L INPUT -n | sed 's/^/  /'
else
    echo "No firewall tools found"
fi
echo ""

# Connection tracking
echo "8. Active Connections:"
echo "HTTPS connections:"
netstat -an | grep :443 | head -10 | sed 's/^/  /'
echo ""
echo "HTTP connections:"
netstat -an | grep :80 | head -5 | sed 's/^/  /'
echo ""

# Load and performance
echo "9. System Load:"
echo "Current load:"
uptime | sed 's/^/  /'
echo ""
echo "Memory usage:"
free -h | sed 's/^/  /'
echo ""

# Recent connection logs
echo "10. Recent Connection Logs:"
if [ -f /var/log/nginx/access.log ]; then
    echo "Recent nginx access (last 5 entries):"
    tail -5 /var/log/nginx/access.log | sed 's/^/  /'
else
    echo "Nginx access log not found"
fi
echo ""

if [ -f ./logs/ipm_api.log ]; then
    echo "Recent API requests (last 5 entries):"
    tail -5 ./logs/ipm_api.log | sed 's/^/  /'
else
    echo "API log not found"
fi

echo ""
echo "=== End of Network Diagnostics ==="
