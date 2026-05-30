import os
from dotenv import load_dotenv

load_dotenv()

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"

# Google
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_DOCS_FOLDER_ID = os.getenv("GOOGLE_DOCS_FOLDER_ID")
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
]

# Email
MY_EMAIL = os.getenv("MY_EMAIL")
REPORT_RECIPIENT = os.getenv("REPORT_RECIPIENT")

# Sheet tab names
TAB_REVENUE = "Revenue"
TAB_LEADS = "Leads"
TAB_TASKS = "Tasks"
TAB_REPORTS = "Reports"
