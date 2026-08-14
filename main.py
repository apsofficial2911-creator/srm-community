import os
import time

import gspread

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from google.oauth2.service_account import Credentials
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


# ============================================================
# CONFIGURATION
# ============================================================

GOOGLE_SHEET_ID = "1ul2El68A2ofpZg4qXo79GK2NDHY__jzTmGojV5oEpVI"

GOOGLE_WORKSHEET_NAME = "Form Responses 1"

GOOGLE_CREDENTIALS_FILE = "service-account.json"

CACHE_TIME = 60


# ============================================================
# FASTAPI SETUP
# ============================================================

app = FastAPI(
    title="SRM Ramapuram Member Directory"
)

templates = Jinja2Templates(
    directory="templates"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ============================================================
# CACHE
# ============================================================

cached_members = []

last_update = 0


# ============================================================
# CONNECT TO GOOGLE SHEETS
# ============================================================

def connect_to_google_sheet():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(
        GOOGLE_SHEET_ID
    )

    worksheet = spreadsheet.worksheet(
        GOOGLE_WORKSHEET_NAME
    )

    return worksheet


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean(value):

    if value is None:
        return ""

    return str(value).strip()


def split_answers(value):

    if not value:
        return []

    return [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]


# ============================================================
# READ GOOGLE SHEET
# ============================================================

def read_students():

    worksheet = connect_to_google_sheet()

    rows = worksheet.get_all_records()

    students = []

    for row_number, row in enumerate(rows, start=2):

        name = clean(
            row.get("Full Name")
        )

        # Ignore completely empty rows
        if not name:
            continue


        student = {

            "id": row_number,

            "name": name,

            "nickname": clean(
                row.get(
                    "Preferred Name / Nickname"
                )
            ),

            # PRIVATE
            "student_id": clean(
                row.get(
                    "SRM Registration / Student ID"
                )
            ),

            # PRIVATE
            "whatsapp": clean(
                row.get(
                    "WhatsApp Number"
                )
            ),

            "branch": clean(
                row.get(
                    "Branch / Course"
                )
            ),

            "section": clean(
                row.get(
                    "Section"
                )
            ),

            "student_type": clean(
                row.get(
                    "Student Type"
                )
            ),

            "hometown": clean(
                row.get(
                    "Hometown"
                )
            ),

            "skills": split_answers(
                row.get(
                    "Skills"
                )
            ),

            "interests": split_answers(
                row.get(
                    "Interests / Hobbies"
                )
            ),

            "bio": clean(
                row.get(
                    "About Me"
                )
            ),

            "instagram": clean(
                row.get(
                    "Instagram Username"
                )
            ),

            "linkedin": clean(
                row.get(
                    "LinkedIn Profile"
                )
            ),

            # PRIVACY SETTINGS
            "visible_fields": split_answers(
                row.get(
                    "Information I am comfortable displaying to batch members"
                )
            ),

            "discoverable": clean(
                row.get(
                    "Do you want your profile to be discoverable by other batch members?"
                )
            )
        }

        students.append(student)

    return students


# ============================================================
# PRIVACY FILTER
# ============================================================

def field_is_visible(student, field):

    # If member doesn't want to be discoverable
    if student["discoverable"].startswith("No"):

        return False

    # Only display fields explicitly selected
    return field in student["visible_fields"]


def create_public_profile(student):

    profile = {

        "id": student["id"],

        "name": (
            student["name"]
            if field_is_visible(student, "Name")
            else "Private Member"
        ),

        "branch": "",

        "section": "",

        "hometown": "",

        "skills": [],

        "interests": [],

        "bio": "",

        "instagram": "",

        "linkedin": ""
    }


    if field_is_visible(
        student,
        "Branch / Course"
    ):

        profile["branch"] = student["branch"]


    if field_is_visible(
        student,
        "Section"
    ):

        profile["section"] = student["section"]


    if field_is_visible(
        student,
        "Hometown"
    ):

        profile["hometown"] = student["hometown"]


    if field_is_visible(
        student,
        "Skills"
    ):

        profile["skills"] = student["skills"]


    if field_is_visible(
        student,
        "Interests"
    ):

        profile["interests"] = student["interests"]


    if field_is_visible(
        student,
        "About Me"
    ):

        profile["bio"] = student["bio"]


    if field_is_visible(
        student,
        "Instagram"
    ):

        profile["instagram"] = student["instagram"]


    if field_is_visible(
        student,
        "LinkedIn"
    ):

        profile["linkedin"] = student["linkedin"]


    return profile


# ============================================================
# GET MEMBERS
# ============================================================

def get_members():

    global cached_members
    global last_update

    current_time = time.time()


    # Use cached data
    if current_time - last_update < CACHE_TIME:

        return cached_members


    students = read_students()


    cached_members = [
        create_public_profile(student)
        for student in students
    ]


    last_update = current_time


    return cached_members


# ============================================================
# WEBSITE
# ============================================================

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="web.html"
    )

@app.get("/test-sheet")
def test_sheet():

    worksheet = connect_to_google_sheet()

    rows = worksheet.get_all_records()

    return {
        "number_of_rows": len(rows),
        "rows": rows
    }
@app.get("/test-sheet")
def test_sheet():

    worksheet = connect_to_google_sheet()

    rows = worksheet.get_all_records()

    return {
        "number_of_rows": len(rows),
        "rows": rows
    }
# ============================================================
# API
# ============================================================

@app.get("/api/members")
def api_members():

    return get_members()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "running"
    }


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

