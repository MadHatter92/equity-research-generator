from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import json
import hashlib
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

import database as db
import auth
from yahoo_finance import fetch_stock_data, search_stocks
from report_generator import generate_ai_analysis, generate_report_html
from config import (
    SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI, FRONTEND_URL
)

# Initialize FastAPI app
app = FastAPI(
    title="Equity Research Generator",
    description="AI-powered equity research report generator for Indian stocks",
    version="1.0.0"
)

# CORS middleware for frontend
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://equity-research-app.onrender.com",
]

# Add FRONTEND_URL to allowed origins if it's not already there
if FRONTEND_URL and FRONTEND_URL not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth state management
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Configure OAuth
oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

# Mount static files for frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# Request/Response Models
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: str
    password: str


class GenerateReportRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# Auth Routes
@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user."""
    success, message, user = auth.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Auto-login after registration
    _, _, token = auth.authenticate_user(user_data.email, user_data.password)

    return TokenResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"]
        }
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and get access token."""
    success, message, token = auth.authenticate_user(
        email=credentials.email,
        password=credentials.password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )

    user = db.get_user_by_email(credentials.email)

    return TokenResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"]
        }
    )


@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(auth.get_current_user)):
    """Get current logged-in user info."""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "avatar_url": current_user.get("avatar_url"),
        "auth_provider": current_user.get("auth_provider", "local"),
        "created_at": current_user["created_at"]
    }


# Google OAuth Routes
@app.get("/api/auth/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth flow."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@app.get("/api/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )

        # Get or create user in database
        user = db.get_or_create_google_user(
            google_id=user_info['sub'],
            email=user_info['email'],
            full_name=user_info.get('name', user_info.get('email', '')),
            avatar_url=user_info.get('picture')
        )

        # Create JWT token
        access_token = auth.create_access_token(
            data={"sub": str(user["id"]), "email": user["email"]}
        )

        # Redirect to frontend with token
        # The frontend will extract the token and store it
        redirect_url = f"{FRONTEND_URL}/dashboard.html?token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        # Redirect to frontend with error
        redirect_url = f"{FRONTEND_URL}/index.html?error=auth_failed"
        return RedirectResponse(url=redirect_url)


# Helper function for anonymous user identification
def get_client_identifier(request: Request) -> str:
    """Get a hashed identifier for anonymous users based on IP."""
    # Try to get real IP from forwarded headers
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    # Hash the IP for privacy
    return hashlib.sha256(client_ip.encode()).hexdigest()[:32]


# Usage Routes
@app.get("/api/usage")
async def get_usage_stats(current_user: dict = Depends(auth.get_current_user)):
    """Get user's current month usage statistics."""
    usage = db.get_usage(current_user["id"])
    return usage


@app.get("/api/usage/anonymous")
async def get_anonymous_usage_stats(request: Request):
    """Get anonymous user's usage statistics."""
    identifier = get_client_identifier(request)
    usage = db.get_anonymous_usage(identifier)
    return usage


# Stock Search Routes
@app.get("/api/stocks/search")
async def search_indian_stocks(
    q: str,
    limit: int = 10
):
    """Search for Indian stocks by name or symbol."""
    if len(q) < 1:
        return []

    results = search_stocks(q, limit=limit)
    return results


@app.get("/api/stocks/{symbol}")
async def get_stock_info(
    symbol: str,
    exchange: str = "NSE"
):
    """Get basic stock information (preview before generating report)."""
    stock_data = fetch_stock_data(symbol, exchange)

    if not stock_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found on {exchange}"
        )

    # Return summary info only
    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})
    valuation = stock_data.get("valuation", {})

    return {
        "symbol": basic.get("ticker", symbol),
        "company_name": basic.get("company_name", ""),
        "sector": basic.get("sector", ""),
        "industry": basic.get("industry", ""),
        "current_price": price.get("current_price", 0),
        "market_cap": valuation.get("market_cap", 0),
        "pe_ratio": valuation.get("pe_ratio", 0),
    }


