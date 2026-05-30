# AI Daily Business Report Generator
### The Label AI Studios PH

Reads your Google Sheets data every morning, analyzes it with Groq AI, writes a clean business report, saves it to Google Docs, and emails it to you — automatically.

---

## What It Generates

- **Executive Summary** — 3-paragraph AI analysis of business health
- **Key Metrics** — Revenue, leads, conversion rate, task completion
- **Top 3 Wins** — What went well this week
- **Top 3 Attention Items** — What needs action today
- **Revenue by Source** — Breakdown of where money came from
- **Overdue Tasks** — What's fallen behind

All saved to a Google Doc + emailed with a styled HTML email.

---

## Google Sheet Setup

Create a Google Sheet with **4 tabs** with these exact names:

### Tab 1: Revenue
| date | source | amount |
|---|---|---|
| 2026-05-30 | Gumroad | 199 |
| 2026-05-30 | Done-for-you | 5000 |

### Tab 2: Leads
| date | name | status | source |
|---|---|---|---|
| 2026-05-30 | Maria Santos | hot | Instagram |
| 2026-05-29 | Juan Cruz | converted | LinkedIn |

Status values: `hot`, `warm`, `cold`, `converted`, `lost`

### Tab 3: Tasks
| task | status | due date |
|---|---|---|
| Build AI inbox agent | completed | 2026-05-30 |
| Post carousel | pending | 2026-05-31 |

Status values: `completed`, `done`, `pending`, `in progress`

### Tab 4: Reports
*(Auto-created by the script)*

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get your free Groq API key
1. Go to **console.groq.com**
2. Sign up free
3. API Keys → Create API Key → Copy it

### 3. Set up Google API credentials
1. Go to **console.cloud.google.com**
2. Create project → Enable:
   - Google Sheets API
   - Google Docs API
   - Google Drive API
   - Gmail API
3. Credentials → OAuth 2.0 Client ID → Desktop app
4. Download JSON → rename to `credentials.json`
5. Place in this folder

### 4. Configure .env
```bash
cp .env.example .env
```
Fill in:
```
GROQ_API_KEY=gsk_...
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_DOCS_FOLDER_ID=your_folder_id
MY_EMAIL=your@gmail.com
REPORT_RECIPIENT=your@gmail.com
```

---

## Usage

```bash
python main.py --send-report
```

First run opens browser for Google auth (once only).

**Output:**
```
✅ DONE!
   Report: Daily Report — The Label AI Studios PH — 2026-05-30
   Doc:    https://docs.google.com/document/d/...
   Email:  Sent to your@gmail.com
```

---

## Schedule Daily (8AM every morning)

```bash
crontab -e
```
Add:
```
0 8 * * * cd ~/Desktop/label-ai-daily-report && python main.py --send-report
```

---

## File Structure
```
label-ai-daily-report/
├── main.py        # Core agent — reads, analyzes, creates doc, emails
├── analyzer.py    # Data analysis — revenue, leads, tasks metrics
├── prompts.py     # Groq prompts for summary, wins, attention
├── config.py      # Settings from .env
├── .env.example   # API key template
├── requirements.txt
└── README.md
```

---

## Built by The Label AI Studios PH
Free AI systems for businesses. Filipino-built. 🇵🇭
