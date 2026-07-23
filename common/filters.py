
import streamlit as st
import pandas as pd


# =====================================================
# PALETTE OFFICIELLE 3F
# =====================================================

C_3F_RED = "#E5114D"
C_3F_NAVY = "#173B69"
C_3F_BLUE = "#0074FF"
C_3F_BLUE_LIGHT = "#80CDFF"
C_3F_PINK = "#FFB7E3"
C_3F_VIOLET = "#432ABD"
C_3F_TEAL = "#008080"
C_3F_YELLOW = "#FFDC55"

C_WHITE = "#FFFFFF"
C_BG_SOFT = "#F8FAFD"
C_BORDER = "#DCE5F0"
C_TEXT = "#173B69"
C_TEXT_SOFT = "#6C7890"
C_PLACEHOLDER = "#929BAD"


# =====================================================
# STYLE FILTRES
# =====================================================

def inject_filters_style():
    st.markdown(
        f"""
        <style>
        /* ==================================================
           SIDEBAR
        ================================================== */

        [data-testid="stSidebar"] {{
            background: #F7F9FC !important;
            border-right: 1px solid {C_BORDER} !important;
        }}

        [data-testid="stSidebarContent"] {{
            padding-top: 1.2rem !important;
        }}

        /* ==================================================
           EN-TÊTE DES FILTRES
        ================================================== */

        .filters-header {{
            position: relative;
            overflow: hidden;
            margin: 12px 0 20px 0;
            padding: 22px 22px 20px 22px;

            background: #EEF5FA;

            border: 1px solid rgba(23, 59, 105, 0.10);
            border-radius: 18px;

            box-shadow: 0 8px 20px -18px rgba(23, 59, 105, 0.24);
        }}

        .filters-header::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: {C_3F_RED};
        }}

        .filters-header::after {{
            display: none;
        }}

        .filters-title {{
            position: relative;
            z-index: 1;
            color: {C_3F_NAVY};
            font-size: 25px;
            line-height: 1.1;
            font-weight: 800;
            letter-spacing: -0.4px;
            margin-bottom: 8px;
        }}

        .filters-subtitle {{
            position: relative;
            z-index: 1;
            color: rgba(23, 59, 105, 0.82);
            font-size: 13px;
            line-height: 1.5;
            font-weight: 600;
            max-width: 330px;
        }}

        /* ==================================================
           LABELS
        ================================================== */

        [data-testid="stSidebar"] label {{
            color: {C_3F_NAVY} !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
            color: {C_3F_NAVY} !important;
            font-weight: 700 !important;
        }}

        /* ==================================================
           MULTISELECT
        ================================================== */

        [data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            min-height: 50px !important;
            background: rgba(255, 255, 255, 0.92) !important;
            border: 1px solid {C_BORDER} !important;
            border-radius: 14px !important;
            box-shadow:
                0 8px 18px -18px rgba(23, 59, 105, 0.40) !important;

            transition:
                border-color 0.16s ease,
                box-shadow 0.16s ease,
                transform 0.16s ease,
                background 0.16s ease !important;
        }}

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {{
            border-color: #AEBECD !important;
            background: {C_WHITE} !important;
            transform: none;
        }}

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {{
            border-color: {C_3F_NAVY} !important;
            box-shadow:
                0 0 0 3px rgba(23, 59, 105, 0.08),
                0 10px 20px -18px rgba(23, 59, 105, 0.45) !important;
        }}

        [data-testid="stSidebar"] div[data-baseweb="select"] span {{
            color: {C_3F_NAVY} !important;
        }}

        [data-testid="stSidebar"] div[data-baseweb="select"] input {{
            color: {C_3F_NAVY} !important;
        }}

        [data-testid="stSidebar"] div[data-baseweb="select"] input::placeholder {{
            color: {C_PLACEHOLDER} !important;
            opacity: 1 !important;
        }}

        /* Valeurs sélectionnées */

        [data-testid="stSidebar"] span[data-baseweb="tag"] {{
            background: #EAF2F8 !important;

            color: {C_3F_NAVY} !important;
            border: 1px solid rgba(67, 42, 189, 0.16) !important;
            border-radius: 9px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] span[data-baseweb="tag"] svg {{
            fill: {C_3F_NAVY} !important;
        }}

        /* Chevron */

        [data-testid="stSidebar"] div[data-baseweb="select"] svg {{
            fill: {C_3F_NAVY} !important;
        }}

        /* ==================================================
           LISTE DÉROULANTE
        ================================================== */

        div[data-baseweb="popover"] ul {{
            background: {C_WHITE} !important;
            border: 1px solid {C_BORDER} !important;
            border-radius: 14px !important;
            box-shadow:
                0 18px 40px -24px rgba(23, 59, 105, 0.38) !important;
            padding: 6px !important;
        }}

        div[data-baseweb="popover"] li {{
            color: {C_3F_NAVY} !important;
            border-radius: 10px !important;
            margin: 2px 0 !important;
        }}

        div[data-baseweb="popover"] li:hover {{
            background: #F1F5F8 !important;
        }}

        div[data-baseweb="popover"] li[aria-selected="true"] {{
            background: #EAF2F8 !important;
            color: {C_3F_NAVY} !important;
            font-weight: 700 !important;
        }}

        /* ==================================================
           MÉTADONNÉES SOUS LES FILTRES
        ================================================== */

        .filter-meta {{
            margin-top: 6px;
            margin-bottom: 17px;
            padding-left: 2px;
            color: {C_TEXT_SOFT};
            font-size: 11px;
            line-height: 1.35;
            font-weight: 600;
        }}

        .filter-meta::before {{
            content: "";
            display: inline-block;
            width: 6px;
            height: 6px;
            margin-right: 7px;
            border-radius: 999px;
            background: {C_3F_NAVY};
            vertical-align: middle;
        }}

        /* ==================================================
           BOUTON RÉINITIALISER
        ================================================== */

        [data-testid="stSidebar"] .stButton button {{
            min-height: 50px !important;
            margin-bottom: 16px !important;

            color: {C_3F_NAVY} !important;
            background: #FFFFFF !important;

            border: 1px solid rgba(23, 59, 105, 0.14) !important;
            border-radius: 14px !important;

            font-size: 13px !important;
            font-weight: 800 !important;

            box-shadow: 0 6px 16px -16px rgba(23, 59, 105, 0.24) !important;

            transition:
                transform 0.16s ease,
                background 0.16s ease,
                border-color 0.16s ease,
                color 0.16s ease !important;
        }}

        [data-testid="stSidebar"] .stButton button:hover {{
            color: {C_WHITE} !important;
            background: {C_3F_NAVY} !important;

            border-color: {C_3F_NAVY} !important;
            transform: none;
        }}

        [data-testid="stSidebar"] .stButton button:focus {{
            box-shadow:
                0 0 0 3px rgba(23, 59, 105, 0.10) !important;
        }}

        /* ==================================================
           ESPACEMENTS
        ================================================== */

        [data-testid="stSidebar"] hr {{
            border-top: 1px solid rgba(23, 59, 105, 0.10) !important;
            margin: 18px 0 !important;
        }}

        @media screen and (max-width: 900px) {{
            .filters-title {{
                font-size: 22px;
            }}

            .filters-header {{
                padding: 20px 18px 18px 18px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        r"""
        <style>
        [data-testid="stSidebar"] {
            background: #F5F7FA !important;
            border-right: 1px solid #DCE4EC !important;
        }

        [data-testid="stSidebarContent"] {
            padding-top: 1rem !important;
        }

        .filters-header {
            position: relative;
            overflow: hidden;
            margin: 10px 0 18px 0 !important;
            padding: 20px 20px 18px 20px !important;
            background: #FFF1F6 !important;
            border: 1px solid #E8D9E1 !important;
            border-radius: 16px !important;
            box-shadow: none !important;
        }

        .filters-header::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: #E5114D !important;
        }

        .filters-header::after {
            display: none !important;
        }

        .filters-title {
            color: #173B69 !important;
            font-size: 23px !important;
            line-height: 1.12 !important;
            font-weight: 800 !important;
            margin-bottom: 7px !important;
        }

        .filters-subtitle {
            color: #5D6E82 !important;
            font-size: 12.5px !important;
            font-weight: 600 !important;
            line-height: 1.5 !important;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #173B69 !important;
            font-weight: 700 !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            min-height: 48px !important;
            background: #FFFFFF !important;
            border: 1px solid #D8E1E9 !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            transition: border-color .15s ease, box-shadow .15s ease !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
            border-color: #B8C6D2 !important;
            background: #FFFFFF !important;
            transform: none !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
            border-color: #173B69 !important;
            box-shadow: 0 0 0 3px rgba(23, 59, 105, 0.08) !important;
        }

        [data-testid="stSidebar"] span[data-baseweb="tag"] {
            background: #EEF4F8 !important;
            color: #173B69 !important;
            border: 1px solid #CBD9E4 !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
        }

        [data-testid="stSidebar"] span[data-baseweb="tag"] svg {
            fill: #173B69 !important;
        }

        .filter-meta {
            margin-top: 6px !important;
            margin-bottom: 16px !important;
            color: #77879A !important;
            font-size: 11px !important;
            font-weight: 600 !important;
        }

        .filter-meta::before {
            width: 6px !important;
            height: 6px !important;
            margin-right: 7px !important;
            background: #173B69 !important;
        }

        [data-testid="stSidebar"] .stButton button {
            min-height: 47px !important;
            margin-bottom: 16px !important;
            color: #173B69 !important;
            background: #FFFFFF !important;
            border: 1px solid #D8E1E9 !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            font-weight: 700 !important;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            color: #173B69 !important;
            background: #EEF4F8 !important;
            border-color: #B8C6D2 !important;
            transform: none !important;
        }

        div[data-baseweb="popover"] ul {
            background: #FFFFFF !important;
            border: 1px solid #D8E1E9 !important;
            border-radius: 12px !important;
            box-shadow: 0 12px 28px -20px rgba(23, 59, 105, 0.28) !important;
        }

        div[data-baseweb="popover"] li:hover {
            background: #EEF4F8 !important;
        }

        div[data-baseweb="popover"] li[aria-selected="true"] {
            background: #E7F0F6 !important;
            color: #173B69 !important;
        }
        </style>
