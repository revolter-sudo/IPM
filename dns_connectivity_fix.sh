#!/bin/bash

# DNS and Connectivity Diagnostic Script
# This script helps diagnose DNS resolution and connectivity issues

echo "=== DNS and Connectivity Diagnostics ==="
echo "Timestamp: $(date)"
echo ""

# Check DNS resolution from multiple perspectives
echo "1. DNS Resolution Tests:"
echo "Testing dashboard.inqilabgroup.com resolution..."

# Test with different DNS servers
dns_servers=("8.8.8.8" "1.1.1.1" "208.67.222.222")
for dns in "${dns_servers[@]}"; do
    echo -n "  Using DNS $dns: "
    if nslookup dashboard.inqilabgroup.com $dns > /dev/null 2>&1; then
        ip=$(nslookup dashboard.inqilabgroup.com $dns | grep -A1 "Name:" | tail -1 | awk '{print $2}' 2>/dev/null || nslookup dashboard.inqilabgroup.com $dns | grep "Address:" | tail -1 | awk '{print $2}')
        echo "✓ Resolved to $ip"
    else
        echo "✗ Failed"
    fi
done

# Check local DNS configuration
echo ""
echo "2. Local DNS Configuration:"
echo "Current DNS servers:"
if [ -f /etc/resolv.conf ]; then
    grep nameserver /etc/resolv.conf | sed 's/^/  /'
else
    echo "  /etc/resolv.conf not found"
fi

# Test DNS propagation
echo ""
echo "3. DNS Propagation Check:"
echo -n "A record for dashboard.inqilabgroup.com: "
if dig +short dashboard.inqilabgroup.com > /dev/null 2>&1; then
    ip=$(dig +short dashboard.inqilabgroup.com)
    echo "✓ $ip"
else
    echo "✗ No A record found"
fi

# Check if the server can resolve its own domain
echo ""
echo "4. Self-Resolution Test:"
echo -n "Can server resolve its own domain: "
if ping -c 1 dashboard.inqilabgroup.com > /dev/null 2>&1; then
    echo "✓ Success"
else
    echo "✗ Failed - This could be the issue!"
fi

# Check network interfaces and routing
echo ""
echo "5. Network Interface Status:"
echo "Active network interfaces:"
ip addr show | grep -E "(inet|UP|DOWN)" | sed 's/^/  /'

echo ""
echo "6. Routing Table:"
echo "Default routes:"
ip route | grep default | sed 's/^/  /'

# Check firewall rules
echo ""
echo "7. Firewall Status:"
if command -v ufw > /dev/null; then
    echo "UFW Status:"
    ufw status | sed 's/^/  /'
elif command -v iptables > /dev/null; then
    echo "IPTables INPUT rules:"
    iptables -L INPUT -n | head -10 | sed 's/^/  /'
else
    echo "No firewall tools found"
fi

# Check if ports are accessible externally
echo ""
echo "8. External Port Accessibility:"
ports=(80 443)
for port in "${ports[@]}"; do
    echo -n "Port $port externally accessible: "
    # Try to connect from external perspective
    if timeout 5 bash -c "</dev/tcp/dashboard.inqilabgroup.com/$port" 2>/dev/null; then
        echo "✓ Accessible"
    else
        echo "✗ Not accessible or timeout"
    fi
done

# Check SSL certificate validity
echo ""
echo "9. SSL Certificate Check:"
echo -n "SSL certificate validity: "
if echo | openssl s_client -connect dashboard.inqilabgroup.com:443 -servername dashboard.inqilabgroup.com 2>/dev/null | openssl x509 -noout -dates > /dev/null 2>&1; then
    echo "✓ Valid"
    cert_dates=$(echo | openssl s_client -connect dashboard.inqilabgroup.com:443 -servername dashboard.inqilabgroup.com 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
    echo "$cert_dates" | sed 's/^/  /'
else
    echo "✗ Invalid or unreachable"
fi

# Check application health
echo ""
echo "10. Application Health:"
echo -n "Local application health: "
if curl -s -f http://localhost:8000/healthcheck > /dev/null; then
    echo "✓ Healthy"
else
    echo "✗ Unhealthy"
fi

echo -n "External application health: "
if curl -s -f https://dashboard.inqilabgroup.com/healthcheck > /dev/null; then
    echo "✓ Healthy"
else
    echo "✗ Unhealthy"
fi

# Check recent logs for DNS/network errors
echo ""
echo "11. Recent Network Errors:"
echo "Nginx error log (last 10 lines):"
if [ -f /var/log/nginx/error.log ]; then
    tail -10 /var/log/nginx/error.log | grep -E "(upstream|timeout|connection|resolve)" | sed 's/^/  /' || echo "  No recent network errors"
else
    echo "  Nginx error log not found"
fi

echo ""
echo "System log network errors:"
if [ -f /var/log/syslog ]; then
    tail -20 /var/log/syslog | grep -E "(network|dns|resolve)" | sed 's/^/  /' || echo "  No recent network errors"
else
    echo "  System log not found"
fi

# Provide recommendations
echo ""
echo "=== Recommendations ==="
echo ""

# Check if DNS resolution is the main issue
if ! nslookup dashboard.inqilabgroup.com > /dev/null 2>&1; then
    echo "🔴 CRITICAL: DNS resolution is failing!"
    echo "   - Check your domain's DNS records"
    echo "   - Verify nameservers are responding"
    echo "   - Contact your DNS provider"
    echo ""
fi

# Check if server can't resolve its own domain
if ! ping -c 1 dashboard.inqilabgroup.com > /dev/null 2>&1; then
    echo "🟡 WARNING: Server cannot resolve its own domain!"
    echo "   - Add entry to /etc/hosts: 127.0.0.1 dashboard.inqilabgroup.com"
    echo "   - Check local DNS configuration"
    echo ""
fi

# Check if application is down
if ! curl -s -f http://localhost:8000/healthcheck > /dev/null; then
    echo "🔴 CRITICAL: Application is not responding!"
    echo "   - Check Docker containers: docker ps"
    echo "   - Check application logs: docker-compose logs api"
    echo "   - Restart application: docker-compose restart"
    echo ""
fi

echo "=== End of Diagnostics ==="
