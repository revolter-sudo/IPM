from uuid import UUID
from datetime import datetime, timedelta
from src.app.utils.logging_config import get_logger

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Security,
    status,
    UploadFile,
    File,
    Query
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from uuid import uuid4
from src.app.database.database import get_db, settings
from src.app.database.models import User, Log, Person, UserTokenMap , UserData
from src.app.schemas.auth_service_schamas import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
    AuthServiceResponse,
    ForgotPasswordRequest,
    UserLogout,
    UserEdit,
    OutsideUserLogin,
    PersonWithRole,
    RoleBasedPersonQueryRequest,
    RoleBasedPersonQueryResponse,
    UpdatePersonRoleRequest,
    UpdatePersonRoleResponse
)
from src.app.notification.notification_service import (
    subscribe_news,
    unsubscribe_news
)
from src.app.schemas import constants
import os
import redis
from typing import Optional
from fastapi import Request
import traceback

# Initialize logger
logger = get_logger(__name__)

# Redis client for token blacklisting
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=int(settings.REDIS_PORT),
        decode_responses=True
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis client initialized for token blacklisting")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Token blacklisting disabled.")
    redis_client = None

# Router Setup
auth_router = APIRouter(prefix="/auth")

# Password Hashing
pwd_context = CryptContext(
    schemes=["bcrypt"], bcrypt__default_rounds=12, deprecated="auto"
)
# print("================================")
# print(f"Password Hash -> {pwd_context.hash('supersecurepassword')}")
# print("================================")

# JWT Configuration
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer()
# OAuth2 scheme for Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Token Blacklisting Functions
def blacklist_token(jti: str, exp_timestamp: int):
    """Add token to blacklist until its natural expiration"""
    if redis_client:
        try:
            # Calculate TTL (time to live) until token expires
            current_time = datetime.utcnow().timestamp()
            ttl = max(int(exp_timestamp - current_time), 1)
            redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
            logger.info(f"Token {jti} blacklisted for {ttl} seconds")
        except Exception as e:
            logger.error(f"Failed to blacklist token {jti}: {e}")


def is_token_blacklisted(jti: str) -> bool:
    """Check if token is blacklisted"""
    if redis_client:
        try:
            return redis_client.exists(f"blacklist:{jti}")
        except Exception as e:
            logger.error(f"Failed to check blacklist for token {jti}: {e}")
    return False


# Utility Functions
def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, request_ip: str = None):
    to_encode = data.copy()
    jti = str(uuid4())  # Unique token identifier for blacklisting
    iat = datetime.utcnow()  # Issued at timestamp

    # Always add JTI and IAT for security
    to_encode.update({
        "jti": jti,
        "iat": iat
    })

    # Environment-based token expiration
    if settings.ENVIRONMENT.upper() == "LOCAL":
        # No expiration for LOCAL environment
        pass
    else:
        # Use configured expiration for other environments (DEV, STAGING, PROD)
        expire_minutes = settings.JWT_TOKEN_EXPIRE_MINUTES
        if expire_minutes > 0:
            expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
            to_encode.update({"exp": expire})

        # Optional: Add IP binding for extra security
        if request_ip and settings.ENABLE_IP_VALIDATION:
            to_encode.update({"ip": request_ip})
            logger.info(f"Token {jti} bound to IP: {request_ip}")

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    token = credentials.credentials  # Extract token from Authorization header
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = payload.get("sub")
        jti = payload.get("jti")  # Token identifier

        if not user_uuid:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        # Check if token is blacklisted
        if jti and is_token_blacklisted(jti):
            logger.warning(f"Blacklisted token used: {jti}")
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked"
            )

        # Optional: Validate IP binding
        if settings.ENABLE_IP_VALIDATION:
            token_ip = payload.get("ip")
            # Note: You'd need to get current request IP here
            # This is a placeholder for IP validation logic

        user = (
            db.query(User)
            .filter(
                User.uuid == user_uuid,
                User.is_deleted.is_(False),
                User.is_active.is_(True),
            )
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User Not Found"
            )

        return user

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )


