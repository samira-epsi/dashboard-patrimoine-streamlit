import streamlit as st
import pandas as pd

from sqlalchemy import create_engine, text
from config import DB_URL


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Analyse SLA - Intent",
    page_icon="⏱️",
    layout="wide",
)

st.markdown("""
<style>

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #EAEAEA;
    padding: 18px;
    border-radius: 14px;
}

[data-testid="stMetricLabel"] {
    font-size: 14px;
}

[data-testid="stMetricValue"] {
    font-size: 28px;
    font-weight: 700;
}

.section-title {
    font-size: 22px;
    font-weight: 700;
    margin-top: 25px;
    margin-bottom: 10px;
}

.info-box {
    padding: 16px 18px;
    border-radius: 12px;
    background-color: #F6F8FB;
    border: 1px solid #E4E8EF;
    margin-bottom: 18px;
}

.warning-box {
    padding: 16px 18px;
    border-radius: 12px;
    background-color: #FFF8E8;
    border: 1px solid #F2D89B;
    margin-bottom: 18px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE
# ============================================================

@st.cache_resource
def get_engine():
    return create_engine(
        DB_URL,
        pool_pre_ping=True,
    )


engine = get_engine()


@st.cache_data(ttl=300)
def run_query(query):
    with engine.connect() as conn:
        return pd.read_sql(
            text(query),
            conn,
        )


# ============================================================
# BASE COMMUNE
# ============================================================

OPS_CTE = """
WITH ops AS (

    SELECT
        type,
        work_type,
        contract_reference,
        service_code,
        sla_intervention_value,
        sla_intervention_unit,
        sla_recovery_value,
        sla_recovery_unit

    FROM operations_active_current

    UNION ALL

    SELECT
        type,
        work_type,
        contract_reference,
        service_code,
        sla_intervention_value,
        sla_intervention_unit,
        sla_recovery_value,
        sla_recovery_unit

    FROM operations_closed_current

    UNION ALL

    SELECT
        type,
        work_type,
        contract_reference,
        service_code,
        sla_intervention_value,
        sla_intervention_unit,
        sla_recovery_value,
        sla_recovery_unit

    FROM operations_denied_current
)
"""


# ============================================================
# TITRE
# ============================================================

st.title("⏱️ Analyse des SLA dans Intent")

st.caption(
    "Analyse exploratoire de la présence et de la structure "
    "des SLA sur les opérations Intent."
)

st.markdown("""
<div class="warning-box">
<b>Point important :</b><br>
L'absence de SLA dans une opération ne signifie pas nécessairement
qu'aucun engagement contractuel n'existe.
Pour les opérations préventives notamment, le pilotage repose
davantage sur une périodicité que sur un délai de type SLA.
</div>
""", unsafe_allow_html=True)


# ============================================================
# 1. VUE GLOBALE
# ============================================================

query_global = OPS_CTE + """
SELECT

    COUNT(*) AS total_operations,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
           OR sla_recovery_value IS NOT NULL
    ) AS avec_sla,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NULL
          AND sla_recovery_value IS NULL
    ) AS sans_sla,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
    ) AS sla_intervention,

    COUNT(*) FILTER (
        WHERE sla_recovery_value IS NOT NULL
    ) AS sla_recovery,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
          AND sla_recovery_value IS NOT NULL
    ) AS deux_sla