""",
        unsafe_allow_html=True,
    )


# =====================================================

    st.markdown(
        r"""
        <style>
        [data-testid="stSidebar"] {
            background: #FAF8FA !important;
            border-right: 1px solid #E7E3E8 !important;
        }

        .filters-header {
            margin: 10px 0 18px 0 !important;
            padding: 20px 20px 18px 20px !important;
            background: #FFF1F6 !important;
            border: 1px solid #E8D8E1 !important;
            border-radius: 16px !important;
            box-shadow: none !important;
        }

        .filters-header::before {
            background: #E5114D !important;
        }

        .filters-header::after {
            display: none !important;
        }

        .filters-title {
            color: #1B2430 !important;
            font-size: 23px !important;
            font-weight: 800 !important;
        }

        .filters-subtitle {
            color: #667085 !important;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #1B2430 !important;
            font-weight: 700 !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            min-height: 48px !important;
            background: #FFFFFF !important;
            border: 1px solid #E1DCE2 !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
            border-color: #D7BEC9 !important;
            transform: none !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
            border-color: #E5114D !important;
            box-shadow: 0 0 0 3px rgba(229, 17, 77, 0.08) !important;
        }

        [data-testid="stSidebar"] span[data-baseweb="tag"] {
            background: #FFF1F6 !important;
            color: #A3184A !important;
            border: 1px solid #E7C8D6 !important;
            border-radius: 8px !important;
        }

        [data-testid="stSidebar"] span[data-baseweb="tag"] svg {
            fill: #A3184A !important;
        }

        .filter-meta {
            color: #8A94A6 !important;
        }

        .filter-meta::before {
            background: #E5114D !important;
        }

        [data-testid="stSidebar"] .stButton button {
            color: #A3184A !important;
            background: #FFFFFF !important;
            border: 1px solid #E1DCE2 !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            color: #E5114D !important;
            background: #FFF7FA !important;
            border-color: #D7BEC9 !important;
            transform: none !important;
        }

        div[data-baseweb="popover"] li:hover {
            background: #FFF7FA !important;
        }

        div[data-baseweb="popover"] li[aria-selected="true"] {
            background: #FFF1F6 !important;
            color: #A3184A !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        r"""
        <style>
        /* Le logo reste visible mais ne crée plus un grand vide. */
        [data-testid="stSidebarHeader"] {
            min-height: 78px !important;
            padding-top: 14px !important;
            padding-bottom: 8px !important;
        }

        [data-testid="stSidebarUserContent"] {
            padding-top: 0 !important;
        }

        [data-testid="stSidebarContent"] {
            padding-top: 0 !important;
        }

        .filters-header {
            margin-top: 0 !important;
            margin-bottom: 18px !important;
            min-height: 178px !important;
            box-sizing: border-box !important;

            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }

        [data-testid="stSidebar"] .stButton button {
            min-height: 48px !important;
        }

        /* Même rythme vertical entre tous les filtres. */
        .filter-meta {
            margin-bottom: 15px !important;
        }

        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
            margin-bottom: 5px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# =====================================================
# OUTILS
# =====================================================


VALEURS_INVALIDES_FILTRES = {
    "",
    "nan",
    "None",
    "<NA>",
    "Non renseigné",
}


COLONNES_FILTRES = [
    "contract_reference",
    "societe",
    "agence",
    "groupe",
    "secteur",
    "esi_reference",
    "contract_topic",
    "third_party_label",
]


CORRESPONDANCE_FILTRES = {
    "contract_reference": "filtre_contrat",
    "societe": "filtre_societe",
    "agence": "filtre_agence",
    "groupe": "filtre_groupe",
    "secteur": "filtre_secteur",
    "esi_reference": "filtre_programme",
    "contract_topic": "filtre_metier",
    "third_party_label": "filtre_prestataire",
}


def options_triees(
    df: pd.DataFrame,
    colonne: str,
) -> list:
    if colonne not in df.columns:
        return []

    valeurs = (
        df[colonne]
        .dropna()
        .astype(str)
        .str.strip()
    )

    valeurs = valeurs[
        ~valeurs.isin(VALEURS_INVALIDES_FILTRES)
    ]

    return sorted(
        valeurs.unique().tolist()
    )


def filtrer_df(
    df: pd.DataFrame,
    filtres: dict,
) -> pd.DataFrame:
    out = df.copy()

    for colonne, valeurs in filtres.items():
        if valeurs and colonne in out.columns:
            serie = (
                out[colonne]
                .astype("string")
                .str.strip()
            )

            out = out[
                serie.isin(valeurs)
            ].copy()

    return out


def nettoyer_session_state(
    key: str,
    options: list,
):
    if key not in st.session_state:
        return

    valeur_actuelle = st.session_state[key]

    if not isinstance(valeur_actuelle, list):
        valeur_actuelle = []

    st.session_state[key] = [
        valeur
        for valeur in valeur_actuelle
        if valeur in options
    ]


def construire_options_contrat(
    df: pd.DataFrame,
):
    """
    Retourne les références de contrats disponibles.

    Le dictionnaire des libellés est conservé pour compatibilité,
    mais les options affichées sont les références.
    """

    if "contract_reference" not in df.columns:
        return [], {}

    colonnes = [
        "contract_reference",
    ]

    if "contract_label" in df.columns:
        colonnes.append(
            "contract_label"
        )

    temp = df[colonnes].copy()

    temp["contract_reference"] = (
        temp["contract_reference"]
        .astype("string")
        .str.strip()
        .replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "<NA>": pd.NA,
            }
        )
    )

    temp = temp[
        temp["contract_reference"].notna()
    ].copy()

    if "contract_label" not in temp.columns:
        temp["contract_label"] = ""

    temp["contract_label"] = (
        temp["contract_label"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    temp = (
        temp
        .drop_duplicates(
            subset=["contract_reference"]
        )
        .sort_values(
            "contract_reference"
        )
    )

    options = (
        temp["contract_reference"]
        .astype(str)
        .tolist()
    )

    labels = dict(
        zip(
            temp["contract_reference"].astype(str),
            temp["contract_label"],
        )
    )

    return options, labels


def construire_options_programme(
    df: pd.DataFrame,
):
    """
    Retourne uniquement les références Programme / ESI.

    Le libellé n'est pas utilisé dans l'affichage du filtre.
    """

    if "esi_reference" not in df.columns:
        return [], {}

    temp = df[
        ["esi_reference"]
    ].copy()

    temp["esi_reference"] = (
        temp["esi_reference"]
        .astype("string")
        .str.strip()
        .replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "<NA>": pd.NA,
            }
        )
    )

    temp = temp[
        temp["esi_reference"].notna()
    ].copy()

    temp = (
        temp
        .drop_duplicates(
            subset=["esi_reference"]
        )
        .sort_values(
            "esi_reference"
        )
    )

    options = (
        temp["esi_reference"]
        .astype(str)
        .tolist()
    )

    return options, {}

