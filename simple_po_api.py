
# Simple PO Management API for unlimited PO support

@project_router.post(
    "/{project_id}/pos",
    status_code=status.HTTP_201_CREATED,
    tags=["Project POs"],
    description="Add a new PO to an existing project"
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

        # Create new PO
        new_po = ProjectPO(
            project_id=project_id,
            po_number=po_request_data.get("po_number"),
            amount=po_request_data["amount"],
            description=po_request_data.get("description"),
            file_path=None,  # Simplified - no file upload for now
            created_by=current_user.uuid
        )
        
        db.add(new_po)
        db.commit()
        db.refresh(new_po)

        return ProjectServiceResponse(
            data={
                "uuid": str(new_po.uuid),
                "project_id": str(new_po.project_id),
                "po_number": new_po.po_number,
                "amount": new_po.amount,
                "description": new_po.description,
                "created_at": new_po.created_at.isoformat() if new_po.created_at else None
            },
            message="PO added to project successfully",
            status_code=201
        ).model_dump()

    except json.JSONDecodeError as json_error:
        return ProjectServiceResponse(
            data=None,
            status_code=400,
            message=f"Invalid JSON in PO data: {str(json_error)}"
        ).model_dump()
    except Exception as e:
        db.rollback()
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
    """Get all POs for a specific project."""
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
        
        for po in pos:
            po_data = {
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "amount": po.amount,
                "description": po.description,
                "created_at": po.created_at.isoformat() if po.created_at else None,
                "created_by": str(po.created_by)
            }
            pos_data.append(po_data)
            total_amount += po.amount

        return ProjectServiceResponse(
            data={
                "project_id": str(project_id),
                "project_name": project.name,
                "po_summary": {
                    "total_pos": len(pos),
                    "total_amount": total_amount
                },
                "pos": pos_data
            },
            message="Project POs fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching project POs: {str(e)}"
        ).model_dump()