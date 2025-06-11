# Enhanced Project and Invoice API Documentation

## Overview
This document provides detailed API documentation for the enhanced project creation and invoice management system with multiple PO support, payment tracking, and analytics.

## Base URLs
- Main API: `http://localhost:8000`
- Admin API: `http://localhost:8000/admin`

## Authentication
All APIs require proper authentication. Include the authentication token in the request headers.

## 1. Project Management APIs

### 1.1 Create Project with Multiple POs
**Endpoint:** `POST /projects/create`

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `request` (required): JSON string containing project details
- `po_document_0` to `po_document_4` (optional): PO document files

**Request JSON Structure:**
```json
{
    "name": "Project Name",
    "description": "Project Description",
    "location": "Project Location", 
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "po_balance": 2000.0,
    "estimated_balance": 2500.0,
    "actual_balance": 1500.0,
    "pos": [
        {
            "po_number": "PO001",
            "amount": 1000.0,
            "description": "First PO description"
        },
        {
            "po_number": "PO002",
            "amount": 1000.0,
            "description": "Second PO description"
        }
    ]
}
```

**Response:**
```json
{
    "data": {
        "uuid": "project-uuid",
        "name": "Project Name",
        "description": "Project Description",
        "location": "Project Location",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "po_balance": 2000.0,
        "estimated_balance": 2500.0,
        "actual_balance": 1500.0,
        "pos": [
            {
                "uuid": "po-uuid-1",
                "po_number": "PO001",
                "amount": 1000.0,
                "description": "First PO description",
                "file_path": "http://host/uploads/PO_project-uuid_0_file-uuid.pdf"
            }
        ]
    },
    "message": "Project Created Successfully",
    "status_code": 201
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/projects/create" \
  -F 'request={"name":"Test Project","pos":[{"po_number":"PO001","amount":1000.0}]}' \
  -F 'po_document_0=@po_document.pdf'
```

### 1.2 List Projects
**Endpoint:** `GET /projects`

**Response:** List of projects with PO information included.

### 1.3 Get Project Details
**Endpoint:** `GET /projects/project?project_uuid={uuid}`

**Response:** Detailed project information including POs.

## 2. Invoice Management APIs

### 2.1 Upload Invoice
**Endpoint:** `POST /admin/invoices`

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `request` (required): JSON string containing invoice details
- `invoice_file` (optional): Invoice document file

**Request JSON Structure:**
```json
{
    "project_id": "project-uuid",
    "project_po_id": "po-uuid",  // Optional - links to specific PO
    "client_name": "ABC Company",
    "invoice_item": "Construction Materials",
    "amount": 750.0,
    "description": "Invoice description",
    "due_date": "2025-06-15"
}
```

**Response:**
```json
{
    "data": {
        "uuid": "invoice-uuid",
        "project_id": "project-uuid",
        "client_name": "ABC Company",
        "invoice_item": "Construction Materials",
        "amount": 750.0,
        "description": "Invoice description",
        "due_date": "2025-06-15",
        "file_path": "http://host/uploads/invoices/Invoice_uuid.pdf",
        "status": "uploaded",
        "created_at": "2025-01-27 12:00:00"
    },
    "message": "Invoice uploaded successfully",
    "status_code": 201
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/admin/invoices" \
  -F 'request={"project_id":"uuid","client_name":"ABC","invoice_item":"Materials","amount":500.0,"due_date":"2025-06-15"}' \
  -F 'invoice_file=@invoice.pdf'
```

### 2.2 List Invoices
**Endpoint:** `GET /admin/invoices`

**Query Parameters:**
- `project_id` (optional): Filter by project
- `status` (optional): Filter by status

**Response:** List of invoices with payment status.

### 2.3 Get Invoice Details
**Endpoint:** `GET /admin/invoices/{invoice_id}`

**Response:** Detailed invoice information including payment status.

### 2.4 Update Invoice Status
**Endpoint:** `PUT /admin/invoices/{invoice_id}/status`

**Request Body:**
```json
{
    "status": "received"
}
```

**Response:** Updated invoice status.

### 2.5 Update Invoice Details
**Endpoint:** `PUT /admin/invoices/{invoice_id}`

**Request Body:**
```json
{
    "client_name": "Updated Company Name",
    "invoice_item": "Updated Item",
    "amount": 600.0,
    "description": "Updated description",
    "due_date": "2025-07-15"
}
```

### 2.6 Delete Invoice
**Endpoint:** `DELETE /admin/invoices/{invoice_id}`

**Response:** Confirmation of soft deletion.

## 3. Invoice Payment APIs

### 3.1 Create Payment
**Endpoint:** `POST /admin/invoices/{invoice_id}/payments`

**Request Body:**
```json
{
    "amount": 250.0,
    "payment_date": "2025-06-15",
    "description": "Partial payment",
    "payment_method": "bank",
    "reference_number": "TXN123456"
}
```