def superadmin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPER_ADMIN:
        return AuthServiceResponse(
                data=None,
                status_code=403,
                message="SuperAdmin privileges required"
            ).model_dump()
    return current_user


@auth_router.post("/upload_photo", tags=["Users"])
def upload_user_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a photo for the current user and updates `photo_path`.
    Returns the path/URL so the frontend can load it.
    """
    try:
        # logger.info(f"[{current_user.name}] Uploading profile photo: {file.filename}")

        upload_dir = os.path.join(constants.UPLOAD_DIR, "users")
        os.makedirs(upload_dir, exist_ok=True)

        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{str(uuid4())}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        # Save URL path for NGINX/static use
        current_user.photo_path = f"{constants.HOST_URL}/uploads/payments/users/{unique_filename}"
        db.commit()
        db.refresh(current_user)

        logger.info(f"[{current_user.name}] Photo uploaded successfully: {current_user.photo_path}")

        return AuthServiceResponse(
            data={"photo_path": current_user.photo_path},
            message="User photo uploaded successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Failed to upload photo: {str(e)}")
        logger.error(traceback.format_exc())

        return AuthServiceResponse(
            data=None,
            message=f"An error occurred: {str(e)}",
            status_code=500
        ).model_dump()



@auth_router.post("/forgot_password", tags=["Users"])
def forgot_password(
    payload: ForgotPasswordRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resets a user's password, given a phone number and a new password.
    In production, you would typically verify OTP or email link, but
    here it's a simple, direct reset for demonstration.
    """
    try:

        # 1) Find user by phone
        user = (
            db.query(User)
            .filter(
                User.phone == payload.phone,
                User.is_deleted.is_(False)
            )
            .first()
        )
        if not user:
            logger.warning(f"[{current_user.name}] Password reset failed - phone not found: {payload.phone}")
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="No user found with this phone number."
            ).model_dump()

        # 2) Hash and update password
        hashed = pwd_context.hash(payload.new_password)
        user.password_hash = hashed
        db.commit()
        db.refresh(user)

        logger.info(f"[{current_user.name}] successfully reset password for user: {user.name} ({user.password_hash})")

        return AuthServiceResponse(
            data={
                "uuid": str(user.uuid),
                "phone": user.phone
            },
            message="Password reset successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error during password reset for phone: {payload.phone} - {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            message="An internal error occurred during password reset.",
            status_code=500
        ).model_dump()


