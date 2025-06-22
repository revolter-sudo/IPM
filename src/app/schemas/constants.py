import os
from dotenv import load_dotenv
load_dotenv()


CAN_NOT_CREATE_PROJECT = "Not authorized to create a project."
PROJECT_NOT_FOUND = "Project does not exist"
CANT_APPROVE_PAYMENT = "Not authorized to approve payments"
PAYMENT_NOT_FOUND = "Payment request not found"
ONLY_PDFS_ALLOWED = "Only PDF files are allowed."
UPLOAD_DIR = "uploads/payments"
UPLOAD_DIR_ADMIN = "uploads/admin"
KHATABOOK_FOLDER = "uploads/khatabook_files"
CANT_DECLINE_PAYMENTS = "Not authorized to decline payments"
PERSON_EXISTS = (
    "A person with the same account number or ifsc code already exists."
)

RoleStatusMapping = {
    "SiteEngineer": "requested",
    "ProjectManager": "verified",
    "Admin": "approved",
    "Accountant": "transferred",
    "SuperAdmin": "transferred"
}

# Payment type constants
KHATABOOK_PAYMENT_TYPE = "Khatabook"

# Khatabook entry type constants
KHATABOOK_ENTRY_TYPE_DEBIT = "Debit"
KHATABOOK_ENTRY_TYPE_CREDIT = "Credit"

HOST_URL = os.getenv("HOST_URL")
