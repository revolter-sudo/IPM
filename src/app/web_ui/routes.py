from fastapi import APIRouter, Depends, Request, Form, HTTPException, Cookie, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import json
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from typing import Optional, List
from uuid import UUID
from jose import JWTError, jwt
from datetime import datetime

from src.app.database.database import get_db
from src.app.database.models import User, Project, ProjectUserMap, Item, ProjectItemMap
from src.app.services.auth_service import create_access_token, verify_password, SECRET_KEY, ALGORITHM
from src.app.schemas.auth_service_schamas import UserRole, UserCreate
from src.app.schemas.payment_service_schemas import CreatePerson

# Initialize templates
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Create router
web_ui_router = APIRouter(prefix="/web", tags=["Web UI"])

# Custom function to get current user from cookie
async def get_current_web_user(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get token from cookie
    token_cookie = request.cookies.get("access_token")

    if not token_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Extract token from "Bearer {token}"
    try:
        token = token_cookie.split("Bearer ")[1]
    except IndexError:
        token = token_cookie  # If it's not in the "Bearer {token}" format

    try:
        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = payload.get("sub")

        if not user_uuid:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get user from database
        user = db.query(User).filter(
            User.uuid == user_uuid,
            User.is_deleted.is_(False),
            User.is_active.is_(True)
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Login page
@web_ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@web_ui_router.post("/login")
async def login_post(
    request: Request,
    phone: int = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Use the existing login API
    try:
        # Create a device ID for web
        device_id = f"web-{phone}"

        # Call the login function directly
        from src.app.services.auth_service import login
        from src.app.schemas.auth_service_schamas import UserLogin

        # Create login data
        login_data = UserLogin(
            phone=phone,
            password=password,
            device_id=device_id
        )

        # Call the login function
        result = login(login_data=login_data, db=db)

        # Check if login was successful
        if result.get("status_code") != 201:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": result.get("message", "Login failed")}
            )

        # Get the data from the result
        data = result.get("data", {})

        # Check if user is admin or super admin
        user_data = data.get("user_data", {})
        if user_data.get("role") not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Only admin users can access this panel"}
            )

        # Get the access token
        access_token = data.get("access_token")

        # Create response with token in cookie
        response = RedirectResponse(url="/web/dashboard", status_code=303)
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

        # Also store user data in a cookie for easy access
        import json
        response.set_cookie(key="user_data", value=json.dumps(user_data), httponly=True)

        return response
    except Exception as e:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Login failed: {str(e)}"}
        )

# Dashboard
@web_ui_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Use the existing APIs to get projects and users
    import requests
    import json

    # Get the access token from cookie
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/web/login", status_code=303)

    # Extract the token from "Bearer {token}"
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]

    # Set up headers for API requests
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Get all projects using the existing API
    try:
        # Use the list_all_projects API
        from src.app.services.project_service import list_all_projects
        projects_response = list_all_projects(db=db, current_user=current_user)
        projects = projects_response.get("data", [])
    except Exception as e:
        projects = []

    # Get all users using the existing API
    try:
        # Use the list_all_active_users API
        from src.app.services.auth_service import list_all_active_users
        users_response = list_all_active_users(db=db)
        users = users_response.get("data", [])
    except Exception as e:
        users = []

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "projects": projects,
            "users": users
        }
    )

