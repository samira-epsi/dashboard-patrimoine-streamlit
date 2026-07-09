import html
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

try:
    import plotly.graph_objects as go
except ImportError:
    go = None

from common.app_config import setup_page
from common.ui_style import apply_3f_page_style, page_header
from common.filters import render_filtres_patrimoine
from config import DB_URL


SOURCE_ESI = "dashboard.esi_couverture"
SOURCE_CONTRATS = "dashboard.contrats_patrimoine"
SOURCE_CREATIONS = "dashboard.kpi_creation_detail"
SOURCE_GLOBAL = "dashboard.kpi_globale"

# Optionnel : table légère uniquement pour les codes de prestation.
# Si elle n'existe pas encore dans Supabase, le tableau contrats fonctionne quand même.
SOURCE_SERVICE_CODES = "dashboard.service_codes_light"

CACHE_TTL = 3600
SQL_TIMEOUT_MS = 20000



# =====================================================
# STYLE LOCAL PAGE SYNTHÈSE
# =====================================================

def _safe(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def inject_synthese_style():
    """Style spécifique à la page Synthèse. Ne dépend pas du fichier ui_style."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1600px !important;
        }

        .synth-hero {
            position: relative;
            overflow: hidden;
            padding: 26px 30px;
            border-radius: 28px;
            background: linear-gradient(135deg, #B5121B 0%, #D64550 52%, #8F0E15 100%);
            box-shadow: 0 20px 48px rgba(181, 18, 27, 0.22);
            margin-bottom: 18px;
            border: 1px solid rgba(255, 255, 255, 0.24);
        }

        .synth-hero::after {
            content: "";
            position: absolute;
            width: 260px;
            height: 260px;
            right: -120px;
            top: -130px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
        }

        .synth-hero-title {
            color: white;
            font-size: 42px;
            line-height: 1.05;
            letter-spacing: -1px;
            font-weight: 950;
            margin-bottom: 8px;
        }

        .synth-hero-subtitle {
            color: rgba(255, 255, 255, 0.88);
            font-size: 15px;
            line-height: 1.5;
            font-weight: 650;
            max-width: 900px;
        }

        .synth-section-title {
            font-size: 27px;
            font-weight: 950;
            color: #0F172A;
            letter-spacing: -0.6px;
            margin-top: 4px;
            margin-bottom: 5px;
        }

        .synth-section-subtitle {
            color: #64748B;
            font-size: 13px;
            font-weight: 650;
            margin-bottom: 18px;
        }

        .synth-info-box {
            padding: 14px 16px;
            background: rgba(255,255,255,0.90);
            border: 1px solid #E2E8F0;
            border-radius: 18px;
            color: #475569;
            font-size: 13px;
            font-weight: 650;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
            margin-bottom: 18px;
        }

        .synth-kpi-card {
            position: relative;
            overflow: hidden;
            min-height: 150px;
            border-radius: 26px;
            padding: 20px 20px 18px 20px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid #E2E8F0;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.09);
            transition: transform 0.16s ease, box-shadow 0.16s ease;
        }

        .synth-kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 22px 52px rgba(15, 23, 42, 0.13);
        }

        .synth-kpi-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 5px;
            background: var(--accent, #B5121B);
        }

        .synth-kpi-card::after {
            content: "";
            position: absolute;
            width: 160px;
            height: 160px;
            right: -90px;
            top: -95px;
            border-radius: 999px;
            background: color-mix(in srgb, var(--accent, #B5121B) 12%, transparent);
        }

        .synth-kpi-label {
            position: relative;
            z-index: 1;
            color: #64748B;
            font-size: 13px;
            font-weight: 900;
            margin-bottom: 18px;
        }

        .synth-kpi-value {
            position: relative;
            z-index: 1;
            color: #0F172A;
            font-size: 38px;
            font-weight: 950;
            letter-spacing: -1px;
            line-height: 1;
            margin-bottom: 13px;
        }

        .synth-kpi-delta {
            position: relative;
            z-index: 1;
            display: inline-flex;
            padding: 6px 11px;
            border-radius: 999px;
            background: #ECFDF3;
            border: 1px solid #BBF7D0;
            color: #16A34A;
            font-size: 12px;
            font-weight: 900;
            margin-bottom: 9px;
        }

        .synth-kpi-help {
            position: relative;
            z-index: 1;
            color: #94A3B8;
            font-size: 11.5px;
            font-weight: 650;
            line-height: 1.42;
            max-width: 330px;
        }

        .synth-chart-title {
            color: #1F2937;
            font-size: 16px;
            font-weight: 900;
            margin: 2px 0 12px 0;
        }

        div[data-testid="stPlotlyChart"] {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 24px;
            padding: 10px;
            box-shadow: 0 16px 38px rgba(15, 23, 42, 0.075);
        }

        .contract-table-shell {
            padding: 16px 18px 12px 18px;
            border-radius: 26px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid #E2E8F0;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.085);
            margin-top: 12px;
            margin-bottom: 10px;
        }

        .contract-table-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }

        .contract-table-pill {
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

        .contract-table-hint {
            color: #64748B;
            font-size: 12px;
            font-weight: 650;
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

        div[data-testid="stDataFrame"] [role="gridcell"] {
            color: #0F172A !important;
        }

        .clear-search-button .stButton button {
            border-color: #F6CBCD !important;
            color: #B5121B !important;
            background: #FFF1F2 !important;
            font-weight: 900 !important;
        }

        .clear-search-button .stButton button:hover {
            background: #FDEBEC !important;
            border-color: #D64550 !important;
            color: #8F0E15 !important;
        }

        @media screen and (max-width: 1100px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }

            .synth-hero-title {
                font-size: 34px;
            }

            .synth-kpi-value {
                font-size: 31px;
            }
        }

        @media screen and (max-width: 760px) {
            .synth-hero {
                padding: 22px 20px;
                border-radius: 22px;
            }

            .synth-hero-title {
                font-size: 29px;
            }

            .synth-section-title {
                font-size: 23px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def hero_header(title: str, subtitle: str = ""):
    title = _safe(title)
    subtitle = _safe(subtitle)
    st.markdown(
        f"""
        <div class="synth-hero">
            <div class="synth-hero-title">{title}</div>
            <div class="synth-hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def section_header(title: str, subtitle: str = ""):
    title = _safe(title)
    subtitle = _safe(subtitle)
    if subtitle:
        st.markdown(
            f"""
            <div class="synth-section-title">{title}</div>
            <div class="synth-section-subtitle">{subtitle}</div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="synth-section-title">{title}</div>
            """,
            unsafe_allow_html=True
        )


def info_box(text: str):
    text = _safe(text)
    st.markdown(
        f"""
        <div class="synth-info-box">{text}</div>
        """,
        unsafe_allow_html=True
    )


setup_page("Vue synthétique", None)
apply_3f_page_style()
inject_synthese_style()


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
            "options": f"-c statement_timeout={SQL_TIMEOUT_MS}"
        }
    )