# Routes
@auth_router.post(
    "/register",
    tags=["Users"],
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
) -> dict:
    try:

        db_user = (
            db.query(User)
            .filter(
                and_(
                    User.phone == user.phone,
                    User.is_deleted.is_(False),
                    User.is_active.is_(True),
                )
            )
            .first()
        )

        if db_user:
            logger.warning(f"[{current_user.name}] Registration failed - Phone already registered: {user.phone}")
            return AuthServiceResponse(
                data=None,
                status_code=400,
                message="Phone already registered"
            ).model_dump()

        hashed_password = get_password_hash(user.password)
        new_user = User(
            name=user.name,
            phone=user.phone,
            password_hash=hashed_password,
            role=user.role.value,
            is_deleted=False,
            is_active=True,
        )
        db.add(new_user)
        db.flush()

        # Check for existing Person
        existing_person = db.query(Person).filter(
            (Person.phone_number == user.person.phone_number) &
            (Person.account_number == user.person.account_number)
        ).first()

        if existing_person:
            existing_person.user_id = new_user.uuid
            db.add(existing_person)
            db.commit()
            db.refresh(new_user)
            db.refresh(existing_person)
            logger.info(f"[{current_user.name}] Linked existing person (ID: {existing_person.id}) to user: {new_user.uuid}")
        else:
            new_person = Person(
                name=user.person.name,
                phone_number=user.person.phone_number,
                account_number=user.person.account_number,
                ifsc_code=user.person.ifsc_code,
                user_id=new_user.uuid
            )
            db.add(new_person)
            db.commit()
            db.refresh(new_user)
            db.refresh(new_person)
            logger.info(f"[{current_user.name}] Created new person (ID: {new_person.id}) for user: {new_user.uuid}")

        access_token = create_access_token(data={"sub": str(new_user.uuid)})
        response = {"access_token": access_token, "token_type": "bearer"}

        logger.info(f"[{current_user.name}] Successfully registered user: {new_user.name} ({new_user.uuid})")

        return AuthServiceResponse(
            data=response,
            message="User registered successfully",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error during user registration for phone: {user.phone} - {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            message="An internal error occurred during registration.",
            status_code=500
        ).model_dump()


def check_or_add_token(
    user_id: UUID,
    fcm_token: str,
    device_id: int,
    db: Session
):
    try:
        data = db.query(UserTokenMap).filter(
            UserTokenMap.device_id == device_id
        ).first()

        if data:
            data.fcm_token = fcm_token
        else:
            user_token_data = UserTokenMap(
                user_id=user_id,
                fcm_token=fcm_token,
                device_id=device_id,
            )
            db.add(user_token_data)

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error while registering FCM token for user {user_id} on device {device_id}: {str(e)}")
        logger.error(traceback.format_exc())

        return AuthServiceResponse(
            data=None,
            message=f"Error while check_or_add_token: {str(e)}",
            status_code=500
        ).model_dump()


@auth_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    tags=["Users"]
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
) -> dict:
    db_user = (
        db.query(User)
        .filter(
            User.phone == login_data.phone,
            User.is_deleted.is_(False),
            User.is_active.is_(True),
        )
        .first()
    )

    if not db_user:
        logger.warning(f"Login failed - no active user found for phone: {login_data.phone}")
        return AuthServiceResponse(
            data=None,
            status_code=400,
            message="Incorrect phone or password"
        ).model_dump()

    if not verify_password(login_data.password, db_user.password_hash):
        logger.warning(f"Login failed - incorrect password for user: {db_user.name} ({db_user.uuid})")
        return AuthServiceResponse(
            data=None,
            status_code=400,
            message="Incorrect phone or password"
        ).model_dump()

    logger.info(f"Login: {db_user.name} (phone: {login_data.phone}, device: {login_data.device_id}) at {datetime.utcnow()}")

    user_data = UserResponse(
        uuid=db_user.uuid,
        name=db_user.name,
        phone=db_user.phone,
        role=db_user.role,
        photo_path=db_user.photo_path
    ).to_dict()

    access_token = create_access_token(data={"sub": str(db_user.uuid)})

    if login_data.fcm_token:
        check_or_add_token(
            user_id=db_user.uuid,
            fcm_token=login_data.fcm_token,
            device_id=login_data.device_id,
            db=db
        )
        subscribe_news(
            tokens=login_data.fcm_token,
            topic=db_user.uuid
        )

    response = {
        "access_token": access_token,
        "token_type": "bearer",
        "user_data": user_data
    }

    return AuthServiceResponse(
        data=response,
        message="User logged in successfully",
        status_code=201
    ).model_dump()

@auth_router.put(
    "/delete",
    status_code=status.HTTP_201_CREATED,
    tags=["Users"]
)
def delete_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    try:

        user_data = (
            db.query(User)
            .filter(
                and_(
                    User.uuid == user_uuid,
                    User.is_deleted.is_(False),
                    User.is_active.is_(True),
                )
            )
            .first()
        )

        if not user_data:
            logger.warning(f"[{current_user.name}] deletion failed - user not found")
            raise HTTPException(status_code=404, detail="User does not exist")

        if user_data.role == UserRole.SUPER_ADMIN:
            logger.warning(f"[{current_user.name}] attempted to delete SUPER_ADMIN user")
            raise HTTPException(
                status_code=403, detail="SuperAdmin user cannot be deleted."
            )

        user_data.is_deleted = True

        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Delete",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(user_data)

        logger.info(f"[{current_user.name}] deleted user: {user_data.name}")

        return AuthServiceResponse(
            data=None,
            message="User deleted successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error while deleting user: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in delete_user API: {str(e)}"
        ).model_dump()


