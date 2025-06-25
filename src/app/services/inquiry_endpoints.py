import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.app.database.database import get_db
from src.app.schemas.inquiry_schemas import (
    InquiryCreateRequest,
    InquiryServiceResponse,
    ProjectType
)
from src.app.services.inquiry_service import (
    create_inquiry_service,
    get_inquiries_service,
    get_inquiry_by_uuid_service
)

# Create router for inquiry endpoints
inquiry_router = APIRouter(prefix="/inquiries", tags=["Inquiries"])


@inquiry_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="Create New Inquiry",
    description="Create a new inquiry. Validates that the same phone number doesn't have multiple inquiries for the same project type."
)
def create_inquiry(
    inquiry_data: InquiryCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new inquiry with the following validations:
    - Phone number must be 10-15 digits
    - Name, state, and city cannot be empty
    - Same phone number can only have one inquiry per project type
    
    Returns a success message: "Thank you for your interest, our team will reach out to you soon."
    """
    try:
        result = create_inquiry_service(db=db, inquiry_data=inquiry_data)
        
        if result.status_code == 409:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.message
            )
        elif result.status_code == 500:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )
        
        return result.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in create_inquiry endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the inquiry"
        )


@inquiry_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Get Inquiries",
    description="Get list of inquiries with optional filtering and pagination"
)
def get_inquiries(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number"),
    project_type: Optional[ProjectType] = Query(None, description="Filter by project type"),
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city")
):
    """
    Get inquiries with optional filtering:
    - Filter by phone number (partial match)
    - Filter by project type
    - Filter by state (partial match)
    - Filter by city (partial match)
    - Pagination support
    """
    try:
        project_type_value = project_type.value if project_type else None
        
        result = get_inquiries_service(
            db=db,
            page=page,
            page_size=page_size,
            phone_number=phone_number,
            project_type=project_type_value,
            state=state,
            city=city
        )
        
        if result.status_code == 500:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )
        
        return result.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in get_inquiries endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching inquiries"
        )


@inquiry_router.get(
    "/{inquiry_uuid}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Get Inquiry by UUID",
    description="Get a specific inquiry by its UUID"
)
def get_inquiry_by_uuid(
    inquiry_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific inquiry by UUID.
    Returns 404 if inquiry is not found or has been deleted.
    """
    try:
        result = get_inquiry_by_uuid_service(db=db, inquiry_uuid=str(inquiry_uuid))
        
        if result.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.message
            )
        elif result.status_code == 500:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message
            )
        
        return result.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in get_inquiry_by_uuid endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching the inquiry"
        )


@inquiry_router.get(
    "/project-types/list",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Get Available Project Types",
    description="Get list of all available project types"
)
def get_project_types():
    """
    Get all available project types for the inquiry form.
    """
    try:
        project_types = [{"value": pt.value, "label": pt.value} for pt in ProjectType]
        
        return InquiryServiceResponse(
            data=project_types,
            message="Project types fetched successfully",
            status_code=200
        ).model_dump()
        
    except Exception as e:
        logging.error(f"Unexpected error in get_project_types endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching project types"
        )
