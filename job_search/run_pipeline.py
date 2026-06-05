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

from ats_scraper import scrape_ats

# Resolve paths relative to this file, not cwd
HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
DOCS_HTML = REPO_ROOT / "docs" / "index.html"
SCORED_JSON = HERE / "scored_jobs.json"
CONTACTS_JSON = HERE / "contacts.json"
FEEDBACK_JSON = HERE / "feedback.json"
CONFIG_JSON = HERE / "config.json"


def attach_contacts(jobs: list[dict]) -> list[dict]:
    """Merge known Clay-enriched contacts onto jobs by company name."""
    try:
        contacts = json.loads(CONTACTS_JSON.read_text(encoding="utf-8"))
    except Exception:
        contacts = {}
    for j in jobs:
        if not j.get("contact"):
            j["contact"] = contacts.get(j.get("company", ""))
    return jobs


def load_feedback() -> dict:
    """Load feedback.json, creating it if missing."""
    if not FEEDBACK_JSON.exists():
        FEEDBACK_JSON.write_text("{}", encoding="utf-8")
    try:
        return json.loads(FEEDBACK_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_feedback(data: dict):
    """Write feedback.json."""
    FEEDBACK_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config() -> dict:
    """Load config.json for custom roles etc., creating defaults if missing."""
    defaults = {
        "roles": [
            "Head of Revenue Operations",
            "RevOps Manager",
            "GTM Engineer",
            "Head of Growth",
            "Marketing Operations Lead",
            "Sales Operations Manager",
        ],
        "updated": date.today().isoformat(),
    }
    if not CONFIG_JSON.exists():
        CONFIG_JSON.write_text(json.dumps(defaults, ensure_ascii=False, indent=2), encoding="utf-8")
        return defaults
    try:
        return json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    except Exception:
        return defaults


load_dotenv(HERE / ".env")

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_BASE_SEARCH_PROMPT = """Search LinkedIn Jobs and other job boards for CURRENTLY OPEN positions (posted in the last 30 days) matching these roles:
{roles}

Search strategy — run these queries:
1. site:linkedin.com/jobs for each role above
2. site:greenhouse.io OR site:lever.co OR site:ashbyhq.com for each role
3. Direct company career pages for B2B SaaS companies in Israel / remote

Focus on: B2B SaaS companies, remote/global, Israel (Tel Aviv area), or hybrid.

CRITICAL RULES:
- Each URL must be a DIRECT link to a SPECIFIC job posting — NOT a search results page
- URLs like indeed.com/jobs?q=... or linkedin.com/jobs/search?... are FORBIDDEN
- Only include jobs where you found the actual job posting page
- If you cannot find a direct URL for a job, skip it entirely

For each job found, return a JSON array with objects containing:
{{
  "company": "...",
  "title": "...",
  "location": "...",
  "url": "DIRECT link to this specific job posting",
  "job_type": "Full-time",
  "posted": "YYYY-MM-DD",
  "description": "... (50-100 words about the role and requirements)"
}}

Return at minimum 8 and at most 15 real, currently open positions with direct URLs.
Return ONLY the JSON array, no other text."""

_BASE_SCORING_PROMPT = """You are evaluating job listings for Omri Gonen, a senior RevOps/GTM executive with 15+ years in B2B SaaS.

CANDIDATE PROFILE:
- Target roles: Head of Revenue Operations, RevOps Manager, GTM Engineer, Head of Growth, Marketing Operations Lead
- Strong fit: HubSpot admin, Salesforce admin, B2B SaaS, Fintech, AI-native GTM, CAC/LTV, pipeline forecasting
- Weak fit: pure media buying, e-commerce D2C only, junior/IC roles, companies under 30 people
- Location OK: Remote/Hybrid globally, Tel Aviv area, Herzliya, Ra'anana, Petah Tikva, Bnei Brak, Holon, Bat Yam
- Location REJECT: Rehovot and south, Modiin, North of Ra'anana (Haifa etc.), non-remote international
{avoid_section}{feedback_section}
JOB LISTING:
Company: {{company}}
Role: {{title}}
Location: {{location}}
Description: {{description}}

Respond in JSON ONLY:
{{{{
  "fit_score": <integer 1-10>,
  "score_reason": "<1-2 sentences>",
  "ai_opener": "<2-3 sentence personalized cold outreach opener specific to this company>",
  "location_ok": <true/false>
}}}}
If location_ok is false, set fit_score to 0."""


def build_prompts() -> tuple[str, str]:
    """Build SEARCH_PROMPT and SCORING_PROMPT incorporating config.json and feedback.json."""
    cfg = load_config()
    roles = cfg.get("roles", [])
    roles_str = "\n".join(f"- {r}" for r in roles)
    search_prompt = _BASE_SEARCH_PROMPT.format(roles=roles_str)

    feedback = load_feedback()
    avoid = feedback.get("avoid_companies", [])
    avoid_section = f"\nCompanies previously marked irrelevant by user (score 0): {avoid}\n" if avoid else ""
    # Per-job user feedback notes incorporated as general pattern hints
    job_feedbacks = feedback.get("job_feedback", {})
    if job_feedbacks:
        hints = "\n".join(f"  - {v}" for v in list(job_feedbacks.values())[:10] if v)
        feedback_section = f"\nUser scoring feedback on past jobs (learn from these patterns):\n{hints}\n" if hints else ""
    else:
        feedback_section = ""
    scoring_prompt = _BASE_SCORING_PROMPT.format(avoid_section=avoid_section, feedback_section=feedback_section)
    return search_prompt, scoring_prompt


def search_jobs() -> list[dict]:
    """Use Anthropic web_search tool to find real job listings."""
    print("🔍 Searching for jobs via Anthropic web search...")
    search_prompt, _ = build_prompts()
    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=8192,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
            messages=[{"role": "user", "content": search_prompt}],
        )
        # Extract text from response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
        # Parse JSON from response — find first [...] array in text
        text = text.strip()
        import re
        # Try code fence first
        fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        else:
            # Find outermost JSON array
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]
            elif start != -1:
                # Truncated response — close the array manually
                text = text[start:].rstrip().rstrip(",") + "]"
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


