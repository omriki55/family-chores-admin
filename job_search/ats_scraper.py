"""
ATS scraper — pulls open positions directly from public job-board APIs.

Greenhouse, Lever, and Ashby all expose free, unauthenticated JSON endpoints
for each company's public job board. This is a legal, stable alternative to
scraping LinkedIn: most B2B SaaS companies host their real listings here, and
LinkedIn merely mirrors them.

Workable is a cross-company search via jobs.workable.com (no auth required).

Configure target companies in config.json:
"ats": {
  "greenhouse": ["stripe", "figma"],
  "lever": ["netflix"],
  "ashby": ["ramp"],
  "workable": ["revenue operations", "revops", "go-to-market"]
}
The string is the company board token (Greenhouse/Lever/Ashby) or a search
query keyword (Workable).
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

_TIMEOUT = 20
_UA = {"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"}


def _get_json(url: str):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&amp;|&lt;|&gt;|&#\d+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _recent(iso_ts: str, days: int = 30) -> bool:
    """True if the timestamp is within `days` of now (or if unparseable)."""
    if not iso_ts:
        return True
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days <= days
    except Exception:
        return True


def _job(company, title, location, url, posted, description) -> dict:
    return {
        "company": company,
        "title": title,
        "location": location or "Not specified",
        "url": url,
        "job_type": "Full-time",
        "posted": posted or date.today().isoformat(),
        "description": _strip_html(description)[:600],
        "source": "ats",
    }


# ── Greenhouse ────────────────────────────────────────────────────────────────

def scrape_greenhouse(token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        data = _get_json(url)
    except Exception as e:
        print(f"  ⚠️  Greenhouse {token}: {e}")
        return []
    out = []
    for j in data.get("jobs", []):
        updated = j.get("updated_at", "")
        if not _recent(updated):
            continue
        out.append(_job(
            j.get("company_name") or token.title(),
            j.get("title", ""),
            (j.get("location") or {}).get("name", ""),
            j.get("absolute_url", ""),
            updated[:10],
            j.get("content", ""),
        ))
    return out


# ── Lever ─────────────────────────────────────────────────────────────────────

def scrape_lever(token: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        data = _get_json(url)
    except Exception as e:
        print(f"  ⚠️  Lever {token}: {e}")
        return []
    out = []
    for j in data:
        created_ms = j.get("createdAt", 0)
        posted = ""
        if created_ms:
            posted = datetime.fromtimestamp(created_ms / 1000, timezone.utc).date().isoformat()
            if (datetime.now(timezone.utc).date() - datetime.fromisoformat(posted).date()).days > 30:
                continue
        cats = j.get("categories", {}) or {}
        out.append(_job(
            token.title(),
            j.get("text", ""),
            cats.get("location", ""),
            j.get("hostedUrl", ""),
            posted,
            j.get("descriptionPlain") or j.get("description", ""),
        ))
    return out


# ── Ashby ─────────────────────────────────────────────────────────────────────

def scrape_ashby(token: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"
    try:
        data = _get_json(url)
    except Exception as e:
        print(f"  ⚠️  Ashby {token}: {e}")
        return []
    out = []
    for j in data.get("jobs", []):
        out.append(_job(
            token.title(),
            j.get("title", ""),
            j.get("location", ""),
            j.get("jobUrl", ""),
            (j.get("publishedAt") or "")[:10],
            j.get("descriptionPlain") or j.get("description", ""),
        ))
    return out


# ── Workable ──────────────────────────────────────────────────────────────────

_WORKABLE_BASE = "https://jobs.workable.com/api/v1/jobs"
_WORKABLE_MAX_PAGES = 5        # up to 5 × ~20 = 100 results per query term


def scrape_workable(query: str) -> list[dict]:
    """Search the Workable job board for *query* across all companies in Israel.

    Unlike Greenhouse/Lever/Ashby (which are company-specific), Workable
    operates as a cross-company job search.  The *token* in the ATS config
    is a search keyword, e.g. "revenue operations" or "revops".
    """
    headers = {**_UA, "Accept": "application/json"}
    out: list[dict] = []
    seen_ids: set[str] = set()
    page_token: str | None = None

    for _ in range(_WORKABLE_MAX_PAGES):
        params: dict[str, str] = {"query": query}
        if page_token:
            params["pageToken"] = page_token
        url = _WORKABLE_BASE + "?" + urllib.parse.urlencode(params)
        try:
            data = _get_json(url)
        except Exception as e:
            print(f"  ⚠️  Workable '{query}': {e}")
            break

        for j in data.get("jobs", []):
            jid = j.get("id")
            if not jid or jid in seen_ids:
                continue
            if not _recent(j.get("created", "")):
                continue
            seen_ids.add(jid)

            company_info = j.get("company") or {}
            company_name = company_info.get("title", "")

            # locations is a list of strings e.g. ["Tel Aviv-Yafo, Tel Aviv District, Israel"]
            locs = j.get("locations") or []
            location = locs[0] if locs else (
                (j.get("location") or {}).get("city", "Not specified")
            )

            out.append(_job(
                company_name,
                j.get("title", ""),
                location,
                j.get("url", ""),
                (j.get("created") or "")[:10],
                j.get("description", ""),
            ))

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return out


# ── Registry ──────────────────────────────────────────────────────────────────

_SCRAPERS = {
    "greenhouse": scrape_greenhouse,
    "lever": scrape_lever,
    "ashby": scrape_ashby,
    "workable": scrape_workable,
}

# Title keywords used to pre-filter ATS jobs before scoring. ATS boards return
# EVERY open role at a company (engineers, recruiters, etc.); scoring all of
# them wastes tokens. Only roles whose title matches one of these are kept.
_DEFAULT_KEYWORDS = [
    "revenue operation", "revops", "rev ops", "gtm", "go-to-market",
    "growth", "sales operation", "sales ops", "marketing operation",
    "marketing ops", "revenue strategy", "sales strategy", "business operation",
]

# Location keywords — a job is kept only if its location matches one of these.
# Covers Israel-based roles plus genuinely remote/global ones.
_DEFAULT_LOCATIONS = [
    "israel", "tel aviv", "tel-aviv", "herzliya", "ra'anana", "raanana",
    "petah tikva", "netanya", "haifa", "jerusalem", "remote", "telecommute", "global",
    "anywhere", "worldwide",
]


def _title_relevant(title: str, keywords: list[str]) -> bool:
    t = (title or "").lower()
    return any(k in t for k in keywords)


def _location_ok(location: str, locations: list[str]) -> bool:
    loc = (location or "").lower()
    if not loc or loc == "not specified":
        return True  # let the scorer decide when location is unknown
    return any(l in loc for l in locations)


def scrape_ats(ats_config: dict, keywords: list[str] | None = None,
               locations: list[str] | None = None) -> list[dict]:
    """Run all configured ATS scrapers, returning role- and location-relevant jobs.

    `keywords` filters by job title (target roles).
    `locations` filters by job location (Israel + remote by default) so we never
    waste scoring tokens on roles that can't pass the location constraint.

    Note: for the 'workable' provider, each token IS a search keyword, so
    Workable results arrive pre-filtered by role and country.  The title and
    location post-filters still run for consistency.
    """
    keywords = [k.lower() for k in (keywords or _DEFAULT_KEYWORDS)]
    locations = [l.lower() for l in (locations or _DEFAULT_LOCATIONS)]
    jobs = []
    for provider, tokens in (ats_config or {}).items():
        fn = _SCRAPERS.get(provider)
        if not fn:
            continue
        for token in tokens:
            found = fn(token)
            relevant = [
                j for j in found
                if _title_relevant(j["title"], keywords) and _location_ok(j["location"], locations)
            ]
            if found:
                print(f"  {provider}/{token}: {len(relevant)}/{len(found)} relevant (title+location)")
            jobs.extend(relevant)
    return jobs


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cfg = {"greenhouse": sys.argv[1:]}
    else:
        cfg = {"workable": ["revenue operations", "revops"]}
    for j in scrape_ats(cfg):
        print(f"[{j['posted']}] {j['title']} @ {j['company']} — {j['location']}")