@auth_router.post(
    "/logout",
    status_code=status.HTTP_201_CREATED,
    tags=["Users"]
)
def logout_user(
    user_data: UserLogout,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    try:

        # 1. Extract and blacklist the JWT token
        token = credentials.credentials
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                blacklist_token(jti, exp)
                logger.info(f"Token blacklisted for user {current_user.name} | JTI: {jti}")
            else:
                logger.warning(f"Missing JTI or EXP while decoding token for logout - user: {current_user.name}")

        except Exception as e:
            logger.warning(f"Failed to decode or blacklist token during logout for user {current_user.name}: {str(e)}")

        # 2. Unsubscribe user from FCM
        user = db.query(User).filter(User.uuid == user_data.user_id).first()
        user_token = db.query(UserTokenMap.fcm_token).filter(
            UserTokenMap.device_id == user_data.device_id
        ).first()

        if user_token:
            unsubscribe_news(tokens=user_token[0], topic=str(user.uuid))
            logger.info(f"[{current_user.name}] unsubscribed from FCM topic.")
        else:
            logger.info(f"[{current_user.name}] no matching FCM token found for device {user_data.device_id}")

        return AuthServiceResponse(
            data=None,
            message="User Logged Out Successfully!",
            status_code=201
        ).model_dump()

    except Exception as e:
        logger.error(f"[{current_user.name}] Error during logout: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            message=f"Error in logout_user API: {str(e)}",
            status_code=200
        ).model_dump()

@auth_router.put("/deactivate", status_code=status.HTTP_200_OK, tags=["Users"])
def deactivate_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    try:

        user_data = (
            db.query(User)
            .filter(
                and_(
                    User.uuid == user_uuid,
                    User.is_deleted.is_(False),
                    User.is_active.is_(True),
                )
            )
            .first()
        )

        if not user_data:
            logger.warning(f"[{current_user.name}] deactivation failed - user not found.")
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User does not exist"
            ).model_dump()

        if user_data.role == UserRole.SUPER_ADMIN:
            logger.warning(f"[{current_user.name}] tried to deactivate SUPER_ADMIN.")
            return AuthServiceResponse(
                data=None,
                status_code=403,
                message="SuperAdmin user cannot be deactivated."
            ).model_dump()

        user_data.is_active = False
        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Deactivate",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(user_data)

        logger.info(f"[{current_user.name}] deactivated user: {user_data.name}.")

        return AuthServiceResponse(
            data=None,
            message="User deactivated successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error in deactivate_user API for user: {str(e)}")
        logger.error(traceback.format_exc())

        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in deactivate_user API: {str(e)}"
        ).model_dump()


@auth_router.put("/activate", status_code=status.HTTP_200_OK, tags=["Users"])
def activate_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    try:

        user_data = (
            db.query(User)
            .filter(
                and_(
                    User.uuid == user_uuid,
                    User.is_deleted.is_(False),
                )
            )
            .first()
        )

        if not user_data:
            logger.warning(f"[{current_user.name}] activation failed - user not found.")
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User does not exist"
            ).model_dump()

        if user_data.role == UserRole.SUPER_ADMIN:
            logger.warning(f"[{current_user.name}] tried to activate SUPER_ADMIN.")
            return AuthServiceResponse(
                data=None,
                status_code=403,
                message="SuperAdmin user cannot be activated."
            ).model_dump()

        user_data.is_active = True
        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Activate",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(user_data)

        logger.info(f"[{current_user.name}] activated user: {user_data.name}.")

        return AuthServiceResponse(
            data=None,
            message="User activated successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error in activate_user API for user: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in activate_user API: {str(e)}"
        ).model_dump()