def marquer_filtre_modifie(key: str):
    """
    Mémorise le filtre que l'utilisateur vient réellement de modifier.
    Ce filtre devient prioritaire lors de la synchronisation.
    """
    st.session_state["_dernier_filtre_modifie"] = key

def render_multiselect(
    label,
    options,
    key,
    placeholder,
    format_func=None,
):
    selected = st.sidebar.multiselect(
        label,
        options=options,
        key=key,
        placeholder=placeholder,
        format_func=(
            format_func
            if format_func is not None
            else lambda valeur: valeur
        ),
        on_change=marquer_filtre_modifie,
        args=(key,),
    )

    nb_selected = len(selected)
    nb_options = len(options)

    if nb_selected == 0:
        meta = f"{nb_options} option(s) disponible(s)"
    else:
        meta = (
            f"{nb_selected} sélection(s) · "
            f"{nb_options} option(s) disponible(s)"
        )

    st.sidebar.markdown(
        f'<div class="filter-meta">{meta}</div>',
        unsafe_allow_html=True,
    )

    return selected


def _selection_session(
    key: str,
) -> list:
    """
    Lit proprement une sélection présente dans
    st.session_state.
    """

    valeur = st.session_state.get(
        key,
        [],
    )

    if not isinstance(
        valeur,
        list,
    ):
        return []

    return [
        str(element).strip()
        for element in valeur
        if str(element).strip()
        not in VALEURS_INVALIDES_FILTRES
    ]


