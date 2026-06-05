"""
ATS scraper — pulls open positions directly from public job-board APIs.

Greenhouse, Lever, and Ashby all expose free, unauthenticated JSON endpoints
for each company's public job board. This is a legal, stable alternative to
scraping LinkedIn: most B2B SaaS companies host their real listings here, and
LinkedIn merely mirrors them.

Configure target companies in config.json:
    "ats": {
        "greenhouse": ["stripe", "figma"],
        "lever": ["netflix"],
        "ashby": ["ramp"]
    }
The string is the company's board token (the slug in their careers URL).
"""
import json
import re
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


def scrape_greenhouse(token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        data = _get_json(url)
    except Exception as e:
        print(f"    ⚠️  Greenhouse {token}: {e}")
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


def scrape_lever(token: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        data = _get_json(url)
    except Exception as e:
        print(f"    ⚠️  Lever {token}: {e}")
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


def scrape_ashby(token: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"
    try:
        data = _get_json(url)
    except Exception as e:
        print(f"    ⚠️  Ashby {token}: {e}")
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


_SCRAPERS = {
    "greenhouse": scrape_greenhouse,
    "lever": scrape_lever,
    "ashby": scrape_ashby,
}

# Title keywords used to pre-filter ATS jobs before scoring. ATS boards return
# EVERY open role at a company (engineers, recruiters, etc.); scoring all of
# them wastes tokens. Only roles whose title matches one of these are kept.
_DEFAULT_KEYWORDS = [
    "revenue operation", "revops", "rev ops", "gtm", "go-to-market",
    "growth", "sales operation", "sales ops", "marketing operation",
    "marketing ops", "revenue strategy", "sales strategy", "business operation",
]


def _title_relevant(title: str, keywords: list[str]) -> bool:
    t = (title or "").lower()
    return any(k in t for k in keywords)


def scrape_ats(ats_config: dict, keywords: list[str] | None = None) -> list[dict]:
    """Run all configured ATS scrapers, returning only role-relevant jobs.

    `keywords` filters by job title (case-insensitive substring match) so we
    only score listings that plausibly fit the target roles.
    """
    keywords = [k.lower() for k in (keywords or _DEFAULT_KEYWORDS)]
    jobs = []
    for provider, tokens in (ats_config or {}).items():
        fn = _SCRAPERS.get(provider)
        if not fn:
            continue
        for token in tokens:
            found = fn(token)
            relevant = [j for j in found if _title_relevant(j["title"], keywords)]
            if found:
                print(f"    {provider}/{token}: {len(relevant)}/{len(found)} relevant")
            jobs.extend(relevant)
    return jobs


if __name__ == "__main__":
    import sys
    cfg = {"greenhouse": sys.argv[1:]} if len(sys.argv) > 1 else {}
    for j in scrape_ats(cfg):
        print(f"[{j['posted']}] {j['title']} @ {j['company']} — {j['location']}")
