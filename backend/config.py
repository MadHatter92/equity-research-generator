import os
from pathlib import Path

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

# Usage Limits
MONTHLY_REPORT_LIMIT = 20
ANONYMOUS_REPORT_LIMIT = 3

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
