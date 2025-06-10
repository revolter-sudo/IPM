#!/usr/bin/env python3
import os
from urllib.parse import urljoin

import requests


def test_file_urls(base_url, uploads_dir):
    """
    Test if files in the uploads directory are accessible via the provided base URL.
    """
    print(f"Testing file URLs with base URL: {base_url}")

    for root, dirs, files in os.walk(uploads_dir):
        for file in files:
            # Get the relative path from the uploads directory
            rel_path = os.path.relpath(os.path.join(root, file), uploads_dir)

            # Construct the URL
            url = urljoin(base_url + "/uploads/", rel_path)

            # Test the URL
            try:
                response = requests.head(url, timeout=5)
                status = response.status_code
                status_text = "OK" if status == 200 else "FAILED"
                print(f"{status} {status_text}: {url}")
            except requests.exceptions.RequestException as e:
                print(f"ERROR: {url} - {str(e)}")


if __name__ == "__main__":
    # Use the provided base URL or default to localhost
    base_url = "https://dev.inqilabgroup.com"
    uploads_dir = "uploads"

    test_file_urls(base_url, uploads_dir)
