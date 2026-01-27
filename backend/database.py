import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

from config import MONTHLY_REPORT_LIMIT, ANONYMOUS_REPORT_LIMIT, get_tier_limits, is_unlimited

# Ensure data directory exists
# On Render: use /opt/render/project/src/data if it exists, otherwise use local data folder
if os.path.exists("/opt/render/project/src"):
    # We're on Render
    DATA_DIR = Path("/opt/render/project/src/data")
else:
    # Local development
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "research.db"
print(f"Database path: {DB_PATH}")


# Pydantic Models
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str


class User(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: str
    is_active: bool = True


class ReportSummary(BaseModel):
    id: int
    company_name: str
    ticker: str
    recommendation: str
    target_price: float
    current_price: float
    created_at: str


class ReportDetail(ReportSummary):
    report_html: str


class UsageStats(BaseModel):
    reports_used: int
    reports_limit: int
    reports_remaining: int
    reset_date: str


class Portfolio(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


class PortfolioHolding(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    exchange: str = "NSE"
    quantity: Optional[float] = None
    buy_price: Optional[float] = None
    buy_date: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class Watchlist(BaseModel):
    id: int
    user_id: int
    name: str
    created_at: str


class WatchlistItem(BaseModel):
    id: int
    watchlist_id: int
    ticker: str
    exchange: str = "NSE"
    added_at: str


class UserLimits(BaseModel):
    reports_limit: Optional[int]
    reports_used: int
    reports_remaining: Optional[int]
    is_monthly: bool
    portfolios_limit: int
    portfolios_used: int
    portfolio_stocks_limit: int
    watchlists_limit: int
    watchlists_used: int
    watchlist_stocks_limit: int
    mf_analytics_access: bool
    pms_tracker_access: bool
    export_pdf: bool
    api_access: bool


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table (with OAuth support)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            full_name TEXT NOT NULL,
            google_id TEXT UNIQUE,
            auth_provider TEXT DEFAULT 'local',
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)

    # Migration: Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT UNIQUE")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
    except sqlite3.OperationalError:
        pass

    # Reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_name TEXT NOT NULL,
            ticker TEXT NOT NULL,
            exchange TEXT DEFAULT 'NSE',
            sector TEXT,
            current_price REAL,
            target_price REAL,
            recommendation TEXT,
            report_html TEXT NOT NULL,
            report_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Usage tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month_year TEXT NOT NULL,
            reports_generated INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, month_year)
        )
    """)

    # Anonymous usage tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anonymous_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT UNIQUE NOT NULL,
            reports_generated INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: Add subscription_tier column to users if it doesn't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Portfolios table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Portfolio holdings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            exchange TEXT DEFAULT 'NSE',
            quantity REAL,
            buy_price REAL,
            buy_date TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) ON DELETE CASCADE,
            UNIQUE(portfolio_id, ticker, exchange)
        )
    """)

    # Portfolio snapshots for performance tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER NOT NULL,
            snapshot_date TEXT NOT NULL,
            total_value REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) ON DELETE CASCADE,
            UNIQUE(portfolio_id, snapshot_date)
        )
    """)

    # Watchlists table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Watchlist items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watchlist_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            exchange TEXT DEFAULT 'NSE',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (watchlist_id) REFERENCES watchlists (id) ON DELETE CASCADE,
            UNIQUE(watchlist_id, ticker, exchange)
        )
    """)

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolios_user ON portfolios(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON portfolio_holdings(portfolio_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist ON watchlist_items(watchlist_id)")

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


# User Operations
def create_user(email: str, password_hash: str, full_name: str) -> Optional[int]:
    """Create a new user and return user ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
            (email, password_hash, full_name)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Email already exists
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_google_id(google_id: str) -> Optional[dict]:
    """Get user by Google ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_or_create_google_user(google_id: str, email: str, full_name: str, avatar_url: str = None) -> dict:
    """Get existing Google user or create a new one."""
    # First, try to find by google_id
    user = get_user_by_google_id(google_id)
    if user:
        return user

    # Check if email exists (user might have registered with email/password before)
    user = get_user_by_email(email)
    if user:
        # Link Google account to existing user
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET google_id = ?, auth_provider = 'google', avatar_url = ? WHERE id = ?",
            (google_id, avatar_url, user["id"])
        )
        conn.commit()
        conn.close()
        user["google_id"] = google_id
        user["auth_provider"] = "google"
        user["avatar_url"] = avatar_url
        return user

    # Create new Google user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO users (email, password_hash, full_name, google_id, auth_provider, avatar_url)
           VALUES (?, NULL, ?, ?, 'google', ?)""",
        (email, full_name, google_id, avatar_url)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "google_id": google_id,
        "auth_provider": "google",
        "avatar_url": avatar_url,
        "is_active": True
    }


# Report Operations
def save_report(
    user_id: int,
    company_name: str,
    ticker: str,
    exchange: str,
    sector: str,
    current_price: float,
    target_price: float,
    recommendation: str,
    report_html: str,
    report_data: str = None
) -> int:
    """Save a generated report and return report ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports
        (user_id, company_name, ticker, exchange, sector, current_price, target_price, recommendation, report_html, report_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, company_name, ticker, exchange, sector, current_price, target_price, recommendation, report_html, report_data))
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id


