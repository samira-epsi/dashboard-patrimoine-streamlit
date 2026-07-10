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

from common.app_config import setup_page
from common.ui_style import apply_3f_page_style
from common.filters import render_filtres_patrimoine
from config import DB_URL


# =====================================================
# SOURCES SUPABASE / POSTGRESQL
# =====================================================

SOURCE_ESI = "dashboard.esi_couverture"
SOURCE_CONTRATS = "dashboard.contrats_patrimoine"
SOURCE_GLOBAL = "dashboard.kpi_globale"
SOURCE_CREATIONS = "dashboard.kpi_creation_detail"
SOURCE_QUALITE = "dashboard.qualite_donnees"
SOURCE_QUALITE_RESUME = "dashboard.qualite_donnees_resume"

CACHE_TTL = 3600
SQL_TIMEOUT_MS = 20000


# =====================================================
# PALETTE CHARTE 3F
# =====================================================

C_NAVY = "#173B69"
C_NAVY_DEEP = "#0F2647"
C_RED = "#E5114D"
C_VIOLET = "#432ABD"
C_TEAL = "#008080"
C_BLUE = "#0074FF"
C_BLUE_LIGHT = "#80CDFF"
C_YELLOW = "#FFDC55"
C_PINK = "#FFB7E3"

C_GRID = "#EDF0F5"
C_INK = "#16233B"


# =====================================================
# PAGE + STYLE
# =====================================================

setup_page("Vue Globale", None)
apply_3f_page_style()