def score_job(job: dict, scoring_prompt: str) -> dict:
    """Score a single job using Claude."""
    prompt = scoring_prompt.format(
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
            job["scan_date"] = date.today().isoformat()
            return job
        except Exception as e:
            if attempt == 0:
                time.sleep(3)
            else:
                job.update({"fit_score": 0, "score_reason": "Scoring failed", "ai_opener": "", "location_ok": False, "scan_date": date.today().isoformat()})
    return job


def score_jobs(jobs: list[dict]) -> list[dict]:
    _, scoring_prompt = build_prompts()
    scored = []
    for i, job in enumerate(jobs):
        print(f"  Scoring {i+1}/{len(jobs)}: {job.get('title')} @ {job.get('company')}")
        scored.append(score_job(job, scoring_prompt))
        if (i + 1) % 5 == 0:
            time.sleep(1)
    return scored


def update_feedback_after_scoring(scored: list[dict]):
    """Write low-score companies back to feedback.json."""
    feedback = load_feedback()
    low = feedback.get("low_score_companies", [])
    for j in scored:
        if j.get("fit_score", 0) == 0:
            company = j.get("company", "")
            if company and company not in low:
                low.append(company)
    feedback["low_score_companies"] = low
    save_feedback(feedback)


TEMPLATE = HERE / "tracker_template.html"


def build_html(jobs: list[dict], last_updated: str) -> str:
    """Render docs/index.html from the tracker template (single source of truth)."""
    template = TEMPLATE.read_text(encoding="utf-8")
    jobs_json = json.dumps(jobs, ensure_ascii=False)
    return template.replace("__JOBS_JSON__", jobs_json).replace("__LAST_UPDATED__", last_updated)


def update_github_pages(jobs: list[dict], last_updated: str):
    """Write updated HTML to docs/index.html and push to GitHub.

    `jobs` is the FULL combined list (pipeline + manual). Manual jobs
    (those with initial_status) are always kept; pipeline jobs must pass
    the location_ok + fit_score >= 4 filter.
    """
    good_jobs = attach_contacts([
        j for j in jobs
        if j.get("initial_status") or (j.get("location_ok") and j.get("fit_score", 0) >= 4)
    ])
    html = build_html(good_jobs, last_updated)
    DOCS_HTML.write_text(html, encoding="utf-8")
    print(f"  Updated docs/index.html ({len(good_jobs)} jobs)")

    try:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "add", "docs/index.html", "job_search/scored_jobs.json",
             "job_search/feedback.json"],
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

    # 1. Search — web_search (Opus) + public ATS APIs (Greenhouse/Lever/Ashby)
    jobs = search_jobs()
    cfg = load_config()
    ats_jobs = []
    if cfg.get("ats"):
        print("\n🏢 Scraping public ATS boards (Greenhouse/Lever/Ashby)...")
        ats_jobs = scrape_ats(cfg["ats"], cfg.get("ats_keywords"))
        print(f"  Found {len(ats_jobs)} role-relevant jobs from ATS boards")
    # Merge, deduplicating by direct URL then by company+title
    seen_urls = {j.get("url") for j in jobs if j.get("url")}
    seen_keys = {(j.get("company", "").lower(), j.get("title", "").lower()) for j in jobs}
    for j in ats_jobs:
        key = (j.get("company", "").lower(), j.get("title", "").lower())
        if j.get("url") in seen_urls or key in seen_keys:
            continue
        seen_urls.add(j.get("url"))
        seen_keys.add(key)
        jobs.append(j)
    if not jobs:
        print("No jobs found. Exiting.")
        sys.exit(0)

    # 2. Score
    print(f"\n📊 Scoring {len(jobs)} jobs...")
    scored = score_jobs(jobs)

    # 3. Update feedback with low-score companies
    update_feedback_after_scoring(scored)

    # 4. Filter
    good = [j for j in scored if j.get("location_ok") and j.get("fit_score", 0) >= 4]
    print(f"\n✅ {len(good)}/{len(scored)} jobs passed filter (score ≥ 4, location OK)")
    for j in sorted(good, key=lambda x: x.get("fit_score", 0), reverse=True):
        print(f"   [{j['fit_score']}/10] {j['title']} @ {j['company']} ({j['location']})")

    # 5. Save JSON — preserve manually-added jobs (those with initial_status)
    existing = []
    if SCORED_JSON.exists():
        try:
            existing = json.loads(SCORED_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    manual = [j for j in existing if j.get("initial_status")]
    # Fallback: if this scan found no good pipeline jobs (e.g. web search
    # returned nothing), keep the previous run's pipeline jobs instead of
    # wiping them out.
    if not good:
        good = [j for j in existing if not j.get("initial_status")]
        print(f"  ⚠️  No new pipeline jobs — keeping {len(good)} from previous run")
    # Deduplicate: drop pipeline jobs whose company+title match a manual entry
    manual_keys = {(j["company"].lower(), j["title"].lower()) for j in manual}
    pipeline_jobs = [j for j in good if (j["company"].lower(), j["title"].lower()) not in manual_keys]
    combined = pipeline_jobs + manual
    SCORED_JSON.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 Saved {len(pipeline_jobs)} pipeline + {len(manual)} manual jobs = {len(combined)} total")

    # 6. Update GitHub Pages — pass the FULL combined list so manual jobs persist
    print("\n🌐 Updating GitHub Pages...")
    update_github_pages(combined, last_updated)

    # 7. Email
    print("\n📧 Sending email summary...")
    send_gmail_draft(good, today, len(good))

    print(f"\n{'='*60}")
    print(f"Done. {len(good)} jobs in tracker.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
