
# Additional PO Management APIs for unlimited PO support

@project_router.post(
    "/{project_id}/pos",
    status_code=status.HTTP_201_CREATED,
    tags=["Project POs"],
    description="""
    Add a new PO to an existing project.
    
    This API allows unlimited POs to be added to a project after creation.
    Each PO can have its own document, amount, and description.
    """
)
def add_project_po(
    project_id: UUID,
    po_data: str = Form(..., description="JSON string containing PO details"),
    po_document: Optional[UploadFile] = File(None, description="PO document file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new PO to an existing project with optional document upload."""
    try:
        # Parse PO data
        po_request_data = json.loads(po_data)
        
        # Validate required fields
        if not po_request_data.get("amount") or po_request_data["amount"] <= 0:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Amount must be greater than 0"
            ).model_dump()

        # Check if project exists
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Check permissions
        user_role = current_user.role if hasattr(current_user, "role") else current_user.get("role")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to add POs to project"
            ).model_dump()

        # Check for duplicate PO number within the project
        if po_request_data.get("po_number"):
            existing_po = db.query(ProjectPO).filter(
                ProjectPO.project_id == project_id,
                ProjectPO.po_number == po_request_data["po_number"],
                ProjectPO.is_deleted.is_(False)
            ).first()
            
            if existing_po:
                po_number = po_request_data["po_number"]
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"PO number '{po_number}' already exists in this project"
                ).model_dump()

        # Handle document upload if provided
        po_file_path = None
        file_info = {"uploaded": False, "filename": None, "size": 0}
        
        if po_document and po_document.filename:
            try:
                upload_dir = constants.UPLOAD_DIR
                os.makedirs(upload_dir, exist_ok=True)

                # Validate file type
                allowed_extensions = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".txt", ".xlsx", ".xls"}
                file_ext = os.path.splitext(po_document.filename)[1].lower()
                
                if file_ext not in allowed_extensions:
                    extensions_str = ", ".join(allowed_extensions)
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message=f"File type {file_ext} not allowed. Allowed types: {extensions_str}"
                    ).model_dump()

                # Create unique filename
                safe_po_number = (po_request_data.get("po_number", "PO") or "PO").replace("/", "_").replace("\\", "_")
                unique_filename = f"PO_{project_id}_{safe_po_number}_{str(uuid4())}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)

                # Read and validate file content
                content = po_document.file.read()
                if len(content) == 0:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message="Uploaded file is empty"
                    ).model_dump()
                
                # Check file size (max 10MB)
                max_size = 10 * 1024 * 1024  # 10MB
                if len(content) > max_size:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message="File size exceeds 10MB limit"
                    ).model_dump()

                # Save the file
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                
                po_file_path = file_path
                file_info.update({
                    "uploaded": True,
                    "filename": po_document.filename,
                    "size": len(content)
                })
                
                logging.info(f"PO document saved: {po_file_path}")
                
            except Exception as file_error:
                logging.error(f"Error saving PO document: {str(file_error)}")
                return ProjectServiceResponse(
                    data=None,
                    status_code=500,
                    message=f"Failed to save PO document: {str(file_error)}"
                ).model_dump()

        # Create new PO
        new_po = ProjectPO(
            project_id=project_id,
            po_number=po_request_data.get("po_number"),
            amount=po_request_data["amount"],
            description=po_request_data.get("description"),
            file_path=po_file_path,
            created_by=current_user.uuid
        )
        
        db.add(new_po)
        db.commit()
        db.refresh(new_po)

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="ProjectPO",
            action="Create",
            entity_id=new_po.uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data={
                "uuid": str(new_po.uuid),
                "project_id": str(new_po.project_id),
                "po_number": new_po.po_number,
                "amount": new_po.amount,
                "description": new_po.description,
                "file_path": constants.HOST_URL + "/" + new_po.file_path if new_po.file_path else None,
                "has_document": new_po.file_path is not None,
                "file_info": file_info,
                "created_at": new_po.created_at.isoformat() if new_po.created_at else None
            },
            message="PO added to project successfully",
            status_code=201
        ).model_dump()

    except json.JSONDecodeError as json_error:
        logging.error(f"JSON parsing error in add_project_po: {str(json_error)}")
        return ProjectServiceResponse(
            data=None,
            status_code=400,
            message=f"Invalid JSON in PO data: {str(json_error)}"
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in add_project_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while adding PO: {str(e)}"
        ).model_dump()


