# JobSearch AI

**English** | [עברית](README.he.md)

> AI-powered job search that comes to you. Sign up, fill a 2-minute wizard, and your personal AI scans job boards 3× a day, scores every opening against *your* profile, and hands you a tracker with outreach openers, interview prep, and emotional support.

![Demo](docs/demo.gif)

**Live:** [omriki55.github.io/omrigonenjobfinder](https://omriki55.github.io/omrigonenjobfinder/landing.html)

---

## What is this

Companies use AI to filter candidates. JobSearch AI gives candidates an AI to **choose companies** — without installing anything.

Unlike CLI-based tools, this is a **zero-install web app**: no terminal, no npm, no config files. Your grandmother could onboard. The entire stack is a static site on GitHub Pages + Supabase + one GitHub Action — free tier all the way.

> **Philosophy: this is a filter, not a spray-and-pray cannon.** The AI recommends applying only when the weighted fit is 6/10 or higher. Your time is valuable — so is the recruiter's.

## Features

| Feature | How it works |
| --- | --- |
| **Automatic scanning, 3×/day** | A central GitHub Action scrapes Greenhouse / Lever / Ashby boards and matches openings to every registered user |
| **Multi-dimension AI evaluation** | Each job gets a weighted score across skills, seniority, location, growth and comp fit — plus concrete gaps, a salary estimate, and a one-line verdict |
| **Bring your own key** | Scoring runs on *your* Anthropic API key. Platform cost: zero |
| **CV upload → instant profile** | Drop a PDF/DOCX résumé in the wizard; roles, experience and locations are extracted client-side |
| **Rich tracker** | Status pipeline, interview rounds, notes, favorites, analytics — synced to your account |
| **Recruiter outreach** | Per-job contact card (Clay-style) with a one-click email pre-filled with a personalized opener |
| **Interview prep** | Company dossier on demand, mock interviews — including **voice interviews** (ElevenLabs optional) |
| **Cover letters & tailored CV** | Generated per job, keyword-aware, print-to-PDF |
| **Emotional support** | Job hunting is hard. A built-in empathetic chat and a daily check-in keep you going |
| **Hebrew + English** | Full RTL support, language toggle everywhere |
| **Liveness checks** | Tracked jobs whose posting disappeared get flagged automatically |

## Quick start (user)

1. Open the [landing page](https://omriki55.github.io/omrigonenjobfinder/landing.html)
2. Click **Get Started** → pick a username & password
3. Fill the wizard (or upload your CV) and paste your [Anthropic API key](https://console.anthropic.com)
4. Done. Jobs appear in **My Jobs** after the next scan — automatically.

That's the whole setup. Nothing to install.

## Architecture

```
                    ┌────────────────────────────┐
   users ──────────▶│  Static site (GitHub Pages)│
                    │  landing / app / admin     │
                    └──────────┬─────────────────┘
                               │ supabase-js (RLS)
                    ┌──────────▼─────────────────┐
                    │  Supabase (free tier)      │
                    │  auth · profiles · jobs    │
                    │  user_secrets · user_state │
                    │  events · site_content    │
                    └──────────▲─────────────────┘
                               │ service role
                    ┌──────────┴─────────────────┐
                    │  GitHub Action (cron 3×/day)│
                    │  scrape boards → score with │
                    │  each user's own API key →  │
                    │  upsert per-user jobs       │
                    └─────────────────────────────┘
```

- **Frontend:** vanilla HTML/CSS/JS, single-file pages, no build step
- **Auth & data:** Supabase with row-level security — every user sees only their own rows
- **Worker:** `job_search/saas_pipeline.py`, stdlib + `anthropic` only
- **Models:** Claude Haiku for scoring (cheap, fast), user-side chat uses the user's key

## Self-hosting

Want your own instance with your own user base? See **[docs/SELF-HOST.md](docs/SELF-HOST.md)** — fork, create a free Supabase project, run one SQL file, set two repo secrets. ~15 minutes.

## Security & privacy

- User API keys are stored in a table readable **only by their owner** (RLS); the scan worker accesses them server-side via service role
- No personal data in the repo — the public site is a shell; everything user-specific lives behind auth
- See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

## Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Good first issues: new board providers (Workable, Comeet), translations, tracker features.

## License

[MIT](LICENSE)

---

*Built with [Claude](https://claude.com) · An experiment in giving candidates the same AI leverage companies have.*
