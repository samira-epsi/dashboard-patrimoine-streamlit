import html
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

try:
    import plotly.graph_objects as go
except ImportError:
    go = None

try:
    from common.app_config import setup_page
except Exception:
    setup_page = None

try:
    from common.ui_style import apply_3f_page_style
except Exception:
    apply_3f_page_style = None

from config import DB_URL


# =====================================================
# SOURCES SUPABASE
# =====================================================

SOURCE_ESI = "dashboard.esi_couverture"
SOURCE_CONTRATS = "dashboard.contrats_patrimoine"
SOURCE_GLOBAL = "dashboard.kpi_globale"
SOURCE_CREATIONS = "dashboard.kpi_creation_detail"
SOURCE_QUALITE = "dashboard.qualite_donnees"
SOURCE_QUALITE_RESUME = "dashboard.qualite_donnees_resume"
SOURCE_SERVICE_CODES = "dashboard.service_codes_light"

CACHE_TTL = 3600
SQL_TIMEOUT_MS = 20000
PARIS_TZ = ZoneInfo("Europe/Paris")

REQUIRED_SOURCES = [SOURCE_ESI, SOURCE_CONTRATS, SOURCE_GLOBAL]
OPTIONAL_SOURCES = [SOURCE_CREATIONS, SOURCE_QUALITE, SOURCE_QUALITE_RESUME, SOURCE_SERVICE_CODES]


# =====================================================
# PAGE CONFIG
# =====================================================

if setup_page:
    setup_page("Vue Globale", None)
else:
    st.set_page_config(page_title="Vue Globale", layout="wide")

if apply_3f_page_style:
    apply_3f_page_style()


# =====================================================
# STYLE
# =====================================================