FROM ops;
"""

global_df = run_query(query_global)

g = global_df.iloc[0]

total = int(g["total_operations"])
avec_sla = int(g["avec_sla"])
sans_sla = int(g["sans_sla"])
sla_intervention = int(g["sla_intervention"])
sla_recovery = int(g["sla_recovery"])
deux_sla = int(g["deux_sla"])

pct_avec = (
    avec_sla / total * 100
    if total
    else 0
)

pct_sans = (
    sans_sla / total * 100
    if total
    else 0
)


st.markdown(
    '<div class="section-title">Vue globale</div>',
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Opérations analysées",
    f"{total:,}".replace(",", " "),
)

c2.metric(
    "Avec au moins un SLA",
    f"{avec_sla:,}".replace(",", " "),
    f"{pct_avec:.1f} %",
)

c3.metric(
    "Sans SLA renseigné",
    f"{sans_sla:,}".replace(",", " "),
    f"{pct_sans:.1f} %",
)

c4.metric(
    "Avec les 2 SLA",
    f"{deux_sla:,}".replace(",", " "),
)


c5, c6 = st.columns(2)

c5.metric(
    "SLA Intervention",
    f"{sla_intervention:,}".replace(",", " "),
)

c6.metric(
    "SLA Recovery",
    f"{sla_recovery:,}".replace(",", " "),
)


# ============================================================
# 2. COUVERTURE PAR TYPE D'OPERATION
# ============================================================

query_work_type = OPS_CTE + """
SELECT
    type,
    COALESCE(work_type, 'NON RENSEIGNE') AS work_type,

    COUNT(*) AS total_operations,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
    ) AS avec_sla_intervention,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_intervention_value IS NOT NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_sla_intervention,

    COUNT(*) FILTER (
        WHERE sla_recovery_value IS NOT NULL
    ) AS avec_sla_recovery,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_recovery_value IS NOT NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_sla_recovery,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
          AND sla_recovery_value IS NOT NULL
    ) AS avec_les_deux,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
           OR sla_recovery_value IS NOT NULL
    ) AS avec_sla,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_intervention_value IS NOT NULL
               OR sla_recovery_value IS NOT NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_avec_sla,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NULL
          AND sla_recovery_value IS NULL
    ) AS sans_sla,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_intervention_value IS NULL
              AND sla_recovery_value IS NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_sans_sla

FROM ops

GROUP BY
    type,
    work_type

ORDER BY
    total_operations DESC;
"""

df_work = run_query(query_work_type)


st.markdown(
    '<div class="section-title">Couverture SLA par type d’opération</div>',
    unsafe_allow_html=True,
)


chart_work = (
    df_work[
        [
            "work_type",
            "pct_avec_sla",
            "pct_sans_sla",
        ]
    ]
    .copy()
    .set_index("work_type")
)

st.bar_chart(
    chart_work,
    horizontal=True,
)


display_work = df_work.rename(
    columns={
        "type": "Type",
        "work_type": "Nature",
        "total_operations": "Opérations",
        "avec_sla_intervention": "SLA intervention",
        "pct_sla_intervention": "% SLA intervention",
        "avec_sla_recovery": "SLA recovery",
        "pct_sla_recovery": "% SLA recovery",
        "avec_les_deux": "Les 2 SLA",
        "avec_sla": "Au moins 1 SLA",
        "pct_avec_sla": "% avec SLA",
        "sans_sla": "Sans SLA",
        "pct_sans_sla": "% sans SLA",
    }
)

st.dataframe(
    display_work,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 3. INSIGHTS AUTOMATIQUES
# ============================================================

st.markdown(
    '<div class="section-title">À retenir</div>',
    unsafe_allow_html=True,
)

corrective = df_work[
    df_work["work_type"] == "corrective"
]

preventive = df_work[
    df_work["work_type"] == "preventive"
]

setup = df_work[
    df_work["work_type"] == "setup"
]


insights = []

if not corrective.empty:

    row = corrective.iloc[0]

    insights.append(
        f"""
        **Curatif :**
        {row['pct_avec_sla']:.1f} % des opérations disposent
        d'au moins un SLA renseigné,
        contre {row['pct_sans_sla']:.1f} % sans SLA.
        """
    )


if not preventive.empty:

    row = preventive.iloc[0]

    insights.append(
        f"""
        **Préventif :**
        seulement {row['pct_avec_sla']:.1f} % disposent
        d'un SLA technique.
        Cette faible couverture est cohérente avec une logique
        davantage basée sur la périodicité.
        """
    )


if not setup.empty:

    row = setup.iloc[0]

    insights.append(
        f"""
        **Setup :**
        {row['pct_avec_sla']:.1f} % des opérations disposent
        d'au moins un SLA, un comportement sensiblement différent
        des autres catégories.
        """
    )


for insight in insights:

    st.markdown(
        f"""
        <div class="info-box">
        {insight}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 4. ZOOM CURATIF PAR CODE PRESTATION
# ============================================================

