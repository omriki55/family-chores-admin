import smtplib
import logging
import os
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1i33qr_r_xj_2LkHzg0Hxe5Dh4G_m4T21Xa4WNhQLkjg/edit"

def _score_color(score: int) -> str:
    if score >= 8:
        return "#d4edda"
    if score >= 5:
        return "#fff3cd"
    return "#ffffff"

def _build_html(jobs: list[dict], today: str) -> str:
    n = len(jobs)
    rows_html = ""
    for job in sorted(jobs, key=lambda j: j.get("Fit Score", 0), reverse=True):
        score = int(job.get("Fit Score", 0))
        bg = _score_color(score)
        rows_html += f"""
        <tr style="background:{bg}">
            <td style="padding:8px;border:1px solid #ddd;text-align:center"><strong>{score}</strong></td>
            <td style="padding:8px;border:1px solid #ddd">{job.get('Company','')}</td>
            <td style="padding:8px;border:1px solid #ddd">{job.get('Role Title','')}</td>
            <td style="padding:8px;border:1px solid #ddd">{job.get('Location','')}</td>
            <td style="padding:8px;border:1px solid #ddd"><a href="{job.get('Job URL','')}" target="_blank">View</a></td>
            <td style="padding:8px;border:1px solid #ddd">{job.get('Score Reason','')}</td>
        </tr>"""

    if n == 0:
        body = f"<p>No new matching jobs were found today ({today}).</p>"
    else:
        body = f"""
        <p>Good morning Omri,</p>
        <p>Here are today's <strong>{n}</strong> new job matches, sorted by fit score:</p>
        <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:14px">
            <thead>
                <tr style="background:#343a40;color:white">
                    <th style="padding:10px;border:1px solid #ddd">Score</th>
                    <th style="padding:10px;border:1px solid #ddd">Company</th>
                    <th style="padding:10px;border:1px solid #ddd">Role</th>
                    <th style="padding:10px;border:1px solid #ddd">Location</th>
                    <th style="padding:10px;border:1px solid #ddd">Link</th>
                    <th style="padding:10px;border:1px solid #ddd">Reason</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        <p style="color:#888;font-size:12px">
            🟢 Score 8+ = Strong match &nbsp;|&nbsp; 🟡 Score 5-7 = Partial match
        </p>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:900px;margin:auto">
        {body}
        <hr>
        <p>📊 <a href="{SHEET_URL}">Open full pipeline in Google Sheets</a></p>
    </body></html>"""

def send_daily_summary(jobs: list[dict], dry_run: bool = False) -> None:
    today = date.today().isoformat()
    n = len(jobs)
    subject = f"🎯 Job Search Daily — {today} — {n} new matches"
    html = _build_html(jobs, today)

    if dry_run:
        logger.info(f"[DRY RUN] Would send email: {subject}")
        return

    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    to_addr = os.environ["SUMMARY_EMAIL_TO"]

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = to_addr
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_addr, msg.as_string())
        logger.info(f"Daily summary email sent to {to_addr}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