def get_user_reports(user_id: int, limit: int = 50) -> List[dict]:
    """Get user's report history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, company_name, ticker, recommendation, target_price, current_price, created_at
        FROM reports
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_report_by_id(report_id: int, user_id: int) -> Optional[dict]:
    """Get a specific report by ID (ensuring user ownership)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM reports
        WHERE id = ? AND user_id = ?
    """, (report_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_report(report_id: int, user_id: int) -> bool:
    """Delete a report (ensuring user ownership)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# Usage Operations
def get_current_month_year() -> str:
    """Get current month-year string."""
    return datetime.now().strftime("%Y-%m")


def get_usage(user_id: int) -> dict:
    """Get user's usage for current month."""
    month_year = get_current_month_year()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reports_generated FROM usage WHERE user_id = ? AND month_year = ?",
        (user_id, month_year)
    )
    row = cursor.fetchone()
    conn.close()

    reports_used = row["reports_generated"] if row else 0

    # Calculate reset date (1st of next month)
    now = datetime.now()
    if now.month == 12:
        reset_date = datetime(now.year + 1, 1, 1)
    else:
        reset_date = datetime(now.year, now.month + 1, 1)

    return {
        "reports_used": reports_used,
        "reports_limit": 20,
        "reports_remaining": max(0, 20 - reports_used),
        "reset_date": reset_date.strftime("%B %d, %Y")
    }


def increment_usage(user_id: int) -> bool:
    """Increment usage count for current month. Returns False if limit reached."""
    month_year = get_current_month_year()
    usage = get_usage(user_id)

    if usage["reports_remaining"] <= 0:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO usage (user_id, month_year, reports_generated)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, month_year)
        DO UPDATE SET reports_generated = reports_generated + 1
    """, (user_id, month_year))
    conn.commit()
    conn.close()
    return True


def can_generate_report(user_id: int) -> bool:
    """Check if user can generate more reports this month."""
    usage = get_usage(user_id)
    return usage["reports_remaining"] > 0


# Anonymous Usage Operations
def get_anonymous_usage(identifier: str) -> dict:
    """Get anonymous user's usage stats."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reports_generated FROM anonymous_usage WHERE identifier = ?",
        (identifier,)
    )
    row = cursor.fetchone()
    conn.close()

    reports_used = row["reports_generated"] if row else 0

    return {
        "reports_used": reports_used,
        "reports_limit": ANONYMOUS_REPORT_LIMIT,
        "reports_remaining": max(0, ANONYMOUS_REPORT_LIMIT - reports_used)
    }


def can_anonymous_generate(identifier: str) -> bool:
    """Check if anonymous user can generate more reports."""
    usage = get_anonymous_usage(identifier)
    return usage["reports_remaining"] > 0


