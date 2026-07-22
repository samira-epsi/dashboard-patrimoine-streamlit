import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from config import DB_URL_2


def setup_page(title="Dashboard Patrimoine", icon="🏢"):
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.logo("assets/Logo.png")


@st.cache_resource
def get_engine():
    return create_engine(
        DB_URL_2,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=15
    )


@st.cache_data(ttl=600, show_spinner=False)
def load_data(query):
    engine = get_engine()
    return pd.read_sql(query, engine)