def tester_connexion():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        return False, str(e)


def verifier_sources(conn):
    """
    Supabase doit rester léger :
    on vérifie uniquement les tables prêtes pour le dashboard.
    Les grosses tables public.* ne sont PAS nécessaires ici.
    """
    sources = [
        SOURCE_ESI,
        SOURCE_CONTRATS,
        SOURCE_CREATIONS,
        SOURCE_GLOBAL
    ]

    sources_manquantes = []

    for source in sources:
        exists = conn.execute(
            text("SELECT to_regclass(:source)"),
            {"source": source}
        ).scalar()

        if exists is None:
            sources_manquantes.append(source)

    return sources_manquantes


def aujourd_hui_france():
    return datetime.now(ZoneInfo("Europe/Paris")).date()


# =====================================================
# NETTOYAGE
# =====================================================

def nettoyer_df(df):
    df = df.copy()

    ref_cols = [
        "esi_reference",
        "contract_reference",
        "objet_reference",
        "third_party_id"
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
        "objet_label"
    ]

    num_cols = [
        "nb_logements",
        "nb_equipements",
        "nb_contrats_actifs",
        "nb_contrats_inactifs",
        "esi_couvert",
        "esi_multi_couvert",
        "esi_sans_contrat",
        "esi_sans_equipement"
    ]

    for col in ref_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .replace({
                    "": pd.NA,
                    "nan": pd.NA,
                    "None": pd.NA,
                    "<NA>": pd.NA
                })
            )

    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("Non renseigné")
                .astype(str)
                .str.strip()
                .replace("", "Non renseigné")
            )

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def normaliser_statut_contrat(df):
    df = df.copy()

    if "contract_status" not in df.columns:
        df["contract_status"] = "Non renseigné"

    df["contract_status_clean"] = (
        df["contract_status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    return df


def normaliser_date_fin_contrat(df):
    df = df.copy()

    for col in ["contract_start_date", "contract_end_date"]:
        if col not in df.columns:
            df[col] = pd.NaT

        df[col] = pd.to_datetime(
            df[col],
            errors="coerce"
        )

    return df


SERVICE_CODES_COLS = [
    "contract_reference",
    "service_code_reference_interne",
    "service_code_reference_prestataire",
    "service_code_label",
    "service_code_work_type"
]


def _normaliser_nom_colonne(col):
    return (
        str(col)
        .strip()
        .lower()
        .replace(".", "")
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )


def trouver_colonne(df, candidats):
    if df.empty:
        return None

    mapping = {
        _normaliser_nom_colonne(col): col
        for col in df.columns
    }

    for candidat in candidats:
        key = _normaliser_nom_colonne(candidat)
        if key in mapping:
            return mapping[key]

    return None


def normaliser_service_codes(df_service_codes):
    if df_service_codes is None or df_service_codes.empty:
        return pd.DataFrame(columns=SERVICE_CODES_COLS)

    df = df_service_codes.copy()

    col_contract = trouver_colonne(df, [
        "contract_reference",
        "contractReference",
        "contract_ref",
        "reference_contrat",
        "contrat_reference",
        "contract.reference",
        "contract.id",
        "contractId"
    ])

    col_code_interne = trouver_colonne(df, [
        "code",
        "service_code",
        "serviceCode",
        "service_code_reference",
        "reference_prestation",
        "prestation_reference",
        "prestation_code",
        "reference"
    ])

    col_code_prestataire = trouver_colonne(df, [
        "thirdPartyCode",
        "third_party_code",
        "thirdpartycode",
        "code_prestataire",
        "prestataire_code",
        "supplierCode",
        "providerCode"
    ])

    col_label = trouver_colonne(df, [
        "label",
        "service_label",
        "serviceCodeLabel",
        "service_code_label",
        "prestation_label",
        "libelle",
        "libellé"
    ])

    col_work_type = trouver_colonne(df, [
        "workType",
        "work_type",
        "worktype",
        "metier",
        "métier",
        "topic"
    ])

    out = pd.DataFrame(index=df.index)

    out["contract_reference"] = (
        df[col_contract].astype("string")
        if col_contract else pd.Series(pd.NA, index=df.index, dtype="string")
    )

    out["service_code_reference_interne"] = (
        df[col_code_interne].astype("string")
        if col_code_interne else pd.Series(pd.NA, index=df.index, dtype="string")
    )

    out["service_code_reference_prestataire"] = (
        df[col_code_prestataire].astype("string")
        if col_code_prestataire else pd.Series(pd.NA, index=df.index, dtype="string")
    )

    out["service_code_label"] = (
        df[col_label].astype("string")
        if col_label else pd.Series(pd.NA, index=df.index, dtype="string")
    )

    out["service_code_work_type"] = (
        df[col_work_type].astype("string")
        if col_work_type else pd.Series(pd.NA, index=df.index, dtype="string")
    )

    for col in SERVICE_CODES_COLS:
        out[col] = (
            out[col]
            .astype("string")
            .str.strip()
            .replace({
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "<NA>": pd.NA
            })
        )

    out = out.dropna(subset=["contract_reference"], how="all")
    out = out.drop_duplicates()

    return out


def charger_service_codes_current(conn):
    exists = conn.execute(
        text("SELECT to_regclass(:source)"),
        {"source": SOURCE_SERVICE_CODES}
    ).scalar()

    if exists is None:
        return pd.DataFrame(columns=SERVICE_CODES_COLS)

    return pd.read_sql_query(
        text(f"SELECT * FROM {SOURCE_SERVICE_CODES}"),
        conn
    )


def dedupliquer_esi(df_esi):
    if df_esi.empty:
        return df_esi.copy()

    if "esi_reference" not in df_esi.columns:
        return df_esi.drop_duplicates().copy()

    df = df_esi.copy()
    df = df[df["esi_reference"].notna()].copy()

    if df.empty:
        return df

    num_cols = [
        "nb_logements",
        "nb_equipements",
        "nb_contrats_actifs",
        "nb_contrats_inactifs",
        "esi_couvert",
        "esi_multi_couvert",
        "esi_sans_contrat",
        "esi_sans_equipement"
    ]

    agg_map = {}

    for col in df.columns:
        if col == "esi_reference":
            continue

        if col in num_cols:
            agg_map[col] = "max"
        else:
            agg_map[col] = "first"

    return df.groupby("esi_reference", as_index=False).agg(agg_map)


def liste_refs_valides(df, colonne):
    if colonne not in df.columns:
        return []

    serie = (
        df[colonne]
        .dropna()
        .astype(str)
        .str.strip()
    )

    serie = serie[
        ~serie.isin(["", "nan", "None", "<NA>", "Non renseigné"])
    ]

    return serie.unique().tolist()


def refs_ont_change(df_base, df_filtre, colonne):
    if colonne not in df_base.columns or colonne not in df_filtre.columns:
        return False

    refs_base = set(liste_refs_valides(df_base, colonne))
    refs_filtre = set(liste_refs_valides(df_filtre, colonne))

    return refs_base != refs_filtre


# =====================================================
# OUTILS SQL SUPABASE LÉGER
# =====================================================

def split_source(source: str):
    morceaux = str(source).split(".")
    if len(morceaux) != 2:
        raise ValueError(f"Source SQL invalide : {source}")
    return morceaux[0], morceaux[1]


def colonnes_source(conn, source: str):
    schema, table_name = split_source(source)

    rows = conn.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table_name
        """),
        {
            "schema": schema,
            "table_name": table_name
        }
    ).scalars().all()

    return set(rows)


def expr_colonne(alias: str, colonne: str, colonnes_disponibles: set, default_sql: str = "NULL"):
    if colonne in colonnes_disponibles:
        return f'{alias}."{colonne}" AS "{colonne}"'

    return f'{default_sql} AS "{colonne}"'


def expr_date(alias: str, colonne: str, colonnes_disponibles: set):
    if colonne not in colonnes_disponibles:
        return f'NULL::date AS "{colonne}"'

    return f"""
        CASE
            WHEN {alias}."{colonne}" IS NULL THEN NULL
            WHEN NULLIF({alias}."{colonne}"::text, '') IS NULL THEN NULL
            ELSE NULLIF({alias}."{colonne}"::text, '')::date
        END AS "{colonne}"
    """


def charger_table_colonnes(conn, source: str, colonnes_attendues: list, colonnes_dates: list | None = None):
    colonnes_dates = colonnes_dates or []
    colonnes_disponibles = colonnes_source(conn, source)

    expressions = []

    for col in colonnes_attendues:
        if col in colonnes_dates:
            expressions.append(expr_date("t", col, colonnes_disponibles))
        else:
            expressions.append(expr_colonne("t", col, colonnes_disponibles))

    sql = f"""
        SELECT
            {", ".join(expressions)}
        FROM {source} t
    """

    return pd.read_sql_query(text(sql), conn)


GLOBAL_KPI_COLS = [
    "contrats_total",
    "contrats_actifs",
    "contrats_inactifs",
    "contrats_actifs_fin_depassee",
    "programmes_total",
    "logements_total",
    "equipements_total"
]


def charger_kpi_global_brut(conn):
    colonnes = colonnes_source(conn, SOURCE_GLOBAL)

    order_by = ""
    if "date_maj" in colonnes:
        order_by = 'ORDER BY "date_maj" DESC NULLS LAST'

    return pd.read_sql_query(
        text(f"""
            SELECT *
            FROM {SOURCE_GLOBAL}
            {order_by}
            LIMIT 1
        """),
        conn
    )


def construire_global_depuis_tables_dashboard(df_esi, df_contrats):
    """
    Fallback léger si dashboard.kpi_globale n'a pas exactement les bons noms de colonnes.
    On recalcule les totaux depuis les tables dashboard déjà chargées.
    """
    df_esi_unique = dedupliquer_esi(df_esi)
    df_contrats_unique = df_contrats.drop_duplicates(subset=["contract_reference"], keep="first").copy()

    if "contract_status_clean" not in df_contrats_unique.columns:
        df_contrats_unique = normaliser_statut_contrat(df_contrats_unique)

    contrats_total = len(liste_refs_valides(df_contrats_unique, "contract_reference"))

    contrats_actifs = int(
        df_contrats_unique[df_contrats_unique["contract_status_clean"] == "active"]["contract_reference"].nunique()
    )

    contrats_inactifs = int(
        df_contrats_unique[df_contrats_unique["contract_status_clean"] != "active"]["contract_reference"].nunique()
    )

    if "contract_end_date" in df_contrats_unique.columns:
        today = pd.Timestamp(aujourd_hui_france())
        end_dates = pd.to_datetime(df_contrats_unique["contract_end_date"], errors="coerce")

        contrats_actifs_fin_depassee = int(
            df_contrats_unique[
                (df_contrats_unique["contract_status_clean"] == "active")
                & end_dates.notna()
                & (end_dates < today)
            ]["contract_reference"].nunique()
        )
    else:
        contrats_actifs_fin_depassee = 0

    programmes_total = len(liste_refs_valides(df_esi_unique, "esi_reference"))

    logements_total = int(
        pd.to_numeric(
            df_esi_unique.get("nb_logements", pd.Series(dtype=float)),
            errors="coerce"
        ).fillna(0).sum()
    )

    equipements_total = int(
        pd.to_numeric(
            df_esi_unique.get("nb_equipements", pd.Series(dtype=float)),
            errors="coerce"
        ).fillna(0).sum()
    )

    return {
        "contrats_total": contrats_total,
        "contrats_actifs": contrats_actifs,
        "contrats_inactifs": contrats_inactifs,
        "contrats_actifs_fin_depassee": contrats_actifs_fin_depassee,
        "programmes_total": programmes_total,
        "logements_total": logements_total,
        "equipements_total": equipements_total
    }


def normaliser_kpi_global(df_global_brut, df_esi, df_contrats):
    """
    Sortie garantie avec les colonnes attendues par les KPI.
    Priorité à dashboard.kpi_globale si les colonnes existent.
    Sinon fallback depuis esi_couverture + contrats_patrimoine.
    """
    valeurs = construire_global_depuis_tables_dashboard(df_esi, df_contrats)

    if df_global_brut is not None and not df_global_brut.empty:
        row = df_global_brut.iloc[0]

        candidats = {
            "contrats_total": ["contrats_total", "nb_contrats_total", "total_contrats", "contrats"],
            "contrats_actifs": ["contrats_actifs", "nb_contrats_actifs", "total_contrats_actifs"],
            "contrats_inactifs": ["contrats_inactifs", "nb_contrats_inactifs", "total_contrats_inactifs"],
            "contrats_actifs_fin_depassee": [
                "contrats_actifs_fin_depassee",
                "nb_contrats_actifs_fin_depassee",
                "contrats_fin_depassee",
                "alertes_contrats_fin_depassee"
            ],
            "programmes_total": ["programmes_total", "nb_programmes_total", "total_programmes", "programmes"],
            "logements_total": ["logements_total", "nb_logements_total", "total_logements", "logements"],
            "equipements_total": ["equipements_total", "nb_equipements_total", "total_equipements", "equipements"]
        }

        for cible, noms_possibles in candidats.items():
            col = trouver_colonne(df_global_brut, noms_possibles)

            if col is not None:
                value = pd.to_numeric(pd.Series([row[col]]), errors="coerce").iloc[0]
                if pd.notna(value):
                    valeurs[cible] = int(value)

    return pd.DataFrame([valeurs])


# =====================================================
# CHARGEMENT INTELLIGENT
# =====================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def charger_donnees():
    try:
        with get_engine().connect() as conn:
            conn.execute(text(f"SET statement_timeout = {SQL_TIMEOUT_MS}"))

            sources_manquantes = verifier_sources(conn)

            if sources_manquantes:
                raise RuntimeError(
                    "Sources SQL manquantes : " + ", ".join(sources_manquantes)
                )

            df_esi = charger_table_colonnes(
                conn=conn,
                source=SOURCE_ESI,
                colonnes_attendues=[
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
                    "esi_multi_couvert",
                    "esi_sans_contrat",
                    "esi_sans_equipement"
                ]
            )

            df_contrats = charger_table_colonnes(
                conn=conn,
                source=SOURCE_CONTRATS,
                colonnes_attendues=[
                    "contract_reference",
                    "contract_label",
                    "contract_status",
                    "contract_topic",
                    "third_party_id",
                    "third_party_label",
                    "esi_reference",
                    "esi_label",
                    "societe",
                    "agence",
                    "groupe",
                    "secteur",
                    "contract_start_date",
                    "contract_end_date"
                ],
                colonnes_dates=[
                    "contract_start_date",
                    "contract_end_date"
                ]
            )

            df_creations = charger_table_colonnes(
                conn=conn,
                source=SOURCE_CREATIONS,
                colonnes_attendues=[
                    "objet_type",
                    "objet_reference",
                    "objet_label",
                    "creation_date",
                    "esi_reference",
                    "esi_label",
                    "societe",
                    "agence",
                    "groupe",
                    "secteur",
                    "contract_topic",
                    "third_party_label"
                ],
                colonnes_dates=[
                    "creation_date"
                ]
            )

            df_global_brut = charger_kpi_global_brut(conn)
            df_service_codes = charger_service_codes_current(conn)

    except SQLAlchemyError as e:
        raise RuntimeError(f"Erreur PostgreSQL : {e}") from e

    df_esi = nettoyer_df(df_esi)

    df_contrats = nettoyer_df(df_contrats)
    df_contrats = normaliser_statut_contrat(df_contrats)
    df_contrats = normaliser_date_fin_contrat(df_contrats)

    df_creations = nettoyer_df(df_creations)
    df_creations["creation_date"] = pd.to_datetime(
        df_creations["creation_date"],
        errors="coerce"
    )

    df_global = normaliser_kpi_global(
        df_global_brut=df_global_brut,
        df_esi=df_esi,
        df_contrats=df_contrats
    )

    df_alertes_globales = calculer_contrats_actifs_fin_depassee(df_contrats)

    df_service_codes = normaliser_service_codes(df_service_codes)

    return df_global, df_esi, df_contrats, df_creations, df_alertes_globales, df_service_codes


# =====================================================
# FORMAT
# =====================================================

def fmt_nombre(value):
    try:
        return f"{int(value):,}".replace(",", " ")
    except Exception:
        return "0"


def fmt_pourcentage(value):
    try:
        return f"{float(value):.1f} %".replace(".", ",")
    except Exception:
        return "0,0 %"


def fmt_delta_nouveaux(value):
    value = int(value or 0)

    if value > 1:
        return f"+{fmt_nombre(value)} nouveaux ce mois-ci"

    if value == 1:
        return "+1 nouveau ce mois-ci"

    return "+0 nouveau ce mois-ci"


# =====================================================
# FILTRES
# =====================================================

def valeur_filtre_active(valeur):
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
        "<NA>"
    }

    if valeur is None:
        return False

    if isinstance(valeur, (pd.Series, pd.Index)):
        valeur = valeur.tolist()

    if isinstance(valeur, (list, tuple, set)):
        valeurs_reelles = [
            str(v).strip()
            for v in valeur
            if str(v).strip() not in valeurs_vides
        ]

        return len(valeurs_reelles) > 0

    return str(valeur).strip() not in valeurs_vides


def filtres_sont_actifs(filtres_selectionnes):
    if not filtres_selectionnes:
        return False

    for valeur in filtres_selectionnes.values():
        if valeur_filtre_active(valeur):
            return True

    return False


def filtre_contrat_est_actif(filtres_selectionnes, statut_selectionne, df_esi, df_esi_filtre, df_contrats, df_contrats_filtre):
    if statut_selectionne is not None:
        return True

    mots_cles_contrat = [
        "metier",
        "métier",
        "topic",
        "prestataire",
        "third",
        "contrat",
        "contract"
    ]

    if filtres_selectionnes:
        for cle, valeur in filtres_selectionnes.items():
            cle_clean = str(cle).lower()

            if any(mot in cle_clean for mot in mots_cles_contrat):
                if valeur_filtre_active(valeur):
                    return True

    try:
        for cle, valeur in st.session_state.items():
            cle_clean = str(cle).lower()

            if any(mot in cle_clean for mot in mots_cles_contrat):
                if valeur_filtre_active(valeur):
                    return True
    except Exception:
        pass

    esi_change = refs_ont_change(df_esi, df_esi_filtre, "esi_reference")
    contrats_change = refs_ont_change(df_contrats, df_contrats_filtre, "contract_reference")

    if contrats_change and not esi_change:
        return True

    return False


def afficher_filtre_statut_contrat():
    choix = st.radio(
        "Statut des contrats",
        ["Tous les contrats", "Contrats actifs", "Contrats inactifs"],
        horizontal=True,
        key="filtre_statut_contrat_radio"
    )

    if choix == "Contrats actifs":
        return "active"

    if choix == "Contrats inactifs":
        return "inactive"

    return None


def filtrer_contrats_par_statut(df_contrats, statut):
    df = normaliser_statut_contrat(df_contrats)

    if statut is None:
        return df.copy()

    if statut == "active":
        return df[df["contract_status_clean"] == "active"].copy()

    if statut == "inactive":
        return df[df["contract_status_clean"] != "active"].copy()

    return df.copy()


def filtrer_esi_depuis_contrats(df_esi, df_contrats, appliquer_filtre_contrat):
    if not appliquer_filtre_contrat:
        return df_esi.copy()

    if df_contrats.empty:
        return df_esi.iloc[0:0].copy()

    esi_refs = liste_refs_valides(df_contrats, "esi_reference")

    if not esi_refs:
        return df_esi.iloc[0:0].copy()

    return df_esi[df_esi["esi_reference"].isin(esi_refs)].copy()


# =====================================================
# CRÉATIONS MENSUELLES
# =====================================================

def calcul_nouveaux_ce_mois(df_creations, objet_type, object_refs=None, esi_refs=None):
    if df_creations.empty:
        return 0

    df = df_creations[df_creations["objet_type"] == objet_type].copy()

    if object_refs is not None:
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


# =====================================================
# ALERTE CONTRATS
# =====================================================

def calculer_contrats_actifs_fin_depassee(df_contrats):
    if df_contrats.empty:
        return df_contrats.copy()

    today = pd.Timestamp(aujourd_hui_france())

    df = df_contrats.copy()

    df["contract_end_date"] = pd.to_datetime(
        df["contract_end_date"],
        errors="coerce"
    )

    df_alertes = df[
        (df["contract_status_clean"] == "active")
        & df["contract_end_date"].notna()
        & (df["contract_end_date"] < today)
    ].copy()

    df_alertes = df_alertes.sort_values(
        by=["contract_end_date", "contract_reference"],
        ascending=[True, True]
    )

    df_alertes = df_alertes.drop_duplicates(
        subset=["contract_reference"],
        keep="first"
    )

    return df_alertes


def preparer_table_alertes(df_alertes):
    if df_alertes.empty:
        return pd.DataFrame()

    colonnes_possibles = [
        "contract_reference",
        "contract_label",
        "contract_topic",
        "third_party_label",
        "contract_end_date",
        "societe",
        "agence",
        "groupe",
        "secteur",
        "esi_reference",
        "esi_label"
    ]

    colonnes = [
        col for col in colonnes_possibles
        if col in df_alertes.columns
    ]

    df_table = df_alertes[colonnes].copy()

    if "contract_end_date" in df_table.columns:
        df_table["contract_end_date"] = pd.to_datetime(
            df_table["contract_end_date"],
            errors="coerce"
        ).dt.strftime("%d/%m/%Y")

    renommage = {
        "contract_reference": "Référence contrat",
        "contract_label": "Libellé contrat",
        "contract_topic": "Métier",
        "third_party_label": "Prestataire",
        "contract_end_date": "Date de fin",
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI"
    }

    return df_table.rename(columns=renommage)


def afficher_alerte_contrats_fin_depassee(
    df_global,
    df_contrats_kpi,
    df_alertes_globales,
    perimetre_filtre_actif,
    perimetre_commun_actif,
    statut_selectionne
):
    section_header("Alerte qualité contrats", "Contrats actifs dont la date de fin est dépassée.")

    utiliser_global = (
        not perimetre_commun_actif
        and statut_selectionne in [None, "active"]
    )

    if statut_selectionne == "inactive" and not perimetre_commun_actif:
        df_alertes = pd.DataFrame()
        nb_alertes = 0
        libelle_perimetre = "sur le périmètre sélectionné"

    elif utiliser_global:
        df_alertes = df_alertes_globales.copy()
        nb_alertes = int(df_global.iloc[0]["contrats_actifs_fin_depassee"] or 0)
        libelle_perimetre = "sur tout le patrimoine"

    else:
        df_alertes = calculer_contrats_actifs_fin_depassee(df_contrats_kpi)
        nb_alertes = df_alertes["contract_reference"].nunique()
        libelle_perimetre = "sur le périmètre sélectionné"

    if nb_alertes > 0:
        st.error(
            f"{fmt_nombre(nb_alertes)} contrat(s) sont encore marqués actifs "
            f"alors que leur date de fin est dépassée, {libelle_perimetre}."
        )

        with st.expander("Voir les contrats concernés", expanded=False):
            df_table = preparer_table_alertes(df_alertes)

            if df_table.empty:
                st.info("Aucun détail disponible dans le périmètre chargé.")
            else:
                st.dataframe(
                    df_table.head(300),
                    use_container_width=True,
                    hide_index=True
                )

                if len(df_table) > 300:
                    st.caption(
                        f"Affichage limité aux 300 premiers contrats sur {fmt_nombre(len(df_table))}."
                    )

    else:
        st.success(
            f"Aucun contrat actif avec une date de fin dépassée, {libelle_perimetre}."
        )


# =====================================================
# KPI
# =====================================================

def construire_kpi_volumetrie(
    df_global,
    df_creations,
    df_esi,
    df_contrats,
    perimetre_filtre_actif
):
    global_row = df_global.iloc[0]
    df_esi_unique = dedupliquer_esi(df_esi)

    if not perimetre_filtre_actif:
        total_contrats = int(global_row["contrats_total"])
        total_programmes = int(global_row["programmes_total"])
        total_logements = int(global_row["logements_total"])
        total_equipements = int(global_row["equipements_total"])

        contract_refs = None
        esi_refs = None

    else:
        total_contrats = len(liste_refs_valides(df_contrats, "contract_reference"))
        total_programmes = len(liste_refs_valides(df_esi_unique, "esi_reference"))

        total_logements = int(
            pd.to_numeric(
                df_esi_unique.get("nb_logements", pd.Series(dtype=float)),
                errors="coerce"
            ).fillna(0).sum()
        )

        total_equipements = int(
            pd.to_numeric(
                df_esi_unique.get("nb_equipements", pd.Series(dtype=float)),
                errors="coerce"
            ).fillna(0).sum()
        )

        contract_refs = liste_refs_valides(df_contrats, "contract_reference")
        esi_refs = liste_refs_valides(df_esi_unique, "esi_reference")

    return {
        "contrats": {
            "total": total_contrats,
            "nouveaux_ce_mois": calcul_nouveaux_ce_mois(
                df_creations,
                "contrat",
                object_refs=contract_refs
            )
        },
        "programmes": {
            "total": total_programmes,
            "nouveaux_ce_mois": calcul_nouveaux_ce_mois(
                df_creations,
                "programme",
                object_refs=esi_refs
            )
        },
        "logements": {
            "total": total_logements,
            "nouveaux_ce_mois": calcul_nouveaux_ce_mois(
                df_creations,
                "logement",
                esi_refs=esi_refs
            )
        },
        "equipements": {
            "total": total_equipements,
            "nouveaux_ce_mois": calcul_nouveaux_ce_mois(
                df_creations,
                "equipement",
                esi_refs=esi_refs
            )
        }
    }


def afficher_kpi_card(label, kpi, help_label, accent="#B5121B"):
    label_safe = _safe(label)
    value_safe = _safe(fmt_nombre(kpi["total"]))
    delta_safe = _safe(fmt_delta_nouveaux(kpi["nouveaux_ce_mois"]))
    help_safe = _safe(
        f"{fmt_nombre(kpi['nouveaux_ce_mois'])} nouvel élément créé depuis le début du mois. "
        f"{help_label}"
    )
    accent_safe = _safe(accent)

    st.markdown(
        f"""
        <div class="synth-kpi-card" style="--accent:{accent_safe};">
            <div class="synth-kpi-label">{label_safe}</div>
            <div class="synth-kpi-value">{value_safe}</div>
            <div class="synth-kpi-delta">{delta_safe}</div>
            <div class="synth-kpi-help">{help_safe}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# GRAPHIQUES
# =====================================================

def construire_repartition_contrats_par_metier(df_contrats):
    if df_contrats.empty:
        return pd.DataFrame(columns=["Métier", "Nombre de contrats"])

    df = df_contrats.copy()

    if "contract_topic" not in df.columns:
        df["contract_topic"] = "Non renseigné"

    df["contract_topic"] = (
        df["contract_topic"]
        .fillna("Non renseigné")
        .astype(str)
        .str.strip()
        .replace("", "Non renseigné")
    )

    df_distinct = df.drop_duplicates(
        subset=["contract_reference", "contract_topic"]
    )

    df_graph = (
        df_distinct
        .groupby("contract_topic", as_index=False)["contract_reference"]
        .nunique()
        .rename(columns={
            "contract_topic": "Métier",
            "contract_reference": "Nombre de contrats"
        })
        .sort_values("Nombre de contrats", ascending=True)
    )

    return df_graph


def construire_taux_couverture(
    df_esi_base,
    df_esi_couverts,
    utiliser_selection_contrats
):
    indicateurs_vides = pd.DataFrame({
        "Indicateur": ["Programmes", "Logements", "Équipements"],
        "Taux de couverture": [0.0, 0.0, 0.0],
        "Détail": ["0 / 0", "0 / 0", "0 / 0"]
    })

    if df_esi_base.empty:
        return indicateurs_vides

    base = dedupliquer_esi(df_esi_base)

    for col in ["nb_logements", "nb_equipements", "esi_couvert"]:
        if col not in base.columns:
            base[col] = 0

    base["nb_logements"] = pd.to_numeric(base["nb_logements"], errors="coerce").fillna(0)
    base["nb_equipements"] = pd.to_numeric(base["nb_equipements"], errors="coerce").fillna(0)
    base["esi_couvert"] = pd.to_numeric(base["esi_couvert"], errors="coerce").fillna(0)

    nb_programmes_total = len(liste_refs_valides(base, "esi_reference"))
    nb_logements_total = int(base["nb_logements"].sum())
    nb_equipements_total = int(base["nb_equipements"].sum())

    if utiliser_selection_contrats:
        couverts_refs = set(liste_refs_valides(df_esi_couverts, "esi_reference"))
        base_couverte = base[base["esi_reference"].isin(couverts_refs)].copy()
    else:
        base_couverte = base[base["esi_couvert"] > 0].copy()

    nb_programmes_couverts = len(liste_refs_valides(base_couverte, "esi_reference"))
    nb_logements_couverts = int(base_couverte["nb_logements"].sum())
    nb_equipements_couverts = int(base_couverte["nb_equipements"].sum())

    def ratio(couverts, total):
        if total == 0:
            return 0.0
        return round((couverts / total) * 100, 1)

    return pd.DataFrame({
        "Indicateur": ["Programmes", "Logements", "Équipements"],
        "Taux de couverture": [
            ratio(nb_programmes_couverts, nb_programmes_total),
            ratio(nb_logements_couverts, nb_logements_total),
            ratio(nb_equipements_couverts, nb_equipements_total)
        ],
        "Détail": [
            f"{fmt_nombre(nb_programmes_couverts)} / {fmt_nombre(nb_programmes_total)}",
            f"{fmt_nombre(nb_logements_couverts)} / {fmt_nombre(nb_logements_total)}",
            f"{fmt_nombre(nb_equipements_couverts)} / {fmt_nombre(nb_equipements_total)}"
        ]
    })


def afficher_histogramme_metier(df_graph):
    if df_graph.empty:
        st.info("Aucun contrat disponible pour afficher la répartition par métier.")
        return

    df_graph = df_graph.copy().sort_values("Nombre de contrats", ascending=True)

    if go is None:
        st.bar_chart(
            df_graph.set_index("Métier")["Nombre de contrats"],
            use_container_width=True
        )
        return

    max_value = max(float(df_graph["Nombre de contrats"].max()), 1.0)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_graph["Nombre de contrats"],
            y=df_graph["Métier"],
            orientation="h",
            text=df_graph["Nombre de contrats"].apply(fmt_nombre),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Contrats : %{x}<extra></extra>",
            marker=dict(
                color="#B5121B",
                line=dict(color="#8F0E15", width=1)
            )
        )
    )

    fig.update_layout(
        title_text="",
        autosize=True,
        height=max(340, 58 * len(df_graph)),
        margin=dict(l=10, r=48, t=8, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        bargap=0.30,
        xaxis=dict(
            title=None,
            range=[0, max_value * 1.18],
            showgrid=True,
            gridcolor="#E5E7EB",
            zeroline=False,
            fixedrange=False
        ),
        yaxis=dict(
            title=None,
            automargin=True,
            fixedrange=False
        ),
        font=dict(
            family="Arial",
            size=12,
            color="#111827"
        ),
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "responsive": True
        }
    )


