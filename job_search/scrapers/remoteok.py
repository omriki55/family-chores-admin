import requests
import logging
from config import SEARCH_QUERIES

logger = logging.getLogger(__name__)

REMOTEOK_API = "https://remoteok.com/api"

def scrape_remoteok() -> list[dict]:
    jobs = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (job-search-bot/1.0)"}
        resp = requests.get(REMOTEOK_API, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # First item is a legal notice, skip it
        listings = [item for item in data if isinstance(item, dict) and "slug" in item]
        queries_lower = [q.lower() for q in SEARCH_QUERIES]
        for job in listings:
            tags = " ".join(job.get("tags", [])).lower()
            title = job.get("position", "").lower()
            text = f"{title} {tags}"
            if any(q in text for q in queries_lower):
                jobs.append({
                    "company": job.get("company", ""),
                    "title": job.get("position", ""),
                    "location": "Remote",
                    "url": f"https://remoteok.com/remote-jobs/{job.get('slug', '')}",
                    "description": job.get("description", "")[:2000],
                    "job_type": "Full-time",
                    "source": "RemoteOK",
                })
        logger.info(f"RemoteOK: found {len(jobs)} matching jobs")
    except Exception as e:
        logger.error(f"RemoteOK scraper failed: {e}")
    return jobs
