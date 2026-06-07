> **לפני פרסום:**
> 📸 **Screenshot** — צלם את הטראקר פתוח עם כמה כרטיסי משרות → העלה כ-Cover Image בלינקדאין

---

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
GitHub Actions runs the pipeline 3× daily (Sun–Thu). A second workflow deploys `docs/` to GitHub Pages.

**3. The Tracker**
A single HTML file, Material 3 design, mobile-first, works offline as a PWA. Every job card has: fit score, status (saved / applied / interview / offer / rejected), interview rounds with dates and interviewers, notes — and a full set of AI-powered tools built directly into each card.

**Model split:** Opus for search (quality matters — you need real URLs, not hallucinations), Haiku for scoring (fast, runs on 14 jobs per cycle).

---

## The Features That Actually Matter

This is where most "I built an AI job tracker" articles stop. They show you a spreadsheet with a score column. Here's what I actually built.

### 🏢 Company Dossier — One Click, Full Intelligence

Every job card has a "Dossier" button. Press it and Claude searches the web in real time and returns a structured company brief:

- **What they do** (one sharp sentence)
- **Funding & stage** (last round, amount, lead investors, valuation if public)
- **Size & offices** (headcount, locations, target market)
- **Recent news** (last 2–3 announcements with dates)
- **Culture & employer reputation** (Glassdoor / LinkedIn signals)
- **Why this role is interesting for me specifically** (RevOps / GTM angle)
- **3 smart questions to ask in the interview** (that prove you did your homework)
- **One red flag** if any exists
- **Sources** for everything

This used to take me 30–45 minutes of research before every interview. Now it takes 15 seconds and comes back more thorough than I could do manually.

The system prompt: *"You are a business intelligence analyst preparing company dossiers for job interviews. Use web search to find current, accurate information. Never fabricate. If a detail isn't found, say so. Always cite sources."*

### 🎯 Interview Prep — Personalized, Not Generic

The "Prep" button opens a live chat with Claude that knows three things simultaneously: the job description, my resume, and the specific company. It generates:

- 8 expected interview questions (behavioral + technical, specific to RevOps)
- Talking points for each question based on my actual experience
- 5 smart questions to ask the interviewer
- One thing to avoid saying

The difference between this and "ask ChatGPT to prep me for an interview" is specificity. It's not generic interview advice — it's prep for this exact role, this exact company, on this exact day.

### 🎙️ Voice Interview Simulation — The Feature That Changes Everything

This one surprised me. I didn't expect it to work as well as it does.

The tracker knows which interview stage I'm at for each company (phone screen, HR, technical, manager, final). The "Practice Interview" button launches a full **voice call simulation** — I speak out loud, the AI responds in a synthetic voice, and the conversation follows the format of the specific stage.

A phone screen feels different from a technical interview. The system uses different prompting for each:

- **Phone screen:** warm, focused on motivation and availability
- **HR interview:** behavioral questions, STAR format, culture fit
- **Technical interview:** deep RevOps — metrics, pipeline, lead scoring, CRM workflows
- **Manager interview:** strategy, 90-day plan, business impact
- **Final round:** vision, leadership, long-term fit

For voice synthesis I use ElevenLabs (10,000 characters/month free — enough for dozens of practice sessions). Without the API key, the browser's built-in speech engine works as a fallback — less natural but functional.

I practiced a Neon Security phone screen twice before the real call. I passed.

### 💙 Emotional Support — The Feature I Didn't Plan to Build

Job searching is emotionally brutal. Three rejections in ten days hits differently when you've customized each application.

I added an emotional support chat to the tracker. Not because it was on my product roadmap — because I needed it.

It's powered by a specific system prompt that turns Claude into a job search mental coach:

1. **Validate first** — acknowledge the feeling before offering advice
2. **Challenge limiting beliefs** — "I'm not good enough" becomes "what evidence actually supports that?"
3. **Shift perspective** — reframe rejection as pipeline data, not personal failure
4. **Practical coping** — breathing, physical breaks, "good enough for today" framing
5. **Energy management** — identify burnout early, end every session with one small concrete action

The job-specific version is even more useful. When I'm spiraling about a specific rejection, I open that company's card and click "Emotional Support" — and it knows the context. It knows I was at the manager stage at Cyolo when the process went quiet. It doesn't ask me to explain.

One thing I realized: a lot of "productivity" advice for job seekers ignores the emotional load entirely. The emotional support feature is the one I open most.

### 🔗 Add Any Job by URL — The Newest Feature

The automated pipeline finds 13 jobs per scan. But I also find jobs manually — on LinkedIn, through referrals, on company career pages. 

The "Add by URL" button (just added this week) takes any job posting link, sends it to Claude with web search enabled, and automatically extracts: company name, title, location, and job description. The job appears in the tracker immediately with the same card format as pipeline-found jobs.

If Claude can't access the page (some ATS systems block scrapers), it falls back to a clean manual entry form.

This closes the last gap between "jobs I found manually" and "jobs tracked systematically." Everything lives in one place now.

---

## The Failures (The Honest Part)

### Failure 1: The Data Wipe

The pipeline treated every run as a fresh slate. Jobs I'd manually added — with status, notes, interview rounds — got overwritten on the next scan.

**The fix:** A `initial_status` field. Any job you add manually carries a flag that tells the pipeline: *never touch this.* The merge logic became: `pipeline_results + manual_entries`, where manual entries always win on conflict.

