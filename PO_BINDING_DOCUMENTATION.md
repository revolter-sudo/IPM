# Enhanced PO Document Binding System

## Overview
This document explains the enhanced system for binding PO documents with their corresponding amounts and descriptions during project creation. The system ensures that each PO document is properly linked to its metadata (amount, description, PO number).

## Key Features

### 1. Explicit File Index Binding
- Each PO in the request can specify a `file_index` (0-9) to bind to a specific uploaded file
- If `file_index` is not specified, it defaults to the array index
- Supports up to 10 PO documents per project

### 2. Enhanced Validation
- Validates PO amounts (must be > 0)
- Checks file type restrictions
- Ensures file size limits (max 10MB per file)
- Validates PO number uniqueness within a project
- Verifies file binding integrity

### 3. Comprehensive Error Handling
- Clear error messages for binding issues
- Detailed logging for troubleshooting
- Rollback on any failure to maintain data consistency

## API Usage

### Request Format

**Endpoint:** `POST /projects/create`

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `request`: JSON string with project and PO details
- `po_document_0` to `po_document_9`: PO document files

**JSON Structure:**
```json
{
    "name": "Construction Project Alpha",
    "description": "Main construction project",
    "location": "Downtown Site",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "po_balance": 2000.0,
    "estimated_balance": 2500.0,
    "actual_balance": 1500.0,
    "pos": [
        {
            "po_number": "PO001",
            "amount": 1000.0,
            "description": "Materials purchase order",
            "file_index": 0
        },
        {
            "po_number": "PO002",
            "amount": 1000.0,
            "description": "Labor purchase order",
            "file_index": 1
        },
        {
            "po_number": "PO003",
            "amount": 500.0,
            "description": "Equipment rental",
            "file_index": 3
        }
    ]
}
```

### File Binding Examples

#### Example 1: Sequential Binding (Default)
```json
{
    "pos": [
        {
            "po_number": "PO001",
            "amount": 1000.0,
            "description": "First PO"
            // file_index not specified, defaults to 0
        },
        {
            "po_number": "PO002",
            "amount": 2000.0,
            "description": "Second PO"
            // file_index not specified, defaults to 1
        }
    ]
}
```
Files: `po_document_0` → PO001, `po_document_1` → PO002

#### Example 2: Explicit Binding
```json
{
    "pos": [
        {
            "po_number": "PO001",
            "amount": 1000.0,
            "description": "First PO",
            "file_index": 2
        },
        {
            "po_number": "PO002",
            "amount": 2000.0,
            "description": "Second PO",
            "file_index": 0
        }
    ]
}
```
Files: `po_document_2` → PO001, `po_document_0` → PO002

#### Example 3: Mixed Binding (Some POs without documents)
```json
{
    "pos": [
        {
            "po_number": "PO001",
            "amount": 1000.0,
            "description": "PO with document",
            "file_index": 0
        },
        {
            "po_number": "PO002",
            "amount": 2000.0,
            "description": "PO without document"
            // No file_index, no document uploaded
        }
    ]
}
```
Files: `po_document_0` → PO001, PO002 has no document

## Response Format