def _normaliser_colonne_filtre(
    df: pd.DataFrame,
    colonne: str,
) -> pd.Series:
    """
    Normalise une colonne utilisée dans la base
    de synchronisation.
    """

    if colonne not in df.columns:
        return pd.Series(
            pd.NA,
            index=df.index,
            dtype="string",
        )

    return (
        df[colonne]
        .astype("string")
        .str.strip()
        .replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "<NA>": pd.NA,
            }
        )
    )


def construire_base_filtres_synchronises(
    df_esi: pd.DataFrame,
    df_contrats: pd.DataFrame,
    inclure_esi_sans_contrat: bool = True,
) -> pd.DataFrame:
    """
    Construit une base relationnelle unique pour
    l'ensemble des filtres.

    Une ligne de contrat conserve :
    contrat, société, agence, groupe, secteur,
    référence ESI, métier et prestataire.

    Les ESI sans contrat peuvent être ajoutés afin
    de rester disponibles quand aucun filtre
    contractuel n'est sélectionné.
    """

    contrats = df_contrats.copy()

    for colonne in COLONNES_FILTRES:
        contrats[colonne] = (
            _normaliser_colonne_filtre(
                contrats,
                colonne,
            )
        )

    contrats = contrats[
        COLONNES_FILTRES
    ].copy()

    morceaux = [
        contrats,
    ]

    if inclure_esi_sans_contrat:
        esi = df_esi.copy()

        for colonne in COLONNES_FILTRES:
            esi[colonne] = (
                _normaliser_colonne_filtre(
                    esi,
                    colonne,
                )
            )

        morceaux.append(
            esi[
                COLONNES_FILTRES
            ].copy()
        )

    return (
        pd.concat(
            morceaux,
            ignore_index=True,
        )
        .drop_duplicates()
        .reset_index(drop=True)
    )