def afficher_taux_couverture(df_graph):
    if df_graph.empty:
        st.info("Aucune donnée disponible pour afficher le taux de couverture.")
        return

    if go is None:
        st.bar_chart(
            df_graph.set_index("Indicateur")["Taux de couverture"],
            use_container_width=True
        )
        return

    df_graph = df_graph.copy().sort_values("Taux de couverture", ascending=True)
    df_graph["Libellé"] = [
        f"{fmt_pourcentage(taux)}"
        for taux in df_graph["Taux de couverture"]
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_graph["Taux de couverture"],
            y=df_graph["Indicateur"],
            orientation="h",
            text=df_graph["Libellé"],
            textposition="auto",
            customdata=df_graph["Détail"],
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Taux : %{x:.1f} %<br>"
                "Détail : %{customdata}"
                "<extra></extra>"
            ),
            marker=dict(
                color="#0057A8",
                line=dict(color="#003F7D", width=1)
            )
        )
    )

    fig.update_layout(
        title_text="",
        autosize=True,
        height=340,
        margin=dict(l=8, r=18, t=8, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        bargap=0.28,
        xaxis=dict(
            range=[0, 105],
            ticksuffix=" %",
            showgrid=True,
            gridcolor="#E5E7EB",
            zeroline=False,
            title=None,
            fixedrange=False
        ),
        yaxis=dict(
            title=None,
            automargin=True,
            fixedrange=False
        ),
        font=dict(
            family="Arial",
            size=12,
            color="#111827"
        ),
        showlegend=False
    )

    fig.update_traces(textfont=dict(size=12))

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "responsive": True
        }
    )


