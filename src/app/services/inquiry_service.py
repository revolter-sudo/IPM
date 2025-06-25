import logging
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.app.database.models import InquiryData
from src.app.schemas.inquiry_schemas import (
    InquiryCreateRequest,
    InquiryServiceResponse,
    InquiryResponse
)


def create_inquiry_service(db: Session, inquiry_data: InquiryCreateRequest) -> InquiryServiceResponse:
    """
    Create a new inquiry with validation to prevent duplicate phone+project_type combinations.
    
    Args:
        db: Database session
        inquiry_data: Inquiry creation request data
        
    Returns:
        InquiryServiceResponse with success/error message
    """
    try:
        # Check if an inquiry with the same phone number and project type already exists
        existing_inquiry = db.query(InquiryData).filter(
            and_(
                InquiryData.phone_number == inquiry_data.phone_number,
                InquiryData.project_type == inquiry_data.project_type.value,
                InquiryData.is_deleted.is_(False)
            )
        ).first()
        
        if existing_inquiry:
            return InquiryServiceResponse(
                data=None,
                message=f"An inquiry for project type '{inquiry_data.project_type.value}' with this phone number already exists.",
                status_code=409  # Conflict
            )
        
        # Create new inquiry
        new_inquiry = InquiryData(
            uuid=uuid4(),
            name=inquiry_data.name,
            phone_number=inquiry_data.phone_number,
            project_type=inquiry_data.project_type.value,
            state=inquiry_data.state,
            city=inquiry_data.city,
            is_deleted=False
        )
        
        db.add(new_inquiry)
        db.commit()
        db.refresh(new_inquiry)
        
        # Convert to response format
        inquiry_response = InquiryResponse(
            uuid=new_inquiry.uuid,
            name=new_inquiry.name,
            phone_number=new_inquiry.phone_number,
            project_type=new_inquiry.project_type,
            state=new_inquiry.state,
            city=new_inquiry.city,
            created_at=new_inquiry.created_at,
            is_deleted=new_inquiry.is_deleted
        )
        
        return InquiryServiceResponse(
            data=inquiry_response.model_dump(),
            message="Thank you for your interest, our team will reach out to you soon.",
            status_code=201
        )
        
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating inquiry: {str(e)}")
        return InquiryServiceResponse(
            data=None,
            message=f"Error creating inquiry: {str(e)}",
            status_code=500
        )


def get_inquiries_service(
    db: Session, 
    page: int = 1, 
    page_size: int = 10,
    phone_number: str = None,
    project_type: str = None,
    state: str = None,
    city: str = None
) -> InquiryServiceResponse:
    """
    Get inquiries with optional filtering and pagination.
    
    Args:
        db: Database session
        page: Page number (1-based)
        page_size: Number of items per page
        phone_number: Filter by phone number
        project_type: Filter by project type
        state: Filter by state
        city: Filter by city
        
    Returns:
        InquiryServiceResponse with inquiry list
    """
    try:
        # Build query with filters
        query = db.query(InquiryData).filter(InquiryData.is_deleted.is_(False))
        
        if phone_number:
            query = query.filter(InquiryData.phone_number.ilike(f"%{phone_number}%"))
        if project_type:
            query = query.filter(InquiryData.project_type.ilike(f"%{project_type}%"))
        if state:
            query = query.filter(InquiryData.state.ilike(f"%{state}%"))
        if city:
            query = query.filter(InquiryData.city.ilike(f"%{city}%"))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        inquiries = query.order_by(InquiryData.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Convert to response format
        inquiry_responses = []
        for inquiry in inquiries:
            inquiry_responses.append(InquiryResponse(
                uuid=inquiry.uuid,
                name=inquiry.name,
                phone_number=inquiry.phone_number,
                project_type=inquiry.project_type,
                state=inquiry.state,
                city=inquiry.city,
                created_at=inquiry.created_at,
                is_deleted=inquiry.is_deleted
            ))
        
        response_data = {
            "inquiries": [inquiry.model_dump() for inquiry in inquiry_responses],
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
        
        return InquiryServiceResponse(
            data=response_data,
            message="Inquiries fetched successfully",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error fetching inquiries: {str(e)}")
        return InquiryServiceResponse(
            data=None,
            message=f"Error fetching inquiries: {str(e)}",
            status_code=500
        )


def get_inquiry_by_uuid_service(db: Session, inquiry_uuid: str) -> InquiryServiceResponse:
    """
    Get a specific inquiry by UUID.
    
    Args:
        db: Database session
        inquiry_uuid: UUID of the inquiry
        
    Returns:
        InquiryServiceResponse with inquiry data
    """
    try:
        inquiry = db.query(InquiryData).filter(
            and_(
                InquiryData.uuid == inquiry_uuid,
                InquiryData.is_deleted.is_(False)
            )
        ).first()
        
        if not inquiry:
            return InquiryServiceResponse(
                data=None,
                message="Inquiry not found",
                status_code=404
            )
        
        inquiry_response = InquiryResponse(
            uuid=inquiry.uuid,
            name=inquiry.name,
            phone_number=inquiry.phone_number,
            project_type=inquiry.project_type,
            state=inquiry.state,
            city=inquiry.city,
            created_at=inquiry.created_at,
            is_deleted=inquiry.is_deleted
        )
        
        return InquiryServiceResponse(
            data=inquiry_response.model_dump(),
            message="Inquiry fetched successfully",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error fetching inquiry: {str(e)}")
        return InquiryServiceResponse(
            data=None,
            message=f"Error fetching inquiry: {str(e)}",
            status_code=500
        )