### Enhanced Response Structure
```json
{
    "data": {
        "uuid": "project-uuid",
        "name": "Construction Project Alpha",
        "description": "Main construction project",
        "location": "Downtown Site",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "po_balance": 2000.0,
        "estimated_balance": 2500.0,
        "actual_balance": 1500.0,
        "po_summary": {
            "total_pos": 3,
            "total_po_amount": 3500.0,
            "files_uploaded": 2,
            "files_missing": 1
        },
        "pos": [
            {
                "uuid": "po-uuid-1",
                "po_number": "PO001",
                "amount": 1000.0,
                "description": "Materials purchase order",
                "file_path": "http://host/uploads/PO_project-uuid_PO001_file-uuid.pdf",
                "has_document": true,
                "file_binding": {
                    "file_index": 0,
                    "original_filename": "materials_po.pdf",
                    "file_size_bytes": 245760,
                    "successfully_bound": true
                },
                "created_at": "2025-01-27T12:00:00"
            },
            {
                "uuid": "po-uuid-2",
                "po_number": "PO002",
                "amount": 1000.0,
                "description": "Labor purchase order",
                "file_path": "http://host/uploads/PO_project-uuid_PO002_file-uuid.pdf",
                "has_document": true,
                "file_binding": {
                    "file_index": 1,
                    "original_filename": "labor_po.pdf",
                    "file_size_bytes": 189440,
                    "successfully_bound": true
                },
                "created_at": "2025-01-27T12:00:00"
            },
            {
                "uuid": "po-uuid-3",
                "po_number": "PO003",
                "amount": 500.0,
                "description": "Equipment rental",
                "file_path": null,
                "has_document": false,
                "file_binding": {
                    "file_index": null,
                    "original_filename": null,
                    "file_size_bytes": 0,
                    "successfully_bound": false
                },
                "created_at": "2025-01-27T12:00:00"
            }
        ]
    },
    "message": "Project Created Successfully with 3 PO(s) and 2 document(s)",
    "status_code": 201
}
```

## File Handling

### Supported File Types
- PDF documents (`.pdf`)
- Microsoft Word (`.doc`, `.docx`)
- Excel files (`.xlsx`, `.xls`)
- Images (`.jpg`, `.jpeg`, `.png`)
- Text files (`.txt`)

### File Size Limits
- Maximum file size: 10MB per file
- Empty files are rejected

### File Naming Convention
Files are saved with the following naming pattern:
```
PO_{project_uuid}_{safe_po_number}_{file_uuid}.{extension}
```

Example: `PO_123e4567-e89b-12d3-a456-426614174000_PO001_987fcdeb-51a2-43d7-8f9e-123456789abc.pdf`

## Validation Rules

### PO Data Validation
1. **Amount**: Must be greater than 0
2. **PO Number**: Must be unique within the project (if specified)
3. **File Index**: Must be between 0-9 (if specified)
4. **Description**: Optional but recommended

### File Validation
1. **File Type**: Must be in allowed extensions list
2. **File Size**: Must not exceed 10MB
3. **File Content**: Must not be empty
4. **File Index**: Must correspond to an available file upload field

## Error Handling

### Common Error Scenarios

#### 1. Invalid File Index
```json
{
    "data": null,
    "message": "PO 1: Invalid file_index 15. Must be between 0-9",
    "status_code": 400
}
```

#### 2. Invalid Amount
```json
{
    "data": null,
    "message": "PO 2: Amount must be greater than 0",
    "status_code": 400
}
```

#### 3. Duplicate PO Number
```json
{
    "data": null,
    "message": "PO number 'PO001' is duplicated. Each PO must have a unique number.",
    "status_code": 400
}
```

#### 4. Invalid File Type
```json
{
    "data": null,
    "message": "PO 1: File type .exe not allowed. Allowed types: .pdf, .doc, .docx, .jpg, .jpeg, .png, .txt, .xlsx, .xls",
    "status_code": 400
}
```

#### 5. File Too Large
```json
{
    "data": null,
    "message": "PO 1: File size exceeds 10MB limit",
    "status_code": 400
}
```

#### 6. Empty File
```json
{
    "data": null,
    "message": "PO 1: Uploaded file is empty",
    "status_code": 400
}
```

## Implementation Examples

### cURL Example
```bash
curl -X POST "http://localhost:8000/projects/create" \
  -F 'request={
    "name": "Test Project",
    "description": "Testing PO binding",
    "pos": [
      {
        "po_number": "PO001",
        "amount": 1000.0,
        "description": "First PO",
        "file_index": 0
      },
      {
        "po_number": "PO002",
        "amount": 2000.0,
        "description": "Second PO",
        "file_index": 1
      }
    ]
  }' \
  -F 'po_document_0=@first_po.pdf' \
  -F 'po_document_1=@second_po.pdf'
```

