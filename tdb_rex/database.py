
"""Connexion PostgreSQL, lecture avec paramètres liés, cache SQL contrôlé.
Lecture seule du schéma rex. Aucune donnée fictive."""

import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# .env situé à la racine de CODE TDB 2
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def load_postgres_config():
    """Récupère la connexion PostgreSQL depuis le .env principal."""
    db_url = os.getenv("DB_URL")

    if not db_url:
        raise RuntimeError(
            f"Variable DB_URL absente du .env : {ROOT_DIR / '.env'}"
        )

    return db_url


@st.cache_resource(show_spinner=False)
def get_engine():
    db_url = load_postgres_config()

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={"connect_timeout": 10},
        future=True,
    )


@st.cache_data(ttl=900, show_spinner=False, max_entries=600)
def read_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    # Mesure uniquement les vrais appels à la base
    started = time.perf_counter()

    with get_engine().connect() as conn:
        df = pd.read_sql_query(
            text(sql),
            conn,
            params=params or {}
        )

    elapsed = time.perf_counter() - started
    flag = "LENT " if elapsed > 1 else "     "

    print(
        f"[SQL] {flag}{elapsed:6.2f} s | "
        f"{len(df):>7} lignes | "
        f"{' '.join(sql.split())[:110]}",
        flush=True,
    )

    return df


def check_connection():
    return read_sql(
        "SELECT current_database() AS database_name, "
        "current_timestamp AS checked_at"
    )
