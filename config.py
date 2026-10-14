import os
from pathlib import Path
from dotenv import load_dotenv

# Localiser le .env à la racine du projet
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# API INTENT
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_URL = os.getenv(
    "TOKEN_URL",
    "https://accounts.hubintent.com/oauth/token"
)

BASE_URL = os.getenv(
    "BASE_URL",
    "https://api.hubintent.com/api"
)

# PostgreSQL
DB_URL = os.getenv("DB_URL")