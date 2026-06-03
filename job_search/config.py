SEARCH_QUERIES = [
    "revenue operations",
    "head of revenue operations",
    "revops",
    "gtm engineer",
    "head of growth",
    "growth manager",
    "marketing operations",
    "sales operations",
]

GREENHOUSE_COMPANIES = [
    "monday", "wix", "fiverr", "similarweb", "gong", "outreach",
    "salesloft", "hubspot", "notion", "airtable", "mixpanel",
    "amplitude", "segment", "intercom", "braze", "drift",
    "clari", "chorus", "highspot", "seismic"
]

LEVER_COMPANIES = [
    "ironSource", "payoneer", "walkme", "varonis", "cyberark",
    "checkmarx", "lemonade", "rapyd", "tipalti",
    "salto", "buildots", "riskified", "lightspin"
]

SCORING_PROMPT = """
You are evaluating a job listing for Omri Gonen, a senior RevOps/GTM executive with 15+ years in B2B SaaS.
CANDIDATE PROFILE:
- Target roles: Head of Revenue Operations, RevOps Manager, GTM Engineer, Head of Growth, Marketing Operations Lead
- Strong fit: HubSpot admin, Salesforce admin, B2B SaaS, Fintech, AI-native GTM, CAC/LTV, pipeline forecasting
- Weak fit: pure media buying, e-commerce D2C only, junior/IC roles, companies under 30 people
- Location: Remote/Hybrid globally OK. In Israel: Tel Aviv area and Gush Dan OK. Reject: Rehovot south, Modiin, Haifa.
JOB LISTING:
Company: {company}
Role: {title}
Location: {location}
Description: {description}
Respond in JSON:
{{
  "fit_score": <integer 1-10>,
  "score_reason": "<1-2 sentences explaining the score>",
  "ai_opener": "<2-3 sentence personalized cold outreach opener Omri could send to a contact at this company — professional, specific to what the company does, not generic>",
  "location_ok": <true/false — false if location violates hard constraints>
}}
Score 8-10: Strong match on role, level, and stack.
Score 5-7: Partial match — right domain but wrong level or missing key signals.
Score 1-4: Poor match.
If location_ok is false, set fit_score to 0.
"""

SHEET_COLUMNS = [
    "Company", "Location", "Role Title", "Job URL", "Job Type",
    "Contact Name", "Contact LinkedIn", "Fit Score", "Score Reason",
    "Status", "AI Opener", "Date Added"
]

SHEET_NAME = "Pipeline"
MIN_FIT_SCORE = 4

# Fast + cheap model for scoring
SCORING_MODEL = "claude-haiku-4-5-20251001"
