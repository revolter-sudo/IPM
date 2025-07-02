#!/bin/bash
# Alternative solution that doesn't require changing /root permissions

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Define paths
UPLOADS_DIR="/root/IPM/uploads"
PUBLIC_DIR="/var/www/uploads"
NGINX_CONF="/etc/nginx/sites-available/dev.inqilabgroup.com.conf"

# Create public directory if it doesn't exist
echo "Creating public directory..."
mkdir -p "$PUBLIC_DIR"

# Create symbolic link if it doesn't exist
if [ ! -L "$PUBLIC_DIR" ]; then
  echo "Creating symbolic link..."
  # Remove the directory first (it's empty, we just created it)
  rmdir "$PUBLIC_DIR"
  # Create the symbolic link
  ln -s "$UPLOADS_DIR" "$PUBLIC_DIR"
  echo "Symbolic link created."
else
  echo "Symbolic link already exists."
fi

# Set permissions for the uploads directory
echo "Setting permissions for uploads directory..."
chown -R www-data:www-data "$UPLOADS_DIR"
chmod -R 755 "$UPLOADS_DIR"
find "$UPLOADS_DIR" -type f -exec chmod 644 {} \;

# Set permissions for the public directory
echo "Setting permissions for public directory..."
chown -R www-data:www-data "$PUBLIC_DIR"
chmod 755 "$PUBLIC_DIR"

# Update nginx configuration to use the public directory
echo "Updating nginx configuration..."
sed -i 's|alias /root/IPM/uploads/;|alias /var/www/uploads/;|g' "$NGINX_CONF"

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
  echo "Configuration test successful. Reloading nginx..."
  systemctl reload nginx
  echo "Nginx reloaded successfully."

  # Create a test file to verify uploads are working
  TEST_FILE="$UPLOADS_DIR/test.txt"
  echo "This is a test file to verify nginx configuration" > "$TEST_FILE"
  chown www-data:www-data "$TEST_FILE"
  chmod 644 "$TEST_FILE"

  echo "Test file created at $TEST_FILE"
  echo "You can verify it's accessible at https://dev.inqilabgroup.com/uploads/test.txt"
else
  echo "Configuration test failed. Please check the nginx error log."
fi

echo "Setup complete!"