def increment_anonymous_usage(identifier: str) -> bool:
    """Increment anonymous usage count. Returns False if limit reached."""
    if not can_anonymous_generate(identifier):
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO anonymous_usage (identifier, reports_generated, last_used_at)
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(identifier)
        DO UPDATE SET reports_generated = reports_generated + 1, last_used_at = CURRENT_TIMESTAMP
    """, (identifier,))
    conn.commit()
    conn.close()
    return True


# ============================================
# Portfolio Operations
# ============================================

def create_portfolio(user_id: int, name: str, description: str = None) -> Optional[dict]:
    """Create a new portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO portfolios (user_id, name, description) VALUES (?, ?, ?)",
            (user_id, name, description)
        )
        conn.commit()
        portfolio_id = cursor.lastrowid
        return get_portfolio_by_id(portfolio_id)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_portfolio_by_id(portfolio_id: int) -> Optional[dict]:
    """Get a portfolio by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_portfolios_by_user_id(user_id: int) -> List[dict]:
    """Get all portfolios for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM portfolios WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_portfolio_count(user_id: int) -> int:
    """Get the number of portfolios for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM portfolios WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0


def update_portfolio(portfolio_id: int, name: str = None, description: str = None) -> Optional[dict]:
    """Update a portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    values = []

    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if description is not None:
        updates.append("description = ?")
        values.append(description)

    if not updates:
        conn.close()
        return get_portfolio_by_id(portfolio_id)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(portfolio_id)

    cursor.execute(
        f"UPDATE portfolios SET {', '.join(updates)} WHERE id = ?",
        values
    )
    conn.commit()
    conn.close()
    return get_portfolio_by_id(portfolio_id)


def delete_portfolio(portfolio_id: int) -> bool:
    """Delete a portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def is_portfolio_owner(portfolio_id: int, user_id: int) -> bool:
    """Check if user owns the portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM portfolios WHERE id = ?", (portfolio_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row["user_id"] == user_id


# ============================================
# Portfolio Holdings Operations
# ============================================

def add_holding(
    portfolio_id: int,
    ticker: str,
    exchange: str = "NSE",
    quantity: float = None,
    buy_price: float = None,
    buy_date: str = None,
    notes: str = None
) -> Optional[dict]:
    """Add a holding to a portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO portfolio_holdings (portfolio_id, ticker, exchange, quantity, buy_price, buy_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (portfolio_id, ticker, exchange, quantity, buy_price, buy_date, notes))
        conn.commit()
        holding_id = cursor.lastrowid
        return get_holding_by_id(holding_id)
    except sqlite3.IntegrityError:
        return None  # Duplicate ticker in portfolio
    finally:
        conn.close()


def get_holding_by_id(holding_id: int) -> Optional[dict]:
    """Get a holding by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolio_holdings WHERE id = ?", (holding_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_holdings_by_portfolio_id(portfolio_id: int) -> List[dict]:
    """Get all holdings for a portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM portfolio_holdings WHERE portfolio_id = ? ORDER BY created_at DESC",
        (portfolio_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_holding_count(portfolio_id: int) -> int:
    """Get the number of holdings in a portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM portfolio_holdings WHERE portfolio_id = ?", (portfolio_id,))
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0


def update_holding(holding_id: int, quantity: float = None, buy_price: float = None, buy_date: str = None, notes: str = None) -> Optional[dict]:
    """Update a holding."""
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    values = []

    if quantity is not None:
        updates.append("quantity = ?")
        values.append(quantity)
    if buy_price is not None:
        updates.append("buy_price = ?")
        values.append(buy_price)
    if buy_date is not None:
        updates.append("buy_date = ?")
        values.append(buy_date)
    if notes is not None:
        updates.append("notes = ?")
        values.append(notes)

    if not updates:
        conn.close()
        return get_holding_by_id(holding_id)

    values.append(holding_id)
    cursor.execute(
        f"UPDATE portfolio_holdings SET {', '.join(updates)} WHERE id = ?",
        values
    )
    conn.commit()
    conn.close()
    return get_holding_by_id(holding_id)


