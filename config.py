"""All paths and settings for the job-hunt project live here.

Why one file? If a path or setting changes, we fix it in ONE place,
not in ten different files.
"""

from pathlib import Path
from typing import Literal, get_args

# ---------- Paths ----------
# BASE_DIR = the folder this file lives in. Building every path from it means
# the project works no matter which folder you start Python from.
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "jobs.db"

# Your PRIVATE data files (git-ignored). If one is missing, the code falls
# back to the matching *.example.yaml file so the project still runs.
MASTER_RESUME_PATH = DATA_DIR / "master_resume.yaml"
MASTER_BULLETS_PATH = DATA_DIR / "master_bullets.yaml"
RUBRIC_PATH = DATA_DIR / "rubric.yaml"

OUTPUT_DIR = BASE_DIR / "output"
RESUMES_DIR = OUTPUT_DIR / "resumes"
COVER_LETTERS_DIR = OUTPUT_DIR / "cover_letters"

# ---------- Server ----------
SERVER_NAME = "job-hunt"

# ---------- Job tracker ----------
# A job moves through these statuses, left to right (or to "rejected").
# `Literal` lists the only allowed values. MCP turns it into a list of choices
# in the tool schema, so Claude can only pick a valid status.
JobStatus = Literal["saved", "applied", "interview", "offer", "rejected"]
JobSource = Literal["linkedin", "naukri", "indeed", "other"]
JOB_STATUSES = list(get_args(JobStatus))
JOB_SOURCES = list(get_args(JobSource))

# ---------- My job search ----------
TARGET_ROLES = ["AI Engineer", "AI/ML Engineer", "Data Analyst", "Data Engineer"]
TARGET_LOCATIONS = ["Kochi", "Bangalore", "Chennai"]

# Different spellings of the same city, so "Bengaluru" counts as "Bangalore".
LOCATION_ALIASES = {
    "kochi": ["kochi", "cochin", "ernakulam", "kakkanad", "infopark"],
    "bangalore": ["bangalore", "bengaluru"],
    "chennai": ["chennai", "madras"],
}

# ---------- Follow-ups ----------
# Remind me to follow up if an applied job has had no update for this many days.
FOLLOWUP_AFTER_DAYS = 7

# ---------- Resume ----------
# How many bullets go on a tailored resume (one page for a fresher).
MAX_BULLETS = 6
