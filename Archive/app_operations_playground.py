import streamlit as st
import pandas as pd

from sqlalchemy import create_engine, text
from config import DB_URL


# ============================================================
# CONFIG STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Playground Interventions",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Playground Interventions & Patrimoine")

st.caption(
    "Exploration du rattachement des interventions "
    "au patrimoine Intent."
)


# ============================================================
# BDD
# ============================================================

@st.cache_resource
def get_engine():
    return create_engine(
        DB_URL,
        pool_pre_ping=True,
    )


engine = get_engine()


# ============================================================
# TABLES AUTORISEES
# ============================================================

TABLES = {
    "Actives": "operations_active_current",
    "Clôturées": "operations_closed_current",
    "Refusées": "operations_denied_current",
}


# ============================================================
# OUTILS SQL
# ============================================================

@st.cache_data(ttl=60)
def run_query(query, params=None):

    with engine.connect() as conn:

        return pd.read_sql(
            text(query),
            conn,
            params=params or {},
        )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Filtres")

source_label = st.sidebar.selectbox(
    "Type d'interventions",
    list(TABLES.keys()),
)

table = TABLES[source_label]


# ------------------------------------------------------------
# Filtre statut
# ------------------------------------------------------------

statuses = run_query(
    f"""
    SELECT DISTINCT status
    FROM {table}
    WHERE status IS NOT NULL
    ORDER BY status
    """
)

status_options = statuses["status"].tolist()

selected_status = st.sidebar.multiselect(
    "Statut",
    status_options,
    default=status_options,
)


# ------------------------------------------------------------
# Contrat
# ------------------------------------------------------------

contract_reference = st.sidebar.text_input(
    "Référence contrat",
    placeholder="Ex : 58201",
)


# ------------------------------------------------------------
# Asset
# ------------------------------------------------------------

asset_search = st.sidebar.text_input(
    "Asset reference",
    placeholder="Ex : 2154P/2154L-A",
)


# ============================================================
# WHERE DYNAMIQUE
# ============================================================

where_conditions = [
    "1 = 1"
]

params = {}


if selected_status:

    where_conditions.append(
        "o.status = ANY(:statuses)"
    )

    params["statuses"] = selected_status


if contract_reference:

    where_conditions.append(
        "o.contract_reference = :contract_reference"
    )

    params["contract_reference"] = contract_reference


if asset_search:

    where_conditions.append(
        "o.asset_reference ILIKE :asset_search"
    )

    params["asset_search"] = f"%{asset_search}%"


where_sql = " AND ".join(
    where_conditions
)


# ============================================================
# KPI
# ============================================================

kpi_query = f"""
SELECT

    COUNT(*) AS total_operations,

    COUNT(*) FILTER (
        WHERE o.asset_reference IS NOT NULL
          AND BTRIM(o.asset_reference) <> ''
    ) AS avec_asset_reference,

    COUNT(*) FILTER (
        WHERE h.asset_reference IS NOT NULL
          AND h.asset_non_identifie = FALSE
    ) AS rattachees,

    COUNT(*) FILTER (
        WHERE h.asset_non_identifie = TRUE
    ) AS asset_non_identifie,

    COUNT(*) FILTER (
        WHERE o.asset_reference IS NOT NULL
          AND BTRIM(o.asset_reference) <> ''
          AND h.asset_reference IS NULL
    ) AS asset_absent,

    COUNT(*) FILTER (
        WHERE o.asset_reference IS NULL
           OR BTRIM(o.asset_reference) = ''
    ) AS sans_asset_reference

FROM {table} o

LEFT JOIN vw_asset_hierarchy_current h
    ON h.asset_reference = o.asset_reference

WHERE {where_sql}
"""

kpi = run_query(
    kpi_query,
    params,
).iloc[0]


total = int(
    kpi["total_operations"]
)

avec_asset = int(
    kpi["avec_asset_reference"]
)

rattachees = int(
    kpi["rattachees"]
)

non_identifie = int(
    kpi["asset_non_identifie"]
)

absent = int(
    kpi["asset_absent"]
)

sans_asset = int(
    kpi["sans_asset_reference"]
)


# ============================================================
# TAUX
# ============================================================

taux_rattachement = (
    rattachees / total * 100
    if total
    else 0
)

taux_asset = (
    avec_asset / total * 100
    if total
    else 0
)


# ============================================================
# AFFICHAGE KPI
# ============================================================

st.subheader(
    f"Vue {source_label.lower()}"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Interventions",
    f"{total:,}".replace(",", " "),
)

c2.metric(
    "Avec asset_reference",
    f"{avec_asset:,}".replace(",", " "),
    f"{taux_asset:.1f} %",
)

c3.metric(
    "Correctement rattachées",
    f"{rattachees:,}".replace(",", " "),
    f"{taux_rattachement:.1f} %",
)

c4.metric(
    "ASSET_NON_IDENTIFIE",
    f"{non_identifie:,}".replace(",", " "),
)


c5, c6, c7 = st.columns(3)

c5.metric(
    "Asset absent",
    f"{absent:,}".replace(",", " "),
)

