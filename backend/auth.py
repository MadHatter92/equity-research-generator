from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import database as db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


def register_user(email: str, password: str, full_name: str) -> tuple[bool, str, Optional[dict]]:
    """
    Register a new user.
    Returns: (success, message, user_data)
    """
    # Validate email format
    if "@" not in email or "." not in email:
        return False, "Invalid email format", None

    # Validate password strength
    if len(password) < 8:
        return False, "Password must be at least 8 characters", None

    # Check if user already exists
    existing_user = db.get_user_by_email(email)
    if existing_user:
        return False, "Email already registered", None

    # Create user
    password_hash = get_password_hash(password)
    user_id = db.create_user(email, password_hash, full_name)

    if user_id is None:
        return False, "Failed to create user", None

    return True, "User created successfully", {
        "id": user_id,
        "email": email,
        "full_name": full_name
    }


def authenticate_user(email: str, password: str) -> tuple[bool, str, Optional[str]]:
    """
    Authenticate user and return token.
    Returns: (success, message, token)
    """
    user = db.get_user_by_email(email)

    if not user:
        return False, "Invalid email or password", None

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid email or password", None

    if not user.get("is_active", True):
        return False, "Account is disabled", None

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"]}
    )

    return True, "Login successful", access_token
