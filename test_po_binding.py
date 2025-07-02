#!/usr/bin/env python3
"""
Test script for PO document binding functionality
This script tests various scenarios of binding PO documents with amounts and descriptions
"""

import json
import os
import tempfile
from datetime import datetime

import requests

# Configuration
BASE_URL = "http://localhost:8000"
TEST_PROJECT_NAME = (
    f"PO Binding Test Project {datetime.now().strftime('%Y%m%d_%H%M%S')}"
)


class POBindingTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_files = {}

    def create_test_files(self):
        """Create temporary test files for PO documents"""
        print("📁 Creating test files...")

        # Create different types of test files
        test_file_contents = {
            "po_document_0.pdf": b"PDF content for PO001 - Materials Purchase Order",
            "po_document_1.txt": b"Text content for PO002 - Labor Purchase Order",
            "po_document_2.pdf": b"PDF content for PO003 - Equipment Rental Order",
            "po_document_3.txt": b"Text content for PO004 - Services Purchase Order",
        }

        for filename, content in test_file_contents.items():
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(filename)[1]
            )
            temp_file.write(content)
            temp_file.close()
            self.test_files[filename] = temp_file.name
            print(f"   Created: {filename} -> {temp_file.name}")

    def cleanup_test_files(self):
        """Clean up temporary test files"""
        print("🧹 Cleaning up test files...")
        for filename, filepath in self.test_files.items():
            try:
                os.unlink(filepath)
                print(f"   Deleted: {filename}")
            except:
                pass

    def test_sequential_binding(self):
        """Test 1: Sequential binding (default behavior)"""
        print("\n🧪 Test 1: Sequential Binding (Default)")
        print("=" * 50)

        project_data = {
            "name": f"{TEST_PROJECT_NAME} - Sequential",
            "description": "Testing sequential PO binding",
            "location": "Test Location",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "po_balance": 3000.0,
            "estimated_balance": 3500.0,
            "actual_balance": 2500.0,
            "pos": [
                {
                    "po_number": "PO001",
                    "amount": 1000.0,
                    "description": "Materials purchase order",
                    # No file_index - should default to 0
                },
                {
                    "po_number": "PO002",
                    "amount": 2000.0,
                    "description": "Labor purchase order",
                    # No file_index - should default to 1
                },
            ],
        }

        return self._send_project_request(
            project_data,
            files={
                "po_document_0": self.test_files["po_document_0.pdf"],
                "po_document_1": self.test_files["po_document_1.txt"],
            },
            test_name="Sequential Binding",
        )

    def test_explicit_binding(self):
        """Test 2: Explicit file index binding"""
        print("\n🧪 Test 2: Explicit File Index Binding")
        print("=" * 50)

        project_data = {
            "name": f"{TEST_PROJECT_NAME} - Explicit",
            "description": "Testing explicit PO binding",
            "location": "Test Location",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "po_balance": 4000.0,
            "estimated_balance": 4500.0,
            "actual_balance": 3500.0,
            "pos": [
                {
                    "po_number": "PO001",
                    "amount": 1500.0,
                    "description": "Materials purchase order",
                    "file_index": 2,  # Bind to po_document_2
                },
                {
                    "po_number": "PO002",
                    "amount": 2500.0,
                    "description": "Labor purchase order",
                    "file_index": 0,  # Bind to po_document_0
                },
            ],
        }

        return self._send_project_request(
            project_data,
            files={
                "po_document_0": self.test_files["po_document_0.pdf"],
                "po_document_2": self.test_files["po_document_2.pdf"],
            },
            test_name="Explicit Binding",
        )

    def test_mixed_binding(self):
        """Test 3: Mixed binding (some POs with documents, some without)"""
        print("\n🧪 Test 3: Mixed Binding (Some POs without documents)")
        print("=" * 50)

        project_data = {
            "name": f"{TEST_PROJECT_NAME} - Mixed",
            "description": "Testing mixed PO binding",
            "location": "Test Location",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "po_balance": 5000.0,
            "estimated_balance": 5500.0,
            "actual_balance": 4500.0,
            "pos": [
                {
                    "po_number": "PO001",
                    "amount": 1000.0,
                    "description": "PO with document",
                    "file_index": 0,
                },
                {
                    "po_number": "PO002",
                    "amount": 2000.0,
                    "description": "PO without document",
                    # No file_index, no document
                },
                {
                    "po_number": "PO003",
                    "amount": 2000.0,
                    "description": "Another PO with document",
                    "file_index": 1,
                },
            ],
        }

        return self._send_project_request(
            project_data,
            files={
                "po_document_0": self.test_files["po_document_0.pdf"],
                "po_document_1": self.test_files["po_document_1.txt"],
            },
            test_name="Mixed Binding",
        )

    def test_validation_errors(self):
        """Test 4: Validation error scenarios"""
        print("\n🧪 Test 4: Validation Error Scenarios")
        print("=" * 50)

        # Test 4a: Invalid amount
        print("\n   Test 4a: Invalid Amount (should fail)")
        project_data = {
            "name": f"{TEST_PROJECT_NAME} - Invalid Amount",
            "description": "Testing invalid amount",
            "pos": [
                {
                    "po_number": "PO001",
                    "amount": -100.0,  # Invalid negative amount
                    "description": "Invalid PO",
                }
            ],
        }

        result_4a = self._send_project_request(
            project_data, files={}, test_name="Invalid Amount", expect_failure=True
        )

        # Test 4b: Duplicate PO numbers
        print("\n   Test 4b: Duplicate PO Numbers (should fail)")
        project_data = {
            "name": f"{TEST_PROJECT_NAME} - Duplicate PO",
            "description": "Testing duplicate PO numbers",
            "pos": [
                {"po_number": "PO001", "amount": 1000.0, "description": "First PO"},
                {
                    "po_number": "PO001",  # Duplicate PO number
                    "amount": 2000.0,
                    "description": "Duplicate PO",
                },
            ],
        }

        result_4b = self._send_project_request(
            project_data,
            files={},
            test_name="Duplicate PO Numbers",
            expect_failure=True,
        )

        # Test 4c: Invalid file index
        print("\n   Test 4c: Invalid File Index (should fail)")
        project_data = {
            "name": f"{TEST_PROJECT_NAME} - Invalid Index",
            "description": "Testing invalid file index",
            "pos": [
                {
                    "po_number": "PO001",
                    "amount": 1000.0,
                    "description": "PO with invalid file index",
                    "file_index": 15,  # Invalid index (max is 9)
                }
            ],
        }

        result_4c = self._send_project_request(
            project_data, files={}, test_name="Invalid File Index", expect_failure=True
        )

        return all([result_4a, result_4b, result_4c])

    def test_large_project(self):
        """Test 5: Large project with multiple POs"""
        print("\n🧪 Test 5: Large Project with Multiple POs")
        print("=" * 50)

        project_data = {
            "name": f"{TEST_PROJECT_NAME} - Large",
            "description": "Testing large project with multiple POs",
            "location": "Large Test Location",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "po_balance": 10000.0,
            "estimated_balance": 12000.0,
            "actual_balance": 8000.0,
            "pos": [
                {
                    "po_number": "PO001",
                    "amount": 2000.0,
                    "description": "Materials - Phase 1",
                    "file_index": 0,
                },
                {
                    "po_number": "PO002",
                    "amount": 3000.0,
                    "description": "Labor - Phase 1",
                    "file_index": 1,
                },
                {
                    "po_number": "PO003",
                    "amount": 1500.0,
                    "description": "Equipment Rental",
                    "file_index": 2,
                },
                {
                    "po_number": "PO004",
                    "amount": 2500.0,
                    "description": "Services and Consulting",
                    "file_index": 3,
                },
                {
                    "po_number": "PO005",
                    "amount": 1000.0,
                    "description": "Miscellaneous Expenses",
                    # No document for this PO
                },
            ],
        }

        return self._send_project_request(
            project_data,
            files={
                "po_document_0": self.test_files["po_document_0.pdf"],
                "po_document_1": self.test_files["po_document_1.txt"],
                "po_document_2": self.test_files["po_document_2.pdf"],
                "po_document_3": self.test_files["po_document_3.txt"],
            },
            test_name="Large Project",
        )

    def _send_project_request(
        self, project_data, files, test_name, expect_failure=False
    ):
        """Send project creation request and analyze response"""
        try:
            # Prepare form data
            form_data = {"request": json.dumps(project_data)}

            # Prepare file uploads
            file_uploads = {}
            for field_name, file_path in files.items():
                if os.path.exists(file_path):
                    file_uploads[field_name] = (
                        os.path.basename(file_path),
                        open(file_path, "rb"),
                        "application/octet-stream",
                    )

            # Send request
            response = self.session.post(
                f"{BASE_URL}/projects/create", data=form_data, files=file_uploads
            )

            # Close file handles
            for file_handle in file_uploads.values():
                file_handle[1].close()

            # Analyze response
            if expect_failure:
                if response.status_code != 201:
                    print(f"   ✅ {test_name}: Expected failure occurred")
                    print(f"      Status: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(
                            f"      Message: {error_data.get('message', 'No message')}"
                        )
                    except:
                        print(f"      Response: {response.text[:200]}...")
                    return True
                else:
                    print(f"   ❌ {test_name}: Expected failure but request succeeded")
                    return False
            else:
                if response.status_code == 201:
                    result = response.json()
                    self._analyze_success_response(result, test_name)
                    return True
                else:
                    print(f"   ❌ {test_name}: Request failed")
                    print(f"      Status: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(
                            f"      Message: {error_data.get('message', 'No message')}"
                        )
                    except:
                        print(f"      Response: {response.text[:200]}...")
                    return False

        except Exception as e:
            print(f"   ❌ {test_name}: Exception occurred - {str(e)}")
            return False

    def _analyze_success_response(self, result, test_name):
        """Analyze successful response for binding information"""
        print(f"   ✅ {test_name}: Project created successfully")

        data = result.get("data", {})
        print(f"      Project UUID: {data.get('uuid')}")
        print(f"      Project Name: {data.get('name')}")

        po_summary = data.get("po_summary", {})
        print(f"      Total POs: {po_summary.get('total_pos', 0)}")
        print(f"      Total Amount: ${po_summary.get('total_po_amount', 0):,.2f}")
        print(f"      Files Uploaded: {po_summary.get('files_uploaded', 0)}")
        print(f"      Files Missing: {po_summary.get('files_missing', 0)}")

        pos = data.get("pos", [])
        print("      PO Details:")
        for i, po in enumerate(pos):
            binding = po.get("file_binding", {})
            print(f"        PO {i+1}: {po.get('po_number')} - ${po.get('amount'):,.2f}")
            print(f"               Description: {po.get('description')}")
            print(f"               Has Document: {po.get('has_document')}")
            if binding.get("successfully_bound"):
                print(f"               File Index: {binding.get('file_index')}")
                print(
                    f"               Original File: {binding.get('original_filename')}"
                )
                print(
                    f"               File Size: {binding.get('file_size_bytes')} bytes"
                )
            print()

    def run_all_tests(self):
        """Run all PO binding tests"""
        print("🚀 Starting PO Document Binding Tests")
        print("=" * 60)

        try:
            # Create test files
            self.create_test_files()

            # Run tests
            tests = [
                ("Sequential Binding", self.test_sequential_binding),
                ("Explicit Binding", self.test_explicit_binding),
                ("Mixed Binding", self.test_mixed_binding),
                ("Validation Errors", self.test_validation_errors),
                ("Large Project", self.test_large_project),
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
            print("\n" + "=" * 60)
            print("📊 Test Results Summary")
            print("=" * 60)

            passed = 0
            total = len(results)

            for test_name, result in results:
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"{status}: {test_name}")
                if result:
                    passed += 1

            print(f"\nOverall: {passed}/{total} tests passed")

            if passed == total:
                print("🎉 All PO binding tests passed!")
            else:
                print("⚠️  Some tests failed. Please check the implementation.")

            return passed == total

        finally:
            # Clean up
            self.cleanup_test_files()


