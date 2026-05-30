import argparse
import base64
import os
import pickle
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from groq import Groq
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import config
import analyzer
import prompts

# ─── Auth ─────────────────────────────────────────────────────────────────────

def get_services():
    creds = None
    token_file = "token.pickle"

    if os.path.exists(token_file):
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.GOOGLE_CREDENTIALS_FILE, config.GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)

    sheets  = build("sheets",  "v4",  credentials=creds)
    docs    = build("docs",    "v1",  credentials=creds)
    gmail   = build("gmail",   "v1",  credentials=creds)
    drive   = build("drive",   "v3",  credentials=creds)
    return sheets, docs, gmail, drive


# ─── Sheets ───────────────────────────────────────────────────────────────────

def read_tab(sheets, tab_name: str) -> list:
    result = sheets.spreadsheets().values().get(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{tab_name}!A:Z"
    ).execute()
    return result.get("values", [])


def ensure_reports_tab(sheets):
    """Create Reports tab with headers if it doesn't exist."""
    meta = sheets.spreadsheets().get(
        spreadsheetId=config.GOOGLE_SHEET_ID
    ).execute()
    tabs = [s["properties"]["title"] for s in meta["sheets"]]

    if config.TAB_REPORTS not in tabs:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": config.TAB_REPORTS}}}]}
        ).execute()
        sheets.spreadsheets().values().update(
            spreadsheetId=config.GOOGLE_SHEET_ID,
            range=f"{config.TAB_REPORTS}!A1",
            valueInputOption="RAW",
            body={"values": [["Date", "Doc Title", "Doc URL", "Revenue This Week", "Leads", "Conversion Rate", "Emailed To"]]}
        ).execute()


def log_report(sheets, doc_title: str, doc_url: str, data: dict):
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        doc_title,
        doc_url,
        f"₱{data['revenue']['this_week_total']:,.2f}",
        data["leads"]["total"],
        f"{data['leads']['conversion_rate']}%",
        config.REPORT_RECIPIENT,
    ]
    sheets.spreadsheets().values().append(
        spreadsheetId=config.GOOGLE_SHEET_ID,
        range=f"{config.TAB_REPORTS}!A:G",
        valueInputOption="RAW",
        body={"values": [row]}
    ).execute()


# ─── Groq ─────────────────────────────────────────────────────────────────────

def call_groq(client: Groq, prompt: str, max_tokens: int = 600) -> str:
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()


# ─── Google Docs ──────────────────────────────────────────────────────────────

