import json
import time
import logging
import os
from anthropic import Anthropic
from config import SCORING_PROMPT

logger = logging.getLogger(__name__)

client = None

def _get_client():
    global client
    if client is None:
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return client

def _score_job(job: dict) -> dict:
    prompt = SCORING_PROMPT.format(
        company=job.get("company", ""),
        title=job.get("title", ""),
        location=job.get("location", ""),
        description=job.get("description", "")[:1500],
    )
    for attempt in range(2):
        try:
            response = _get_client().messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            # Extract JSON from response
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
            job["fit_score"] = int(result.get("fit_score", 0))
            job["score_reason"] = result.get("score_reason", "")
            job["ai_opener"] = result.get("ai_opener", "")
            job["location_ok"] = bool(result.get("location_ok", True))
            return job
        except Exception as e:
            if attempt == 0:
                logger.warning(f"Scoring attempt 1 failed for {job.get('title')}: {e}, retrying in 5s")
                time.sleep(5)
            else:
                logger.error(f"Scoring failed for {job.get('title')}: {e}, skipping")
                job["fit_score"] = 0
                job["score_reason"] = "Scoring failed"
                job["ai_opener"] = ""
                job["location_ok"] = False
    return job

def score_jobs(jobs: list[dict]) -> list[dict]:
    scored = []
    batch_size = 5
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        for job in batch:
            scored.append(_score_job(job))
        if i + batch_size < len(jobs):
            time.sleep(1)
    logger.info(f"Scored {len(scored)} jobs")
    return scored
