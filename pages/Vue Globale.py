from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
except ImportError:
    go = None

from common.app_config import setup_page
from common.charts_style import *
from common.charts_style import _layout_plotly
from common.filters import render_filtres_patrimoine
from common.export_utils import dataframe_download
from common.ui_style import (
    _safe,
    apply_3f_page_style,
    apply_vue_globale_style,
    vg_alert_card as alert_card,
    vg_hero as hero,
    vg_info as info,
    vg_kpi_card as kpi_card,
    vg_section as section,
)
from common.vue_globale_data import *
from common.vue_globale_tables import *


setup_page("Vue Globale", None)

logo_path = Path("assets/Logo.png")
if logo_path.exists():
    st.logo(str(logo_path))

apply_3f_page_style()
apply_vue_globale_style()


def effacer_recherche_contrat():
    st.session_state["global_search_contract"] = ""

# =====================================================
# GRAPHIQUES ET COMPOSANTS DE LA PAGE
# =====================================================


def afficher_evolution_contrats(
    df_contrats: pd.DataFrame,
    df_prestations: pd.DataFrame,
):
    section(
        "Évolution des contrats dans Intent",
        "Créations, désactivations et stock de contrats selon les dates enregistrées dans Intent.",
    )

    c_granularite, c_periode = st.columns([1, 1], gap="large")

    with c_granularite:
        st.markdown(
            '<div class="vg-mini-title">Granularité</div>',
            unsafe_allow_html=True,
        )
        granularite = st.radio(
            "Granularité",
            ["Mensuel", "Annuel"],
            horizontal=True,
            label_visibility="collapsed",
            key="evolution_granularite",
        )

    with c_periode:
        if granularite == "Mensuel":
            st.markdown(
                '<div class="vg-mini-title">Période mensuelle</div>',
                unsafe_allow_html=True,
            )
            periode_label = st.radio(
                "Période mensuelle",
                ["12 mois", "24 mois", "36 mois"],
                index=1,
                horizontal=True,
                label_visibility="collapsed",
                key="evolution_periode_mensuelle",
            )
            nb_mois = int(periode_label.split()[0])
        else:
            st.markdown(
                '<div class="vg-mini-title">Période annuelle</div>',
                unsafe_allow_html=True,
            )
            periode_label = st.radio(
                "Période annuelle",
                ["3 ans", "5 ans", "10 ans"],
                index=1,
                horizontal=True,
                label_visibility="collapsed",
                key="evolution_periode_annuelle",
            )
            nb_mois = int(periode_label.split()[0]) * 12

    evolution = construire_evolution_contrats(
        df_contrats=df_contrats,
        df_prestations=df_prestations,
        granularite=granularite,
        nb_mois=nb_mois,
    )

    if evolution.empty:
        st.info("Aucune donnée d'évolution disponible.")
        return

    col_flux, col_stock = st.columns(
        [1, 1],
        gap="medium",
        vertical_alignment="top",
    )

    with col_flux:
        st.markdown(
            '<div class="vg-mini-title">Flux de contrats</div>',
            unsafe_allow_html=True,
        )

        fig_flux = go.Figure()

        fig_flux.add_trace(
            go.Bar(
                x=evolution["Période"],
                y=evolution["Créés"],
                name="Créés",
                marker=dict(color=C_RED),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Contrats créés : %{y}<extra></extra>"
                ),
            )
        )

        fig_flux.add_trace(
            go.Bar(
                x=evolution["Période"],
                y=evolution["Désactivés"],
                name="Désactivés",
                marker=dict(color=C_BLUE_LIGHT),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Contrats désactivés : %{y}<extra></extra>"
                ),
            )
        )

        _layout_plotly(fig_flux, 360)
        fig_flux.update_layout(
            barmode="group",
            bargap=0.28,
            bargroupgap=0.08,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                title=None,
            ),
            margin=dict(l=55, r=18, t=50, b=70),
            xaxis=dict(
                title=None,
                type="category",
                categoryorder="array",
                categoryarray=evolution["Période"].tolist(),
                tickmode="array",
                tickvals=graduations_periodes(evolution, maximum=6),
                ticktext=graduations_periodes(evolution, maximum=6),
                tickangle=-25 if len(evolution) > 12 else 0,
                showgrid=False,
                automargin=True,
            ),
            yaxis=dict(
                title="Nombre de contrats",
                rangemode="tozero",
                gridcolor=C_GRID,
                zeroline=False,
            ),
        )

        st.plotly_chart(
            fig_flux,
            use_container_width=True,
            config=config_plotly("evolution_flux_contrats"),
        )

    with col_stock:
        st.markdown(
            '<div class="vg-mini-title">Stock de contrats</div>',
            unsafe_allow_html=True,
        )

        fig_stock = go.Figure()

        series_stock = [
            ("Contrats actifs", C_RED),
            ("Contrats inactifs", C_BLUE_LIGHT),
            ("Actifs avec date de fin dépassée", C_VIOLET),
        ]

        for colonne, couleur in series_stock:
            fig_stock.add_trace(
                go.Scatter(
                    x=evolution["Période"],
                    y=evolution[colonne],
                    name=colonne,
                    mode="lines+markers",
                    line=dict(color=couleur, width=3),
                    marker=dict(size=6),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        + colonne
                        + " : %{y}<extra></extra>"
                    ),
                )
            )

        _layout_plotly(fig_stock, 360)
        fig_stock.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                title=None,
            ),
            margin=dict(l=55, r=18, t=50, b=70),
            hovermode="x unified",
            xaxis=dict(
                title=None,
                type="category",
                categoryorder="array",
                categoryarray=evolution["Période"].tolist(),
                tickmode="array",
                tickvals=graduations_periodes(evolution, maximum=6),
                ticktext=graduations_periodes(evolution, maximum=6),
                tickangle=-25 if len(evolution) > 12 else 0,
                showgrid=False,
                automargin=True,
            ),
            yaxis=dict(
                title="Nombre de contrats",
                rangemode="tozero",
                gridcolor=C_GRID,
                zeroline=False,
            ),
        )

        st.plotly_chart(
            fig_stock,
            use_container_width=True,
            config=config_plotly("evolution_stock_contrats"),
        )

    export = evolution[
        [
            "Période",
            "Créés",
            "Désactivés",
            "Contrats actifs",
            "Contrats inactifs",
            "Actifs avec date de fin dépassée",
        ]
    ].copy()

    dataframe_download(
        "Télécharger les données d’évolution des contrats",
        export,
        "evolution_contrats.xlsx",
    )

    st.caption(
        "Les périodes sans événement sont conservées et affichées avec une valeur égale à zéro. "
        "Le stock historique est reconstitué à partir des dates de création et de désactivation disponibles dans Intent."
    )


# =====================================================
# GRAPHIQUES, COMPOSANTS ET EXPORTS
# =====================================================


def construire_couverture(df_esi_base, df_esi_couverts, utiliser_selection_contrats):
    base = dedupliquer_esi(df_esi_base)

    if base.empty:
        return pd.DataFrame(
            {
                "Indicateur": ["Programmes", "Logements", "Équipements"],
                "Couverts": [0, 0, 0],
                "Total": [0, 0, 0],
                "Taux": [0.0, 0.0, 0.0],
            }
        )

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
        (
            "Programmes",
            len(liste_refs_valides(couverts, "esi_reference")),
            len(liste_refs_valides(base, "esi_reference")),
        ),
        ("Logements", int(couverts["nb_logements"].sum()), int(base["nb_logements"].sum())),
        ("Équipements", int(couverts["nb_equipements"].sum()), int(base["nb_equipements"].sum())),
    ]

    rows = []
    for indicateur, couverts_value, total in data:
        taux = round((couverts_value / total) * 100, 1) if total else 0.0
        rows.append(
            {
                "Indicateur": indicateur,
                "Couverts": couverts_value,
                "Total": total,
                "Taux": taux,
            }
        )

    return pd.DataFrame(rows)


def afficher_couverture(df_couverture: pd.DataFrame):
    if df_couverture.empty:
        st.info("Aucune donnée de couverture disponible.")
        return

    df = df_couverture.copy().sort_values("Taux", ascending=True)
    df["Texte"] = df.apply(lambda row: fmt_pourcentage(row["Taux"]), axis=1)
    df["Détail"] = df.apply(
        lambda row: f"{fmt_nombre(row['Couverts'])} / {fmt_nombre(row['Total'])}",
        axis=1,
    )

    if go is None:
        st.bar_chart(df.set_index("Indicateur")["Taux"], width="stretch")
        return

    fig = go.Figure()
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
            hovertemplate=(
                "<b>%{y}</b><br>Taux : %{x:.1f} %"
                "<br>Détail : %{customdata}<extra></extra>"
            ),
            marker=dict(color=C_RED),
        )
    )
    _layout_plotly(fig, 300)
    fig.update_layout(
        barmode="overlay",
        bargap=0.42,
        xaxis=dict(
            range=[0, 100],
            ticksuffix=" %",
            gridcolor=C_GRID,
            zeroline=False,
            title=None,
        ),
        yaxis=dict(title=None, automargin=True),
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=config_plotly("taux_couverture_patrimoine"),
    )


def construire_graph_metier(df_contrats: pd.DataFrame, top_n=20):
    if df_contrats.empty:
        return pd.DataFrame(columns=["Métier", "Contrats"])

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

    return (
        df.drop_duplicates(["contract_reference", "contract_topic"])
        .groupby("contract_topic", as_index=False)["contract_reference"]
        .nunique()
        .rename(columns={"contract_topic": "Métier", "contract_reference": "Contrats"})
        .sort_values("Contrats", ascending=False)
        .head(top_n)
        .sort_values("Contrats", ascending=True)
    )


def afficher_barres_horizontales(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    color=C_RED,
    height_base=320,
    fixed_height=None,
):
    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    if go is None:
        st.bar_chart(df.set_index(label_col)[value_col], width="stretch")
        return

    max_value = max(float(df[value_col].max()), 1.0)
    height = (
        int(fixed_height)
        if fixed_height is not None
        else max(height_base, 34 * len(df) + 80)
    )

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
        margin=dict(l=18, r=46, t=14, b=24),
        xaxis=dict(
            range=[0, max_value * 1.18],
            gridcolor=C_GRID,
            zeroline=False,
            title=None,
        ),
        yaxis=dict(title=None, automargin=True),
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=config_plotly("graphique_barres_horizontales"),
    )


