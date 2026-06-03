import requests
import logging
from config import SEARCH_QUERIES, LEVER_COMPANIES

logger = logging.getLogger(__name__)

def scrape_lever() -> list[dict]:
    jobs = []
    queries_lower = [q.lower() for q in SEARCH_QUERIES]
    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            listings = resp.json()
            for job in listings:
                title = job.get("text", "").lower()
                if any(q in title for q in queries_lower):
                    categories = job.get("categories", {})
                    location_str = categories.get("location", "") or categories.get("allLocations", [""])[0] if categories.get("allLocations") else ""
                    description_parts = [
                        job.get("descriptionPlain", ""),
                        " ".join(
                            item.get("content", "") for item in job.get("lists", [])
                        ),
                    ]
                    description = " ".join(description_parts)[:2000]
                    jobs.append({
                        "company": company,
                        "title": job.get("text", ""),
                        "location": location_str,
                        "url": job.get("hostedUrl", ""),
                        "description": description,
                        "job_type": "Full-time",
                        "source": "Lever",
                    })
        except Exception as e:
            logger.warning(f"Lever scraper failed for {company}: {e}")
    logger.info(f"Lever: found {len(jobs)} matching jobs")
    return jobs
