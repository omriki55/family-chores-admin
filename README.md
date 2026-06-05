# 🎯 AI Job Search Engine

An autonomous job search pipeline built with Claude. It scans job boards 3× a day, scores every listing against your profile, and serves a live visual tracker — automatically.

```
run_pipeline.py
  ├─ search_jobs()   → Claude Opus + web_search  → finds real open positions
  ├─ score_jobs()    → Claude Haiku              → scores 1–10 vs. your profile
  ├─ filter          → fit_score ≥ 4 + location
  ├─ save JSON       → scored_jobs.json          → single source of truth
  ├─ build HTML      → docs/index.html
  └─ git push        → GitHub Pages (live URL)

.github/workflows/
  ├─ job-scan.yml    → cron 3× daily → runs the pipeline
  └─ deploy-pages.yml → push to docs/ → GitHub Pages auto-deploys
```

**[→ Live Tracker](https://omriki55.github.io/family-chores-admin/)**

---

## What this does

A structured pipeline that turns Claude into a full-stack job search assistant. Fork it, fill in your profile, and get a live dashboard that finds, scores, and tracks every application — including interview rounds, cover letter prompts, and follow-up reminders.

| Feature | How |
|---|---|
| Finds open jobs | Opus 4.8 + `web_search` tool, searches LinkedIn + Greenhouse + Lever + Ashby |
| Scores fit 1–10 | Haiku 4.5 — cheap and fast, evaluates each listing against your profile |
| Preserves manual jobs | `initial_status` field — pipeline scans never overwrite what you add by hand |
| Live tracker | GitHub Pages, auto-deploys on every push |
| Interview rounds | Per-job round tracker: date, interviewer, stage, outcome |
| Cover letter prompt | One click → Claude-ready prompt copied to clipboard |
| CV tailor | Tailored CV text + printable PDF per job |

---

## Results (10 days, real data)

| Metric | Count |
|---|---|
| Total jobs tracked | **52** |
| Applied | **25** |
| Interviews | **5** |
| Passed | **3** (Sauce, Gambit, Neon) |
| Pipeline auto-discovered | **13** |
| Confirmation emails captured | **16+** |

---

## How to use it

### 1. Fork & configure

```bash
git clone https://github.com/your-username/your-repo
cd your-repo
pip install anthropic python-dotenv
```

Edit `job_search/config.json` — set your target roles, location, and profile.

### 2. Add your API key

In GitHub → Settings → Secrets → Actions:
```
ANTHROPIC_API_KEY = sk-ant-...
```

### 3. Enable GitHub Pages

Settings → Pages → Source: `Deploy from a branch` → Branch: `main` → Folder: `/docs`

### 4. Run manually or wait for cron

```bash
python job_search/run_pipeline.py
```

The GitHub Actions workflow runs automatically at **08:00, 13:00, 18:00 Israel time** every day.

---

## Architecture decisions worth knowing

**Opus for search, Haiku for scoring** — Opus finds real job URLs (quality matters); Haiku scores 40+ listings per run (cost matters). Splitting models cut cost ~10× vs. running everything on Opus.

**`scored_jobs.json` as single source of truth** — the pipeline and the tracker both read from this file. Manual jobs have `initial_status` set, which tells the pipeline to preserve them on every scan.

**GitHub Pages over CDN** — raw CDN links cache aggressively and break on push. GitHub Pages redeploys automatically and gives you a stable URL.

**`initial_rounds` for interview data** — pre-populate interview history from your calendar directly in the JSON. The tracker reads it on first open and syncs to localStorage.

---

## The prompts (copy freely)

**Search prompt (Opus)**
```
Search LinkedIn Jobs and other job boards for CURRENTLY OPEN positions
(posted in the last 30 days) matching these roles: {roles}

Search strategy:
1. site:linkedin.com/jobs for each role
2. site:greenhouse.io OR site:lever.co OR site:ashbyhq.com
3. Direct company career pages for B2B SaaS in Israel / remote

CRITICAL RULES:
- Each URL must be a DIRECT link to a SPECIFIC job posting
- URLs like indeed.com/jobs?q=... are FORBIDDEN
- If you cannot find a direct URL, skip it entirely

Return 8-15 real positions as JSON array:
{company, title, location, url, job_type, posted, description}
```

**Scoring prompt (Haiku)**
```
You are evaluating job listings for [name], a [role] with [experience].
CANDIDATE PROFILE: [target roles, strong fit, weak fit, location OK/reject]

Respond in JSON ONLY:
{fit_score (1-10), score_reason, ai_opener, location_ok}
If location_ok is false, set fit_score to 0.
```

---

## What's next

- [ ] `/apply` flow — Claude drafts a tailored cover letter from the job card
- [ ] Gmail sync — auto-capture application confirmation emails
- [ ] LinkedIn API — pull application status directly

---

## License

MIT — fork it, adapt it, ship it.

Built with [Claude Code](https://claude.ai/code) · [Anthropic API](https://anthropic.com)