def construire_graph_qualite(df_resume: pd.DataFrame, df_qualite: pd.DataFrame):
    if not df_resume.empty:
        count_col = None
        for candidate in ["nombre_objets_distincts", "nb_objets_distincts"]:
            if candidate in df_resume.columns:
                count_col = candidate
                break

        if count_col and "anomalie_type" in df_resume.columns:
            df = df_resume.copy()
            df[count_col] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)
            return (
                df.groupby("anomalie_type", as_index=False)[count_col]
                .sum()
                .rename(
                    columns={
                        "anomalie_type": "Anomalie",
                        count_col: "Objets distincts",
                    }
                )
                .sort_values("Objets distincts", ascending=False)
                .head(8)
                .sort_values("Objets distincts", ascending=True)
            )

    if not df_qualite.empty and {"anomalie_type", "objet_reference"}.issubset(df_qualite.columns):
        return (
            df_qualite.groupby("anomalie_type", as_index=False)["objet_reference"]
            .nunique()
            .rename(
                columns={
                    "anomalie_type": "Anomalie",
                    "objet_reference": "Objets distincts",
                }
            )
            .sort_values("Objets distincts", ascending=False)
            .head(8)
            .sort_values("Objets distincts", ascending=True)
        )

    return pd.DataFrame(columns=["Anomalie", "Objets distincts"])


# =====================================================
# PAGE
# =====================================================

hero(
    "Pilotage du patrimoine",
    "Une lecture en trois temps : réalité source, couverture exploitable, puis anomalies à corriger.",
)

ok, erreur = tester_connexion()
if not ok:
    st.error("Connexion PostgreSQL impossible.")
    st.code(erreur)
    st.stop()

nav_col, refresh_col = st.columns([5, 1], vertical_alignment="bottom")

with nav_col:
    with st.container(key="dashboard_tabs"):
        vue_active = st.radio(
            "Navigation",
            ["Vue globale", "Couverture", "Qualité et anomalies"],
            horizontal=True,
            label_visibility="collapsed",
            key="dashboard_vue_active",
        )

with refresh_col:
    if st.button("Actualiser", width="stretch", key="dashboard_refresh"):
        st.cache_data.clear()
        st.rerun()

