import requests
import logging
from config import SEARCH_QUERIES, GREENHOUSE_COMPANIES

logger = logging.getLogger(__name__)

def scrape_greenhouse() -> list[dict]:
    jobs = []
    queries_lower = [q.lower() for q in SEARCH_QUERIES]
    for company in GREENHOUSE_COMPANIES:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
            for job in data.get("jobs", []):
                title = job.get("title", "").lower()
                if any(q in title for q in queries_lower):
                    meta = job.get("metadata", []) or []
                    location_str = job.get("location", {}).get("name", "")
                    jobs.append({
                        "company": company.capitalize(),
                        "title": job.get("title", ""),
                        "location": location_str,
                        "url": job.get("absolute_url", ""),
                        "description": job.get("content", "")[:2000],
                        "job_type": "Full-time",
                        "source": "Greenhouse",
                    })
        except Exception as e:
            logger.warning(f"Greenhouse scraper failed for {company}: {e}")
    logger.info(f"Greenhouse: found {len(jobs)} matching jobs")
    return jobs
