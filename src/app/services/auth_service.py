from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from src.app.database.database import get_db
from src.app.database.models import User
from src.app.schemas.auth_service_schamas import UserCreate, UserLogin, Token

# Router Setup
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password Hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__default_rounds=12,
    deprecated="auto"
)

# JWT Configuration
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"


# Utility Functions
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# Dependency for Role-based Access
def get_current_user(db: Session = Depends(get_db), token: str = Depends(lambda: "")):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(User).filter(User.uuid == payload.get("sub")).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

def superadmin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "SuperAdmin":
        raise HTTPException(status_code=403, detail="SuperAdmin privileges required")
    return current_user

# Routes
@auth_router.post("/register", response_model=Token)
def register_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(superadmin_required)):
    db_user = db.query(User).filter(User.phone == user.phone).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Phone already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        phone=user.phone,
        password_hash=hashed_password,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": str(new_user.uuid)})
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.phone == user.phone).first()
    print(f"Entered Password: {user.password}")
    print(f"Stored Hash: {db_user.password_hash}")
    verified = verify_password(user.password, db_user.password_hash)
    print(f"Password Verified: {verified}")  
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect phone or password")
    access_token = create_access_token(data={"sub": str(db_user.uuid)})
    return {"access_token": access_token, "token_type": "bearer"}
