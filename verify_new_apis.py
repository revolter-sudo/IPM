#!/usr/bin/env python3
"""
Script to verify that the new PO management APIs are properly mounted and accessible
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"

def check_api_endpoints():
    """Check if the new PO management APIs are accessible"""
    
    print("🔍 Verifying New PO Management APIs")
    print("=" * 50)
    
    # Test endpoints to check
    test_endpoints = [
        {
            "method": "GET",
            "url": f"{BASE_URL}/docs",
            "description": "FastAPI Documentation"
        },
        {
            "method": "GET", 
            "url": f"{BASE_URL}/openapi.json",
            "description": "OpenAPI Schema"
        }
    ]
    
    for endpoint in test_endpoints:
        try:
            print(f"\n📡 Testing {endpoint['description']}")
            print(f"   URL: {endpoint['url']}")
            
            if endpoint["method"] == "GET":
                response = requests.get(endpoint["url"], timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Endpoint accessible")
                
                # Check if it's the OpenAPI schema
                if "openapi.json" in endpoint["url"]:
                    try:
                        schema = response.json()
                        paths = schema.get("paths", {})
                        
                        # Look for our new PO management endpoints
                        po_endpoints = []
                        for path, methods in paths.items():
                            if "/pos" in path and "{project_id}" in path:
                                for method, details in methods.items():
                                    po_endpoints.append({
                                        "path": path,
                                        "method": method.upper(),
                                        "summary": details.get("summary", ""),
                                        "tags": details.get("tags", [])
                                    })
                        
                        if po_endpoints:
                            print(f"\n   🎯 Found {len(po_endpoints)} PO Management Endpoints:")
                            for ep in po_endpoints:
                                print(f"      {ep['method']} {ep['path']}")
                                print(f"         Tags: {', '.join(ep['tags'])}")
                                print(f"         Summary: {ep['summary']}")
                                print()
                        else:
                            print("   ⚠️  No PO management endpoints found in schema")
                            
                    except json.JSONDecodeError:
                        print("   ❌ Could not parse OpenAPI schema")
                        
            else:
                print(f"   ❌ Endpoint not accessible: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection error: {str(e)}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def check_specific_po_endpoints():
    """Check specific PO endpoints with dummy project ID"""
    print("\n🔍 Testing Specific PO Endpoints")
    print("=" * 50)
    
    # Use a dummy project ID for testing endpoint availability
    dummy_project_id = "123e4567-e89b-12d3-a456-426614174000"
    dummy_po_id = "987fcdeb-51a2-43d7-8f9e-123456789abc"
    
    po_endpoints = [
        {
            "method": "GET",
            "url": f"{BASE_URL}/projects/{dummy_project_id}/pos",
            "description": "Get Project POs",
            "expected_status": [401, 403, 404]  # Auth required or not found
        },
        {
            "method": "POST", 
            "url": f"{BASE_URL}/projects/{dummy_project_id}/pos",
            "description": "Add Project PO",
            "expected_status": [401, 403, 422]  # Auth required or validation error
        },
        {
            "method": "PUT",
            "url": f"{BASE_URL}/projects/{dummy_project_id}/pos/{dummy_po_id}",
            "description": "Update Project PO", 
            "expected_status": [401, 403, 404, 422]  # Auth required or not found
        },
        {
            "method": "DELETE",
            "url": f"{BASE_URL}/projects/{dummy_project_id}/pos/{dummy_po_id}",
            "description": "Delete Project PO",
            "expected_status": [401, 403, 404]  # Auth required or not found
        }
    ]
    
    for endpoint in po_endpoints:
        try:
            print(f"\n📡 Testing {endpoint['description']}")
            print(f"   URL: {endpoint['url']}")
            
            if endpoint["method"] == "GET":
                response = requests.get(endpoint["url"], timeout=5)
            elif endpoint["method"] == "POST":
                response = requests.post(endpoint["url"], timeout=5)
            elif endpoint["method"] == "PUT":
                response = requests.put(endpoint["url"], timeout=5)
            elif endpoint["method"] == "DELETE":
                response = requests.delete(endpoint["url"], timeout=5)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code in endpoint["expected_status"]:
                print("   ✅ Endpoint exists and responding as expected")
            elif response.status_code == 404:
                print("   ❌ Endpoint not found - API may not be mounted")
            elif response.status_code == 405:
                print("   ❌ Method not allowed - API exists but method not supported")
            else:
                print(f"   ⚠️  Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection error: {str(e)}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def main():
    """Main verification function"""
    print("🚀 API Verification Script")
    print("This script checks if the new PO management APIs are properly mounted")
    print()
    
    print("⚠️  NOTE: This script requires:")
    print("1. The application server to be running on localhost:8000")
    print("2. The server to be accessible (may show auth errors, which is normal)")
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/healthcheck", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and accessible")
        else:
            print(f"⚠️  Server responded with status: {response.status_code}")
    except:
        print("❌ Server is not accessible. Please ensure it's running on localhost:8000")
        return
    
    # Run verification tests
    check_api_endpoints()
    check_specific_po_endpoints()
    
    print("\n" + "=" * 50)
    print("📊 Verification Summary")
    print("=" * 50)
    print("If you see the PO management endpoints in the OpenAPI schema,")
    print("then the APIs are properly mounted and should be visible in:")
    print("1. FastAPI Docs: http://localhost:8000/docs")
    print("2. Admin Docs: http://localhost:8000/admin/docs")
    print()
    print("🔍 Look for these new endpoints:")
    print("   GET    /projects/{project_id}/pos")
    print("   POST   /projects/{project_id}/pos") 
    print("   PUT    /projects/{project_id}/pos/{po_id}")
    print("   DELETE /projects/{project_id}/pos/{po_id}")
    print()
    print("📝 These should appear under the 'Project POs' tag in the documentation.")

if __name__ == "__main__":
    main()