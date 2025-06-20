#!/bin/bash
# Script to check for a specific file and fix permissions

# Define the file path
FILE_PATH="/root/IPM/uploads/payments/users/c25cc06d-8629-4602-99ce-87dc6bfcecce.webp"
DIR_PATH="/root/IPM/uploads/payments/users"
UPLOADS_DIR="/root/IPM/uploads"

# Check if the uploads directory exists
if [ ! -d "$UPLOADS_DIR" ]; then
  echo "Main uploads directory does not exist: $UPLOADS_DIR"
  echo "Creating directory..."
  mkdir -p "$UPLOADS_DIR"
  echo "Directory created."
fi

# Create all necessary subdirectories
echo "Creating all necessary subdirectories..."
mkdir -p "$UPLOADS_DIR/payments"
mkdir -p "$UPLOADS_DIR/payments/users"
mkdir -p "$UPLOADS_DIR/admin"
mkdir -p "$UPLOADS_DIR/khatabook_files"
mkdir -p "$UPLOADS_DIR/invoices"

# Set permissions for all directories
echo "Setting permissions for all directories..."
# First, make sure the /root directory is accessible by nginx
chmod 755 /root
# Then set permissions for the uploads directory and its contents
find "$UPLOADS_DIR" -type d -exec chmod 755 {} \;
find "$UPLOADS_DIR" -type d -exec chown www-data:www-data {} \;
# Make sure all existing files are readable
find "$UPLOADS_DIR" -type f -exec chmod 644 {} \;
find "$UPLOADS_DIR" -type f -exec chown www-data:www-data {} \;

# Check if the specific file exists
if [ -f "$FILE_PATH" ]; then
  echo "File exists: $FILE_PATH"

  # Check file permissions
  PERMS=$(stat -c "%a %U:%G" "$FILE_PATH")
  echo "Current permissions: $PERMS"

  # Fix permissions if needed
  echo "Setting proper permissions..."
  chown www-data:www-data "$FILE_PATH"
  chmod 644 "$FILE_PATH"

  PERMS=$(stat -c "%a %U:%G" "$FILE_PATH")
  echo "New permissions: $PERMS"
else
  echo "File does not exist: $FILE_PATH"

  # List files in the directory
  echo "Files in directory:"
  ls -la "$DIR_PATH"

  # Create a test file with the same name
  echo "Creating a test file with the same name..."
  echo "This is a test file" > "$FILE_PATH"
  chown www-data:www-data "$FILE_PATH"
  chmod 644 "$FILE_PATH"

  echo "Test file created. You can check if it's accessible at:"
  echo "https://dev.inqilabgroup.com/uploads/payments/users/c25cc06d-8629-4602-99ce-87dc6bfcecce.webp"
fi

# Create additional test files in each directory
echo "Creating test files in each directory..."
echo "Test file for root uploads" > "$UPLOADS_DIR/test.txt"
echo "Test file for payments" > "$UPLOADS_DIR/payments/test.txt"
echo "Test file for users" > "$UPLOADS_DIR/payments/users/test.txt"
echo "Test file for admin" > "$UPLOADS_DIR/admin/test.txt"
echo "Test file for khatabook" > "$UPLOADS_DIR/khatabook_files/test.txt"
echo "Test file for invoices" > "$UPLOADS_DIR/invoices/test.txt"

# Set permissions for all test files
find "$UPLOADS_DIR" -type f -name "test.txt" -exec chmod 644 {} \;
find "$UPLOADS_DIR" -type f -name "test.txt" -exec chown www-data:www-data {} \;

echo "Test files created. You can check if they are accessible at:"
echo "https://dev.inqilabgroup.com/uploads/test.txt"
echo "https://dev.inqilabgroup.com/uploads/payments/test.txt"
echo "https://dev.inqilabgroup.com/uploads/payments/users/test.txt"
echo "https://dev.inqilabgroup.com/uploads/admin/test.txt"
echo "https://dev.inqilabgroup.com/uploads/khatabook_files/test.txt"
echo "https://dev.inqilabgroup.com/uploads/invoices/test.txt"

# Restart nginx to apply changes
echo "Restarting nginx..."
systemctl restart nginx

echo "Check complete! Please verify that the files are accessible."