c6.metric(
    "Sans asset_reference",
    f"{sans_asset:,}".replace(",", " "),
)

c7.metric(
    "Non rattachées au total",
    f"{non_identifie + absent + sans_asset:,}".replace(",", " "),
)


# ============================================================
# REPARTITION RATTACHEMENT
# ============================================================

st.divider()

st.subheader("État du rattachement")

df_rattachement = pd.DataFrame(
    {
        "État": [
            "Rattaché",
            "Asset non identifié",
            "Asset absent",
            "Sans asset reference",
        ],
        "Nombre": [
            rattachees,
            non_identifie,
            absent,
            sans_asset,
        ],
    }
)

st.bar_chart(
    df_rattachement.set_index("État")
)


# ============================================================
# HIERARCHIE
# ============================================================

st.divider()

st.subheader("Répartition patrimoine")

niveau = st.selectbox(
    "Niveau de regroupement",
    [
        "Société",
        "Agence",
        "Groupe",
        "Secteur",
        "Programme",
    ],
)


LEVELS = {

    "Société": (
        "societe_reference",
        "societe_label",
    ),

    "Agence": (
        "agence_reference",
        "agence_label",
    ),

    "Groupe": (
        "groupe_reference",
        "groupe_label",
    ),

    "Secteur": (
        "secteur_reference",
        "secteur_label",
    ),

    "Programme": (
        "programme_reference",
        "programme_label",
    ),
}


reference_column, label_column = (
    LEVELS[niveau]
)


hierarchy_query = f"""
SELECT

    h.{reference_column} AS reference,
    h.{label_column} AS label,

    COUNT(*) AS nb_operations

FROM {table} o

LEFT JOIN vw_asset_hierarchy_current h
    ON h.asset_reference = o.asset_reference

WHERE {where_sql}

  AND h.{reference_column} IS NOT NULL

GROUP BY
    h.{reference_column},
    h.{label_column}

ORDER BY
    nb_operations DESC

LIMIT 100
"""


df_hierarchy = run_query(
    hierarchy_query,
    params,
)

st.dataframe(
    df_hierarchy,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# TOP PROGRAMMES
# ============================================================

st.subheader(
    "Top 20"
)

if not df_hierarchy.empty:

    chart_df = (
        df_hierarchy
        .head(20)
        .copy()
    )

    chart_df["nom"] = (
        chart_df["reference"].fillna("")
        + " - "
        + chart_df["label"].fillna("")
    )

    st.bar_chart(
        chart_df.set_index("nom")[
            ["nb_operations"]
        ]
    )


# ============================================================
# EXPLORATEUR DES INTERVENTIONS
# ============================================================

st.divider()

st.subheader(
    "Explorateur des interventions"
)

etat = st.selectbox(
    "Afficher",
    [
        "Toutes",
        "Rattachées",
        "ASSET_NON_IDENTIFIE",
        "Asset absent",
        "Sans asset_reference",
    ],
)


extra_condition = ""


if etat == "Rattachées":

    extra_condition = """
        AND h.asset_reference IS NOT NULL
        AND h.asset_non_identifie = FALSE
    """


elif etat == "ASSET_NON_IDENTIFIE":

    extra_condition = """
        AND h.asset_non_identifie = TRUE
    """


elif etat == "Asset absent":

    extra_condition = """
        AND o.asset_reference IS NOT NULL
        AND BTRIM(o.asset_reference) <> ''
        AND h.asset_reference IS NULL
    """


elif etat == "Sans asset_reference":

    extra_condition = """
        AND (
            o.asset_reference IS NULL
            OR BTRIM(o.asset_reference) = ''
        )
    """


detail_query = f"""
SELECT

    o.reference AS operation_reference,

    o.status,

    o.contract_reference,

    o.asset_reference,

    o.event_date,

    h.asset_type,

    h.terminal_category,

    h.societe_reference,
    h.societe_label,

    h.agence_reference,
    h.agence_label,

    h.groupe_reference,
    h.groupe_label,

    h.secteur_reference,
    h.secteur_label,

    h.programme_reference,
    h.programme_label,

    h.batiment_reference,
    h.batiment_label,

    h.escalier_reference,
    h.escalier_label,

    h.logement_reference,

    h.equipment_reference,

    h.asset_non_identifie

FROM {table} o

LEFT JOIN vw_asset_hierarchy_current h
    ON h.asset_reference = o.asset_reference

WHERE {where_sql}

{extra_condition}

ORDER BY
    o.event_date DESC NULLS LAST

LIMIT 500
"""


df_detail = run_query(
    detail_query,
    params,
)

st.caption(
    "500 lignes maximum pour éviter de charger "
    "des millions d'interventions dans Streamlit."
)

st.dataframe(
    df_detail,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# EXPORT
# ============================================================

if not df_detail.empty:

    csv = df_detail.to_csv(
        index=False,
    ).encode(
        "utf-8-sig"
    )

    st.download_button(
        "Télécharger les résultats",
        csv,
        file_name="operations_rattachement.csv",
        mime="text/csv",
    )