def filtrer_base_synchronisee(
    base: pd.DataFrame,
    selections: dict,
    colonne_ignoree: str | None = None,
) -> pd.DataFrame:
    """
    Applique toutes les sélections sur la base.

    colonne_ignoree permet de calculer les options
    d'un filtre sans que celui-ci se filtre lui-même.
    """

    out = base.copy()

    for colonne, valeurs in selections.items():
        if colonne == colonne_ignoree:
            continue

        if (
            valeurs
            and colonne in out.columns
        ):
            out = out[
                out[colonne].isin(valeurs)
            ].copy()

    return out


def options_filtre_synchronisees(
    base: pd.DataFrame,
    colonne_cible: str,
    selections: dict,
) -> list:
    """
    Retourne les options d'un filtre en tenant compte
    de toutes les autres sélections.
    """

    contexte = filtrer_base_synchronisee(
        base=base,
        selections=selections,
        colonne_ignoree=colonne_cible,
    )

    return options_triees(
        contexte,
        colonne_cible,
    )


def _stabiliser_selections_filtres(
    base: pd.DataFrame,
    correspondance: dict,
    max_iterations: int = 12,
):
    """
    Synchronise les filtres en conservant en priorité
    celui que l'utilisateur vient de modifier.

    Les autres sélections incompatibles sont supprimées.
    """

    derniere_cle = st.session_state.get(
        "_dernier_filtre_modifie"
    )

    colonne_prioritaire = next(
        (
            colonne
            for colonne, cle in correspondance.items()
            if cle == derniere_cle
        ),
        None,
    )

    for _ in range(max_iterations):
        changements = False

        selections = {
            colonne: _selection_session(cle)
            for colonne, cle in correspondance.items()
        }

        # Le filtre modifié est toujours traité en dernier
        # afin de ne pas être supprimé par un ancien filtre.
        colonnes_ordonnees = [
            colonne
            for colonne in correspondance
            if colonne != colonne_prioritaire
        ]

        if colonne_prioritaire is not None:
            colonnes_ordonnees.append(
                colonne_prioritaire
            )

        for colonne in colonnes_ordonnees:
            cle = correspondance[colonne]

            selection_actuelle = _selection_session(
                cle
            )

            # On ne supprime jamais la sélection du filtre
            # que l'utilisateur vient de modifier.
            if colonne == colonne_prioritaire:
                continue

            options_valides = options_filtre_synchronisees(
                base=base,
                colonne_cible=colonne,
                selections=selections,
            )

            selection_valide = [
                valeur
                for valeur in selection_actuelle
                if valeur in options_valides
            ]

            if selection_valide != selection_actuelle:
                st.session_state[cle] = selection_valide
                selections[colonne] = selection_valide
                changements = True

        if not changements:
            break


