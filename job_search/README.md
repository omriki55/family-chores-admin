# Job Search Automation Pipeline

Automated daily pipeline that scrapes job listings, scores them against a candidate profile using Claude AI, writes results to Google Sheets, and sends a daily summary email.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Google Service Account
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable **Google Sheets API** + **Google Drive API**
3. Create a Service Account → Download JSON → save as `credentials/google_service_account.json`
4. Share the Google Sheet with the service account email (Editor access)

### 3. Gmail App Password
1. Enable 2FA on your Google Account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Generate a password for "Mail" → paste into `.env`

### 4. Anthropic API Key
Get from [console.anthropic.com](https://console.anthropic.com) → paste into `.env`

### 5. Configure environment
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 6. Run manually
```bash
python main.py
```

### 7. Dry run (no writes, no email)
```bash
python main.py --dry-run
```

### 8. Schedule daily run (cron)
```
0 7 * * * cd /path/to/job_search && python main.py >> logs/pipeline.log 2>&1
```

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | Orchestrator — runs full pipeline |
| `config.py` | Constants, search queries, prompt template |
| `scrapers/` | One scraper per job source |
| `scorer.py` | Claude API scoring (Haiku model) |
| `sheets.py` | Google Sheets read/write via gspread |
| `email_summary.py` | Daily HTML email via Gmail SMTP |
| `deduplication.py` | URL + fuzzy-match deduplication |

## Google Sheet Columns

| Column | Description |
|--------|-------------|
| Company | Company name |
| Location | Job location |
| Role Title | Exact job title |
| Job URL | Direct link |
| Job Type | Full-time / Part-time / Contract |
| Contact Name | Filled manually |
| Contact LinkedIn | Filled manually |
| Fit Score | 1–10 from Claude |
| Score Reason | Brief explanation |
| Status | Default: "לפנות" |
| AI Opener | Cold outreach opener from Claude |
| Date Added | ISO date YYYY-MM-DD |

## Fit Score Thresholds

- **8–10**: Strong match → highlighted green in email
- **5–7**: Partial match → highlighted yellow
- **< 4**: Filtered out, not written to sheet
- **0**: Location constraint violated → filtered out
