#!/bin/bash
# Script to set up nginx configuration for dev.inqilabgroup.com

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Define paths
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
CONFIG_FILE="dev.inqilabgroup.com.conf"
UPLOADS_DIR="/root/IPM/uploads"

# Create uploads directories if they don't exist
echo "Creating uploads directories..."
mkdir -p "$UPLOADS_DIR"
mkdir -p "$UPLOADS_DIR/payments"
mkdir -p "$UPLOADS_DIR/payments/users"
mkdir -p "$UPLOADS_DIR/admin"
mkdir -p "$UPLOADS_DIR/khatabook_files"
mkdir -p "$UPLOADS_DIR/invoices"

# Set proper permissions
echo "Setting permissions..."
chown -R www-data:www-data "$UPLOADS_DIR"
chmod -R 755 "$UPLOADS_DIR"

# Copy the configuration file
echo "Installing nginx configuration..."
cp "$CONFIG_FILE" "$NGINX_AVAILABLE/"

# Create symlink if it doesn't exist
if [ ! -f "$NGINX_ENABLED/$CONFIG_FILE" ]; then
  ln -s "$NGINX_AVAILABLE/$CONFIG_FILE" "$NGINX_ENABLED/"
  echo "Created symlink for configuration"
else
  echo "Symlink already exists"
fi

# Check if default configuration is enabled and disable it if needed
if [ -f "$NGINX_ENABLED/default" ]; then
  echo "Disabling default configuration..."
  rm "$NGINX_ENABLED/default"
fi

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