**The lesson:** A single source of truth only works if you protect it from yourself.

### Failure 2: The Tracker That Never Updated

I was using `raw.githack.com` to serve the HTML. Githack has aggressive caching — sometimes 24+ hours. I'd push a fix and see the old version. Every time.

**The fix:** Moved everything to GitHub Pages. Committed, pushed, live within 60 seconds.

### Failure 3: The Service Worker That Served Stale Code

Even after switching to GitHub Pages, the browser kept showing an old version. The PWA service worker had cached everything.

**The fix:** Bump the cache version string (`jobtracker-v5`). The service worker detects the new cache name, purges the old one, fetches fresh. One line change.

**The lesson:** PWA offline-first is powerful but version your cache intentionally.

### Failure 4: The AI Chat That Wasn't Live

I built a chat interface. Except it wasn't actually calling the API — it was injecting a copy-paste prompt into the input field and waiting for me to manually run it.

**The fix:** Real API integration with a saved key, a "Test connection" button, and an onboarding banner when no key is set.

### Failure 5: The Scan Button That Injected Text Into a Circle

The floating action button for manual scan was 56px wide. When scanning, I set its inner text to "Scanning…" — obviously breaking the layout.

**The fix:** Toggle a CSS class and swap the icon only. The button stays a button.

These are small bugs. But they compound. Five small bugs in a system you're relying on daily turns a useful tool into a frustrating one.

---

## The One Feature That Surprised Me Most: Interview Rounds

Not just "interview" as a status — a structured log: date, interviewer name, stage, outcome, color-coded by result. Expandable card. Fits on mobile.

I have 5 interviews tracked. I know who I spoke to, when, what happened, and what's next. If a recruiter follows up two weeks later, I open the card — not my email.

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
13 out of 52 jobs came from the automated scanner. The other 39 I added manually — LinkedIn, referrals, direct outreach. The system augments the search; it doesn't replace the human part.

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
- Add by URL: button that takes any job link, extracts details with Claude + web_search,
  adds to tracker immediately, falls back to manual entry form

Per-job AI buttons (each opens a live chat or report with full context):
1. Cover letter — personalized to the JD and my resume
2. Interview prep — 8 questions + talking points + smart questions to ask
3. Voice practice — live voice simulation of the specific interview stage
   (phone screen / HR / technical / manager / final), with ElevenLabs voice
4. Company dossier — AI web research: funding, team size, culture, news,
   3 smart questions, 1 red flag, sources
5. CV tailoring — adjusted resume for this specific role
6. Emotional support — mental coach chat, context-aware per job/stage

Global emotional support (bottom nav) — same mental coach but open-ended.
Analytics screen: funnel chart (applied → interview → offer), conversion rates,
average days waiting, interview rounds won/lost.
Dark mode toggle.

## Cost
Use Haiku for scoring (cheap). Use Opus only for search (quality).

Ask me before any significant architectural decision. Start with onboarding.
```

### The 4 Setup Steps

1. **Get an Anthropic API key** — `console.anthropic.com` → create key. Pay-as-you-go, no subscription.

2. **Paste the prompt above into Claude Code** — answer the onboarding questions about your roles and experience.

3. **Add your API key to GitHub Secrets** — Settings → Secrets → Actions → `ANTHROPIC_API_KEY`.

4. **Enable GitHub Pages** — Settings → Pages → Branch: main → Folder: /docs.

**Optional:** Add an ElevenLabs API key (free tier) for human-quality voice in interview practice. Without it, the browser's speech engine works as fallback.

**Note on LinkedIn:** LinkedIn has no public jobs API since 2023, and scraping violates their ToS. The working legal solution: Claude finds direct links via web search + Greenhouse/Lever/Ashby public APIs, which is where most tech companies post anyway.

---

## Four Things I Actually Learned

**1. Single source of truth is not a philosophy — it's a constraint you enforce in code.**
The moment my pipeline and my manual data lived in two places, I lost data. One JSON file. One read path. One write path. Anything else is a bug waiting to happen.

**2. Split your models by task.**
Opus for search — URL quality matters, hallucinated links waste your time. Haiku for scoring — fast, runs 42 calls per day, negligible quality difference for this task.

**3. The emotional features matter as much as the analytical ones.**
I built the emotional support chat because I needed it, not because it was on my roadmap. Job searching is genuinely hard emotionally. A system that helps you track conversion rates but ignores the human experience of rejection is only half a product.

**4. AI systems are built in the second version.**
The first version worked. The second version is the one I actually use. The bugs I hit weren't edge cases — they were the predictable failures of a system that had never been stressed. Build v1 fast, stress it immediately, build v2 right.

---

## What's Next

The system works. I'm still searching. Three interviews passed, pipeline still running, tracker still updating.

If you want to build your own: the prompt above is exactly what built mine.

👉 **Repo (open source):** github.com/omriki55/family-chores-admin
👉 **Live tracker:** omriki55.github.io/family-chores-admin

The architecture is public. The data is yours — your GitHub, your API key, pay as you go.

If you build it and hit a wall — reach out. Happy to share.

---

*Written during an active job search. The prompt above built the system I'm using right now.*

*#JobSearch #AI #Claude #BuildInPublic #RevOps #Automation #PWA*
