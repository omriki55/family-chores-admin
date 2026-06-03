"""
Automated job search pipeline — runs via SessionStart hook.
Uses Anthropic API with web_search tool to find real job listings,
scores them, updates docs/index.html, commits and pushes to GitHub,
and sends a Gmail draft summary.
"""
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

# Resolve paths relative to this file, not cwd
HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
DOCS_HTML = REPO_ROOT / "docs" / "index.html"
SCORED_JSON = HERE / "scored_jobs.json"

load_dotenv(HERE / ".env")

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SEARCH_PROMPT = """Search for current job listings (posted in the last 30 days) matching these roles:
- Head of Revenue Operations
- RevOps Manager
- GTM Engineer
- Head of Growth
- Marketing Operations Lead
- Sales Operations Manager

Focus on: B2B SaaS companies, remote/global, Israel (Tel Aviv area), or hybrid.

For each job found, return a JSON array with objects containing:
{
  "company": "...",
  "title": "...",
  "location": "...",
  "url": "...",
  "job_type": "Full-time",
  "description": "... (50-100 words about the role and requirements)"
}

Return at minimum 6 and at most 15 real, currently open positions.
Return ONLY the JSON array, no other text."""

SCORING_PROMPT = """You are evaluating job listings for Omri Gonen, a senior RevOps/GTM executive with 15+ years in B2B SaaS.

CANDIDATE PROFILE:
- Target roles: Head of Revenue Operations, RevOps Manager, GTM Engineer, Head of Growth, Marketing Operations Lead
- Strong fit: HubSpot admin, Salesforce admin, B2B SaaS, Fintech, AI-native GTM, CAC/LTV, pipeline forecasting
- Weak fit: pure media buying, e-commerce D2C only, junior/IC roles, companies under 30 people
- Location OK: Remote/Hybrid globally, Tel Aviv area, Herzliya, Ra'anana, Petah Tikva, Bnei Brak, Holon, Bat Yam
- Location REJECT: Rehovot and south, Modiin, North of Ra'anana (Haifa etc.), non-remote international

JOB LISTING:
Company: {company}
Role: {title}
Location: {location}
Description: {description}

Respond in JSON ONLY:
{{
  "fit_score": <integer 1-10>,
  "score_reason": "<1-2 sentences>",
  "ai_opener": "<2-3 sentence personalized cold outreach opener specific to this company>",
  "location_ok": <true/false>
}}
If location_ok is false, set fit_score to 0."""


def search_jobs() -> list[dict]:
    """Use Anthropic web_search tool to find real job listings."""
    print("🔍 Searching for jobs via Anthropic web search...")
    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=4096,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
            messages=[{"role": "user", "content": SEARCH_PROMPT}],
        )
        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
        # Parse JSON from response
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.split("```")[0]
        jobs = json.loads(text.strip())
        print(f"  Found {len(jobs)} job listings")
        return jobs
    except Exception as e:
        print(f"  ⚠️  Web search failed: {e}")
        # Fall back to existing scored_jobs if available
        if SCORED_JSON.exists():
            print("  Using cached results from previous run")
            return json.load(open(SCORED_JSON))
        return []


def score_job(job: dict) -> dict:
    """Score a single job using Claude."""
    prompt = SCORING_PROMPT.format(
        company=job.get("company", ""),
        title=job.get("title", ""),
        location=job.get("location", ""),
        description=job.get("description", "")[:800],
    )
    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.split("```")[0]
            result = json.loads(text.strip())
            job["fit_score"] = int(result.get("fit_score", 0))
            job["score_reason"] = result.get("score_reason", "")
            job["ai_opener"] = result.get("ai_opener", "")
            job["location_ok"] = bool(result.get("location_ok", True))
            return job
        except Exception as e:
            if attempt == 0:
                time.sleep(3)
            else:
                job.update({"fit_score": 0, "score_reason": "Scoring failed", "ai_opener": "", "location_ok": False})
    return job


