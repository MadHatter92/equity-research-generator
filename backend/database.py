import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

# Ensure data directory exists - Use Render's persistent disk if available
DATA_DIR = Path(os.getenv("RENDER_DISK_PATH", str(Path(__file__).resolve().parent.parent / "data")))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "research.db"


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


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)

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


# Initialize database on module import
init_database()
