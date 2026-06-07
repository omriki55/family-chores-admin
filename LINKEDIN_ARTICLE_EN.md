# I Built an AI Job Search Engine — Then It Crashed, and I Built It Better

*The real story: failures, fixes, and the exact prompts to replicate it yourself*

---

I opened my job tracker on a Tuesday morning and saw 14 jobs.

There were supposed to be 52.

The pipeline had run overnight, overwritten everything, and silently deleted every job I'd manually added. No warning. No error. Just gone.

That was the moment I stopped thinking about job hunting and started thinking about engineering.

---

## How This Started

Ten days ago I started an active job search. I'm a RevOps professional, and my first instinct wasn't "let me update my resume." It was: *"let me build a system that does this for me."*

So I did.

I built an AI agent that scans for open positions three times a day, scores each one against my profile, and publishes a live tracker — automatically. No manual searching. No spreadsheet archaeology. A real URL I can open on my phone and see exactly where I stand.

**Ten days in: 25 applications, 5 interviews, 3 passed.**

But this article isn't about the wins. It's about what broke, why it broke, and how I fixed it — because that's actually the more useful story.

---

## The Architecture (What I Built)

The system has three layers:

**1. The Pipeline (`run_pipeline.py`)**
```
search_jobs()   → Claude Opus + web_search → finds real, live postings
score_jobs()    → Claude Haiku             → scores 1–10 against my profile  
filter          → fit_score ≥ 4 + location match
save            → scored_jobs.json (single source of truth)
build           → docs/index.html from template
git push        → GitHub Pages (live URL, always current)
```

**2. The Automation**
GitHub Actions runs the pipeline 3× daily (Sun–Thu). A second workflow deploys `docs/` to GitHub Pages. Total cost: $0 for compute.

**3. The Tracker**
A single HTML file, Material 3 design, mobile-first, works offline as a PWA. Every job gets a card with: fit score, status (saved / applied / interview / offer / rejected), interview rounds with dates and interviewers, notes, and one-click prompt generation for cover letters, interview prep, and company research.

**Model split:** Opus for search (quality matters — you need real URLs, not hallucinations), Haiku for scoring (fast, cheap, runs on 14 jobs per cycle). This alone cuts API cost by ~80%.

---

## The Failures (The Honest Part)

### Failure 1: The Data Wipe

The pipeline treated every run as a fresh slate. Jobs I'd manually added — with status, notes, interview rounds — got overwritten on the next scan.

**The fix:** A `initial_status` field. Any job you add manually carries a flag that tells the pipeline: *never touch this.* The merge logic became: `pipeline_results + manual_entries`, where manual entries always win on conflict.

**The lesson:** A single source of truth only works if you protect it from yourself.

### Failure 2: The Tracker That Never Updated

I was using `raw.githack.com` to serve the HTML. Githack has aggressive caching — sometimes 24+ hours. I'd push a fix and check the site and see the old version. Every time.

**The fix:** Moved everything to GitHub Pages. Committed, pushed, live within 60 seconds. This should have been the setup from day one.

### Failure 3: The Service Worker That Served Stale Code

Even after switching to GitHub Pages, the browser kept showing an old version. The PWA service worker had cached everything.

**The fix:** Bump the cache version string (`jobtracker-v5`). The service worker detects a new cache name, purges the old one, fetches fresh. One line change.

**The lesson:** PWA offline-first is powerful but you have to version your cache intentionally, not accidentally.

### Failure 4: The AI Chat That Wasn't Live

I built a chat interface powered by Claude. Users would ask questions about companies, get interview prep, generate tailored cover letters. Except — it wasn't actually calling the API. It was injecting a copy-paste prompt into the input field and waiting for the user to manually run it.

**The fix:** Real API integration with a saved key, a "Test connection" button, and a clear onboarding banner when no key is set. Now it's genuinely live — type a question, get an answer.

### Failure 5: The Scan Button That Injected Text Into a Circle

The floating action button (FAB) for triggering a manual scan was 56px wide. When it was "scanning," I was setting its inner text to "Scanning…" — which obviously broke the layout. A 56px circle cannot fit 9 characters.

**The fix:** Toggle a CSS class (`scanning`) and swap the icon only. The button stays a button. The icon rotates to indicate activity.

These are small bugs. But they compound. Five small bugs in a system you're relying on daily turns a useful tool into a frustrating one.

---

## The One Feature That Changed Everything

**Interview Rounds tracking.**

Not just "interview" as a status, but a structured log: date, interviewer name, stage (HR / Technical / Final), outcome, color-coded by result. Expandable card. Fits in a mobile viewport.

I have 5 interviews in the tracker. I know exactly who I spoke to, when, and what happened. If a recruiter follows up two weeks later, I don't have to dig through email — I open the card.

This took two hours to build. It should have been in version one.

---

## The Numbers (Transparent)

