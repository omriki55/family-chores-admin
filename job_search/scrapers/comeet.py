import requests
import logging
from bs4 import BeautifulSoup
from config import SEARCH_QUERIES

logger = logging.getLogger(__name__)

COMEET_SEARCH_URL = "https://www.comeet.com/jobs/"

def scrape_comeet() -> list[dict]:
    jobs = []
    queries_lower = [q.lower() for q in SEARCH_QUERIES]
    seen_urls = set()
    for query in SEARCH_QUERIES:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (job-search-bot/1.0)"}
            params = {"q": query}
            resp = requests.get(COMEET_SEARCH_URL, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Comeet renders results in job cards; try multiple selectors
            cards = soup.select("[class*='position']") or soup.select("[class*='job']") or soup.select("article")
            for card in cards:
                link_tag = card.find("a", href=True)
                if not link_tag:
                    continue
                url = link_tag["href"]
                if not url.startswith("http"):
                    url = f"https://www.comeet.com{url}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                title_tag = card.find(["h2", "h3", "h4"]) or link_tag
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not any(q in title.lower() for q in queries_lower):
                    continue
                company_tag = card.select_one("[class*='company']") or card.select_one("[class*='employer']")
                company = company_tag.get_text(strip=True) if company_tag else ""
                location_tag = card.select_one("[class*='location']") or card.select_one("[class*='city']")
                location = location_tag.get_text(strip=True) if location_tag else ""
                jobs.append({
                    "company": company,
                    "title": title,
                    "location": location,
                    "url": url,
                    "description": card.get_text(" ", strip=True)[:2000],
                    "job_type": "Full-time",
                    "source": "Comeet",
                })
        except Exception as e:
            logger.warning(f"Comeet scraper failed for query '{query}': {e}")
    logger.info(f"Comeet: found {len(jobs)} matching jobs")
    return jobs