**Response:**
```json
{
    "data": {
        "uuid": "payment-uuid",
        "invoice_id": "invoice-uuid",
        "amount": 250.0,
        "payment_date": "2025-06-15",
        "description": "Partial payment",
        "payment_method": "bank",
        "reference_number": "TXN123456",
        "created_at": "2025-01-27 12:00:00",
        "invoice_payment_status": "partially_paid",
        "invoice_total_paid": 250.0
    },
    "message": "Invoice payment created successfully",
    "status_code": 201
}
```

**Payment Status Logic:**
- `not_paid`: No payments recorded
- `partially_paid`: Total payments < invoice amount
- `fully_paid`: Total payments >= invoice amount

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/admin/invoices/{invoice_id}/payments" \
  -H "Content-Type: application/json" \
  -d '{"amount":250.0,"payment_date":"2025-06-15","payment_method":"bank","reference_number":"TXN123"}'
```

### 3.2 List Payments
**Endpoint:** `GET /admin/invoices/{invoice_id}/payments`

**Response:**
```json
{
    "data": {
        "invoice_id": "invoice-uuid",
        "invoice_amount": 750.0,
        "payment_status": "partially_paid",
        "total_paid_amount": 250.0,
        "remaining_amount": 500.0,
        "payments": [
            {
                "uuid": "payment-uuid",
                "invoice_id": "invoice-uuid",
                "amount": 250.0,
                "payment_date": "2025-06-15",
                "description": "Partial payment",
                "payment_method": "bank",
                "reference_number": "TXN123456",
                "created_at": "2025-01-27 12:00:00"
            }
        ]
    },
    "message": "Invoice payments fetched successfully",
    "status_code": 200
}
```

## 4. Invoice Analytics API

### 4.1 Get Project Invoice Analytics
**Endpoint:** `GET /admin/projects/{project_id}/invoice-analytics`

**Response:**
```json
{
    "data": {
        "project_id": "project-uuid",
        "project_name": "Project Name",
        "project_end_date": "2025-12-31",
        "invoices": [
            {
                "invoice_uuid": "invoice-uuid",
                "project_name": "Project Name",
                "po_number": "PO001",
                "po_amount": 1000.0,
                "invoice_amount": 750.0,
                "invoice_due_date": "2025-06-15",
                "payment_status": "partially_paid",
                "total_paid_amount": 250.0,
                "is_late": false
            }
        ]
    },
    "message": "Invoice analytics fetched successfully",
    "status_code": 200
}
```

**is_late Flag Logic:**
- `true`: Payment made after project end date OR not paid and project end date passed
- `false`: Payment made before project end date
- `null`: Not paid and project end date not yet passed

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/admin/projects/{project_id}/invoice-analytics"
```

## 5. Error Responses

### 5.1 Common Error Codes
- `400`: Bad Request - Invalid input data
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `500`: Internal Server Error - Server error

### 5.2 Error Response Format
```json
{
    "data": null,
    "message": "Error description",
    "status_code": 400
}
```

## 6. File Upload Guidelines

### 6.1 Supported File Types
- PDF documents
- Image files (JPG, PNG)
- Text files

### 6.2 File Size Limits
- Maximum file size: 10MB per file
- Maximum 5 PO documents per project

### 6.3 File Storage
- PO documents: `uploads/PO_projectuuid_index_fileuuid.ext`
- Invoice files: `uploads/invoices/Invoice_uuid.ext`

## 7. Database Schema

### 7.1 Key Tables
- `projects`: Project information
- `project_pos`: Multiple PO records per project
- `invoices`: Invoice information with PO links
- `invoice_payments`: Multiple payment records per invoice

### 7.2 Relationships
- Project → Multiple POs (1:N)
- PO → Multiple Invoices (1:N)
- Invoice → Multiple Payments (1:N)

## 8. Migration Commands

### 8.1 Apply Migrations
```bash
cd /path/to/project
alembic upgrade head
```

### 8.2 Check Migration Status
```bash
alembic current
alembic history
```

## 9. Testing

### 9.1 Run Test Suite
```bash
python test_implementation.py
```

### 9.2 Manual Testing Checklist
- [ ] Create project with multiple POs
- [ ] Upload PO documents
- [ ] Create invoices linked to POs
- [ ] Record multiple payments per invoice
- [ ] Verify payment status updates
- [ ] Check analytics data accuracy
- [ ] Test late payment detection

## 10. Performance Considerations

### 10.1 Database Indexes
All necessary indexes are created for optimal query performance:
- Project-PO relationships
- Invoice-Payment relationships
- Date-based queries for analytics

### 10.2 File Handling
- Files are stored with unique names to prevent conflicts
- File paths are stored in database for quick access
- Consider implementing file cleanup for deleted records

## 11. Security Notes

### 11.1 Access Control
- Role-based access for all endpoints
- Admin/Super Admin required for most operations
- Project Manager access for project-specific operations

### 11.2 Input Validation
- All UUIDs are validated
- File types and sizes are restricted
- Date formats are validated
- Amount values must be positive

### 11.3 File Security
- Uploaded files are stored outside web root
- File access is controlled through API endpoints
- File type validation prevents malicious uploads