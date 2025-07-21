#!/usr/bin/env python3
"""
Test script for the enhanced project creation and invoice flow implementation.
This script tests all the new functionality including multiple POs, invoice payments, and analytics.
"""

import requests
import json
import os
from datetime import datetime, date, timedelta
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_BASE_URL = f"{BASE_URL}/admin"

# Test data
TEST_PROJECT_DATA = {
    "name": "Test Project with Multiple POs",
    "description": "Testing multiple PO functionality",
    "location": "Test Location",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "po_balance": 2000.0,
    "estimated_balance": 2500.0,
    "actual_balance": 1500.0,
    "pos": [
        {
            "po_number": "PO001",
            "amount": 1000.0,
            "description": "First PO for materials"
        },
        {
            "po_number": "PO002",
            "amount": 1000.0,
            "description": "Second PO for labor"
        }
    ]
}

TEST_INVOICE_DATA = {
    "client_name": "ABC Construction Company",
    "invoice_item": "Construction Materials",
    "amount": 750.0,
    "description": "Invoice for construction materials",
    "due_date": "2025-06-15"
}

TEST_PAYMENT_DATA = {
    "amount": 250.0,
    "payment_date": "2025-06-20",
    "description": "Partial payment",
    "payment_method": "bank",
    "reference_number": "TXN123456"
}

