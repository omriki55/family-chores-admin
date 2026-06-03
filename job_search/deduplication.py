import difflib
import logging

logger = logging.getLogger(__name__)

def deduplicate(new_jobs: list[dict], existing_urls: set[str], existing_rows: list[dict]) -> list[dict]:
    unique = []
    existing_keys = {
        (row.get("Company", "").lower(), row.get("Role Title", "").lower())
        for row in existing_rows
    }
    seen_in_batch: set[str] = set()
    seen_keys_in_batch: set[tuple] = set()

    for job in new_jobs:
        url = job.get("url", "")
        if url and url in existing_urls:
            continue
        if url and url in seen_in_batch:
            continue

        company = job.get("company", "").lower()
        title = job.get("title", "").lower()
        key = (company, title)

        # Exact key match
        if key in existing_keys or key in seen_keys_in_batch:
            continue

        # Fuzzy match against existing rows
        is_dupe = False
        for (ex_company, ex_title) in existing_keys | seen_keys_in_batch:
            company_sim = difflib.SequenceMatcher(None, company, ex_company).ratio()
            title_sim = difflib.SequenceMatcher(None, title, ex_title).ratio()
            if company_sim > 0.85 and title_sim > 0.85:
                is_dupe = True
                break

        if is_dupe:
            continue

        unique.append(job)
        if url:
            seen_in_batch.add(url)
        seen_keys_in_batch.add(key)

    logger.info(f"Deduplication: {len(new_jobs)} raw → {len(unique)} unique new jobs")
    return unique
