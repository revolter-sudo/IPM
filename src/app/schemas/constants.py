CAN_NOT_CREATE_PROJECT = "Not authorized to create a project."
PROJECT_NOT_FOUND = "Project does not exist"
CANT_APPROVE_PAYMENT = "Not authorized to approve payments"
PAYMENT_NOT_FOUND = "Payment request not found"
ONLY_PDFS_ALLOWED = "Only PDF files are allowed."
UPLOAD_DIR = "uploads/payments"
CANT_DECLINE_PAYMENTS = "Not authorized to decline payments"
PERSON_EXISTS = (
    "A person with the same account number or ifsc code already exists."
)

RoleStatusMapping = {
    "SiteEngineer": "requested",
    "ProjectManager": "verified",
    "Admin": "approved",
    "Accountant": "transffered",
    "SuperAdmin": "transffered"
}
HOST_URL = "http://147.93.31.224:8000"