@auth_router.get("/users", status_code=status.HTTP_200_OK, tags=["Users"])
def list_all_active_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        users = db.query(User).filter(
            User.is_active.is_(True),
            User.is_deleted.is_(False)
        ).order_by(User.id.desc()).all()

        user_response_data = []
        for user in users:
            person_data = None
            if user.person:
                person_data = {
                    "uuid": str(user.person.uuid),
                    "name": user.person.name,
                    "account_number": user.person.account_number,
                    "ifsc_code": user.person.ifsc_code,
                    "phone_number": user.person.phone_number,
                }

            user_response_data.append({
                "uuid": str(user.uuid),
                "name": user.name,
                "phone": user.phone,
                "role": user.role,
                "photo_path": user.photo_path,
                "person": person_data
            })

        logger.info(f"[{current_user.name}] fetched {len(user_response_data)} active users successfully")

        return AuthServiceResponse(
            data=user_response_data,
            message="All users fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"[{current_user.name}] Error in list_all_active_users API: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching users: {str(e)}"
        ).model_dump()


# @auth_router.get("/user", tags=["Users"])
# def get_user_info(user_uuid: UUID, db: Session = Depends(get_db)):
#     try:
#         user = (
#             db.query(User)
#             .filter(and_(User.uuid == user_uuid, User.is_active.is_(True)))
#             .first()
#         )

#         if not user:
#             return AuthServiceResponse(
#                 data=None,
#                 status_code=404,
#                 message="User does not exist"
#             ).model_dump()

#         person_data = None
#         if user.person:
#             person_data = {
#                 "uuid": user.person.uuid,
#                 "name": user.person.name,
#                 "account_number": user.person.account_number,
#                 "ifsc_code": user.person.ifsc_code,
#                 "phone_number": user.person.phone_number,
#             }

#         user_response = {
#             "uuid": user.uuid,
#             "name": user.name,
#             "phone": user.phone,
#             "role": user.role,
#             "photo_path": user.photo_path,
#             "person": person_data
#         }

#         return AuthServiceResponse(
#             data=user_response,
#             message="User info fetched successfully",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         logger.error(f"Error in get_user_info API: {str(e)}")
#         return AuthServiceResponse(
#             data=None,
#             status_code=500,
#             message=f"Error fetching user info: {str(e)}"
#         ).model_dump()


@auth_router.get("/user", tags=["Users"])
def get_user_info(
    user_uuid: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        user = (
            db.query(User)
            .filter(
                User.uuid == user_uuid,
                User.is_active.is_(True),
                User.is_deleted.is_(False)
            )
            .first()
        )

        if not user:
            logger.warning(f"[{current_user.name}] attempted to fetch non-existent user.")
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User does not exist"
            ).model_dump()

        person_data = None
        if user.person:
            person_record = user.person
            person_data = {
                "uuid": str(person_record.uuid),
                "name": person_record.name,
                "account_number": person_record.account_number,
                "ifsc_code": person_record.ifsc_code,
                "phone_number": person_record.phone_number,
                "parent_id": person_record.parent_id,
                "upi_number": person_record.upi_number,
                "secondary_accounts": [
                    {
                        "uuid": str(child.uuid),
                        "name": child.name,
                        "account_number": child.account_number,
                        "ifsc_code": child.ifsc_code,
                        "phone_number": child.phone_number,
                        "upi_number": child.upi_number
                    }
                    for child in person_record.children
                ]
            }

        user_response = {
            "uuid": str(user.uuid),
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "photo_path": user.photo_path,
            "person": person_data
        }

        logger.info(f"[{current_user.name}] successfully fetched info for user: {user.name}")

        return AuthServiceResponse(
            data=user_response,
            message="User info fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error fetching user info - {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred: {str(e)}"
        ).model_dump()


