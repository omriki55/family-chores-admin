"""
SaaS scan pipeline v2 — runs centrally via GitHub Actions.

Improvements over v1:
  • Multi-dimensional scoring: skills / seniority / location / growth / comp
    → weighted fit_score + comp_estimate + gaps[] + verdict + apply (bool)
  • Writes rich data to jobs.meta (JSONB) when the column exists — detected at
    runtime so the same binary works before/after the schema migration.
  • Liveness check: re-checks URLs that are 7+ days old and marks gone ones
    fit_score=0 / status='נסגרה' so the tracker flags them.
  • apply threshold configurable via site_content key 'platform:apply_threshold'
    (default 6).

Required env vars (GitHub Actions secrets):
  SUPABASE_URL                e.g. https://xxxx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY   service role key (bypasses RLS — server only!)
"""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from anthropic import Anthropic

from ats_scraper import scrape_ats

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

MAX_JOBS_PER_USER_PER_RUN = 20
LIVENESS_AGE_DAYS = 7          # re-check jobs older than this
LIVENESS_SAMPLE = 10           # max jobs to liveness-check per run per user

DEFAULT_APPLY_THRESHOLD = 6

DEFAULT_ATS = {
    "greenhouse": ["monday", "wiz", "fireblocks", "melio", "gong", "riskified",
                   "similarweb", "lemonade", "jfrog", "snyk", "taboola", "verbit"],
    "lever": ["yotpo", "bigpanda", "deel"],
    "ashby": ["island"],
    # Workable: tokens are search keywords (not company slugs).
    # Returns cross-company results; includes remote/TELECOMMUTE roles globally.
    "workable": ["revops", "revenue operations"],
}

SENIORITY_PREFIXES = ("head of ", "senior ", "sr. ", "sr ", "lead ", "principal ",
                      "director of ", "director, ", "vp of ", "vp ", "chief ", "staff ")


# ─── Supabase helpers ────────────────────────────────────────────────────────