def _appliquer_statut_contrat(
    df_contrats: pd.DataFrame,
    statut_vue_globale: str,
) -> pd.DataFrame:
    """
    Applique le filtre actif / inactif choisi
    au-dessus du dashboard.
    """

    base_contrats = df_contrats.copy()

    if (
        "contract_status_clean"
        in base_contrats.columns
    ):
        statut_normalise = (
            base_contrats[
                "contract_status_clean"
            ]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
        )

    elif (
        "contract_status"
        in base_contrats.columns
    ):
        statut_normalise = (
            base_contrats[
                "contract_status"
            ]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
        )

    else:
        statut_normalise = pd.Series(
            "",
            index=base_contrats.index,
            dtype="string",
        )

    if (
        statut_vue_globale
        == "Contrats actifs"
    ):
        return base_contrats[
            statut_normalise == "active"
        ].copy()

    if (
        statut_vue_globale
        == "Contrats inactifs"
    ):
        return base_contrats[
            statut_normalise != "active"
        ].copy()

    return base_contrats


def _rechercher_references_contrats(
    base_contrats: pd.DataFrame,
    recherche: str,
) -> list:
    """
    Recherche les références des contrats correspondant
    au texte saisi dans le tableau.
    """

    if not recherche:
        return []

    if (
        "contract_reference"
        not in base_contrats.columns
    ):
        return []

    colonnes_recherche = [
        colonne
        for colonne in [
            "contract_reference",
            "contract_label",
            "third_party_label",
            "contract_topic",
        ]
        if colonne in base_contrats.columns
    ]

    if not colonnes_recherche:
        return []

    masque = pd.Series(
        False,
        index=base_contrats.index,
    )

    for colonne in colonnes_recherche:
        masque = (
            masque
            | base_contrats[colonne]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(
                recherche,
                regex=False,
            )
        )

    references = (
        base_contrats.loc[
            masque,
            "contract_reference",
        ]
        .dropna()
        .astype(str)
        .str.strip()
    )

    references = references[
        ~references.isin(
            VALEURS_INVALIDES_FILTRES
        )
    ]

    return references.unique().tolist()


def _refs_esi_depuis_contrats(
    df_contrats: pd.DataFrame,
) -> list:
    if (
        df_contrats.empty
        or "esi_reference"
        not in df_contrats.columns
    ):
        return []

    references = (
        df_contrats[
            "esi_reference"
        ]
        .dropna()
        .astype(str)
        .str.strip()
    )

    references = references[
        ~references.isin(
            VALEURS_INVALIDES_FILTRES
        )
    ]

    return references.unique().tolist()


# =====================================================
# FILTRES PATRIMOINE
# =====================================================