def afficher_graphiques_bas(
    df_contrats,
    df_esi_base,
    df_esi_couverts,
    utiliser_selection_contrats
):
    st.divider()
    section_header(
        "Analyse contrats et couverture",
        "Répartition par métier et taux de couverture du patrimoine. Les deux graphiques restent côte à côte sur écran large."
    )

    col_left, col_right = st.columns([1.25, 1])

    with col_left:
        st.markdown('<div class="synth-chart-title">Répartition des contrats par métier</div>', unsafe_allow_html=True)
        df_metier = construire_repartition_contrats_par_metier(df_contrats)
        afficher_histogramme_metier(df_metier)

    with col_right:
        st.markdown('<div class="synth-chart-title">Taux de couverture</div>', unsafe_allow_html=True)
        df_couverture = construire_taux_couverture(
            df_esi_base=df_esi_base,
            df_esi_couverts=df_esi_couverts,
            utiliser_selection_contrats=utiliser_selection_contrats
        )
        afficher_taux_couverture(df_couverture)

        if utiliser_selection_contrats:
            st.caption(
                "Lecture : part du patrimoine filtré couvert par les contrats du périmètre sélectionné."
            )
        else:
            st.caption(
                "Lecture : part du patrimoine filtré couverte par au moins un contrat actif."
            )


