

import os

CLIENT_ID = "c0ef2840-8322-4482-85ba-0641b90e63fd"
CLIENT_SECRET = "a383254f-2af4-4bf1-931c-badd63ac1c16"

TOKEN_URL = "https://accounts.hubintent.com/oauth/token"
BASE_URL = "https://api.hubintent.com/api"

# Base locale utilisée par le pipeline
DB_URL = "postgresql+psycopg2://postgres:momopopolove2026?@localhost:5432/patrimoine"

# Base utilisée par Streamlit
try:
    import streamlit as st
    DB_URL_2 = st.secrets["postgres"]["url"]
except Exception:
    DB_URL_2 = os.getenv("DB_URL_2", DB_URL)