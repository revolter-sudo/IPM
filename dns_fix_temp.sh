#!/bin/bash

# Temporary DNS Fix Script
# This adds the correct IP mapping to /etc/hosts as a temporary solution

echo "=== Temporary DNS Fix ==="
echo "Adding correct IP mapping to /etc/hosts"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo privileges"
    echo "Usage: sudo ./dns_fix_temp.sh"
    exit 1
fi

# Backup hosts file
cp /etc/hosts /etc/hosts.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backed up /etc/hosts"

# Remove any existing entries for dashboard.inqilabgroup.com
sed -i '/dashboard\.inqilabgroup\.com/d' /etc/hosts
echo "✓ Removed existing entries"

# Add correct mapping
echo "147.93.31.224 dashboard.inqilabgroup.com" >> /etc/hosts
echo "✓ Added correct IP mapping: 147.93.31.224 dashboard.inqilabgroup.com"

echo ""
echo "Testing the fix..."

# Test local resolution
echo -n "Local DNS resolution: "
if ping -c 1 dashboard.inqilabgroup.com > /dev/null 2>&1; then
    resolved_ip=$(ping -c 1 dashboard.inqilabgroup.com | grep PING | awk '{print $3}' | tr -d '()')
    echo "✓ Resolves to $resolved_ip"
else
    echo "✗ Still failing"
fi

# Test HTTPS connectivity
echo -n "HTTPS connectivity: "
if curl -s -f https://dashboard.inqilabgroup.com/healthcheck > /dev/null; then
    echo "✓ Working"
else
    echo "✗ Still failing"
fi

echo ""
echo "=== Temporary Fix Applied ==="
echo ""
echo "This is a TEMPORARY solution for the server only."
echo "You still need to fix the DNS records with your domain provider:"
echo ""
echo "1. Log into your domain registrar/DNS provider"
echo "2. Find DNS settings for inqilabgroup.com"
echo "3. Update the A record for 'dashboard' subdomain:"
echo "   - Type: A"
echo "   - Name: dashboard"
echo "   - Value: 147.93.31.224"
echo "   - TTL: 300 (5 minutes) for quick propagation"
echo ""
echo "4. Remove or fix any incorrect AAAA (IPv6) records"
echo ""
echo "5. Wait for DNS propagation (can take 5 minutes to 48 hours)"
echo ""
echo "Users will still have issues until DNS is properly configured!"
