# Integration Examples for Enhanced Logging

## How to Update Existing Services

### 1. Project Service Example

**Before (current code):**
```python
def create_project_service(data: dict, user_id: UUID, db: Session):
    try:
        new_project = Project(
            name=data["name"],
            description=data.get("description"),
            # ... other fields
        )
        db.add(new_project)
        db.commit()
        return ProjectServiceResponse(...)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in create_project API: {str(e)}")
        return ProjectServiceResponse(...)
```

**After (with enhanced logging):**
```python
from src.app.utils.logging_config import get_logger, get_database_logger
from src.app.middleware.database_logging import log_database_operation

logger = get_logger(__name__)
db_logger = get_database_logger()

def create_project_service(data: dict, user_id: UUID, db: Session):
    try:
        with log_database_operation("create_project", session=db):
            db_logger.info(f"Creating new project: {data['name']} for user: {user_id}")
            
            new_project = Project(
                name=data["name"],
                description=data.get("description"),
                # ... other fields
            )
            db.add(new_project)
            db.flush()  # Get the ID before commit
            
            db_logger.info(f"Project created with ID: {new_project.uuid}")
            
            # Log entry creation
            log_entry = Log(
                entity="Project",
                action="Create",
                entity_id=new_project.uuid,
                performed_by=user_id
            )
            db.add(log_entry)
            db.commit()
            
            db_logger.info(f"Project creation completed successfully: {new_project.uuid}")
            
        return ProjectServiceResponse(...)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in create_project API: {str(e)}")
        db_logger.error(f"Project creation failed for user {user_id}: {str(e)}")
        return ProjectServiceResponse(...)
```

### 2. Payment Service Example

**Enhanced payment processing with logging:**
```python
from src.app.utils.logging_config import get_database_logger, get_performance_logger
from src.app.middleware.database_logging import log_database_operation
import time

db_logger = get_database_logger()
perf_logger = get_performance_logger()

def process_payment_service(payment_data: dict, user_id: UUID, db: Session):
    start_time = time.time()
    
    try:
        with log_database_operation("process_payment", session=db):
            db_logger.info(f"Processing payment for user: {user_id}, amount: {payment_data.get('amount')}")
            
            # Create payment record
            payment = Payment(
                amount=payment_data["amount"],
                user_id=user_id,
                # ... other fields
            )
            db.add(payment)
            db.flush()
            
            # Process payment items
            for item_data in payment_data.get("items", []):
                db_logger.debug(f"Adding payment item: {item_data}")
                payment_item = PaymentItem(
                    payment_id=payment.uuid,
                    item_id=item_data["item_id"],
                    quantity=item_data["quantity"]
                )
                db.add(payment_item)
            
            db.commit()
            
            execution_time = time.time() - start_time
            perf_logger.info(f"Payment processing completed in {execution_time:.4f}s")
            
            if execution_time > 2.0:  # Log slow payments
                perf_logger.warning(f"Slow payment processing: {execution_time:.4f}s for payment {payment.uuid}")
            
            db_logger.info(f"Payment processed successfully: {payment.uuid}")
            
        return {"status": "success", "payment_id": str(payment.uuid)}
        
    except Exception as e:
        db.rollback()
        execution_time = time.time() - start_time
        db_logger.error(f"Payment processing failed after {execution_time:.4f}s: {str(e)}")
        raise
```

### 3. Khatabook Service Example

**Enhanced khatabook operations:**
```python
from src.app.utils.logging_config import get_database_logger
from src.app.middleware.database_logging import log_database_operation

db_logger = get_database_logger()

def create_khatabook_entry_service(data: dict, file_paths: list, user_id: UUID, db: Session):
    try:
        with log_database_operation("create_khatabook_entry", session=db):
            db_logger.info(f"Creating khatabook entry for user: {user_id}")
            db_logger.debug(f"Entry data: {data}")
            
            # Create main khatabook entry
            kb_entry = Khatabook(
                person_id=data["person_id"],
                project_id=data["project_id"],
                amount=data["amount"],
                created_by=user_id,
                # ... other fields
            )
            db.add(kb_entry)
            db.flush()
            
            db_logger.info(f"Khatabook entry created: {kb_entry.uuid}")
            
            # Attach items
            item_count = 0
            for item_uuid in data.get("item_ids", []):
                item_obj = db.query(Item).filter(Item.uuid == item_uuid).first()
                if item_obj:
                    kb_item = KhatabookItem(
                        khatabook_id=kb_entry.uuid,
                        item_id=item_obj.uuid
                    )
                    db.add(kb_item)
                    item_count += 1
            
            db_logger.info(f"Attached {item_count} items to khatabook entry")
            
            # Store file attachments
            file_count = 0
            for file_path in file_paths:
                new_file = KhatabookFile(khatabook_id=kb_entry.uuid, file_path=file_path)
                db.add(new_file)
                file_count += 1
            
            db_logger.info(f"Attached {file_count} files to khatabook entry")
            
            db.commit()
            db_logger.info(f"Khatabook entry creation completed: {kb_entry.uuid}")
            
        return kb_entry
        
    except Exception as e:
        db.rollback()
        db_logger.error(f"Khatabook entry creation failed: {str(e)}")
        raise
```

### 4. Database Query Performance Monitoring

**Add to frequently used queries:**
```python
from src.app.middleware.performance import QueryPerformanceTracker

def get_user_projects_service(user_id: UUID, db: Session):
    with QueryPerformanceTracker("get_user_projects"):
        projects = (
            db.query(Project)
            .join(ProjectUserMap)
            .filter(ProjectUserMap.user_id == user_id)
            .filter(Project.is_deleted.is_(False))
            .all()
        )
    return projects

def get_project_payments_service(project_id: UUID, db: Session):
    with QueryPerformanceTracker("get_project_payments"):
        payments = (
            db.query(Payment)
            .filter(Payment.project_id == project_id)
            .filter(Payment.is_deleted.is_(False))
            .order_by(Payment.created_at.desc())
            .all()
        )
    return payments
```

## Quick Integration Checklist

### For Each Service File:

1. **Add imports at the top:**
```python
from src.app.utils.logging_config import get_database_logger, get_performance_logger
from src.app.middleware.database_logging import log_database_operation
```

2. **Initialize loggers:**
```python
db_logger = get_database_logger()
perf_logger = get_performance_logger()
```

3. **Wrap database operations:**
```python
with log_database_operation("operation_name", session=db):
    # Your database operations here
```

4. **Add specific logging:**
```python
db_logger.info("Starting operation...")
db_logger.error("Operation failed...")
perf_logger.warning("Slow operation detected...")
```

### For Performance-Critical Operations:

1. **Add timing:**
```python
import time
start_time = time.time()
# ... operation ...
execution_time = time.time() - start_time
perf_logger.info(f"Operation completed in {execution_time:.4f}s")
```

2. **Use QueryPerformanceTracker:**
```python
from src.app.middleware.performance import QueryPerformanceTracker

with QueryPerformanceTracker("query_name"):
    result = db.query(...).all()
```

## Benefits of This Approach

1. **Separate log files** make it easier to monitor specific aspects
2. **Performance tracking** helps identify bottlenecks
3. **Database operation logging** provides audit trail
4. **Error isolation** makes debugging easier
5. **Production monitoring** becomes more effective

## Deployment Notes

- Test the logging locally first using `python test_logging.py`
- Deploy incrementally, updating one service at a time
- Monitor log file sizes and rotation
- Set up log monitoring alerts for errors and slow operations
