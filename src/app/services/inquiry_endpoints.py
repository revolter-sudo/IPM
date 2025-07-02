from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from src.app.database.database import get_db
from src.app.schemas.inquiry_schemas import InquiryCreateRequest, ProjectType
from src.app.services.inquiry_service import (
    create_inquiry_service,
    get_inquiries_service,
    get_inquiry_by_uuid_service,
)
from src.app.utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create router for inquiry endpoints
inquiry_router = APIRouter(prefix="/inquiries", tags=["Inquiries"])


@inquiry_router.post(
    "",
    response_model=dict,
    summary="Create New Inquiry",
    description="Create a new inquiry. Validates that the same phone number doesn't have multiple inquiries for the same project type.",
)
def create_inquiry(
    inquiry_data: InquiryCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Create a new inquiry with the following validations:
    - Phone number must be 10-15 digits
    - Name, state, and city cannot be empty
    - Same phone number can only have one inquiry per project type

    Returns a success message: "Thank you for your interest, our team will reach out to you soon."
    """
    try:
        logger.info(f"Creating inquiry for customer: {inquiry_data.name}")
        result = create_inquiry_service(db=db, inquiry_data=inquiry_data)

        if result.status_code == 409:
            logger.warning(f"Duplicate inquiry attempt: {result.message}")
            response.status_code = status.HTTP_409_CONFLICT
        elif result.status_code == 500:
            logger.error(f"Service error: {result.message}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            logger.info("Inquiry created successfully")
            response.status_code = status.HTTP_201_CREATED

        # Return the service response directly (it already has the correct format)
        return result.model_dump() if hasattr(result, "model_dump") else result

    except HTTPException as he:
        logger.error(f"HTTP error in create_inquiry endpoint: {str(he)}")
        response.status_code = he.status_code
        return {"data": None, "message": str(he.detail), "status_code": he.status_code}

    except Exception as e:
        logger.error(f"Unexpected error in create_inquiry endpoint: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "data": None,
            "message": "An unexpected error occurred while creating the inquiry",
            "status_code": 500,
        }


@inquiry_router.get(
    "",
    response_model=dict,
    summary="Get Inquiries",
    description="Get list of inquiries with optional filtering and pagination",
)
def get_inquiries(
    response: Response,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number"),
    project_type: Optional[ProjectType] = Query(
        None, description="Filter by project type"
    ),
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city"),
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
        logger.info(f"Fetching inquiries - Page: {page}, Size: {page_size}")
        project_type_value = project_type.value if project_type else None

        result = get_inquiries_service(
            db=db,
            page=page,
            page_size=page_size,
            phone_number=phone_number,
            project_type=project_type_value,
            state=state,
            city=city,
        )

        if result.status_code == 500:
            logger.error(f"Service error: {result.message}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            logger.info("Successfully fetched inquiries")
            response.status_code = status.HTTP_200_OK

        # Return the service response directly
        return result.model_dump() if hasattr(result, "model_dump") else result

    except HTTPException as he:
        logger.error(f"HTTP error in get_inquiries endpoint: {str(he)}")
        response.status_code = he.status_code
        return {"data": None, "message": str(he.detail), "status_code": he.status_code}
    except Exception as e:
        logger.error(f"Unexpected error in get_inquiries endpoint: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "data": None,
            "message": "An unexpected error occurred while fetching inquiries",
            "status_code": 500,
        }


@inquiry_router.get(
    "/{inquiry_uuid}",
    response_model=dict,
    summary="Get Inquiry by UUID",
    description="Get a specific inquiry by its UUID",
)
def get_inquiry_by_uuid(
    inquiry_uuid: UUID, response: Response, db: Session = Depends(get_db)
):
    """
    Get a specific inquiry by UUID.
    Returns 404 if inquiry is not found or has been deleted.
    """
    try:
        logger.info(f"Fetching inquiry by UUID: {inquiry_uuid}")
        result = get_inquiry_by_uuid_service(db=db, inquiry_uuid=str(inquiry_uuid))

        if result.status_code == 404:
            logger.warning(f"Inquiry not found: {inquiry_uuid}")
            response.status_code = status.HTTP_404_NOT_FOUND
        elif result.status_code == 500:
            logger.error(f"Service error: {result.message}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            logger.info(f"Successfully fetched inquiry: {inquiry_uuid}")
            response.status_code = status.HTTP_200_OK

        # Return the service response directly
        return result.model_dump() if hasattr(result, "model_dump") else result

    except HTTPException as he:
        logger.error(f"HTTP error in get_inquiry_by_uuid endpoint: {str(he)}")
        response.status_code = he.status_code
        return {"data": None, "message": str(he.detail), "status_code": he.status_code}
    except Exception as e:
        logger.error(f"Unexpected error in get_inquiry_by_uuid endpoint: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "data": None,
            "message": "An unexpected error occurred while fetching the inquiry",
            "status_code": 500,
        }


@inquiry_router.get(
    "/project-types/list",
    response_model=dict,
    summary="Get Available Project Types",
    description="Get list of all available project types",
)
def get_project_types(response: Response):
    """
    Get all available project types for the inquiry form.
    """
    try:
        logger.info("Fetching available project types")
        project_types = [{"value": pt.value, "label": pt.value} for pt in ProjectType]

        logger.info(f"Successfully fetched {len(project_types)} project types")
        response.status_code = status.HTTP_200_OK
        return {
            "data": project_types,
            "message": "Project types fetched successfully",
            "status_code": 200,
        }

    except Exception as e:
        logger.error(f"Unexpected error in get_project_types endpoint: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "data": None,
            "message": "An unexpected error occurred while fetching project types",
            "status_code": 500,
        }