# Project details
@web_ui_router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_details(
    request: Request,
    project_id: UUID,
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get the access token from cookie
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/web/login", status_code=303)

    # Extract the token from "Bearer {token}"
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]

    # Get project details using the existing API
    try:
        # Use the get_project_info API
        from src.app.services.project_service import get_project_info
        project_response = get_project_info(project_uuid=project_id, db=db)
        project = project_response.get("data", {})

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Project not found: {str(e)}")

    # Get project users using the admin API
    try:
        # Use the get_project_users API
        from src.app.admin_panel.endpoints import get_project_users
        users_response = get_project_users(project_id=project_id, db=db, current_user=current_user)
        project_users = users_response.get("data", [])
    except Exception as e:
        project_users = []

    # Get project items using the admin API
    try:
        # Use the get_project_items API
        from src.app.admin_panel.endpoints import get_project_items
        items_response = get_project_items(project_id=project_id, db=db, current_user=current_user)
        project_items = items_response.get("data", [])
    except Exception as e:
        project_items = []

    # Get all users for assignment
    try:
        # Use the list_all_active_users API
        from src.app.services.auth_service import list_all_active_users
        users_response = list_all_active_users(db=db)
        all_users = users_response.get("data", [])
    except Exception as e:
        all_users = []

    # Get all items
    try:
        # Get all items from the database
        items_query = db.query(Item).all()

        # Log the number of items found
        logging.info(f"Found {len(items_query)} items in the database")

        # Convert SQLAlchemy objects to dictionaries
        all_items = []
        for item in items_query:
            logging.info(f"Item: {item.uuid} - {item.name}")
            all_items.append({
                "uuid": str(item.uuid),
                "name": item.name,
                "category": item.category
            })

        # Log the converted items
        logging.info(f"Converted {len(all_items)} items to dictionaries")
    except Exception as e:
        logging.error(f"Error getting items: {str(e)}")
        all_items = []

    return templates.TemplateResponse(
        "admin/project_details.html",
        {
            "request": request,
            "current_user": current_user,
            "project": project,
            "project_users": project_users,
            "project_items": project_items,
            "all_users": all_users,
            "all_items": all_items
        }
    )

# User details
@web_ui_router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_details(
    request: Request,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get the access token from cookie
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/web/login", status_code=303)

    # Extract the token from "Bearer {token}"
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]

    # Get user details using the existing API
    try:
        # Use the get_user_info API
        from src.app.services.auth_service import get_user_info
        user_response = get_user_info(user_uuid=user_id, db=db)
        user = user_response.get("data", {})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")

    # Get user projects using the admin API
    try:
        # Use the get_user_projects API
        from src.app.admin_panel.endpoints import get_user_projects
        projects_response = get_user_projects(user_id=user_id, db=db, current_user=current_user)
        user_projects = projects_response.get("data", [])
    except Exception as e:
        user_projects = []

    # Get user details with projects and items
    try:
        # Use the get_user_details API
        from src.app.admin_panel.endpoints import get_user_details
        details_response = get_user_details(user_id=user_id, db=db, current_user=current_user)
        user_details = details_response.get("data", {})

        # Merge user details with user info
        if user_details:
            user.update(user_details)
    except Exception as e:
        logging.error(f"Error fetching user details: {str(e)}")

    # Get user's assigned project items
    try:
        # Use the get_user_project_items API
        from src.app.admin_panel.endpoints import get_user_project_items
        items_response = get_user_project_items(user_id=user_id, db=db, current_user=current_user)
        user_project_items = items_response.get("data", {})

        # If we have project items data, update the user object
        if user_project_items and "projects" in user_project_items:
            user["projects"] = user_project_items["projects"]
    except Exception as e:
        logging.error(f"Error fetching user project items: {str(e)}")

    return templates.TemplateResponse(
        "admin/user_details.html",
        {
            "request": request,
            "current_user": current_user,
            "user": user,
            "user_projects": user_projects
        }
    )

