import json
import logging
import os
from datetime import date
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_COLUMNS, SHEET_NAME

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_PATH = Path("credentials/google_service_account.json")

_sheet = None

def _get_sheet():
    global _sheet
    if _sheet is None:
        creds = Credentials.from_service_account_file(str(CREDENTIALS_PATH), scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(os.environ["GOOGLE_SHEETS_ID"])
        _sheet = spreadsheet.worksheet(SHEET_NAME)
    return _sheet

def get_existing_urls() -> set[str]:
    try:
        sheet = _get_sheet()
        records = sheet.get_all_records()
        url_col = "Job URL"
        return {row[url_col] for row in records if row.get(url_col)}
    except Exception as e:
        logger.error(f"Failed to fetch existing URLs: {e}")
        return set()

def get_existing_rows() -> list[dict]:
    try:
        sheet = _get_sheet()
        return sheet.get_all_records()
    except Exception as e:
        logger.error(f"Failed to fetch existing rows: {e}")
        return []

def append_jobs(jobs: list[dict], dry_run: bool = False) -> None:
    if not jobs:
        logger.info("No jobs to append")
        return
    if dry_run:
        logger.info(f"[DRY RUN] Would append {len(jobs)} jobs to sheet")
        return
    rows = []
    today = date.today().isoformat()
    for job in jobs:
        rows.append([
            job.get("company", ""),
            job.get("location", ""),
            job.get("title", ""),
            job.get("url", ""),
            job.get("job_type", "Full-time"),
            "",  # Contact Name
            "",  # Contact LinkedIn
            job.get("fit_score", 0),
            job.get("score_reason", ""),
            "לפנות",
            job.get("ai_opener", ""),
            today,
        ])
    try:
        sheet = _get_sheet()
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info(f"Appended {len(rows)} rows to sheet")
    except Exception as e:
        logger.error(f"Failed to write to sheet: {e}")
        backup_path = f"failed_jobs_{today}.json"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved backup to {backup_path}")

def get_todays_jobs() -> list[dict]:
    try:
        sheet = _get_sheet()
        records = sheet.get_all_records()
        today = date.today().isoformat()
        return [r for r in records if r.get("Date Added") == today]
    except Exception as e:
        logger.error(f"Failed to get today's jobs: {e}")
        return []
