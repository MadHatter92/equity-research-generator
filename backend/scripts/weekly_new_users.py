#!/usr/bin/env python3
"""
Get new users from the last N days (default: 7 days).

Usage:
    python scripts/weekly_new_users.py              # Users from last 7 days
    python scripts/weekly_new_users.py --days 30    # Users from last 30 days
    python scripts/weekly_new_users.py --format csv # Export as CSV
    python scripts/weekly_new_users.py --send-email # Send report via email (requires config)
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import get_db_connection


def get_new_users(days: int = 7, google_only: bool = False) -> list[dict]:
    """Fetch users created in the last N days."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate cutoff date
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    query = """
        SELECT id, email, full_name, google_id, auth_provider, avatar_url, created_at, is_active
        FROM users
        WHERE created_at >= ? AND is_active = 1
    """

    if google_only:
        query += " AND google_id IS NOT NULL"

    query += " ORDER BY created_at DESC"

    cursor.execute(query, (cutoff,))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_usage_stats(user_id: int) -> dict:
    """Get usage stats for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total reports
    cursor.execute("SELECT COUNT(*) as count FROM reports WHERE user_id = ?", (user_id,))
    reports = cursor.fetchone()["count"]

    # Get current month usage
    month_year = datetime.now().strftime("%Y-%m")
    cursor.execute(
        "SELECT reports_generated FROM usage WHERE user_id = ? AND month_year = ?",
        (user_id, month_year)
    )
    row = cursor.fetchone()
    monthly_reports = row["reports_generated"] if row else 0

    conn.close()

    return {
        "total_reports": reports,
        "monthly_reports": monthly_reports
    }


def format_report(users: list[dict], days: int, include_stats: bool = True) -> str:
    """Format the weekly report."""
    lines = []

    # Header
    lines.append("=" * 70)
    lines.append(f"NEW USERS REPORT - Last {days} days")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    if not users:
        lines.append("No new users in this period.")
        return "\n".join(lines)

    # Summary
    google_users = sum(1 for u in users if u.get("google_id"))
    local_users = len(users) - google_users

    lines.append(f"Total New Users: {len(users)}")
    lines.append(f"  - Google OAuth: {google_users}")
    lines.append(f"  - Email/Password: {local_users}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("")

    # User list
    for i, user in enumerate(users, 1):
        lines.append(f"{i}. {user['email']}")
        lines.append(f"   Name: {user['full_name']}")
        lines.append(f"   Provider: {user.get('auth_provider', 'local')}")
        lines.append(f"   Joined: {user['created_at']}")

        if include_stats:
            stats = get_usage_stats(user["id"])
            lines.append(f"   Reports: {stats['total_reports']} total, {stats['monthly_reports']} this month")

        lines.append("")

    lines.append("-" * 70)
    lines.append(f"End of report. {len(users)} new users.")

    return "\n".join(lines)


def format_as_csv(users: list[dict]) -> str:
    """Format as CSV."""
    if not users:
        return "No users found"

    lines = ["id,email,full_name,auth_provider,created_at"]

    for user in users:
        lines.append(
            f"{user['id']},"
            f"\"{user['email']}\","
            f"\"{user.get('full_name', '')}\","
            f"{user.get('auth_provider', 'local')},"
            f"{user['created_at']}"
        )

    return "\n".join(lines)


def format_as_json(users: list[dict]) -> str:
    """Format as JSON."""
    return json.dumps({
        "generated_at": datetime.now().isoformat(),
        "total_users": len(users),
        "users": users
    }, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Get new users from the last N days")
    parser.add_argument("--days", "-d", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--google-only", "-g", action="store_true", help="Only Google OAuth users")
    parser.add_argument("--format", "-f", choices=["report", "csv", "json", "emails"], default="report", help="Output format")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--no-stats", action="store_true", help="Skip usage stats in report")

    args = parser.parse_args()

    # Fetch users
    users = get_new_users(days=args.days, google_only=args.google_only)

    # Format output
    if args.format == "emails":
        output = "\n".join(user["email"] for user in users if user.get("email"))
    elif args.format == "csv":
        output = format_as_csv(users)
    elif args.format == "json":
        output = format_as_json(users)
    else:
        output = format_report(users, args.days, include_stats=not args.no_stats)

    # Write output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report saved to {args.output}")
    else:
        print(output)

    # Return count for scripting
    return len(users)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