# =====================================================
# TABLE CONTRATS + CODES DE PRESTATION
# =====================================================

def _format_date_table(serie):
    return pd.to_datetime(serie, errors="coerce").dt.strftime("%d/%m/%Y").fillna("")


def construire_table_contrats_prestations(
    df_contrats,
    df_service_codes,
    afficher_codes_prestation,
    recherche_contrat
):
    colonnes_base = [
        "contract_reference",
        "contract_label",
        "third_party_label",
        "contract_start_date",
        "contract_end_date",
        "contract_topic",
        "contract_status"
    ]

    colonnes_manquantes = [
        col for col in colonnes_base
        if col not in df_contrats.columns
    ]

    if colonnes_manquantes:
        return pd.DataFrame()

    base = df_contrats[colonnes_base].copy()
    base = base.drop_duplicates(subset=["contract_reference"], keep="first")

    for col in ["contract_status", "contract_topic", "third_party_label", "contract_label", "contract_reference"]:
        base[col] = (
            base[col]
            .fillna("Non renseigné")
            .astype(str)
            .str.strip()
            .replace("", "Non renseigné")
        )

    if afficher_codes_prestation:
        services = normaliser_service_codes(df_service_codes)

        table = base.merge(
            services,
            on="contract_reference",
            how="left"
        )

        colonnes_recherche = [
            "contract_reference",
            "contract_label",
            "third_party_label",
            "contract_topic",
            "contract_status",
            "service_code_reference_interne",
            "service_code_reference_prestataire",
            "service_code_label",
            "service_code_work_type"
        ]
    else:
        table = base.copy()
        colonnes_recherche = [
            "contract_reference",
            "contract_label",
            "third_party_label",
            "contract_topic",
            "contract_status"
        ]

    recherche_contrat = str(recherche_contrat or "").strip().lower()

    if recherche_contrat:
        masque = pd.Series(False, index=table.index)

        for col in colonnes_recherche:
            if col in table.columns:
                masque = masque | (
                    table[col]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(recherche_contrat, na=False, regex=False)
                )

        table = table[masque].copy()

    table["contract_start_date"] = _format_date_table(table["contract_start_date"])
    table["contract_end_date"] = _format_date_table(table["contract_end_date"])

    renommage = {
        "contract_reference": "Référence contrat",
        "contract_label": "Libellé contrat",
        "third_party_label": "Prestataire",
        "contract_start_date": "Date de début",
        "contract_end_date": "Date de fin",
        "contract_topic": "Métier",
        "contract_status": "Statut",
        "service_code_reference_interne": "Référence prestation chez nous",
        "service_code_reference_prestataire": "Référence prestation prestataire"
    }

    if afficher_codes_prestation:
        colonnes_finales = [
            "contract_reference",
            "contract_label",
            "third_party_label",
            "contract_start_date",
            "contract_end_date",
            "contract_topic",
            "contract_status",
            "service_code_reference_interne",
            "service_code_reference_prestataire"
        ]
    else:
        colonnes_finales = colonnes_base

    table = table[[col for col in colonnes_finales if col in table.columns]].copy()
    table = table.rename(columns=renommage)

    for col in table.columns:
        table[col] = (
            table[col]
            .fillna("")
            .astype(str)
            .replace("<NA>", "")
        )

    table = table.drop_duplicates().reset_index(drop=True)

    return table


