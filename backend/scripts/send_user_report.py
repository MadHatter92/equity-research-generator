#!/usr/bin/env python3
"""
Send user report via email. Designed to run as a Render Cron Job.

Usage:
    python scripts/send_user_report.py daily    # Daily new users report
    python scripts/send_user_report.py weekly   # Weekly new users report

Environment variables required:
    REPORT_EMAIL_TO      - Recipient email address
    RESEND_API_KEY       - Resend API key (or use SMTP vars below)

    # Alternative: SMTP
    SMTP_HOST            - SMTP server host
    SMTP_PORT            - SMTP server port (default: 587)
    SMTP_USER            - SMTP username
    SMTP_PASSWORD        - SMTP password
    SMTP_FROM            - From email address
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import get_db_connection


def get_new_users(days: int = 7) -> list[dict]:
    """Fetch users created in the last N days."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        SELECT id, email, full_name, google_id, auth_provider, created_at
        FROM users
        WHERE created_at >= ? AND is_active = 1
        ORDER BY created_at DESC
    """, (cutoff,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_usage_stats(user_id: int) -> dict:
    """Get usage stats for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM reports WHERE user_id = ?", (user_id,))
    reports = cursor.fetchone()["count"]

    conn.close()
    return {"total_reports": reports}


def get_total_stats() -> dict:
    """Get overall platform stats."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = 1")
    total_users = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE google_id IS NOT NULL AND is_active = 1")
    google_users = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM reports")
    total_reports = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM portfolios")
    total_portfolios = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM watchlists")
    total_watchlists = cursor.fetchone()["count"]

    conn.close()

    return {
        "total_users": total_users,
        "google_users": google_users,
        "total_reports": total_reports,
        "total_portfolios": total_portfolios,
        "total_watchlists": total_watchlists,
    }


def generate_report(period: str = "daily") -> tuple[str, str]:
    """Generate email subject and body."""
    days = 1 if period == "daily" else 7
    period_label = "Daily" if period == "daily" else "Weekly"

    users = get_new_users(days=days)
    stats = get_total_stats()

    # Subject
    subject = f"[Equity Research] {period_label} User Report - {len(users)} new users"

    # Body
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"EQUITY RESEARCH GENERATOR - {period_label.upper()} USER REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Period: Last {days} day{'s' if days > 1 else ''}")
    lines.append(f"{'='*60}")
    lines.append("")

    # Platform stats
    lines.append("PLATFORM OVERVIEW")
    lines.append("-" * 40)
    lines.append(f"Total Users:      {stats['total_users']}")
    lines.append(f"Google OAuth:     {stats['google_users']}")
    lines.append(f"Total Reports:    {stats['total_reports']}")
    lines.append(f"Total Portfolios: {stats['total_portfolios']}")
    lines.append(f"Total Watchlists: {stats['total_watchlists']}")
    lines.append("")

    # New users
    lines.append(f"NEW USERS ({len(users)})")
    lines.append("-" * 40)

    if not users:
        lines.append("No new users in this period.")
    else:
        google_count = sum(1 for u in users if u.get("google_id"))
        lines.append(f"Google OAuth: {google_count} | Email/Password: {len(users) - google_count}")
        lines.append("")

        for i, user in enumerate(users, 1):
            usage = get_usage_stats(user["id"])
            provider = "Google" if user.get("google_id") else "Email"
            lines.append(f"{i}. {user['email']}")
            lines.append(f"   Name: {user['full_name']} | Provider: {provider}")
            lines.append(f"   Joined: {user['created_at']} | Reports: {usage['total_reports']}")
            lines.append("")

    lines.append("-" * 40)
    lines.append("End of report.")
    lines.append("")
    lines.append("--")
    lines.append("Equity Research Generator")
    lines.append("https://equity-research-app.onrender.com")

    return subject, "\n".join(lines)


def send_via_resend(to_email: str, subject: str, body: str) -> bool:
    """Send email via Resend API."""
    import urllib.request
    import json

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("Error: RESEND_API_KEY not set")
        return False

    data = json.dumps({
        "from": "Equity Research <reports@resend.dev>",
        "to": [to_email],
        "subject": subject,
        "text": body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"Email sent successfully: {result.get('id')}")
            return True
    except urllib.error.HTTPError as e:
        print(f"Error sending email: {e.code} - {e.read().decode()}")
        return False


def send_via_smtp(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        print("Error: SMTP configuration incomplete")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python send_user_report.py [daily|weekly]")
        sys.exit(1)

    period = sys.argv[1].lower()
    if period not in ["daily", "weekly"]:
        print("Error: Period must be 'daily' or 'weekly'")
        sys.exit(1)

    to_email = os.environ.get("REPORT_EMAIL_TO")
    if not to_email:
        print("Error: REPORT_EMAIL_TO environment variable not set")
        sys.exit(1)

    print(f"Generating {period} report...")
    subject, body = generate_report(period)

    print(f"Sending to {to_email}...")

    # Try Resend first, fall back to SMTP
    if os.environ.get("RESEND_API_KEY"):
        success = send_via_resend(to_email, subject, body)
    elif os.environ.get("SMTP_HOST"):
        success = send_via_smtp(to_email, subject, body)
    else:
        print("Error: No email configuration found")
        print("Set RESEND_API_KEY or SMTP_* environment variables")
        print("\nReport preview:")
        print("-" * 40)
        print(body)
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
