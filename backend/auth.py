from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, get_tier_limits, is_unlimited
import database as db

# Password hashing - using pbkdf2_sha256 (no length limit, secure)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Bearer token security
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def _prepare_password(password: str) -> str:
    """Prepare password for hashing (handle any preprocessing)."""
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(_prepare_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(_prepare_password(password))


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


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[dict]:
    """
    Dependency to get current user if authenticated, None otherwise.
    Use this for routes that work for both authenticated and anonymous users.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = db.get_user_by_id(int(user_id))
    if user is None:
        return None

    if not user.get("is_active", True):
        return None

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

    # Check if user is Google-only (no password)
    if user.get("password_hash") is None:
        return False, "Please sign in with Google", None

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid email or password", None

    if not user.get("is_active", True):
        return False, "Account is disabled", None

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"]}
    )

    return True, "Login successful", access_token


# ============================================
# Access Control Functions
# ============================================

def can_create_portfolio(user: dict) -> tuple[bool, str]:
    """Check if user can create another portfolio."""
    tier = user.get("subscription_tier", "free")
    limits = get_tier_limits(tier)

    if is_unlimited(limits["portfolios"]):
        return True, ""

    current_count = db.get_portfolio_count(user["id"])
    if current_count >= limits["portfolios"]:
        return False, f"You have reached the maximum of {limits['portfolios']} portfolio{'s' if limits['portfolios'] != 1 else ''}. Upgrade to create more."

    return True, ""


def can_add_to_portfolio(user: dict, portfolio_id: int) -> tuple[bool, str]:
    """Check if user can add more stocks to a portfolio."""
    tier = user.get("subscription_tier", "free")
    limits = get_tier_limits(tier)

    if is_unlimited(limits["portfolio_stocks"]):
        return True, ""

    current_count = db.get_holding_count(portfolio_id)
    if current_count >= limits["portfolio_stocks"]:
        return False, f"Portfolio has reached the maximum of {limits['portfolio_stocks']} stocks. Upgrade to add more."

    return True, ""


def can_create_watchlist(user: dict) -> tuple[bool, str]:
    """Check if user can create another watchlist."""
    tier = user.get("subscription_tier", "free")
    limits = get_tier_limits(tier)

    if is_unlimited(limits["watchlists"]):
        return True, ""

    current_count = db.get_watchlist_count(user["id"])
    if current_count >= limits["watchlists"]:
        return False, f"You have reached the maximum of {limits['watchlists']} watchlist{'s' if limits['watchlists'] != 1 else ''}. Upgrade to create more."

    return True, ""


def can_add_to_watchlist(user: dict, watchlist_id: int) -> tuple[bool, str]:
    """Check if user can add more stocks to a watchlist."""
    tier = user.get("subscription_tier", "free")
    limits = get_tier_limits(tier)

    if is_unlimited(limits["watchlist_stocks"]):
        return True, ""

    current_count = db.get_watchlist_item_count(watchlist_id)
    if current_count >= limits["watchlist_stocks"]:
        return False, f"Watchlist has reached the maximum of {limits['watchlist_stocks']} stocks. Upgrade to add more."

    return True, ""


def can_access_mf_analytics(user: dict) -> bool:
    """Check if user has access to MF Analytics."""
    if not user:
        return False
    tier = user.get("subscription_tier", "free")
    limits = get_tier_limits(tier)
    return limits["mf_analytics_access"]


def can_access_pms_tracker(user: dict) -> bool:
    """Check if user has access to PMS Tracker."""
    if not user:
        return False
    tier = user.get("subscription_tier", "free")
    limits = get_tier_limits(tier)
    return limits["pms_tracker_access"]


def require_tier(*allowed_tiers: str):
    """Dependency to require specific subscription tiers."""
    async def tier_checker(current_user: dict = Depends(get_current_user)):
        user_tier = current_user.get("subscription_tier", "free")
        if user_tier not in allowed_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {' or '.join(allowed_tiers)} subscription",
                headers={"X-Required-Tier": ",".join(allowed_tiers)}
            )
        return current_user
    return tier_checker
