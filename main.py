import os
import json
import time

import gspread

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from google.oauth2.service_account import Credentials


# =====================================================
# CONFIGURATION
# =====================================================

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

GOOGLE_WORKSHEET_NAME = os.environ.get(
    "GOOGLE_WORKSHEET_NAME",
    "Form Responses 1"
)

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_JSON"
)

CACHE_TIME = 60




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


# =====================================================
# CACHE
# =====================================================

cached_members = []

last_update = 0


# =====================================================
# GOOGLE SHEETS CONNECTION
# =====================================================

def connect_to_google_sheet():

    if not GOOGLE_SHEET_ID:
        raise RuntimeError(
            "GOOGLE_SHEET_ID environment variable is missing."
        )

    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON environment variable is missing."
        )


    try:

        service_account_info = json.loads(
            GOOGLE_SERVICE_ACCOUNT_JSON
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON contains invalid JSON."
        ) from error


    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]


    credentials = (
        Credentials.from_service_account_info(
            service_account_info,
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


# =====================================================
# DATA CLEANING
# =====================================================

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


# =====================================================
# READ GOOGLE SHEET
# =====================================================

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


            # =========================================
            # PRIVATE INFORMATION
            # =========================================

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


            # =========================================
            # PUBLIC-POSSIBLE INFORMATION
            # =========================================

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


            # =========================================
            # PRIVACY SETTINGS
            # =========================================

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


# =====================================================
# PRIVACY CHECK
# =====================================================

def field_is_visible(
    student,
    field
):

    visible_fields = student.get(
        "visible_fields",
        []
    )


    return field in visible_fields


# =====================================================
# CREATE PUBLIC PROFILE
#
# IMPORTANT:
# PRIVATE INFORMATION NEVER ENTERS THIS OBJECT.
# =====================================================

def create_public_profile(student):

    discoverable = student.get(
        "discoverable",
        ""
    ).strip().lower()


    # -----------------------------------------------
    # Hidden profile
    # -----------------------------------------------

    if discoverable.startswith("no"):

        return None


    # -----------------------------------------------
    # EMPTY PUBLIC PROFILE
    # -----------------------------------------------

    profile = {

        "id": student["id"],

        "name": "",

        "nickname": "",

        "branch": "",

        "section": "",

        "hometown": "",

        "skills": [],

        "interests": [],

        "bio": "",

        "instagram": "",

        "linkedin": ""
    }


    # -----------------------------------------------
    # NAME
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Name"
    ):

        profile["name"] = student["name"]


    # -----------------------------------------------
    # NICKNAME
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Preferred Name / Nickname"
    ):

        profile["nickname"] = student["nickname"]


    # -----------------------------------------------
    # BRANCH
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Branch / Course"
    ):

        profile["branch"] = student["branch"]


    # -----------------------------------------------
    # SECTION
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Section"
    ):

        profile["section"] = student["section"]


    # -----------------------------------------------
    # HOMETOWN
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Hometown"
    ):

        profile["hometown"] = student["hometown"]


    # -----------------------------------------------
    # SKILLS
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Skills"
    ):

        profile["skills"] = student["skills"]


    # -----------------------------------------------
    # INTERESTS
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Interests"
    ):

        profile["interests"] = student["interests"]


    # -----------------------------------------------
    # ABOUT ME
    # -----------------------------------------------

    if field_is_visible(
        student,
        "About Me"
    ):

        profile["bio"] = student["bio"]


    # -----------------------------------------------
    # INSTAGRAM
    # -----------------------------------------------

    if field_is_visible(
        student,
        "Instagram"
    ):

        profile["instagram"] = student["instagram"]


    # -----------------------------------------------
    # LINKEDIN
    # -----------------------------------------------

    if field_is_visible(
        student,
        "LinkedIn"
    ):

        profile["linkedin"] = student["linkedin"]


    return profile


# =====================================================
# GET MEMBERS
# =====================================================

def get_members():

    global cached_members
    global last_update


    current_time = time.time()


    # -----------------------------------------------
    # CACHE
    # -----------------------------------------------

    if (
        current_time - last_update
        < CACHE_TIME
    ):

        return cached_members


    # -----------------------------------------------
    # READ PRIVATE SHEET
    # -----------------------------------------------

    students = read_students()


    # -----------------------------------------------
    # CREATE PUBLIC DATA
    # -----------------------------------------------

    public_members = []


    for student in students:

        profile = create_public_profile(
            student
        )


        if profile is not None:

            public_members.append(
                profile
            )


    cached_members = public_members

    last_update = current_time


    return cached_members


# =====================================================
# SECURITY HEADERS
# =====================================================

@app.middleware("http")
async def security_headers(
    request: Request,
    call_next
):

    response = await call_next(
        request
    )


    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"


    response.headers[
        "X-Frame-Options"
    ] = "DENY"


    response.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"


    return response


# =====================================================
# HOME PAGE
# =====================================================

@app.get("/")
def home(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="web.html"
    )


# =====================================================
# PUBLIC MEMBER API
# =====================================================

@app.get(
    "/api/members"
)
def api_members():

    members = get_members()


    response = JSONResponse(
        content=members
    )


    response.headers[
        "Cache-Control"
    ] = "no-store"


    return response


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
def health():

    return {
        "status": "running"
    }


# =====================================================
# LOCAL DEVELOPMENT
# =====================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
