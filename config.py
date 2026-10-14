import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_URL = "https://accounts.hubintent.com/oauth/token"
BASE_URL = "https://api.hubintent.com/api"

DB_URL = os.getenv("DB_URL")

if not DB_URL:
    try:
        import streamlit as st
        DB_URL = st.secrets["postgres"]["url"]
    except (KeyError, FileNotFoundError, ImportError):
        pass

if not DB_URL:
    raise RuntimeError("Configuration PostgreSQL manquante")