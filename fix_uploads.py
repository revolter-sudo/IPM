#!/usr/bin/env python3
"""
Script to check and fix file upload issues in the IPM application.

This script:
1. Creates missing upload directories
2. Checks database records for file paths
3. Verifies if files exist at the specified paths
4. Reports any issues found

Usage:
    python fix_uploads.py

Requirements:
    - SQLAlchemy
    - The application's database models
"""

import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application models
try:
    from src.app.database.models import User, PaymentFile, KhatabookFile, Invoice, Project
    from src.app.database.database import settings
except ImportError:
    print("Error: Could not import application models. Make sure you're running this script from the project root.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("upload_fix.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Create database connection
try:
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    logging.info("Connected to database successfully")
except Exception as e:
    logging.error(f"Failed to connect to database: {str(e)}")
    sys.exit(1)

def ensure_directories_exist():
    """Create all necessary upload directories if they don't exist."""
    directories = [
        "uploads",
        "uploads/payments",
        "uploads/payments/users",
        "uploads/admin",
        "uploads/khatabook_files",
        "uploads/invoices"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Created directory: {directory}")
        else:
            logging.info(f"Directory already exists: {directory}")

def check_user_photos():
    """Check if user photos exist at the paths specified in the database."""
    users = session.query(User).filter(User.photo_path.isnot(None)).all()
    logging.info(f"Found {len(users)} users with photo paths")
    
    issues = 0
    for user in users:
        # Extract the filename from the URL
        if not user.photo_path:
            continue
            
        if "uploads/payments/users/" in user.photo_path:
            filename = user.photo_path.split("uploads/payments/users/")[-1]
            file_path = os.path.join("uploads/payments/users", filename)
            
            if not os.path.exists(file_path):
                logging.warning(f"User {user.uuid}: Photo file not found at {file_path}")
                issues += 1
    
    return issues

def check_payment_files():
    """Check if payment files exist at the paths specified in the database."""
    payment_files = session.query(PaymentFile).filter(PaymentFile.is_deleted.is_(False)).all()
    logging.info(f"Found {len(payment_files)} payment files")
    
    issues = 0
    for pf in payment_files:
        if not pf.file_path:
            continue
            
        if not os.path.exists(pf.file_path):
            logging.warning(f"Payment file {pf.id}: File not found at {pf.file_path}")
            issues += 1
    
    return issues

def check_khatabook_files():
    """Check if khatabook files exist at the paths specified in the database."""
    kb_files = session.query(KhatabookFile).all()
    logging.info(f"Found {len(kb_files)} khatabook files")
    
    issues = 0
    for kbf in kb_files:
        if not kbf.file_path:
            continue
            
        # For khatabook files, we need to check if the file exists in the uploads directory
        filename = os.path.basename(kbf.file_path)
        file_path = os.path.join("uploads/khatabook_files", filename)
        
        if not os.path.exists(file_path):
            logging.warning(f"Khatabook file {kbf.id}: File not found at {file_path}")
            issues += 1
    
    return issues

def check_invoice_files():
    """Check if invoice files exist at the paths specified in the database."""
    invoices = session.query(Invoice).filter(Invoice.file_path.isnot(None)).all()
    logging.info(f"Found {len(invoices)} invoices with file paths")
    
    issues = 0
    for invoice in invoices:
        if not invoice.file_path:
            continue
            
        if not os.path.exists(invoice.file_path):
            logging.warning(f"Invoice {invoice.uuid}: File not found at {invoice.file_path}")
            issues += 1
    
    return issues

def check_po_documents():
    """Check if PO documents exist at the paths specified in the database."""
    projects = session.query(Project).filter(Project.po_document_path.isnot(None)).all()
    logging.info(f"Found {len(projects)} projects with PO document paths")
    
    issues = 0
    for project in projects:
        if not project.po_document_path:
            continue
            
        if not os.path.exists(project.po_document_path):
            logging.warning(f"Project {project.uuid}: PO document not found at {project.po_document_path}")
            issues += 1
    
    return issues

def main():
    """Main function to run all checks."""
    logging.info("Starting upload directory and file check")
    
    # Ensure all necessary directories exist
    ensure_directories_exist()
    
    # Check all file types
    user_photo_issues = check_user_photos()
    payment_file_issues = check_payment_files()
    khatabook_file_issues = check_khatabook_files()
    invoice_file_issues = check_invoice_files()
    po_document_issues = check_po_documents()
    
    total_issues = user_photo_issues + payment_file_issues + khatabook_file_issues + invoice_file_issues + po_document_issues
    
    logging.info(f"Check completed. Found {total_issues} issues:")
    logging.info(f"- User photos: {user_photo_issues}")
    logging.info(f"- Payment files: {payment_file_issues}")
    logging.info(f"- Khatabook files: {khatabook_file_issues}")
    logging.info(f"- Invoice files: {invoice_file_issues}")
    logging.info(f"- PO documents: {po_document_issues}")
    
    if total_issues > 0:
        logging.info("Please check the log file for details on the issues found.")
    else:
        logging.info("No issues found. All files appear to be in the correct locations.")

if __name__ == "__main__":
    main()