@project_router.get(
    "/{project_id}/pos",
    tags=["Project POs"],
    description="Get all POs for a specific project"
)
def get_project_pos(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all POs for a specific project with their details."""
    try:
        # Check if project exists
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Get all POs for this project
        pos = db.query(ProjectPO).filter(
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).order_by(ProjectPO.created_at).all()

        # Format PO data
        pos_data = []
        total_amount = 0.0
        files_count = 0
        
        for po in pos:
            po_data = {
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "amount": po.amount,
                "description": po.description,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                "has_document": po.file_path is not None,
                "created_at": po.created_at.isoformat() if po.created_at else None,
                "created_by": str(po.created_by)
            }
            pos_data.append(po_data)
            total_amount += po.amount
            if po.file_path:
                files_count += 1

        return ProjectServiceResponse(
            data={
                "project_id": str(project_id),
                "project_name": project.name,
                "po_summary": {
                    "total_pos": len(pos),
                    "total_amount": total_amount,
                    "files_uploaded": files_count,
                    "files_missing": len(pos) - files_count
                },
                "pos": pos_data
            },
            message="Project POs fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in get_project_pos API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching project POs: {str(e)}"
        ).model_dump()


@project_router.put(
    "/{project_id}/pos/{po_id}",
    tags=["Project POs"],
    description="Update an existing PO"
)
def update_project_po(
    project_id: UUID,
    po_id: UUID,
    po_data: str = Form(..., description="JSON string containing updated PO details"),
    po_document: Optional[UploadFile] = File(None, description="New PO document file (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing PO with optional document replacement."""
    try:
        # Parse PO data
        po_request_data = json.loads(po_data)

        # Check permissions
        user_role = current_user.role if hasattr(current_user, "role") else current_user.get("role")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to update POs"
            ).model_dump()

        # Find the PO
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).first()
        
        if not po:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found"
            ).model_dump()

        # Update PO fields
        if "po_number" in po_request_data:
            po.po_number = po_request_data["po_number"]
        if "amount" in po_request_data:
            if po_request_data["amount"] <= 0:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message="Amount must be greater than 0"
                ).model_dump()
            po.amount = po_request_data["amount"]
        if "description" in po_request_data:
            po.description = po_request_data["description"]

        db.commit()
        db.refresh(po)

        return ProjectServiceResponse(
            data={
                "uuid": str(po.uuid),
                "project_id": str(po.project_id),
                "po_number": po.po_number,
                "amount": po.amount,
                "description": po.description,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                "has_document": po.file_path is not None,
                "updated_at": po.updated_at.isoformat() if po.updated_at else None
            },
            message="PO updated successfully",
            status_code=200
        ).model_dump()

    except json.JSONDecodeError as json_error:
        logging.error(f"JSON parsing error in update_project_po: {str(json_error)}")
        return ProjectServiceResponse(
            data=None,
            status_code=400,
            message=f"Invalid JSON in PO data: {str(json_error)}"
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in update_project_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while updating PO: {str(e)}"
        ).model_dump()


@project_router.delete(
    "/{project_id}/pos/{po_id}",
    tags=["Project POs"],
    description="Delete a PO from a project"
)
def delete_project_po(
    project_id: UUID,
    po_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a PO from a project."""
    try:
        # Check permissions
        user_role = current_user.role if hasattr(current_user, "role") else current_user.get("role")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to delete POs"
            ).model_dump()

        # Find the PO
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).first()
        
        if not po:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found"
            ).model_dump()

        # Check if PO has associated invoices
        invoices = db.query(Invoice).filter(
            Invoice.project_po_id == po_id,
            Invoice.is_deleted.is_(False)
        ).count()
        
        if invoices > 0:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message=f"Cannot delete PO. It has {invoices} associated invoice(s). Please delete or reassign the invoices first."
            ).model_dump()

        # Soft delete the PO
        po.is_deleted = True
        db.commit()

        return ProjectServiceResponse(
            data={"deleted_po_id": str(po_id)},
            message="PO deleted successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logging.error(f"Error in delete_project_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while deleting PO: {str(e)}"
        ).model_dump()