class TestImplementation:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.project_id = None
        self.po_ids = []
        self.invoice_id = None
        
    def authenticate(self):
        """Authenticate with the API (implement based on your auth system)"""
        # This is a placeholder - implement based on your authentication system
        print("🔐 Authentication step - implement based on your auth system")
        # For now, we'll assume authentication is handled elsewhere
        return True
        
    def test_project_creation_with_multiple_pos(self):
        """Test creating a project with multiple POs"""
        print("\n📁 Testing Project Creation with Multiple POs...")
        
        try:
            # Prepare form data
            form_data = {
                'request': json.dumps(TEST_PROJECT_DATA)
            }
            
            # Create dummy PO files for testing
            files = {}
            for i in range(2):
                # Create a simple text file as a dummy PO document
                dummy_content = f"Dummy PO Document {i+1}\nPO Number: PO00{i+1}\nAmount: 1000.0"
                files[f'po_document_{i}'] = (f'po_document_{i}.txt', dummy_content, 'text/plain')
            
            response = self.session.post(
                f"{BASE_URL}/projects/create",
                data=form_data,
                files=files
            )
            
            if response.status_code == 201:
                result = response.json()
                self.project_id = result['data']['uuid']
                print(f"✅ Project created successfully: {self.project_id}")
                print(f"   POs created: {len(result['data'].get('pos', []))}")
                
                # Store PO IDs for later use
                for po in result['data'].get('pos', []):
                    self.po_ids.append(po['uuid'])
                    
                return True
            else:
                print(f"❌ Project creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error in project creation: {str(e)}")
            return False
    
    def test_invoice_upload_with_po_link(self):
        """Test uploading an invoice linked to a specific PO"""
        print("\n📄 Testing Invoice Upload with PO Link...")
        
        if not self.project_id or not self.po_ids:
            print("❌ Cannot test invoice upload - no project or PO IDs available")
            return False
            
        try:
            # Prepare invoice data with PO link
            invoice_data = TEST_INVOICE_DATA.copy()
            invoice_data['project_id'] = self.project_id
            invoice_data['project_po_id'] = self.po_ids[0]  # Link to first PO
            
            # Prepare form data
            form_data = {
                'request': json.dumps(invoice_data)
            }
            
            # Create dummy invoice file
            dummy_invoice = "Dummy Invoice Document\nAmount: 750.0\nDue Date: 2025-06-15"
            files = {
                'invoice_file': ('invoice.txt', dummy_invoice, 'text/plain')
            }
            
            response = self.session.post(
                f"{ADMIN_BASE_URL}/invoices",
                data=form_data,
                files=files
            )
            
            if response.status_code == 201:
                result = response.json()
                self.invoice_id = result['data']['uuid']
                print(f"✅ Invoice uploaded successfully: {self.invoice_id}")
                print(f"   Linked to PO: {invoice_data['project_po_id']}")
                return True
            else:
                print(f"❌ Invoice upload failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error in invoice upload: {str(e)}")
            return False
    
    def test_invoice_payment_creation(self):
        """Test creating multiple payments for an invoice"""
        print("\n💰 Testing Invoice Payment Creation...")
        
        if not self.invoice_id:
            print("❌ Cannot test payment creation - no invoice ID available")
            return False
            
        try:
            # Create first payment
            payment1_data = TEST_PAYMENT_DATA.copy()
            
            response1 = self.session.post(
                f"{ADMIN_BASE_URL}/invoices/{self.invoice_id}/payments",
                json=payment1_data
            )
            
            if response1.status_code == 201:
                result1 = response1.json()
                print(f"�� First payment created: {result1['data']['amount']}")
                print(f"   Invoice status: {result1['data']['invoice_payment_status']}")
                
                # Create second payment
                payment2_data = {
                    "amount": 300.0,
                    "payment_date": "2025-07-01",
                    "description": "Second payment",
                    "payment_method": "cash",
                    "reference_number": "CASH001"
                }
                
                response2 = self.session.post(
                    f"{ADMIN_BASE_URL}/invoices/{self.invoice_id}/payments",
                    json=payment2_data
                )
                
                if response2.status_code == 201:
                    result2 = response2.json()
                    print(f"✅ Second payment created: {result2['data']['amount']}")
                    print(f"   Invoice status: {result2['data']['invoice_payment_status']}")
                    return True
                else:
                    print(f"❌ Second payment creation failed: {response2.status_code}")
                    return False
            else:
                print(f"❌ First payment creation failed: {response1.status_code}")
                print(f"   Response: {response1.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error in payment creation: {str(e)}")
            return False
    
    def test_invoice_analytics(self):
        """Test the invoice analytics API"""
        print("\n📊 Testing Invoice Analytics...")
        
        if not self.project_id:
            print("❌ Cannot test analytics - no project ID available")
            return False
            
        try:
            response = self.session.get(
                f"{ADMIN_BASE_URL}/projects/{self.project_id}/invoice-analytics"
            )
            
            if response.status_code == 200:
                result = response.json()
                analytics_data = result['data']
                
                print(f"✅ Analytics retrieved successfully")
                print(f"   Project: {analytics_data['project_name']}")
                print(f"   Project End Date: {analytics_data['project_end_date']}")
                print(f"   Number of Invoices: {len(analytics_data['invoices'])}")
                
                for i, invoice in enumerate(analytics_data['invoices']):
                    print(f"   Invoice {i+1}:")
                    print(f"     - Amount: {invoice['invoice_amount']}")
                    print(f"     - PO Number: {invoice['po_number']}")
                    print(f"     - Payment Status: {invoice['payment_status']}")
                    print(f"     - Total Paid: {invoice['total_paid_amount']}")
                    print(f"     - Is Late: {invoice['is_late']}")
                
                return True
            else:
                print(f"❌ Analytics retrieval failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error in analytics retrieval: {str(e)}")
            return False
    
    def test_payment_listing(self):
        """Test listing payments for an invoice"""
        print("\n📋 Testing Payment Listing...")
        
        if not self.invoice_id:
            print("❌ Cannot test payment listing - no invoice ID available")
            return False
            
        try:
            response = self.session.get(
                f"{ADMIN_BASE_URL}/invoices/{self.invoice_id}/payments"
            )
            
            if response.status_code == 200:
                result = response.json()
                payment_data = result['data']
                
                print(f"✅ Payments listed successfully")
                print(f"   Invoice Amount: {payment_data['invoice_amount']}")
                print(f"   Payment Status: {payment_data['payment_status']}")
                print(f"   Total Paid: {payment_data['total_paid_amount']}")
                print(f"   Remaining: {payment_data['remaining_amount']}")
                print(f"   Number of Payments: {len(payment_data['payments'])}")
                
                for i, payment in enumerate(payment_data['payments']):
                    print(f"   Payment {i+1}:")
                    print(f"     - Amount: {payment['amount']}")
                    print(f"     - Date: {payment['payment_date']}")
                    print(f"     - Method: {payment['payment_method']}")
                    print(f"     - Reference: {payment['reference_number']}")
                
                return True
            else:
                print(f"❌ Payment listing failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error in payment listing: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Implementation Tests...")
        print("=" * 50)
        
        tests = [
            ("Authentication", self.authenticate),
            ("Project Creation with Multiple POs", self.test_project_creation_with_multiple_pos),
            ("Invoice Upload with PO Link", self.test_invoice_upload_with_po_link),
            ("Invoice Payment Creation", self.test_invoice_payment_creation),
            ("Payment Listing", self.test_payment_listing),
            ("Invoice Analytics", self.test_invoice_analytics),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {str(e)}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status}: {test_name}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("��� All tests passed! Implementation is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the implementation.")
        
        return passed == total

def main():
    """Main function to run the tests"""
    print("🧪 Enhanced Project and Invoice Flow Test Suite")
    print("This script tests the implementation of:")
    print("1. Multiple PO support in project creation")
    print("2. Invoice linking to specific POs")
    print("3. Multiple payment records per invoice")
    print("4. Invoice analytics with late payment detection")
    print()
    
    # Note about running the tests
    print("⚠️  NOTE: This test script requires:")
    print("1. The application server to be running")
    print("2. Proper authentication setup")
    print("3. Database migrations to be applied")
    print()
    
    response = input("Do you want to proceed with the tests? (y/N): ")
    if response.lower() != 'y':
        print("Tests cancelled.")
        return
    
    tester = TestImplementation()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Run the database migration: alembic upgrade head")
        print("2. Test the APIs manually using the provided examples")
        print("3. Verify file uploads are working correctly")
        print("4. Check the analytics data for accuracy")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Ensure the server is running on the correct port")
        print("2. Check authentication is properly configured")
        print("3. Verify database migrations have been applied")
        print("4. Check server logs for any errors")

if __name__ == "__main__":
    main()