def afficher_table_contrats_prestations(df_contrats, df_service_codes):
    st.divider()
    section_header(
        "Liste des contrats",
        "Tableau dynamique synchronisé avec les filtres. Les codes de prestation peuvent être affichés à la demande."
    )

    col_option, col_search, col_clear = st.columns([1.15, 2.45, 0.65])

    with col_option:
        afficher_codes_prestation = st.toggle(
            "Afficher les codes de prestation",
            value=False,
            key="synthese_afficher_codes_prestation"
        )

    with col_clear:
        st.markdown('<div class="clear-search-button">', unsafe_allow_html=True)
        effacer_recherche = st.button(
            "Effacer",
            key="synthese_effacer_recherche_contrat",
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if effacer_recherche:
        st.session_state["synthese_recherche_contrat"] = ""
        st.rerun()

    with col_search:
        recherche_contrat = st.text_input(
            "Rechercher un contrat",
            placeholder="Référence, libellé, prestataire, métier, statut...",
            key="synthese_recherche_contrat"
        )

    table = construire_table_contrats_prestations(
        df_contrats=df_contrats,
        df_service_codes=df_service_codes,
        afficher_codes_prestation=afficher_codes_prestation,
        recherche_contrat=recherche_contrat
    )

    if table.empty:
        st.info("Aucun contrat trouvé pour le périmètre sélectionné.")
        return

    nb_lignes_total = len(table)
    suffixe_codes = "avec codes de prestation" if afficher_codes_prestation else "sans codes de prestation"

    st.markdown(
        f"""
        <div class="contract-table-shell">
            <div class="contract-table-topline">
                <div class="contract-table-pill">{fmt_nombre(nb_lignes_total)} résultat(s) {suffixe_codes}</div>
                <div class="contract-table-hint">Le tableau défile horizontalement et verticalement.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    column_config = {
        "Référence contrat": st.column_config.TextColumn("Référence contrat", width="small"),
        "Libellé contrat": st.column_config.TextColumn("Libellé contrat", width="large"),
        "Prestataire": st.column_config.TextColumn("Prestataire", width="medium"),
        "Date de début": st.column_config.TextColumn("Date de début", width="small"),
        "Date de fin": st.column_config.TextColumn("Date de fin", width="small"),
        "Métier": st.column_config.TextColumn("Métier", width="medium"),
        "Statut": st.column_config.TextColumn("Statut", width="small"),
        "Référence prestation chez nous": st.column_config.TextColumn("Référence prestation chez nous", width="medium"),
        "Référence prestation prestataire": st.column_config.TextColumn("Référence prestation prestataire", width="medium"),
    }

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            col: config
            for col, config in column_config.items()
            if col in table.columns
        }
    )


# =====================================================
# PAGE
# =====================================================

hero_header(
    title="Vue globale",
    # subtitle="Pilotage clair des contrats, de la couverture patrimoine et des alertes qualité."
)

info_box("Les chiffres et les graphiques se recalculent automatiquement selon les filtres du périmètre et le statut de contrat sélectionné.")


# =====================================================
# CONNEXION + CHARGEMENT
# =====================================================

ok, erreur = tester_connexion()

if not ok:
    st.error("Connexion PostgreSQL impossible.")
    st.code(erreur)
    st.stop()


col_refresh, _ = st.columns([1, 4])

with col_refresh:
    if st.button("Rafraîchir depuis la source", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


try:
    with st.spinner("Chargement des données..."):
        (
            df_global,
            df_esi,
            df_contrats,
            df_creations,
            df_alertes_globales,
            df_service_codes
        ) = charger_donnees()

except Exception as e:
    st.error("Erreur pendant le chargement des données.")
    st.code(str(e))
    st.stop()


# =====================================================
# FILTRES COMMUNS
# =====================================================

df_esi_filtre, df_contrats_filtre, filtres_selectionnes = render_filtres_patrimoine(
    df_esi=df_esi,
    df_contrats=df_contrats
)


# =====================================================
# FILTRE STATUT CONTRAT
# =====================================================

st.divider()
section_header("Périmètre contrat", "Choix du statut de contrat à appliquer aux indicateurs.")

statut_selectionne = afficher_filtre_statut_contrat()

df_contrats_kpi = filtrer_contrats_par_statut(
    df_contrats=df_contrats_filtre,
    statut=statut_selectionne
)


# =====================================================
# CONNEXION RÉELLE DES FILTRES AUX KPI
# =====================================================

perimetre_commun_actif = (
    refs_ont_change(df_esi, df_esi_filtre, "esi_reference")
    or refs_ont_change(df_contrats, df_contrats_filtre, "contract_reference")
)

perimetre_filtre_actif = (
    perimetre_commun_actif
    or statut_selectionne is not None
)

filtre_contrat_actif = filtre_contrat_est_actif(
    filtres_selectionnes=filtres_selectionnes,
    statut_selectionne=statut_selectionne,
    df_esi=df_esi,
    df_esi_filtre=df_esi_filtre,
    df_contrats=df_contrats,
    df_contrats_filtre=df_contrats_filtre
)

df_esi_kpi = filtrer_esi_depuis_contrats(
    df_esi=df_esi_filtre,
    df_contrats=df_contrats_kpi,
    appliquer_filtre_contrat=filtre_contrat_actif
)


# =====================================================
# ALERTE CONTRATS
# =====================================================

st.divider()

afficher_alerte_contrats_fin_depassee(
    df_global=df_global,
    df_contrats_kpi=df_contrats_kpi,
    df_alertes_globales=df_alertes_globales,
    perimetre_filtre_actif=perimetre_filtre_actif,
    perimetre_commun_actif=perimetre_commun_actif,
    statut_selectionne=statut_selectionne
)


# =====================================================
# KPI PRINCIPAUX
# =====================================================

st.divider()
section_header("Indicateurs principaux", "Les volumes clés du périmètre sélectionné.")

kpi_volumetrie = construire_kpi_volumetrie(
    df_global=df_global,
    df_creations=df_creations,
    df_esi=df_esi_kpi,
    df_contrats=df_contrats_kpi,
    perimetre_filtre_actif=perimetre_filtre_actif
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    afficher_kpi_card(
        "Contrats",
        kpi_volumetrie["contrats"],
        "Contrats uniques selon le périmètre sélectionné.",
        accent="#B5121B"
    )

with c2:
    afficher_kpi_card(
        "Programmes / ESI",
        kpi_volumetrie["programmes"],
        "Programmes / ESI selon le périmètre sélectionné.",
        accent="#0057A8"
    )

with c3:
    afficher_kpi_card(
        "Logements",
        kpi_volumetrie["logements"],
        "Logements rattachés aux programmes / ESI du périmètre sélectionné.",
        accent="#16A34A"
    )

with c4:
    afficher_kpi_card(
        "Équipements",
        kpi_volumetrie["equipements"],
        "Équipements rattachés aux programmes / ESI du périmètre sélectionné.",
        accent="#EA580C"
    )

st.caption(
    "Le delta indique le nombre de nouveaux éléments créés depuis le début du mois en cours."
)


# =====================================================
# GRAPHIQUES BAS
# =====================================================

afficher_graphiques_bas(
    df_contrats=df_contrats_kpi,
    df_esi_base=df_esi_filtre,
    df_esi_couverts=df_esi_kpi,
    utiliser_selection_contrats=filtre_contrat_actif
)


# =====================================================
# TABLEAU CONTRATS + CODES DE PRESTATION
# =====================================================

afficher_table_contrats_prestations(
    df_contrats=df_contrats_kpi,
    df_service_codes=df_service_codes
)
