import os
from pathlib import Path
from typing import TypedDict

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database - Use Render's persistent disk if available
DATA_DIR = os.getenv("RENDER_DISK_PATH", str(BASE_DIR / "data"))
DATABASE_URL = f"sqlite:///{DATA_DIR}/research.db"

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-abc123xyz")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Google OAuth Settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

# Frontend URL for OAuth redirects
# Default to localhost:8000/static for local dev (backend serves frontend)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000/static")

# Yahoo Finance - Indian stock suffixes
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"


# ============================================
# Subscription Tier Configuration
# ============================================

class TierLimits(TypedDict):
    reports_total: int | None      # For guest (lifetime limit), None for monthly tiers
    reports_monthly: int | None    # For paid tiers (monthly limit)
    portfolios: int                # -1 = unlimited
    portfolio_stocks: int          # Max stocks per portfolio, -1 = unlimited
    watchlists: int                # -1 = unlimited
    watchlist_stocks: int          # Max stocks per watchlist, -1 = unlimited
    mf_analytics_access: bool
    pms_tracker_access: bool
    export_pdf: bool
    api_access: bool


TIER_LIMITS: dict[str, TierLimits] = {
    "guest": {
        "reports_total": 3,           # 3 total lifetime reports
        "reports_monthly": None,
        "portfolios": 0,
        "portfolio_stocks": 0,
        "watchlists": 0,
        "watchlist_stocks": 0,
        "mf_analytics_access": False,
        "pms_tracker_access": False,
        "export_pdf": False,
        "api_access": False,
    },
    "free": {
        "reports_total": None,
        "reports_monthly": 20,        # 20 reports per month
        "portfolios": 1,
        "portfolio_stocks": 20,
        "watchlists": 1,
        "watchlist_stocks": 10,
        "mf_analytics_access": False,
        "pms_tracker_access": False,
        "export_pdf": False,
        "api_access": False,
    },
    "pro": {
        "reports_total": None,
        "reports_monthly": 100,       # 100 reports per month
        "portfolios": 5,
        "portfolio_stocks": 50,
        "watchlists": 5,
        "watchlist_stocks": 25,
        "mf_analytics_access": True,
        "pms_tracker_access": True,
        "export_pdf": True,
        "api_access": False,
    },
    "enterprise": {
        "reports_total": None,
        "reports_monthly": 1000,      # 1000 reports per month
        "portfolios": -1,             # Unlimited
        "portfolio_stocks": -1,
        "watchlists": -1,
        "watchlist_stocks": -1,
        "mf_analytics_access": True,
        "pms_tracker_access": True,
        "export_pdf": True,
        "api_access": True,
    },
}

# Legacy constants for backward compatibility
MONTHLY_REPORT_LIMIT = TIER_LIMITS["free"]["reports_monthly"]
ANONYMOUS_REPORT_LIMIT = TIER_LIMITS["guest"]["reports_total"]


def get_tier_limits(tier: str) -> TierLimits:
    """Get limits for a subscription tier."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


def is_unlimited(limit: int) -> bool:
    """Check if a limit is unlimited (-1)."""
    return limit == -1
