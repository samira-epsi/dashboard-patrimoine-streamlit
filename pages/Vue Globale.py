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
        .block-container {
            padding-top: 1.25rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1560px !important;
        }

        .vg-hero {
            position: relative;
            overflow: hidden;
            padding: 28px 30px;
            border-radius: 28px;
            background: linear-gradient(135deg, #B5121B 0%, #D64550 54%, #8F0E15 100%);
            box-shadow: 0 22px 52px rgba(181, 18, 27, 0.22);
            margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,0.22);
        }
        .vg-hero:after {
            content: "";
            position: absolute;
            width: 300px;
            height: 300px;
            right: -150px;
            top: -150px;
            border-radius: 999px;
            background: rgba(255,255,255,0.13);
        }
        .vg-hero-title {
            position: relative;
            z-index: 1;
            color: white;
            font-size: 42px;
            line-height: 1.05;
            letter-spacing: -1.1px;
            font-weight: 950;
            margin-bottom: 10px;
        }
        .vg-hero-subtitle {
            position: relative;
            z-index: 1;
            color: rgba(255,255,255,0.90);
            font-size: 15px;
            line-height: 1.55;
            font-weight: 650;
            max-width: 980px;
        }

        .vg-info {
            padding: 14px 16px;
            border-radius: 18px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            color: #475569;
            font-size: 13px;
            font-weight: 650;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.055);
            margin: 10px 0 18px 0;
        }
        .vg-section-title {
            font-size: 26px;
            font-weight: 950;
            color: #0F172A;
            letter-spacing: -0.6px;
            margin-top: 4px;
            margin-bottom: 5px;
        }
        .vg-section-subtitle {
            color: #64748B;
            font-size: 13px;
            font-weight: 650;
            margin-bottom: 16px;
        }

        .vg-card {
            min-height: 166px;
            border-radius: 26px;
            padding: 19px 20px 17px 20px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid #E2E8F0;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.085);
            position: relative;
            overflow: hidden;
        }
        .vg-card:before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 5px;
            background: var(--accent, #B5121B);
        }
        .vg-card:after {
            content: "";
            position: absolute;
            width: 150px;
            height: 150px;
            right: -90px;
            top: -90px;
            border-radius: 999px;
            background: color-mix(in srgb, var(--accent, #B5121B) 12%, transparent);
        }
        .vg-card-label {
            position: relative;
            z-index: 1;
            color: #64748B;
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 15px;
        }
        .vg-card-value {
            position: relative;
            z-index: 1;
            color: #0F172A;
            font-size: 36px;
            font-weight: 950;
            letter-spacing: -1px;
            line-height: 1;
            margin-bottom: 11px;
        }
        .vg-card-pill {
            position: relative;
            z-index: 1;
            display: inline-flex;
            padding: 6px 10px;
            border-radius: 999px;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            color: #334155;
            font-size: 12px;
            font-weight: 850;
            margin-bottom: 9px;
        }
        .vg-card-help {
            position: relative;
            z-index: 1;
            color: #94A3B8;
            font-size: 11.7px;
            font-weight: 650;
            line-height: 1.42;
        }

        .vg-alert-card {
            min-height: 132px;
            border-radius: 24px;
            padding: 17px 18px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            box-shadow: 0 16px 36px rgba(15, 23, 42, 0.075);
        }
        .vg-alert-title {
            color: #475569;
            font-size: 12px;
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: .25px;
            margin-bottom: 10px;
        }
        .vg-alert-value {
            font-size: 30px;
            line-height: 1;
            color: #0F172A;
            font-weight: 950;
            letter-spacing: -0.6px;
            margin-bottom: 9px;
        }
        .vg-alert-help {
            color: #64748B;
            font-size: 12px;
            font-weight: 650;
            line-height: 1.4;
        }

        .vg-mini-title {
            color: #1F2937;
            font-size: 16px;
            font-weight: 900;
            margin: 2px 0 10px 0;
        }
        div[data-testid="stPlotlyChart"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 24px;
            padding: 10px;
            box-shadow: 0 16px 38px rgba(15, 23, 42, 0.075);
        }
        div[data-testid="stDataFrame"] {
            border-radius: 20px !important;
            overflow: hidden !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.065) !important;
            background: white !important;
        }
        div[data-testid="stDataFrame"] [role="columnheader"] {
            background: #F8FAFC !important;
            color: #334155 !important;
            font-weight: 900 !important;
        }
        .stButton button {
            border-radius: 14px !important;
            font-weight: 850 !important;
        }
        .stDownloadButton button {
            border-radius: 14px !important;
            font-weight: 850 !important;
        }

        @media screen and (max-width: 1100px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .vg-hero-title { font-size: 34px; }
            .vg-card-value { font-size: 31px; }
        }
        @media screen and (max-width: 760px) {
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


def hero(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="vg-hero">
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

def kpi_card(label, value, pill, help_text, accent="#B5121B"):
    st.markdown(
        f"""
        <div class="vg-card" style="--accent:{_safe(accent)};">
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
    fig.add_trace(
        go.Bar(
            x=df["Taux"],
            y=df["Indicateur"],
            orientation="h",
            text=df["Texte"],
            textposition="auto",
            customdata=df["Détail"],
            hovertemplate="<b>%{y}</b><br>Taux : %{x:.1f} %<br>Détail : %{customdata}<extra></extra>",
            marker=dict(color="#0057A8", line=dict(color="#003F7D", width=1)),
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=8, r=18, t=8, b=18),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(range=[0, 105], ticksuffix=" %", gridcolor="#E5E7EB", zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
        font=dict(family="Arial", size=12, color="#111827"),
        showlegend=False,
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


def afficher_barres_horizontales(df: pd.DataFrame, label_col: str, value_col: str, color="#B5121B", height_base=320):
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
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Nombre : %{x}<extra></extra>",
            marker=dict(color=color),
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=48, t=8, b=18),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(range=[0, max_value * 1.18], gridcolor="#E5E7EB", zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
        font=dict(family="Arial", size=12, color="#111827"),
        showlegend=False,
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
        section("Détail — contrats actifs avec date de fin dépassée", "Contrats exploitables dans le périmètre filtré.")
        table = preparer_contrats_table(contrats_actifs_fin_depassee(df_contrats_kpi))
        if table.empty:
            st.success("Aucun contrat actif expiré dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), use_container_width=True, hide_index=True, height=360)
            dataframe_download("Télécharger les contrats expirés", table, "contrats_actifs_expires.csv")

    elif focus == "unlinked_contracts":
        section("Détail — contrats non rattachés", "Contrats présents en source mais absents de la couverture programme.")
        table = df_qualite[df_qualite.get("anomalie_type", "") == "CONTRAT_NON_RATTACHE_PROGRAMME"].copy() if not df_qualite.empty else pd.DataFrame()
        table = preparer_qualite_table(table)
        if table.empty:
            st.info("Aucun détail disponible dans la table qualité.")
        else:
            st.dataframe(table.head(500), use_container_width=True, hide_index=True, height=360)
            dataframe_download("Télécharger les contrats non rattachés", table, "contrats_non_rattaches.csv")

    elif focus == "housing":
        section("Détail — logements sans programme", "Logements non exploitables dans les calculs de couverture ESI.")
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
        section("Détail — ESI avec plusieurs contrats actifs sur le même métier", "Ce signal peut révéler des doublons ou des chevauchements de contrats.")
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
        section("Détail — ESI sans contrat actif", "Programmes sans contrat actif rattaché dans le périmètre affiché.")
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
    "Vue globale",
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
# FILTRES EXISTANTS — ON GARDE LA DYNAMIQUE DU PROJET
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
    kpi_card("Contrats", contrats_value, contrats_pill, contrats_help, accent="#B5121B")
with c2:
    kpi_card("Programmes / ESI", programmes_value, programmes_pill, programmes_help, accent="#0057A8")
with c3:
    kpi_card("Logements", logements_value, logements_pill, logements_help, accent="#16A34A")
with c4:
    kpi_card("Équipements", equipements_value, equipements_pill, equipements_help, accent="#EA580C")

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
    afficher_barres_horizontales(df_metier, "Métier", "Contrats", color="#B5121B", height_base=320)

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
    afficher_barres_horizontales(df_q_graph, "Anomalie", "Objets distincts", color="#EA580C", height_base=320)

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
