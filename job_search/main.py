import argparse
import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from scrapers import (
    scrape_remoteok,
    scrape_greenhouse,
    scrape_lever,
    scrape_comeet,
    scrape_alljobs,
)
from scorer import score_jobs
from sheets import get_existing_urls, get_existing_rows, append_jobs, get_todays_jobs
from deduplication import deduplicate
from email_summary import send_daily_summary
from config import MIN_FIT_SCORE


def main(dry_run: bool = False):
    logger.info("Starting job search pipeline...")

    # 1. Scrape all sources
    all_jobs = []
    for scraper_fn in [scrape_remoteok, scrape_greenhouse, scrape_lever, scrape_comeet, scrape_alljobs]:
        try:
            results = scraper_fn()
            all_jobs.extend(results)
        except Exception as e:
            logger.error(f"Scraper {scraper_fn.__name__} crashed: {e}")

    logger.info(f"Scraped {len(all_jobs)} total jobs")

    # 2. Deduplicate
    existing_urls = get_existing_urls() if not dry_run else set()
    existing_rows = get_existing_rows() if not dry_run else []
    new_jobs = deduplicate(all_jobs, existing_urls, existing_rows)
    logger.info(f"{len(new_jobs)} new jobs after dedup")

    # 3. Score with Claude
    scored_jobs = score_jobs(new_jobs)

    # 4. Filter
    good_jobs = [
        j for j in scored_jobs
        if j.get("location_ok", False) and j.get("fit_score", 0) >= MIN_FIT_SCORE
    ]
    logger.info(f"{len(good_jobs)} jobs pass filter (location_ok + score >= {MIN_FIT_SCORE})")

    if dry_run:
        logger.info("[DRY RUN] Top 5 results:")
        for j in sorted(good_jobs, key=lambda x: x.get("fit_score", 0), reverse=True)[:5]:
            logger.info(f"  [{j['fit_score']}] {j['title']} @ {j['company']} ({j['location']})")
            logger.info(f"       {j['score_reason']}")

    # 5. Write to sheet
    append_jobs(good_jobs, dry_run=dry_run)

    # 6. Send daily email
    email_jobs = good_jobs if dry_run else get_todays_jobs()
    send_daily_summary(email_jobs, dry_run=dry_run)

    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Score but don't write to sheet or send email")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
