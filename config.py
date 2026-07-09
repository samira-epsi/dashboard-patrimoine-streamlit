# Code pour connexion avec Postgresql

# CLIENT_ID = "c0ef2840-8322-4482-85ba-0641b90e63fd"
# CLIENT_SECRET = "a383254f-2af4-4bf1-931c-badd63ac1c16"

# TOKEN_URL = "https://accounts.hubintent.com/oauth/token"
# BASE_URL = "https://api.hubintent.com/api"

# DB_URL = "postgresql+psycopg2://postgres:momopopolove2026?@localhost:5432/patrimoine"


import streamlit as st

DB_URL = st.secrets["postgres"]["postgresql+psycopg2://postgres.ppjnxrqauxiyoyunaobf:momopopolove2026?@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"]