### JavaScript Example
```javascript
const formData = new FormData();

// Add project data
const projectData = {
    name: "Test Project",
    description: "Testing PO binding",
    pos: [
        {
            po_number: "PO001",
            amount: 1000.0,
            description: "First PO",
            file_index: 0
        },
        {
            po_number: "PO002",
            amount: 2000.0,
            description: "Second PO",
            file_index: 1
        }
    ]
};

formData.append('request', JSON.stringify(projectData));

// Add files
formData.append('po_document_0', firstPoFile);
formData.append('po_document_1', secondPoFile);

// Send request
fetch('/projects/create', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

### Python Example
```python
import requests
import json

# Prepare data
project_data = {
    "name": "Test Project",
    "description": "Testing PO binding",
    "pos": [
        {
            "po_number": "PO001",
            "amount": 1000.0,
            "description": "First PO",
            "file_index": 0
        },
        {
            "po_number": "PO002",
            "amount": 2000.0,
            "description": "Second PO",
            "file_index": 1
        }
    ]
}

# Prepare files
files = {
    'po_document_0': ('first_po.pdf', open('first_po.pdf', 'rb'), 'application/pdf'),
    'po_document_1': ('second_po.pdf', open('second_po.pdf', 'rb'), 'application/pdf')
}

# Prepare form data
data = {
    'request': json.dumps(project_data)
}

# Send request
response = requests.post(
    'http://localhost:8000/projects/create',
    data=data,
    files=files
)

print(response.json())
```

## Best Practices

### 1. File Organization
- Use descriptive PO numbers
- Include meaningful descriptions
- Upload documents in a logical order

### 2. Error Prevention
- Validate file types before upload
- Check file sizes client-side
- Ensure PO numbers are unique
- Verify amounts are positive

### 3. Performance Optimization
- Compress large PDF files before upload
- Use appropriate file formats
- Batch upload multiple files efficiently

### 4. Data Integrity
- Always include descriptions for POs
- Use consistent PO numbering schemes
- Verify file binding after upload

## Troubleshooting

### Common Issues

#### 1. Files Not Binding Correctly
- **Cause**: Incorrect file_index values
- **Solution**: Verify file_index matches uploaded file names

#### 2. Upload Failures
- **Cause**: File size or type restrictions
- **Solution**: Check file requirements and compress if needed

#### 3. Missing Documents
- **Cause**: Files not uploaded or binding failed
- **Solution**: Check response for binding status and retry if needed

#### 4. Validation Errors
- **Cause**: Invalid PO data
- **Solution**: Review validation rules and fix data issues

### Debugging Tips

1. **Check Response**: Always review the response for binding information
2. **Verify File Names**: Ensure file upload field names match expected pattern
3. **Test Incrementally**: Start with one PO and add more gradually
4. **Use Logging**: Enable detailed logging to track file processing
5. **Validate JSON**: Ensure request JSON is properly formatted

## Migration from Old System

### Backward Compatibility
The enhanced system maintains backward compatibility with the old approach:
- If `file_index` is not specified, it defaults to array index
- Old API calls will continue to work
- Existing projects are not affected

### Migration Steps
1. Update client code to use `file_index` for explicit binding
2. Test with small projects first
3. Gradually migrate larger projects
4. Update documentation and training materials

## Security Considerations

### File Security
- Files are validated for type and size
- Unique filenames prevent conflicts
- Files are stored outside web root
- Access is controlled through API endpoints

### Data Validation
- All inputs are validated and sanitized
- SQL injection protection through ORM
- File upload restrictions prevent malicious files
- Error messages don't expose sensitive information

## Performance Considerations

### Database Optimization
- Proper indexes on foreign keys
- Efficient queries for PO retrieval
- Batch operations for multiple POs

### File Storage
- Organized directory structure
- Efficient file naming for quick access
- Consider CDN for large deployments

### API Performance
- Streaming file uploads for large files
- Proper error handling to prevent timeouts
- Efficient JSON parsing and validation