| Metric | Count |
|--------|-------|
| Jobs in tracker | 52 |
| Applications submitted | 25 |
| Interviews | 5 |
| Passed interviews | 3 (Neon Security, Sauce, Gambit Security) |
| Rejections | 3 (Cyolo, Agora, NEEMA) |
| Jobs found automatically by pipeline | 13 |
| Estimated API cost so far | ~$5–8 |

13 out of 52 jobs came from the automated scanner. The other 39 I added manually — from LinkedIn, referrals, direct outreach. The system augments the search; it doesn't replace the human part.

---

## How to Build This Yourself (The Exact Prompt)

This is the prompt I used with Claude Code. Copy it. Paste it. Answer the onboarding questions. You'll have a working system within a session.

```
Build me an automated AI job search engine, deployed on GitHub Pages.

## Step 1 — Onboarding: Ask me first
1. What roles am I looking for?
2. Where am I willing to work? (location / remote)
3. What is my experience and key strengths?
4. Ask me to upload my resume (PDF or TXT)
Generate config.json + profile.md from my answers.

## Architecture
run_pipeline.py:
  - search_jobs()  → Claude Opus + web_search → finds real open postings
  - ats_scraper    → Greenhouse / Lever / Ashby public APIs (companies I select)
  - score_jobs()   → Claude Haiku → scores 1-10 against my profile
  - filter         → score ≥ 4 + location match + posted within 30 days
  - save           → scored_jobs.json (single source of truth)
  - build          → docs/index.html from template
  - git push       → GitHub Pages

## Critical Rule
scored_jobs.json is the ONLY source of truth. Jobs I add manually get an
initial_status field. The pipeline NEVER deletes them. Merge = pipeline + manual.

## Search Prompt (Opus)
"Find CURRENTLY OPEN jobs (posted last 30 days) for: {roles}.
Each URL must be a DIRECT link to a specific posting — search result pages FORBIDDEN.
Return 8-15 as JSON: {company, title, location, url, posted, description}"

## Scoring Prompt (Haiku)
"Evaluate this job for [profile]. Return JSON only:
{fit_score 1-10, score_reason, ai_opener, location_ok}. If location not OK → 0."

## Automation
GitHub Actions: cron 3x daily (Sun–Thu), permissions: contents: write.
Second workflow: deploy docs/ to GitHub Pages.

## Tracker (docs/index.html) — Material 3, mobile-first, PWA
Single HTML file, all state in localStorage. Each job card:
- Fit score, status (saved/applied/interview/offer/rejected)
- Interview rounds: date, interviewer, stage, outcome, color by result
- Notes field
- Buttons: generate cover letter prompt, interview prep, company research dossier
- "Not relevant — learn from this" → saves to feedback.json for next scan

Analytics screen: funnel chart (applied → interview → offer). Dark mode toggle.

## Cost
Use Haiku for scoring (cheap). Use Opus only for search (quality).

Ask me before any significant architectural decision. Start with onboarding.
```

### The 4 Setup Steps

1. **Get an Anthropic API key** — `console.anthropic.com` → add $10 credit → create key. (This is the API, pay-as-you-go. Not Claude Pro.)

2. **Paste the prompt above into Claude Code** — answer the onboarding questions about your roles and experience.

3. **Add your API key to GitHub Secrets** — Settings → Secrets → Actions → `ANTHROPIC_API_KEY`.

4. **Enable GitHub Pages** — Settings → Pages → Branch: main → Folder: /docs. Done.

**Note on LinkedIn:** LinkedIn has no public jobs API since 2023, and scraping violates their ToS. The working legal solution: Claude finds direct links via web search + Greenhouse/Lever/Ashby public APIs, which is where most tech companies post anyway.

---

## Three Things I Actually Learned

**1. Single source of truth is not a philosophy — it's a constraint you enforce in code.**
The moment my pipeline and my manual data lived in two places, I lost data. One JSON file. One read path. One write path. Anything else is a bug waiting to happen.

**2. Split your models by task, not by budget.**
I use Opus for search because URL quality matters — hallucinated links waste your time. I use Haiku for scoring because scoring 14 jobs 3× daily is 42 Haiku calls, not 42 Opus calls. The cost difference is ~10×. The quality difference for scoring is negligible.

**3. AI systems are built in the second version.**
The first version of this tracker worked. The second version is the one I actually use. The bugs I hit weren't edge cases — they were the predictable failures of a system that had never been stressed. Build v1 fast, stress it immediately, build v2 right.

---

## What's Next

The system works. I'm still searching. Three interviews passed, pipeline still running, tracker still updating.

If you want to build your own: the prompt above is exactly what built mine. The architecture is public. The data is yours — it lives in your GitHub, runs on your API key, costs ~$5–10/month.

If you build it and hit a wall, or if you want to see how I structured the interview rounds feature — reach out. The tracker is open source. I'm happy to share.

---

*Written during an active job search. The prompt above built the system I'm using right now.*

*#JobSearch #AI #Claude #BuildInPublic #RevOps #Automation*
