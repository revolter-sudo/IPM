#!/usr/bin/env python3
"""
Test script for invoice APIs
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

from src.app.database.database import get_db
from src.app.database.models import Invoice, Project, User


def test_invoice_model():
    """Test if the Invoice model has the new fields"""
    print("Testing Invoice model...")

    db = next(get_db())

    # Check if there are any users
    users = db.query(User).all()
    print(f"Found {len(users)} users in database")

    # Check if there are any projects
    projects = db.query(Project).all()
    print(f"Found {len(projects)} projects in database")

    # Check if there are any invoices
    invoices = db.query(Invoice).all()
    print(f"Found {len(invoices)} invoices in database")

    # Test creating a new invoice with the new fields (if we have users and projects)
    if users and projects:
        user = users[0]
        project = projects[0]

        print(f"Testing with user: {user.name} and project: {project.name}")

        # Create a test invoice
        test_invoice = Invoice(
            project_id=project.uuid,
            client_name="Test Client",
            invoice_item="Test Item",
            amount=1000.0,
            description="Test invoice description",
            due_date=datetime(2025, 6, 15),
            status="uploaded",
            created_by=user.uuid,
        )

        try:
            db.add(test_invoice)
            db.commit()
            db.refresh(test_invoice)

            print("✅ Successfully created test invoice with new fields:")
            print(f"   UUID: {test_invoice.uuid}")
            print(f"   Client Name: {test_invoice.client_name}")
            print(f"   Invoice Item: {test_invoice.invoice_item}")
            print(f"   Amount: {test_invoice.amount}")
            print(f"   Due Date: {test_invoice.due_date}")
            print(f"   Description: {test_invoice.description}")

            # Clean up - delete the test invoice
            db.delete(test_invoice)
            db.commit()
            print("✅ Test invoice cleaned up successfully")

        except Exception as e:
            db.rollback()
            print(f"❌ Error creating test invoice: {str(e)}")
    else:
        print("⚠️  Cannot test invoice creation - no users or projects found")

    db.close()


if __name__ == "__main__":
    test_invoice_model()