@auth_router.put(
    "/edit-user/{user_uuid}",
    tags=["Users"],
    status_code=status.HTTP_200_OK
)
def edit_user(
    user_uuid: UUID,
    user_data: UserEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    """
    Edit user information including person data.
    Only superadmin can edit users.
    """
    try:

        user = db.query(User).filter(
            User.uuid == user_uuid,
            User.is_deleted.is_(False)
        ).first()

        if not user:
            logger.warning(f"[{current_user.name}] edit failed - user not found")
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        if user_data.name:
            user.name = user_data.name

        if user_data.phone:
            existing_user = db.query(User).filter(
                User.phone == user_data.phone,
                User.uuid != user_uuid,
                User.is_deleted.is_(False)
            ).first()

            if existing_user:
                logger.warning(f"[{current_user.name}] edit failed - phone number already in use")
                return AuthServiceResponse(
                    data=None,
                    status_code=400,
                    message="Phone number already in use by another user"
                ).model_dump()

            user.phone = user_data.phone

        if user_data.role:
            user.role = user_data.role.value

        if user_data.person:
            person = user.person
            if not person:
                person = Person(user_id=user.uuid)
                db.add(person)
                db.flush()

            if user_data.person.name:
                person.name = user_data.person.name
            if user_data.person.account_number:
                person.account_number = user_data.person.account_number
            if user_data.person.ifsc_code:
                person.ifsc_code = user_data.person.ifsc_code
            if user_data.person.phone_number:
                person.phone_number = user_data.person.phone_number
            if user_data.person.upi_number:
                person.upi_number = user_data.person.upi_number
            if user_data.person.parent_id:
                person.parent_id = user_data.person.parent_id

        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Edit",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)

        db.commit()
        db.refresh(user)

        logger.info(f"[{current_user.name}] successfully edited user: {user.name}")

        person_data = None
        if user.person:
            person_data = {
                "uuid": str(user.person.uuid),
                "name": user.person.name,
                "account_number": user.person.account_number,
                "ifsc_code": user.person.ifsc_code,
                "phone_number": user.person.phone_number,
                "upi_number": user.person.upi_number
            }

        return AuthServiceResponse(
            data={
                "uuid": str(user.uuid),
                "name": user.name,
                "phone": user.phone,
                "role": user.role,
                "photo_path": user.photo_path,
                "person": person_data
            },
            message="User updated successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error in edit_user API for user: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error updating user: {str(e)}"
        ).model_dump()


@auth_router.get("/persons", status_code=status.HTTP_200_OK, tags=["Persons"])
def get_persons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    name: Optional[str] = Query(None, description="Filter by name"),
    phone: Optional[str] = Query(None, description="Filter by phone number"),
):
    """
    Get all persons with optional filters. This endpoint provides a simplified view
    of persons for frontend dropdowns and selections.
    """
    try:

        query = db.query(Person).filter(Person.is_deleted.is_(False))

        if name:
            query = query.filter(Person.name.ilike(f"%{name}%"))
        if phone:
            query = query.filter(Person.phone_number == phone)

        persons = query.all()

        persons_data = [{
            "uuid": str(person.uuid),
            "name": person.name,
            "phone_number": person.phone_number,
            "account_number": person.account_number,
            "ifsc_code": person.ifsc_code,
            "upi_number": person.upi_number
        } for person in persons]

        logger.info(f"[{current_user.name}] fetched {len(persons_data)} persons successfully")

        return AuthServiceResponse(
            data=persons_data,
            message="Persons fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error in get_persons API: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching persons: {str(e)}"
        ).model_dump()
    

@auth_router.post(
    '/register_and_save_user',
    tags=['non-user']
)
def register_and_outside_user(
    data: OutsideUserLogin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    phone = str(data.phone_number)

    try:

        existing = db.query(UserData).filter(UserData.phone_number == phone).first()
        if existing:
            logger.warning(f"[{current_user.name}] registration blocked - phone already submitted: {phone}")
            return AuthServiceResponse(
                data=None,
                message=(
                    "You’ve already submitted a request with this number, "
                    "our team is looking into it and will reach out shortly."
                ),
                status_code=200
            )

        user_data = UserData(
            name=data.name,
            email=data.email,
            phone_number=phone,
            password=data.password
        )
        db.add(user_data)
        db.commit()
        db.refresh(user_data)

        logger.info(f"[{current_user.name}] successfully registered external user: {data.name}")

        return AuthServiceResponse(
            data=None,
            message="We have received your request, our team will reach out to you soon.",
            status_code=201
        )

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error registering outside user- {str(e)}")
        logger.error(traceback.format_exc())

        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred: {str(e)}"
        ).model_dump()


