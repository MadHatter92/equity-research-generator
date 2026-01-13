from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import json
from pathlib import Path

import database as db
import auth
from yahoo_finance import fetch_stock_data, search_stocks
from report_generator import generate_ai_analysis, generate_report_html

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "created_at": current_user["created_at"]
    }


# Usage Routes
@app.get("/api/usage")
async def get_usage_stats(current_user: dict = Depends(auth.get_current_user)):
    """Get user's current month usage statistics."""
    usage = db.get_usage(current_user["id"])
    return usage


# Stock Search Routes
@app.get("/api/stocks/search")
async def search_indian_stocks(
    q: str,
    limit: int = 10,
    current_user: dict = Depends(auth.get_current_user)
):
    """Search for Indian stocks by name or symbol."""
    if len(q) < 1:
        return []

    results = search_stocks(q, limit=limit)
    return results


@app.get("/api/stocks/{symbol}")
async def get_stock_info(
    symbol: str,
    exchange: str = "NSE",
    current_user: dict = Depends(auth.get_current_user)
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
    request: GenerateReportRequest,
    current_user: dict = Depends(auth.get_current_user)
):
    """Generate a new equity research report."""
    # Check usage limit
    if not db.can_generate_report(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly report limit reached. Please wait for the next billing cycle."
        )

    # Fetch stock data
    stock_data = fetch_stock_data(request.symbol, request.exchange)

    if not stock_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {request.symbol} not found on {request.exchange}"
        )

    # Generate AI analysis
    analysis = generate_ai_analysis(stock_data)

    # Generate HTML report
    report_html = generate_report_html(stock_data, analysis)

    # Extract key info for storage
    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})

    # Save report to database
    report_id = db.save_report(
        user_id=current_user["id"],
        company_name=basic.get("company_name", request.symbol),
        ticker=basic.get("ticker", request.symbol),
        exchange=request.exchange,
        sector=basic.get("sector", ""),
        current_price=price.get("current_price", 0),
        target_price=analysis.get("target_price", 0),
        recommendation=analysis.get("recommendation", "HOLD"),
        report_html=report_html,
        report_data=json.dumps({"stock_data": stock_data, "analysis": analysis})
    )

    # Increment usage counter
    db.increment_usage(current_user["id"])

    # Get updated usage
    usage = db.get_usage(current_user["id"])

    return {
        "report_id": report_id,
        "company_name": basic.get("company_name", ""),
        "ticker": request.symbol,
        "recommendation": analysis.get("recommendation", "HOLD"),
        "target_price": analysis.get("target_price", 0),
        "current_price": price.get("current_price", 0),
        "usage": usage
    }


@app.get("/api/reports")
async def get_user_reports(
    limit: int = 50,
    current_user: dict = Depends(auth.get_current_user)
):
    """Get user's report history."""
    reports = db.get_user_reports(current_user["id"], limit=limit)
    return reports


@app.get("/api/reports/{report_id}")
async def get_report(
    report_id: int,
    current_user: dict = Depends(auth.get_current_user)
):
    """Get a specific report by ID."""
    report = db.get_report_by_id(report_id, current_user["id"])

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    return report


@app.get("/api/reports/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(
    report_id: int,
    current_user: dict = Depends(auth.get_current_user)
):
    """Get the HTML content of a report for viewing."""
    report = db.get_report_by_id(report_id, current_user["id"])

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
    """Delete a report."""
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
