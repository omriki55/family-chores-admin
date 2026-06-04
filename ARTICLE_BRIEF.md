# 📝 מסמך תכנון — מאמר לינקדאין: "איך בניתי מנוע חיפוש עבודה אוטונומי עם AI"

> מסמך זה מרכז את כל המידע הדרוש לכתיבת המאמר. נוצר ב-04/06/2026.
> שפה: עברית · זווית: סיפור אישי + How-to + מנהיגות מחשבתית · קוד: פתוח לגמרי · נתונים: אמיתיים ושקופים

---

## 1. הנתונים האמיתיים (שקיפות מלאה)

### ציר הזמן
- **התחלה:** יום ראשון (≈ 25/05/2026)
- **היום:** 04/06/2026 (≈ 10 ימים)

### תוצאות מדידות
| מדד | מספר |
|-----|------|
| סה"כ משרות בטראקר | **52** |
| משרות שהוגשו (applied) | **25** |
| ראיונות שהתקיימו | **5** |
| ראיונות שעברו בהצלחה | **3** (Sauce, Gambit, Neon) |
| דחיות | **3** (Cyolo, Agora, NEEMA) |
| משרות שנמצאו אוטומטית ע"י הפייפליין | **13** |
| מיילי אישור הגשה שנקלטו (Gmail) | **16+** |

### 5 הראיונות (אמיתי)
| חברה | תאריך | מראיין | תוצאה |
|------|-------|--------|-------|
| Neon Security | 27/05 | Inna | ✅ עבר |
| Sauce | 01/06 | Vladimir Slavkovski | ✅ עבר |
| Gambit Security | 03/06 | Mor Ben-Kalifa | ✅ עבר |
| SmartUp/Tickchak | 03/06 | Yair Fradkin | ⏳ ממתין |
| Plus500 | 04/06 | Plus500 Recruiting | ⏳ היום |

### חברות אמיתיות שהגישו אליהן (דוגמאות)
Cyolo, Connecteam, AppsFlyer, MAËLYS, Base44, OurRitual, Playtika, SysAid, Swimm, Ocean Security, ZyG, WalkMe, Team8/Charm, MDalgorithms, NEEMA, Agora.

---

## 2. עלות בטוקנים — שקיפות + הסתייגות

⚠️ **חשוב:** אין לי גישה ל-usage API מצטבר, אז זה **אומדן** ולא מספר מדויק.
המספר המדויק זמין ב-[console.anthropic.com → Usage](https://console.anthropic.com).

### פירוק האומדן
| רכיב | מודל | אומדן טוקנים לריצה |
|------|------|---------------------|
| חיפוש משרות (web_search ×8) | Opus 4.8 | ~30K–50K input + ~6K output |
| ניקוד משרות (×14) | Haiku 4.5 | ~16K input + ~7K output |
| **סה"כ לריצת פייפליין אחת** | | **~60K–80K טוקנים** |
| פיתוח אינטראקטיבי (כל הסשנים) | Sonnet/Opus | הרכיב הדומיננטי — קריאת קבצים גדולים (HTML 120KB, לוגים 380KB), בנייה, דיבוג |

**להשלמה ב-Cowork:** למשוך את המספר המדויק מ-Console ולהכניס למאמר. זה נתון מנצח לשקיפות.

---

## 3. הארכיטקטורה (לפרק ה-How-to)

```
run_pipeline.py
  ├─ 1. search_jobs()    → Opus 4.8 + web_search tool  → מוצא משרות אמיתיות
  ├─ 2. score_jobs()     → Haiku 4.5  → מנקד 1-10 לפי פרופיל המועמד
  ├─ 3. filter           → fit_score ≥ 4 + location_ok
  ├─ 4. save JSON        → scored_jobs.json (משמר משרות ידניות!)
  ├─ 5. build HTML       → docs/index.html מתבנית
  ├─ 6. git push         → GitHub
  └─ 7. email summary    → Gmail SMTP (אופציונלי)

.github/workflows/
  ├─ job-scan.yml        → cron 3x ביום → מריץ את הפייפליין
  └─ deploy-pages.yml    → push ל-docs/ → GitHub Pages

הצגה: GitHub Pages (קישור קבוע, מתעדכן אוטומטית)
מצב: localStorage בדפדפן (סטטוס, הערות, סבבי ראיונות)
```

### החלטות עיצוב מפתח שכדאי לספר עליהן
1. **scored_jobs.json כמקור אמת יחיד** — הפייפליין והטראקר קוראים ממנו
2. **`initial_status` / `initial_rounds`** — מאפשר להזין דאטה ידני שלא נמחק בסריקה
3. **הבאג שתפסנו**: הפייפליין מחק משרות ידניות → תוקן לשמר אותן
4. **GitHub Pages ולא githack** — קישור אמין שמתעדכן אוטומטית
5. **סבבי ראיונות מובנים** — תאריך, מראיין, שלב, תוצאה, צבע לפי סטטוס

---

## 4. הפרומפטים המלאים (לחשיפה במאמר)

### פרומפט חיפוש (search_jobs)
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

Return 8-15 real positions as JSON array with:
{company, title, location, url, job_type, posted, description}
```

### פרומפט ניקוד (score_job)
```
You are evaluating job listings for [שם], a [תפקיד] with [נסיון].
CANDIDATE PROFILE: [target roles, strong fit, weak fit, location OK/reject]

Respond in JSON ONLY:
{fit_score (1-10), score_reason, ai_opener, location_ok}
If location_ok is false, set fit_score to 0.
```

> **טיפ למאמר:** הפרדת המודלים — Opus לחיפוש (איכות), Haiku לניקוד (זול ומהיר) — זו החלטת עלות חכמה.

---

## 5. מבנה המאמר המוצע

**כותרת מוצעת:** "חיפשתי עבודה. אז בניתי לעצמי מנוע AI שעושה את זה בשבילי — והנה הקוד."

1. **הפתיח (Hook)** — "ביום ראשון התחלתי לחפש עבודה. תוך 10 ימים: 25 הגשות, 5 ראיונות, 3 שעברתי — בלי לפתוח לוח דרושים ידנית פעם אחת."
2. **הבעיה** — חיפוש עבודה ידני = שעות בזבוז, פספוס משרות, חוסר מעקב
3. **הרעיון** — סוכן AI שסורק, מנקד, ומעדכן טראקר אוטומטית 3x ביום
4. **הביצוע (How-to)** — הארכיטקטורה + הפרומפטים (חשיפה מלאה)
5. **השקיפות** — המספרים האמיתיים + עלות הטוקנים
6. **הלקחים** — הבאגים, ההחלטות, מה הייתי עושה אחרת
7. **תעשו את זה בעצמכם** — קישור ל-repo + הפרומפטים להעתקה
8. **CTA** — "מי שרוצה את התבנית — תכתבו לי / ה-repo פתוח"

---

## 6. מה צריך להשלים ב-Cowork
- [ ] מספר טוקנים מדויק מ-Console
- [ ] להפוך את ה-repo לציבורי (אם עוד לא) + ניקוי מידע רגיש
- [ ] סקרינשוטים של הטראקר
- [ ] גרסה מקוצרת לפוסט לינקדאין (3-4 פסקאות) + גרסה ארוכה למאמר
- [ ] החלטה: לכלול את ה-AI openers שנוצרו? (דוגמה חזקה ליכולת)