def create_report_doc(docs, drive, title: str, sections: dict) -> tuple[str, str]:
    """Build a formatted Google Doc report. Returns (doc_id, doc_url)."""

    doc = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    if config.GOOGLE_DOCS_FOLDER_ID:
        drive.files().update(
            fileId=doc_id,
            addParents=config.GOOGLE_DOCS_FOLDER_ID,
            removeParents="root",
            fields="id, parents"
        ).execute()

    r = sections["revenue"]
    l = sections["leads"]
    t = sections["tasks"]

    # Build full document text
    lines = [
        f"DAILY BUSINESS REPORT\n",
        f"{sections['date']}\n",
        f"The Label AI Studios PH\n\n",
        "━" * 50 + "\n\n",

        "EXECUTIVE SUMMARY\n\n",
        sections["summary"] + "\n\n",

        "━" * 50 + "\n\n",

        "KEY METRICS\n\n",
        f"• Revenue this week:    ₱{r['this_week_total']:,.2f}\n",
        f"• Revenue last week:    ₱{r['last_week_total']:,.2f}\n",
        f"• Week-over-week:       {r['trend'].upper()} {r['trend_pct']}%\n",
        f"• Total leads:          {l['total']}\n",
        f"• Converted:            {l['converted']}\n",
        f"• Conversion rate:      {l['conversion_rate']}%\n",
        f"• New leads this week:  {l['this_week_leads']}\n",
        f"• Tasks completed:      {t['completed']}/{t['total']} ({t['completion_rate']}%)\n",
        f"• Overdue tasks:        {len(t['overdue'])}\n\n",

        "━" * 50 + "\n\n",

        "TOP 3 WINS THIS WEEK\n\n",
        sections["wins"] + "\n\n",

        "━" * 50 + "\n\n",

        "TOP 3 THINGS NEEDING ATTENTION\n\n",
        sections["attention"] + "\n\n",

        "━" * 50 + "\n\n",

        "REVENUE BY SOURCE\n\n",
    ]

    for source, amount in sorted(r["by_source"].items(), key=lambda x: -x[1]):
        lines.append(f"• {source}: ₱{amount:,.2f}\n")

    lines += [
        "\n",
        "LEAD SOURCES\n\n",
    ]
    for source, count in sorted(l["by_source"].items(), key=lambda x: -x[1]):
        lines.append(f"• {source}: {count} leads\n")

    if t["overdue"]:
        lines += ["\n", "OVERDUE TASKS\n\n"]
        for item in t["overdue"]:
            lines.append(f"• {item['task']} (due {item['due']})\n")

    lines += [
        "\n",
        "━" * 50 + "\n\n",
        f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "The Label AI Studios PH · AI Ops · No-Code · 🇵🇭\n",
    ]

    full_text = "".join(lines)

    # Insert text
    requests = [{"insertText": {"location": {"index": 1}, "text": full_text}}]
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

    # Apply heading styles
    doc_content = docs.documents().get(documentId=doc_id).execute()
    style_requests = []

    heading_texts = [
        "DAILY BUSINESS REPORT",
        "EXECUTIVE SUMMARY",
        "KEY METRICS",
        "TOP 3 WINS THIS WEEK",
        "TOP 3 THINGS NEEDING ATTENTION",
        "REVENUE BY SOURCE",
        "LEAD SOURCES",
        "OVERDUE TASKS",
    ]

    content = doc_content.get("body", {}).get("content", [])
    for element in content:
        paragraph = element.get("paragraph", {})
        for elem in paragraph.get("elements", []):
            text_run = elem.get("textRun", {})
            text = text_run.get("content", "").strip()
            if text in heading_texts:
                start = elem.get("startIndex", 1)
                end = elem.get("endIndex", start + len(text))
                style = "TITLE" if text == "DAILY BUSINESS REPORT" else "HEADING_2"
                style_requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": start, "endIndex": end},
                        "paragraphStyle": {"namedStyleType": style},
                        "fields": "namedStyleType",
                    }
                })

    if style_requests:
        docs.documents().batchUpdate(documentId=doc_id, body={"requests": style_requests}).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return doc_id, doc_url


# ─── Gmail ────────────────────────────────────────────────────────────────────

def send_email(gmail, subject: str, body: str, doc_url: str):
    html_body = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <div style="background: #7C3AED; padding: 24px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 20px;">📊 Daily Business Report</h1>
    <p style="color: #C4B5FD; margin: 4px 0 0 0; font-size: 13px;">The Label AI Studios PH</p>
  </div>
  <div style="background: #f9f9f9; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb;">
    <pre style="font-family: Arial, sans-serif; white-space: pre-wrap; font-size: 14px; line-height: 1.6; color: #1f2937;">{body}</pre>
    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e5e7eb;">
      <a href="{doc_url}" style="background: #7C3AED; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px;">
        📄 Open Full Report in Google Docs →
      </a>
    </div>
    <p style="margin-top: 20px; font-size: 11px; color: #9ca3af;">
      AI Ops · No-Code · 🇵🇭 Filipino-built
    </p>
  </div>
