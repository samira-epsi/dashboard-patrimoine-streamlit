
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

# OUTILS
# =====================================================

def options_triees(df: pd.DataFrame, colonne: str):
    if colonne not in df.columns:
        return []

    valeurs = (
        df[colonne]
        .dropna()
        .astype(str)
        .str.strip()
    )

    valeurs = valeurs[
        (valeurs != "")
        & (valeurs != "Non renseigné")
        & (valeurs != "nan")
        & (valeurs != "None")
    ]

    return sorted(valeurs.unique().tolist())


def filtrer_df(df: pd.DataFrame, filtres: dict) -> pd.DataFrame:
    out = df.copy()

    for colonne, valeurs in filtres.items():
        if valeurs and colonne in out.columns:
            out = out[out[colonne].isin(valeurs)]

    return out


def nettoyer_session_state(key: str, options: list):
    if key not in st.session_state:
        return

    valeur_actuelle = st.session_state[key]

    if not isinstance(valeur_actuelle, list):
        valeur_actuelle = []

    st.session_state[key] = [
        value for value in valeur_actuelle
        if value in options
    ]


def construire_options_programme(df: pd.DataFrame):
    if "esi_reference" not in df.columns:
        return [], {}

    colonnes = ["esi_reference"]
    if "esi_label" in df.columns:
        colonnes.append("esi_label")

    temp = df[colonnes].copy()
    temp = temp[temp["esi_reference"].notna()]
    temp["esi_reference"] = temp["esi_reference"].astype(str).str.strip()
    temp = temp[temp["esi_reference"] != ""]

    if "esi_label" not in temp.columns:
        temp["esi_label"] = ""

    temp["esi_label"] = (
        temp["esi_label"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    temp = (
        temp
        .drop_duplicates(subset=["esi_reference"])
        .sort_values("esi_reference")
    )

    options = temp["esi_reference"].tolist()
    labels = dict(zip(temp["esi_reference"], temp["esi_label"]))

    return options, labels


def render_multiselect(label, options, key, placeholder, format_func=None):
    selected = st.sidebar.multiselect(
        label,
        options=options,
        key=key,
        placeholder=placeholder,
        format_func=format_func if format_func else lambda x: x,
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


# =====================================================
# FILTRES PATRIMOINE
# =====================================================

def render_filtres_patrimoine(
    df_esi: pd.DataFrame,
    df_contrats: pd.DataFrame,
    reset_keys=None,
):
    """
    Bloc de filtres réutilisable.

    Entrées
    -------
    df_esi :
        DataFrame au niveau ESI.

    df_contrats :
        DataFrame au niveau contrat x ESI.

    reset_keys :
        Clés Streamlit à réinitialiser.

    Retour
    ------
    df_esi_filtre
    df_contrats_filtre
    filtres_selectionnes
    """

    inject_filters_style()

    if reset_keys is None:
        reset_keys = [
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
            <div class="filters-title">Filtres patrimoine</div>
            <div class="filters-subtitle">
                Affinez le périmètre par société, agence,
                programme / ESI, métier et prestataire.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "Réinitialiser tous les filtres",
        use_container_width=True,
        key="btn_reset_filtres_patrimoine",
    ):
        for key in reset_keys:
            st.session_state[key] = []
        st.rerun()

    base_geo = df_esi.copy()

    # -------------------------------
    # Société
    # -------------------------------

    societe_options = options_triees(base_geo, "societe")
    nettoyer_session_state("filtre_societe", societe_options)

    selected_societes = render_multiselect(
        label="Société",
        options=societe_options,
        key="filtre_societe",
        placeholder="Toutes les sociétés",
    )

    df_apres_societe = filtrer_df(
        base_geo,
        {"societe": selected_societes},
    )

    # -------------------------------
    # Agence
    # -------------------------------

    agence_options = options_triees(df_apres_societe, "agence")
    nettoyer_session_state("filtre_agence", agence_options)

    selected_agences = render_multiselect(
        label="Agence",
        options=agence_options,
        key="filtre_agence",
        placeholder="Toutes les agences",
    )

    df_apres_agence = filtrer_df(
        df_apres_societe,
        {"agence": selected_agences},
    )

    # -------------------------------
    # Groupe
    # -------------------------------

    groupe_options = options_triees(df_apres_agence, "groupe")
    nettoyer_session_state("filtre_groupe", groupe_options)

    selected_groupes = render_multiselect(
        label="Groupe",
        options=groupe_options,
        key="filtre_groupe",
        placeholder="Tous les groupes",
    )

    df_apres_groupe = filtrer_df(
        df_apres_agence,
        {"groupe": selected_groupes},
    )

    # -------------------------------
    # Secteur
    # -------------------------------

    secteur_options = options_triees(df_apres_groupe, "secteur")
    nettoyer_session_state("filtre_secteur", secteur_options)

    selected_secteurs = render_multiselect(
        label="Secteur",
        options=secteur_options,
        key="filtre_secteur",
        placeholder="Tous les secteurs",
    )

    df_apres_secteur = filtrer_df(
        df_apres_groupe,
        {"secteur": selected_secteurs},
    )

    # -------------------------------
    # Programme / ESI
    # -------------------------------

    programme_options, programme_labels = construire_options_programme(
        df_apres_secteur
    )
    nettoyer_session_state("filtre_programme", programme_options)

    selected_programmes = render_multiselect(
        label="Programme / ESI",
        options=programme_options,
        key="filtre_programme",
        placeholder="Tous les programmes / ESI",
        format_func=lambda ref: (
            f"{ref} — {programme_labels.get(ref, '')}"
            if programme_labels.get(ref, "")
            else str(ref)
        ),
    )

    # -------------------------------
    # Filtres géographiques
    # -------------------------------

    filtres_geo = {
        "societe": selected_societes,
        "agence": selected_agences,
        "groupe": selected_groupes,
        "secteur": selected_secteurs,
        "esi_reference": selected_programmes,
    }

    df_esi_filtre = filtrer_df(df_esi, filtres_geo)
    df_contrats_geo = filtrer_df(df_contrats, filtres_geo)

    # -------------------------------
    # Métier
    # -------------------------------

    metier_options = options_triees(
        df_contrats_geo,
        "contract_topic",
    )
    nettoyer_session_state("filtre_metier", metier_options)

    selected_metiers = render_multiselect(
        label="Métier",
        options=metier_options,
        key="filtre_metier",
        placeholder="Tous les métiers",
    )

    df_apres_metier = filtrer_df(
        df_contrats_geo,
        {"contract_topic": selected_metiers},
    )

    # -------------------------------
    # Prestataire
    # -------------------------------

    prestataire_options = options_triees(
        df_apres_metier,
        "third_party_label",
    )
    nettoyer_session_state(
        "filtre_prestataire",
        prestataire_options,
    )

    selected_prestataires = render_multiselect(
        label="Prestataire",
        options=prestataire_options,
        key="filtre_prestataire",
        placeholder="Tous les prestataires",
    )

    # -------------------------------
    # Filtres contrats complets
    # -------------------------------

    filtres_contrats = {
        "societe": selected_societes,
        "agence": selected_agences,
        "groupe": selected_groupes,
        "secteur": selected_secteurs,
        "esi_reference": selected_programmes,
        "contract_topic": selected_metiers,
        "third_party_label": selected_prestataires,
    }

    df_contrats_filtre = filtrer_df(
        df_contrats,
        filtres_contrats,
    )

    # Si métier ou prestataire est sélectionné,
    # on réduit aussi les ESI au périmètre contractuel restant.

    if selected_metiers or selected_prestataires:
        if "esi_reference" in df_contrats_filtre.columns:
            esi_restants = (
                df_contrats_filtre["esi_reference"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            esi_restants = esi_restants[
                (esi_restants != "")
                & (esi_restants != "nan")
                & (esi_restants != "None")
            ].unique().tolist()

            df_esi_filtre = df_esi_filtre[
                df_esi_filtre["esi_reference"]
                .astype(str)
                .isin(esi_restants)
            ]

    filtres_selectionnes = {
        "societe": selected_societes,
        "agence": selected_agences,
        "groupe": selected_groupes,
        "secteur": selected_secteurs,
        "programme": selected_programmes,
        "metier": selected_metiers,
        "prestataire": selected_prestataires,
    }

    return (
        df_esi_filtre,
        df_contrats_filtre,
        filtres_selectionnes,
    )
