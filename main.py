import os
import time
import json

import gspread

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from google.oauth2.service_account import Credentials


# ============================================================
# CONFIGURATION
# ============================================================

GOOGLE_SHEET_ID = "1ul2El68A2ofpZg4qXo79GK2NDHY__jzTmGojV5oEpVI"

GOOGLE_WORKSHEET_NAME = "Form Responses 1"

CACHE_TIME = 60


# ============================================================
# FASTAPI
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
# GOOGLE SHEETS CONNECTION
# ============================================================

def connect_to_google_sheet():

    # Render will provide this environment variable.
    credentials_json = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT"
    )

    if not credentials_json:

        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT environment variable is not set."
        )


    try:

        credentials_info = json.loads(
            credentials_json
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT contains invalid JSON."
        ) from error


    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]


    credentials = (
        Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes
        )
    )


    client = gspread.authorize(
        credentials
    )


    spreadsheet = client.open_by_key(
        GOOGLE_SHEET_ID
    )


    worksheet = spreadsheet.worksheet(
        GOOGLE_WORKSHEET_NAME
    )


    return worksheet


# ============================================================
# DATA CLEANING
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
# READ STUDENTS
# ============================================================

def read_students():

    worksheet = connect_to_google_sheet()

    rows = worksheet.get_all_records()

    students = []


    for row_number, row in enumerate(
        rows,
        start=2
    ):

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


            # =================================================
            # PRIVATE INFORMATION
            # =================================================

            "student_id": clean(
                row.get(
                    "SRM Registration / Student ID"
                )
            ),

            "whatsapp": clean(
                row.get(
                    "WhatsApp Number"
                )
            ),


            # =================================================
            # BASIC INFORMATION
            # =================================================

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


            # =================================================
            # COMMUNITY INFORMATION
            # =================================================

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


            # =================================================
            # PRIVACY SETTINGS
            # =================================================

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


        students.append(
            student
        )


    return students


# ============================================================
# PRIVACY CHECK
# ============================================================

def field_is_visible(
    student,
    field
):

    # Member doesn't want to be discoverable.

    if student["discoverable"].startswith(
        "No"
    ):

        return False


    # Only display fields explicitly selected
    # by the member.

    return field in student["visible_fields"]


# ============================================================
# CREATE PUBLIC PROFILE
# ============================================================

def create_public_profile(
    student
):

    profile = {

        "id": student["id"],

        "name": (
            student["name"]
            if field_is_visible(
                student,
                "Name"
            )
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


    # ========================================================
    # BRANCH
    # ========================================================

    if field_is_visible(
        student,
        "Branch / Course"
    ):

        profile["branch"] = (
            student["branch"]
        )


    # ========================================================
    # SECTION
    # ========================================================

    if field_is_visible(
        student,
        "Section"
    ):

        profile["section"] = (
            student["section"]
        )


    # ========================================================
    # HOMETOWN
    # ========================================================

    if field_is_visible(
        student,
        "Hometown"
    ):

        profile["hometown"] = (
            student["hometown"]
        )


    # ========================================================
    # SKILLS
    # ========================================================

    if field_is_visible(
        student,
        "Skills"
    ):

        profile["skills"] = (
            student["skills"]
        )


    # ========================================================
    # INTERESTS
    # ========================================================

    if field_is_visible(
        student,
        "Interests"
    ):

        profile["interests"] = (
            student["interests"]
        )


    # ========================================================
    # BIO
    # ========================================================

    if field_is_visible(
        student,
        "About Me"
    ):

        profile["bio"] = (
            student["bio"]
        )


    # ========================================================
    # INSTAGRAM
    # ========================================================

    if field_is_visible(
        student,
        "Instagram"
    ):

        profile["instagram"] = (
            student["instagram"]
        )


    # ========================================================
    # LINKEDIN
    # ========================================================

    if field_is_visible(
        student,
        "LinkedIn"
    ):

        profile["linkedin"] = (
            student["linkedin"]
        )


    return profile


# ============================================================
# GET MEMBERS WITH CACHE
# ============================================================

def get_members():

    global cached_members
    global last_update


    current_time = time.time()


    # Use cached data if it is still fresh.

    if (
        current_time - last_update
        < CACHE_TIME
    ):

        return cached_members


    students = read_students()


    cached_members = [

        create_public_profile(
            student
        )

        for student in students

    ]


    last_update = current_time


    return cached_members


# ============================================================
# WEBSITE
# ============================================================

@app.get("/")
def home(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="web.html"
    )


# ============================================================
# PUBLIC MEMBER API
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
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