st.markdown(
    '<div class="section-title">Zoom curatif par code prestation</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Objectif : comprendre si la présence d'un SLA dépend "
    "du type de prestation."
)


query_services = OPS_CTE + """
SELECT
    COALESCE(service_code, 'NON RENSEIGNE') AS service_code,

    COUNT(*) AS total_operations,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
           OR sla_recovery_value IS NOT NULL
    ) AS avec_sla,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_intervention_value IS NOT NULL
               OR sla_recovery_value IS NOT NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_avec_sla,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NULL
          AND sla_recovery_value IS NULL
    ) AS sans_sla,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_intervention_value IS NULL
              AND sla_recovery_value IS NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_sans_sla

FROM ops

WHERE work_type = 'corrective'

GROUP BY service_code

HAVING COUNT(*) >= 100

ORDER BY
    total_operations DESC;
"""

df_services = run_query(query_services)


top_services = (
    df_services
    .head(20)
    .copy()
)

st.bar_chart(
    top_services.set_index(
        "service_code"
    )[
        [
            "pct_avec_sla",
            "pct_sans_sla",
        ]
    ],
    horizontal=True,
)

st.dataframe(
    df_services,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 5. ZOOM CONTRAT + PRESTATION
# ============================================================

st.markdown(
    '<div class="section-title">Zoom contrat / prestation</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Permet d'identifier si la présence d'un SLA varie "
    "selon le contrat pour une même prestation."
)


query_contracts = OPS_CTE + """
SELECT
    contract_reference,
    service_code,

    COUNT(*) AS total_operations,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NOT NULL
           OR sla_recovery_value IS NOT NULL
    ) AS avec_sla,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_intervention_value IS NOT NULL
               OR sla_recovery_value IS NOT NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_avec_sla,

    COUNT(*) FILTER (
        WHERE sla_intervention_value IS NULL
          AND sla_recovery_value IS NULL
    ) AS sans_sla,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE sla_intervention_value IS NULL
              AND sla_recovery_value IS NULL
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_sans_sla

FROM ops

WHERE work_type = 'corrective'

GROUP BY
    contract_reference,
    service_code

HAVING COUNT(*) >= 50

ORDER BY
    total_operations DESC;
"""

df_contracts = run_query(
    query_contracts
)


st.dataframe(
    df_contracts,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 6. VALEURS SLA
# ============================================================

st.markdown(
    '<div class="section-title">Quels délais SLA sont réellement utilisés ?</div>',
    unsafe_allow_html=True,
)


query_values = OPS_CTE + """
SELECT
    work_type,

    sla_intervention_value,
    sla_intervention_unit,

    sla_recovery_value,
    sla_recovery_unit,

    COUNT(*) AS nb_operations

FROM ops

WHERE sla_intervention_value IS NOT NULL
   OR sla_recovery_value IS NOT NULL

GROUP BY
    work_type,
    sla_intervention_value,
    sla_intervention_unit,
    sla_recovery_value,
    sla_recovery_unit

ORDER BY
    nb_operations DESC

LIMIT 100;
"""

df_values = run_query(
    query_values
)


st.dataframe(
    df_values,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 7. CONCLUSION
# ============================================================

st.markdown(
    '<div class="section-title">Lecture métier</div>',
    unsafe_allow_html=True,
)

st.markdown("""
<div class="info-box">

<b>Ce que l'analyse permet déjà d'établir :</b>

<br><br>

• Les deux SLA techniques disponibles dans les opérations Intent sont
<b>maxTimeToIntervention</b> et <b>maxTimeToRecovery</b>.

<br><br>

• Leur présence varie fortement selon la nature de l'opération.

<br><br>

• Pour le préventif, l'analyse des SLA techniques ne suffit pas :
la logique de pilotage doit être complétée par la
<b>périodicité contractuelle</b>.

<br><br>

• Pour le curatif, l'absence de SLA dans l'opération ne doit pas encore
être interprétée comme une absence d'engagement contractuel.

<br><br>

• La prochaine étape consiste à déterminer si les SLA sont définis
selon le <b>code prestation</b>, le <b>contrat</b>,
le niveau d'urgence ou une combinaison de ces éléments.

</div>
""", unsafe_allow_html=True)