def reinitialiser_filtres_dashboard():
    """
    Réinitialise les filtres sans changer l'onglet actif.
    """

    # On conserve l'onglet dans lequel se trouve l'utilisateur.
    vue_active = st.session_state.get(
        "dashboard_vue_active",
        "Vue globale",
    )

    # Les multiselects doivent recevoir une liste vide.
    cles_multiselect = [
        "filtre_contrat",
        "filtre_societe",
        "filtre_agence",
        "filtre_groupe",
        "filtre_secteur",
        "filtre_programme",
        "filtre_metier",
        "filtre_prestataire",
    ]

    for cle in cles_multiselect:
        st.session_state[cle] = []

    # Réinitialisation explicite des autres filtres.
    st.session_state["global_search_contract"] = ""
    st.session_state["vg_filtre_statut_contrat"] = (
        "Tous les contrats"
    )
    st.session_state["global_contract_table_mode"] = (
        "Contrats uniques"
    )

    # On conserve impérativement l'onglet actif.
    st.session_state["dashboard_vue_active"] = vue_active

    # Nettoyage des états techniques.
    cles_techniques = [
        "_derniere_recherche_contrat_synchro",
        "_dernier_filtre_modifie",
    ]

    for cle in cles_techniques:
        st.session_state.pop(
            cle,
            None,
        )

    prefixes = (
        "colonne_uniques_",
        "colonne_rattachements_",
        "colonne_prestations_",
        "page_table_contrats_",
        "page_precedente_",
        "page_suivante_",
        "form_colonnes_",
        "tout_selectionner_",
        "reinitialiser_colonnes_",
        "preparer_export_",
        "annuler_export_",
        "export_complet_",
    )

    for cle in list(
        st.session_state.keys()
    ):
        if cle.startswith(prefixes):
            del st.session_state[cle]


