import requests
import logging
from bs4 import BeautifulSoup
from config import SEARCH_QUERIES

logger = logging.getLogger(__name__)

ALLJOBS_SEARCH_URL = "https://www.alljobs.co.il/SearchResultsGuest.aspx"

def scrape_alljobs() -> list[dict]:
    jobs = []
    seen_urls = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
        "Accept-Charset": "utf-8",
    }
    for query in SEARCH_QUERIES:
        try:
            params = {"q": query}
            resp = requests.get(ALLJOBS_SEARCH_URL, params=params, headers=headers, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # AllJobs job cards
            cards = soup.select(".job-content") or soup.select("[class*='job_item']") or soup.select(".single-position")
            for card in cards:
                link_tag = card.find("a", href=True)
                if not link_tag:
                    continue
                url = link_tag["href"]
                if not url.startswith("http"):
                    url = f"https://www.alljobs.co.il{url}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                title = link_tag.get_text(strip=True) or card.find(["h2", "h3", "h4"]).get_text(strip=True) if card.find(["h2","h3","h4"]) else ""
                company_tag = card.select_one(".company-name") or card.select_one("[class*='company']")
                company = company_tag.get_text(strip=True) if company_tag else ""
                location_tag = card.select_one(".job-location") or card.select_one("[class*='location']")
                location = location_tag.get_text(strip=True) if location_tag else ""
                jobs.append({
                    "company": company,
                    "title": title,
                    "location": location,
                    "url": url,
                    "description": card.get_text(" ", strip=True)[:2000],
                    "job_type": "Full-time",
                    "source": "AllJobs",
                })
        except Exception as e:
            logger.warning(f"AllJobs scraper failed for query '{query}': {e}")
    logger.info(f"AllJobs: found {len(jobs)} matching jobs")
    return jobs