@auth_router.get(
    '/outside_users',
    status_code=status.HTTP_200_OK,
    tags=['non-user']
)
def list_outside_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required)
):
    """
    List all outside users who have registered through the register_and_outside_user endpoint.
    Only accessible by SuperAdmin users.
    """
    try:

        outside_users = db.query(UserData).all()

        outside_users_data = []
        for user in outside_users:
            outside_users_data.append({
                "uuid": str(user.uuid),
                "name": user.name,
                "email": user.email,
                "phone_number": user.phone_number,
                "password": user.password,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })

        logger.info(f"[{current_user.name}] fetched {len(outside_users_data)} outside users successfully")

        return AuthServiceResponse(
            data=outside_users_data,
            message="Outside users fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"[{current_user.name}] Error in list_outside_users API: {str(e)}")
        logger.error(traceback.format_exc())

        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching outside users: {str(e)}"
        ).model_dump()


@auth_router.get("/persons/by-role", status_code=status.HTTP_200_OK, tags=["Persons"])
def get_persons_by_role(
    role: UserRole = Query(..., description="Role to filter persons by"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        # Validate user role
        if not current_user or not hasattr(current_user, 'role'):
            logger.warning("Invalid session in get_persons_by_role")
            return AuthServiceResponse(
                data=None,
                message="Invalid user session",
                status_code=401
            ).model_dump()

        if current_user.role not in [
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            logger.warning(f"Access denied for user [{current_user.name}] to /persons/by-role")
            return AuthServiceResponse(
                data=None,
                message="Access denied. Admin, Super Admin, or Project Manager privileges required.",
                status_code=403
            ).model_dump()

        role_value = role.value

        # Query persons with direct role
        try:
            persons_with_direct_role = db.query(Person).filter(
                Person.role == role_value,
                Person.is_deleted.is_(False)
            ).all()
            logger.info(f"[{current_user.name}] found {len(persons_with_direct_role)} persons with direct role: {role_value}")
        except Exception as e:
            logger.error(f"DB error querying persons with direct role '{role_value}': {str(e)}")
            logger.error(traceback.format_exc())
            return AuthServiceResponse(
                data=None,
                message="Error retrieving persons with direct role assignment",
                status_code=500
            ).model_dump()

        # Query persons linked to users with this role
        try:
            persons_with_user_role = db.query(Person).join(
                User, Person.user_id == User.uuid
            ).filter(
                User.role == role_value,
                User.is_deleted.is_(False),
                User.is_active.is_(True),
                Person.is_deleted.is_(False)
            ).all()
            logger.info(f"[{current_user.name}] found {len(persons_with_user_role)} persons with linked user role: {role_value}")
        except Exception as e:
            logger.error(f"DB error querying persons with user role '{role_value}': {str(e)}")
            logger.error(traceback.format_exc())
            return AuthServiceResponse(
                data=None,
                message="Error retrieving persons with user role assignment",
                status_code=500
            ).model_dump()

        combined_persons = {}

        # Process direct role persons
        try:
            for person in persons_with_direct_role:
                if not person or not hasattr(person, 'uuid'):
                    continue
                combined_persons[str(person.uuid)] = PersonWithRole(
                    uuid=person.uuid,
                    name=person.name or "",
                    phone_number=person.phone_number or "",
                    account_number=person.account_number,
                    ifsc_code=person.ifsc_code,
                    upi_number=person.upi_number,
                    role=person.role or role_value,
                    role_source="person",
                    user_id=person.user_id
                )
        except Exception as e:
            logger.error(f"Error processing direct role persons: {str(e)}")
            logger.error(traceback.format_exc())
            return AuthServiceResponse(
                data=None,
                message="Error processing direct role persons",
                status_code=500
            ).model_dump()

        # Process linked user-role persons
        try:
            for person in persons_with_user_role:
                pid = str(person.uuid)
                if pid in combined_persons:
                    continue

                user = db.query(User).filter(User.uuid == person.user_id).first() if person.user_id else None

                combined_persons[pid] = PersonWithRole(
                    uuid=person.uuid,
                    name=person.name or "",
                    phone_number=person.phone_number or "",
                    account_number=person.account_number,
                    ifsc_code=person.ifsc_code,
                    upi_number=person.upi_number,
                    role=user.role if user else role_value,
                    role_source="user",
                    user_id=person.user_id
                )
        except Exception as e:
            logger.error(f"Error processing user-linked role persons: {str(e)}")
            logger.error(traceback.format_exc())
            return AuthServiceResponse(
                data=None,
                message="Error processing persons with user role assignment",
                status_code=500
            ).model_dump()

        # Sort and prepare response
        try:
            result_persons = sorted(combined_persons.values(), key=lambda x: x.name or "")
        except Exception as e:
            logger.warning(f"Sorting failed: {str(e)}")
            result_persons = list(combined_persons.values())

        logger.info(f"[{current_user.name}] total deduplicated persons fetched: {len(result_persons)}")

        return RoleBasedPersonQueryResponse(
            data=result_persons,
            message=f"Persons with role '{role_value}' fetched successfully. Found {len(result_persons)} persons.",
            status_code=200
        ).to_dict()

    except Exception as e:
        logger.error(f"Unhandled error in get_persons_by_role: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching persons by role: {str(e)}"
        ).model_dump()


@auth_router.put("/persons/{person_id}/role", status_code=status.HTTP_200_OK, tags=["Persons"])
def update_person_role(
    person_id: UUID,
    request_data: UpdatePersonRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        if not current_user or not hasattr(current_user, 'role'):
            logger.warning(f"Invalid session while updating person {person_id}")
            return AuthServiceResponse(
                data=None,
                message="Invalid user session",
                status_code=401
            ).model_dump()

        if current_user.role not in [
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value,
        ]:
            logger.warning(f"Access denied - [{current_user.name}] tried to update person {person_id}")
            return AuthServiceResponse(
                data=None,
                message="Access denied. Admin or Super Admin privileges required.",
                status_code=403
            ).model_dump()

        if not person_id:
            logger.warning(f"Missing person_id in request by [{current_user.name}]")
            return AuthServiceResponse(
                data=None,
                message="Person ID is required",
                status_code=400
            ).model_dump()

        try:
            person = db.query(Person).filter(
                Person.uuid == person_id,
                Person.is_deleted.is_(False)
            ).first()
        except Exception as e:
            logger.error(f"DB error querying person {person_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return AuthServiceResponse(
                data=None,
                message="Error retrieving person data",
                status_code=500
            ).model_dump()

        if not person:
            logger.warning(f"Person not found or deleted: {person_id}")
            return AuthServiceResponse(
                data=None,
                message="Person not found or has been deleted",
                status_code=404
            ).model_dump()

        role_value = request_data.role.value if request_data.role else None

        try:
            old_role = person.role
            person.role = role_value
            db.commit()
            db.refresh(person)
            logger.info(f"[{current_user.name}] updated role for person {person_id} from '{old_role}' to '{role_value}'")
        except Exception as e:
            db.rollback()
            logger.error(f"DB error updating role for person {person_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return AuthServiceResponse(
                data=None,
                message="Error updating person role",
                status_code=500
            ).model_dump()

        try:
            response_data = {
                "person_id": str(person.uuid),
                "name": person.name,
                "phone_number": person.phone_number,
                "old_role": old_role,
                "new_role": role_value,
                "updated_by": str(current_user.uuid),
                "updated_at": datetime.now().isoformat()
            }

            message = "Person role updated successfully."
            if role_value:
                message += f" Role set to '{role_value}'."
            else:
                message += " Role removed."

            return UpdatePersonRoleResponse(
                data=response_data,
                message=message,
                status_code=200
            ).to_dict()

        except Exception as e:
            logger.error(f"Error formatting response for person {person_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return AuthServiceResponse(
                data=None,
                message="Error formatting response data",
                status_code=500
            ).model_dump()

    except Exception as e:
        logger.error(f"Unexpected error in update_person_role for person {person_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error updating person role: {str(e)}"
        ).model_dump()