# Khatabook entries
@web_ui_router.get("/khatabook", response_class=HTMLResponse)
async def khatabook_entries(
    request: Request,
    user_id: Optional[UUID] = None,
    item_id: Optional[UUID] = None,
    person_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    payment_mode: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get the access token from cookie
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/web/login", status_code=303)

    # Extract the token from "Bearer {token}"
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]

    # Convert string dates to datetime if provided
    from datetime import datetime
    start_datetime = None
    end_datetime = None

    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
        except ValueError:
            pass

    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
        except ValueError:
            pass

    # Get khatabook entries using the admin API
    try:
        # Use the get_all_khatabook_entries_admin API
        from src.app.admin_panel.endpoints import get_all_khatabook_entries_admin
        entries_response = get_all_khatabook_entries_admin(
            user_id=user_id,
            item_id=item_id,
            person_id=person_id,
            project_id=project_id,
            min_amount=min_amount,
            max_amount=max_amount,
            start_date=start_datetime,
            end_date=end_datetime,
            payment_mode=payment_mode,
            db=db,
            current_user=current_user
        )
        khatabook_data = entries_response.get("data", {})
        entries = khatabook_data.get("entries", [])
        total_amount = khatabook_data.get("total_amount", 0)
        entries_count = khatabook_data.get("entries_count", 0)
    except Exception as e:
        entries = []
        total_amount = 0
        entries_count = 0

    # Get all users for filtering
    try:
        from src.app.services.auth_service import list_all_active_users
        users_response = list_all_active_users(db=db)
        users = users_response.get("data", [])
    except Exception as e:
        users = []

    # Get all items for filtering
    try:
        items_query = db.query(Item).all()

        # Convert SQLAlchemy objects to dictionaries
        items = []
        for item in items_query:
            items.append({
                "uuid": str(item.uuid),
                "name": item.name,
                "category": item.category
            })
    except Exception as e:
        items = []

    # Get all projects for filtering
    try:
        from src.app.services.project_service import list_all_projects
        projects_response = list_all_projects(db=db, current_user=current_user)
        projects = projects_response.get("data", [])
    except Exception as e:
        projects = []

    return templates.TemplateResponse(
        "admin/khatabook.html",
        {
            "request": request,
            "current_user": current_user,
            "entries": entries,
            "total_amount": total_amount,
            "entries_count": entries_count,
            "users": users,
            "items": items,
            "projects": projects,
            "filters": {
                "user_id": user_id,
                "item_id": item_id,
                "person_id": person_id,
                "project_id": project_id,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "start_date": start_date,
                "end_date": end_date,
                "payment_mode": payment_mode
            }
        }
    )

# Create Project
@web_ui_router.post("/projects/create")
async def create_project(
    request: Request,
    project_name: str = Form(...),
    project_description: str = Form(None),
    po_balance: float = Form(...),
    estimated_balance: float = Form(...),
    actual_balance: float = Form(0.0),
    project_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get the access token from cookie
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/web/login", status_code=303)

    # Extract the token from "Bearer {token}"
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]

    try:
        # Prepare project data
        project_data = {
            "name": project_name,
            "description": project_description or "",
            "location": "",  # Default empty location
            "po_balance": po_balance,
            "estimated_balance": estimated_balance,
            "actual_balance": actual_balance
        }

        # Convert to JSON string for the API
        import json
        request_json = json.dumps(project_data)

        # Use the create_project API
        from src.app.services.project_service import create_project as api_create_project

        # Call the API function
        result = api_create_project(
            request=request_json,
            po_document=project_file,
            db=db,
            current_user=current_user
        )

        # Check if project was created successfully
        if result.get("status_code") != 201:
            return templates.TemplateResponse(
                "admin/dashboard.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "error": result.get("message", "Failed to create project")
                }
            )

        # Redirect to dashboard
        return RedirectResponse(url="/web/dashboard", status_code=303)
    except Exception as e:
        # Log the error
        import logging
        logging.error(f"Error creating project: {str(e)}")

        # Return to dashboard with error
        return templates.TemplateResponse(
            "admin/dashboard.html",
            {
                "request": request,
                "current_user": current_user,
                "error": f"Error creating project: {str(e)}"
            }
        )

