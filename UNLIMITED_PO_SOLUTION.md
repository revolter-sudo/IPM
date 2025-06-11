# Unlimited PO Documents Solution

## Current Limitation
The current implementation is limited to 5 PO documents because FastAPI requires explicit parameter definitions for file uploads in multipart forms.

## Solutions

### Solution 1: Extend to 20 PO Documents (Recommended)
Update the function signature to support 20 PO documents, which should cover most real-world scenarios.

### Solution 2: Dynamic File Upload (Advanced)
Use a more flexible approach that can handle unlimited files by using a different upload strategy.

### Solution 3: Multiple API Calls (Alternative)
Allow adding POs after project creation through separate API calls.

## Implementation

### Option 1: Extended Fixed Parameters (Immediate Solution)

```python
def create_project(
    request: str = Form(...),
    po_document_0: Optional[UploadFile] = File(None),
    po_document_1: Optional[UploadFile] = File(None),
    # ... up to po_document_19
    po_document_19: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
```

### Option 2: Dynamic Upload with File List

```python
from fastapi import UploadFile
from typing import List

def create_project(
    request: str = Form(...),
    po_documents: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
```

### Option 3: Separate PO Addition API

```python
@project_router.post("/{project_id}/pos")
def add_project_po(
    project_id: UUID,
    po_data: str = Form(...),
    po_document: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
```

## Recommended Approach

I recommend **Option 1** (extending to 20 parameters) because:
1. It maintains backward compatibility
2. It's simple and reliable
3. 20 POs should cover 99% of real-world use cases
4. It keeps the explicit binding approach

If you need more than 20 POs, we can implement **Option 3** as an additional API.