#!/usr/bin/env python3
"""
Export users from the database.

Usage:
    python scripts/export_users.py                    # Export all users
    python scripts/export_users.py --google-only      # Export only Google OAuth users
    python scripts/export_users.py --format csv       # Export as CSV
    python scripts/export_users.py --output users.csv # Save to file
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import get_db_connection


def get_users(google_only: bool = False, active_only: bool = True) -> list[dict]:
    """Fetch users from database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, email, full_name, google_id, auth_provider, avatar_url, created_at, is_active FROM users"
    conditions = []

    if google_only:
        conditions.append("google_id IS NOT NULL")

    if active_only:
        conditions.append("is_active = 1")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def format_as_csv(users: list[dict]) -> str:
    """Format users as CSV string."""
    if not users:
        return "No users found"

    output = []
    fieldnames = ["id", "email", "full_name", "auth_provider", "created_at", "is_active"]

    # Header
    output.append(",".join(fieldnames))

    # Rows
    for user in users:
        row = [str(user.get(field, "")) for field in fieldnames]
        # Escape commas in fields
        row = [f'"{field}"' if "," in field else field for field in row]
        output.append(",".join(row))

    return "\n".join(output)


def format_as_json(users: list[dict]) -> str:
    """Format users as JSON string."""
    return json.dumps(users, indent=2, default=str)


def format_as_table(users: list[dict]) -> str:
    """Format users as readable table."""
    if not users:
        return "No users found"

    lines = []
    lines.append(f"{'ID':<6} {'Email':<40} {'Name':<25} {'Provider':<10} {'Created':<20}")
    lines.append("-" * 105)

    for user in users:
        lines.append(
            f"{user['id']:<6} "
            f"{(user['email'] or '')[:38]:<40} "
            f"{(user['full_name'] or '')[:23]:<25} "
            f"{(user['auth_provider'] or 'local'):<10} "
            f"{user['created_at'][:19]:<20}"
        )

    lines.append("-" * 105)
    lines.append(f"Total: {len(users)} users")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export users from the database")
    parser.add_argument("--google-only", "-g", action="store_true", help="Export only Google OAuth users")
    parser.add_argument("--include-inactive", action="store_true", help="Include inactive users")
    parser.add_argument("--format", "-f", choices=["table", "csv", "json"], default="table", help="Output format")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--emails-only", "-e", action="store_true", help="Output only email addresses (one per line)")

    args = parser.parse_args()

    # Fetch users
    users = get_users(
        google_only=args.google_only,
        active_only=not args.include_inactive
    )

    # Format output
    if args.emails_only:
        output = "\n".join(user["email"] for user in users if user.get("email"))
    elif args.format == "csv":
        output = format_as_csv(users)
    elif args.format == "json":
        output = format_as_json(users)
    else:
        output = format_as_table(users)

    # Write output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Exported {len(users)} users to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
