"""
Enhanced Project Service supporting up to 20 PO documents
This replaces the create_project function to support more PO documents
"""

@project_router.post(
    "/create", status_code=status.HTTP_201_CREATED, tags=["Projects"],
    description="""
    Create a new project with up to 20 PO documents upload.

    Request body should be sent as a form with 'request' field containing a JSON string with the following structure:
    ```json
    {
        "name": "Project Name",
        "description": "Project Description",
        "location": "Project Location",
        "start_date": "2025-06-04",
        "end_date": "2026-06-04",
        "po_balance": 1000.0,
        "estimated_balance": 1500.0,
        "actual_balance": 500.0,
        "pos": [
            {
                "po_number": "PO001",
                "amount": 500.0,
                "description": "First PO",
                "file_index": 0
            },
            {
                "po_number": "PO002",
                "amount": 500.0,
                "description": "Second PO",
                "file_index": 1
            }
        ]
    }
    ```

    Up to 20 PO documents can be uploaded as files with names 'po_document_0' to 'po_document_19'.
    Each PO can specify a file_index to bind to a specific document.
    """
)
def create_project_20_pos(
    request: str = Form(..., description="JSON string containing project details including multiple POs"),
    # PO Documents 0-9
    po_document_0: Optional[UploadFile] = File(None, description="PO document file 0"),
    po_document_1: Optional[UploadFile] = File(None, description="PO document file 1"),
    po_document_2: Optional[UploadFile] = File(None, description="PO document file 2"),
    po_document_3: Optional[UploadFile] = File(None, description="PO document file 3"),
    po_document_4: Optional[UploadFile] = File(None, description="PO document file 4"),
    po_document_5: Optional[UploadFile] = File(None, description="PO document file 5"),
    po_document_6: Optional[UploadFile] = File(None, description="PO document file 6"),
    po_document_7: Optional[UploadFile] = File(None, description="PO document file 7"),
    po_document_8: Optional[UploadFile] = File(None, description="PO document file 8"),
    po_document_9: Optional[UploadFile] = File(None, description="PO document file 9"),
    # PO Documents 10-19
    po_document_10: Optional[UploadFile] = File(None, description="PO document file 10"),
    po_document_11: Optional[UploadFile] = File(None, description="PO document file 11"),
    po_document_12: Optional[UploadFile] = File(None, description="PO document file 12"),
    po_document_13: Optional[UploadFile] = File(None, description="PO document file 13"),
    po_document_14: Optional[UploadFile] = File(None, description="PO document file 14"),
    po_document_15: Optional[UploadFile] = File(None, description="PO document file 15"),
    po_document_16: Optional[UploadFile] = File(None, description="PO document file 16"),
    po_document_17: Optional[UploadFile] = File(None, description="PO document file 17"),
    po_document_18: Optional[UploadFile] = File(None, description="PO document file 18"),
    po_document_19: Optional[UploadFile] = File(None, description="PO document file 19"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Enhanced project creation supporting up to 20 PO documents with proper binding.
    """
    try:
        # Parse the request data from form
        request_data = json.loads(request)
        project_request = ProjectCreateRequest(**request_data)

        logging.info(f"Create project request received: {project_request}")
        
        # Role validation
        user_role = current_user.role if hasattr(current_user, 'role') else current_user.get('role')
        logging.info(f"Current user role: {user_role}")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message=constants.CAN_NOT_CREATE_PROJECT
            ).model_dump()

        project_uuid = str(uuid4())

        # Create a mapping of uploaded files by index for proper binding
        po_documents = {
            0: po_document_0, 1: po_document_1, 2: po_document_2, 3: po_document_3, 4: po_document_4,
            5: po_document_5, 6: po_document_6, 7: po_document_7, 8: po_document_8, 9: po_document_9,
            10: po_document_10, 11: po_document_11, 12: po_document_12, 13: po_document_13, 14: po_document_14,
            15: po_document_15, 16: po_document_16, 17: po_document_17, 18: po_document_18, 19: po_document_19,
        }

        # Validate PO data and file bindings
        if project_request.pos:
            for idx, po_request in enumerate(project_request.pos):
                # Validate required fields
                if not po_request.amount or po_request.amount <= 0:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message=f"PO {idx + 1}: Amount must be greater than 0"
                    ).model_dump()
                
                # Check if file_index is specified and valid
                file_index = getattr(po_request, 'file_index', idx)  # Default to sequential index if not specified
                if file_index not in po_documents:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message=f"PO {idx + 1}: Invalid file_index {file_index}. Must be between 0-19"
                    ).model_dump()
                
                # Validate PO number uniqueness within the project
                po_numbers = [po.po_number for po in project_request.pos if po.po_number]
                if po_request.po_number and po_numbers.count(po_request.po_number) > 1:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message=f"PO number '{po_request.po_number}' is duplicated. Each PO must have a unique number."
                    ).model_dump()

        # Create new project
        new_project = Project(
            uuid=project_uuid,
            name=project_request.name,
            description=project_request.description,
            start_date=project_request.start_date,
            end_date=project_request.end_date,
            location=project_request.location,
            po_balance=project_request.po_balance,
            estimated_balance=project_request.estimated_balance,
            actual_balance=project_request.actual_balance,
            po_document_path=None  # Keep for backward compatibility
        )
        db.add(new_project)
        db.flush()  # Get the project ID without committing

        # Handle multiple POs with proper file binding
        created_pos = []
        po_binding_summary = []
        
        if project_request.pos:
            for idx, po_request in enumerate(project_request.pos):
                # Get the file index for this PO (default to sequential if not specified)
                file_index = getattr(po_request, 'file_index', idx)
                
                # Handle PO document upload if provided
                po_file_path = None
                po_file = po_documents.get(file_index)
                
                binding_info = {
                    "po_index": idx,
                    "po_number": po_request.po_number,
                    "file_index": file_index,
                    "file_uploaded": False,
                    "file_name": None,
                    "file_size": 0
                }
                
                if po_file and po_file.filename:
                    try:
                        upload_dir = constants.UPLOAD_DIR
                        os.makedirs(upload_dir, exist_ok=True)

                        # Validate file type
                        allowed_extensions = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt', '.xlsx', '.xls'}
                        file_ext = os.path.splitext(po_file.filename)[1].lower()
                        
                        if file_ext not in allowed_extensions:
                            return ProjectServiceResponse(
                                data=None,
                                status_code=400,
                                message=f"PO {idx + 1}: File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
                            ).model_dump()

                        # Create a unique filename with proper binding information
                        safe_po_number = (po_request.po_number or f'PO{idx+1}').replace('/', '_').replace('\\', '_')
                        unique_filename = f"PO_{project_uuid}_{safe_po_number}_{str(uuid4())}{file_ext}"
                        file_path = os.path.join(upload_dir, unique_filename)

                        # Read and validate file content
                        content = po_file.file.read()
                        if len(content) == 0:
                            logging.warning(f"Empty file uploaded for PO {idx + 1}")
                            return ProjectServiceResponse(
                                data=None,
                                status_code=400,
                                message=f"PO {idx + 1}: Uploaded file is empty"
                            ).model_dump()
                        
                        # Check file size (max 10MB)
                        max_size = 10 * 1024 * 1024  # 10MB
                        if len(content) > max_size:
                            return ProjectServiceResponse(
                                data=None,
                                status_code=400,
                                message=f"PO {idx + 1}: File size exceeds 10MB limit"
                            ).model_dump()

                        # Save the file
                        with open(file_path, "wb") as buffer:
                            buffer.write(content)
                        
                        po_file_path = file_path
                        binding_info.update({
                            "file_uploaded": True,
                            "file_name": po_file.filename,
                            "file_size": len(content)
                        })
                        
                        logging.info(f"PO {idx + 1} document saved: {po_file_path}")
                        
                    except Exception as file_error:
                        logging.error(f"Error saving PO {idx + 1} document: {str(file_error)}")
                        return ProjectServiceResponse(
                            data=None,
                            status_code=500,
                            message=f"Failed to save PO {idx + 1} document: {str(file_error)}"
                        ).model_dump()

                # Create ProjectPO entry with proper binding
                new_po = ProjectPO(
                    project_id=new_project.uuid,
                    po_number=po_request.po_number,
                    amount=po_request.amount,
                    description=po_request.description,
                    file_path=po_file_path,
                    created_by=current_user.uuid
                )
                db.add(new_po)
                created_pos.append(new_po)
                po_binding_summary.append(binding_info)
                
                logging.info(f"Created PO {idx + 1}: {po_request.po_number}, Amount: {po_request.amount}, File: {po_file_path is not None}")

        db.commit()
        db.refresh(new_project)

        # Initialize project balances
        if project_request.po_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.po_balance,
                description="Initial PO balance",
                current_user=current_user,
                balance_type="po"
            )

        if project_request.estimated_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.estimated_balance,
                description="Initial estimated balance",
                current_user=current_user,
                balance_type="estimated"
            )

        if project_request.actual_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.actual_balance,
                description="Initial actual balance",
                current_user=current_user,
                balance_type="actual"
            )

        # Create a log entry for project creation
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Project",
            action="Create",
            entity_id=project_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        # Prepare enhanced PO data for response with binding information
        pos_data = []
        for idx, po in enumerate(created_pos):
            binding_info = po_binding_summary[idx] if idx < len(po_binding_summary) else {}
            
            po_data = {
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "amount": po.amount,
                "description": po.description,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                "has_document": po.file_path is not None,
                "file_binding": {
                    "file_index": binding_info.get("file_index"),
                    "original_filename": binding_info.get("file_name"),
                    "file_size_bytes": binding_info.get("file_size", 0),
                    "successfully_bound": binding_info.get("file_uploaded", False)
                },
                "created_at": po.created_at.isoformat() if po.created_at else None
            }
            pos_data.append(po_data)

        # Calculate summary statistics
        total_po_amount = sum(po.amount for po in created_pos)
        files_uploaded = sum(1 for binding in po_binding_summary if binding.get("file_uploaded", False))

        return ProjectServiceResponse(
            data={
                "uuid": str(new_project.uuid),
                "name": new_project.name,
                "description": new_project.description,
                "location": new_project.location,
                "start_date": new_project.start_date,
                "end_date": new_project.end_date,
                "po_balance": new_project.po_balance,
                "estimated_balance": new_project.estimated_balance,
                "actual_balance": new_project.actual_balance,
                "po_summary": {
                    "total_pos": len(created_pos),
                    "total_po_amount": total_po_amount,
                    "files_uploaded": files_uploaded,
                    "files_missing": len(created_pos) - files_uploaded,
                    "max_pos_supported": 20
                },
                "pos": pos_data  # Enhanced PO data with binding information
            },
            message=f"Project Created Successfully with {len(created_pos)} PO(s) and {files_uploaded} document(s)",
            status_code=201
        ).model_dump()
        
    except json.JSONDecodeError as json_error:
        logging.error(f"JSON parsing error in create_project: {str(json_error)}")
        return ProjectServiceResponse(
            data=None,
            status_code=400,
            message=f"Invalid JSON in request data: {str(json_error)}"
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in create_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while creating project: {str(e)}"
        ).model_dump()