chargement_placeholder = st.empty()
chargement_placeholder.markdown(
    """
    <div class="vg-loading-card">
        <div class="vg-loading-mark">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <div>
            <div class="vg-loading-title">Chargement du patrimoine</div>
            <div class="vg-loading-subtitle">
                Préparation des données, des filtres et des indicateurs…
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    (
        df_global,
        df_esi,
        df_contrats,
        df_prestations,
        df_equipements_couverture,
        df_equipements_contrats,
        df_creations,
        df_qualite,
        df_qualite_resume,
    ) = charger_donnees()
except Exception as exc:
    chargement_placeholder.empty()
    st.error("Erreur pendant le chargement des données.")
    st.code(str(exc))
    st.stop()
finally:
    chargement_placeholder.empty()

if df_global.empty:
    st.error("La table dashboard.kpi_globale est vide.")
    st.stop()

# Filtres patrimoine dans la barre latérale.
df_esi_filtre, df_contrats_filtre, filtres_selectionnes = render_filtres_patrimoine(
    df_esi=df_esi,
    df_contrats=df_contrats,
)

with st.container(key="contract_status_filter"):
    st.markdown(
        '<div class="vg-mini-title">Statut des contrats</div>',
        unsafe_allow_html=True,
    )
    statut_selectionne = afficher_filtre_statut_contrat()
    st.caption(
        "Les totaux source restent fixes dans la vue globale. "
        "La couverture et les détails suivent les filtres sélectionnés."
    )

# Calculs communs.
df_contrats_kpi = filtrer_contrats_par_statut(
    df_contrats_filtre,
    statut_selectionne,
)

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

df_esi_kpi = filtrer_esi_depuis_contrats(
    df_esi_filtre,
    df_contrats_kpi,
    filtre_contrat_actif,
)
df_esi_base = dedupliquer_esi(df_esi_filtre)
df_esi_context = dedupliquer_esi(df_esi_kpi)

df_prestations_kpi = filtrer_prestations_depuis_contrats(
    df_prestations=df_prestations,
    df_contrats_kpi=df_contrats_kpi,
    perimetre_filtre_actif=perimetre_filtre_actif,
    statut_selectionne=statut_selectionne,
)

df_contrats_source_kpi = construire_contrats_uniques_source(
    df_prestations=df_prestations_kpi,
    df_contrats_rattaches=df_contrats_kpi,
)


df_equipements_couverture_kpi = filtrer_table_par_esi(
    df_equipements_couverture,
    df_esi_context,
)
df_equipements_contrats_kpi = filtrer_table_par_esi(
    df_equipements_contrats,
    df_esi_context,
)


# =====================================================
# VUE 1 — VUE GLOBALE
# =====================================================

if vue_active == "Vue globale":
    if statut_selectionne == "active":
        section(
            "Vue globale",
            "Périmètre des contrats actifs et patrimoine associé.",
        )
    elif statut_selectionne == "inactive":
        section(
            "Vue globale",
            "Périmètre des contrats inactifs et patrimoine associé.",
        )
    else:
        section(
            "Vue globale",
            "La réalité présente dans Intent, puis la part réellement exploitable pour les analyses de couverture.",
        )

    # Tous les contrats sans filtre : on conserve la lecture globale de la source.
    if statut_selectionne is None and not perimetre_filtre_actif:
        contrats_value = global_value(df_global, "contrats_total")
        contrats_pill = (
            f"{fmt_nombre(global_value(df_global, 'contrats_rattaches_programme'))} exploitables"
        )
        contrats_help = (
            f"{fmt_nombre(global_value(df_global, 'contrats_non_rattaches_programme'))} "
            "non rattachés à un programme."
        )

        programmes_value = global_value(df_global, "programmes_total")
        programmes_couverts = int(serie_numerique(df_esi, "esi_couvert").sum())
        programmes_pill = f"{fmt_nombre(programmes_couverts)} couverts"
        programmes_help = "Programmes / ESI présents dans la source patrimoniale."

        logements_value = global_value(df_global, "logements_total")
        logements_pill = (
            f"{fmt_nombre(global_value(df_global, 'logements_rattaches_programme'))} exploitables"
        )
        logements_help = (
            f"{fmt_nombre(global_value(df_global, 'logements_sans_programme'))} sans programme."
        )

        equipements_value = global_value(df_global, "equipements_total")
        equipements_pill = (
            f"{fmt_nombre(global_value(df_global, 'equipements_rattaches_programme'))} exploitables"
        )
        equipements_help = (
            f"{fmt_nombre(global_value(df_global, 'equipements_sans_programme'))} sans programme."
        )

        contrats_label = "Contrats"
        programmes_label = "Programmes / ESI"
        logements_label = "Logements"
        equipements_label = "Équipements"

    # Contrats actifs : les titres suffisent à raconter la relation entre contrats et patrimoine.
    elif statut_selectionne == "active":
        contrats_value = len(liste_refs_valides(df_contrats_kpi, "contract_reference"))
        programmes_value = len(liste_refs_valides(df_esi_context, "esi_reference"))
        logements_value = int(serie_numerique(df_esi_context, "nb_logements").sum())
        equipements_value = int(serie_numerique(df_esi_context, "nb_equipements").sum())

        contrats_label = "Contrats actifs"
        programmes_label = "ESI concernés"
        logements_label = "Logements rattachés"
        equipements_label = "Équipements rattachés"

        contrats_pill = contrats_help = ""
        programmes_pill = programmes_help = ""
        logements_pill = logements_help = ""
        equipements_pill = equipements_help = ""

    # Contrats inactifs : même lecture, sans introduire une notion de couverture.
    elif statut_selectionne == "inactive":
        contrats_value = len(liste_refs_valides(df_contrats_kpi, "contract_reference"))
        programmes_value = len(liste_refs_valides(df_esi_context, "esi_reference"))
        logements_value = int(serie_numerique(df_esi_context, "nb_logements").sum())
        equipements_value = int(serie_numerique(df_esi_context, "nb_equipements").sum())

        contrats_label = "Contrats inactifs"
        programmes_label = "ESI concernés"
        logements_label = "Logements rattachés"
        equipements_label = "Équipements rattachés"

        contrats_pill = contrats_help = ""
        programmes_pill = programmes_help = ""
        logements_pill = logements_help = ""
        equipements_pill = equipements_help = ""

    # Tous les contrats avec un filtre patrimoine ou métier/prestataire actif.
    else:
        contrats_value = len(liste_refs_valides(df_contrats_kpi, "contract_reference"))
        contrats_pill = "Périmètre filtré"
        contrats_help = "Contrats exploitables correspondant aux filtres actifs."

        programmes_value = len(liste_refs_valides(df_esi_context, "esi_reference"))
        programmes_couverts = int(serie_numerique(df_esi_context, "esi_couvert").sum())
        programmes_pill = f"{fmt_nombre(programmes_couverts)} couverts"
        programmes_help = "Programmes / ESI correspondant aux filtres actifs."

        logements_value = int(serie_numerique(df_esi_context, "nb_logements").sum())
        logements_pill = "Rattachés aux ESI"
        logements_help = "Logements exploitables du périmètre filtré."

        equipements_value = int(serie_numerique(df_esi_context, "nb_equipements").sum())
        equipements_pill = "Rattachés aux ESI"
        equipements_help = "Équipements exploitables du périmètre filtré."

        contrats_label = "Contrats"
        programmes_label = "Programmes / ESI"
        logements_label = "Logements"
        equipements_label = "Équipements"

    cartes_compactes = statut_selectionne in {"active", "inactive"}

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card(
            contrats_label,
            contrats_value,
            contrats_pill,
            contrats_help,
            accent=C_NAVY,
            compact=cartes_compactes,
        )
    with c2:
        kpi_card(
            programmes_label,
            programmes_value,
            programmes_pill,
            programmes_help,
            accent=C_NAVY,
            compact=cartes_compactes,
        )
    with c3:
        kpi_card(
            logements_label,
            logements_value,
            logements_pill,
            logements_help,
            accent=C_PINK,
            compact=cartes_compactes,
        )
    with c4:
        kpi_card(
            equipements_label,
            equipements_value,
            equipements_pill,
            equipements_help,
            accent=C_VIOLET,
            compact=cartes_compactes,
        )

    if statut_selectionne is not None:
        statut_texte = "actifs" if statut_selectionne == "active" else "inactifs"
        info(
            f"Les contrats {statut_texte} sélectionnés sont rattachés à "
            f"{fmt_nombre(programmes_value)} ESI, représentant "
            f"{fmt_nombre(logements_value)} logements et "
            f"{fmt_nombre(equipements_value)} équipements. "
            "Seuls les contrats rattachés à un ESI sont inclus ; les autres sont visibles dans "
            "Qualité et anomalies."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    df_graph_metier = construire_graph_metier(
        df_contrats_source_kpi,
        top_n=20,
    )

    HAUTEUR_GRAPHIQUES = max(
        500,
        min(620, 30 * len(df_graph_metier) + 100),
    )

    col_statut, col_metier = st.columns(
        [0.82, 1.35],
        gap="medium",
        vertical_alignment="top",
    )

    with col_statut:
        with st.container(key="global_graph_status"):
            st.markdown(
                '<div class="vg-mini-title">Statut des contrats</div>',
                unsafe_allow_html=True,
            )

            contrats_uniques = df_contrats_source_kpi.drop_duplicates(
                "contract_reference"
            ).copy()
            nb_actifs = int(
                (contrats_uniques["contract_status_clean"] == "active").sum()
            )
            nb_inactifs = int(
                (contrats_uniques["contract_status_clean"] != "active").sum()
            )

            if go is None:
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Statut": ["Actifs", "Inactifs"],
                            "Contrats": [nb_actifs, nb_inactifs],
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                    height=HAUTEUR_GRAPHIQUES,
                )
            else:
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=["Actifs", "Inactifs"],
                            values=[nb_actifs, nb_inactifs],
                            hole=0.66,
                            marker=dict(
                                colors=[C_RED, "#F2DDE3"],
                                line=dict(color="#FFFFFF", width=2),
                            ),
                            textinfo="label+value",
                            textposition="inside",
                            insidetextorientation="horizontal",
                            hovertemplate=(
                                "<b>%{label}</b><br>"
                                "%{value} contrat(s)<extra></extra>"
                            ),
                            domain=dict(x=[0.05, 0.95], y=[0.10, 0.90]),
                            sort=False,
                        )
                    ]
                )
                _layout_plotly(fig, HAUTEUR_GRAPHIQUES)
                fig.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=False,
                    uniformtext_minsize=12,
                    uniformtext_mode="hide",
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config=config_plotly("repartition_statut_contrats"),
                )

    with col_metier:
        with st.container(key="global_graph_metier"):
            st.markdown(
                '<div class="vg-mini-title">Répartition des contrats par métier</div>',
                unsafe_allow_html=True,
            )
            if go is None:
                st.bar_chart(
                    df_graph_metier.set_index("Métier")["Contrats"],
                    width="stretch",
                )
            else:
                max_value = max(
                    float(df_graph_metier["Contrats"].max()),
                    1.0,
                )
                fig_metier = go.Figure(
                    go.Bar(
                        x=df_graph_metier["Contrats"],
                        y=df_graph_metier["Métier"],
                        orientation="h",
                        text=df_graph_metier["Contrats"].apply(fmt_nombre),
                        textposition="outside",
                        textfont=dict(color=C_INK, size=12),
                        cliponaxis=False,
                        marker=dict(color=C_RED),
                        hovertemplate=(
                            "<b>%{y}</b><br>"
                            "Nombre de contrats : %{x}"
                            "<extra></extra>"
                        ),
                    )
                )
                _layout_plotly(fig_metier, HAUTEUR_GRAPHIQUES)
                fig_metier.update_layout(
                    bargap=0.36,
                    margin=dict(l=18, r=46, t=14, b=24),
                    xaxis=dict(
                        range=[0, max_value * 1.18],
                        gridcolor=C_GRID,
                        zeroline=False,
                        title=None,
                    ),
                    yaxis=dict(title=None, automargin=True),
                )
                st.plotly_chart(
                    fig_metier,
                    use_container_width=True,
                    config=config_plotly(
                        "repartition_contrats_par_metier"
                    ),
                )

    with st.expander("Consulter la liste des contrats", expanded=False):
        recherche_contrat = st.text_input(
            "Rechercher un contrat",
            placeholder=(
                "Référence, libellé, prestataire, métier ou code de prestation..."
            ),
            key="global_search_contract",
            help=(
                "La recherche s'applique au niveau d'affichage sélectionné. "
                "Les filtres patrimoine continuent de piloter le périmètre."
            ),
        )

        if recherche_contrat:
            st.markdown(
                (
                    '<div class="vg-search-active">'
                    '<span class="vg-search-active-dot"></span>'
                    '<span>Recherche appliquée au tableau affiché</span>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            st.button(
                "Effacer la recherche",
                key="effacer_recherche_contrat",
                width="content",
                on_click=effacer_recherche_contrat,
            )

        mode_col, colonnes_col = st.columns([1.25, 2.75], vertical_alignment="top")

        with mode_col:
            mode_tableau = st.radio(
                "Niveau d’affichage",
                [
                    "Contrats uniques",
                    "Contrats et rattachements",
                    "Contrats et codes de prestation",
                ],
                horizontal=False,
                key="global_contract_table_mode",
                help=(
                    "Contrats uniques : une ligne par contrat. "
                    "Contrats et rattachements : une ligne par contrat et ESI. "
                    "Contrats et codes de prestation : une ligne par code de prestation."
                ),
            )

        if mode_tableau == "Contrats uniques":
            source_tableau = construire_contrats_uniques_source(
                df_prestations=df_prestations_kpi,
                df_contrats_rattaches=df_contrats_kpi,
            )
            table_contrats_complete = preparer_contrats_table(source_tableau)

        elif mode_tableau == "Contrats et rattachements":
            cles_dedoublonnage = [
                col
                for col in ["contract_reference", "esi_reference"]
                if col in df_contrats_kpi.columns
            ]
            source_tableau = (
                df_contrats_kpi.drop_duplicates(cles_dedoublonnage)
                if cles_dedoublonnage
                else df_contrats_kpi.copy()
            )
            table_contrats_complete = preparer_contrats_table(source_tableau)

        else:
            cles_dedoublonnage = [
                col
                for col in ["contract_reference_3f", "service_code_id_intent"]
                if col in df_prestations_kpi.columns
            ]
            source_tableau = (
                df_prestations_kpi.drop_duplicates(cles_dedoublonnage)
                if cles_dedoublonnage
                else df_prestations_kpi.copy()
            )
            table_contrats_complete = preparer_prestations_table(source_tableau)

        table_contrats_complete = filtrer_table_recherche(
            table_contrats_complete,
            recherche_contrat,
        )

        colonnes_contrat = [
            "Référence contrat",
            "Libellé contrat",
            "Prestataire",
            "Date de début",
            "Date de fin",
            "Métier",
            "Statut",
        ]

        colonnes_rattachement = [
            "Société",
            "Agence",
            "Groupe",
            "Secteur",
            "Référence ESI",
            "Libellé ESI",
        ]

        colonnes_prestation_principales = [
            "Référence contrat 3F",
            "Référence contrat prestataire",
            "Libellé contrat",
            "Prestataire",
            "Métier",
            "Statut",
            "Date de début",
            "Date de fin",
            "Référence prestation 3F",
            "Référence prestation prestataire",
            "Libellé prestation",
            "Type d’intervention",
        ]

        colonnes_prestation_detail = [
            # "Identifiant contrat Intent",
            "Description contrat",
            # "Référence prestataire",
            "Date de création Intent",
            "Date de désactivation Intent",
            "Dernière modification",
            # "Contrat actif expiré",
            # "Identifiant prestation Intent",
            "Description prestation",
            # "Niveau de criticité",
            # "Forfait fixe",
            # "Périodicité SLA",
            # "Unité périodicité",
            # "Durée estimée intervention",
            # "Unité durée estimée",
            # "Délai maximal intervention",
            # "Unité délai intervention",
            # "Délai maximal rétablissement",
            # "Unité délai rétablissement",
        ]

        if mode_tableau == "Contrats et codes de prestation":
            colonnes_disponibles = [
                col
                for col in (
                    colonnes_prestation_principales + colonnes_prestation_detail
                )
                if col in table_contrats_complete.columns
            ]
            colonnes_par_defaut = [
                col
                for col in colonnes_prestation_principales
                if col in colonnes_disponibles
            ]
        else:
            colonnes_disponibles = [
                col
                for col in (colonnes_contrat + colonnes_rattachement)
                if col in table_contrats_complete.columns
            ]
            if mode_tableau == "Contrats uniques":
                colonnes_par_defaut = [
                    col for col in colonnes_contrat if col in colonnes_disponibles
                ]
            else:
                colonnes_par_defaut = [
                    col
                    for col in (
                        colonnes_contrat + ["Référence ESI", "Libellé ESI"]
                    )
                    if col in colonnes_disponibles
                ]

        with colonnes_col:
            st.markdown(
                '<div class="vg-column-title">Colonnes affichées</div>',
                unsafe_allow_html=True,
            )

            if mode_tableau == "Contrats uniques":
                cle_mode = "uniques"
            elif mode_tableau == "Contrats et rattachements":
                cle_mode = "rattachements"
            else:
                cle_mode = "prestations"

            def cle_checkbox_colonne(colonne: str) -> str:
                cle_simple = (
                    colonne.lower()
                    .replace(" ", "_")
                    .replace("é", "e")
                    .replace("è", "e")
                    .replace("ê", "e")
                    .replace("à", "a")
                    .replace("’", "")
                    .replace("'", "")
                    .replace("/", "_")
                )
                return f"colonne_{cle_mode}_{cle_simple}"

            for colonne in colonnes_disponibles:
                cle_case = cle_checkbox_colonne(colonne)
                if cle_case not in st.session_state:
                    st.session_state[cle_case] = colonne in colonnes_par_defaut

            with st.popover("Choisir les colonnes", width="stretch"):
                with st.form(
                    key=f"form_colonnes_{cle_mode}",
                    clear_on_submit=False,
                ):
                    bouton_tout, bouton_reset = st.columns(2)

                    with bouton_tout:
                        tout_selectionner = st.form_submit_button(
                            "Tout sélectionner",
                            width="stretch",
                        )

                    with bouton_reset:
                        reinitialiser = st.form_submit_button(
                            "Réinitialiser",
                            width="stretch",
                        )

                    if tout_selectionner:
                        for colonne in colonnes_disponibles:
                            st.session_state[cle_checkbox_colonne(colonne)] = True

                    if reinitialiser:
                        for colonne in colonnes_disponibles:
                            st.session_state[cle_checkbox_colonne(colonne)] = (
                                colonne in colonnes_par_defaut
                            )

                    st.markdown(
                        '<div class="vg-columns-separator"></div>',
                        unsafe_allow_html=True,
                    )

                    for colonne in colonnes_disponibles:
                        st.checkbox(colonne, key=cle_checkbox_colonne(colonne))

                    st.form_submit_button(
                        "Appliquer",
                        width="stretch",
                        type="primary",
                    )

            colonnes_affichees = [
                colonne
                for colonne in colonnes_disponibles
                if st.session_state.get(cle_checkbox_colonne(colonne), False)
            ]

            st.caption(
                f"{len(colonnes_affichees)} colonne(s) sélectionnée(s)."
                if colonnes_affichees
                else "Aucune colonne sélectionnée."
            )

        if "Référence contrat" in table_contrats_complete.columns:
            colonne_reference_contrat = "Référence contrat"
        elif "Référence contrat 3F" in table_contrats_complete.columns:
            colonne_reference_contrat = "Référence contrat 3F"
        else:
            colonne_reference_contrat = None

        if colonne_reference_contrat:
            nb_contrats_resultat = int(
                table_contrats_complete[colonne_reference_contrat]
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )
        else:
            nb_contrats_resultat = len(table_contrats_complete)

        nb_lignes_resultat = len(table_contrats_complete)

        libelle_contrats = (
            "contrat trouvé" if nb_contrats_resultat == 1 else "contrats trouvés"
        )
        libelle_lignes = (
            "ligne trouvée" if nb_lignes_resultat == 1 else "lignes trouvées"
        )

        resume_html = (
            '<div class="vg-table-summary">'
            '<div class="vg-table-summary-item">'
            f'<span class="vg-table-summary-value">{fmt_nombre(nb_contrats_resultat)}</span>'
            f'<span class="vg-table-summary-label">{libelle_contrats}</span>'
            "</div>"
            '<div class="vg-table-summary-separator"></div>'
            '<div class="vg-table-summary-item">'
            f'<span class="vg-table-summary-value">{fmt_nombre(nb_contrats_resultat)}</span>'
            f'<span class="vg-table-summary-label">{libelle_lignes}</span>'
            "</div>"
            f'<div class="vg-table-summary-mode">{mode_tableau}</div>'
            "</div>"
        )
        st.markdown(resume_html, unsafe_allow_html=True)

        if not colonnes_affichees:
            st.warning("Sélectionne au moins une colonne à afficher.")
        elif table_contrats_complete.empty:
            st.info("Aucun résultat ne correspond aux filtres et à la recherche.")
        else:
            TAILLE_PAGE = 500
            nb_pages = max(
                1,
                (nb_lignes_resultat + TAILLE_PAGE - 1) // TAILLE_PAGE,
            )

            cle_page = f"page_table_contrats_{cle_mode}"
            if cle_page not in st.session_state:
                st.session_state[cle_page] = 1

            st.session_state[cle_page] = max(
                1,
                min(int(st.session_state[cle_page]), nb_pages),
            )
            page_selectionnee = int(st.session_state[cle_page])

            pagination_gauche, pagination_centre, pagination_droite = st.columns(
                [1, 1.4, 1],
                vertical_alignment="center",
            )

            with pagination_gauche:
                if st.button(
                    "‹  Précédent",
                    key=f"page_precedente_{cle_mode}",
                    width="stretch",
                    disabled=page_selectionnee <= 1,
                ):
                    st.session_state[cle_page] = page_selectionnee - 1
                    st.rerun()

            with pagination_centre:
                st.markdown(
                    (
                        '<div class="vg-pagination-current">'
                        '<span class="vg-pagination-label">Page</span>'
                        f"<strong>{page_selectionnee}</strong>"
                        f'<span class="vg-pagination-total">sur {nb_pages}</span>'
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

            with pagination_droite:
                if st.button(
                    "Suivant  ›",
                    key=f"page_suivante_{cle_mode}",
                    width="stretch",
                    disabled=page_selectionnee >= nb_pages,
                ):
                    st.session_state[cle_page] = page_selectionnee + 1
                    st.rerun()

            debut = (page_selectionnee - 1) * TAILLE_PAGE
            fin = debut + TAILLE_PAGE

            table_page = (
                table_contrats_complete.iloc[debut:fin][colonnes_affichees].copy()
            )

            for colonne in table_page.columns:
                serie = table_page[colonne]
                if pd.api.types.is_datetime64_any_dtype(serie):
                    table_page[colonne] = (
                        pd.to_datetime(serie, errors="coerce")
                        .dt.strftime("%d/%m/%Y")
                        .fillna("")
                    )
                else:
                    table_page[colonne] = (
                        serie.where(serie.notna(), "").astype(str)
                    )

            st.caption(
                f"Page {page_selectionnee} sur {nb_pages} · lignes "
                f"{fmt_nombre(debut + 1)} à "
                f"{fmt_nombre(min(fin, nb_lignes_resultat))}"
            )

            st.dataframe(
                table_page,
                width="stretch",
                hide_index=True,
                height=430,
            )

            if mode_tableau == "Contrats uniques":
                nom_export = "contrats_uniques_complets.xlsx"
            elif mode_tableau == "Contrats et rattachements":
                nom_export = "contrats_rattachements_complets.xlsx"
            else:
                nom_export = "contrats_codes_prestation_complets.xlsx"

            cle_export = f"export_complet_{cle_mode}"
            if cle_export not in st.session_state:
                st.session_state[cle_export] = False

            if not st.session_state[cle_export]:
                if st.button(
                    "Préparer le téléchargement complet",
                    width="stretch",
                    key=f"preparer_export_{cle_mode}",
                ):
                    st.session_state[cle_export] = True
                    st.rerun()
            else:
                table_export_complete = table_contrats_complete[
                    colonnes_affichees
                ].copy()
                st.caption(
                    "Le fichier contient toutes les lignes filtrées : "
                    f"{format_nombre(len(table_export_complete))} ligne(s)."
                )
                dataframe_download(
                    "Télécharger toutes les lignes",
                    table_export_complete,
                    nom_export,
                )

                if st.button(
                    "Annuler la préparation",
                    width="stretch",
                    key=f"annuler_export_{cle_mode}",
                ):
                    st.session_state[cle_export] = False
                    st.rerun()


    st.markdown("<br>", unsafe_allow_html=True)

    afficher_evolution_contrats(
        df_contrats=df_contrats_source_kpi,
        df_prestations=df_prestations_kpi,
    )


# =====================================================
# VUE 2 — COUVERTURE
# =====================================================

elif vue_active == "Couverture":
    if statut_selectionne == "active":
        section(
            "Couverture du patrimoine",
            "Périmètre des contrats actifs et patrimoine associé.",
        )
    elif statut_selectionne == "inactive":
        section(
            "Couverture du patrimoine",
            "Périmètre des contrats inactifs et patrimoine associé.",
        )
    else:
        section(
            "Couverture du patrimoine",
            "La réalité présente dans Intent, puis la part réellement exploitable pour les analyses de couverture.",
        )

    # Même base de lecture que la Vue globale.
    if statut_selectionne is None and not perimetre_filtre_actif:
        contrats_value = global_value(df_global, "contrats_total")
        contrats_pill = (
            f"{fmt_nombre(global_value(df_global, 'contrats_rattaches_programme'))} exploitables"
        )
        contrats_help = (
            f"{fmt_nombre(global_value(df_global, 'contrats_non_rattaches_programme'))} "
            "non rattachés à un programme."
        )

        programmes_value = global_value(df_global, "programmes_total")
        programmes_couverts = int(serie_numerique(df_esi, "esi_couvert").sum())
        programmes_pill = f"{fmt_nombre(programmes_couverts)} couverts"
        programmes_help = "Programmes / ESI présents dans la source patrimoniale."

        logements_value = global_value(df_global, "logements_total")
        logements_pill = (
            f"{fmt_nombre(global_value(df_global, 'logements_rattaches_programme'))} exploitables"
        )
        logements_help = (
            f"{fmt_nombre(global_value(df_global, 'logements_sans_programme'))} sans programme."
        )

        equipements_value = global_value(df_global, "equipements_total")
        equipements_pill = (
            f"{fmt_nombre(global_value(df_global, 'equipements_rattaches_programme'))} exploitables"
        )
        equipements_help = (
            f"{fmt_nombre(global_value(df_global, 'equipements_sans_programme'))} sans programme."
        )

        contrats_label = "Contrats"
        programmes_label = "Programmes / ESI"
        logements_label = "Logements"
        equipements_label = "Équipements"

    elif statut_selectionne == "active":
        contrats_value = len(liste_refs_valides(df_contrats_kpi, "contract_reference"))
        programmes_value = len(liste_refs_valides(df_esi_context, "esi_reference"))
        logements_value = int(serie_numerique(df_esi_context, "nb_logements").sum())
        equipements_value = int(serie_numerique(df_esi_context, "nb_equipements").sum())

        contrats_label = "Contrats actifs"
        programmes_label = "ESI concernés"
        logements_label = "Logements rattachés"
        equipements_label = "Équipements rattachés"

        contrats_pill = contrats_help = ""
        programmes_pill = programmes_help = ""
        logements_pill = logements_help = ""
        equipements_pill = equipements_help = ""

    elif statut_selectionne == "inactive":
        contrats_value = len(liste_refs_valides(df_contrats_kpi, "contract_reference"))
        programmes_value = len(liste_refs_valides(df_esi_context, "esi_reference"))
        logements_value = int(serie_numerique(df_esi_context, "nb_logements").sum())
        equipements_value = int(serie_numerique(df_esi_context, "nb_equipements").sum())

        contrats_label = "Contrats inactifs"
        programmes_label = "ESI concernés"
        logements_label = "Logements rattachés"
        equipements_label = "Équipements rattachés"

        contrats_pill = contrats_help = ""
        programmes_pill = programmes_help = ""
        logements_pill = logements_help = ""
        equipements_pill = equipements_help = ""

    else:
        contrats_value = len(liste_refs_valides(df_contrats_kpi, "contract_reference"))
        contrats_pill = "Périmètre filtré"
        contrats_help = "Contrats exploitables correspondant aux filtres actifs."

        programmes_value = len(liste_refs_valides(df_esi_context, "esi_reference"))
        programmes_couverts = int(serie_numerique(df_esi_context, "esi_couvert").sum())
        programmes_pill = f"{fmt_nombre(programmes_couverts)} couverts"
        programmes_help = "Programmes / ESI correspondant aux filtres actifs."

        logements_value = int(serie_numerique(df_esi_context, "nb_logements").sum())
        logements_pill = "Rattachés aux ESI"
        logements_help = "Logements exploitables du périmètre filtré."

        equipements_value = int(serie_numerique(df_esi_context, "nb_equipements").sum())
        equipements_pill = "Rattachés aux ESI"
        equipements_help = "Équipements exploitables du périmètre filtré."

        contrats_label = "Contrats"
        programmes_label = "Programmes / ESI"
        logements_label = "Logements"
        equipements_label = "Équipements"

    cartes_compactes = statut_selectionne in {"active", "inactive"}

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card(
            contrats_label,
            contrats_value,
            contrats_pill,
            contrats_help,
            accent=C_NAVY,
            compact=cartes_compactes,
        )
    with c2:
        kpi_card(
            programmes_label,
            programmes_value,
            programmes_pill,
            programmes_help,
            accent=C_NAVY,
            compact=cartes_compactes,
        )
    with c3:
        kpi_card(
            logements_label,
            logements_value,
            logements_pill,
            logements_help,
            accent=C_PINK,
            compact=cartes_compactes,
        )
    with c4:
        kpi_card(
            equipements_label,
            equipements_value,
            equipements_pill,
            equipements_help,
            accent=C_VIOLET,
            compact=cartes_compactes,
        )

    if statut_selectionne is not None:
        statut_texte = "actifs" if statut_selectionne == "active" else "inactifs"
        info(
            f"Les contrats {statut_texte} sélectionnés sont rattachés à "
            f"{fmt_nombre(programmes_value)} ESI, représentant "
            f"{fmt_nombre(logements_value)} logements et "
            f"{fmt_nombre(equipements_value)} équipements. "
            "Seuls les contrats rattachés à un ESI sont inclus."
        )


    with st.expander(
        "Situation actuelle des ESI",
        expanded=True,
    ):
        # =====================================================
        # SITUATION ACTUELLE DES ESI
        # =====================================================

        st.markdown("<br>", unsafe_allow_html=True)
        section(
            "Situation actuelle des ESI",
            "Trois lectures complémentaires : présence des équipements, couverture réelle et répartition des contrats par ESI.",
        )

        df_esi_situation = dedupliquer_esi(df_esi_context)
        refs_esi_situation = liste_refs_valides(
            df_esi_situation,
            "esi_reference",
        )
        total_esi_situation = len(refs_esi_situation)

        def compter_indicateur(colonne: str) -> int:
            return int(
                (
                    serie_numerique(
                        df_esi_situation,
                        colonne,
                    ) > 0
                ).sum()
            )

        def taux_esi(nombre: int, denominateur: int | None = None) -> float:
            base = (
                total_esi_situation
                if denominateur is None
                else denominateur
            )
            return round(nombre / base * 100, 1) if base else 0.0

        nb_esi_avec_equipement = compter_indicateur(
            "esi_avec_equipement"
        )
        nb_esi_sans_equipement = compter_indicateur(
            "esi_sans_equipement"
        )

        if statut_selectionne == "active":
            colonne_avec_contrat_equipement = (
                "esi_avec_equipement_couvert_valide"
            )
            colonne_sans_contrat_equipement = (
                "esi_avec_equipement_sans_couverture_valide"
            )
            colonne_sans_contrat_programme = "esi_sans_contrat_valide"
            colonne_multi_metier = "esi_multi_meme_metier_valide"
            libelle_contrat_equipement = (
                "Avec contrat actif valide"
            )
            libelle_sans_contrat_equipement = (
                "Équipés sans couverture active"
            )
        else:
            colonne_avec_contrat_equipement = (
                "esi_avec_equipement_et_contrat"
            )
            colonne_sans_contrat_equipement = (
                "esi_avec_equipement_sans_contrat_equipement"
            )
            colonne_sans_contrat_programme = "esi_sans_aucun_contrat"
            colonne_multi_metier = "esi_multi_meme_metier"
            libelle_contrat_equipement = (
                "Avec contrat rattaché"
            )
            libelle_sans_contrat_equipement = (
                "Équipés sans contrat équipement"
            )

        nb_esi_avec_contrat_equipement = compter_indicateur(
            colonne_avec_contrat_equipement
        )
        nb_esi_sans_contrat_equipement = compter_indicateur(
            colonne_sans_contrat_equipement
        )
        # Présence d'au moins un contrat directement rattaché au programme.
        refs_esi_avec_contrat_programme = set(
            liste_refs_valides(
                df_contrats_kpi,
                "esi_reference",
            )
        )
        refs_esi_du_perimetre = set(refs_esi_situation)

        nb_esi_avec_contrat_programme = len(
            refs_esi_avec_contrat_programme
            & refs_esi_du_perimetre
        )
        nb_esi_sans_contrat_programme = max(
            total_esi_situation - nb_esi_avec_contrat_programme,
            0,
        )

        nb_esi_multi_metier = compter_indicateur(
            colonne_multi_metier
        )

        # Calcul fiable : un nombre de contrats DISTINCTS pour chaque ESI.
        # Les ESI sans contrat sont explicitement conservés avec la valeur 0.
        base_esi_contrats = pd.DataFrame(
            {"esi_reference": refs_esi_situation}
        )

        if (
            not df_contrats_kpi.empty
            and "esi_reference" in df_contrats_kpi.columns
            and "contract_reference" in df_contrats_kpi.columns
        ):
            contrats_distincts_par_esi = (
                df_contrats_kpi[
                    df_contrats_kpi["esi_reference"].notna()
                    & df_contrats_kpi["contract_reference"].notna()
                ]
                .groupby("esi_reference")["contract_reference"]
                .nunique()
                .rename("nb_contrats")
                .reset_index()
            )
        else:
            contrats_distincts_par_esi = pd.DataFrame(
                columns=["esi_reference", "nb_contrats"]
            )

        repartition_contrats_esi = base_esi_contrats.merge(
            contrats_distincts_par_esi,
            on="esi_reference",
            how="left",
        )
        repartition_contrats_esi["nb_contrats"] = (
            pd.to_numeric(
                repartition_contrats_esi["nb_contrats"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        moyenne_contrats_esi = (
            float(repartition_contrats_esi["nb_contrats"].mean())
            if not repartition_contrats_esi.empty
            else 0.0
        )
        mediane_contrats_esi = (
            float(repartition_contrats_esi["nb_contrats"].median())
            if not repartition_contrats_esi.empty
            else 0.0
        )

        repartition_contrats_esi["Tranche"] = pd.cut(
            repartition_contrats_esi["nb_contrats"],
            bins=[-1, 0, 1, 2, 3, float("inf")],
            labels=[
                "0 contrat",
                "1 contrat",
                "2 contrats",
                "3 contrats",
                "4 contrats ou plus",
            ],
        )

        distribution_contrats = (
            repartition_contrats_esi["Tranche"]
            .value_counts(sort=False)
            .rename_axis("Tranche")
            .reset_index(name="ESI")
        )
        distribution_contrats["Taux"] = distribution_contrats["ESI"].map(
            lambda nombre: taux_esi(int(nombre))
        )

        # =====================================================
        # VISUELS DE COUVERTURE
        # =====================================================

        ligne_haute_gauche, ligne_haute_droite = st.columns(
            2,
            gap="large",
        )

        with ligne_haute_gauche:
            st.markdown(
                '<div class="vg-mini-title">Présence des équipements</div>',
                unsafe_allow_html=True,
            )

            donnees_equipements = pd.DataFrame(
                {
                    "Situation": [
                        "Avec équipement",
                        "Sans équipement",
                    ],
                    "ESI": [
                        nb_esi_avec_equipement,
                        nb_esi_sans_equipement,
                    ],
                }
            )

            if go is None:
                st.bar_chart(
                    donnees_equipements.set_index("Situation")["ESI"],
                    width="stretch",
                )
            else:
                fig_equipements = go.Figure(
                    go.Pie(
                        labels=donnees_equipements["Situation"],
                        values=donnees_equipements["ESI"],
                        hole=0.64,
                        sort=False,
                        textinfo="percent",
                        textfont=dict(size=14),
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "ESI : %{value:,}<br>"
                            "Part : %{percent}<extra></extra>"
                        ),
                        marker=dict(
                            colors=["#173B69", "#63B9DF"],
                            line=dict(color="#FFFFFF", width=4),
                        ),
                    )
                )
                fig_equipements.add_annotation(
                    text=(
                        f"<b>{fmt_nombre(total_esi_situation)}</b>"
                        "<br><span style='font-size:12px'>ESI</span>"
                    ),
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(color=C_INK, size=22),
                )
                _layout_plotly(fig_equipements, 390)
                fig_equipements.update_layout(
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.12,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=12),
                    ),
                    margin=dict(l=12, r=12, t=16, b=60),
                )
                st.plotly_chart(
                    fig_equipements,
                    use_container_width=True,
                    config=config_plotly("presence_equipements_esi"),
                )

        with ligne_haute_droite:
            st.markdown(
                '<div class="vg-mini-title">Couverture réelle</div>',
                unsafe_allow_html=True,
            )

            donnees_couverture = pd.DataFrame(
                {
                    "Situation": [
                        "ESI équipés avec contrat équipement",
                        "ESI équipés sans contrat équipement",
                        "ESI avec au moins un contrat",
                        "ESI sans contrat",
                    ],
                    "ESI": [
                        nb_esi_avec_contrat_equipement,
                        nb_esi_sans_contrat_equipement,
                        nb_esi_avec_contrat_programme,
                        nb_esi_sans_contrat_programme,
                    ],
                    "Couleur": [
                        "#2F7C6D",
                        "#E89BC7",
                        "#173B69",
                        "#F4D84E",
                    ],
                }
            )
            donnees_couverture["Taux"] = donnees_couverture["ESI"].map(
                lambda nombre: taux_esi(int(nombre))
            )
            donnees_couverture = donnees_couverture.iloc[::-1].reset_index(
                drop=True
            )

            if go is None:
                st.bar_chart(
                    donnees_couverture.set_index("Situation")["Taux"],
                    width="stretch",
                )
            else:
                fig_couverture = go.Figure(
                    go.Bar(
                        x=donnees_couverture["Taux"],
                        y=donnees_couverture["Situation"],
                        orientation="h",
                        text=donnees_couverture["Taux"].map(
                            lambda valeur: fmt_pourcentage(valeur)
                        ),
                        textposition="outside",
                        textfont=dict(size=13),
                        customdata=donnees_couverture["ESI"],
                        marker=dict(
                            color=donnees_couverture["Couleur"],
                        ),
                        hovertemplate=(
                            "<b>%{y}</b><br>"
                            "ESI : %{customdata:,}<br>"
                            "Taux : %{x:.1f} %<extra></extra>"
                        ),
                    )
                )
                _layout_plotly(fig_couverture, 390)
                fig_couverture.update_layout(
                    xaxis=dict(
                        title=None,
                        ticksuffix=" %",
                        range=[0, 108],
                        gridcolor=C_GRID,
                        tickfont=dict(size=11),
                    ),
                    yaxis=dict(
                        title=None,
                        automargin=True,
                        tickfont=dict(size=12),
                    ),
                    margin=dict(l=18, r=70, t=16, b=45),
                    showlegend=False,
                    bargap=0.38,
                )
                st.plotly_chart(
                    fig_couverture,
                    use_container_width=True,
                    config=config_plotly("couverture_reelle_esi"),
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="vg-mini-title">Répartition des contrats par ESI</div>',
            unsafe_allow_html=True,
        )

        if go is None:
            st.bar_chart(
                distribution_contrats.set_index("Tranche")["ESI"],
                width="stretch",
            )
        else:
            fig_contrats = go.Figure(
                go.Bar(
                    x=distribution_contrats["Tranche"].astype(str),
                    y=distribution_contrats["ESI"],
                    text=distribution_contrats["Taux"].map(
                        lambda valeur: fmt_pourcentage(valeur)
                    ),
                    textposition="outside",
                    textfont=dict(size=13),
                    customdata=distribution_contrats["Taux"],
                    marker=dict(
                        color=[
                            "#E89BC7",
                            "#63B9DF",
                            "#F4D84E",
                            "#2F7C6D",
                            "#432ABD",
                        ],
                        line=dict(color="#FFFFFF", width=1.5),
                    ),
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "ESI : %{y:,}<br>"
                        "Part : %{customdata:.1f} %<extra></extra>"
                    ),
                )
            )
            _layout_plotly(fig_contrats, 410)
            fig_contrats.update_layout(
                xaxis=dict(
                    title=None,
                    tickangle=0,
                    automargin=True,
                    tickfont=dict(size=12),
                ),
                yaxis=dict(
                    title="Nombre d’ESI",
                    gridcolor=C_GRID,
                    tickfont=dict(size=11),
                ),
                margin=dict(l=55, r=25, t=18, b=55),
                showlegend=False,
                bargap=0.28,
            )
            st.plotly_chart(
                fig_contrats,
                use_container_width=True,
                config=config_plotly("distribution_contrats_par_esi"),
            )

        moyenne_texte = f"{moyenne_contrats_esi:.2f}".replace(".", ",")
        mediane_texte = f"{mediane_contrats_esi:.0f}".replace(".", ",")

        indicateur_1, indicateur_2, indicateur_3 = st.columns(
            [1, 1, 1.45],
            gap="large",
        )

        with indicateur_1:
            st.markdown(
                f"""
                <div class="vg-card vg-card-compact"
                     style="--accent:{C_TEAL};">
                    <div class="vg-card-accent"></div>
                    <div class="vg-card-label">Moyenne</div>
                    <div class="vg-card-value">{_safe(moyenne_texte)}</div>
                    <div class="vg-card-help">
                        Contrats distincts par ESI, en incluant les ESI à zéro.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with indicateur_2:
            st.markdown(
                f"""
                <div class="vg-card vg-card-compact"
                     style="--accent:{C_NAVY};">
                    <div class="vg-card-accent"></div>
                    <div class="vg-card-label">Médiane</div>
                    <div class="vg-card-value">{_safe(mediane_texte)}</div>
                    <div class="vg-card-help">
                        La moitié des ESI possède ce nombre de contrats ou moins.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with indicateur_3:
            st.markdown(
                f"""
                <div class="vg-card vg-card-compact"
                     style="--accent:{C_RED};">
                    <div class="vg-card-accent"></div>
                    <div class="vg-card-label">
                        Multi-contrats sur un même métier
                    </div>
                    <div class="vg-card-value">
                        {fmt_nombre(nb_esi_multi_metier)}
                    </div>
                    <div class="vg-card-pill">
                        {fmt_pourcentage(taux_esi(nb_esi_multi_metier))}
                    </div>
                    <div class="vg-card-help">
                        ESI ayant plusieurs contrats rattachés au même métier.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(
            "Calcul : les références de contrats sont dédupliquées pour chaque ESI. "
            "Les ESI sans contrat sont conservés avec la valeur zéro."
        )

        presence_metiers = construire_presence_metiers(
            df_contrats=df_contrats_kpi,
            total_esi=total_esi_situation,
            top_n=15,
        )

        repartition_types = construire_repartition_types_equipement(
            df_equipements=df_equipements_couverture_kpi,
            top_n=12,
        )

        couverture_equipements = construire_couverture_reelle_equipements(
            df_equipements=df_equipements_couverture_kpi,
            statut=statut_selectionne,
        )

    # =====================================================
    # ÉQUIPEMENTS DU PATRIMOINE
    # =====================================================

    with st.expander(
        "Équipements du patrimoine",
        expanded=True,
    ):
        section(
            "Équipements du patrimoine",
            "Répartition du parc et part des équipements disposant réellement d’un contrat directement rattaché dans Intent.",
        )

        repartition_types = construire_repartition_types_equipement(
            df_equipements=df_equipements_couverture_kpi,
            top_n=12,
        )
        couverture_equipements = construire_couverture_reelle_equipements(
            df_equipements=df_equipements_couverture_kpi,
            statut=statut_selectionne,
        )

        total_equipements_couverture = int(
            couverture_equipements["Équipements"].sum()
        ) if not couverture_equipements.empty else 0

        col_types, col_couverture = st.columns(
            [1.25, 0.85],
            gap="large",
        )

        with col_types:
            st.markdown(
                f"""
                <div class="vg-chart-intro">
                    <div class="vg-chart-question">
                        Quels types d’équipement trouve-t-on dans le patrimoine ?
                    </div>
                    <div class="vg-chart-base">
                        {fmt_nombre(total_equipements_couverture)} équipements
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if repartition_types.empty:
                st.info(
                    "Aucun type d’équipement disponible sur ce périmètre."
                )
            elif go is None:
                st.bar_chart(
                    repartition_types.set_index(
                        "Type d’équipement"
                    )["Équipements"],
                    width="stretch",
                )
            else:
                couleurs_types_3f = [
                    "#173B69",
                    "#63B9DF",
                    "#2F7C6D",
                    "#E89BC7",
                    "#432ABD",
                    "#F4D84E",
                    "#8CC8BC",
                    "#7B9BC3",
                    "#D83B55",
                    "#B8DFF1",
                    "#A99BE8",
                    "#D8C95B",
                ]

                fig_types = go.Figure(
                    go.Bar(
                        x=repartition_types["Équipements"],
                        y=repartition_types["Type d’équipement"],
                        orientation="h",
                        text=[
                            f"{fmt_nombre(nb)} · {fmt_pourcentage(part)}"
                            for nb, part in zip(
                                repartition_types["Équipements"],
                                repartition_types["Part du parc"],
                            )
                        ],
                        textposition="outside",
                        cliponaxis=False,
                        customdata=repartition_types[
                            ["ESI", "Part du parc"]
                        ].to_numpy(),
                        marker=dict(
                            color=[
                                couleurs_types_3f[
                                    index % len(couleurs_types_3f)
                                ]
                                for index in range(
                                    len(repartition_types)
                                )
                            ],
                            line=dict(
                                color="#FFFFFF",
                                width=1.5,
                            ),
                        ),
                        hovertemplate=(
                            "<b>%{y}</b><br>"
                            "Équipements : %{x:,}<br>"
                            "ESI concernés : %{customdata[0]:,}<br>"
                            "Part du parc : %{customdata[1]:.1f} %"
                            "<extra></extra>"
                        ),
                    )
                )
                hauteur_types = max(
                    370,
                    min(
                        570,
                        39 * len(repartition_types) + 100,
                    ),
                )
                _layout_plotly(fig_types, hauteur_types)
                fig_types.update_layout(
                    xaxis=dict(
                        title="Nombre d’équipements",
                        gridcolor=C_GRID,
                        rangemode="tozero",
                    ),
                    yaxis=dict(
                        title=None,
                        automargin=True,
                    ),
                    margin=dict(
                        l=18,
                        r=115,
                        t=8,
                        b=48,
                    ),
                    bargap=0.34,
                    showlegend=False,
                )
                st.plotly_chart(
                    fig_types,
                    use_container_width=True,
                    config=config_plotly(
                        "repartition_types_equipement"
                    ),
                )

        with col_couverture:
            st.markdown(
                f"""
                <div class="vg-chart-intro">
                    <div class="vg-chart-question">
                        Quelle part des équipements possède un contrat ?
                    </div>
                    <div class="vg-chart-base">
                        {fmt_nombre(total_equipements_couverture)} équipements
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if couverture_equipements.empty:
                st.info(
                    "Aucune donnée de couverture équipement disponible."
                )
            elif go is None:
                st.bar_chart(
                    couverture_equipements.set_index(
                        "Couverture"
                    )["Équipements"],
                    width="stretch",
                )
            else:
                couleurs_couverture = {
                    "Équipements avec contrat": "#2F7C6D",
                    "Équipements sans contrat": "#F4D84E",
                }

                couverture_indexee = (
                    couverture_equipements
                    .set_index("Couverture")
                    .reindex(
                        [
                            "Équipements avec contrat",
                            "Équipements sans contrat",
                        ],
                        fill_value=0,
                    )
                )

                nb_avec_contrat = int(
                    couverture_indexee.loc[
                        "Équipements avec contrat",
                        "Équipements",
                    ]
                )
                nb_sans_contrat = int(
                    couverture_indexee.loc[
                        "Équipements sans contrat",
                        "Équipements",
                    ]
                )
                taux_avec_contrat = float(
                    couverture_indexee.loc[
                        "Équipements avec contrat",
                        "Taux",
                    ]
                )
                taux_sans_contrat = float(
                    couverture_indexee.loc[
                        "Équipements sans contrat",
                        "Taux",
                    ]
                )

                fig_couverture = go.Figure()

                fig_couverture.add_trace(
                    go.Bar(
                        y=["Parc d’équipements"],
                        x=[taux_avec_contrat],
                        name="Avec contrat",
                        orientation="h",
                        marker=dict(
                            color=couleurs_couverture[
                                "Équipements avec contrat"
                            ],
                            line=dict(
                                color="#FFFFFF",
                                width=2,
                            ),
                        ),
                        text=[
                            (
                                f"<b>{fmt_pourcentage(taux_avec_contrat)}</b>"
                                f"<br>{fmt_nombre(nb_avec_contrat)} équipements"
                            )
                        ],
                        textposition="inside",
                        insidetextanchor="middle",
                        textfont=dict(
                            size=14,
                            color="#FFFFFF",
                        ),
                        customdata=[[nb_avec_contrat]],
                        hovertemplate=(
                            "<b>Équipements avec contrat</b><br>"
                            "Équipements : %{customdata[0]:,}<br>"
                            "Part du parc : %{x:.1f} %"
                            "<extra></extra>"
                        ),
                    )
                )

                fig_couverture.add_trace(
                    go.Bar(
                        y=["Parc d’équipements"],
                        x=[taux_sans_contrat],
                        name="Sans contrat",
                        orientation="h",
                        marker=dict(
                            color=couleurs_couverture[
                                "Équipements sans contrat"
                            ],
                            line=dict(
                                color="#FFFFFF",
                                width=2,
                            ),
                        ),
                        text=[
                            (
                                f"<b>{fmt_pourcentage(taux_sans_contrat)}</b>"
                                f"<br>{fmt_nombre(nb_sans_contrat)}"
                            )
                        ],
                        textposition=(
                            "inside"
                            if taux_sans_contrat >= 12
                            else "outside"
                        ),
                        insidetextanchor="middle",
                        textfont=dict(
                            size=13,
                            color=(
                                "#173B69"
                                if taux_sans_contrat >= 12
                                else C_INK
                            ),
                        ),
                        customdata=[[nb_sans_contrat]],
                        hovertemplate=(
                            "<b>Équipements sans contrat</b><br>"
                            "Équipements : %{customdata[0]:,}<br>"
                            "Part du parc : %{x:.1f} %"
                            "<extra></extra>"
                        ),
                        cliponaxis=False,
                    )
                )

                _layout_plotly(fig_couverture, 245)
                fig_couverture.update_layout(
                    barmode="stack",
                    barnorm=None,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.18,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11),
                        itemclick=False,
                        itemdoubleclick=False,
                    ),
                    xaxis=dict(
                        range=[0, 100],
                        ticksuffix=" %",
                        tickvals=[0, 25, 50, 75, 100],
                        title=None,
                        gridcolor=C_GRID,
                        fixedrange=True,
                    ),
                    yaxis=dict(
                        title=None,
                        showticklabels=False,
                        fixedrange=True,
                    ),
                    margin=dict(
                        l=12,
                        r=55,
                        t=30,
                        b=72,
                    ),
                    bargap=0.55,
                    uniformtext=dict(
                        minsize=10,
                        mode="hide",
                    ),
                )

                st.plotly_chart(
                    fig_couverture,
                    use_container_width=True,
                    config=config_plotly(
                        "part_equipements_avec_contrat"
                    ),
                )

                resume_avec, resume_sans = st.columns(2)

                with resume_avec:
                    st.markdown(
                        f"""
                        <div class="vg-info" style="
                            margin:0;
                            border-left:4px solid {couleurs_couverture["Équipements avec contrat"]};
                            background:#F3FAF7;
                        ">
                            <strong>{fmt_nombre(nb_avec_contrat)}</strong>
                            équipements avec contrat
                            · <strong>{fmt_pourcentage(taux_avec_contrat)}</strong>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with resume_sans:
                    st.markdown(
                        f"""
                        <div class="vg-info" style="
                            margin:0;
                            border-left:4px solid {couleurs_couverture["Équipements sans contrat"]};
                            background:#FFFBEA;
                        ">
                            <strong>{fmt_nombre(nb_sans_contrat)}</strong>
                            équipements sans contrat
                            · <strong>{fmt_pourcentage(taux_sans_contrat)}</strong>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


            definition_couverture = (
                "un contrat actif valide"
                if statut_selectionne == "active"
                else "un contrat inactif"
                if statut_selectionne == "inactive"
                else "au moins un contrat actif ou inactif"
            )
            st.caption(
                "Un équipement est compté comme couvert lorsqu’il possède "
                f"{definition_couverture} directement rattaché dans Intent."
            )

        export_types, export_couverture = st.columns(2)

        with export_types:
            dataframe_download(
                "Télécharger la répartition des équipements",
                repartition_types,
                "repartition_types_equipement.xlsx",
                cle="export_repartition_types_equipement",
            )

        with export_couverture:
            dataframe_download(
                "Télécharger la synthèse de couverture",
                couverture_equipements,
                "couverture_equipements.xlsx",
                cle="export_couverture_equipements",
            )

        afficher_detail_equipements = st.toggle(
            "Afficher le détail des équipements",
            value=False,
            key="afficher_detail_equipements",
        )

        if afficher_detail_equipements:
            detail_equipements = (
                df_equipements_couverture_kpi.copy()
            )

            colonne_type_detail = next(
                (
                    candidate
                    for candidate in [
                        "equipment_type",
                        "equipment_asset_type",
                    ]
                    if candidate in detail_equipements.columns
                ),
                None,
            )

            if colonne_type_detail is not None:
                types_disponibles = (
                    detail_equipements[colonne_type_detail]
                    .fillna("Non renseigné")
                    .astype(str)
                    .str.strip()
                    .replace("", "Non renseigné")
                    .sort_values()
                    .unique()
                    .tolist()
                )
            else:
                types_disponibles = []

            filtre_type, filtre_couverture = st.columns(2)

            with filtre_type:
                type_selectionne = st.selectbox(
                    "Type d’équipement",
                    ["Tous les types"] + types_disponibles,
                    key="detail_type_equipement",
                )

            with filtre_couverture:
                couverture_selectionnee = st.selectbox(
                    "Couverture",
                    [
                        "Tous les équipements",
                        "Avec contrat",
                        "Sans contrat",
                    ],
                    key="detail_couverture_equipement",
                )

            if (
                type_selectionne != "Tous les types"
                and colonne_type_detail is not None
            ):
                detail_equipements = detail_equipements[
                    detail_equipements[colonne_type_detail]
                    .fillna("Non renseigné")
                    .astype(str)
                    .str.strip()
                    == type_selectionne
                ].copy()

            if statut_selectionne == "active":
                indicateur_detail = (
                    serie_numerique(
                        detail_equipements,
                        "equipment_covered_valid",
                    ) > 0
                )
            elif statut_selectionne == "inactive":
                indicateur_detail = (
                    serie_numerique(
                        detail_equipements,
                        "nb_contrats_inactifs",
                    ) > 0
                )
            else:
                indicateur_detail = (
                    serie_numerique(
                        detail_equipements,
                        "equipment_has_contract_link",
                    ) > 0
                )

            detail_equipements["_avec_contrat"] = (
                indicateur_detail.astype(int)
            )

            if couverture_selectionnee == "Avec contrat":
                detail_equipements = detail_equipements[
                    detail_equipements["_avec_contrat"] > 0
                ].copy()
            elif couverture_selectionnee == "Sans contrat":
                detail_equipements = detail_equipements[
                    detail_equipements["_avec_contrat"] == 0
                ].copy()

            if "equipment_reference" in detail_equipements.columns:
                detail_equipements = (
                    detail_equipements.drop_duplicates(
                        "equipment_reference"
                    )
                )

            detail_equipements["Couverture"] = (
                detail_equipements["_avec_contrat"]
                .map(
                    {
                        1: "Avec contrat",
                        0: "Sans contrat",
                    }
                )
            )

            colonnes_detail = {
                "societe": "Société",
                "agence": "Agence",
                "groupe": "Groupe",
                "secteur": "Secteur",
                "esi_reference": "Référence ESI",
                "esi_label": "Libellé ESI",
                "equipment_reference": "Référence équipement",
                "equipment_label": "Libellé équipement",
                "equipment_type": "Type d’équipement",
                "equipment_asset_type": "Famille d’équipement",
                "Couverture": "Couverture",
                "nb_contrats_total": "Contrats rattachés",
                "nb_contrats_actifs_valides": "Contrats actifs valides",
                "nb_contrats_inactifs": "Contrats inactifs",
            }

            colonnes_disponibles = [
                colonne
                for colonne in colonnes_detail
                if colonne in detail_equipements.columns
            ]
            table_detail_equipements = (
                detail_equipements[colonnes_disponibles]
                .rename(columns=colonnes_detail)
                .copy()
            )

            st.caption(
                f"{fmt_nombre(len(table_detail_equipements))} "
                "équipement(s) affiché(s)."
            )
            st.dataframe(
                table_detail_equipements,
                width="stretch",
                hide_index=True,
                height=430,
            )
            dataframe_download(
                "Télécharger le détail en Excel",
                table_detail_equipements,
                "detail_equipements.xlsx",
                cle="export_detail_equipements",
            )



    with st.expander(
        "Contrats par métier",
        expanded=False,
    ):
        # =====================================================
        # MÉTIERS ET ÉQUIPEMENTS
        # =====================================================

        section(
            "Contrats par métier",
            "Pour chaque métier, on compte les ESI qui possèdent au moins un contrat de ce métier.",
        )

        # -----------------------------------------------------
        # 1. PRÉSENCE DES CONTRATS PAR MÉTIER — PLEINE LARGEUR
        # -----------------------------------------------------
        st.markdown(
            '<div class="vg-mini-title">ESI concernés par métier</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Base analysée : {fmt_nombre(total_esi_situation)} ESI. "
            "Un ESI peut être compté dans plusieurs métiers."
        )

        if presence_metiers.empty:
            st.info("Aucune donnée métier disponible sur le périmètre sélectionné.")
        elif go is None:
            st.bar_chart(
                presence_metiers.set_index("Métier")["Taux"],
                width="stretch",
            )
        else:
            fig_metiers = go.Figure(
                go.Bar(
                    x=presence_metiers["ESI"],
                    y=presence_metiers["Métier"],
                    orientation="h",
                    text=[
                        (
                            f"{fmt_nombre(nb)} ESI · "
                            f"{fmt_pourcentage(taux)}"
                        )
                        for nb, taux in zip(
                            presence_metiers["ESI"],
                            presence_metiers["Taux"],
                        )
                    ],
                    textposition="outside",
                    cliponaxis=False,
                    customdata=presence_metiers["Taux"],
                    marker=dict(
                        color=presence_metiers["Taux"],
                        colorscale=[
                            [0.0, "#FFE8F2"],
                            [0.35, "#FFB7D1"],
                            [0.68, "#E66AA2"],
                            [1.0, "#A83A73"],
                        ],
                        showscale=False,
                        line=dict(color="#FFFFFF", width=1),
                    ),
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "ESI concernés : %{x:,}<br>"
                        "Part du périmètre : %{customdata:.1f} %"
                        "<extra></extra>"
                    ),
                )
            )
            hauteur_metiers = max(
                390,
                min(620, 35 * len(presence_metiers) + 95),
            )
            _layout_plotly(fig_metiers, hauteur_metiers)
            fig_metiers.update_layout(
                xaxis=dict(
                    title="Nombre d’ESI ayant ce métier",
                    range=[
                        0,
                        max(
                            int(total_esi_situation),
                            int(presence_metiers["ESI"].max()) + 500,
                        ),
                    ],
                    gridcolor=C_GRID,
                    tickfont=dict(size=11),
                    separatethousands=True,
                ),
                yaxis=dict(
                    title=None,
                    automargin=True,
                    tickfont=dict(size=12),
                ),
                margin=dict(l=24, r=135, t=12, b=50),
                bargap=0.34,
                showlegend=False,
            )
            st.plotly_chart(
                fig_metiers,
                use_container_width=True,
                config=config_plotly("presence_contrats_par_metier"),
            )

        st.caption(
            "Lecture : chaque barre répond à la question « sur combien d’ESI ce métier est-il présent ? ». "
            "Le pourcentage indique la part correspondante dans le périmètre."
        )


        afficher_detail_metier = st.toggle(
            "Afficher le détail d’un métier",
            value=False,
            key="afficher_detail_metier",
        )

        if afficher_detail_metier:
            liste_metiers = (
                presence_metiers["Métier"].astype(str).tolist()
                if not presence_metiers.empty
                else []
            )
            metier_selectionne = st.selectbox(
                "Métier",
                liste_metiers,
                key="coverage_drilldown_metier",
            ) if liste_metiers else None

            if metier_selectionne:
                detail_metier = df_contrats_kpi[
                    df_contrats_kpi["contract_topic"]
                    .fillna("Non renseigné")
                    .astype(str)
                    .str.strip()
                    == metier_selectionne
                ].copy()

                detail_metier = detail_metier.drop_duplicates(
                    ["esi_reference", "contract_reference"]
                )

                colonnes_metier = {
                    "societe": "Société",
                    "agence": "Agence",
                    "groupe": "Groupe",
                    "secteur": "Secteur",
                    "esi_reference": "Référence ESI",
                    "esi_label": "Libellé ESI",
                    "contract_reference": "Référence contrat",
                    "contract_label": "Libellé contrat",
                    "contract_status": "Statut",
                    "third_party_label": "Prestataire",
                }
                disponibles_metier = [
                    colonne for colonne in colonnes_metier
                    if colonne in detail_metier.columns
                ]
                table_detail_metier = (
                    detail_metier[disponibles_metier]
                    .rename(columns=colonnes_metier)
                    .copy()
                )

                st.markdown(
                    f"""
                    <div class="vg-drilldown-summary">
                        <span class="vg-drilldown-pill">
                            {fmt_nombre(detail_metier["esi_reference"].nunique())} ESI
                        </span>
                        <span class="vg-drilldown-pill">
                            {fmt_nombre(detail_metier["contract_reference"].nunique())} contrats
                        </span>
                        <span class="vg-drilldown-pill">
                            {_safe(metier_selectionne)}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.dataframe(
                    table_detail_metier,
                    width="stretch",
                    hide_index=True,
                    height=420,
                )
                dataframe_download(
                    "Télécharger le détail en Excel",
                    table_detail_metier,
                    "detail_metier.xlsx",
                    cle="export_detail_metier",
                )


# =====================================================
# VUE 3 — QUALITÉ ET ANOMALIES
# =====================================================

else:
    section(
        "Qualité et anomalies",
        "Les données non exploitables ou incohérentes sont rendues visibles pour être corrigées, pas masquées.",
    )

    expired_detail = contrats_actifs_fin_depassee(df_contrats_kpi)
    expired_value = (
        int(global_value(df_global, "contrats_actifs_fin_depassee", 0))
        if not perimetre_filtre_actif
        else expired_detail["contract_reference"].nunique()
    )
    unlinked_contracts = int(
        global_value(df_global, "contrats_non_rattaches_programme", 0)
    )
    housing_without_program = int(
        global_value(df_global, "logements_sans_programme", 0)
    )
    multi_meme_metier = int(
        serie_numerique(df_esi_context, "esi_multi_meme_metier").sum()
    )

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        alert_card(
            "Contrats actifs expirés",
            expired_value,
            "Statut actif malgré une date de fin dépassée.",
        )
    with q2:
        alert_card(
            "Contrats non rattachés",
            unlinked_contracts,
            "Présents en source mais hors couverture programme.",
        )
    with q3:
        alert_card(
            "Logements sans programme",
            housing_without_program,
            "Existants mais non exploitables pour la couverture ESI.",
        )
    with q4:
        alert_card(
            "ESI multi même métier",
            multi_meme_metier,
            "Plusieurs contrats actifs sur un même métier.",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "Choisir une anomalie",
        "Un seul détail est affiché à la fois pour garder une lecture claire.",
    )

    if "vg_detail_focus" not in st.session_state:
        st.session_state["vg_detail_focus"] = "expired"

    b1, b2, b3, b4, b5 = st.columns(5)
    with b1:
        if st.button("Contrats expirés", width="stretch", key="quality_expired"):
            st.session_state["vg_detail_focus"] = "expired"
    with b2:
        if st.button("Non rattachés", width="stretch", key="quality_unlinked"):
            st.session_state["vg_detail_focus"] = "unlinked_contracts"
    with b3:
        if st.button(
            "Logements sans programme",
            width="stretch",
            key="quality_housing",
        ):
            st.session_state["vg_detail_focus"] = "housing"
    with b4:
        if st.button("Multi même métier", width="stretch", key="quality_multi"):
            st.session_state["vg_detail_focus"] = "multi_topic"
    with b5:
        if st.button("ESI sans contrat", width="stretch", key="quality_no_contract"):
            st.session_state["vg_detail_focus"] = "no_contract"

    afficher_detail_qualite(
        st.session_state["vg_detail_focus"],
        df_contrats_kpi=df_contrats_kpi,
        df_esi_context=df_esi_context,
        df_qualite=df_qualite,
        df_global=df_global,
    )

    with st.expander("Vue consolidée de toutes les anomalies", expanded=False):
        col_quality_graph, col_quality_table = st.columns([1, 1.15])

        with col_quality_graph:
            st.markdown(
                '<div class="vg-mini-title">Anomalies principales</div>',
                unsafe_allow_html=True,
            )
            df_q_graph = construire_graph_qualite(df_qualite_resume, df_qualite)
            afficher_barres_horizontales(
                df_q_graph,
                "Anomalie",
                "Objets distincts",
                color=C_VIOLET,
                height_base=320,
            )

        with col_quality_table:
            st.markdown(
                '<div class="vg-mini-title">Résumé qualité</div>',
                unsafe_allow_html=True,
            )
            if df_qualite_resume.empty:
                st.info("Aucun résumé qualité disponible.")
            else:
                resume = df_qualite_resume.copy()

                # Compatibilité avec l'ancienne et la nouvelle vue résumé.
                rename_count = {}
                if "nombre_objets_distincts" in resume.columns:
                    rename_count["nombre_objets_distincts"] = "Objets distincts"
                elif "nb_objets_distincts" in resume.columns:
                    rename_count["nb_objets_distincts"] = "Objets distincts"

                if "nombre_occurrences" in resume.columns:
                    rename_count["nombre_occurrences"] = "Lignes détail"
                elif "nb_lignes_detail" in resume.columns:
                    rename_count["nb_lignes_detail"] = "Lignes détail"

                cols = [
                    col
                    for col in [
                        "anomalie_type",
                        "objet_type",
                        "gravite",
                        "nombre_objets_distincts",
                        "nb_objets_distincts",
                        "nombre_occurrences",
                        "nb_lignes_detail",
                    ]
                    if col in resume.columns
                ]
                resume = resume[cols].rename(
                    columns={
                        "anomalie_type": "Type anomalie",
                        "objet_type": "Type objet",
                        "gravite": "Gravité",
                        **rename_count,
                    }
                )
                if "Objets distincts" in resume.columns:
                    resume = resume.sort_values("Objets distincts", ascending=False)

                st.dataframe(
                    resume,
                    width="stretch",
                    hide_index=True,
                    height=320,
                )

        recherche_anomalie = st.text_input(
            "Rechercher dans toutes les anomalies",
            placeholder="Référence, type, description, société, agence...",
            key="quality_search_all",
        )
        table_qualite = filtrer_table_recherche(
            preparer_qualite_table(df_qualite),
            recherche_anomalie,
        )
        st.dataframe(
            table_qualite,
            width="stretch",
            hide_index=True,
            height=460,
        )
        dataframe_download(
            "Télécharger les anomalies",
            table_qualite,
            "anomalies_patrimoine.xlsx",
        )


# =====================================================
# FOOTER TECHNIQUE
# =====================================================

if "date_maj" in df_global.columns:
    date_maj = global_value(df_global, "date_maj", "")
    st.caption(f"Dernière mise à jour des tables dashboard : {date_maj}")
