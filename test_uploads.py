#!/usr/bin/env python3
"""
Script to test file uploads and accessibility in the IPM application.

This script:
1. Creates a test file in each upload directory
2. Checks if the file is accessible via HTTP
3. Verifies file permissions

Usage:
    python test_uploads.py
"""

import logging
import os
import subprocess

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("upload_test.log"), logging.StreamHandler()],
)

# Base URL of the application
BASE_URL = "https://dev.inqilabgroup.com"


def create_test_files():
    """Create test files in each upload directory and check permissions."""
    directories = [
        "uploads",
        "uploads/payments",
        "uploads/payments/users",
        "uploads/admin",
        "uploads/khatabook_files",
        "uploads/invoices",
    ]

    test_files = []

    for directory in directories:
        # Create directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Created directory: {directory}")

        # Check directory permissions
        dir_permissions = subprocess.run(
            ["ls", "-ld", directory], capture_output=True, text=True
        ).stdout.strip()
        logging.info(f"Directory permissions: {dir_permissions}")

        # Create a test file
        test_file = os.path.join(directory, "test_file.txt")
        with open(test_file, "w") as f:
            f.write("This is a test file to check upload accessibility.")

        # Check file permissions
        file_permissions = subprocess.run(
            ["ls", "-l", test_file], capture_output=True, text=True
        ).stdout.strip()
        logging.info(f"File permissions: {file_permissions}")

        # Try to make the file readable by nginx
        subprocess.run(["chmod", "644", test_file])

        test_files.append(test_file)

    return test_files


def check_file_accessibility(test_files):
    """Check if the test files are accessible via HTTP."""
    for test_file in test_files:
        # Convert local path to URL path
        url_path = test_file.replace("\\", "/")  # For Windows compatibility
        url = f"{BASE_URL}/{url_path}"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                logging.info(f"File accessible: {url}")
            else:
                logging.warning(
                    f"File not accessible: {url}, Status code: {response.status_code}"
                )
        except Exception as e:
            logging.error(f"Error accessing file: {url}, Error: {str(e)}")


def check_nginx_config():
    """Check the nginx configuration for the uploads location."""
    try:
        # Check if nginx is running
        nginx_status = subprocess.run(
            ["systemctl", "status", "nginx"], capture_output=True, text=True
        )
        logging.info(
            f"Nginx status: {'running' if nginx_status.returncode == 0 else 'not running'}"
        )

        # Check nginx configuration
        nginx_config = subprocess.run(["nginx", "-T"], capture_output=True, text=True)

        # Look for uploads location in nginx config
        uploads_config = [
            line for line in nginx_config.stdout.split("\n") if "uploads" in line
        ]
        logging.info("Nginx uploads configuration:")
        for line in uploads_config:
            logging.info(line)

    except Exception as e:
        logging.error(f"Error checking nginx configuration: {str(e)}")


def check_specific_file(file_path):
    """Check if a specific file exists and is accessible."""
    # Check if file exists locally
    if os.path.exists(file_path):
        logging.info(f"File exists locally: {file_path}")

        # Check file permissions
        file_permissions = subprocess.run(
            ["ls", "-l", file_path], capture_output=True, text=True
        ).stdout.strip()
        logging.info(f"File permissions: {file_permissions}")

        # Try to make the file readable by nginx
        subprocess.run(["chmod", "644", file_path])
    else:
        logging.warning(f"File does not exist locally: {file_path}")

        # Check if the directory exists
        directory = os.path.dirname(file_path)
        if os.path.exists(directory):
            logging.info(f"Directory exists: {directory}")

            # List files in the directory
            files = os.listdir(directory)
            logging.info(f"Files in directory: {files}")
        else:
            logging.warning(f"Directory does not exist: {directory}")


def main():
    """Main function to run all tests."""
    logging.info("Starting upload accessibility tests")

    # Create test files and check permissions
    test_files = create_test_files()

    # Check if the test files are accessible via HTTP
    check_file_accessibility(test_files)

    # Check nginx configuration
    check_nginx_config()

    # Check the specific file that's giving 404
    specific_file = "uploads/payments/users/c25cc06d-8629-4602-99ce-87dc6bfcecce.webp"
    check_specific_file(specific_file)

    logging.info("Tests completed. Check the log file for details.")


if __name__ == "__main__":
    main()