</div>
"""
    message = MIMEMultipart("alternative")
    message["to"] = config.REPORT_RECIPIENT
    message["from"] = config.MY_EMAIL
    message["subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail.users().messages().send(userId="me", body={"raw": raw}).execute()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AI Daily Business Report — The Label AI Studios PH"
    )
    parser.add_argument("--send-report", action="store_true", help="Generate and email the report")
    args = parser.parse_args()

    if not args.send_report:
        print("Usage: python main.py --send-report")
        return

    print("\n📊 AI Daily Business Report Generator")
    print("   The Label AI Studios PH\n")

    groq_client = Groq(api_key=config.GROQ_API_KEY)
    sheets_svc, docs_svc, gmail_svc, drive_svc = get_services()

    # Step 1: Read Google Sheets data
    print("📥 Reading Google Sheets data...")
    revenue_rows = read_tab(sheets_svc, config.TAB_REVENUE)
    leads_rows   = read_tab(sheets_svc, config.TAB_LEADS)
    tasks_rows   = read_tab(sheets_svc, config.TAB_TASKS)
    print(f"   ✓ Revenue: {len(revenue_rows)-1} rows | Leads: {len(leads_rows)-1} | Tasks: {len(tasks_rows)-1}")

    # Step 2: Analyze data
    print("\n🔢 Analyzing data...")
    rev_data   = analyzer.analyze_revenue(revenue_rows)
    leads_data = analyzer.analyze_leads(leads_rows)
    tasks_data = analyzer.analyze_tasks(tasks_rows)
    summary_data = analyzer.build_summary_data(rev_data, leads_data, tasks_data)
    print("   ✓ Analysis complete")

    # Step 3: Generate AI content
    print("\n🧠 Generating AI report content with Groq...")
    print("   → Executive summary...")
    summary = call_groq(groq_client, prompts.executive_summary_prompt(summary_data), max_tokens=600)
    print("   → Wins...")
    wins = call_groq(groq_client, prompts.wins_prompt(summary_data), max_tokens=200)
    print("   → Attention items...")
    attention = call_groq(groq_client, prompts.attention_prompt(summary_data), max_tokens=200)
    print("   ✓ Content generated")

    # Step 4: Build doc sections
    sections = {
        "date": summary_data["date"],
        "summary": summary,
        "wins": wins,
        "attention": attention,
        "revenue": rev_data,
        "leads": leads_data,
        "tasks": tasks_data,
    }

    # Step 5: Create Google Doc
    today_str = datetime.now().strftime("%Y-%m-%d")
    doc_title = f"Daily Report — The Label AI Studios PH — {today_str}"
    print(f"\n📄 Creating Google Doc...")
    doc_id, doc_url = create_report_doc(docs_svc, drive_svc, doc_title, sections)
    print(f"   ✓ Doc created: {doc_url}")

    # Step 6: Build email body (plain text summary)
    email_body = f"""Good morning, Rana! Here's your daily business snapshot.

{summary}

TOP 3 WINS
{wins}

NEEDS ATTENTION
{attention}

KEY NUMBERS
• Revenue this week: ₱{rev_data['this_week_total']:,.2f} ({rev_data['trend'].upper()} {rev_data['trend_pct']}%)
• Lead conversion rate: {leads_data['conversion_rate']}%
• Tasks completed: {tasks_data['completed']}/{tasks_data['total']}
• Overdue tasks: {len(tasks_data['overdue'])}

Full report with all data: {doc_url}
"""

    # Step 7: Send email
    print(f"\n📧 Sending email to {config.REPORT_RECIPIENT}...")
    subject = f"📊 Daily Report — {summary_data['date']} | ₱{rev_data['this_week_total']:,.0f} this week | {leads_data['conversion_rate']}% conversion"
    send_email(gmail_svc, subject, email_body, doc_url)
    print("   ✓ Email sent")

    # Step 8: Log to Reports tab
    print("\n📋 Logging to Google Sheets...")
    ensure_reports_tab(sheets_svc)
    log_report(sheets_svc, doc_title, doc_url, summary_data)
    print("   ✓ Logged")

    # Done
    print(f"\n✅ DONE!")
    print(f"   Report: {doc_title}")
    print(f"   Doc:    {doc_url}")
    print(f"   Email:  Sent to {config.REPORT_RECIPIENT}\n")


if __name__ == "__main__":
    main()