def _sb(method: str, path: str, body=None, prefer: str | None = None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Config loaders ──────────────────────────────────────────────────────────

def load_platform_ats() -> dict:
    try:
        rows = _sb("GET", "site_content?key=eq.platform%3Aats&select=value")
        if rows:
            cfg = json.loads(rows[0]["value"])
            if isinstance(cfg, dict) and cfg:
                print("  Using admin-configured ATS list")
                return cfg
    except Exception as e:
        print(f"  ⚠️  platform:ats read failed: {e}")
    return DEFAULT_ATS


def load_apply_threshold() -> int:
    try:
        rows = _sb("GET", "site_content?key=eq.platform%3Aapply_threshold&select=value")
        if rows:
            return int(rows[0]["value"])
    except Exception:
        pass
    return DEFAULT_APPLY_THRESHOLD


def detect_meta_column() -> bool:
    """Return True if jobs table has a 'meta' column (runtime detection)."""
    try:
        # Try fetching a single row with meta — 400 = column missing, 200 = exists
        _sb("GET", "jobs?select=meta&limit=1")
        return True
    except Exception:
        return False


# ─── Matching helpers ─────────────────────────────────────────────────────────

def role_keywords(roles: list[str]) -> list[str]:
    out = set()
    for role in roles or []:
        r = (role or "").strip().lower()
        if len(r) < 3:
            continue
        out.add(r)
        for p in SENIORITY_PREFIXES:
            if r.startswith(p):
                stripped = r[len(p):].strip()
                if len(stripped) >= 3:
                    out.add(stripped)
    return sorted(out)


def title_matches(title: str, keywords: list[str]) -> bool:
    t = (title or "").lower()
    return any(k in t for k in keywords)


# ─── Scoring ──────────────────────────────────────────────────────────────────

SCORING_PROMPT = """\
You are a precise job-fit evaluator. Score this opening for the candidate below.

CANDIDATE:
- Target roles: {roles}
- Background: {background}
- Preferred location: {location}

JOB:
Company: {company}
Title: {title}
Location: {job_location}
Description: {description}

Respond ONLY with valid JSON (no markdown):
{{
  "dimensions": {{
    "skills": <1-10>,
    "seniority": <1-10>,
    "location": <1-10>,
    "growth": <1-10>,
    "comp": <1-10>
  }},
  "fit_score": <weighted integer 1-10; weights: skills×0.35, seniority×0.25, location×0.20, growth×0.10, comp×0.10>,
  "comp_estimate": "<salary range string, e.g. '25–35K NIS/mo' or 'unknown'>",
  "gaps": ["<gap 1>", "<gap 2>"],
  "verdict": "<one crisp sentence: why apply or skip>",
  "apply": <true if fit_score >= {threshold}, else false>,
  "score_reason": "<1-2 sentences summarising the score>",
  "ai_opener": "<2-3 sentence personalised cold outreach opener for this specific company>"
}}
If the location is incompatible and non-remote set location dimension to 1 and fit_score to 0.\
"""


def score_job(client: Anthropic, profile: dict, job: dict, threshold: int) -> dict | None:
    roles = ", ".join(profile.get("roles") or []) or "any relevant role"
    background = profile.get("profile_summary") or "Not provided"
    location = profile.get("location") or "Not specified"

    prompt = SCORING_PROMPT.format(
        roles=roles,
        background=background,
        location=location,
        company=job.get("company", ""),
        title=job.get("title", ""),
        job_location=job.get("location", ""),
        description=(job.get("description") or "")[:900],
        threshold=threshold,
    )
    for attempt in range(2):
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.split("```")[0]
            return json.loads(text.strip())
        except Exception as e:
            if attempt == 0:
                time.sleep(3)
            else:
                print(f"      ⚠️  scoring failed: {e}")
    return None


# ─── Liveness ─────────────────────────────────────────────────────────────────

def check_liveness(url: str) -> bool:
    """Return False if the URL returns 404/410 (job taken down)."""
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "JobSearchAI-liveness/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status < 400
    except urllib.error.HTTPError as e:
        return e.code not in (404, 410)
    except Exception:
        return True  # network error → assume alive


def run_liveness_check(uid: str):
    """Mark old jobs that 404 as closed."""
    cutoff = date.today().isoformat()
    # jobs older than LIVENESS_AGE_DAYS, not already closed, limit sample
    rows = _sb(
        "GET",
        f"jobs?user_id=eq.{uid}"
        f"&scan_date=lt.{cutoff}"
        f"&status=neq.נסגרה"
        f"&select=id,url,scan_date"
        f"&order=scan_date.asc"
        f"&limit={LIVENESS_SAMPLE}"
    ) or []

    # filter to LIVENESS_AGE_DAYS old
    from datetime import timedelta
    threshold_date = (date.today() - timedelta(days=LIVENESS_AGE_DAYS)).isoformat()
    old = [r for r in rows if (r.get("scan_date") or "") <= threshold_date]

    closed = 0
    for row in old:
        if not check_liveness(row["url"]):
            _sb("PATCH", f"jobs?id=eq.{row['id']}",
                {"fit_score": 0, "status": "נסגרה", "score_reason": "המשרה הוסרה"})
            closed += 1
        time.sleep(0.3)

    if closed:
        print(f"    liveness: {closed}/{len(old)} jobs marked closed")


# ─── Per-user processing ──────────────────────────────────────────────────────

def process_user(profile: dict, key: str, all_jobs: list[dict],
                 threshold: int, has_meta: bool):
    username = profile.get("username", "?")
    uid = profile["user_id"]
    keywords = role_keywords(profile.get("roles") or [])
    if not keywords:
        print(f"  {username}: no roles configured — skipping")
        return

    existing = _sb("GET", f"jobs?user_id=eq.{uid}&select=url") or []
    existing_urls = {r["url"] for r in existing}

    candidates = [j for j in all_jobs
                  if title_matches(j["title"], keywords) and j["url"] not in existing_urls]
    candidates = candidates[:MAX_JOBS_PER_USER_PER_RUN]
    print(f"  {username}: {len(candidates)} new matching jobs to score")

    # Liveness check on old jobs (background, best-effort)
    try:
        run_liveness_check(uid)
    except Exception as e:
        print(f"    liveness check error: {e}")

    if not candidates:
        _sb("PATCH", f"profiles?user_id=eq.{uid}", {"last_scanned": _now_iso()})
        return

    client = Anthropic(api_key=key)
    rows = []
    today = date.today().isoformat()

    for i, job in enumerate(candidates):
        print(f"    scoring {i+1}/{len(candidates)}: {job['title']} @ {job['company']}")
        scored = score_job(client, profile, job, threshold)
        if scored is None:
            continue

        row = {
            "user_id": uid,
            "company": job.get("company", ""),
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "description": (job.get("description") or "")[:600],
            "fit_score": int(scored.get("fit_score", 0)),
            "score_reason": scored.get("score_reason", ""),
            "ai_opener": scored.get("ai_opener", ""),
            "posted": job.get("posted") or today,
            "scan_date": today,
        }

        if has_meta:
            row["meta"] = json.dumps({
                "dimensions": scored.get("dimensions"),
                "comp_estimate": scored.get("comp_estimate"),
                "gaps": scored.get("gaps", []),
                "verdict": scored.get("verdict", ""),
                "apply": scored.get("apply", row["fit_score"] >= threshold),
            })

        rows.append(row)
        if (i + 1) % 5 == 0:
            time.sleep(1)

    if rows:
        _sb("POST", "jobs?on_conflict=user_id,url", rows,
            prefer="resolution=merge-duplicates,return=minimal")
        print(f"    saved {len(rows)} jobs")

    _sb("PATCH", f"profiles?user_id=eq.{uid}", {"last_scanned": _now_iso()})


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("👥 Loading users...")
    profiles = _sb("GET",
                   "profiles?select=user_id,username,full_name,roles,location,profile_summary"
                   ) or []
    secrets = _sb("GET", "user_secrets?select=user_id,anthropic_key") or []
    keys = {s["user_id"]: s["anthropic_key"] for s in secrets if s.get("anthropic_key")}
    active = [p for p in profiles if p["user_id"] in keys]
    print(f"  {len(profiles)} users, {len(active)} with API keys")
    if not active:
        print("Nothing to do.")
        return

    threshold = load_apply_threshold()
    print(f"  apply threshold: {threshold}/10")

    has_meta = detect_meta_column()
    print(f"  jobs.meta column: {'✅' if has_meta else '⏳ not yet — skipping meta writes'}")

    print("🔍 Scraping ATS boards (platform-wide, once)...")
    ats = load_platform_ats()
    all_jobs = scrape_ats(ats, keywords=[""])
    seen: set[str] = set()
    unique_jobs = []
    for j in all_jobs:
        if j["url"] and j["url"] not in seen:
            seen.add(j["url"])
            unique_jobs.append(j)
    print(f"  {len(unique_jobs)} unique jobs scraped")

    for profile in active:
        try:
            process_user(profile, keys[profile["user_id"]], unique_jobs,
                         threshold, has_meta)
        except Exception as e:
            print(f"  ⚠️  user {profile.get('username')}: {e}")

    print("✅ Done")


if __name__ == "__main__":
    main()