def main():
    """Main function to run the PO binding tests"""
    print("🧪 PO Document Binding Test Suite")
    print("This script tests the enhanced PO document binding functionality:")
    print("1. Sequential binding (default behavior)")
    print("2. Explicit file index binding")
    print("3. Mixed binding (some POs with/without documents)")
    print("4. Validation error scenarios")
    print("5. Large projects with multiple POs")
    print()

    # Note about running the tests
    print("⚠️  NOTE: This test script requires:")
    print("1. The application server to be running on localhost:8000")
    print("2. Proper authentication setup (or authentication disabled for testing)")
    print("3. Database migrations to be applied")
    print("4. Write permissions for file uploads")
    print()

    response = input("Do you want to proceed with the PO binding tests? (y/N): ")
    if response.lower() != "y":
        print("Tests cancelled.")
        return

    tester = POBindingTester()
    success = tester.run_all_tests()

    if success:
        print("\n🎯 Next Steps:")
        print("1. Verify the created projects in the database")
        print("2. Check that PO documents are properly stored")
        print("3. Test the invoice creation against specific POs")
        print("4. Verify the analytics API includes PO information")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check server logs for detailed error information")
        print("2. Verify database schema is up to date")
        print("3. Ensure file upload directory has write permissions")
        print("4. Check authentication configuration")


if __name__ == "__main__":
    main()