def _safe(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def inject_style():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.15rem !important;
            padding-left: 1.7rem !important;
            padding-right: 1.7rem !important;
            max-width: 1660px !important;
        }

        .vg-hero {
            position: relative;
            overflow: hidden;
            border-radius: 30px;
            padding: 28px 30px;
            margin-bottom: 18px;
            background:
                radial-gradient(circle at top right, rgba(255,255,255,0.24), transparent 32%),
                linear-gradient(135deg, #8F0E15 0%, #B5121B 42%, #E34B56 100%);
            box-shadow: 0 22px 54px rgba(181, 18, 27, 0.22);
            border: 1px solid rgba(255,255,255,0.24);
        }

        .vg-hero-title {
            color: #FFFFFF;
            font-size: 43px;
            line-height: 1.02;
            letter-spacing: -1.1px;
            font-weight: 950;
            margin-bottom: 9px;
        }

        .vg-hero-subtitle {
            color: rgba(255,255,255,0.88);
            max-width: 1050px;
            font-size: 14.5px;
            line-height: 1.55;
            font-weight: 650;
        }

        .vg-chip-row {
            display: flex;
            gap: 9px;
            flex-wrap: wrap;
            margin-top: 16px;
        }

        .vg-chip {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 7px 12px;
            background: rgba(255,255,255,0.16);
            border: 1px solid rgba(255,255,255,0.24);
            color: white;
            font-weight: 850;
            font-size: 12px;
        }

        .vg-section-title {
            margin-top: 4px;
            margin-bottom: 5px;
            color: #0F172A;
            font-size: 27px;
            line-height: 1.1;
            font-weight: 950;
            letter-spacing: -0.6px;
        }

        .vg-section-subtitle {
            color: #64748B;
            font-size: 13px;
            line-height: 1.45;
            font-weight: 650;
            margin-bottom: 16px;
        }

        .vg-card {
            position: relative;
            overflow: hidden;
            min-height: 142px;
            border-radius: 26px;
            padding: 19px 19px 17px 19px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid #E2E8F0;
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.085);
        }

        .vg-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 5px;
            background: var(--accent, #B5121B);
        }

        .vg-card::after {
            content: "";
            position: absolute;
            width: 160px;
            height: 160px;
            right: -95px;
            top: -100px;
            border-radius: 999px;
            background: color-mix(in srgb, var(--accent, #B5121B) 13%, transparent);
        }

        .vg-card-label {
            position: relative;
            z-index: 2;
            color: #64748B;
            font-size: 12.5px;
            font-weight: 900;
            margin-bottom: 17px;
        }

        .vg-card-value {
            position: relative;
            z-index: 2;
            color: #0F172A;
            font-size: 36px;
            font-weight: 950;
            letter-spacing: -1px;
            line-height: 1;
            margin-bottom: 12px;
        }

        .vg-card-note {
            position: relative;
            z-index: 2;
            color: #94A3B8;
            font-size: 11.5px;
            font-weight: 700;
            line-height: 1.45;
        }

        .vg-mini-card {
            border-radius: 22px;
            padding: 16px 17px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.07);
        }

        .vg-mini-title {
            color: #64748B;
            font-size: 12px;
            font-weight: 900;
            margin-bottom: 8px;
        }

        .vg-mini-value {
            color: #0F172A;
            font-size: 26px;
            line-height: 1;
            font-weight: 950;
            letter-spacing: -0.5px;
        }

        .vg-mini-note {
            margin-top: 8px;
            color: #94A3B8;
            font-size: 11px;
            font-weight: 700;
            line-height: 1.35;
        }

        .vg-alert {
            border-radius: 22px;
            padding: 15px 17px;
            background: #FFF7ED;
            border: 1px solid #FED7AA;
            color: #9A3412;
            font-size: 13px;
            font-weight: 750;
            line-height: 1.45;
            box-shadow: 0 12px 28px rgba(154, 52, 18, 0.08);
            margin-bottom: 14px;
        }

        .vg-good {
            border-radius: 22px;
            padding: 15px 17px;
            background: #ECFDF3;
            border: 1px solid #BBF7D0;
            color: #166534;
            font-size: 13px;
            font-weight: 750;
            line-height: 1.45;
            box-shadow: 0 12px 28px rgba(22, 101, 52, 0.06);
            margin-bottom: 14px;
        }

        .vg-filter-box {
            border-radius: 26px;
            padding: 18px 18px 10px 18px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid #E2E8F0;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.075);
            margin-bottom: 18px;
        }

        .vg-table-shell {
            border-radius: 26px;
            padding: 16px 18px 14px 18px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid #E2E8F0;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.075);
            margin-bottom: 10px;
        }

        .vg-pill {
            display: inline-flex;
            align-items: center;
            padding: 7px 12px;
            border-radius: 999px;
            background: #FDEBEC;
            border: 1px solid #F6CBCD;
            color: #B5121B;
            font-size: 12px;
            font-weight: 900;
        }

        div[data-testid="stPlotlyChart"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 24px;
            padding: 10px;
            box-shadow: 0 16px 38px rgba(15, 23, 42, 0.075);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 22px !important;
            overflow: hidden !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.075) !important;
            background: #FFFFFF !important;
        }

        div[data-testid="stDataFrame"] [role="columnheader"] {
            background: #F8FAFC !important;
            color: #334155 !important;
            font-weight: 900 !important;
        }

        div[data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 22px;
            padding: 14px 16px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.065);
        }

        button[kind="primary"] {
            background: #B5121B !important;
            border-color: #B5121B !important;
        }

        @media screen and (max-width: 1000px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .vg-hero-title { font-size: 34px; }
            .vg-card-value { font-size: 30px; }
        }

        @media screen and (max-width: 720px) {
            .vg-hero {
                padding: 22px 20px;
                border-radius: 22px;
            }
            .vg-hero-title { font-size: 29px; }
            .vg-section-title { font-size: 23px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_style()


# =====================================================
# HELPERS AFFICHAGE
# =====================================================

def fmt_int(value) -> str:
    try:
        return f"{int(float(value)):,}".replace(",", " ")
    except Exception:
        return "0"


def fmt_pct(value) -> str:
    try:
        return f"{float(value):.1f} %".replace(".", ",")
    except Exception:
        return "0,0 %"


def safe_int(row, col, default=0) -> int:
    try:
        return int(float(row.get(col, default) or default))
    except Exception:
        return default


def hero(title: str, subtitle: str, chips=None):
    chips = chips or []
    chips_html = "".join([f'<span class="vg-chip">{_safe(c)}</span>' for c in chips])
    chip_row = f'<div class="vg-chip-row">{chips_html}</div>' if chips_html else ""
    st.markdown(
        f"""
        <div class="vg-hero">
            <div class="vg-hero-title">{_safe(title)}</div>
            <div class="vg-hero-subtitle">{_safe(subtitle)}</div>
            {chip_row}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = ""):
    subtitle_html = f'<div class="vg-section-subtitle">{_safe(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="vg-section-title">{_safe(title)}</div>
        {subtitle_html}
        """,
        unsafe_allow_html=True,
    )


def card(label: str, value, note: str = "", accent: str = "#B5121B"):
    st.markdown(
        f"""
        <div class="vg-card" style="--accent:{_safe(accent)};">
            <div class="vg-card-label">{_safe(label)}</div>
            <div class="vg-card-value">{_safe(fmt_int(value))}</div>
            <div class="vg-card-note">{_safe(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini_card(label: str, value, note: str = ""):
    st.markdown(
        f"""
        <div class="vg-mini-card">
            <div class="vg-mini-title">{_safe(label)}</div>
            <div class="vg-mini-value">{_safe(fmt_int(value))}</div>
            <div class="vg-mini-note">{_safe(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_box(text: str):
    st.markdown(f'<div class="vg-alert">{_safe(text)}</div>', unsafe_allow_html=True)


def good_box(text: str):
    st.markdown(f'<div class="vg-good">{_safe(text)}</div>', unsafe_allow_html=True)


# =====================================================
# CONNEXION ET CHARGEMENT
# =====================================================

@st.cache_resource(show_spinner=False)
def get_engine():
    return create_engine(
        DB_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 10,
            "options": f"-c statement_timeout={SQL_TIMEOUT_MS}",
        },
    )


def exists_source(conn, source: str) -> bool:
    return conn.execute(text("SELECT to_regclass(:source)"), {"source": source}).scalar() is not None


def read_table(conn, source: str) -> pd.DataFrame:
    return pd.read_sql_query(text(f"SELECT * FROM {source}"), conn)


def empty_df(cols):
    return pd.DataFrame(columns=cols)


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    ref_cols = [
        "esi_reference", "contract_reference", "objet_reference", "third_party_id", "objet_label"
    ]
    text_cols = [
        "esi_label", "societe", "agence", "groupe", "secteur",
        "contract_label", "contract_status", "contract_topic", "third_party_label",
        "objet_type", "anomalie_type", "objet_type", "gravite", "description",
        "service_code_reference_interne", "service_code_reference_prestataire",
        "service_code_label", "service_code_work_type",
    ]
    num_cols = [
        "nb_logements", "nb_equipements", "nb_contrats_actifs", "nb_contrats_inactifs",
        "nb_prestataires_actifs", "nb_contrats_actifs_date_depassee",
        "esi_couvert", "esi_multi_couvert", "esi_multi_meme_metier",
        "esi_sans_contrat", "esi_sans_equipement", "nb_objets_distincts", "nb_lignes_detail",
    ]
    date_cols = ["contract_start_date", "contract_end_date", "creation_date", "date_maj"]

    for col in ref_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
            )

    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("Non renseigné")
                .astype(str)
                .str.strip()
                .replace({"": "Non renseigné", "nan": "Non renseigné", "None": "Non renseigné", "<NA>": "Non renseigné"})
            )

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_dashboard_data():
    try:
        with get_engine().connect() as conn:
            conn.execute(text(f"SET statement_timeout = {SQL_TIMEOUT_MS}"))

            missing = [source for source in REQUIRED_SOURCES if not exists_source(conn, source)]
            if missing:
                raise RuntimeError("Sources SQL manquantes : " + ", ".join(missing))

            available = {source: exists_source(conn, source) for source in OPTIONAL_SOURCES}

            df_esi = read_table(conn, SOURCE_ESI)
            df_contrats = read_table(conn, SOURCE_CONTRATS)
            df_global = read_table(conn, SOURCE_GLOBAL)

            df_creations = read_table(conn, SOURCE_CREATIONS) if available[SOURCE_CREATIONS] else empty_df([
                "objet_type", "objet_reference", "objet_label", "creation_date", "esi_reference",
                "societe", "agence", "groupe", "secteur", "contract_topic", "third_party_label"
            ])
            df_qualite = read_table(conn, SOURCE_QUALITE) if available[SOURCE_QUALITE] else empty_df([
                "anomalie_type", "objet_type", "objet_reference", "objet_label", "gravite", "description",
                "societe", "agence", "groupe", "secteur", "esi_reference", "esi_label",
                "contract_topic", "third_party_label", "contract_status", "contract_end_date"
            ])
            df_qualite_resume = read_table(conn, SOURCE_QUALITE_RESUME) if available[SOURCE_QUALITE_RESUME] else empty_df([
                "anomalie_type", "objet_type", "gravite", "nb_objets_distincts", "nb_lignes_detail"
            ])
            df_service_codes = read_table(conn, SOURCE_SERVICE_CODES) if available[SOURCE_SERVICE_CODES] else empty_df([
                "contract_reference", "service_code_reference_interne", "service_code_reference_prestataire",
                "service_code_label", "service_code_work_type"
            ])

    except SQLAlchemyError as e:
        raise RuntimeError(f"Erreur PostgreSQL : {e}") from e

    df_esi = normalize_df(df_esi)
    df_contrats = normalize_df(df_contrats)
    df_global = normalize_df(df_global)
    df_creations = normalize_df(df_creations)
    df_qualite = normalize_df(df_qualite)
    df_qualite_resume = normalize_df(df_qualite_resume)
    df_service_codes = normalize_df(df_service_codes)

    for col in ["contract_start_date", "contract_end_date"]:
        if col not in df_contrats.columns:
            df_contrats[col] = pd.NaT

    if "contract_status" not in df_contrats.columns:
        df_contrats["contract_status"] = "Non renseigné"

    df_contrats["contract_status_clean"] = df_contrats["contract_status"].fillna("").astype(str).str.lower().str.strip()

    if "creation_date" in df_creations.columns:
        df_creations["creation_date"] = pd.to_datetime(df_creations["creation_date"], errors="coerce")

    return {
        "esi": df_esi,
        "contrats": df_contrats,
        "global": df_global,
        "creations": df_creations,
        "qualite": df_qualite,
        "qualite_resume": df_qualite_resume,
        "service_codes": df_service_codes,
        "optional_available": available,
    }


# =====================================================
# FILTRES
# =====================================================

def clean_options(series) -> list:
    if series is None:
        return []
    values = (
        pd.Series(series)
        .dropna()
        .astype(str)
        .str.strip()
    )
    values = values[~values.isin(["", "nan", "None", "<NA>"])]
    return sorted(values.unique().tolist(), key=lambda x: x.lower())


def apply_in(df: pd.DataFrame, col: str, selected: list) -> pd.DataFrame:
    if not selected or col not in df.columns:
        return df.copy()
    return df[df[col].astype(str).isin([str(x) for x in selected])].copy()


def valid_refs(df: pd.DataFrame, col: str) -> set:
    if col not in df.columns:
        return set()
    s = df[col].dropna().astype(str).str.strip()
    s = s[~s.isin(["", "nan", "None", "<NA>", "Non renseigné"])]
    return set(s.tolist())


def reset_filters():
    for key in list(st.session_state.keys()):
        if key.startswith("vg_"):
            del st.session_state[key]


def filter_panel(df_esi: pd.DataFrame, df_contrats: pd.DataFrame):
    st.markdown('<div class="vg-filter-box">', unsafe_allow_html=True)

    top_a, top_b, top_c = st.columns([1.2, 1.2, 2.2])
    with top_a:
        if st.button("Réinitialiser les filtres", key="vg_reset_filters", use_container_width=True):
            reset_filters()
            st.rerun()
    with top_b:
        if st.button("Actualiser l’affichage", key="vg_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with top_c:
        st.caption("Les données sont lues depuis Supabase. Ce bouton actualise uniquement le cache Streamlit.")

    geo1, geo2, geo3, geo4 = st.columns(4)

    tmp = df_esi.copy()
    with geo1:
        societes = st.multiselect("Société", clean_options(tmp.get("societe")), key="vg_societe")
    tmp = apply_in(tmp, "societe", societes)

    with geo2:
        agences = st.multiselect("Agence", clean_options(tmp.get("agence")), key="vg_agence")
    tmp = apply_in(tmp, "agence", agences)

    with geo3:
        groupes = st.multiselect("Groupe", clean_options(tmp.get("groupe")), key="vg_groupe")
    tmp = apply_in(tmp, "groupe", groupes)

    with geo4:
        secteurs = st.multiselect("Secteur", clean_options(tmp.get("secteur")), key="vg_secteur")
    tmp = apply_in(tmp, "secteur", secteurs)

    # Programme / ESI
    tmp = tmp.copy()
    if "esi_reference" in tmp.columns and "esi_label" in tmp.columns:
        tmp["programme_display"] = tmp["esi_reference"].astype(str) + " — " + tmp["esi_label"].astype(str)
    else:
        tmp["programme_display"] = ""

    prog_options = clean_options(tmp["programme_display"])
    selected_programs = st.multiselect(
        "Programme / ESI",
        prog_options,
        key="vg_programmes",
        placeholder="Choisir un ou plusieurs programmes"
    )

    df_esi_geo = tmp.copy()
    if selected_programs:
        df_esi_geo = df_esi_geo[df_esi_geo["programme_display"].isin(selected_programs)].copy()

    esi_scope = valid_refs(df_esi_geo, "esi_reference")
    df_contrats_geo = df_contrats[df_contrats["esi_reference"].astype(str).isin(esi_scope)].copy() if esi_scope else df_contrats.iloc[0:0].copy()

    f1, f2, f3, f4 = st.columns([1.15, 1.15, 1.1, 1.6])

    with f1:
        topics = st.multiselect("Métier", clean_options(df_contrats_geo.get("contract_topic")), key="vg_topics")
    with f2:
        prestataires = st.multiselect("Prestataire", clean_options(df_contrats_geo.get("third_party_label")), key="vg_prestataires")
    with f3:
        statut = st.radio(
            "Statut contrat",
            ["Tous", "Actifs", "Inactifs"],
            horizontal=True,
            key="vg_statut",
        )
    with f4:
        recherche = st.text_input(
            "Recherche contrat",
            placeholder="Référence, libellé, prestataire, métier...",
            key="vg_recherche",
        )

    df_contrats_filtered = df_contrats_geo.copy()
    df_contrats_filtered = apply_in(df_contrats_filtered, "contract_topic", topics)
    df_contrats_filtered = apply_in(df_contrats_filtered, "third_party_label", prestataires)

    if statut == "Actifs":
        df_contrats_filtered = df_contrats_filtered[df_contrats_filtered["contract_status_clean"] == "active"].copy()
    elif statut == "Inactifs":
        df_contrats_filtered = df_contrats_filtered[df_contrats_filtered["contract_status_clean"] != "active"].copy()

    recherche_clean = str(recherche or "").strip().lower()
    if recherche_clean:
        cols_search = ["contract_reference", "contract_label", "third_party_label", "contract_topic", "contract_status"]
        mask = pd.Series(False, index=df_contrats_filtered.index)
        for col in cols_search:
            if col in df_contrats_filtered.columns:
                mask = mask | df_contrats_filtered[col].fillna("").astype(str).str.lower().str.contains(recherche_clean, regex=False)
        df_contrats_filtered = df_contrats_filtered[mask].copy()

    contract_filter_active = bool(topics or prestataires or statut != "Tous" or recherche_clean)

    if contract_filter_active:
        esi_from_contracts = valid_refs(df_contrats_filtered, "esi_reference")
        df_esi_effective = df_esi_geo[df_esi_geo["esi_reference"].astype(str).isin(esi_from_contracts)].copy()
    else:
        df_esi_effective = df_esi_geo.copy()

    selected = {
        "societe": societes,
        "agence": agences,
        "groupe": groupes,
        "secteur": secteurs,
        "programmes": selected_programs,
        "topics": topics,
        "prestataires": prestataires,
        "statut": statut,
        "recherche": recherche_clean,
        "contract_filter_active": contract_filter_active,
    }

    st.markdown('</div>', unsafe_allow_html=True)
    return df_esi_geo, df_esi_effective, df_contrats_geo, df_contrats_filtered, selected


# =====================================================
# CALCULS
# =====================================================

def unique_count(df, col):
    if df.empty or col not in df.columns:
        return 0
    return len(valid_refs(df, col))


def sum_col(df, col):
    if df.empty or col not in df.columns:
        return 0
    return int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def current_month_new(df_creations, objet_type, object_refs=None, esi_refs=None):
    if df_creations.empty or "creation_date" not in df_creations.columns or "objet_type" not in df_creations.columns:
        return 0

    today = pd.Timestamp(datetime.now(PARIS_TZ).date())
    start_month = today.replace(day=1)
    tomorrow = today + pd.Timedelta(days=1)

    df = df_creations[df_creations["objet_type"].astype(str).str.lower() == objet_type.lower()].copy()

    if object_refs is not None and "objet_reference" in df.columns:
        df = df[df["objet_reference"].astype(str).isin(set(map(str, object_refs)))].copy()

    if esi_refs is not None and "esi_reference" in df.columns:
        df = df[df["esi_reference"].astype(str).isin(set(map(str, esi_refs)))].copy()

    df = df[df["creation_date"].notna()]
    df = df[(df["creation_date"] >= start_month) & (df["creation_date"] < tomorrow)]

    return unique_count(df, "objet_reference")


def coverage_frame(df_esi_base, df_esi_effective, contract_filter_active):
    base = df_esi_base.drop_duplicates(subset=["esi_reference"]).copy() if "esi_reference" in df_esi_base.columns else df_esi_base.copy()
    effective = df_esi_effective.drop_duplicates(subset=["esi_reference"]).copy() if "esi_reference" in df_esi_effective.columns else df_esi_effective.copy()

    total_prog = unique_count(base, "esi_reference")
    total_log = sum_col(base, "nb_logements")
    total_eq = sum_col(base, "nb_equipements")

    if contract_filter_active:
        covered_prog = unique_count(effective, "esi_reference")
        covered_log = sum_col(effective, "nb_logements")
        covered_eq = sum_col(effective, "nb_equipements")
    else:
        covered = base[pd.to_numeric(base.get("esi_couvert", 0), errors="coerce").fillna(0) > 0].copy()
        covered_prog = unique_count(covered, "esi_reference")
        covered_log = sum_col(covered, "nb_logements")
        covered_eq = sum_col(covered, "nb_equipements")

    def ratio(a, b):
        return round((a / b) * 100, 1) if b else 0.0

    return pd.DataFrame({
        "Indicateur": ["Programmes", "Logements", "Équipements"],
        "Couverts": [covered_prog, covered_log, covered_eq],
        "Total": [total_prog, total_log, total_eq],
        "Taux": [ratio(covered_prog, total_prog), ratio(covered_log, total_log), ratio(covered_eq, total_eq)],
        "Détail": [f"{fmt_int(covered_prog)} / {fmt_int(total_prog)}", f"{fmt_int(covered_log)} / {fmt_int(total_log)}", f"{fmt_int(covered_eq)} / {fmt_int(total_eq)}"],
    })


def filter_quality(df_qualite, df_esi_geo, selected):
    if df_qualite.empty:
        return df_qualite.copy()

    df = df_qualite.copy()
    geo_cols = ["societe", "agence", "groupe", "secteur"]
    for col in geo_cols:
        values = selected.get(col) or []
        df = apply_in(df, col, values)

    if selected.get("programmes"):
        refs = valid_refs(df_esi_geo, "esi_reference")
        if "esi_reference" in df.columns:
            df = df[df["esi_reference"].astype(str).isin(refs)].copy()

    if selected.get("topics"):
        df = apply_in(df, "contract_topic", selected["topics"])

    if selected.get("prestataires"):
        df = apply_in(df, "third_party_label", selected["prestataires"])

    statut = selected.get("statut")
    if statut == "Actifs" and "contract_status" in df.columns:
        df = df[df["contract_status"].fillna("").astype(str).str.lower().str.strip() == "active"].copy()
    elif statut == "Inactifs" and "contract_status" in df.columns:
        df = df[df["contract_status"].fillna("").astype(str).str.lower().str.strip() != "active"].copy()

    recherche = selected.get("recherche") or ""
    if recherche:
        cols = ["objet_reference", "objet_label", "description", "third_party_label", "contract_topic", "anomalie_type"]
        mask = pd.Series(False, index=df.index)
        for col in cols:
            if col in df.columns:
                mask = mask | df[col].fillna("").astype(str).str.lower().str.contains(recherche, regex=False)
        df = df[mask].copy()

    return df


# =====================================================
# GRAPHIQUES
# =====================================================

def plot_horizontal_bar(df, x, y, title="", color="#B5121B", height=None, suffix=""):
    if df.empty or go is None:
        if not df.empty:
            st.bar_chart(df.set_index(y)[x], use_container_width=True)
        else:
            st.info("Aucune donnée disponible.")
        return

    data = df.copy().sort_values(x, ascending=True)
    height = height or max(320, min(760, 46 * len(data) + 80))
    max_value = max(float(data[x].max()), 1.0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data[x],
        y=data[y],
        orientation="h",
        text=data[x].apply(lambda v: f"{fmt_int(v)}{suffix}"),
        textposition="outside",
        cliponaxis=False,
        marker=dict(color=color, line=dict(color="#111827", width=0.5)),
        hovertemplate="<b>%{y}</b><br>Valeur : %{x}<extra></extra>",
    ))
    fig.update_layout(
        title_text=title,
        height=height,
        margin=dict(l=8, r=56, t=28 if title else 8, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(title=None, range=[0, max_value * 1.18], gridcolor="#E5E7EB", zeroline=False),
        yaxis=dict(title=None, automargin=True),
        font=dict(family="Arial", size=12, color="#111827"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def plot_coverage(df_cov):
    if df_cov.empty:
        st.info("Aucune donnée de couverture disponible.")
        return

    if go is None:
        st.bar_chart(df_cov.set_index("Indicateur")["Taux"], use_container_width=True)
        return

    data = df_cov.copy().sort_values("Taux", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["Taux"],
        y=data["Indicateur"],
        orientation="h",
        text=data["Taux"].apply(fmt_pct),
        textposition="auto",
        customdata=data["Détail"],
        marker=dict(color="#0057A8", line=dict(color="#003F7D", width=1)),
        hovertemplate="<b>%{y}</b><br>Taux : %{x:.1f} %<br>Détail : %{customdata}<extra></extra>",
    ))
    fig.update_layout(
        height=350,
        margin=dict(l=8, r=18, t=8, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(range=[0, 105], ticksuffix=" %", gridcolor="#E5E7EB", zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
        font=dict(family="Arial", size=12, color="#111827"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def plot_donut(labels, values, title=""):
    if go is None:
        st.write(pd.DataFrame({"label": labels, "value": values}))
        return

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value}<extra></extra>",
    )])
    fig.update_layout(
        title_text=title,
        height=340,
        margin=dict(l=8, r=8, t=42 if title else 8, b=8),
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color="#111827"),
        showlegend=True,
        legend=dict(orientation="h", y=-0.05),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


# =====================================================
# TABLES AFFICHAGE
# =====================================================

def prepare_contract_table(df_contrats, df_service_codes, show_services=False, only_expired=False):
    df = df_contrats.copy()

    if only_expired:
        df = df[
            (df["contract_status_clean"] == "active")
            & df["contract_end_date"].notna()
            & (df["contract_end_date"].dt.date < datetime.now(PARIS_TZ).date())
        ].copy()

    base_cols = [
        "contract_reference", "contract_label", "third_party_label", "contract_start_date", "contract_end_date",
        "contract_topic", "contract_status", "esi_reference", "esi_label", "societe", "agence", "groupe", "secteur"
    ]
    keep = [c for c in base_cols if c in df.columns]
    table = df[keep].drop_duplicates().copy()

    if show_services and not df_service_codes.empty and "contract_reference" in df_service_codes.columns:
        svc_cols = [
            "contract_reference", "service_code_reference_interne", "service_code_reference_prestataire",
            "service_code_label", "service_code_work_type"
        ]
        services = df_service_codes[[c for c in svc_cols if c in df_service_codes.columns]].drop_duplicates().copy()
        table = table.merge(services, on="contract_reference", how="left")

    for col in ["contract_start_date", "contract_end_date"]:
        if col in table.columns:
            table[col] = pd.to_datetime(table[col], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

    rename = {
        "contract_reference": "Référence contrat",
        "contract_label": "Libellé contrat",
        "third_party_label": "Prestataire",
        "contract_start_date": "Date de début",
        "contract_end_date": "Date de fin",
        "contract_topic": "Métier",
        "contract_status": "Statut",
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI",
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "service_code_reference_interne": "Référence prestation chez nous",
        "service_code_reference_prestataire": "Référence prestation prestataire",
        "service_code_label": "Libellé prestation",
        "service_code_work_type": "Métier prestation",
    }
    table = table.rename(columns=rename)

    for col in table.columns:
        table[col] = table[col].fillna("").astype(str).replace("<NA>", "")

    return table.reset_index(drop=True)


def prepare_quality_table(df_qualite):
    if df_qualite.empty:
        return pd.DataFrame()

    cols = [
        "anomalie_type", "objet_type", "objet_reference", "objet_label", "gravite", "description",
        "societe", "agence", "groupe", "secteur", "esi_reference", "esi_label",
        "contract_topic", "third_party_label", "contract_status", "contract_end_date"
    ]
    table = df_qualite[[c for c in cols if c in df_qualite.columns]].copy()

    if "contract_end_date" in table.columns:
        table["contract_end_date"] = pd.to_datetime(table["contract_end_date"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

    rename = {
        "anomalie_type": "Type anomalie",
        "objet_type": "Objet",
        "objet_reference": "Référence",
        "objet_label": "Libellé",
        "gravite": "Gravité",
        "description": "Description",
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI",
        "contract_topic": "Métier",
        "third_party_label": "Prestataire",
        "contract_status": "Statut contrat",
        "contract_end_date": "Date fin contrat",
    }
    table = table.rename(columns=rename)

    for col in table.columns:
        table[col] = table[col].fillna("").astype(str).replace("<NA>", "")

    return table.reset_index(drop=True)


# =====================================================
# APP
# =====================================================

hero(
    "Vue globale patrimoine",
    "Pilotage de la réalité source, du périmètre exploitable pour la couverture et des anomalies qualité. Le dashboard distingue volontairement les données totales des données réellement exploitables.",
    chips=["Source Supabase", "Couverture ESI", "Qualité des données", "Filtres dynamiques"],
)

try:
    with st.spinner("Chargement des données Supabase..."):
        data = load_dashboard_data()
except Exception as exc:
    st.error("Erreur pendant le chargement des données.")
    st.code(str(exc))
    st.stop()

# Dataframes

df_esi = data["esi"]
df_contrats = data["contrats"]
df_global = data["global"]
df_creations = data["creations"]
df_qualite = data["qualite"]
df_qualite_resume = data["qualite_resume"]
df_service_codes = data["service_codes"]
optional_available = data["optional_available"]

if df_global.empty:
    st.error("La table dashboard.kpi_globale est vide.")
    st.stop()

row_global = df_global.sort_values("date_maj", ascending=False).iloc[0] if "date_maj" in df_global.columns else df_global.iloc[0]

last_update = row_global.get("date_maj", None)
if pd.notna(last_update):
    chips_update = f"Dernière publication : {pd.to_datetime(last_update).strftime('%d/%m/%Y %H:%M')}"
else:
    chips_update = "Dernière publication non renseignée"

st.caption(chips_update)

section("Patrimoine source", "Ces chiffres reflètent la réalité brute Intent, même quand une partie de la donnée n’est pas exploitable pour la couverture.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    card("Contrats source", safe_int(row_global, "contrats_total"), f"{fmt_int(safe_int(row_global, 'contrats_rattaches_programme'))} exploitables couverture", "#B5121B")
with c2:
    card("Programmes / ESI", safe_int(row_global, "programmes_total"), "Base de calcul de la couverture", "#0057A8")
with c3:
    card("Logements source", safe_int(row_global, "logements_total"), f"{fmt_int(safe_int(row_global, 'logements_sans_programme'))} sans programme", "#16A34A")
with c4:
    card("Équipements source", safe_int(row_global, "equipements_total"), f"{fmt_int(safe_int(row_global, 'equipements_sans_programme'))} sans programme", "#EA580C")

anomalie_message = (
    f"Hors périmètre exploitable : {fmt_int(safe_int(row_global, 'logements_sans_programme'))} logements sans programme, "
    f"{fmt_int(safe_int(row_global, 'equipements_sans_programme'))} équipement sans programme, "
    f"{fmt_int(safe_int(row_global, 'contrats_non_rattaches_programme'))} contrats non rattachés et "
    f"{fmt_int(safe_int(row_global, 'contrats_fantomes_couverture'))} contrats fantômes dans l’ancienne couverture."
)
alert_box(anomalie_message)

section("Filtres", "Les indicateurs du périmètre filtré se recalculent selon la hiérarchie patrimoine, le métier, le prestataire, le statut et la recherche contrat.")
df_esi_geo, df_esi_effective, df_contrats_geo, df_contrats_filtered, selected = filter_panel(df_esi, df_contrats)
df_qualite_filtered = filter_quality(df_qualite, df_esi_geo, selected)

# KPI filtered

contract_refs = valid_refs(df_contrats_filtered, "contract_reference")
esi_refs = valid_refs(df_esi_effective, "esi_reference")

filtered_contracts = len(contract_refs)
filtered_programmes = len(esi_refs)
filtered_logements = sum_col(df_esi_effective.drop_duplicates(subset=["esi_reference"]), "nb_logements") if not df_esi_effective.empty else 0
filtered_equipements = sum_col(df_esi_effective.drop_duplicates(subset=["esi_reference"]), "nb_equipements") if not df_esi_effective.empty else 0

new_contracts = current_month_new(df_creations, "contrat", object_refs=contract_refs if contract_refs else None)
new_programmes = current_month_new(df_creations, "programme", object_refs=esi_refs if esi_refs else None)
new_logements = current_month_new(df_creations, "logement", esi_refs=esi_refs if esi_refs else None)
new_equipements = current_month_new(df_creations, "equipement", esi_refs=esi_refs if esi_refs else None)

section("Périmètre filtré", "Volumes dynamiques après application des filtres.")
f1, f2, f3, f4 = st.columns(4)
with f1:
    card("Contrats", filtered_contracts, f"+{fmt_int(new_contracts)} nouveaux ce mois-ci", "#B5121B")
with f2:
    card("Programmes / ESI", filtered_programmes, f"+{fmt_int(new_programmes)} nouveaux ce mois-ci", "#0057A8")
with f3:
    card("Logements exploitables", filtered_logements, f"+{fmt_int(new_logements)} nouveaux ce mois-ci", "#16A34A")
with f4:
    card("Équipements exploitables", filtered_equipements, f"+{fmt_int(new_equipements)} nouveaux ce mois-ci", "#EA580C")

# Tabs

tab_synthese, tab_couverture, tab_qualite, tab_contrats = st.tabs([
    "Synthèse", "Couverture", "Qualité des données", "Contrats"
])

with tab_synthese:
    section("Lecture rapide", "Ce bloc met côte à côte la réalité source et le périmètre exploitable.")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        mini_card("Contrats non rattachés", safe_int(row_global, "contrats_non_rattaches_programme"), "Existent en source mais absents de la couverture.")
    with m2:
        mini_card("Contrats actifs expirés", safe_int(row_global, "contrats_actifs_fin_depassee"), "Statut actif avec date de fin dépassée.")
    with m3:
        mini_card("ESI sans contrat actif", sum_col(df_esi, "esi_sans_contrat"), "Programmes sans contrat actif rattaché.")
    with m4:
        mini_card("Multi même métier", sum_col(df_esi, "esi_multi_meme_metier"), "ESI avec plusieurs contrats actifs du même métier.")

    st.divider()
    left, right = st.columns([1.18, 1])

    with left:
        section("Contrats par métier", "Répartition des contrats exploitables du périmètre filtré.")
        if not df_contrats_filtered.empty:
            df_topic = (
                df_contrats_filtered.drop_duplicates(subset=["contract_reference", "contract_topic"])
                .groupby("contract_topic", as_index=False)["contract_reference"]
                .nunique()
                .rename(columns={"contract_topic": "Métier", "contract_reference": "Contrats"})
                .sort_values("Contrats", ascending=False)
                .head(15)
            )
            plot_horizontal_bar(df_topic, "Contrats", "Métier", color="#B5121B")
        else:
            st.info("Aucun contrat dans le périmètre filtré.")

    with right:
        section("Statut des contrats", "Contrats distincts du périmètre filtré.")
        actifs = unique_count(df_contrats_filtered[df_contrats_filtered["contract_status_clean"] == "active"], "contract_reference")
        inactifs = unique_count(df_contrats_filtered[df_contrats_filtered["contract_status_clean"] != "active"], "contract_reference")
        plot_donut(["Actifs", "Inactifs"], [actifs, inactifs])

with tab_couverture:
    section("Couverture simple", "Un programme est couvert s’il possède au moins un contrat actif. Les logements et équipements sont alors couverts par appartenance à ce programme.")

    cov = coverage_frame(df_esi_geo, df_esi_effective, selected["contract_filter_active"])
    c_left, c_right = st.columns([1, 1])

    with c_left:
        plot_coverage(cov)
        if selected["contract_filter_active"]:
            st.caption("Lecture : part du patrimoine filtré couverte par les contrats correspondant aux filtres métier, prestataire, statut ou recherche.")
        else:
            st.caption("Lecture : part du patrimoine filtré couverte par au moins un contrat actif.")

    with c_right:
        base = df_esi_geo.drop_duplicates(subset=["esi_reference"]).copy()
        section("Qualité de couverture ESI", "Signaux utiles pour prioriser les contrôles métier.")
        k1, k2 = st.columns(2)
        with k1:
            mini_card("ESI couverts", sum_col(base, "esi_couvert"), "Au moins un contrat actif.")
        with k2:
            mini_card("ESI sans contrat", sum_col(base, "esi_sans_contrat"), "Aucun contrat actif.")
        k3, k4 = st.columns(2)
        with k3:
            mini_card("ESI multi-couverts", sum_col(base, "esi_multi_couvert"), "Plusieurs contrats actifs.")
        with k4:
            mini_card("Multi même métier", sum_col(base, "esi_multi_meme_metier"), "Plusieurs contrats actifs sur un même métier.")

    st.divider()
    section("ESI à contrôler", "Liste priorisée des programmes sans contrat actif ou avec plusieurs contrats actifs sur le même métier.")

    mode = st.radio(
        "Liste à afficher",
        ["ESI sans contrat actif", "ESI multi même métier", "ESI multi-couverts"],
        horizontal=True,
        key="vg_esi_list_mode",
    )

    df_esi_table = df_esi_geo.drop_duplicates(subset=["esi_reference"]).copy()
    if mode == "ESI sans contrat actif":
        df_esi_table = df_esi_table[pd.to_numeric(df_esi_table.get("esi_sans_contrat", 0), errors="coerce").fillna(0) > 0]
    elif mode == "ESI multi même métier":
        df_esi_table = df_esi_table[pd.to_numeric(df_esi_table.get("esi_multi_meme_metier", 0), errors="coerce").fillna(0) > 0]
    else:
        df_esi_table = df_esi_table[pd.to_numeric(df_esi_table.get("esi_multi_couvert", 0), errors="coerce").fillna(0) > 0]

    table_cols = [
        "esi_reference", "esi_label", "societe", "agence", "groupe", "secteur",
        "nb_logements", "nb_equipements", "nb_contrats_actifs", "nb_contrats_inactifs",
        "esi_multi_meme_metier"
    ]
    df_esi_show = df_esi_table[[c for c in table_cols if c in df_esi_table.columns]].copy()
    df_esi_show = df_esi_show.rename(columns={
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI",
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "nb_logements": "Logements",
        "nb_equipements": "Équipements",
        "nb_contrats_actifs": "Contrats actifs",
        "nb_contrats_inactifs": "Contrats inactifs",
        "esi_multi_meme_metier": "Multi même métier",
    })
    st.dataframe(df_esi_show.head(1000), use_container_width=True, hide_index=True, height=430)

with tab_qualite:
    section("Qualité des données", "Les anomalies sont volontairement séparées de la couverture pour ne pas masquer la donnée sale.")

    if df_qualite.empty:
        st.info("La table dashboard.qualite_donnees est absente ou vide.")
    else:
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            mini_card("Anomalies détail", len(df_qualite_filtered), "Lignes après filtres.")
        with q2:
            mini_card("Objets distincts", unique_count(df_qualite_filtered, "objet_reference"), "Compteur métier recommandé.")
        with q3:
            high = len(df_qualite_filtered[df_qualite_filtered.get("gravite", "").astype(str).str.lower().isin(["haute", "critique"])]) if "gravite" in df_qualite_filtered.columns else 0
            mini_card("Haute / critique", high, "Lignes de détail.")
        with q4:
            expired = unique_count(df_qualite_filtered[df_qualite_filtered.get("anomalie_type", "").astype(str) == "CONTRAT_ACTIF_DATE_FIN_DEPASSEE"], "objet_reference") if "anomalie_type" in df_qualite_filtered.columns else 0
            mini_card("Contrats actifs expirés", expired, "Contrats distincts.")

        st.divider()
        q_left, q_right = st.columns([1.15, 1])

        with q_left:
            if "anomalie_type" in df_qualite_filtered.columns:
                df_q = (
                    df_qualite_filtered.groupby("anomalie_type", as_index=False)["objet_reference"]
                    .nunique()
                    .rename(columns={"anomalie_type": "Anomalie", "objet_reference": "Objets distincts"})
                    .sort_values("Objets distincts", ascending=False)
                    .head(12)
                )
                plot_horizontal_bar(df_q, "Objets distincts", "Anomalie", color="#EA580C")
            else:
                st.info("Type d’anomalie indisponible.")

        with q_right:
            if "gravite" in df_qualite_filtered.columns:
                df_g = df_qualite_filtered.groupby("gravite", as_index=False)["objet_reference"].nunique()
                plot_donut(df_g["gravite"].tolist(), df_g["objet_reference"].tolist(), "Gravité")
            else:
                st.info("Gravité indisponible.")

        st.divider()
        show_detail = st.toggle("Afficher le détail des anomalies", value=True, key="vg_show_quality_detail")
        if show_detail:
            q_table = prepare_quality_table(df_qualite_filtered)
            st.markdown(f'<div class="vg-pill">{fmt_int(len(q_table))} ligne(s) détail</div>', unsafe_allow_html=True)
            st.dataframe(q_table.head(1500), use_container_width=True, hide_index=True, height=520)
            if len(q_table) > 1500:
                st.caption(f"Affichage limité aux 1 500 premières lignes sur {fmt_int(len(q_table))}.")

with tab_contrats:
    section("Liste des contrats", "Tableau synchronisé avec les filtres. Les contrats non rattachés sont exclus de cette table de couverture et remontés côté qualité.")

    opts1, opts2, opts3 = st.columns([1, 1, 2])
    with opts1:
        only_expired = st.toggle("Actifs expirés uniquement", value=False, key="vg_only_expired_contracts")
    with opts2:
        show_services = st.toggle("Codes prestation", value=False, key="vg_show_services")
    with opts3:
        if show_services and df_service_codes.empty:
            st.caption("La table dashboard.service_codes_light n’est pas disponible. Le tableau s’affiche sans codes de prestation.")

    contract_table = prepare_contract_table(
        df_contrats_filtered,
        df_service_codes,
        show_services=show_services,
        only_expired=only_expired,
    )

    st.markdown(
        f"""
        <div class="vg-table-shell">
            <span class="vg-pill">{fmt_int(len(contract_table))} ligne(s)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if contract_table.empty:
        st.info("Aucun contrat trouvé pour le périmètre sélectionné.")
    else:
        st.dataframe(contract_table.head(2500), use_container_width=True, hide_index=True, height=590)
        if len(contract_table) > 2500:
            st.caption(f"Affichage limité aux 2 500 premières lignes sur {fmt_int(len(contract_table))}.")

# Footer

st.caption(
    "Lecture métier : les KPI source décrivent ce qui existe dans Intent. Les KPI couverture décrivent uniquement ce qui est rattaché à un programme / ESI. Les anomalies qualité expliquent les écarts."
)