def render_filtres_patrimoine(
    df_esi: pd.DataFrame,
    df_contrats: pd.DataFrame,
    reset_keys=None,
):
    """
    Filtres patrimoine totalement synchronisés.

    Une sélection dans n'importe quel filtre réduit
    immédiatement les options de tous les autres :

    contrat
    société
    agence
    groupe
    secteur
    ESI
    métier
    prestataire
    """

    inject_filters_style()

    if reset_keys is None:
        reset_keys = [
            "filtre_contrat",
            "filtre_societe",
            "filtre_agence",
            "filtre_groupe",
            "filtre_secteur",
            "filtre_programme",
            "filtre_metier",
            "filtre_prestataire",
        ]

    st.sidebar.markdown(
        """
        <div class="filters-header">
            <div class="filters-title">Filtres</div>
            <div class="filters-subtitle">Chaque sélection actualise toutes les autres listes disponibles.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.button(
        "Réinitialiser tous les filtres",
        width="stretch",
        key="btn_reset_filtres_patrimoine",
        on_click=(
            reinitialiser_filtres_dashboard
        ),
    )

    # =================================================
    # 1. STATUT CONTRAT
    # =================================================

    statut_vue_globale = (
        st.session_state.get(
            "vg_filtre_statut_contrat",
            "Tous les contrats",
        )
    )

    base_contrats = (
        _appliquer_statut_contrat(
            df_contrats=df_contrats,
            statut_vue_globale=(
                statut_vue_globale
            ),
        )
    )

    # Les lignes ESI sans contrat sont utiles quand
    # aucun statut contractuel précis n'est imposé.
    inclure_esi_sans_contrat = (
        statut_vue_globale
        == "Tous les contrats"
    )

    base_synchro = (
        construire_base_filtres_synchronises(
            df_esi=df_esi,
            df_contrats=base_contrats,
            inclure_esi_sans_contrat=(
                inclure_esi_sans_contrat
            ),
        )
    )

    # =================================================
    # 2. RECHERCHE TABLEAU -> CONTRAT
    # =================================================

    recherche_tableau = str(
        st.session_state.get(
            "global_search_contract",
            "",
        )
        or ""
    ).strip().lower()

    contrats_recherche = (
        _rechercher_references_contrats(
            base_contrats=base_contrats,
            recherche=recherche_tableau,
        )
    )

    derniere_recherche = (
        st.session_state.get(
            "_derniere_recherche_contrat_synchro"
        )
    )

    if (
        recherche_tableau
        != derniere_recherche
    ):
        st.session_state[
            "_derniere_recherche_contrat_synchro"
        ] = recherche_tableau

        st.session_state[
            "filtre_contrat"
        ] = (
            contrats_recherche
            if recherche_tableau
            else []
        )

    # =================================================
    # 3. STABILISATION DES SÉLECTIONS
    # =================================================

    _stabiliser_selections_filtres(
        base=base_synchro,
        correspondance=(
            CORRESPONDANCE_FILTRES
        ),
    )

    selections_avant_widgets = {
        colonne: _selection_session(cle)
        for colonne, cle
        in CORRESPONDANCE_FILTRES.items()
    }

    # Toutes les listes sont calculées à partir
    # exactement du même état de filtres.
    options = {
        colonne: (
            options_filtre_synchronisees(
                base=base_synchro,
                colonne_cible=colonne,
                selections=(
                    selections_avant_widgets
                ),
            )
        )
        for colonne
        in CORRESPONDANCE_FILTRES
    }

    # Sécurité supplémentaire avant création
    # des widgets Streamlit.
    for colonne, cle in (
        CORRESPONDANCE_FILTRES.items()
    ):
        nettoyer_session_state(
            key=cle,
            options=options[colonne],
        )

    # =================================================
    # 4. WIDGETS
    # =================================================

    selected_contrats = (
        render_multiselect(
            label="Contrat",
            options=options[
                "contract_reference"
            ],
            key="filtre_contrat",
            placeholder=(
                "Tous les contrats"
            ),
        )
    )

    selected_societes = (
        render_multiselect(
            label="Société",
            options=options["societe"],
            key="filtre_societe",
            placeholder=(
                "Toutes les sociétés"
            ),
        )
    )

    selected_agences = (
        render_multiselect(
            label="Agence",
            options=options["agence"],
            key="filtre_agence",
            placeholder=(
                "Toutes les agences"
            ),
        )
    )

    selected_groupes = (
        render_multiselect(
            label="Groupe",
            options=options["groupe"],
            key="filtre_groupe",
            placeholder=(
                "Tous les groupes"
            ),
        )
    )

    selected_secteurs = (
        render_multiselect(
            label="Secteur",
            options=options["secteur"],
            key="filtre_secteur",
            placeholder=(
                "Tous les secteurs"
            ),
        )
    )

    # Pas de format_func :
    # l'utilisateur voit uniquement esi_reference.
    selected_programmes = (
        render_multiselect(
            label=(
                "Référence programme / ESI"
            ),
            options=options[
                "esi_reference"
            ],
            key="filtre_programme",
            placeholder=(
                "Toutes les références "
                "programme / ESI"
            ),
        )
    )

    selected_metiers = (
        render_multiselect(
            label="Métier",
            options=options[
                "contract_topic"
            ],
            key="filtre_metier",
            placeholder=(
                "Tous les métiers"
            ),
        )
    )

    selected_prestataires = (
        render_multiselect(
            label="Prestataire",
            options=options[
                "third_party_label"
            ],
            key="filtre_prestataire",
            placeholder=(
                "Tous les prestataires"
            ),
        )
    )

    # =================================================
    # 5. APPLICATION FINALE
    # =================================================

    filtres_contrats = {
        "contract_reference": (
            selected_contrats
        ),
        "societe": selected_societes,
        "agence": selected_agences,
        "groupe": selected_groupes,
        "secteur": selected_secteurs,
        "esi_reference": (
            selected_programmes
        ),
        "contract_topic": (
            selected_metiers
        ),
        "third_party_label": (
            selected_prestataires
        ),
    }

    df_contrats_filtre = filtrer_df(
        df=base_contrats,
        filtres=filtres_contrats,
    )

    filtres_geo = {
        "societe": selected_societes,
        "agence": selected_agences,
        "groupe": selected_groupes,
        "secteur": selected_secteurs,
        "esi_reference": (
            selected_programmes
        ),
    }

    df_esi_filtre = filtrer_df(
        df=df_esi,
        filtres=filtres_geo,
    )

    # Un contrat, un métier ou un prestataire
    # réduit aussi le parc ESI.
    filtre_contractuel_actif = bool(
        selected_contrats
        or selected_metiers
        or selected_prestataires
    )

    if filtre_contractuel_actif:
        esi_restants = (
            _refs_esi_depuis_contrats(
                df_contrats_filtre
            )
        )

        if esi_restants:
            df_esi_filtre = (
                df_esi_filtre[
                    df_esi_filtre[
                        "esi_reference"
                    ]
                    .astype(str)
                    .str.strip()
                    .isin(esi_restants)
                ]
                .copy()
            )
        else:
            df_esi_filtre = (
                df_esi_filtre
                .iloc[0:0]
                .copy()
            )

    filtres_selectionnes = {
        "contrat": selected_contrats,
        "recherche_contrat": (
            recherche_tableau
        ),
        "societe": selected_societes,
        "agence": selected_agences,
        "groupe": selected_groupes,
        "secteur": selected_secteurs,
        "programme": (
            selected_programmes
        ),
        "metier": selected_metiers,
        "prestataire": (
            selected_prestataires
        ),
        "statut_contrat": (
            statut_vue_globale
        ),
    }

    return (
        df_esi_filtre,
        df_contrats_filtre,
        filtres_selectionnes,
    )