def score_jobs(jobs: list[dict]) -> list[dict]:
    scored = []
    for i, job in enumerate(jobs):
        print(f"  Scoring {i+1}/{len(jobs)}: {job.get('title')} @ {job.get('company')}")
        scored.append(score_job(job))
        if (i + 1) % 5 == 0:
            time.sleep(1)
    return scored


def build_html(jobs: list[dict], last_updated: str) -> str:
    jobs_json = json.dumps(jobs, ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>🎯 Job Tracker — Omri</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#0f1117;--card:#1e2130;--accent:#00c853;--text:#e0e0e0;--muted:#8a8fa8;--yellow:#ffd600;--red:#f44336;--border:#2a2d3e;--radius:12px}}
    body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;min-height:100vh;padding-bottom:40px}}
    header{{background:#131620;border-bottom:1px solid var(--border);padding:14px 16px 10px;position:sticky;top:0;z-index:100}}
    .header-top{{display:flex;align-items:center;justify-content:space-between;gap:8px}}
    header h1{{font-size:1.25rem;font-weight:700;color:var(--accent)}}
    .header-meta{{font-size:0.72rem;color:var(--muted);margin-top:2px}}
    .filter-bar{{display:flex;gap:8px;padding:12px 16px 0;flex-wrap:wrap}}
    .filter-btn{{background:var(--card);border:1px solid var(--border);color:var(--muted);border-radius:20px;padding:5px 14px;font-size:.8rem;cursor:pointer;transition:all .15s}}
    .filter-btn.active{{background:var(--accent);color:#000;border-color:var(--accent);font-weight:600}}
    .count-label{{font-size:.75rem;color:var(--muted);padding:8px 16px 0}}
    .jobs-container{{padding:12px 16px 0;display:flex;flex-direction:column;gap:10px}}
    .job-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:14px;display:flex;flex-direction:column;gap:8px}}
    .card-row1{{display:flex;align-items:flex-start;gap:12px}}
    .score-badge{{flex-shrink:0;width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:800}}
    .score-green{{background:rgba(0,200,83,.18);color:var(--accent);border:1.5px solid rgba(0,200,83,.35)}}
    .score-yellow{{background:rgba(255,214,0,.15);color:var(--yellow);border:1.5px solid rgba(255,214,0,.3)}}
    .score-red{{background:rgba(244,67,54,.15);color:var(--red);border:1.5px solid rgba(244,67,54,.3)}}
    .card-title-block{{flex:1;min-width:0}}
    .card-company{{font-weight:700;font-size:.95rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .card-role{{font-size:.82rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .card-tags{{display:flex;flex-wrap:wrap;gap:6px}}
    .tag{{background:#1a1d2e;border:1px solid var(--border);border-radius:6px;padding:2px 8px;font-size:.73rem;color:var(--muted)}}
    .card-reason{{font-size:.8rem;color:var(--muted);line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
    .card-actions{{display:flex;gap:8px;margin-top:2px}}
    .btn-view,.btn-copy{{flex:1;padding:9px 0;border-radius:8px;font-size:.82rem;font-weight:600;text-align:center;cursor:pointer;border:none;transition:opacity .15s}}
    .btn-view{{background:rgba(0,200,83,.12);color:var(--accent);border:1px solid rgba(0,200,83,.3);text-decoration:none;display:flex;align-items:center;justify-content:center;gap:4px}}
    .btn-copy{{background:rgba(138,143,168,.12);color:var(--muted);border:1px solid var(--border)}}
    .btn-copy.copied{{color:var(--accent);border-color:rgba(0,200,83,.4)}}
    #toast{{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(80px);background:#2a2d3e;color:var(--text);border:1px solid var(--border);border-radius:24px;padding:10px 20px;font-size:.85rem;z-index:999;transition:transform .3s ease;pointer-events:none}}
    #toast.show{{transform:translateX(-50%) translateY(0)}}
  </style>
</head>
<body>
<header>
  <div class="header-top">
    <div>
      <h1>🎯 Job Tracker</h1>
      <div class="header-meta">Last updated: {last_updated}</div>
    </div>
    <a href="https://docs.google.com/spreadsheets/d/1i33qr_r_xj_2LkHzg0Hxe5Dh4G_m4T21Xa4WNhQLkjg/edit" target="_blank" style="background:var(--card);border:1px solid var(--border);color:var(--muted);border-radius:8px;padding:8px 12px;font-size:.8rem;text-decoration:none">📊 Sheet</a>
  </div>
</header>
<div class="filter-bar">
  <button class="filter-btn active" onclick="setFilter(event,'all')">All</button>
  <button class="filter-btn" onclick="setFilter(event,'high')">🟢 8+</button>
  <button class="filter-btn" onclick="setFilter(event,'mid')">🟡 5–7</button>
</div>
<div class="count-label" id="count"></div>
<div class="jobs-container" id="container"></div>
<div id="toast"></div>
<script>
const JOBS={jobs_json};
let currentFilter="all";
function badgeClass(s){{return s>=8?"score-green":s>=5?"score-yellow":"score-red";}}
function filterVal(s){{return s>=8?"high":s>=5?"mid":"low";}}
function render(){{
  const sorted=[...JOBS].sort((a,b)=>b.fit_score-a.fit_score);
  let v=0;
  document.getElementById("container").innerHTML=sorted.map(j=>{{
    const fv=filterVal(j.fit_score);
    const show=currentFilter==="all"||fv===currentFilter;
    if(show)v++;
    return `<div class="job-card" data-filter="${{fv}}" style="display:${{show?"":"none"}}">
      <div class="card-row1">
        <div class="score-badge ${{badgeClass(j.fit_score)}}">${{j.fit_score}}</div>
        <div class="card-title-block">
          <div class="card-company">${{j.company}}</div>
          <div class="card-role">${{j.title}}</div>
        </div>
      </div>
      <div class="card-tags">
        ${{j.location?`<span class="tag">📍 ${{j.location}}</span>`:""}}
        ${{j.job_type?`<span class="tag">${{j.job_type}}</span>`:""}}
      </div>
      ${{j.score_reason?`<div class="card-reason">${{j.score_reason}}</div>`:""}}
      <div class="card-actions">
        <a href="${{j.url}}" target="_blank" rel="noopener" class="btn-view">View Job ↗</a>
        <button class="btn-copy" onclick="copyOpener(this,${{JSON.stringify(j.ai_opener||'')}})">Copy Opener 📋</button>
      </div>
    </div>`;
  }}).join("");
  document.getElementById("count").textContent=v+" job"+(v!==1?"s":"");
}}
function setFilter(e,f){{
  currentFilter=f;
  document.querySelectorAll(".filter-btn").forEach(b=>b.classList.remove("active"));
  e.target.classList.add("active");
  let v=0;
  document.querySelectorAll(".job-card").forEach(c=>{{
    const show=f==="all"||c.dataset.filter===f;
    c.style.display=show?"":"none";
    if(show)v++;
  }});
  document.getElementById("count").textContent=v+" job"+(v!==1?"s":"");
}}
function showToast(msg){{const t=document.getElementById("toast");t.textContent=msg;t.classList.add("show");setTimeout(()=>t.classList.remove("show"),2500);}}
function copyOpener(btn,text){{
  if(!text){{showToast("No opener");return;}}
  navigator.clipboard.writeText(text).then(()=>{{
    btn.textContent="Copied! ✓";btn.classList.add("copied");showToast("Opener copied!");
    setTimeout(()=>{{btn.textContent="Copy Opener 📋";btn.classList.remove("copied");}},2000);
  }}).catch(()=>showToast("Copy failed"));
}}
render();
</script>
</body>
</html>'''


def update_github_pages(jobs: list[dict], last_updated: str):
    """Write updated HTML to docs/index.html and push to GitHub."""
    good_jobs = [j for j in jobs if j.get("location_ok") and j.get("fit_score", 0) >= 4]
    html = build_html(good_jobs, last_updated)
    DOCS_HTML.write_text(html, encoding="utf-8")
    print(f"  Updated docs/index.html ({len(good_jobs)} jobs)")

    try:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "add", "docs/index.html"],
            check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "commit", "-m",
             f"Update job tracker — {last_updated}"],
            check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "push"],
            check=True, capture_output=True
        )
        print("  ✅ Pushed to GitHub")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        if "nothing to commit" in stderr or "nothing added" in stderr:
            print("  ℹ️  No changes to push")
        else:
            print(f"  ⚠️  Git push failed: {stderr[:200]}")


def send_gmail_draft(jobs: list[dict], today: str, n: int):
    """Send daily summary via Gmail SMTP if credentials are set."""
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_password:
        print("  ℹ️  No Gmail credentials — skipping email")
        return

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    rows = ""
    for j in sorted(jobs, key=lambda x: x.get("fit_score", 0), reverse=True):
        s = j.get("fit_score", 0)
        bg = "#d4edda" if s >= 8 else "#fff3cd" if s >= 5 else "#fff"
        rows += f'<tr style="background:{bg}"><td style="padding:8px;border:1px solid #ddd;text-align:center"><b>{s}</b></td><td style="padding:8px;border:1px solid #ddd">{j.get("company","")}</td><td style="padding:8px;border:1px solid #ddd">{j.get("title","")}</td><td style="padding:8px;border:1px solid #ddd">{j.get("location","")}</td><td style="padding:8px;border:1px solid #ddd"><a href="{j.get("url","")}">View</a></td><td style="padding:8px;border:1px solid #ddd">{j.get("score_reason","")}</td></tr>'

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:900px;margin:auto">
<p>Good morning Omri,</p>
<p>Here are today's <b>{n}</b> new job matches:</p>
<table style="border-collapse:collapse;width:100%;font-size:14px">
<thead><tr style="background:#343a40;color:white">
<th style="padding:10px;border:1px solid #ddd">Score</th><th style="padding:10px;border:1px solid #ddd">Company</th>
<th style="padding:10px;border:1px solid #ddd">Role</th><th style="padding:10px;border:1px solid #ddd">Location</th>
<th style="padding:10px;border:1px solid #ddd">Link</th><th style="padding:10px;border:1px solid #ddd">Reason</th>
</tr></thead><tbody>{rows}</tbody></table>
<hr><p>📊 <a href="https://docs.google.com/spreadsheets/d/1i33qr_r_xj_2LkHzg0Hxe5Dh4G_m4T21Xa4WNhQLkjg/edit">Open Pipeline Sheet</a></p>
</body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 Job Search Daily — {today} — {n} new matches"
        msg["From"] = gmail_user
        msg["To"] = os.environ.get("SUMMARY_EMAIL_TO", gmail_user)
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.ehlo(); s.starttls(); s.login(gmail_user, gmail_password)
            s.sendmail(gmail_user, msg["To"], msg.as_string())
        print(f"  ✅ Email sent to {msg['To']}")
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")


def main():
    today = date.today().isoformat()
    last_updated = date.today().strftime("%b %d, %Y")
    print(f"\n{'='*60}")
    print(f"🎯 Job Search Pipeline — {today}")
    print(f"{'='*60}")

    # 1. Search
    jobs = search_jobs()
    if not jobs:
        print("No jobs found. Exiting.")
        sys.exit(0)

    # 2. Score
    print(f"\n📊 Scoring {len(jobs)} jobs...")
    scored = score_jobs(jobs)

    # 3. Filter
    good = [j for j in scored if j.get("location_ok") and j.get("fit_score", 0) >= 4]
    print(f"\n✅ {len(good)}/{len(scored)} jobs passed filter (score ≥ 4, location OK)")
    for j in sorted(good, key=lambda x: x.get("fit_score", 0), reverse=True):
        print(f"   [{j['fit_score']}/10] {j['title']} @ {j['company']} ({j['location']})")

    # 4. Save JSON
    SCORED_JSON.write_text(json.dumps(good, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5. Update GitHub Pages
    print("\n🌐 Updating GitHub Pages...")
    update_github_pages(good, last_updated)

    # 6. Email
    print("\n📧 Sending email summary...")
    send_gmail_draft(good, today, len(good))

    print(f"\n{'='*60}")
    print(f"Done. {len(good)} jobs in tracker.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