def delete_holding(portfolio_id: int, ticker: str, exchange: str = "NSE") -> bool:
    """Delete a holding from a portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM portfolio_holdings WHERE portfolio_id = ? AND ticker = ? AND exchange = ?",
        (portfolio_id, ticker, exchange)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ============================================
# Watchlist Operations
# ============================================

def create_watchlist(user_id: int, name: str) -> Optional[dict]:
    """Create a new watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO watchlists (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        conn.commit()
        watchlist_id = cursor.lastrowid
        return get_watchlist_by_id(watchlist_id)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_watchlist_by_id(watchlist_id: int) -> Optional[dict]:
    """Get a watchlist by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM watchlists WHERE id = ?", (watchlist_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_watchlists_by_user_id(user_id: int) -> List[dict]:
    """Get all watchlists for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM watchlists WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_watchlist_count(user_id: int) -> int:
    """Get the number of watchlists for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM watchlists WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0


def delete_watchlist(watchlist_id: int) -> bool:
    """Delete a watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def is_watchlist_owner(watchlist_id: int, user_id: int) -> bool:
    """Check if user owns the watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM watchlists WHERE id = ?", (watchlist_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row["user_id"] == user_id


# ============================================
# Watchlist Items Operations
# ============================================

def add_watchlist_item(watchlist_id: int, ticker: str, exchange: str = "NSE") -> Optional[dict]:
    """Add a stock to a watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO watchlist_items (watchlist_id, ticker, exchange) VALUES (?, ?, ?)",
            (watchlist_id, ticker, exchange)
        )
        conn.commit()
        item_id = cursor.lastrowid
        return get_watchlist_item_by_id(item_id)
    except sqlite3.IntegrityError:
        return None  # Duplicate ticker in watchlist
    finally:
        conn.close()


def get_watchlist_item_by_id(item_id: int) -> Optional[dict]:
    """Get a watchlist item by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM watchlist_items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_watchlist_items_by_watchlist_id(watchlist_id: int) -> List[dict]:
    """Get all items in a watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM watchlist_items WHERE watchlist_id = ? ORDER BY added_at DESC",
        (watchlist_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_watchlist_item_count(watchlist_id: int) -> int:
    """Get the number of items in a watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM watchlist_items WHERE watchlist_id = ?", (watchlist_id,))
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0


def delete_watchlist_item(watchlist_id: int, ticker: str, exchange: str = "NSE") -> bool:
    """Delete an item from a watchlist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM watchlist_items WHERE watchlist_id = ? AND ticker = ? AND exchange = ?",
        (watchlist_id, ticker, exchange)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ============================================
# User Limits Operations
# ============================================

def get_user_limits(user: dict, identifier: str = None) -> dict:
    """Get user's limits based on their subscription tier."""
    if user is None:
        # Guest user
        limits = get_tier_limits("guest")
        reports_used = 0
        if identifier:
            usage = get_anonymous_usage(identifier)
            reports_used = usage["reports_used"]

        reports_limit = limits["reports_total"]
        reports_remaining = max(0, reports_limit - reports_used) if reports_limit else None

        return {
            "reports_limit": reports_limit,
            "reports_used": reports_used,
            "reports_remaining": reports_remaining,
            "is_monthly": False,
            "portfolios_limit": limits["portfolios"],
            "portfolios_used": 0,
            "portfolio_stocks_limit": limits["portfolio_stocks"],
            "watchlists_limit": limits["watchlists"],
            "watchlists_used": 0,
            "watchlist_stocks_limit": limits["watchlist_stocks"],
            "mf_analytics_access": limits["mf_analytics_access"],
            "pms_tracker_access": limits["pms_tracker_access"],
            "export_pdf": limits["export_pdf"],
            "api_access": limits["api_access"],
        }

    tier = user.get("subscription_tier", "free")
    limits = get_tier_limits(tier)

    usage = get_usage(user["id"])
    reports_used = usage["reports_used"]
    reports_limit = limits["reports_monthly"]

    if reports_limit and not is_unlimited(reports_limit):
        reports_remaining = max(0, reports_limit - reports_used)
    else:
        reports_remaining = None  # Unlimited

    portfolios_used = get_portfolio_count(user["id"])
    watchlists_used = get_watchlist_count(user["id"])

    return {
        "reports_limit": reports_limit,
        "reports_used": reports_used,
        "reports_remaining": reports_remaining,
        "is_monthly": True,
        "portfolios_limit": limits["portfolios"],
        "portfolios_used": portfolios_used,
        "portfolio_stocks_limit": limits["portfolio_stocks"],
        "watchlists_limit": limits["watchlists"],
        "watchlists_used": watchlists_used,
        "watchlist_stocks_limit": limits["watchlist_stocks"],
        "mf_analytics_access": limits["mf_analytics_access"],
        "pms_tracker_access": limits["pms_tracker_access"],
        "export_pdf": limits["export_pdf"],
        "api_access": limits["api_access"],
    }


# Initialize database on module import
init_database()
