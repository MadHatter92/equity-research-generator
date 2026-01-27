# Admin Scripts Guide

Scripts for user management, reporting, and data export.

---

## Quick Reference

| Task | Command |
|------|---------|
| Get all user emails | `python scripts/export_users.py --google-only --emails-only` |
| New users this week | `python scripts/weekly_new_users.py --days 7` |
| Export to CSV | `python scripts/export_users.py --format csv --output users.csv` |
| Send manual report | `python scripts/send_user_report.py daily` |

---

## 1. Export All Users (`export_users.py`)

Exports user data from the database with various filtering and format options.

### Basic Usage

```bash
cd F:\Dev\ClaudeProjects\equity-research-generator\backend

# View all users in a table
python scripts/export_users.py

# Google OAuth users only (recommended - these have verified emails)
python scripts/export_users.py --google-only
```

### Get Just Email Addresses

```bash
# All user emails (one per line)
python scripts/export_users.py --emails-only

# Only Google OAuth user emails
python scripts/export_users.py --google-only --emails-only

# Save to file
python scripts/export_users.py --google-only --emails-only --output user_emails.txt
```

### Export to Different Formats

```bash
# CSV (for Excel/Google Sheets)
python scripts/export_users.py --format csv --output users.csv

# JSON (for programmatic use)
python scripts/export_users.py --format json --output users.json

# Table (human-readable, default)
python scripts/export_users.py --format table
```

### All Options

| Option | Short | Description |
|--------|-------|-------------|
| `--google-only` | `-g` | Only Google OAuth users |
| `--include-inactive` | | Include deactivated users |
| `--format` | `-f` | Output format: `table`, `csv`, `json` |
| `--output` | `-o` | Save to file instead of printing |
| `--emails-only` | `-e` | Output only email addresses |

### Example Output (Table)

```
ID     Email                                    Name                      Provider   Created
---------------------------------------------------------------------------------------------------------
15     john.doe@gmail.com                       John Doe                  google     2026-01-25 14:30:22
14     jane.smith@gmail.com                     Jane Smith                google     2026-01-24 09:15:43
---------------------------------------------------------------------------------------------------------
Total: 2 users
```

---

## 2. New Users Report (`weekly_new_users.py`)

Get users who signed up within a specific time period.

### Basic Usage

```bash
# New users from last 7 days (default)
python scripts/weekly_new_users.py

# New users from last 30 days
python scripts/weekly_new_users.py --days 30

# New users from yesterday only
python scripts/weekly_new_users.py --days 1
```

### Output Formats

```bash
# Detailed report (default)
python scripts/weekly_new_users.py --days 7

# Just email addresses
python scripts/weekly_new_users.py --days 7 --format emails

# CSV export
python scripts/weekly_new_users.py --days 7 --format csv --output new_users.csv

# JSON export
python scripts/weekly_new_users.py --days 30 --format json --output new_users.json
```

### All Options

| Option | Short | Description |
|--------|-------|-------------|
| `--days` | `-d` | Number of days to look back (default: 7) |
| `--google-only` | `-g` | Only Google OAuth users |
| `--format` | `-f` | Output format: `report`, `csv`, `json`, `emails` |
| `--output` | `-o` | Save to file instead of printing |
| `--no-stats` | | Skip usage statistics in report |

### Example Output (Report)

```
======================================================================
NEW USERS REPORT - Last 7 days
Generated: 2026-01-27 10:30:45
======================================================================

Total New Users: 5
  - Google OAuth: 4
  - Email/Password: 1

----------------------------------------------------------------------

1. john.doe@gmail.com
   Name: John Doe
   Provider: google
   Joined: 2026-01-25 14:30:22
   Reports: 3 total, 3 this month

2. jane.smith@gmail.com
   Name: Jane Smith
   Provider: google
   Joined: 2026-01-24 09:15:43
   Reports: 1 total, 1 this month

----------------------------------------------------------------------
End of report. 5 new users.
```

---

## 3. Send User Report (`send_user_report.py`)

Manually trigger the daily/weekly email reports (same as the Render cron jobs).

### Prerequisites

Set environment variables:
```bash
# Required
set RESEND_API_KEY=re_your_api_key_here
set REPORT_EMAIL_TO=mail@mayaskara.com

# OR use SMTP instead
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USER=your@gmail.com
set SMTP_PASSWORD=your_app_password
```

### Usage

```bash
# Send daily report (new users from last 24 hours)
python scripts/send_user_report.py daily

# Send weekly report (new users from last 7 days)
python scripts/send_user_report.py weekly
```

### What the Report Contains

1. **Platform Overview**
   - Total users
   - Google OAuth users count
   - Total reports generated
   - Total portfolios
   - Total watchlists

2. **New Users List**
   - Email address
   - Full name
   - Auth provider (Google/Email)
   - Join date
   - Number of reports generated

---

## Running on Production (Render)

The scripts above work on your **local database**. To get **production data**, you have these options:

### Option A: Download Production Database

1. Go to Render Dashboard → `equity-research-api` service
2. Go to "Disks" → Download the SQLite file from `/opt/render/project/src/data/`
3. Place it locally and run scripts against it

### Option B: Run via Render Shell

1. Go to Render Dashboard → `equity-research-api` service
2. Click "Shell" to open a terminal
3. Run:
   ```bash
   cd /opt/render/project/src/backend
   python scripts/export_users.py --google-only --emails-only
   ```

### Option C: Trigger Cron Job Manually

1. Go to Render Dashboard → `daily-user-report` or `weekly-user-report`
2. Click "Trigger Run" to send a report immediately

---

## Common Use Cases

### Marketing: Get all verified emails for newsletter

```bash
python scripts/export_users.py --google-only --emails-only --output marketing_list.txt
```

### Analytics: Weekly growth tracking

```bash
python scripts/weekly_new_users.py --days 7 --format csv --output weekly_growth.csv
```

### Support: Find a specific user

```bash
python scripts/export_users.py --format json | findstr "john@example.com"
```

### Investor Update: Total user count

```bash
python scripts/export_users.py --google-only --format json
# Look at the total count at the bottom
```

---

## Troubleshooting

### "No module named 'database'"

Make sure you're running from the `backend` directory:
```bash
cd F:\Dev\ClaudeProjects\equity-research-generator\backend
python scripts/export_users.py
```

### "No users found"

- Check if the database file exists at `data/app.db`
- Verify users have been created (check via the app)

### Email not sending

- Verify `RESEND_API_KEY` is set correctly
- Check Resend dashboard for delivery logs
- Try the SMTP fallback if Resend isn't working

---

## File Locations

| File | Purpose |
|------|---------|
| `scripts/export_users.py` | Export all users |
| `scripts/weekly_new_users.py` | Export new users by time period |
| `scripts/send_user_report.py` | Send email reports |
| `data/app.db` | SQLite database (local) |
| `/opt/render/project/src/data/app.db` | SQLite database (production on Render) |
