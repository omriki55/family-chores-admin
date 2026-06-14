"""
notify_high_scores.py — email alert for high-scoring jobs.

Run AFTER the main scan (called from job-scan.yml).
Reads new high-score jobs from Supabase and emails a digest via Resend.

Required env vars (add to GitHub Actions secrets):
  SUPABASE_URL               — same as pipeline
  SUPABASE_SERVICE_ROLE_KEY  — same as pipeline
  RESEND_API_KEY             — from resend.com (free tier: 3k emails/mo)
  ALERT_EMAIL                — destination address (e.g. omrigonen5050@gmail.com)

Optional:
  ALERT_THRESHOLD            — minimum fit_score to include (default: 8)
  ALERT_FROM                 — sender address (default: alerts@jobsearch.ai)
"""
import json
import os
import urllib.request
from datetime import date, timezone, datetime
from collections import defaultdict

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
RESEND_KEY = os.environ.get("RESEND_API_KEY", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "omrigonen5050@gmail.com")
ALERT_FROM = os.environ.get("ALERT_FROM", "onboarding@resend.dev")  # free-tier default
THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", "8"))


def _sb(method, path, body=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else None


def fetch_todays_high_scores():
    today = date.today().isoformat()
    rows = _sb(
        "GET",
        f"jobs"
        f"?scan_date=eq.{today}"
        f"&fit_score=gte.{THRESHOLD}"
        f"&select=user_id,company,title,location,url,fit_score,score_reason,ai_opener,meta"
        f"&order=fit_score.desc"
        f"&limit=30"
    ) or []
    return rows


def fetch_user_emails(user_ids):
    """Return {user_id: email} from Supabase auth admin API."""
    if not user_ids:
        return {}
    out = {}
    for uid in user_ids:
        try:
            url = f"{SUPABASE_URL}/auth/v1/admin/users/{uid}"
            headers = {
                "apikey": SERVICE_KEY,
                "Authorization": f"Bearer {SERVICE_KEY}",
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                u = json.loads(r.read())
                out[uid] = u.get("email", "")
        except Exception as e:
            print(f"  ⚠️  Could not fetch email for {uid[:8]}...: {e}")
    return out


def build_html(jobs, username=""):
    score_color = lambda s: "#16a34a" if s >= 9 else "#ca8a04" if s >= 8 else "#dc2626"
    rows = ""
    for j in jobs:
        meta = {}
        try:
            meta = json.loads(j.get("meta") or "{}")
        except Exception:
            pass
        gaps = meta.get("gaps", [])
        verdict = meta.get("verdict", j.get("score_reason", ""))
        comp = meta.get("comp_estimate", "")
        opener = j.get("ai_opener", "")
        score = j.get("fit_score", 0)
        rows += f"""
        <tr>
          <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;vertical-align:top">
            <div style="font-weight:700;font-size:15px;color:#111">{j['title']}</div>
            <div style="color:#4f6bed;font-weight:600;font-size:13px;margin-top:2px">{j['company']}</div>
            <div style="color:#6b7280;font-size:12px;margin-top:2px">📍 {j.get('location','')}</div>
            {f'<div style="color:#6b7280;font-size:12px">💰 {comp}</div>' if comp and comp != 'unknown' else ''}
            <div style="margin-top:8px;font-size:13px;color:#374151">{verdict}</div>
            {f'<div style="margin-top:6px;font-size:12px;color:#9ca3af;font-style:italic">"{opener}"</div>' if opener else ''}
            {f'<div style="margin-top:6px;font-size:12px;color:#ef4444">פערים: {", ".join(gaps)}</div>' if gaps else ''}
            <a href="{j['url']}" style="display:inline-block;margin-top:10px;padding:7px 14px;background:#4f6bed;color:#fff;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600">הגש מועמדות →</a>
          </td>
          <td style="padding:14px 16px;border-bottom:1px solid #e5e7eb;text-align:center;vertical-align:top;white-space:nowrap">
            <div style="font-size:28px;font-weight:800;color:{score_color(score)}">{score}/10</div>
          </td>
        </tr>"""

    greeting = f"שלום {username}," if username else "שלום,"
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"/></head>
<body style="font-family:system-ui,sans-serif;background:#f9fafb;margin:0;padding:20px">
  <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.1)">
    <div style="background:linear-gradient(135deg,#4f6bed,#7c3aed);padding:24px 28px;color:#fff">
      <div style="font-size:22px;font-weight:800">🎯 משרות מומלצות ממצאן AI</div>
      <div style="font-size:14px;opacity:.85;margin-top:4px">{greeting} נמצאו {len(jobs)} משרות עם ציון {THRESHOLD}+ היום</div>
    </div>
    <table style="width:100%;border-collapse:collapse">
      <tr style="background:#f3f4f6">
        <th style="padding:10px 16px;text-align:right;font-size:12px;color:#6b7280;font-weight:600">משרה</th>
        <th style="padding:10px 16px;font-size:12px;color:#6b7280;font-weight:600">ציון</th>
      </tr>
      {rows}
    </table>
    <div style="padding:20px 28px;text-align:center;border-top:1px solid #e5e7eb">
      <a href="https://omriki55.github.io/omrigonenjobfinder/app.html" 
         style="padding:12px 28px;background:#4f6bed;color:#fff;border-radius:12px;text-decoration:none;font-weight:700;font-size:15px">
        פתח את כל המשרות
      </a>
      <div style="margin-top:12px;font-size:12px;color:#9ca3af">JobSearch AI • סריקה אוטומטית</div>
    </div>
  </div>
</body>
</html>"""


def send_email(to_email, subject, html):
    if not RESEND_KEY:
        print(f"  ⚠️  RESEND_API_KEY not set — skipping email to {to_email}")
        return False
    body = json.dumps({
        "from": ALERT_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            print(f"  ✅ Email sent to {to_email} (id={resp.get('id','')})")
            return True
    except urllib.error.HTTPError as e:
        print(f"  ❌ Resend error {e.code}: {e.read().decode()[:200]}")
        return False


def main():
    today = date.today().isoformat()
    print(f"📧 Checking high-score jobs for {today} (threshold: {THRESHOLD}/10)...")

    jobs = fetch_todays_high_scores()
    if not jobs:
        print("  No high-score jobs today — nothing to send.")
        return

    # Group by user
    by_user = defaultdict(list)
    for j in jobs:
        by_user[j["user_id"]].append(j)

    print(f"  {len(jobs)} jobs across {len(by_user)} users")

    # Fetch emails via Supabase auth admin API (no profiles table required)
    user_emails = fetch_user_emails(list(by_user.keys()))

    sent = 0
    for uid, user_jobs in by_user.items():
        # Use auth email if found, else fall back to ALERT_EMAIL env var
        email = user_emails.get(uid) or ALERT_EMAIL
        username = ""

        if not email:
            print(f"  ⚠️  No email for user {uid[:8]}... — skipping")
            continue

        subject = f"🎯 {len(user_jobs)} משרות חדשות עם ציון {THRESHOLD}+ — {today}"
        html = build_html(user_jobs, username)
        if send_email(email, subject, html):
            sent += 1

    print(f"✅ Done — {sent}/{len(by_user)} users emailed")


if __name__ == "__main__":
    main()