# Project User Mapping
@web_ui_router.post("/project_mapping")
async def create_project_user_mapping(
    request: Request,
    project_id: UUID = Form(...),
    user_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        # Check if project exists
        project = db.query(Project).filter(
            Project.uuid == project_id
        ).first()

        if not project:
            return templates.TemplateResponse(
                "admin/project_details.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "project": {},
                    "project_users": [],
                    "project_items": [],
                    "all_users": [],
                    "all_items": [],
                    "error": "Project not found"
                }
            )

        # Check if user exists
        user = db.query(User).filter(
            User.uuid == user_id,
            User.is_deleted.is_(False),
            User.is_active.is_(True)
        ).first()

        if not user:
            # Get project details for the response
            from src.app.services.project_service import get_project_info
            project_response = get_project_info(project_uuid=project_id, db=db)
            project_data = project_response.get("data", {})

            # Get project users
            from src.app.admin_panel.endpoints import get_project_users
            users_response = get_project_users(project_id=project_id, db=db, current_user=current_user)
            project_users = users_response.get("data", [])

            # Get project items
            from src.app.admin_panel.endpoints import get_project_items
            items_response = get_project_items(project_id=project_id, db=db, current_user=current_user)
            project_items = items_response.get("data", [])

            # Get all users for assignment
            from src.app.services.auth_service import list_all_active_users
            users_response = list_all_active_users(db=db)
            all_users = users_response.get("data", [])

            # Get all items
            items_query = db.query(Item).all()

            # Convert SQLAlchemy objects to dictionaries
            all_items = []
            for item in items_query:
                all_items.append({
                    "uuid": str(item.uuid),
                    "name": item.name,
                    "category": item.category
                })

            return templates.TemplateResponse(
                "admin/project_details.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "project": project_data,
                    "project_users": project_users,
                    "project_items": project_items,
                    "all_users": all_users,
                    "all_items": all_items,
                    "error": "User not found"
                }
            )

        # Check if mapping already exists
        existing_mapping = db.query(ProjectUserMap).filter(
            ProjectUserMap.project_id == project_id,
            ProjectUserMap.user_id == user_id
        ).first()

        if existing_mapping:
            # Redirect back to project details page
            return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

        # Create new mapping
        new_mapping = ProjectUserMap(
            project_id=project_id,
            user_id=user_id
        )

        db.add(new_mapping)
        db.commit()

        # Redirect back to project details page
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

    except Exception as e:
        # Log the error
        logging.error(f"Error creating project user mapping: {str(e)}")

        # Redirect back to project details page with error
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

