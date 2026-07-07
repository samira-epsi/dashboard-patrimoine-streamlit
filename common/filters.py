import streamlit as st
import pandas as pd


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

    st.session_state[key] = [
        value for value in st.session_state[key]
        if value in options
    ]


def construire_options_programme(df: pd.DataFrame):
    if "esi_reference" not in df.columns:
        return [], {}

    temp = (
        df[["esi_reference", "esi_label"]]
        .drop_duplicates()
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
        format_func=format_func if format_func else lambda x: x
    )

    nb_selected = len(selected)
    nb_options = len(options)

    if nb_selected == 0:
        meta = f"{nb_options} option(s) disponible(s)"
    else:
        meta = f"{nb_selected} sélection(s) · {nb_options} option(s) disponible(s)"

    st.sidebar.markdown(
        f'<div class="filter-meta">{meta}</div>',
        unsafe_allow_html=True
    )

    return selected


def render_filtres_patrimoine(
    df_esi: pd.DataFrame,
    df_contrats: pd.DataFrame,
    reset_keys=None
):
    """
    Bloc filtres réutilisable.

    Entrées :
    - df_esi : dataframe niveau ESI
    - df_contrats : dataframe niveau contrat x ESI

    Retourne :
    - df_esi_filtre
    - df_contrats_filtre
    - filtres_selectionnes
    """

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
                Affinez le périmètre par ESO, ESI, métier et prestataire.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.sidebar.button("Réinitialiser tous les filtres", use_container_width=True):
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
        placeholder="Toutes les sociétés"
    )

    df_apres_societe = filtrer_df(
        base_geo,
        {"societe": selected_societes}
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
        placeholder="Toutes les agences"
    )

    df_apres_agence = filtrer_df(
        df_apres_societe,
        {"agence": selected_agences}
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
        placeholder="Tous les groupes"
    )

    df_apres_groupe = filtrer_df(
        df_apres_agence,
        {"groupe": selected_groupes}
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
        placeholder="Tous les secteurs"
    )

    df_apres_secteur = filtrer_df(
        df_apres_groupe,
        {"secteur": selected_secteurs}
    )

    # -------------------------------
    # Programme / ESI
    # -------------------------------
    programme_options, programme_labels = construire_options_programme(df_apres_secteur)
    nettoyer_session_state("filtre_programme", programme_options)

    selected_programmes = render_multiselect(
        label="Programme / ESI",
        options=programme_options,
        key="filtre_programme",
        placeholder="Tous les programmes / ESI",
        format_func=lambda ref: f"{ref} — {programme_labels.get(ref, '')}"
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
    metier_options = options_triees(df_contrats_geo, "contract_topic")
    nettoyer_session_state("filtre_metier", metier_options)

    selected_metiers = render_multiselect(
        label="Métier",
        options=metier_options,
        key="filtre_metier",
        placeholder="Tous les métiers"
    )

    df_apres_metier = filtrer_df(
        df_contrats_geo,
        {"contract_topic": selected_metiers}
    )

    # -------------------------------
    # Prestataire
    # -------------------------------
    prestataire_options = options_triees(df_apres_metier, "third_party_label")
    nettoyer_session_state("filtre_prestataire", prestataire_options)

    selected_prestataires = render_multiselect(
        label="Prestataire",
        options=prestataire_options,
        key="filtre_prestataire",
        placeholder="Tous les prestataires"
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

    df_contrats_filtre = filtrer_df(df_contrats, filtres_contrats)

    # Si métier / prestataire sélectionné,
    # on réduit aussi les ESI au périmètre contractuel restant.
    if selected_metiers or selected_prestataires:
        if "esi_reference" in df_contrats_filtre.columns:
            esi_restants = (
                df_contrats_filtre["esi_reference"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            df_esi_filtre = df_esi_filtre[
                df_esi_filtre["esi_reference"].isin(esi_restants)
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

    return df_esi_filtre, df_contrats_filtre, filtres_selectionnes