def _safe(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def inject_style():
    st.markdown(
        """
        <style>
        :root {
            --navy: #173B69;
            --navy-deep: #0F2647;
            --red: #E5114D;
            --violet: #432ABD;
            --teal: #008080;
            --blue: #0074FF;
            --blue-light: #80CDFF;
            --yellow: #FFDC55;
            --pink: #FFB7E3;

            --ink: #16233B;
            --ink-soft: #51617A;
            --ink-mute: #8493A8;
            --line: #E6EAF1;
            --line-soft: #EEF1F6;
            --surface: #FFFFFF;
            --canvas: #F4F6FA;
        }

        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .stApp {
            background: var(--canvas);
        }

        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 2.2rem !important;
            padding-right: 2.2rem !important;
            max-width: 1520px !important;
        }

        hr {
            border: none !important;
            border-top: 1px solid var(--line-soft) !important;
            margin: 22px 0 !important;
        }

        /* ---------- HERO ---------- */
        .vg-hero {
            position: relative;
            overflow: hidden;
            padding: 30px 34px;
            border-radius: 20px;
            background: linear-gradient(118deg, #173B69 0%, #1E4A82 58%, #0F2647 100%);
            box-shadow: 0 1px 2px rgba(23,59,105,0.10),
                        0 22px 44px -20px rgba(23,59,105,0.55);
            margin-bottom: 22px;
        }
        .vg-hero:before {
            content: "";
            position: absolute;
            left: 0; top: 0; right: 0;
            height: 4px;
            background: var(--red);
        }
        .vg-hero:after {
            content: "";
            position: absolute;
            width: 360px; height: 360px;
            right: -140px; top: -190px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0) 70%);
        }
        .vg-hero-eyebrow {
            position: relative; z-index: 1;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            color: rgba(255,255,255,0.72);
            font-size: 11.5px;
            font-weight: 700;
            letter-spacing: 1.4px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }
        .vg-hero-eyebrow:before {
            content: "";
            width: 22px; height: 2px;
            background: var(--red);
            border-radius: 99px;
        }
        .vg-hero-title {
            position: relative; z-index: 1;
            color: #FFFFFF;
            font-size: 34px;
            line-height: 1.08;
            letter-spacing: -0.6px;
            font-weight: 800;
            margin-bottom: 9px;
        }
        .vg-hero-subtitle {
            position: relative; z-index: 1;
            color: rgba(255,255,255,0.82);
            font-size: 14.5px;
            line-height: 1.55;
            font-weight: 500;
            max-width: 940px;
        }

        /* ---------- INFO ---------- */
        .vg-info {
            padding: 12px 16px;
            border-radius: 12px;
            background: #EFF3F9;
            border: 1px solid #E1E9F3;
            color: var(--ink-soft);
            font-size: 12.5px;
            font-weight: 500;
            line-height: 1.5;
            margin: 8px 0 16px 0;
        }

        /* ---------- SECTIONS ---------- */
        .vg-section-title {
            font-size: 20px;
            font-weight: 800;
            color: var(--navy);
            letter-spacing: -0.3px;
            margin-top: 2px;
            margin-bottom: 3px;
        }
        .vg-section-subtitle {
            color: var(--ink-soft);
            font-size: 13px;
            font-weight: 500;
            line-height: 1.5;
            margin-bottom: 14px;
            max-width: 920px;
        }
        .vg-mini-title {
            color: var(--navy);
            font-size: 14px;
            font-weight: 700;
            margin: 2px 0 10px 0;
        }

        /* ---------- KPI CARDS ---------- */
        .vg-card {
            min-height: 156px;
            border-radius: 16px;
            padding: 20px 20px 18px 20px;
            background: var(--surface);
            border: 1px solid var(--line);
            box-shadow: 0 1px 2px rgba(16,35,59,0.04),
                        0 12px 28px -20px rgba(16,35,59,0.35);
            position: relative;
            overflow: hidden;
            transition: transform .18s ease, box-shadow .18s ease;
        }
        .vg-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 1px 2px rgba(16,35,59,0.05),
                        0 18px 34px -20px rgba(16,35,59,0.42);
        }
        .vg-card-accent {
            width: 32px; height: 4px;
            border-radius: 99px;
            background: var(--accent, #173B69);
            margin-bottom: 15px;
        }
        .vg-card-label {
            color: var(--ink-mute);
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 10px;
        }
        .vg-card-value {
            color: var(--ink);
            font-size: 34px;
            font-weight: 800;
            letter-spacing: -1px;
            line-height: 1;
            margin-bottom: 12px;
        }
        .vg-card-pill {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 99px;
            background: color-mix(in srgb, var(--accent, #173B69) 11%, transparent);
            color: var(--accent, #173B69);
            font-size: 11.5px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .vg-card-help {
            color: var(--ink-mute);
            font-size: 11.5px;
            font-weight: 500;
            line-height: 1.45;
        }

        /* ---------- SYNTHESE (30 s) ---------- */
        .vg-synthese {
            display: flex;
            flex-wrap: wrap;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: 0 1px 2px rgba(16,35,59,0.04),
                        0 12px 28px -20px rgba(16,35,59,0.35);
            overflow: hidden;
            margin: 4px 0 6px 0;
        }
        .vg-syn-item {
            flex: 1 1 0;
            min-width: 172px;
            padding: 16px 22px;
            border-left: 1px solid var(--line-soft);
        }
        .vg-syn-item:first-child { border-left: none; }
        .vg-syn-label {
            color: var(--ink-mute);
            font-size: 10.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 9px;
        }
        .vg-syn-value {
            color: var(--ink);
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.8px;
            line-height: 1;
            margin-bottom: 7px;
        }
        .vg-syn-sub {
            font-size: 11.5px;
            font-weight: 600;
            line-height: 1.35;
        }
        .vg-syn-sub.ok { color: var(--teal); }
        .vg-syn-sub.warn { color: var(--red); }
        .vg-syn-sub.mute { color: var(--ink-mute); }

        /* ---------- ALERT CARDS ---------- */
        .vg-alert-card {
            min-height: 118px;
            border-radius: 14px;
            padding: 16px 18px;
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 3px solid var(--red);
            box-shadow: 0 1px 2px rgba(16,35,59,0.04);
        }
        .vg-alert-title {
            color: var(--ink-soft);
            font-size: 10.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 9px;
        }
        .vg-alert-value {
            color: var(--ink);
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
            line-height: 1;
            margin-bottom: 8px;
        }
        .vg-alert-help {
            color: var(--ink-mute);
            font-size: 11.5px;
            font-weight: 500;
            line-height: 1.4;
        }

        /* ---------- CHARTS + TABLES ---------- */
        div[data-testid="stPlotlyChart"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 12px;
            box-shadow: 0 1px 2px rgba(16,35,59,0.04);
        }
        div[data-testid="stDataFrame"] {
            border-radius: 14px !important;
            overflow: hidden !important;
            border: 1px solid var(--line) !important;
            box-shadow: 0 1px 2px rgba(16,35,59,0.04) !important;
            background: var(--surface) !important;
        }
        div[data-testid="stDataFrame"] [role="columnheader"] {
            background: #F5F7FB !important;
            color: var(--navy) !important;
            font-weight: 700 !important;
        }

        /* ---------- BUTTONS ---------- */
        .stButton button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid var(--line) !important;
            background: var(--surface) !important;
            color: var(--navy) !important;
            transition: all .15s ease !important;
        }
        .stButton button:hover {
            border-color: var(--navy) !important;
            background: #F5F7FB !important;
        }
        .stDownloadButton button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid var(--navy) !important;
            background: var(--navy) !important;
            color: #FFFFFF !important;
        }
        .stDownloadButton button:hover {
            background: var(--navy-deep) !important;
        }

        /* ---------- RESPONSIVE ---------- */
        @media screen and (max-width: 1100px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .vg-hero-title { font-size: 28px; }
            .vg-card-value { font-size: 30px; }
        }
        @media screen and (max-width: 760px) {
            .vg-hero { padding: 24px 20px; border-radius: 16px; }
            .vg-hero-title { font-size: 25px; }
            .vg-section-title { font-size: 18px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="vg-hero">
            <div class="vg-hero-eyebrow">Patrimoine 3F</div>
            <div class="vg-hero-title">{_safe(title)}</div>
            <div class="vg-hero-subtitle">{_safe(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="vg-section-title">{_safe(title)}</div>
        <div class="vg-section-subtitle">{_safe(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )


def info(text: str):
    st.markdown(f'<div class="vg-info">{_safe(text)}</div>', unsafe_allow_html=True)


def synthese_strip(items):
    """items = liste de tuples (label, valeur, sous_texte, tonalite) ; tonalite dans {ok, warn, mute}."""
    blocs = ""
    for label, value, sub, tone in items:
        sub_html = f'<div class="vg-syn-sub {tone}">{_safe(sub)}</div>' if sub else ""
        blocs += (
            '<div class="vg-syn-item">'
            f'<div class="vg-syn-label">{_safe(label)}</div>'
            f'<div class="vg-syn-value">{_safe(value)}</div>'
            f"{sub_html}"
            "</div>"
        )
    st.markdown(f'<div class="vg-synthese">{blocs}</div>', unsafe_allow_html=True)


inject_style()


# =====================================================
# CONNEXION
# =====================================================

@st.cache_resource
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


def tester_connexion():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        return False, str(e)


def table_exists(conn, source: str) -> bool:
    return conn.execute(text("SELECT to_regclass(:source)"), {"source": source}).scalar() is not None


def verifier_sources(conn):
    required = [SOURCE_ESI, SOURCE_CONTRATS, SOURCE_GLOBAL]
    missing = [src for src in required if not table_exists(conn, src)]
    return missing


# =====================================================
# FORMAT + NETTOYAGE
# =====================================================

def fmt_nombre(value):
    try:
        return f"{int(float(value or 0)):,}".replace(",", " ")
    except Exception:
        return "0"


def fmt_pourcentage(value):
    try:
        return f"{float(value):.1f} %".replace(".", ",")
    except Exception:
        return "0,0 %"


def fmt_date(value):
    try:
        if pd.isna(value):
            return ""
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except Exception:
        return ""


def aujourd_hui_france():
    return datetime.now(ZoneInfo("Europe/Paris")).date()


def nettoyer_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    ref_cols = [
        "esi_reference",
        "contract_reference",
        "objet_reference",
        "third_party_id",
    ]

    text_cols = [
        "esi_label",
        "societe",
        "agence",
        "groupe",
        "secteur",
        "contract_label",
        "contract_status",
        "contract_topic",
        "third_party_label",
        "objet_type",
        "objet_label",
        "anomalie_type",
        "gravite",
        "description",
    ]

    num_cols = [
        "nb_logements",
        "nb_equipements",
        "nb_contrats_actifs",
        "nb_contrats_inactifs",
        "nb_prestataires_actifs",
        "nb_contrats_actifs_date_depassee",
        "esi_couvert",
        "esi_multi_couvert",
        "esi_multi_meme_metier",
        "esi_sans_contrat",
        "esi_sans_equipement",
    ]

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
                .replace("", "Non renseigné")
                .replace("nan", "Non renseigné")
                .replace("undefined", "Non renseigné")
            )

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def normaliser_contrats(df: pd.DataFrame) -> pd.DataFrame:
    df = nettoyer_df(df)

    if "contract_status" not in df.columns:
        df["contract_status"] = "Non renseigné"

    df["contract_status_clean"] = (
        df["contract_status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    for col in ["contract_start_date", "contract_end_date"]:
        if col not in df.columns:
            df[col] = pd.NaT
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def normaliser_creations(df: pd.DataFrame) -> pd.DataFrame:
    df = nettoyer_df(df)
    if "creation_date" in df.columns:
        df["creation_date"] = pd.to_datetime(df["creation_date"], errors="coerce")
    else:
        df["creation_date"] = pd.NaT
    return df


def dedupliquer_esi(df_esi: pd.DataFrame) -> pd.DataFrame:
    if df_esi.empty:
        return df_esi.copy()

    if "esi_reference" not in df_esi.columns:
        return df_esi.drop_duplicates().copy()

    df = df_esi[df_esi["esi_reference"].notna()].copy()
    if df.empty:
        return df

    num_cols = [
        "nb_logements",
        "nb_equipements",
        "nb_contrats_actifs",
        "nb_contrats_inactifs",
        "nb_prestataires_actifs",
        "nb_contrats_actifs_date_depassee",
        "esi_couvert",
        "esi_multi_couvert",
        "esi_multi_meme_metier",
        "esi_sans_contrat",
        "esi_sans_equipement",
    ]

    agg = {}
    for col in df.columns:
        if col == "esi_reference":
            continue
        agg[col] = "max" if col in num_cols else "first"

    return df.groupby("esi_reference", as_index=False).agg(agg)


def liste_refs_valides(df: pd.DataFrame, colonne: str):
    if colonne not in df.columns:
        return []

    s = df[colonne].dropna().astype(str).str.strip()
    s = s[~s.isin(["", "nan", "None", "<NA>", "Non renseigné"])]
    return s.unique().tolist()


def refs_ont_change(df_base: pd.DataFrame, df_filtre: pd.DataFrame, colonne: str) -> bool:
    if colonne not in df_base.columns or colonne not in df_filtre.columns:
        return False
    return set(liste_refs_valides(df_base, colonne)) != set(liste_refs_valides(df_filtre, colonne))


# =====================================================
# CHARGEMENT DATA
# =====================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def charger_donnees():
    try:
        with get_engine().connect() as conn:
            conn.execute(text(f"SET statement_timeout = {SQL_TIMEOUT_MS}"))

            missing = verifier_sources(conn)
            if missing:
                raise RuntimeError("Sources SQL manquantes : " + ", ".join(missing))

            df_global = pd.read_sql_query(
                text(f"SELECT * FROM {SOURCE_GLOBAL} ORDER BY date_maj DESC NULLS LAST LIMIT 1"),
                conn,
            )

            df_esi = pd.read_sql_query(text(f"SELECT * FROM {SOURCE_ESI}"), conn)
            df_contrats = pd.read_sql_query(text(f"SELECT * FROM {SOURCE_CONTRATS}"), conn)

            if table_exists(conn, SOURCE_CREATIONS):
                df_creations = pd.read_sql_query(text(f"SELECT * FROM {SOURCE_CREATIONS}"), conn)
            else:
                df_creations = pd.DataFrame()

            if table_exists(conn, SOURCE_QUALITE):
                df_qualite = pd.read_sql_query(text(f"SELECT * FROM {SOURCE_QUALITE}"), conn)
            else:
                df_qualite = pd.DataFrame()

            if table_exists(conn, SOURCE_QUALITE_RESUME):
                df_qualite_resume = pd.read_sql_query(text(f"SELECT * FROM {SOURCE_QUALITE_RESUME}"), conn)
            else:
                df_qualite_resume = pd.DataFrame()

    except SQLAlchemyError as e:
        raise RuntimeError(f"Erreur PostgreSQL : {e}") from e

    df_esi = nettoyer_df(df_esi)
    df_contrats = normaliser_contrats(df_contrats)
    df_creations = normaliser_creations(df_creations)
    df_qualite = normaliser_contrats(df_qualite) if not df_qualite.empty else df_qualite
    df_qualite_resume = nettoyer_df(df_qualite_resume) if not df_qualite_resume.empty else df_qualite_resume

    return df_global, df_esi, df_contrats, df_creations, df_qualite, df_qualite_resume


# =====================================================
# FILTRES + CALCULS
# =====================================================

def valeur_filtre_active(valeur) -> bool:
    valeurs_vides = {
        "",
        "Tous",
        "Toutes",
        "Tous les contrats",
        "Toutes les sociétés",
        "Toutes les agences",
        "Tous les groupes",
        "Tous les secteurs",
        "Tous les programmes",
        "Tous les métiers",
        "Tous les prestataires",
        "None",
        "nan",
        "<NA>",
    }

    if valeur is None:
        return False

    if isinstance(valeur, (pd.Series, pd.Index)):
        valeur = valeur.tolist()

    if isinstance(valeur, (list, tuple, set)):
        return len([str(v).strip() for v in valeur if str(v).strip() not in valeurs_vides]) > 0

    return str(valeur).strip() not in valeurs_vides


def filtre_contrat_est_actif(filtres_selectionnes, statut_selectionne, df_esi, df_esi_filtre, df_contrats, df_contrats_filtre):
    if statut_selectionne is not None:
        return True

    mots_cles_contrat = ["metier", "métier", "topic", "prestataire", "third", "contrat", "contract"]

    if filtres_selectionnes:
        for cle, valeur in filtres_selectionnes.items():
            cle_clean = str(cle).lower()
            if any(mot in cle_clean for mot in mots_cles_contrat) and valeur_filtre_active(valeur):
                return True

    esi_change = refs_ont_change(df_esi, df_esi_filtre, "esi_reference")
    contrats_change = refs_ont_change(df_contrats, df_contrats_filtre, "contract_reference")

    return contrats_change and not esi_change


def afficher_filtre_statut_contrat():
    choix = st.radio(
        "Statut des contrats",
        ["Tous les contrats", "Contrats actifs", "Contrats inactifs"],
        horizontal=True,
        key="vg_filtre_statut_contrat",
    )

    if choix == "Contrats actifs":
        return "active"
    if choix == "Contrats inactifs":
        return "inactive"
    return None


def filtrer_contrats_par_statut(df_contrats: pd.DataFrame, statut):
    df = normaliser_contrats(df_contrats)

    if statut is None:
        return df.copy()

    if statut == "active":
        return df[df["contract_status_clean"] == "active"].copy()

    if statut == "inactive":
        return df[df["contract_status_clean"] != "active"].copy()

    return df.copy()


def filtrer_esi_depuis_contrats(df_esi: pd.DataFrame, df_contrats: pd.DataFrame, appliquer_filtre_contrat: bool):
    if not appliquer_filtre_contrat:
        return df_esi.copy()

    if df_contrats.empty:
        return df_esi.iloc[0:0].copy()

    refs = liste_refs_valides(df_contrats, "esi_reference")
    if not refs:
        return df_esi.iloc[0:0].copy()

    return df_esi[df_esi["esi_reference"].isin(refs)].copy()


def calcul_nouveaux_ce_mois(df_creations, objet_type, object_refs=None, esi_refs=None):
    if df_creations.empty or "objet_type" not in df_creations.columns:
        return 0

    df = df_creations[df_creations["objet_type"] == objet_type].copy()

    if object_refs is not None and "objet_reference" in df.columns:
        df = df[df["objet_reference"].isin(object_refs)]

    if esi_refs is not None and "esi_reference" in df.columns:
        df = df[df["esi_reference"].isin(esi_refs)]

    today = pd.Timestamp.today().normalize()
    debut_mois = today.replace(day=1)
    demain = today + pd.Timedelta(days=1)

    return df[
        df["creation_date"].notna()
        & (df["creation_date"] >= debut_mois)
        & (df["creation_date"] < demain)
    ]["objet_reference"].nunique()


def contrats_actifs_fin_depassee(df_contrats: pd.DataFrame) -> pd.DataFrame:
    if df_contrats.empty:
        return df_contrats.copy()

    today = pd.Timestamp(aujourd_hui_france())
    df = df_contrats.copy()
    df["contract_end_date"] = pd.to_datetime(df["contract_end_date"], errors="coerce")

    out = df[
        (df["contract_status_clean"] == "active")
        & df["contract_end_date"].notna()
        & (df["contract_end_date"] < today)
    ].copy()

    return out.sort_values(["contract_end_date", "contract_reference"]).drop_duplicates("contract_reference")


def global_value(df_global: pd.DataFrame, col: str, default=0):
    if df_global.empty or col not in df_global.columns:
        return default
    try:
        return df_global.iloc[0][col]
    except Exception:
        return default


# =====================================================
# COMPOSANTS VISUELS
# =====================================================

def kpi_card(label, value, pill, help_text, accent=C_NAVY):
    st.markdown(
        f"""
        <div class="vg-card" style="--accent:{_safe(accent)};">
            <div class="vg-card-accent"></div>
            <div class="vg-card-label">{_safe(label)}</div>
            <div class="vg-card-value">{_safe(fmt_nombre(value))}</div>
            <div class="vg-card-pill">{_safe(pill)}</div>
            <div class="vg-card-help">{_safe(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_card(title, value, help_text):
    st.markdown(
        f"""
        <div class="vg-alert-card">
            <div class="vg-alert-title">{_safe(title)}</div>
            <div class="vg-alert-value">{_safe(fmt_nombre(value))}</div>
            <div class="vg-alert-help">{_safe(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _layout_plotly(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=24, t=10, b=18),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color=C_INK),
        showlegend=False,
    )
    return fig


def construire_couverture(df_esi_base, df_esi_couverts, utiliser_selection_contrats):
    base = dedupliquer_esi(df_esi_base)

    if base.empty:
        return pd.DataFrame({
            "Indicateur": ["Programmes", "Logements", "Équipements"],
            "Couverts": [0, 0, 0],
            "Total": [0, 0, 0],
            "Taux": [0.0, 0.0, 0.0],
        })

    for col in ["nb_logements", "nb_equipements", "esi_couvert"]:
        if col not in base.columns:
            base[col] = 0
        base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0)

    if utiliser_selection_contrats:
        refs_couverts = set(liste_refs_valides(df_esi_couverts, "esi_reference"))
        couverts = base[base["esi_reference"].isin(refs_couverts)].copy()
    else:
        couverts = base[base["esi_couvert"] > 0].copy()

    data = [
        ("Programmes", len(liste_refs_valides(couverts, "esi_reference")), len(liste_refs_valides(base, "esi_reference"))),
        ("Logements", int(couverts["nb_logements"].sum()), int(base["nb_logements"].sum())),
        ("Équipements", int(couverts["nb_equipements"].sum()), int(base["nb_equipements"].sum())),
    ]

    rows = []
    for indicateur, couv, total in data:
        taux = round((couv / total) * 100, 1) if total else 0.0
        rows.append({"Indicateur": indicateur, "Couverts": couv, "Total": total, "Taux": taux})

    return pd.DataFrame(rows)


def afficher_couverture(df_couverture: pd.DataFrame):
    if df_couverture.empty:
        st.info("Aucune donnée de couverture disponible.")
        return

    df = df_couverture.copy().sort_values("Taux", ascending=True)
    df["Texte"] = df.apply(lambda r: f"{fmt_pourcentage(r['Taux'])}", axis=1)
    df["Détail"] = df.apply(lambda r: f"{fmt_nombre(r['Couverts'])} / {fmt_nombre(r['Total'])}", axis=1)

    if go is None:
        st.bar_chart(df.set_index("Indicateur")["Taux"], use_container_width=True)
        return

    fig = go.Figure()
    # rail de fond (100 %) pour lire la progression d'un coup d'oeil
    fig.add_trace(
        go.Bar(
            x=[100] * len(df),
            y=df["Indicateur"],
            orientation="h",
            marker=dict(color="#EEF1F6"),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["Taux"],
            y=df["Indicateur"],
            orientation="h",
            text=df["Texte"],
            textposition="auto",
            insidetextfont=dict(color="white"),
            customdata=df["Détail"],
            hovertemplate="<b>%{y}</b><br>Taux : %{x:.1f} %<br>Détail : %{customdata}<extra></extra>",
            marker=dict(color=C_NAVY),
        )
    )
    _layout_plotly(fig, 300)
    fig.update_layout(
        barmode="overlay",
        bargap=0.42,
        xaxis=dict(range=[0, 100], ticksuffix=" %", gridcolor=C_GRID, zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def construire_exploitabilite(df_global: pd.DataFrame) -> pd.DataFrame:
    def gv(col):
        return int(float(global_value(df_global, col, 0) or 0))

    lignes = [
        ("Contrats", gv("contrats_total"), gv("contrats_rattaches_programme")),
        ("Logements", gv("logements_total"), gv("logements_rattaches_programme")),
        ("Équipements", gv("equipements_total"), gv("equipements_rattaches_programme")),
    ]

    rows = []
    for nom, total, expl in lignes:
        gap = max(total - expl, 0)
        taux = round((expl / total) * 100, 1) if total else 0.0
        rows.append({
            "Entité": nom,
            "Total": total,
            "Exploitable": expl,
            "Non exploitable": gap,
            "Taux": taux,
        })
    return pd.DataFrame(rows)


def afficher_exploitabilite(df: pd.DataFrame):
    if df.empty:
        st.info("Aucune donnée d’exploitabilité disponible.")
        return

    df = df.copy().sort_values("Taux", ascending=True)

    if go is None:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    tot = df["Total"].replace(0, 1)
    pct_expl = df["Exploitable"] / tot * 100
    pct_gap = 100 - pct_expl

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["Entité"],
            x=pct_expl,
            orientation="h",
            name="Exploitable",
            marker=dict(color=C_TEAL),
            text=df["Exploitable"].apply(fmt_nombre),
            textposition="auto",
            insidetextfont=dict(color="white"),
            customdata=df["Taux"],
            hovertemplate="<b>%{y}</b><br>Exploitable : %{customdata:.1f} %<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=df["Entité"],
            x=pct_gap,
            orientation="h",
            name="Non exploitable",
            marker=dict(color="#F4C4CF"),
            text=df["Non exploitable"].apply(fmt_nombre),
            textposition="auto",
            insidetextfont=dict(color=C_RED),
            hovertemplate="<b>%{y}</b><br>Non exploitable : %{x:.1f} %<extra></extra>",
        )
    )
    _layout_plotly(fig, 250)
    fig.update_layout(
        barmode="stack",
        bargap=0.45,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0, font=dict(size=11)),
        xaxis=dict(range=[0, 100], ticksuffix=" %", gridcolor=C_GRID, zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def construire_graph_metier(df_contrats: pd.DataFrame, top_n=12):
    if df_contrats.empty:
        return pd.DataFrame(columns=["Métier", "Contrats"])

    df = df_contrats.copy()
    df["contract_topic"] = df.get("contract_topic", "Non renseigné")
    df["contract_topic"] = df["contract_topic"].fillna("Non renseigné").astype(str).str.strip().replace("", "Non renseigné")

    out = (
        df.drop_duplicates(["contract_reference", "contract_topic"])
        .groupby("contract_topic", as_index=False)["contract_reference"]
        .nunique()
        .rename(columns={"contract_topic": "Métier", "contract_reference": "Contrats"})
        .sort_values("Contrats", ascending=False)
        .head(top_n)
        .sort_values("Contrats", ascending=True)
    )
    return out


def afficher_barres_horizontales(df: pd.DataFrame, label_col: str, value_col: str, color=C_RED, height_base=320):
    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    if go is None:
        st.bar_chart(df.set_index(label_col)[value_col], use_container_width=True)
        return

    max_value = max(float(df[value_col].max()), 1.0)
    height = max(height_base, 34 * len(df) + 80)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df[value_col],
            y=df[label_col],
            orientation="h",
            text=df[value_col].apply(fmt_nombre),
            textposition="outside",
            textfont=dict(color=C_INK, size=12),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Nombre : %{x}<extra></extra>",
            marker=dict(color=color),
        )
    )
    _layout_plotly(fig, height)
    fig.update_layout(
        bargap=0.36,
        margin=dict(l=10, r=52, t=10, b=18),
        xaxis=dict(range=[0, max_value * 1.18], gridcolor=C_GRID, zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def construire_graph_qualite(df_resume: pd.DataFrame, df_qualite: pd.DataFrame):
    if not df_resume.empty and {"anomalie_type", "nb_objets_distincts"}.issubset(df_resume.columns):
        df = df_resume.copy()
        df["nb_objets_distincts"] = pd.to_numeric(df["nb_objets_distincts"], errors="coerce").fillna(0)
        return (
            df.groupby("anomalie_type", as_index=False)["nb_objets_distincts"]
            .sum()
            .rename(columns={"anomalie_type": "Anomalie", "nb_objets_distincts": "Objets distincts"})
            .sort_values("Objets distincts", ascending=False)
            .head(8)
            .sort_values("Objets distincts", ascending=True)
        )

    if not df_qualite.empty and {"anomalie_type", "objet_reference"}.issubset(df_qualite.columns):
        return (
            df_qualite.groupby("anomalie_type", as_index=False)["objet_reference"]
            .nunique()
            .rename(columns={"anomalie_type": "Anomalie", "objet_reference": "Objets distincts"})
            .sort_values("Objets distincts", ascending=False)
            .head(8)
            .sort_values("Objets distincts", ascending=True)
        )

    return pd.DataFrame(columns=["Anomalie", "Objets distincts"])


def dataframe_download(label: str, df: pd.DataFrame, filename: str):
    if df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(label, csv, file_name=filename, mime="text/csv", use_container_width=True)


# =====================================================
# DÉTAILS QUALITÉ + RECHERCHE
# =====================================================

def preparer_contrats_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = [
        "contract_reference",
        "contract_label",
        "third_party_label",
        "contract_start_date",
        "contract_end_date",
        "contract_topic",
        "contract_status",
        "societe",
        "agence",
        "groupe",
        "secteur",
        "esi_reference",
        "esi_label",
    ]
    cols = [c for c in cols if c in df.columns]
    out = df[cols].copy()

    for col in ["contract_start_date", "contract_end_date"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

    return out.rename(
        columns={
            "contract_reference": "Référence contrat",
            "contract_label": "Libellé contrat",
            "third_party_label": "Prestataire",
            "contract_start_date": "Date de début",
            "contract_end_date": "Date de fin",
            "contract_topic": "Métier",
            "contract_status": "Statut",
            "societe": "Société",
            "agence": "Agence",
            "groupe": "Groupe",
            "secteur": "Secteur",
            "esi_reference": "Référence ESI",
            "esi_label": "Libellé ESI",
        }
    )


def preparer_esi_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = [
        "esi_reference",
        "esi_label",
        "societe",
        "agence",
        "groupe",
        "secteur",
        "nb_logements",
        "nb_equipements",
        "nb_contrats_actifs",
        "nb_contrats_inactifs",
        "esi_couvert",
        "esi_multi_meme_metier",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].copy().rename(
        columns={
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
            "esi_couvert": "ESI couvert",
            "esi_multi_meme_metier": "Multi même métier",
        }
    )


def preparer_qualite_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = [
        "anomalie_type",
        "objet_type",
        "objet_reference",
        "objet_label",
        "gravite",
        "description",
        "societe",
        "agence",
        "groupe",
        "secteur",
        "esi_reference",
        "esi_label",
        "contract_topic",
        "third_party_label",
        "contract_status",
        "contract_end_date",
    ]
    cols = [c for c in cols if c in df.columns]
    out = df[cols].copy()

    if "contract_end_date" in out.columns:
        out["contract_end_date"] = pd.to_datetime(out["contract_end_date"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

    return out.rename(
        columns={
            "anomalie_type": "Type anomalie",
            "objet_type": "Type objet",
            "objet_reference": "Référence objet",
            "objet_label": "Libellé objet",
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
            "contract_end_date": "Date de fin contrat",
        }
    )


def filtrer_table_recherche(df: pd.DataFrame, recherche: str) -> pd.DataFrame:
    if df.empty or not recherche:
        return df.copy()

    recherche = str(recherche).strip().lower()
    if not recherche:
        return df.copy()

    masque = pd.Series(False, index=df.index)
    for col in df.columns:
        masque = masque | df[col].fillna("").astype(str).str.lower().str.contains(recherche, regex=False, na=False)
    return df[masque].copy()


def afficher_detail_qualite(focus, df_contrats_kpi, df_esi_context, df_qualite, df_global):
    if not focus:
        return

    st.markdown("---")

    if focus == "expired":
        section("Détail : contrats actifs avec date de fin dépassée", "Contrats exploitables dans le périmètre filtré.")
        table = preparer_contrats_table(contrats_actifs_fin_depassee(df_contrats_kpi))
        if table.empty:
            st.success("Aucun contrat actif expiré dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), use_container_width=True, hide_index=True, height=360)
            dataframe_download("Télécharger les contrats expirés", table, "contrats_actifs_expires.csv")

    elif focus == "unlinked_contracts":
        section("Détail : contrats non rattachés", "Contrats présents en source mais absents de la couverture programme.")
        table = df_qualite[df_qualite.get("anomalie_type", "") == "CONTRAT_NON_RATTACHE_PROGRAMME"].copy() if not df_qualite.empty else pd.DataFrame()
        table = preparer_qualite_table(table)
        if table.empty:
            st.info("Aucun détail disponible dans la table qualité.")
        else:
            st.dataframe(table.head(500), use_container_width=True, hide_index=True, height=360)
            dataframe_download("Télécharger les contrats non rattachés", table, "contrats_non_rattaches.csv")

    elif focus == "housing":
        section("Détail : logements sans programme", "Logements non exploitables dans les calculs de couverture ESI.")
        table = df_qualite[df_qualite.get("anomalie_type", "") == "LOGEMENT_SANS_PROGRAMME"].copy() if not df_qualite.empty else pd.DataFrame()
        table = preparer_qualite_table(table)
        if table.empty:
            st.info("Aucun détail disponible dans la table qualité.")
        else:
            st.dataframe(table.head(500), use_container_width=True, hide_index=True, height=360)
            dataframe_download("Télécharger les logements sans programme", table, "logements_sans_programme.csv")
            if len(table) > 500:
                st.caption(f"Affichage limité à 500 lignes sur {fmt_nombre(len(table))}.")

    elif focus == "multi_topic":
        section("Détail : ESI avec plusieurs contrats actifs sur le même métier", "Ce signal peut révéler des doublons ou des chevauchements de contrats.")
        if "esi_multi_meme_metier" not in df_esi_context.columns:
            st.info("La colonne esi_multi_meme_metier n'est pas disponible.")
            return
        table = df_esi_context[pd.to_numeric(df_esi_context["esi_multi_meme_metier"], errors="coerce").fillna(0) > 0].copy()
        table = preparer_esi_table(table)
        if table.empty:
            st.success("Aucun ESI multi même métier dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), use_container_width=True, hide_index=True, height=360)
            dataframe_download("Télécharger les ESI multi même métier", table, "esi_multi_meme_metier.csv")

    elif focus == "no_contract":
        section("Détail : ESI sans contrat actif", "Programmes sans contrat actif rattaché dans le périmètre affiché.")
        table = df_esi_context[pd.to_numeric(df_esi_context.get("nb_contrats_actifs", 0), errors="coerce").fillna(0) == 0].copy()
        table = preparer_esi_table(table)
        if table.empty:
            st.success("Aucun ESI sans contrat actif dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), use_container_width=True, hide_index=True, height=360)
            dataframe_download("Télécharger les ESI sans contrat actif", table, "esi_sans_contrat_actif.csv")


# =====================================================
# PAGE
# =====================================================

hero(
    "Vue lalalalal",
    "Une lecture simple : volumes réels, données exploitables pour la couverture, puis points d’attention qualité.",
)

ok, erreur = tester_connexion()
if not ok:
    st.error("Connexion PostgreSQL impossible.")
    st.code(erreur)
    st.stop()

col_refresh, col_update = st.columns([1, 4])
with col_refresh:
    if st.button("Actualiser l’affichage", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    with st.spinner("Chargement des données..." ):
        df_global, df_esi, df_contrats, df_creations, df_qualite, df_qualite_resume = charger_donnees()
except Exception as e:
    st.error("Erreur pendant le chargement des données.")
    st.code(str(e))
    st.stop()

if df_global.empty:
    st.error("La table dashboard.kpi_globale est vide.")
    st.stop()

# =====================================================
# SYNTHESE — LA VERITE EN 30 SECONDES (VUE SOURCE)
# =====================================================

section(
    "En un coup d’œil",
    "État source du patrimoine, indépendant des filtres. Le volume réel, la part exploitable, la couverture et ce qui bloque.",
)

_syn_contrats_total = int(float(global_value(df_global, "contrats_total", 0) or 0))
_syn_contrats_expl = int(float(global_value(df_global, "contrats_rattaches_programme", 0) or 0))
_syn_contrats_nonr = int(float(global_value(df_global, "contrats_non_rattaches_programme", 0) or 0))
_syn_esi_total = int(float(global_value(df_global, "programmes_total", 0) or 0))
_syn_esi_couv = int(pd.to_numeric(df_esi.get("esi_couvert", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
_syn_esi_sans = int(pd.to_numeric(df_esi.get("esi_sans_contrat", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
_syn_taux = round((_syn_esi_couv / _syn_esi_total) * 100, 1) if _syn_esi_total else 0.0
_syn_log_sans = int(float(global_value(df_global, "logements_sans_programme", 0) or 0))
_syn_contrats_exp = int(float(global_value(df_global, "contrats_actifs_fin_depassee", 0) or 0))

synthese_strip([
    ("Contrats", fmt_nombre(_syn_contrats_total),
     f"{fmt_nombre(_syn_contrats_expl)} exploitables · {fmt_nombre(_syn_contrats_nonr)} non rattachés", "mute"),
    ("Programmes / ESI", fmt_nombre(_syn_esi_total),
     f"{fmt_nombre(_syn_esi_couv)} couverts · {fmt_nombre(_syn_esi_sans)} sans contrat", "mute"),
    ("Couverture programmes", fmt_pourcentage(_syn_taux),
     f"{fmt_nombre(_syn_esi_couv)} ESI sur {fmt_nombre(_syn_esi_total)} couverts", "ok" if _syn_taux >= 80 else "warn"),
    ("Logements sans programme", fmt_nombre(_syn_log_sans),
     "Exclus du calcul de couverture", "warn"),
    ("Contrats actifs expirés", fmt_nombre(_syn_contrats_exp),
     "Date de fin dépassée", "warn"),
])

st.divider()

# =====================================================
# FILTRES EXISTANTS
# =====================================================

info("Les filtres ci-dessous pilotent les indicateurs, les graphiques et les tableaux de détail. Les totaux source restent séparés des données exploitables.")

df_esi_filtre, df_contrats_filtre, filtres_selectionnes = render_filtres_patrimoine(
    df_esi=df_esi,
    df_contrats=df_contrats,
)

st.divider()
section("Périmètre contrat", "Le statut contrat affine les indicateurs sans changer les filtres patrimoine existants.")
statut_selectionne = afficher_filtre_statut_contrat()

df_contrats_kpi = filtrer_contrats_par_statut(df_contrats_filtre, statut_selectionne)

perimetre_commun_actif = (
    refs_ont_change(df_esi, df_esi_filtre, "esi_reference")
    or refs_ont_change(df_contrats, df_contrats_filtre, "contract_reference")
)
perimetre_filtre_actif = perimetre_commun_actif or statut_selectionne is not None

filtre_contrat_actif = filtre_contrat_est_actif(
    filtres_selectionnes=filtres_selectionnes,
    statut_selectionne=statut_selectionne,
    df_esi=df_esi,
    df_esi_filtre=df_esi_filtre,
    df_contrats=df_contrats,
    df_contrats_filtre=df_contrats_filtre,
)

df_esi_kpi = filtrer_esi_depuis_contrats(df_esi_filtre, df_contrats_kpi, filtre_contrat_actif)
df_esi_base = dedupliquer_esi(df_esi_filtre)
df_esi_context = dedupliquer_esi(df_esi_kpi)

# =====================================================
# VUE D'ENSEMBLE
# =====================================================

st.divider()
section(
    "Vue d’ensemble",
    "Les cartes affichent la situation du périmètre. Sans filtre, elles montrent la réalité source et ce qui est exploitable pour la couverture.",
)

if not perimetre_filtre_actif:
    contrats_value = global_value(df_global, "contrats_total")
    contrats_pill = f"{fmt_nombre(global_value(df_global, 'contrats_rattaches_programme'))} exploitables"
    contrats_help = f"{fmt_nombre(global_value(df_global, 'contrats_non_rattaches_programme'))} contrats ne sont pas rattachés à un programme."

    programmes_value = global_value(df_global, "programmes_total")
    programmes_couverts = int(pd.to_numeric(df_esi["esi_couvert"], errors="coerce").fillna(0).sum()) if "esi_couvert" in df_esi.columns else 0
    programmes_sans = int(pd.to_numeric(df_esi["esi_sans_contrat"], errors="coerce").fillna(0).sum()) if "esi_sans_contrat" in df_esi.columns else 0
    programmes_pill = f"{fmt_nombre(programmes_couverts)} couverts"
    programmes_help = f"{fmt_nombre(programmes_sans)} programmes / ESI n'ont pas de contrat actif."

    logements_value = global_value(df_global, "logements_total")
    logements_pill = f"{fmt_nombre(global_value(df_global, 'logements_rattaches_programme'))} exploitables"
    logements_help = f"{fmt_nombre(global_value(df_global, 'logements_sans_programme'))} logements sont sans programme."

    equipements_value = global_value(df_global, "equipements_total")
    equipements_pill = f"{fmt_nombre(global_value(df_global, 'equipements_rattaches_programme'))} exploitables"
    equipements_help = f"{fmt_nombre(global_value(df_global, 'equipements_sans_programme'))} équipement(s) sans programme."
else:
    contrats_value = len(liste_refs_valides(df_contrats_kpi, "contract_reference"))
    nouveaux_contrats = calcul_nouveaux_ce_mois(df_creations, "contrat", object_refs=liste_refs_valides(df_contrats_kpi, "contract_reference"))
    contrats_pill = f"+{fmt_nombre(nouveaux_contrats)} ce mois-ci"
    contrats_help = "Contrats exploitables dans le périmètre filtré."

    programmes_value = len(liste_refs_valides(df_esi_context, "esi_reference"))
    programmes_couverts = int(pd.to_numeric(df_esi_context.get("esi_couvert", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    programmes_sans = int(pd.to_numeric(df_esi_context.get("esi_sans_contrat", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    programmes_pill = f"{fmt_nombre(programmes_couverts)} couverts"
    programmes_help = f"{fmt_nombre(programmes_sans)} programmes / ESI sans contrat actif dans le périmètre."

    logements_value = int(pd.to_numeric(df_esi_context.get("nb_logements", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    nouveaux_logements = calcul_nouveaux_ce_mois(df_creations, "logement", esi_refs=liste_refs_valides(df_esi_context, "esi_reference"))
    logements_pill = f"+{fmt_nombre(nouveaux_logements)} ce mois-ci"
    logements_help = "Logements rattachés aux ESI du périmètre filtré."

    equipements_value = int(pd.to_numeric(df_esi_context.get("nb_equipements", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    nouveaux_equipements = calcul_nouveaux_ce_mois(df_creations, "equipement", esi_refs=liste_refs_valides(df_esi_context, "esi_reference"))
    equipements_pill = f"+{fmt_nombre(nouveaux_equipements)} ce mois-ci"
    equipements_help = "Équipements rattachés aux ESI du périmètre filtré."

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Contrats", contrats_value, contrats_pill, contrats_help, accent=C_NAVY)
with c2:
    kpi_card("Programmes / ESI", programmes_value, programmes_pill, programmes_help, accent=C_BLUE)
with c3:
    kpi_card("Logements", logements_value, logements_pill, logements_help, accent=C_TEAL)
with c4:
    kpi_card("Équipements", equipements_value, equipements_pill, equipements_help, accent=C_VIOLET)

# =====================================================
# SOURCE VS EXPLOITABLE
# =====================================================

st.divider()
section(
    "Réalité source et données exploitables",
    "Tout ce qui existe dans Intent n’est pas utilisable pour la couverture. Un logement sans programme ou un contrat non rattaché existe bien, mais ne peut pas entrer proprement dans un calcul ESI. Voici la part réellement exploitable et l’écart, sans le cacher.",
)

st.markdown('<div class="vg-mini-title">Part exploitable par entité (vue source)</div>', unsafe_allow_html=True)
df_exploitabilite = construire_exploitabilite(df_global)
afficher_exploitabilite(df_exploitabilite)
st.caption(
    "Barres en proportion, valeurs affichées en volumes réels. "
    "« Exploitable » signifie rattaché à un programme, ce qui est distinct de « couvert » (au moins un contrat actif) mesuré plus bas."
)

# =====================================================
# COUVERTURE
# =====================================================

st.divider()
section(
    "Couverture du patrimoine",
    "Lecture simple : part du patrimoine exploitable couverte par au moins un contrat actif. La couverture stricte métier par équipement sera une couche dédiée.",
)

col_cov, col_metier = st.columns([1, 1.18])

with col_cov:
    st.markdown('<div class="vg-mini-title">Taux de couverture</div>', unsafe_allow_html=True)
    df_couverture = construire_couverture(df_esi_base, df_esi_context, filtre_contrat_actif)
    afficher_couverture(df_couverture)

    if filtre_contrat_actif:
        st.caption("Le taux mesure la part du patrimoine filtré touchée par les contrats sélectionnés.")
    else:
        st.caption("Le taux mesure les ESI ayant au moins un contrat actif. Les données sans programme sont exclues de ce calcul.")

with col_metier:
    st.markdown('<div class="vg-mini-title">Contrats par métier</div>', unsafe_allow_html=True)
    df_metier = construire_graph_metier(df_contrats_kpi, top_n=12)
    afficher_barres_horizontales(df_metier, "Métier", "Contrats", color=C_RED, height_base=320)

# =====================================================
# POINTS D'ATTENTION
# =====================================================

st.divider()
section(
    "Points d’attention",
    "Les chiffres ci-dessous servent à piloter la qualité de la donnée et à comprendre ce qui limite la couverture.",
)

expired_detail = contrats_actifs_fin_depassee(df_contrats_kpi)
expired_global = int(global_value(df_global, "contrats_actifs_fin_depassee", 0))
expired_value = expired_global if not perimetre_filtre_actif else expired_detail["contract_reference"].nunique()

unlinked_contracts = int(global_value(df_global, "contrats_non_rattaches_programme", 0))
housing_without_program = int(global_value(df_global, "logements_sans_programme", 0))
multi_meme_metier = int(pd.to_numeric(df_esi_context.get("esi_multi_meme_metier", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
esi_sans_contrat = int(pd.to_numeric(df_esi_context.get("esi_sans_contrat", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())

q1, q2, q3, q4 = st.columns(4)
with q1:
    alert_card("Contrats actifs expirés", expired_value, "Actifs dans le système alors que leur date de fin est dépassée.")
with q2:
    alert_card("Contrats non rattachés", unlinked_contracts, "Contrats source absents de la couverture programme.")
with q3:
    alert_card("Logements sans programme", housing_without_program, "Logements existants mais exclus du calcul de couverture ESI.")
with q4:
    alert_card("ESI multi même métier", multi_meme_metier, "Plusieurs contrats actifs sur le même métier pour un même ESI.")

b1, b2, b3, b4, b5 = st.columns(5)
if "vg_detail_focus" not in st.session_state:
    st.session_state["vg_detail_focus"] = None

with b1:
    if st.button("Voir expirés", use_container_width=True):
        st.session_state["vg_detail_focus"] = "expired"
with b2:
    if st.button("Voir non rattachés", use_container_width=True):
        st.session_state["vg_detail_focus"] = "unlinked_contracts"
with b3:
    if st.button("Voir logements", use_container_width=True):
        st.session_state["vg_detail_focus"] = "housing"
with b4:
    if st.button("Voir multi métier", use_container_width=True):
        st.session_state["vg_detail_focus"] = "multi_topic"
with b5:
    if st.button("Voir ESI sans contrat", use_container_width=True):
        st.session_state["vg_detail_focus"] = "no_contract"

if st.session_state.get("vg_detail_focus"):
    afficher_detail_qualite(
        st.session_state["vg_detail_focus"],
        df_contrats_kpi=df_contrats_kpi,
        df_esi_context=df_esi_context,
        df_qualite=df_qualite,
        df_global=df_global,
    )

# =====================================================
# ANALYSE QUALITÉ
# =====================================================

st.divider()
section(
    "Qualité des données",
    "Un résumé court des anomalies. Les détails restent accessibles via les boutons et la recherche.",
)

col_quality_graph, col_quality_table = st.columns([1, 1])
with col_quality_graph:
    st.markdown('<div class="vg-mini-title">Anomalies principales</div>', unsafe_allow_html=True)
    df_q_graph = construire_graph_qualite(df_qualite_resume, df_qualite)
    afficher_barres_horizontales(df_q_graph, "Anomalie", "Objets distincts", color=C_VIOLET, height_base=320)

with col_quality_table:
    st.markdown('<div class="vg-mini-title">Résumé qualité</div>', unsafe_allow_html=True)
    if df_qualite_resume.empty:
        st.info("Aucun résumé qualité disponible.")
    else:
        resume = df_qualite_resume.copy()
        cols = [c for c in ["anomalie_type", "objet_type", "gravite", "nb_objets_distincts", "nb_lignes_detail"] if c in resume.columns]
        resume = resume[cols].sort_values(cols[-2] if "nb_objets_distincts" in cols else cols[0], ascending=False)
        resume = resume.rename(
            columns={
                "anomalie_type": "Type anomalie",
                "objet_type": "Type objet",
                "gravite": "Gravité",
                "nb_objets_distincts": "Objets distincts",
                "nb_lignes_detail": "Lignes détail",
            }
        )
        st.dataframe(resume, use_container_width=True, hide_index=True, height=320)

# =====================================================
# RECHERCHE RAPIDE
# =====================================================

st.divider()
section(
    "Recherche rapide",
    "Trouver un contrat, un programme / ESI ou une anomalie sans parcourir toute la page.",
)

search_col1, search_col2 = st.columns([1, 2.2])
with search_col1:
    search_type = st.radio(
        "Chercher dans",
        ["Contrats", "Programmes / ESI", "Anomalies"],
        horizontal=False,
        key="vg_search_type",
    )

with search_col2:
    recherche = st.text_input(
        "Recherche",
        placeholder="Référence, libellé, prestataire, métier, société, agence...",
        key="vg_search_input",
    )

if search_type == "Contrats":
    base_table = preparer_contrats_table(df_contrats_kpi.drop_duplicates(["contract_reference", "esi_reference"]))
    filename = "recherche_contrats.csv"
elif search_type == "Programmes / ESI":
    base_table = preparer_esi_table(df_esi_context)
    filename = "recherche_esi.csv"
else:
    base_table = preparer_qualite_table(df_qualite)
    filename = "recherche_anomalies.csv"

resultats = filtrer_table_recherche(base_table, recherche)

st.caption(f"{fmt_nombre(len(resultats))} résultat(s).")

if resultats.empty:
    st.info("Aucun résultat trouvé.")
else:
    st.dataframe(resultats.head(600), use_container_width=True, hide_index=True, height=520)
    if len(resultats) > 600:
        st.caption(f"Affichage limité à 600 lignes sur {fmt_nombre(len(resultats))}.")
    dataframe_download("Télécharger les résultats", resultats, filename)

# =====================================================
# FOOTER TECHNIQUE DISCRET
# =====================================================

if "date_maj" in df_global.columns:
    date_maj = global_value(df_global, "date_maj", "")
    st.caption(f"Dernière mise à jour des tables dashboard : {date_maj}")