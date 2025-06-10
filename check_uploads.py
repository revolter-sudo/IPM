#!/usr/bin/env python3
import os
import sys


def check_uploads_directory(base_dir):
    """
    Check if the uploads directory exists and has the necessary subdirectories.
    Also checks if there are any files in these directories.
    """
    print(f"Checking uploads directory: {base_dir}")

    if not os.path.exists(base_dir):
        print(f"ERROR: Directory {base_dir} does not exist!")
        return False

    # Check for required subdirectories
    required_subdirs = ["payments", "admin", "khatabook_files"]
    for subdir in required_subdirs:
        subdir_path = os.path.join(base_dir, subdir)
        if not os.path.exists(subdir_path):
            print(f"Creating missing directory: {subdir_path}")
            os.makedirs(subdir_path, exist_ok=True)

        # Check if there are any files in this directory
        files = os.listdir(subdir_path)
        if files:
            print(f"Files found in {subdir_path}:")
            for file in files:
                file_path = os.path.join(subdir_path, file)
                file_size = os.path.getsize(file_path)
                print(f"  - {file} ({file_size} bytes)")
        else:
            print(f"No files found in {subdir_path}")

    return True


if __name__ == "__main__":
    # Use the provided directory or default to 'uploads'
    uploads_dir = sys.argv[1] if len(sys.argv) > 1 else "uploads"
    check_uploads_directory(uploads_dir)