# Report Generation Routes
@app.post("/api/reports/generate")
async def generate_report(
    request: Request,
    report_request: GenerateReportRequest,
    current_user: Optional[dict] = Depends(auth.get_optional_current_user)
):
    """Generate a new equity research report."""
    # Check usage limits
    if current_user:
        # Authenticated user - check monthly limit
        if not db.can_generate_report(current_user["id"]):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly report limit reached (20/month). Limit resets on the 1st of next month."
            )
        user_id = current_user["id"]
        is_anonymous = False
    else:
        # Anonymous user - check total limit (3)
        identifier = get_client_identifier(request)
        if not db.can_anonymous_generate(identifier):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Free report limit reached (3 reports). Please sign in for 20 reports/month."
            )
        user_id = None
        is_anonymous = True

    # Fetch stock data
    stock_data = fetch_stock_data(report_request.symbol, report_request.exchange)

    if not stock_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {report_request.symbol} not found on {report_request.exchange}"
        )

    # Generate AI analysis
    analysis = generate_ai_analysis(stock_data)

    # Generate HTML report
    report_html = generate_report_html(stock_data, analysis)

    # Extract key info for storage
    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})

    # Save report to database and increment usage
    if is_anonymous:
        # For anonymous users, we still save the report but with a special marker
        # Use a negative ID to indicate anonymous (or you could use user_id = 0)
        report_id = db.save_report(
            user_id=0,  # Anonymous user marker
            company_name=basic.get("company_name", report_request.symbol),
            ticker=basic.get("ticker", report_request.symbol),
            exchange=report_request.exchange,
            sector=basic.get("sector", ""),
            current_price=price.get("current_price", 0),
            target_price=analysis.get("target_price", 0),
            recommendation=analysis.get("recommendation", "HOLD"),
            report_html=report_html,
            report_data=json.dumps({"stock_data": stock_data, "analysis": analysis})
        )
        db.increment_anonymous_usage(identifier)
    else:
        report_id = db.save_report(
            user_id=user_id,
            company_name=basic.get("company_name", report_request.symbol),
            ticker=basic.get("ticker", report_request.symbol),
            exchange=report_request.exchange,
            sector=basic.get("sector", ""),
            current_price=price.get("current_price", 0),
            target_price=analysis.get("target_price", 0),
            recommendation=analysis.get("recommendation", "HOLD"),
            report_html=report_html,
            report_data=json.dumps({"stock_data": stock_data, "analysis": analysis})
        )
        db.increment_usage(user_id)

    return {
        "report_id": report_id,
        "company_name": basic.get("company_name", ""),
        "ticker": report_request.symbol,
        "recommendation": analysis.get("recommendation", "HOLD"),
        "target_price": analysis.get("target_price", 0),
        "current_price": price.get("current_price", 0)
    }


@app.get("/api/reports")
async def get_user_reports(
    limit: int = 50,
    current_user: dict = Depends(auth.get_current_user)
):
    """Get report history for authenticated user."""
    reports = db.get_user_reports(current_user["id"], limit=limit)
    return reports


@app.get("/api/reports/{report_id}")
async def get_report(
    report_id: int,
    current_user: Optional[dict] = Depends(auth.get_optional_current_user)
):
    """Get a specific report by ID."""
    # For authenticated users, check ownership
    if current_user:
        report = db.get_report_by_id(report_id, current_user["id"])
    else:
        # Anonymous users can access anonymous reports (user_id = 0)
        report = db.get_report_by_id(report_id, 0)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    return report


@app.get("/api/reports/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(
    report_id: int,
    current_user: Optional[dict] = Depends(auth.get_optional_current_user)
):
    """Get the HTML content of a report for viewing."""
    if current_user:
        report = db.get_report_by_id(report_id, current_user["id"])
    else:
        report = db.get_report_by_id(report_id, 0)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    return HTMLResponse(content=report["report_html"])


@app.delete("/api/reports/{report_id}")
async def delete_report(
    report_id: int,
    current_user: dict = Depends(auth.get_current_user)
):
    """Delete a report (authenticated users only)."""
    deleted = db.delete_report(report_id, current_user["id"])

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    return {"message": "Report deleted successfully"}


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Equity Research Generator"}


# Root redirect to frontend
@app.get("/")
async def root():
    """Redirect to frontend."""
    return {"message": "Welcome to Equity Research Generator API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
