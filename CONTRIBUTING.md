# Contributing

Thanks for wanting to help! / תודה שבאתם לעזור!

## Ways to contribute

- **New board providers** — `job_search/ats_scraper.py` has one function per provider (Greenhouse/Lever/Ashby). Workable, Comeet and SmartRecruiters all have public JSON endpoints and make great PRs.
- **Tracker features** — everything lives in `docs/app.html` (single file, vanilla JS).
- **Translations** — the landing page uses a `data-i18n` dictionary; adding a language = adding one dict.
- **Bug reports** — use the issue templates.

## Ground rules

1. No personal data in commits — ever. The repo is public.
2. Single-file pages stay single-file (no build step).
3. Hebrew RTL must keep working — test with the language toggle.
4. Keep the worker stdlib-only (plus `anthropic`).

## Dev setup

There is no build. Open `docs/landing.html` locally or fork + enable GitHub Pages.
For the worker: `pip install anthropic`, set `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`, run `python job_search/saas_pipeline.py`.
