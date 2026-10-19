"""Connexion PostgreSQL, lecture avec paramètres liés, cache SQL contrôlé.
Lecture seule du schéma rex. Aucune donnée fictive."""
import os
import time
import tomllib
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

SECRETS_FILE = Path(__file__).parent / ".streamlit" / "secrets.toml"


def load_postgres_config():
    """Lit la section [postgres] : d'abord st.secrets, sinon directement le fichier du projet,
    ce qui évite de dépendre du dossier depuis lequel Streamlit est lancé."""
    try:
        if "postgres" in st.secrets:
            return dict(st.secrets["postgres"])
    except Exception:
        pass
    if not SECRETS_FILE.exists():
        raise RuntimeError(f"Fichier introuvable : {SECRETS_FILE}")
    with open(SECRETS_FILE, "rb") as f:
        data = tomllib.load(f)
    if "postgres" not in data:
        raise RuntimeError(f"Section [postgres] absente de {SECRETS_FILE}. Sections trouvées : {list(data.keys())}")
    return dict(data["postgres"])


@st.cache_resource(show_spinner=False)
def get_engine():
    cfg = load_postgres_config()
    url = URL.create(
        "postgresql+psycopg2",
        username=cfg["user"], password=cfg["password"],
        host=cfg["host"], port=int(cfg.get("port", 5432)),
        database=cfg["database"],
    )
    return create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=2,
                         connect_args={"connect_timeout": 10}, future=True)


@st.cache_data(ttl=900, show_spinner=False, max_entries=600)
def read_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    # Ce corps ne s'exécute que lorsque le résultat n'est pas en cache : on mesure donc les vrais appels à la base.
    started = time.perf_counter()
    with get_engine().connect() as conn:
        df = pd.read_sql_query(text(sql), conn, params=params or {})
    elapsed = time.perf_counter() - started
    flag = "LENT " if elapsed > 1 else "     "
    print(f"[SQL] {flag}{elapsed:6.2f} s | {len(df):>7} lignes | {' '.join(sql.split())[:110]}", flush=True)
    return df


def check_connection():
    return read_sql("SELECT current_database() AS database_name, current_timestamp AS checked_at")