# Project User Mapping Remove
@web_ui_router.post("/project_mapping/remove")
async def remove_project_user_mapping(
    request: Request,
    project_id: UUID = Form(...),
    user_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        # Find the mapping
        mapping = db.query(ProjectUserMap).filter(
            ProjectUserMap.project_id == project_id,
            ProjectUserMap.user_id == user_id
        ).first()

        if mapping:
            # Delete the mapping
            db.delete(mapping)
            db.commit()

        # Redirect back to project details page
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

    except Exception as e:
        # Log the error
        logging.error(f"Error removing project user mapping: {str(e)}")

        # Redirect back to project details page with error
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

# Item Mapping
@web_ui_router.post("/item_mapping")
async def create_item_mapping(
    request: Request,
    project_id: UUID = Form(...),
    item_id: UUID = Form(...),
    item_balance: float = Form(...),
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        # Check if project exists
        project = db.query(Project).filter(
            Project.uuid == project_id
        ).first()

        if not project:
            return RedirectResponse(url="/web/dashboard", status_code=303)

        # Check if item exists
        item = db.query(Item).filter(
            Item.uuid == item_id
        ).first()

        if not item:
            return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

        # Check if mapping already exists
        existing_mapping = db.query(ProjectItemMap).filter(
            ProjectItemMap.project_id == project_id,
            ProjectItemMap.item_id == item_id
        ).first()

        if existing_mapping:
            # Update the existing mapping
            existing_mapping.item_balance = item_balance
            db.commit()
        else:
            # Create new mapping
            new_mapping = ProjectItemMap(
                project_id=project_id,
                item_id=item_id,
                item_balance=item_balance
            )

            db.add(new_mapping)
            db.commit()

        # Redirect back to project details page
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

    except Exception as e:
        # Log the error
        logging.error(f"Error creating item mapping: {str(e)}")

        # Redirect back to project details page with error
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

# Item Mapping Remove
@web_ui_router.post("/item_mapping/remove")
async def remove_item_mapping(
    request: Request,
    project_id: UUID = Form(...),
    item_id: UUID = Form(...),
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        # Find the mapping
        mapping = db.query(ProjectItemMap).filter(
            ProjectItemMap.project_id == project_id,
            ProjectItemMap.item_id == item_id
        ).first()

        if mapping:
            # Delete the mapping
            db.delete(mapping)
            db.commit()

        # Redirect back to project details page
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

    except Exception as e:
        # Log the error
        logging.error(f"Error removing item mapping: {str(e)}")

        # Redirect back to project details page with error
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

# User Item Mapping
@web_ui_router.post("/user_item_mapping")
async def create_user_item_mapping(
    request: Request,
    project_id: UUID = Form(...),
    user_id: UUID = Form(...),
    item_ids: List[UUID] = Form(...),
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        # Check if project exists
        project = db.query(Project).filter(
            Project.uuid == project_id
        ).first()

        if not project:
            return RedirectResponse(url="/web/dashboard", status_code=303)

        # Check if user exists
        user = db.query(User).filter(
            User.uuid == user_id
        ).first()

        if not user:
            return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

        # First, check if the user is assigned to the project
        user_project_mapping = db.query(ProjectUserMap).filter(
            ProjectUserMap.project_id == project_id,
            ProjectUserMap.user_id == user_id
        ).first()

        if not user_project_mapping:
            # User is not assigned to the project, create the mapping first
            new_mapping = ProjectUserMap(
                project_id=project_id,
                user_id=user_id
            )
            db.add(new_mapping)
            db.commit()

        # Create a table to store user-item mappings if it doesn't exist
        # This is a custom table not in the original schema
        from sqlalchemy import Table, Column, ForeignKey, String, Boolean, MetaData
        from sqlalchemy.dialects.postgresql import UUID as PGUUID

        metadata = MetaData()

        # Check if the table exists
        inspector = inspect(db.bind)
        if 'user_item_mappings' not in inspector.get_table_names():
            # Create the table
            user_item_mappings = Table(
                'user_item_mappings',
                metadata,
                Column('id', PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
                Column('user_id', PGUUID(as_uuid=True), ForeignKey('users.uuid')),
                Column('project_id', PGUUID(as_uuid=True), ForeignKey('projects.uuid')),
                Column('item_id', PGUUID(as_uuid=True), ForeignKey('items.uuid')),
                Column('is_deleted', Boolean, default=False)
            )
            metadata.create_all(db.bind)

        # Now assign the selected items to the user
        for item_id in item_ids:
            # Check if the item exists and is assigned to the project
            project_item_mapping = db.query(ProjectItemMap).filter(
                ProjectItemMap.project_id == project_id,
                ProjectItemMap.item_id == item_id
            ).first()

            if not project_item_mapping:
                continue  # Skip if item is not assigned to the project

            # Check if mapping already exists
            stmt = text("""
                SELECT * FROM user_item_mappings
                WHERE user_id = :user_id
                AND project_id = :project_id
                AND item_id = :item_id
                AND is_deleted = false
            """)

            existing_mapping = db.execute(
                stmt,
                {"user_id": str(user_id), "project_id": str(project_id), "item_id": str(item_id)}
            ).fetchone()

            if existing_mapping:
                continue  # Skip if mapping already exists

            # Create new mapping
            stmt = text("""
                INSERT INTO user_item_mappings (id, user_id, project_id, item_id, is_deleted)
                VALUES (:id, :user_id, :project_id, :item_id, false)
            """)

            db.execute(
                stmt,
                {
                    "id": str(uuid.uuid4()),
                    "user_id": str(user_id),
                    "project_id": str(project_id),
                    "item_id": str(item_id)
                }
            )

        db.commit()

        # Redirect back to project details page
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

    except Exception as e:
        # Log the error
        logging.error(f"Error creating user item mapping: {str(e)}")

        # Redirect back to project details page with error
        return RedirectResponse(url=f"/web/projects/{project_id}", status_code=303)

# Create User
@web_ui_router.post("/users/create")
async def create_user(
    request: Request,
    db: Session = Depends(get_db)
):
    # Get current user from cookie
    current_user = await get_current_web_user(request, db)

    # Check if user is admin or super admin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        return JSONResponse(
            status_code=403,
            content={"message": "Not authorized", "status_code": 403}
        )

    try:
        # Initialize variables
        name = None
        phone = None
        password = None
        role = None
        person_name = None
        phone_number = None
        account_number = None
        ifsc_code = None
        upi_number = None

        # Check if the request is form data or JSON
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # Parse the request body as JSON
            request_data = await request.json()

            # Extract user data
            name = request_data.get("name")
            phone = request_data.get("phone")
            password = request_data.get("password")
            role = request_data.get("role")

            # Extract person data
            person_data_dict = request_data.get("person", {})
            person_name = person_data_dict.get("name")
            phone_number = person_data_dict.get("phone_number")
            account_number = person_data_dict.get("account_number")
            ifsc_code = person_data_dict.get("ifsc_code")
            upi_number = person_data_dict.get("upi_number")
        else:
            # Handle form data
            form_data = await request.form()
            name = form_data.get("name")
            phone = form_data.get("phone")
            if phone and isinstance(phone, str):
                phone = int(phone)
            password = form_data.get("password")
            role = form_data.get("role")

            # Extract person data from form
            person_name = form_data.get("person_name") or form_data.get("person.name")
            phone_number = form_data.get("phone_number") or form_data.get("person.phone_number")
            account_number = form_data.get("account_number") or form_data.get("person.account_number")
            ifsc_code = form_data.get("ifsc_code") or form_data.get("person.ifsc_code")
            upi_number = form_data.get("upi_number") or form_data.get("person.upi_number")

        # Validate required fields
        if not name or not phone or not password or not role:
            return JSONResponse(
                status_code=422,
                content={
                    "message": "Missing required fields: name, phone, password, and role are required",
                    "status_code": 422
                }
            )

        # Validate account details (now required)
        if not person_name or not phone_number or not account_number or not ifsc_code:
            return JSONResponse(
                status_code=422,
                content={
                    "message": "Missing required account details: person name, phone number, account number, and IFSC code are required",
                    "status_code": 422
                }
            )

        # If person_name is not provided, use the user's name
        if not person_name:
            person_name = name

        # Ensure phone_number is set - use the user's phone if not provided
        if not phone_number:
            phone_number = str(phone)

        # Create person data
        person_data = CreatePerson(
            name=person_name,
            phone_number=phone_number,
            account_number=account_number,
            ifsc_code=ifsc_code,
            upi_number=upi_number
        )

        user_data = UserCreate(
            name=name,
            phone=phone,
            password=password,
            role=UserRole(role),
            person=person_data
        )

        # Use the register_user API
        from src.app.services.auth_service import register_user

        # Call the API function
        result = register_user(
            user=user_data,
            db=db,
            current_user=current_user
        )

        # Check if the creation was successful
        if result.get("status_code") == 201:
            # Redirect back to the dashboard
            return RedirectResponse(
                url="/web/dashboard",
                status_code=303  # 303 See Other
            )
        else:
            # Return the error result
            return JSONResponse(
                status_code=result.get("status_code", 500),
                content=result
            )
    except Exception as e:
        # Log the error
        logging.error(f"Error creating user: {str(e)}")

        # Return error response
        return JSONResponse(
            status_code=500,
            content={"message": f"Error creating user: {str(e)}", "status_code": 500}
        )


# Logout
@web_ui_router.get("/logout")
async def logout():
    response = RedirectResponse(url="/web/login", status_code=303)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="user_data")
    return response
