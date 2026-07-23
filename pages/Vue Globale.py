import html
import re
import unicodedata
from io import BytesIO
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
SOURCE_PRESTATIONS = "dashboard.contrats_prestations"
SOURCE_EQUIPEMENTS_COUVERTURE = "dashboard.equipements_couverture"
SOURCE_EQUIPEMENTS_CONTRATS = "dashboard.equipements_contrats"
SOURCE_GLOBAL = "dashboard.kpi_globale"
SOURCE_CREATIONS = "dashboard.kpi_creation_detail"
SOURCE_QUALITE = "dashboard.qualite_donnees"
SOURCE_QUALITE_RESUME = "dashboard.qualite_donnees_resume"
SOURCE_ALERTES = "dashboard.alertes_couverture"
CACHE_TTL = 3600
SQL_TIMEOUT_MS = 20000


# =====================================================
# PALETTE 3F
# =====================================================

C_RED = "#E5114D"
C_NAVY = "#173B69"
C_VIOLET = "#432ABD"
C_YELLOW = "#FFDC55"
C_TEAL = "#008080"
C_BLUE = "#0074FF"
C_BLUE_LIGHT = "#80CDFF"
C_PINK = "#FFB7E3"

C_RED_DARK = "#BF0F40"
C_NAVY_DEEP = "#102A4C"
C_PINK_SOFT = "#FFF3FA"
C_BLUE_SOFT = "#EFF9FF"
C_CANVAS = "#F7FAFD"
C_GRID = "#E8EEF5"
C_INK = "#17243A"


PALETTE_3F_GRAPHIQUES = [
    "#173B69",  # bleu marine
    "#63B9DF",  # bleu ciel
    "#2F7C6D",  # vert profond
    "#432ABD",  # violet
    "#E89BC7",  # rose poudré
    "#F4D84E",  # jaune
    "#D83B55",  # rouge framboise
    "#4C6FB1",  # bleu moyen
]


# =====================================================
# PAGE + STYLE
# =====================================================

setup_page("Vue Globale", None)
apply_3f_page_style()


def _safe(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def format_nombre(value) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def effacer_recherche_contrat():
    st.session_state["global_search_contract"] = ""


def effacer_recherche_equipement():
    """Vide uniquement la recherche du tableau des équipements."""
    st.session_state["recherche_detail_equipement"] = ""


def ouvrir_onglet_alertes():
    st.session_state["dashboard_vue_active"] = "Alertes"

def inject_style():
    st.markdown(
        r"""
        <style>
        :root {
            --3f-red: #E5114D;
            --3f-red-dark: #BF0F40;
            --3f-pink-soft: #FFF1F6;
            --3f-blue-light: #80CDFF;
            --navy: #173B69;
            --navy-deep: #102A4C;
            --text-main: #1B2430;
            --text-soft: #667085;
            --text-muted: #8A94A6;
            --surface: #FFFFFF;
            --canvas: #FAFAFB;
            --border: #E7E3E8;
            --line-soft: #EEE7EB;
        }

        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .stApp {
            background: var(--canvas) !important;
        }

        .block-container {
            max-width: 1520px !important;
            padding-top: 1.15rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }

        hr {
            border: none !important;
            border-top: 1px solid #E9EEF3 !important;
            margin: 22px 0 !important;
        }

        /* HERO */
        .vg-hero {
            position: relative;
            overflow: hidden;
            padding: 28px 34px !important;
            margin: 50px 0 14px 0 !important;
            background: var(--3f-pink-soft) !important;
            border: 1px solid #E8D8E1 !important;
            border-radius: 20px !important;
            box-shadow: 0 10px 26px -22px rgba(27, 36, 48, 0.24) !important;
        }

        .vg-hero::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            height: 5px;
            background: var(--3f-red) !important;
        }

        .vg-hero::after {
            content: "";
            position: absolute;
            width: 135px;
            height: 135px;
            right: -70px;
            bottom: -75px;
            border-radius: 50%;
            background: rgba(128, 205, 255, 0.18);
        }

        .vg-hero-eyebrow {
            position: relative;
            z-index: 1;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            color: #A33A61;
            font-size: 11.5px;
            font-weight: 700;
            letter-spacing: 1.4px;
            text-transform: uppercase;
            margin-bottom: 11px;
        }

        .vg-hero-eyebrow::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--3f-red);
        }

        .vg-hero-title {
            position: relative;
            z-index: 1;
            color: var(--text-main);
            font-size: 34px;
            line-height: 1.08;
            letter-spacing: -0.6px;
            font-weight: 800;
            margin-bottom: 8px;
        }

        .vg-hero-subtitle {
            position: relative;
            z-index: 1;
            color: var(--text-soft);
            font-size: 14.5px;
            line-height: 1.55;
            font-weight: 500;
            max-width: 940px;
        }

        /* SECTIONS */
        .vg-section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text-main);
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.3px;
            margin: 2px 0 3px 0;
        }

        .vg-section-title::before {
            content: "";
            width: 5px;
            height: 21px;
            border-radius: 99px;
            background: var(--3f-red);
        }

        .vg-section-subtitle {
            color: var(--text-soft);
            font-size: 13px;
            font-weight: 500;
            line-height: 1.5;
            margin-bottom: 14px;
            max-width: 920px;
        }

        .vg-mini-title,
        .vg-column-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 700;
            margin: 2px 0 10px 0;
        }

        .vg-info {
            padding: 12px 16px;
            border-radius: 12px;
            background: #FFF7FA;
            border: 1px solid #EEDCE5;
            color: var(--text-soft);
            font-size: 12.5px;
            font-weight: 500;
            line-height: 1.5;
            margin: 8px 0 16px 0;
        }

        /* CARTES */
        .vg-card {
            height: 190px;
            min-height: 190px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
            padding: 18px 19px 17px 19px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.22);
            transition: border-color .15s ease, box-shadow .15s ease;
        }

        .vg-card:hover {
            border-color: #DCCED5;
            box-shadow: 0 10px 24px -18px rgba(27, 36, 48, 0.28);
        }

        .vg-card-accent {
            width: 32px;
            height: 4px;
            border-radius: 99px;
            background: var(--accent, #173B69);
            margin-bottom: 15px;
        }

        .vg-card-label {
            color: var(--text-muted);
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 10px;
        }

        .vg-card-value {
            color: var(--text-main);
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -1px;
            line-height: 1;
            margin-bottom: 12px;
        }

        .vg-card-pill {
            display: inline-flex;
            width: fit-content;
            align-items: center;
            padding: 4px 10px;
            border-radius: 99px;
            background: color-mix(in srgb, var(--accent, #173B69) 11%, transparent);
            color: var(--accent, #173B69);
            font-size: 11.5px;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .vg-equipment-type-value {
            text-align: right;
            white-space: nowrap;
        }

        .vg-equipment-type-rate {
            color: var(--text-main);
            font-size: 12px;
            font-weight: 850;
            line-height: 1.2;
        }

        .vg-equipment-type-detail {
            margin-top: 3px;
            color: var(--text-muted);
            font-size: 10px;
            font-weight: 650;
            line-height: 1.2;
        }
        .vg-card-help {
            color: var(--text-muted);
            font-size: 11.5px;
            font-weight: 500;
            line-height: 1.45;
            margin-top: auto;
        }

        .vg-card.vg-card-compact {
            height: 158px;
            min-height: 158px;
            justify-content: flex-start;
        }

        .vg-card.vg-card-compact .vg-card-value {
            margin-bottom: 0;
        }

        .vg-alert-card {
            height: 148px;
            min-height: 148px;
            box-sizing: border-box;
            padding: 16px 18px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 4px solid var(--3f-red);
            border-radius: 14px;
            box-shadow: 0 7px 18px -17px rgba(27, 36, 48, 0.22);
        }

        .vg-alert-title {
            color: var(--text-soft);
            font-size: 10.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 9px;
        }

        .vg-alert-value {
            color: var(--text-main);
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
            line-height: 1;
            margin-bottom: 8px;
        }

        .vg-alert-help {
            color: var(--text-muted);
            font-size: 11.5px;
            font-weight: 500;
            line-height: 1.4;
        }

        /* TABLES / GRAPHIQUES */
        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {
            width: 100% !important;
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.22) !important;
        }

        div[data-testid="stPlotlyChart"] {
            overflow: visible !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        div[data-testid="stPlotlyChart"] > div,
        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container {
            width: 100% !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }

        div[data-testid="stDataFrame"] {
            overflow: hidden !important;
        }

        div[data-testid="stDataFrame"] [role="columnheader"] {
            background: #F3F6F9 !important;
            color: var(--navy) !important;
            font-weight: 700 !important;
        }

        /* ALIGNEMENT DES DEUX GRAPHIQUES DE LA VUE GLOBALE */
        div[data-testid="stHorizontalBlock"]:has(.st-key-global_graph_status) {
            align-items: stretch !important;
        }

        .st-key-global_graph_status,
        .st-key-global_graph_metier {
            height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
        }

        .st-key-global_graph_status > div,
        .st-key-global_graph_metier > div {
            width: 100% !important;
        }

        .st-key-global_graph_status div[data-testid="stPlotlyChart"],
        .st-key-global_graph_metier div[data-testid="stPlotlyChart"] {
            flex: 1 1 auto !important;
            width: 100% !important;
        }

        /* BOUTONS */
        .stButton button {
            min-height: 44px !important;
            color: #9D174D !important;
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            font-weight: 650 !important;
        }

        .stButton button:hover {
            color: var(--3f-red) !important;
            background: #FFF7FA !important;
            border-color: #E7C8D6 !important;
            transform: none !important;
        }

        .stDownloadButton button {
            border-radius: 10px !important;
            font-weight: 650 !important;
            border: 1px solid var(--3f-red) !important;
            background: var(--3f-red) !important;
            color: #FFFFFF !important;
        }

        .stDownloadButton button:hover {
            background: var(--3f-red-dark) !important;
        }

        /* ONGLETS PRINCIPAUX */
        .st-key-dashboard_tabs {
            margin-top: 0 !important;
            margin-bottom: 20px !important;
            border-bottom: 1px solid var(--border);
        }

        .st-key-dashboard_tabs div[role="radiogroup"] {
            display: flex !important;
            align-items: flex-end !important;
            gap: 28px !important;
            padding: 0 4px !important;
            background: transparent !important;
            border: 0 !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label {
            position: relative !important;
            min-height: 48px !important;
            padding: 13px 2px 12px 2px !important;
            color: var(--text-soft) !important;
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            font-weight: 650 !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label *,
        .st-key-dashboard_tabs div[role="radiogroup"] label p,
        .st-key-dashboard_tabs div[role="radiogroup"] label span {
            color: inherit !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked),
        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked) * {
            color: var(--3f-red) !important;
            background: transparent !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked)::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: -1px;
            height: 3px;
            border-radius: 3px 3px 0 0;
            background: var(--3f-red);
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label input[type="radio"],
        .st-key-dashboard_tabs div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }

        .st-key-dashboard_refresh button {
            min-height: 42px !important;
            margin-bottom: 20px !important;
        }

        /* FILTRE STATUT */
        .st-key-contract_status_filter {
            max-width: 760px;
            margin-bottom: 20px !important;
        }

        .st-key-contract_status_filter div[role="radiogroup"] {
            width: fit-content !important;
            gap: 4px !important;
            padding: 5px !important;
            background: #F5F6F8 !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
        }

        .st-key-contract_status_filter div[role="radiogroup"] label {
            min-height: 42px !important;
            padding: 8px 15px !important;
            border-radius: 9px !important;
        }

        /* EXPANDERS / RADIOS INTERNES */
        div[data-testid="stExpander"] {
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            background: #FFFFFF !important;
            overflow: hidden !important;
        }

        div[data-testid="stExpander"] div[role="radiogroup"] {
            width: 100% !important;
            gap: 5px !important;
            padding: 5px !important;
            background: #F7F5F7 !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
        }

        div[data-testid="stExpander"] div[role="radiogroup"] label {
            min-height: 41px !important;
            padding: 8px 12px !important;
            background: #FFFFFF !important;
            color: var(--text-main) !important;
            border: 1px solid transparent !important;
            border-radius: 9px !important;
        }

        div[data-testid="stExpander"] div[role="radiogroup"] label:has(input:checked) {
            background: var(--3f-pink-soft) !important;
            color: #A3184A !important;
            border-color: #E7C8D6 !important;
        }

        div[data-testid="stExpander"] div[role="radiogroup"] label:has(input:checked) p,
        div[data-testid="stExpander"] div[role="radiogroup"] label:has(input:checked) span {
            color: #A3184A !important;
        }

        /* RÉSUMÉ TABLE */
        .vg-table-summary {
            display: flex;
            align-items: center;
            gap: 18px;
            overflow: hidden;
            margin: 8px 0 14px 0;
            padding: 12px 15px;
            background: #FFF7FA;
            border: 1px solid #EEDCE5;
            border-radius: 12px;
        }

        .vg-table-summary-item {
            display: flex;
            align-items: baseline;
            gap: 7px;
        }

        .vg-table-summary-value {
            color: var(--3f-red);
            font-size: 20px;
            font-weight: 800;
            line-height: 1;
        }

        .vg-table-summary-label {
            color: var(--text-soft);
            font-size: 12px;
            font-weight: 650;
        }

        .vg-table-summary-separator {
            width: 1px;
            height: 26px;
            background: #E7D9E0;
        }

        .vg-table-summary-mode {
            margin-left: auto;
            padding: 5px 10px;
            color: #A3184A;
            background: #FFFFFF;
            border: 1px solid #E7C8D6;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
        }

        /* POPOVER COLONNES */
        div[data-testid="stPopover"] button {
            min-height: 44px !important;
            color: #A3184A !important;
            background: #FFFFFF !important;
            border: 1px solid #E1DCE2 !important;
            border-radius: 11px !important;
            box-shadow: none !important;
        }

        div[data-testid="stPopoverBody"] {
            min-width: 360px !important;
            max-width: 430px !important;
        }

        .vg-columns-separator {
            height: 1px;
            margin: 10px 0 8px 0;
            background: var(--line-soft);
        }

        div[data-testid="stPopoverBody"] form [data-testid="stFormSubmitButton"] button[kind="primary"] {
            color: #FFFFFF !important;
            background: var(--3f-red) !important;
            border-color: var(--3f-red) !important;
        }

        /* RECHERCHE ACTIVE */
        .vg-search-active {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 7px;
            margin-bottom: 10px;
            padding: 7px 10px;
            color: #A3184A;
            background: var(--3f-pink-soft);
            border: 1px solid #E7C8D6;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
        }

        .vg-search-active-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--3f-red);
        }

        .st-key-effacer_recherche_contrat button {
            min-height: 36px !important;
            padding-left: 13px !important;
            padding-right: 13px !important;
        }

        /* PAGINATION */
        .vg-pagination-current {
            display: grid !important;
            grid-template-columns: 1fr auto 1fr !important;
            align-items: center !important;
            width: 100% !important;
            min-height: 48px !important;
            height: 48px !important;
            padding: 6px 14px !important;
            background: #FFF7FA !important;
            border: 1px solid #EEDCE5 !important;
            border-radius: 12px !important;
            box-sizing: border-box !important;
        }

        .vg-pagination-label {
            justify-self: end !important;
            margin-right: 9px !important;
            color: var(--text-soft) !important;
            font-size: 12px !important;
            font-weight: 700 !important;
        }

        .vg-pagination-current strong {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-width: 38px !important;
            height: 34px !important;
            padding: 0 10px !important;
            color: #FFFFFF !important;
            background: var(--3f-red) !important;
            border-radius: 9px !important;
            font-size: 14px !important;
            font-weight: 800 !important;
        }

        .vg-pagination-total {
            justify-self: start !important;
            margin-left: 9px !important;
            color: var(--text-soft) !important;
            font-size: 12px !important;
            font-weight: 700 !important;
        }

        .st-key-page_precedente_uniques button,
        .st-key-page_precedente_rattachements button,
        .st-key-page_precedente_prestations button,
        .st-key-page_suivante_uniques button,
        .st-key-page_suivante_rattachements button,
        .st-key-page_suivante_prestations button {
            min-height: 48px !important;
            height: 48px !important;
            color: #A3184A !important;
            background: #FFFFFF !important;
            border: 1px solid #E7DDE2 !important;
            border-radius: 12px !important;
            box-shadow: none !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }

        .st-key-page_precedente_uniques button:disabled,
        .st-key-page_precedente_rattachements button:disabled,
        .st-key-page_precedente_prestations button:disabled,
        .st-key-page_suivante_uniques button:disabled,
        .st-key-page_suivante_rattachements button:disabled,
        .st-key-page_suivante_prestations button:disabled {
            color: #B9C0CA !important;
            background: #F7F7F8 !important;
            border-color: #ECEDEF !important;
            opacity: 1 !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.vg-pagination-current) {
            align-items: stretch !important;
        }



        /* STABILITÉ APRÈS RERUN / PAGINATION */
        div[data-testid="stExpander"] {
            contain: none !important;
            overflow: visible !important;
        }

        div[data-testid="stExpanderDetails"] {
            overflow: visible !important;
        }

        [data-testid="stMainBlockContainer"] {
            min-height: max-content !important;
        }

        /* BLOCS COUVERTURE RESPONSIVES */
        .vg-chart-intro {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 18px;
            margin: 2px 0 12px 0;
        }

        .vg-chart-question {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 750;
            line-height: 1.35;
        }

        .vg-chart-base {
            flex: 0 0 auto;
            padding: 5px 9px;
            color: var(--navy);
            background: #EFF7FC;
            border: 1px solid #D9EAF5;
            border-radius: 999px;
            font-size: 10.5px;
            font-weight: 700;
            white-space: nowrap;
        }

        .vg-coverage-legend {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
            margin-top: 10px;
        }

        .vg-coverage-legend-item {
            display: grid;
            grid-template-columns: 11px minmax(0, 1fr) auto;
            align-items: center;
            gap: 9px;
            padding: 8px 10px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 10px;
        }

        .vg-coverage-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--dot);
        }

        .vg-coverage-label {
            color: var(--text-soft);
            font-size: 11px;
            font-weight: 650;
            line-height: 1.25;
        }

        .vg-coverage-value {
            color: var(--text-main);
            font-size: 11px;
            font-weight: 800;
            white-space: nowrap;
        }

        .vg-drilldown-summary {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 5px 0 13px 0;
        }

        .vg-drilldown-pill {
            padding: 6px 9px;
            color: var(--navy);
            background: #F4F8FB;
            border: 1px solid #DFEAF2;
            border-radius: 999px;
            font-size: 10.5px;
            font-weight: 700;
        }
  
                /* SYNTHÈSE ALERTES ET ANOMALIES */
        .vg-priority-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin: 4px 0 22px 0;
        }

        .vg-priority-card {
            min-height: 126px;
            padding: 17px 18px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-top: 4px solid var(--priority-color);
            border-radius: 15px;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.24);
            box-sizing: border-box;
        }

        .vg-priority-head {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }

        .vg-priority-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--priority-color);
        }

        .vg-priority-label {
            color: var(--text-soft);
            font-size: 11px;
            font-weight: 750;
            letter-spacing: 0.45px;
            text-transform: uppercase;
        }

        .vg-priority-value {
            color: var(--text-main);
            font-size: 30px;
            line-height: 1;
            font-weight: 800;
            margin-bottom: 9px;
        }

        .vg-priority-help {
            color: var(--text-muted);
            font-size: 11.5px;
            line-height: 1.45;
            font-weight: 500;
        }

        .vg-family-card {
            min-height: 142px;
            padding: 17px 18px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 14px;
            box-shadow: 0 7px 18px -17px rgba(27, 36, 48, 0.22);
            box-sizing: border-box;
        }

        .vg-family-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 800;
            margin-bottom: 8px;
        }

        .vg-family-value {
            color: var(--family-color);
            font-size: 25px;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 9px;
        }

        .vg-family-help {
            color: var(--text-muted);
            font-size: 11.5px;
            line-height: 1.45;
        }

        .vg-status-banner {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 15px 17px;
            margin: 4px 0 18px 0;
            background: var(--status-background);
            border: 1px solid var(--status-border);
            border-radius: 13px;
        }

        .vg-status-banner-dot {
            width: 11px;
            height: 11px;
            border-radius: 50%;
            background: var(--status-color);
            flex: 0 0 auto;
        }

        .vg-status-banner-title {
            color: var(--text-main);
            font-size: 13px;
            font-weight: 800;
        }

        .vg-status-banner-help {
            color: var(--text-soft);
            font-size: 12px;
            margin-top: 2px;
        }

        
        /* PAGE ALERTES — VERSION COMPACTE */
        .vg-alerts-hero {
            position: relative;
            overflow: hidden;
            margin: 4px 0 18px 0;
            padding: 19px 22px;
            color: #FFFFFF;
            background:
                radial-gradient(circle at 92% 12%, rgba(255,255,255,.20), transparent 24%),
                linear-gradient(135deg, #B92B57 0%, #D94B73 58%, #E97A99 100%);
            border: 1px solid #C94A70;
            border-radius: 16px;
            box-shadow: 0 12px 28px -23px rgba(150, 47, 82, .48);
        }

        .vg-alerts-hero::after {
            display: none;
        }

        .vg-alerts-hero-inner {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
        }

        .vg-alerts-hero-main {
            min-width: 0;
        }

        .vg-alerts-hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            margin-bottom: 7px;
            padding: 4px 9px;
            color: #FFFFFF;
            background: rgba(255,255,255,.16);
            border: 1px solid rgba(255,255,255,.26);
            border-radius: 999px;
            font-size: 9.5px;
            font-weight: 800;
            letter-spacing: .5px;
            text-transform: uppercase;
        }

        .vg-alerts-hero-line {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 5px;
        }

        .vg-alerts-hero-value {
            color: #FFFFFF;
            font-size: 36px;
            line-height: 1;
            letter-spacing: -1.1px;
            font-weight: 900;
        }

        .vg-alerts-hero-title {
            color: #FFFFFF;
            font-size: 16px;
            font-weight: 850;
        }

        .vg-alerts-hero-help {
            max-width: 680px;
            color: rgba(255,255,255,.84);
            font-size: 11.5px;
            line-height: 1.45;
            font-weight: 550;
        }

        .vg-alerts-hero-stats {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
            flex: 0 0 auto;
        }

        .vg-alerts-hero-stat {
            min-width: 112px;
            padding: 9px 11px;
            background: rgba(255,255,255,.16);
            border: 1px solid rgba(255,255,255,.25);
            border-radius: 10px;
            backdrop-filter: blur(4px);
        }

        .vg-alerts-hero-stat-label {
            display: block;
            margin-bottom: 2px;
            color: rgba(255,255,255,.78);
            font-size: 9.5px;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: .35px;
        }

        .vg-alerts-hero-stat-value {
            display: block;
            color: #FFFFFF;
            font-size: 17px;
            line-height: 1;
            font-weight: 900;
        }

        .vg-alert-zone-title {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 20px 0 10px 0;
            color: var(--text-main);
            font-size: 12px;
            font-weight: 850;
            letter-spacing: .65px;
            text-transform: uppercase;
        }

        .vg-alert-zone-title::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--zone-color);
            box-shadow: 0 0 0 5px color-mix(in srgb, var(--zone-color) 12%, transparent);
        }

        .vg-impact-alert-card {
            position: relative;
            overflow: hidden;
            min-height: 176px;
            padding: 18px 19px 16px 19px;
            background: linear-gradient(
                145deg,
                color-mix(in srgb, var(--alert-color) 8%, #FFFFFF),
                #FFFFFF 64%
            );
            border: 1px solid color-mix(in srgb, var(--alert-color) 22%, #E7E3E8);
            border-top: 5px solid var(--alert-color);
            border-radius: 16px;
            box-shadow: 0 12px 26px -22px color-mix(in srgb, var(--alert-color) 55%, transparent);
            box-sizing: border-box;
        }

        .vg-impact-alert-card::after {
            content: "";
            position: absolute;
            width: 80px;
            height: 80px;
            right: -34px;
            top: -34px;
            border-radius: 50%;
            background: color-mix(in srgb, var(--alert-color) 10%, transparent);
        }

        .vg-impact-alert-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 15px;
        }

        .vg-impact-alert-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            color: var(--alert-color);
            background: #FFFFFF;
            border: 1px solid color-mix(in srgb, var(--alert-color) 25%, #E7E3E8);
            border-radius: 10px;
            font-size: 16px;
            font-weight: 900;
        }

        .vg-impact-alert-badge {
            padding: 5px 9px;
            color: var(--alert-color);
            background: color-mix(in srgb, var(--alert-color) 10%, #FFFFFF);
            border: 1px solid color-mix(in srgb, var(--alert-color) 20%, #FFFFFF);
            border-radius: 999px;
            font-size: 9.5px;
            font-weight: 850;
            letter-spacing: .4px;
            text-transform: uppercase;
        }

        .vg-impact-alert-value {
            color: var(--text-main);
            font-size: 36px;
            line-height: 1;
            letter-spacing: -1px;
            font-weight: 900;
            margin-bottom: 7px;
        }

        .vg-impact-alert-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 850;
            line-height: 1.25;
            margin-bottom: 7px;
        }

        .vg-impact-alert-action {
            color: var(--text-soft);
            font-size: 11.5px;
            line-height: 1.45;
            font-weight: 550;
        }

        .vg-alert-detail-intro {
            margin: 12px 0 14px 0;
            padding: 15px 17px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 5px solid var(--detail-color);
            border-radius: 13px;
            box-shadow: 0 8px 20px -19px rgba(27, 36, 48, .25);
        }

        .vg-alert-detail-intro-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 850;
            margin-bottom: 5px;
        }

        .vg-alert-detail-intro-help {
            color: var(--text-soft);
            font-size: 12px;
            line-height: 1.5;
        }

        .st-key-alertes_navigation_rapide div[role="radiogroup"] {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 7px !important;
            padding: 6px !important;
            background: #F5F6F8 !important;
            border: 1px solid var(--border) !important;
            border-radius: 13px !important;
        }

        .st-key-alertes_navigation_rapide div[role="radiogroup"] label {
            min-height: 40px !important;
            padding: 8px 12px !important;
            color: var(--text-soft) !important;
            background: #FFFFFF !important;
            border: 1px solid transparent !important;
            border-radius: 9px !important;
            font-size: 11px !important;
            font-weight: 750 !important;
        }

        .st-key-alertes_navigation_rapide div[role="radiogroup"] label:has(input:checked) {
            color: #FFFFFF !important;
            background: var(--3f-red) !important;
            border-color: var(--3f-red) !important;
        }

        .st-key-alertes_navigation_rapide div[role="radiogroup"] label:has(input:checked) * {
            color: #FFFFFF !important;
        }

        .st-key-alertes_navigation_rapide div[role="radiogroup"] label input[type="radio"],
        .st-key-alertes_navigation_rapide div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }

        @media screen and (max-width: 900px) {
            .vg-alerts-hero {
                padding: 17px 18px;
            }

            .vg-alerts-hero-inner {
                align-items: flex-start;
                flex-direction: column;
                gap: 14px;
            }

            .vg-alerts-hero-stats {
                width: 100%;
                justify-content: flex-start;
            }

            .vg-alerts-hero-stat {
                flex: 1 1 105px;
                min-width: 0;
            }

            .vg-alerts-hero-value {
                font-size: 32px;
            }

            .vg-impact-alert-card {
                min-height: 158px;
            }
        }


        /* PAGE ANOMALIES — VERSION IMPACTANTE */
        .vg-anomaly-hero {
            position: relative;
            overflow: hidden;
            margin: 4px 0 18px 0;
            padding: 18px 22px;
            background:
                radial-gradient(circle at 92% 8%, rgba(255,255,255,.22), transparent 24%),
                linear-gradient(135deg, #3B2CAD 0%, #5140C5 55%, #7D70DD 100%);
            border: 1px solid #4938B8;
            border-radius: 17px;
            box-shadow: 0 15px 32px -25px rgba(67, 42, 189, .65);
        }

        .vg-anomaly-hero::after {
            display: none;
        }

        .vg-anomaly-hero-main {
            position: relative;
            z-index: 1;
        }

        .vg-anomaly-hero-kicker {
            display: inline-flex;
            align-items: center;
            margin-bottom: 8px;
            padding: 5px 10px;
            color: #FFFFFF;
            background: rgba(255,255,255,.14);
            border: 1px solid rgba(255,255,255,.22);
            border-radius: 999px;
            font-size: 9.5px;
            font-weight: 850;
            letter-spacing: .5px;
            text-transform: uppercase;
        }

        .vg-anomaly-hero-line {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 6px;
        }

        .vg-anomaly-hero-value {
            color: #FFFFFF;
            font-size: 36px;
            line-height: 1;
            letter-spacing: -1.1px;
            font-weight: 900;
        }

        .vg-anomaly-hero-title {
            color: #FFFFFF;
            font-size: 16px;
            font-weight: 850;
        }

        .vg-anomaly-hero-help {
            max-width: 720px;
            color: rgba(255,255,255,.84);
            font-size: 11.5px;
            line-height: 1.45;
            font-weight: 550;
        }

        .vg-anomaly-main-card {
            position: relative;
            overflow: hidden;
            min-height: 205px;
            padding: 22px 23px;
            background:
                radial-gradient(circle at 90% 10%, rgba(229,17,77,.08), transparent 28%),
                linear-gradient(145deg, #FFF3F7 0%, #FFFFFF 72%);
            border: 1px solid #F0C8D6;
            border-left: 6px solid var(--3f-red);
            border-radius: 17px;
            box-shadow: 0 14px 30px -24px rgba(229, 17, 77, .45);
            box-sizing: border-box;
        }

        .vg-anomaly-main-badge {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            margin-bottom: 14px;
            padding: 5px 10px;
            color: #A3184A;
            background: #FFFFFF;
            border: 1px solid #EFC8D6;
            border-radius: 999px;
            font-size: 9.5px;
            font-weight: 850;
            letter-spacing: .42px;
            text-transform: uppercase;
        }

        .vg-anomaly-main-value {
            color: var(--text-main);
            font-size: 47px;
            line-height: .95;
            letter-spacing: -1.7px;
            font-weight: 900;
            margin-bottom: 9px;
        }

        .vg-anomaly-main-title {
            color: var(--text-main);
            font-size: 17px;
            font-weight: 900;
            margin-bottom: 8px;
        }

        .vg-anomaly-main-help {
            max-width: 650px;
            color: var(--text-soft);
            font-size: 12px;
            line-height: 1.5;
            font-weight: 550;
        }

        .vg-anomaly-main-share {
            position: absolute;
            right: 22px;
            top: 22px;
            padding: 8px 10px;
            color: #A3184A;
            background: #FFFFFF;
            border: 1px solid #EFC8D6;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 900;
        }

        .vg-anomaly-secondary-card {
            min-height: 205px;
            padding: 20px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-top: 5px solid var(--anomaly-color);
            border-radius: 16px;
            box-shadow: 0 10px 24px -22px rgba(27, 36, 48, .28);
            box-sizing: border-box;
        }

        .vg-anomaly-secondary-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            margin-bottom: 15px;
            color: var(--anomaly-color);
            background: color-mix(in srgb, var(--anomaly-color) 9%, #FFFFFF);
            border: 1px solid color-mix(in srgb, var(--anomaly-color) 20%, #FFFFFF);
            border-radius: 10px;
            font-size: 15px;
            font-weight: 900;
        }

        .vg-anomaly-secondary-value {
            color: var(--text-main);
            font-size: 34px;
            line-height: 1;
            letter-spacing: -1px;
            font-weight: 900;
            margin-bottom: 8px;
        }

        .vg-anomaly-secondary-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 850;
            margin-bottom: 7px;
        }

        .vg-anomaly-secondary-help {
            color: var(--text-soft);
            font-size: 11.5px;
            line-height: 1.45;
        }

        .vg-anomaly-detail-intro {
            margin: 12px 0 14px 0;
            padding: 15px 17px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 5px solid var(--anomaly-detail-color);
            border-radius: 13px;
            box-shadow: 0 8px 20px -19px rgba(27, 36, 48, .25);
        }

        .vg-anomaly-detail-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 850;
            margin-bottom: 5px;
        }

        .vg-anomaly-detail-help {
            color: var(--text-soft);
            font-size: 12px;
            line-height: 1.5;
        }

        .st-key-anomalies_navigation_rapide div[role="radiogroup"] {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 7px !important;
            padding: 6px !important;
            background: #F5F6F8 !important;
            border: 1px solid var(--border) !important;
            border-radius: 13px !important;
        }

        .st-key-anomalies_navigation_rapide div[role="radiogroup"] label {
            min-height: 40px !important;
            padding: 8px 13px !important;
            color: var(--text-soft) !important;
            background: #FFFFFF !important;
            border: 1px solid transparent !important;
            border-radius: 9px !important;
            font-size: 11px !important;
            font-weight: 750 !important;
        }

        .st-key-anomalies_navigation_rapide div[role="radiogroup"] label:has(input:checked) {
            color: #FFFFFF !important;
            background: var(--3f-violet, #432ABD) !important;
            border-color: #432ABD !important;
        }

        .st-key-anomalies_navigation_rapide div[role="radiogroup"] label:has(input:checked) * {
            color: #FFFFFF !important;
        }

        .st-key-anomalies_navigation_rapide div[role="radiogroup"] label input[type="radio"],
        .st-key-anomalies_navigation_rapide div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }

        @media screen and (max-width: 900px) {
            .vg-anomaly-hero {
                padding: 17px 18px;
            }

            .vg-anomaly-main-card,
            .vg-anomaly-secondary-card {
                min-height: 170px;
            }

            .vg-anomaly-main-share {
                position: static;
                display: inline-flex;
                margin-top: 12px;
            }
        }


        /* COUVERTURE — SYNTHÈSE MÉTIER */
        .vg-coverage-summary {
            position: relative;
            overflow: hidden;
            display: grid;
            grid-template-columns: minmax(285px, 1.1fr) minmax(0, 2fr);
            gap: 18px;
            margin: 8px 0 18px 0;
            padding: 18px;
            background: linear-gradient(145deg, #F4FAFD 0%, #FFFFFF 70%);
            border: 1px solid #DCE8F0;
            border-radius: 18px;
            box-shadow: 0 14px 30px -26px rgba(23, 59, 105, .36);
        }

        .vg-coverage-summary::after {
            content: "";
            position: absolute;
            width: 150px;
            height: 150px;
            right: -72px;
            top: -78px;
            border-radius: 50%;
            background: rgba(128, 205, 255, .16);
        }

        .vg-coverage-main {
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 154px;
            padding: 18px 20px;
            color: #FFFFFF;
            background:
                radial-gradient(circle at 88% 12%, rgba(255,255,255,.16), transparent 26%),
                linear-gradient(135deg, #173B69 0%, #285B8E 58%, #4A8DB8 100%);
            border-radius: 15px;
            box-sizing: border-box;
        }

        .vg-coverage-main-kicker {
            display: inline-flex;
            width: fit-content;
            margin-bottom: 11px;
            padding: 4px 9px;
            color: rgba(255,255,255,.88);
            background: rgba(255,255,255,.13);
            border: 1px solid rgba(255,255,255,.2);
            border-radius: 999px;
            font-size: 9.5px;
            font-weight: 850;
            letter-spacing: .5px;
            text-transform: uppercase;
        }

        .vg-coverage-main-line {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 9px;
            margin-bottom: 8px;
        }

        .vg-coverage-main-value {
            color: #FFFFFF;
            font-size: 43px;
            line-height: .95;
            letter-spacing: -1.5px;
            font-weight: 900;
        }

        .vg-coverage-main-label {
            color: #FFFFFF;
            font-size: 16px;
            font-weight: 850;
        }

        .vg-coverage-main-help {
            color: rgba(255,255,255,.8);
            font-size: 11.5px;
            line-height: 1.45;
        }

        .vg-coverage-kpi-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .vg-coverage-kpi {
            min-height: 72px;
            padding: 12px 14px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 4px solid var(--coverage-color);
            border-radius: 12px;
            box-shadow: 0 7px 18px -18px rgba(27, 36, 48, .22);
            box-sizing: border-box;
        }

        .vg-coverage-kpi-label {
            margin-bottom: 5px;
            color: var(--text-muted);
            font-size: 9.5px;
            font-weight: 800;
            letter-spacing: .4px;
            text-transform: uppercase;
        }

        .vg-coverage-kpi-line {
            display: flex;
            align-items: baseline;
            gap: 8px;
        }

        .vg-coverage-kpi-value {
            color: var(--text-main);
            font-size: 23px;
            line-height: 1;
            letter-spacing: -.5px;
            font-weight: 900;
        }

        .vg-coverage-kpi-rate {
            color: var(--coverage-color);
            font-size: 11px;
            font-weight: 850;
        }

        .vg-coverage-kpi-help {
            margin-top: 5px;
            color: var(--text-soft);
            font-size: 10.5px;
            line-height: 1.35;
        }

        .vg-coverage-context {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin: 0 0 18px 0;
            padding: 9px 12px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 11px;
        }

        .vg-coverage-context-label {
            color: var(--text-muted);
            font-size: 10px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .42px;
        }

        .vg-coverage-context-pill {
            padding: 5px 8px;
            color: var(--navy);
            background: #F2F7FB;
            border: 1px solid #DEEAF2;
            border-radius: 999px;
            font-size: 10.5px;
            font-weight: 750;
        }

        @media screen and (max-width: 900px) {
            .vg-coverage-summary {
                grid-template-columns: 1fr;
            }

            .vg-coverage-kpi-grid {
                grid-template-columns: 1fr;
            }

            .vg-coverage-main {
                min-height: 138px;
            }
        }


        /* COUVERTURE — LECTURE CLAIRE ET DOUCE */
        .vg-coverage-summary {
            position: relative;
            overflow: hidden;
            display: block;
            margin: 8px 0 14px 0;
            padding: 20px 22px;
            background: linear-gradient(135deg, #FFF5F9 0%, #FFFFFF 72%);
            border: 1px solid #EEDBE4;
            border-left: 6px solid #D65A83;
            border-radius: 17px;
            box-shadow: 0 12px 28px -25px rgba(145, 54, 88, .32);
        }

        .vg-coverage-summary::after {
            content: "";
            position: absolute;
            width: 135px;
            height: 135px;
            right: -65px;
            top: -70px;
            border-radius: 50%;
            background: rgba(128, 205, 255, .16);
        }

        .vg-coverage-summary-kicker {
            position: relative;
            z-index: 1;
            display: inline-flex;
            margin-bottom: 9px;
            padding: 4px 9px;
            color: #A53860;
            background: #FFFFFF;
            border: 1px solid #EACBD7;
            border-radius: 999px;
            font-size: 9.5px;
            font-weight: 850;
            letter-spacing: .45px;
            text-transform: uppercase;
        }

        .vg-coverage-summary-title {
            position: relative;
            z-index: 1;
            color: var(--text-main);
            font-size: 22px;
            line-height: 1.25;
            font-weight: 900;
            letter-spacing: -.35px;
            margin-bottom: 7px;
        }

        .vg-coverage-summary-title strong {
            color: #C63F6D;
            font-size: 30px;
            letter-spacing: -.8px;
        }

        .vg-coverage-summary-help {
            position: relative;
            z-index: 1;
            max-width: 940px;
            color: var(--text-soft);
            font-size: 12px;
            line-height: 1.5;
            font-weight: 550;
        }

        .vg-coverage-context {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin: 0 0 18px 0;
            padding: 9px 12px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 11px;
        }

        .vg-coverage-context-label {
            color: var(--text-muted);
            font-size: 10px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .42px;
        }

        .vg-coverage-context-pill {
            padding: 5px 8px;
            color: #35566E;
            background: #F3F8FB;
            border: 1px solid #DFEAF1;
            border-radius: 999px;
            font-size: 10.5px;
            font-weight: 750;
        }

        .vg-reading-note {
            margin: 0 0 16px 0;
            padding: 13px 15px;
            color: #526373;
            background: #F7FBFD;
            border: 1px solid #DDEAF1;
            border-radius: 12px;
            font-size: 11.5px;
            line-height: 1.5;
        }

        .vg-reading-note strong {
            color: #263F50;
        }

        .vg-coverage-reading-card {
            min-height: 255px;
            padding: 19px 20px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-top: 5px solid var(--reading-color);
            border-radius: 16px;
            box-shadow: 0 10px 24px -23px rgba(27,36,48,.28);
            box-sizing: border-box;
        }

        .vg-coverage-reading-eyebrow {
            margin-bottom: 7px;
            color: var(--reading-color);
            font-size: 9.5px;
            font-weight: 850;
            letter-spacing: .48px;
            text-transform: uppercase;
        }

        .vg-coverage-reading-title {
            color: var(--text-main);
            font-size: 16px;
            font-weight: 900;
            margin-bottom: 5px;
        }

        .vg-coverage-reading-question {
            min-height: 38px;
            color: var(--text-soft);
            font-size: 11.5px;
            line-height: 1.45;
            margin-bottom: 16px;
        }

        .vg-coverage-reading-main {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 13px;
        }

        .vg-coverage-reading-rate {
            color: var(--text-main);
            font-size: 35px;
            line-height: 1;
            letter-spacing: -1.1px;
            font-weight: 900;
        }

        .vg-coverage-reading-count {
            color: var(--text-soft);
            font-size: 11.5px;
            font-weight: 700;
        }

        .vg-coverage-progress {
            display: flex;
            overflow: hidden;
            width: 100%;
            height: 12px;
            margin-bottom: 14px;
            background: #EEF2F4;
            border-radius: 999px;
        }

        .vg-coverage-progress-covered {
            height: 100%;
            background: var(--reading-color);
        }

        .vg-coverage-progress-gap {
            height: 100%;
            background: var(--gap-color);
        }

        .vg-coverage-reading-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 9px;
        }

        .vg-coverage-reading-stat {
            padding: 10px 11px;
            background: #FAFBFC;
            border: 1px solid #EBEEF1;
            border-radius: 10px;
        }

        .vg-coverage-reading-stat-label {
            color: var(--text-muted);
            font-size: 9px;
            font-weight: 800;
            letter-spacing: .35px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .vg-coverage-reading-stat-value {
            color: var(--text-main);
            font-size: 18px;
            font-weight: 900;
        }

        .vg-coverage-reading-base {
            margin-top: 11px;
            color: var(--text-muted);
            font-size: 10px;
            font-weight: 600;
        }

        .vg-simple-section-title {
            margin: 20px 0 10px 0;
            color: var(--text-main);
            font-size: 14px;
            font-weight: 900;
        }

        .vg-park-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
        }

        .vg-park-card {
            padding: 14px 15px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 4px solid var(--park-color);
            border-radius: 12px;
        }

        .vg-park-label {
            margin-bottom: 5px;
            color: var(--text-muted);
            font-size: 9.5px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .38px;
        }

        .vg-park-line {
            display: flex;
            align-items: baseline;
            gap: 7px;
        }

        .vg-park-value {
            color: var(--text-main);
            font-size: 24px;
            line-height: 1;
            font-weight: 900;
        }

        .vg-park-rate {
            color: var(--park-color);
            font-size: 11px;
            font-weight: 850;
        }

        .vg-contract-intensity {
            display: grid;
            grid-template-columns: minmax(0, 1.7fr) minmax(260px, .9fr);
            gap: 12px;
        }

        .vg-intensity-distribution {
            padding: 16px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 14px;
        }

        .vg-intensity-row {
            display: grid;
            grid-template-columns: 135px minmax(0, 1fr) 78px;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }

        .vg-intensity-row:last-child {
            margin-bottom: 0;
        }

        .vg-intensity-label {
            color: var(--text-soft);
            font-size: 11px;
            font-weight: 750;
        }

        .vg-intensity-track {
            overflow: hidden;
            height: 10px;
            background: #EEF1F4;
            border-radius: 999px;
        }

        .vg-intensity-fill {
            height: 100%;
            width: var(--intensity-width);
            background: var(--intensity-color);
            border-radius: 999px;
        }

        .vg-intensity-value {
            color: var(--text-main);
            font-size: 11px;
            font-weight: 850;
            text-align: right;
        }

        .vg-intensity-kpis {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
        }

        .vg-intensity-kpi {
            min-height: 94px;
            padding: 11px 13px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 4px solid var(--intensity-color);
            border-radius: 11px;
        }

        .vg-intensity-kpi-label {
            color: var(--text-muted);
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .35px;
            margin-bottom: 3px;
        }

        .vg-intensity-kpi-value {
            color: var(--text-main);
            font-size: 20px;
            font-weight: 900;
        }

        .vg-intensity-kpi-help {
            margin-top: 3px;
            color: var(--text-soft);
            font-size: 9.5px;
            line-height: 1.35;
        }

        @media screen and (max-width: 900px) {
            .vg-park-grid,
            .vg-contract-intensity {
                grid-template-columns: 1fr;
            }

            .vg-intensity-row {
                grid-template-columns: 105px minmax(0, 1fr) 66px;
            }
        }


        /* ÉQUIPEMENTS — PRÉSENTATION PREMIUM */
        .vg-equipment-hero {
            position: relative;
            overflow: hidden;
            display: grid;
            grid-template-columns: minmax(260px, .8fr) minmax(0, 1.5fr);
            gap: 18px;
            align-items: stretch;
            margin: 8px 0 16px 0;
            padding: 18px;
            background: linear-gradient(145deg, #F3FBF9 0%, #FFFFFF 72%);
            border: 1px solid #DCEBE7;
            border-radius: 17px;
            box-shadow: 0 13px 28px -25px rgba(47, 124, 109, .34);
        }

        .vg-equipment-hero-main {
            display: flex;
            align-items: center;
            gap: 18px;
            min-height: 190px;
            padding: 18px;
            background: #FFFFFF;
            border: 1px solid #DDEBE7;
            border-radius: 15px;
            box-sizing: border-box;
        }

        .vg-equipment-ring {
            --ring-rate: 0;
            --ring-color: #4F9B88;
            position: relative;
            flex: 0 0 auto;
            width: 128px;
            height: 128px;
            border-radius: 50%;
            background:
                conic-gradient(
                    var(--ring-color) calc(var(--ring-rate) * 1%),
                    #F3D9E4 0
                );
            box-shadow: inset 0 0 0 1px rgba(79,155,136,.1);
        }

        .vg-equipment-ring::before {
            content: "";
            position: absolute;
            inset: 13px;
            background: #FFFFFF;
            border-radius: 50%;
            box-shadow: 0 5px 14px -12px rgba(27,36,48,.35);
        }

        .vg-equipment-ring-center {
            position: absolute;
            inset: 0;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }

        .vg-equipment-ring-value {
            color: var(--text-main);
            font-size: 25px;
            line-height: 1;
            font-weight: 900;
            letter-spacing: -.7px;
        }

        .vg-equipment-ring-label {
            margin-top: 4px;
            color: var(--text-muted);
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .35px;
        }

        .vg-equipment-hero-copy {
            min-width: 0;
        }

        .vg-equipment-hero-kicker {
            display: inline-flex;
            margin-bottom: 8px;
            padding: 4px 8px;
            color: #347564;
            background: #EAF7F3;
            border: 1px solid #CDE9E1;
            border-radius: 999px;
            font-size: 9px;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: .4px;
        }

        .vg-equipment-hero-title {
            color: var(--text-main);
            font-size: 18px;
            line-height: 1.28;
            font-weight: 900;
            margin-bottom: 7px;
        }

        .vg-equipment-hero-help {
            color: var(--text-soft);
            font-size: 11.5px;
            line-height: 1.5;
        }

        .vg-equipment-stats {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .vg-equipment-stat {
            min-height: 89px;
            padding: 13px 14px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-left: 4px solid var(--equipment-color);
            border-radius: 12px;
            box-sizing: border-box;
        }

        .vg-equipment-stat-label {
            margin-bottom: 5px;
            color: var(--text-muted);
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .38px;
        }

        .vg-equipment-stat-line {
            display: flex;
            align-items: baseline;
            gap: 7px;
        }

        .vg-equipment-stat-value {
            color: var(--text-main);
            font-size: 23px;
            line-height: 1;
            font-weight: 900;
        }

        .vg-equipment-stat-rate {
            color: var(--equipment-color);
            font-size: 11px;
            font-weight: 850;
        }

        .vg-equipment-stat-help {
            margin-top: 5px;
            color: var(--text-soft);
            font-size: 10px;
            line-height: 1.35;
        }

        .vg-equipment-types-panel {
            margin-top: 8px;
            padding: 17px 18px;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 15px;
        }

        .vg-equipment-types-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 16px;
        }

        .vg-equipment-types-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 900;
        }

        .vg-equipment-types-subtitle {
            margin-top: 3px;
            color: var(--text-soft);
            font-size: 10.5px;
            line-height: 1.4;
        }

        .vg-equipment-types-total {
            flex: 0 0 auto;
            padding: 5px 9px;
            color: #35566E;
            background: #F2F7FB;
            border: 1px solid #DDEAF2;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 800;
        }

        .vg-equipment-type-row {
            display: grid;
            grid-template-columns: minmax(175px, .9fr) minmax(320px, 2.3fr) 205px;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }

        .vg-equipment-type-row:last-child {
            margin-bottom: 0;
        }

        .vg-equipment-type-label {
            overflow: hidden;
            color: var(--text-soft);
            font-size: 10.5px;
            font-weight: 800;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .vg-equipment-type-track {
            display: flex;
            overflow: hidden;
            width: 100%;
            height: 13px;
            background: #EEF2F4;
            border-radius: 999px;
            box-shadow: inset 0 0 0 1px rgba(27, 36, 48, .04);
        }

        .vg-equipment-type-covered {
            height: 100%;
            width: var(--covered-width);
            background: #4F9B88;
            transition: width .2s ease;
        }

        .vg-equipment-type-uncovered {
            height: 100%;
            width: var(--uncovered-width);
            background: #F3B6C6;
            transition: width .2s ease;
        }

        .vg-equipment-type-value {
            min-width: 0;
            color: var(--text-main);
            text-align: right;
            white-space: nowrap;
        }

        .vg-equipment-type-rate {
            color: var(--text-main);
            font-size: 11.5px;
            font-weight: 900;
            line-height: 1.2;
        }

        .vg-equipment-type-detail {
            margin-top: 4px;
            color: var(--text-muted);
            font-size: 9.8px;
            font-weight: 650;
            line-height: 1.25;
        }

        .vg-equipment-type-detail strong {
            color: var(--text-soft);
            font-weight: 800;
        }

        .vg-equipment-types-legend {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 13px;
            margin-top: -4px;
            margin-bottom: 16px;
            color: var(--text-soft);
            font-size: 9.5px;
            font-weight: 700;
        }

        .vg-equipment-types-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .vg-equipment-types-legend-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--legend-color);
        }

        .vg-equipment-category-bar {
            margin: 14px 0 10px 0;
            padding: 13px 15px 10px 15px;
            background: #F8FAFC;
            border: 1px solid #E4E9EE;
            border-radius: 13px;
        }

        .vg-equipment-category-bar-title {
            margin-bottom: 3px;
            color: var(--text-main);
            font-size: 11.5px;
            font-weight: 850;
        }

        .vg-equipment-category-bar-help {
            color: var(--text-soft);
            font-size: 10px;
            line-height: 1.35;
        }

        .st-key-filtre_analyse_type_equipement {
            margin-top: -8px !important;
            margin-bottom: 8px !important;
        }

        .st-key-filtre_analyse_type_equipement div[data-baseweb="select"] > div {
            min-height: 44px !important;
            background: #FFFFFF !important;
            border: 1px solid #DCE3E9 !important;
            border-radius: 11px !important;
            box-shadow: none !important;
        }

        .st-key-filtre_analyse_type_equipement div[data-baseweb="select"] > div:focus-within {
            border-color: #D65A83 !important;
            box-shadow: 0 0 0 3px rgba(214, 90, 131, .08) !important;
        }

        /* Filtres présents uniquement dans le détail équipements */
        .st-key-filtre_statut_couverture_equipement {
            margin: 4px 0 12px 0 !important;
        }

        .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] {
            display: inline-flex !important;
            gap: 5px !important;
            padding: 5px !important;
            background: #F5F6F8 !important;
            border: 1px solid #E2E6EA !important;
            border-radius: 12px !important;
        }

        .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] label {
            min-height: 38px !important;
            padding: 7px 13px !important;
            color: var(--text-soft) !important;
            background: #FFFFFF !important;
            border: 1px solid transparent !important;
            border-radius: 9px !important;
            font-size: 11px !important;
            font-weight: 750 !important;
        }

        .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] label:has(input:checked) {
            color: #FFFFFF !important;
            background: #4F9B88 !important;
            border-color: #4F9B88 !important;
        }

        .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] label:has(input:checked) * {
            color: #FFFFFF !important;
        }

        .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] label input[type="radio"],
        .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }

        .st-key-effacer_recherche_equipement {
            display: flex !important;
            align-items: flex-end !important;
            height: 74px !important;
        }

        .st-key-effacer_recherche_equipement button {
            width: 42px !important;
            min-width: 42px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 0 !important;
            margin: 0 !important;

            color: #A3184A !important;
            background: #FFF7FA !important;
            border: 1px solid #E7C8D6 !important;
            border-radius: 11px !important;

            font-size: 16px !important;
            font-weight: 900 !important;
            box-shadow: none !important;
        }

        .st-key-effacer_recherche_equipement button:hover {
            color: #FFFFFF !important;
            background: var(--3f-red) !important;
            border-color: var(--3f-red) !important;
        }

        @media screen and (max-width: 900px) {
            .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] {
                display: flex !important;
                width: 100% !important;
            }

            .st-key-filtre_statut_couverture_equipement div[role="radiogroup"] label {
                flex: 1 1 0 !important;
                justify-content: center !important;
            }

            .st-key-effacer_recherche_equipement {
                height: auto !important;
            }

            .st-key-effacer_recherche_equipement button {
                width: 100% !important;
                min-width: 100% !important;
            }
        }

        .st-key-export_repartition_types_equipement,
        .st-key-export_couverture_equipements {
            display: flex !important;
            justify-content: flex-end !important;
        }

        .st-key-export_repartition_types_equipement button,
        .st-key-export_couverture_equipements button {
            min-height: 36px !important;
            width: auto !important;
            padding: 7px 12px !important;
            color: #A3184A !important;
            background: #FFFFFF !important;
            border: 1px solid #E5C4D2 !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            font-size: 11px !important;
            font-weight: 750 !important;
        }

        .st-key-export_repartition_types_equipement button:hover,
        .st-key-export_couverture_equipements button:hover {
            color: #FFFFFF !important;
            background: #D65A83 !important;
            border-color: #D65A83 !important;
        }

        @media screen and (max-width: 900px) {
            .vg-equipment-hero {
                grid-template-columns: 1fr;
            }

            .vg-equipment-stats {
                grid-template-columns: 1fr;
            }

            .vg-equipment-type-row {
                grid-template-columns: 1fr;
                gap: 7px;
                padding-bottom: 10px;
                border-bottom: 1px solid #EEF1F4;
            }

            .vg-equipment-type-value {
                text-align: left;
            }

            .vg-equipment-ring {
                width: 108px;
                height: 108px;
            }
        }


        /* COUVERTURE — STRUCTURE CLAIRE */
        .vg-step-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 20px 0 12px 0;
        }

        .vg-step-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            flex: 0 0 auto;
            color: #FFFFFF;
            background: #D65A83;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 900;
        }

        .vg-step-copy {
            min-width: 0;
        }

        .vg-step-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 900;
            line-height: 1.2;
        }

        .vg-step-help {
            margin-top: 2px;
            color: var(--text-soft);
            font-size: 10.5px;
            line-height: 1.4;
        }

        .vg-coverage-reading-card {
            min-height: 238px;
            padding: 18px 19px;
            background: #FFFFFF;
            border: 1px solid #E5E8EC;
            border-radius: 15px;
            box-shadow: 0 9px 22px -22px rgba(27,36,48,.28);
            box-sizing: border-box;
        }

        .vg-coverage-reading-card.primary {
            border-top: 5px solid #D65A83;
        }

        .vg-coverage-reading-card.secondary {
            border-top: 5px solid #4F9B88;
        }

        .vg-coverage-reading-eyebrow {
            margin-bottom: 8px;
            color: var(--reading-color);
            font-size: 9px;
            font-weight: 850;
            letter-spacing: .5px;
            text-transform: uppercase;
        }

        .vg-coverage-reading-title {
            color: var(--text-main);
            font-size: 16px;
            font-weight: 900;
            margin-bottom: 5px;
        }

        .vg-coverage-reading-question {
            min-height: 34px;
            color: var(--text-soft);
            font-size: 11px;
            line-height: 1.45;
            margin-bottom: 13px;
        }

        .vg-coverage-reading-main {
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }

        .vg-coverage-reading-rate {
            color: var(--text-main);
            font-size: 34px;
            line-height: 1;
            letter-spacing: -1px;
            font-weight: 900;
        }

        .vg-coverage-reading-count {
            color: var(--text-soft);
            font-size: 11px;
            font-weight: 750;
        }

        .vg-coverage-progress {
            display: flex;
            overflow: hidden;
            width: 100%;
            height: 10px;
            margin-bottom: 13px;
            background: #EEF2F4;
            border-radius: 999px;
        }

        .vg-coverage-progress-covered {
            height: 100%;
            background: var(--reading-color);
        }

        .vg-coverage-progress-gap {
            height: 100%;
            background: var(--gap-color);
        }

        .vg-coverage-reading-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 9px;
        }

        .vg-coverage-reading-stat {
            padding: 10px 11px;
            background: #F8FAFB;
            border: 1px solid #E9EDF0;
            border-radius: 10px;
        }

        .vg-coverage-reading-stat-label {
            color: var(--text-muted);
            font-size: 8.7px;
            font-weight: 800;
            letter-spacing: .35px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .vg-coverage-reading-stat-value {
            color: var(--text-main);
            font-size: 18px;
            font-weight: 900;
        }

        .vg-coverage-reading-base {
            margin-top: 10px;
            color: var(--text-muted);
            font-size: 9.7px;
            font-weight: 600;
        }

        .vg-park-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
        }

        .vg-park-card {
            padding: 14px 15px;
            background: #FFFFFF;
            border: 1px solid #E5E8EC;
            border-radius: 12px;
            box-shadow: 0 6px 16px -18px rgba(27,36,48,.22);
        }

        .vg-park-label {
            margin-bottom: 5px;
            color: var(--text-muted);
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .38px;
        }

        .vg-park-line {
            display: flex;
            align-items: baseline;
            gap: 7px;
        }

        .vg-park-value {
            color: var(--text-main);
            font-size: 23px;
            line-height: 1;
            font-weight: 900;
        }

        .vg-park-rate {
            color: var(--park-color);
            font-size: 10.5px;
            font-weight: 850;
        }

        .vg-contract-intensity {
            display: grid;
            grid-template-columns: minmax(0, 1.6fr) minmax(250px, .8fr);
            gap: 12px;
        }

        .vg-intensity-distribution {
            padding: 16px;
            background: #FFFFFF;
            border: 1px solid #E5E8EC;
            border-radius: 13px;
        }

        .vg-intensity-row {
            display: grid;
            grid-template-columns: 125px minmax(0, 1fr) 78px;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }

        .vg-intensity-row:last-child {
            margin-bottom: 0;
        }

        .vg-intensity-label {
            color: var(--text-soft);
            font-size: 10.5px;
            font-weight: 750;
        }

        .vg-intensity-track {
            overflow: hidden;
            height: 9px;
            background: #EEF1F4;
            border-radius: 999px;
        }

        .vg-intensity-fill {
            height: 100%;
            width: var(--intensity-width);
            background: var(--intensity-color);
            border-radius: 999px;
        }

        .vg-intensity-value {
            color: var(--text-main);
            font-size: 10.5px;
            font-weight: 850;
            text-align: right;
        }

        .vg-intensity-kpis {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
        }

        .vg-intensity-kpi {
            padding: 11px 13px;
            background: #FFFFFF;
            border: 1px solid #E5E8EC;
            border-left: 4px solid var(--intensity-color);
            border-radius: 11px;
        }

        .vg-intensity-kpi-label {
            color: var(--text-muted);
            font-size: 8.8px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .35px;
            margin-bottom: 3px;
        }

        .vg-intensity-kpi-value {
            color: var(--text-main);
            font-size: 19px;
            font-weight: 900;
        }

        .vg-intensity-kpi-help {
            margin-top: 3px;
            color: var(--text-soft);
            font-size: 9.3px;
            line-height: 1.35;
        }

        /* ÉQUIPEMENTS — STRUCTURE SIMPLIFIÉE */
        .vg-equipment-summary {
            display: grid;
            grid-template-columns: minmax(250px, .8fr) minmax(0, 1.4fr);
            gap: 14px;
            align-items: stretch;
        }

        .vg-equipment-main-card {
            display: flex;
            align-items: center;
            gap: 18px;
            min-height: 170px;
            padding: 18px;
            background: linear-gradient(145deg, #EFF8F5 0%, #FFFFFF 75%);
            border: 1px solid #DCEAE6;
            border-radius: 15px;
        }

        .vg-equipment-ring {
            --ring-rate: 0;
            position: relative;
            flex: 0 0 auto;
            width: 116px;
            height: 116px;
            border-radius: 50%;
            background:
                conic-gradient(
                    #4F9B88 calc(var(--ring-rate) * 1%),
                    #F1D7E1 0
                );
        }

        .vg-equipment-ring::before {
            content: "";
            position: absolute;
            inset: 13px;
            background: #FFFFFF;
            border-radius: 50%;
        }

        .vg-equipment-ring-center {
            position: absolute;
            inset: 0;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }

        .vg-equipment-ring-value {
            color: var(--text-main);
            font-size: 24px;
            line-height: 1;
            font-weight: 900;
        }

        .vg-equipment-ring-label {
            margin-top: 4px;
            color: var(--text-muted);
            font-size: 8.5px;
            font-weight: 800;
            text-transform: uppercase;
        }

        .vg-equipment-main-title {
            color: var(--text-main);
            font-size: 17px;
            line-height: 1.3;
            font-weight: 900;
            margin-bottom: 7px;
        }

        .vg-equipment-main-help {
            color: var(--text-soft);
            font-size: 10.8px;
            line-height: 1.45;
        }

        .vg-equipment-kpis {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .vg-equipment-kpi {
            padding: 14px 15px;
            background: #FFFFFF;
            border: 1px solid #E5E8EC;
            border-left: 4px solid var(--equipment-color);
            border-radius: 12px;
        }

        .vg-equipment-kpi-label {
            margin-bottom: 5px;
            color: var(--text-muted);
            font-size: 9px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .35px;
        }

        .vg-equipment-kpi-line {
            display: flex;
            align-items: baseline;
            gap: 7px;
        }

        .vg-equipment-kpi-value {
            color: var(--text-main);
            font-size: 22px;
            line-height: 1;
            font-weight: 900;
        }

        .vg-equipment-kpi-rate {
            color: var(--equipment-color);
            font-size: 10.5px;
            font-weight: 850;
        }

        .vg-equipment-kpi-help {
            margin-top: 5px;
            color: var(--text-soft);
            font-size: 9.7px;
            line-height: 1.35;
        }

        .vg-equipment-types-panel {
            margin-top: 14px;
            padding: 17px 18px;
            background: #FFFFFF;
            border: 1px solid #E5E8EC;
            border-radius: 14px;
        }

        .vg-equipment-types-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 15px;
        }

        .vg-equipment-types-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 900;
        }

        .vg-equipment-types-subtitle {
            margin-top: 3px;
            color: var(--text-soft);
            font-size: 10.3px;
        }

        .vg-equipment-types-total {
            padding: 5px 9px;
            color: #35566E;
            background: #F2F7FB;
            border: 1px solid #DDEAF2;
            border-radius: 999px;
            font-size: 9.8px;
            font-weight: 800;
        }

        .vg-equipment-type-row {
            display: grid;
            grid-template-columns: minmax(140px, .8fr) minmax(0, 2fr) 140px;
            align-items: center;
            gap: 11px;
            margin-bottom: 11px;
        }

        .vg-equipment-type-row:last-child {
            margin-bottom: 0;
        }

        .vg-equipment-type-label {
            overflow: hidden;
            color: var(--text-soft);
            font-size: 10.2px;
            font-weight: 750;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .vg-equipment-type-track {
            overflow: hidden;
            height: 9px;
            background: #EEF2F4;
            border-radius: 999px;
        }

        .vg-equipment-type-fill {
            height: 100%;
            width: var(--equipment-width);
            background: var(--equipment-bar-color);
            border-radius: 999px;
        }

        .vg-equipment-type-value {
            color: var(--text-main);
            font-size: 10.2px;
            font-weight: 850;
            text-align: right;
            white-space: nowrap;
        }

        @media screen and (max-width: 900px) {
            .vg-park-grid,
            .vg-contract-intensity,
            .vg-equipment-summary {
                grid-template-columns: 1fr;
            }

            .vg-equipment-kpis {
                grid-template-columns: 1fr;
            }

            .vg-equipment-type-row {
                grid-template-columns: 105px minmax(0, 1fr) 100px;
            }
        }


        /* COUVERTURE — LECTURE EXECUTIVE */
        .vg-coverage-insights {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 4px 0 18px 0;
        }

        .vg-coverage-insight {
            display: flex;
            align-items: flex-start;
            gap: 11px;
            min-height: 88px;
            padding: 13px 14px;
            background: #FFFFFF;
            border: 1px solid #E5E8EC;
            border-left: 4px solid var(--insight-color);
            border-radius: 12px;
            box-shadow: 0 7px 18px -19px rgba(27,36,48,.24);
            box-sizing: border-box;
        }

        .vg-coverage-insight-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            width: 30px;
            height: 30px;
            color: var(--insight-color);
            background: color-mix(in srgb, var(--insight-color) 9%, #FFFFFF);
            border: 1px solid color-mix(in srgb, var(--insight-color) 18%, #FFFFFF);
            border-radius: 9px;
            font-size: 14px;
            font-weight: 900;
        }

        .vg-coverage-insight-value {
            color: var(--text-main);
            font-size: 19px;
            line-height: 1;
            font-weight: 900;
            margin-bottom: 5px;
        }

        .vg-coverage-insight-text {
            color: var(--text-soft);
            font-size: 10.5px;
            line-height: 1.4;
            font-weight: 600;
        }

        /* Cartes patrimoine plus compactes */
        .vg-park-card {
            min-height: 86px !important;
            padding: 12px 14px !important;
            border-left: 4px solid var(--park-color) !important;
            box-sizing: border-box !important;
        }

        .vg-park-label {
            margin-bottom: 7px !important;
        }

        .vg-park-value {
            font-size: 25px !important;
        }

        /* Deux niveaux plus différenciés */
        .vg-coverage-reading-card {
            min-height: 244px !important;
            position: relative;
            overflow: hidden;
        }

        .vg-coverage-reading-card.primary {
            background: linear-gradient(145deg, #FFF7FA 0%, #FFFFFF 68%);
            border-top-color: #D65A83 !important;
        }

        .vg-coverage-reading-card.secondary {
            background: linear-gradient(145deg, #F3FAF7 0%, #FFFFFF 68%);
            border-top-color: #4F9B88 !important;
        }

        .vg-coverage-reading-card::after {
            content: "";
            position: absolute;
            width: 82px;
            height: 82px;
            right: -40px;
            top: -40px;
            border-radius: 50%;
            background: color-mix(in srgb, var(--reading-color) 8%, transparent);
        }

        .vg-coverage-reading-title,
        .vg-coverage-reading-question,
        .vg-coverage-reading-main,
        .vg-coverage-progress,
        .vg-coverage-reading-stats,
        .vg-coverage-reading-base,
        .vg-coverage-reading-eyebrow {
            position: relative;
            z-index: 1;
        }

        /* Intensité : plus lisible et plus dashboard */
        .vg-intensity-distribution {
            padding: 17px 18px !important;
            background: #FFFFFF !important;
            border: 1px solid #E5E8EC !important;
            border-radius: 14px !important;
        }

        .vg-intensity-row {
            grid-template-columns: 175px minmax(0, 1fr) 105px !important;
            margin-bottom: 15px !important;
        }

        .vg-intensity-track {
            height: 12px !important;
        }

        .vg-intensity-label {
            font-size: 11px !important;
        }

        .vg-intensity-value {
            font-size: 11px !important;
        }

        .vg-intensity-kpi {
            min-height: 94px !important;
            padding: 13px 14px !important;
        }

        .vg-intensity-kpi-value {
            font-size: 22px !important;
        }

        /* Lecture d'introduction moins vide */
        .vg-reading-note {
            margin-bottom: 12px !important;
            padding: 11px 14px !important;
            background: #F7FAFC !important;
        }

        @media screen and (max-width: 900px) {
            .vg-coverage-insights {
                grid-template-columns: 1fr;
            }

            .vg-intensity-row {
                grid-template-columns: 120px minmax(0, 1fr) 88px !important;
            }
        }

        /* RENVOI COUVERTURE VERS ALERTES */
        .vg-coverage-alert {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 22px;
            margin: 4px 0 20px 0;
            padding: 17px 19px;
            background: #FFF7FA;
            border: 1px solid #EBCFD9;
            border-left: 5px solid var(--3f-red);
            border-radius: 14px;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.24);
        }

        .vg-coverage-alert-content {
            display: flex;
            align-items: flex-start;
            gap: 13px;
            min-width: 0;
        }

        .vg-coverage-alert-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            width: 38px;
            height: 38px;
            color: var(--3f-red);
            background: #FFFFFF;
            border: 1px solid #EBCFD9;
            border-radius: 11px;
            font-size: 18px;
            font-weight: 800;
        }

        .vg-coverage-alert-title {
            color: var(--text-main);
            font-size: 14px;
            font-weight: 800;
            margin-bottom: 4px;
        }

        .vg-coverage-alert-help {
            color: var(--text-soft);
            font-size: 12px;
            line-height: 1.5;
            font-weight: 500;
        }

        .st-key-ouvrir_alertes_depuis_couverture button {
            min-height: 42px !important;
            white-space: nowrap !important;
            color: #FFFFFF !important;
            background: var(--3f-red) !important;
            border-color: var(--3f-red) !important;
        }

        .st-key-ouvrir_alertes_depuis_couverture button:hover {
            color: #FFFFFF !important;
            background: var(--3f-red-dark) !important;
            border-color: var(--3f-red-dark) !important;
        }


        /* TÉLÉCHARGEMENTS COMPACTS DES ÉQUIPEMENTS */
        .st-key-export_repartition_types_equipement,
        .st-key-export_couverture_equipements {
            display: flex !important;
            justify-content: flex-end !important;
        }

        .st-key-export_repartition_types_equipement button,
        .st-key-export_couverture_equipements button {
            min-height: 36px !important;
            width: auto !important;
            padding: 7px 12px !important;
            color: #A3184A !important;
            background: #FFFFFF !important;
            border: 1px solid #E7C8D6 !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            font-size: 11.5px !important;
            font-weight: 700 !important;
        }

        .st-key-export_repartition_types_equipement button:hover,
        .st-key-export_couverture_equipements button:hover {
            color: var(--3f-red) !important;
            background: #FFF7FA !important;
            border-color: var(--3f-red) !important;
        }

        @media screen and (max-width: 900px) {
            .vg-coverage-alert {
                align-items: stretch;
                flex-direction: column;
            }
        }

        @media screen and (max-width: 900px) {
            .vg-priority-grid {
                grid-template-columns: 1fr;
            }
        }

        @media screen and (max-width: 900px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }

            .vg-hero {
                padding: 24px 22px !important;
            }

            .vg-hero-title {
                font-size: 29px !important;
            }

            .st-key-dashboard_tabs div[role="radiogroup"] {
                gap: 16px !important;
                overflow-x: auto !important;
                flex-wrap: nowrap !important;
            }

            .vg-card,
            .vg-alert-card {
                height: auto !important;
                min-height: 148px !important;
            }

            .vg-table-summary {
                align-items: flex-start;
                flex-wrap: wrap;
                gap: 10px 14px;
            }

            .vg-table-summary-mode {
                margin-left: 0;
            }
        }

        /* =====================================================
           RESPONSIVITÉ GLOBALE CORRIGÉE
           Respecte la largeur disponible calculée par Streamlit.
        ===================================================== */

        /* Ne jamais utiliser vw ici : la sidebar Streamlit occupe déjà
           une partie de la fenêtre. */
        .block-container {
            width: 100% !important;
            max-width: 1680px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-top: clamp(.7rem, 1vw, 1.2rem) !important;
            padding-left: clamp(.8rem, 1.6vw, 1.8rem) !important;
            padding-right: clamp(.8rem, 1.6vw, 1.8rem) !important;
            padding-bottom: 2rem !important;
            box-sizing: border-box !important;
        }

        /* Typographie fluide, mais avec une amplitude limitée. */
        .vg-hero-title {
            font-size: clamp(27px, 1.8vw, 35px) !important;
        }

        .vg-section-title {
            font-size: clamp(18px, 1.15vw, 21px) !important;
        }

        .vg-section-subtitle {
            font-size: clamp(11.5px, .78vw, 13px) !important;
        }

        /* Cartes Couverture plus compactes. */
        .vg-coverage-reading-card {
            min-height: 0 !important;
            height: auto !important;
            padding: clamp(15px, 1.2vw, 19px) !important;
        }

        .vg-coverage-reading-question {
            min-height: 0 !important;
            margin-bottom: 11px !important;
        }

        .vg-coverage-reading-rate {
            font-size: clamp(29px, 2.3vw, 38px) !important;
        }

        .vg-coverage-reading-stats {
            gap: 8px !important;
        }

        .vg-coverage-reading-stat {
            padding: 9px 10px !important;
        }

        .vg-coverage-reading-stat-value {
            font-size: clamp(17px, 1.3vw, 21px) !important;
        }

        /* Composition du patrimoine compacte. */
        .vg-park-card {
            min-height: 76px !important;
            height: auto !important;
            padding: 11px 13px !important;
        }

        .vg-park-value {
            font-size: clamp(21px, 1.55vw, 27px) !important;
        }

        /* Les constats restent flexibles. */
        .vg-coverage-insights {
            grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        }

        .vg-coverage-insight {
            min-height: 76px !important;
            padding: 11px 12px !important;
        }

        /* Intensité contractuelle plus compacte. */
        .vg-intensity-distribution {
            padding: 14px 15px !important;
        }

        .vg-intensity-row {
            grid-template-columns: minmax(145px, .8fr) minmax(150px, 2fr) minmax(88px, auto) !important;
            gap: 9px !important;
            margin-bottom: 12px !important;
        }

        .vg-intensity-track {
            height: 10px !important;
        }

        .vg-intensity-kpi {
            min-height: 82px !important;
            height: auto !important;
            padding: 10px 12px !important;
        }

        /* Équipements plus compacts. */
        .vg-equipment-main-card {
            min-height: 0 !important;
            height: auto !important;
            padding: 15px !important;
        }

        .vg-equipment-ring {
            width: 104px !important;
            height: 104px !important;
        }

        .vg-equipment-kpi {
            min-height: 76px !important;
            height: auto !important;
            padding: 11px 12px !important;
        }

        /* Les graphiques et tableaux restent dans leur conteneur. */
        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
        }

        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container {
            max-width: 100% !important;
        }

        /* Les libellés longs peuvent revenir à la ligne. */
        .vg-intensity-label,
        .vg-equipment-type-label,
        .vg-coverage-reading-title,
        .vg-coverage-reading-question {
            overflow-wrap: anywhere !important;
        }

        /* Navigation : reste compacte, sans déborder. */
        .st-key-dashboard_tabs div[role="radiogroup"] {
            gap: clamp(12px, 1.5vw, 26px) !important;
        }

        /* =====================================================
           LAPTOP : 1024 à 1366 px environ
        ===================================================== */
        @media screen and (max-width: 1366px) {
            .block-container {
                max-width: 100% !important;
                padding-left: .9rem !important;
                padding-right: .9rem !important;
            }

            .vg-hero {
                padding: 21px 23px !important;
            }

            .vg-coverage-reading-card {
                padding: 15px !important;
            }

            .vg-coverage-reading-title {
                font-size: 15px !important;
            }

            .vg-coverage-reading-question {
                font-size: 10.5px !important;
            }

            .vg-coverage-insight {
                min-height: 72px !important;
            }

            .vg-equipment-type-row {
                grid-template-columns: minmax(120px, .7fr) minmax(130px, 1.8fr) minmax(95px, auto) !important;
            }
        }

        /* =====================================================
           PETIT LAPTOP / TABLETTE PAYSAGE
        ===================================================== */
        @media screen and (max-width: 1100px) {
            /* Les deux grandes cartes passent l'une sous l'autre seulement ici. */
            div[data-testid="stHorizontalBlock"]:has(.vg-coverage-reading-card) {
                flex-wrap: wrap !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.vg-coverage-reading-card) > div[data-testid="stColumn"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
            }

            .vg-coverage-insights {
                grid-template-columns: 1fr !important;
            }

            .vg-contract-intensity,
            .vg-equipment-summary,
            .vg-equipment-hero {
                grid-template-columns: 1fr !important;
            }

            .vg-intensity-row {
                grid-template-columns: minmax(130px, .75fr) minmax(120px, 1.6fr) minmax(82px, auto) !important;
            }

            .vg-alerts-hero-inner {
                align-items: flex-start !important;
                flex-direction: column !important;
                gap: 13px !important;
            }

            .vg-alerts-hero-stats {
                width: 100% !important;
                justify-content: flex-start !important;
            }
        }

        /* =====================================================
           TABLETTE / MOBILE
        ===================================================== */
        @media screen and (max-width: 760px) {
            .block-container {
                padding-top: .5rem !important;
                padding-left: .5rem !important;
                padding-right: .5rem !important;
            }

            .vg-hero {
                padding: 17px 15px !important;
                border-radius: 14px !important;
            }

            .vg-hero-title {
                font-size: 24px !important;
            }

            .vg-section-title {
                font-size: 18px !important;
            }

            .vg-step-header {
                align-items: flex-start !important;
                gap: 8px !important;
                margin-top: 16px !important;
            }

            .vg-step-number {
                width: 24px !important;
                height: 24px !important;
            }

            .vg-park-grid,
            .vg-coverage-kpi-grid,
            .vg-equipment-kpis,
            .vg-priority-grid {
                grid-template-columns: 1fr !important;
            }

            /* Les 3 cartes Streamlit de composition s'empilent sur mobile. */
            div[data-testid="stHorizontalBlock"]:has(.vg-park-card) {
                flex-wrap: wrap !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.vg-park-card) > div[data-testid="stColumn"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
            }

            /* Les 3 KPI d'intensité s'empilent. */
            div[data-testid="stHorizontalBlock"]:has(.vg-intensity-kpi) {
                flex-wrap: wrap !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.vg-intensity-kpi) > div[data-testid="stColumn"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
            }

            .vg-coverage-reading-stats {
                grid-template-columns: 1fr !important;
            }

            .vg-intensity-row,
            .vg-equipment-type-row {
                grid-template-columns: 1fr !important;
                gap: 5px !important;
            }

            .vg-intensity-value,
            .vg-equipment-type-value {
                text-align: left !important;
            }

            .vg-equipment-main-card,
            .vg-equipment-hero-main {
                flex-direction: column !important;
                align-items: flex-start !important;
            }

            .vg-equipment-ring {
                align-self: center !important;
            }

            .st-key-dashboard_tabs {
                overflow-x: auto !important;
            }

            .st-key-dashboard_tabs div[role="radiogroup"] {
                flex-wrap: nowrap !important;
                min-width: max-content !important;
                gap: 15px !important;
            }

            .st-key-dashboard_tabs div[role="radiogroup"] label {
                flex: 0 0 auto !important;
            }

            div[data-testid="stDataFrame"] {
                overflow-x: auto !important;
            }

            .stButton button,
            .stDownloadButton button {
                max-width: 100% !important;
                white-space: normal !important;
            }
        }

        /* =====================================================
           PETIT MOBILE
        ===================================================== */
        @media screen and (max-width: 430px) {
            .block-container {
                padding-left: .35rem !important;
                padding-right: .35rem !important;
            }

            .vg-coverage-summary-title {
                font-size: 18px !important;
            }

            .vg-coverage-summary-title strong {
                display: block !important;
                margin-bottom: 3px !important;
                font-size: 27px !important;
            }

            .vg-coverage-reading-main {
                align-items: flex-start !important;
                flex-direction: column !important;
            }

            .vg-coverage-context {
                align-items: flex-start !important;
                flex-direction: column !important;
            }

            .vg-coverage-context-pill {
                width: 100% !important;
                box-sizing: border-box !important;
            }

            .vg-alerts-hero,
            .vg-anomaly-hero {
                padding: 15px !important;
            }
        }

        /* =====================================================
           GRAND ÉCRAN
        ===================================================== */
        @media screen and (min-width: 1800px) {
            .block-container {
                max-width: 1760px !important;
            }

            .vg-coverage-reading-card {
                padding: 19px 20px !important;
            }

            .vg-coverage-reading-title {
                font-size: 17px !important;
            }

            .vg-park-card {
                min-height: 82px !important;
            }
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


def info(message: str):
    st.markdown(
        f'<div class="vg-info">{_safe(message)}</div>',
        unsafe_allow_html=True,
    )


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
    except Exception as exc:
        return False, str(exc)


def table_exists(conn, source: str) -> bool:
    return conn.execute(
        text("SELECT to_regclass(:source)"),
        {"source": source},
    ).scalar() is not None


def verifier_sources(conn):
    required = [
        SOURCE_ESI,
        SOURCE_CONTRATS,
        SOURCE_PRESTATIONS,
        SOURCE_EQUIPEMENTS_COUVERTURE,
        SOURCE_EQUIPEMENTS_CONTRATS,
        SOURCE_GLOBAL,
    ]
    return [source for source in required if not table_exists(conn, source)]


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


MOIS_FR_COURTS = {
    1: "janv.",
    2: "févr.",
    3: "mars",
    4: "avr.",
    5: "mai",
    6: "juin",
    7: "juil.",
    8: "août",
    9: "sept.",
    10: "oct.",
    11: "nov.",
    12: "déc.",
}


def libelle_mois_fr(date_value) -> str:
    date_value = pd.Timestamp(date_value)
    return f"{MOIS_FR_COURTS[date_value.month]} {date_value.year}"


PLOTLY_FR_DICTIONARY = {
    "Download plot as a PNG": "Télécharger en PNG",
    "Download plot": "Télécharger le graphique",
    "Zoom": "Zoomer",
    "Pan": "Déplacer",
    "Zoom in": "Zoom avant",
    "Zoom out": "Zoom arrière",
    "Autoscale": "Ajustement automatique",
    "Reset axes": "Réinitialiser les axes",
    "Reset camera to default": "Réinitialiser la vue",
    "Reset camera to last save": "Restaurer la dernière vue",
    "Orbit rotation": "Rotation orbitale",
    "Turntable rotation": "Rotation horizontale",
    "Show closest data on hover": "Afficher la donnée la plus proche",
    "Compare data on hover": "Comparer les données",
    "Toggle Spike Lines": "Afficher ou masquer les lignes de repère",
    "Snapshot succeeded": "Image téléchargée",
    "Sorry, there was a problem downloading your snapshot!": (
        "Le téléchargement de l’image a échoué."
    ),
}


def config_plotly(nom_fichier: str, afficher_barre: bool = True) -> dict:
    return {
        "displayModeBar": afficher_barre,
        "displaylogo": False,
        "responsive": True,
        "locale": "fr",
        "locales": {
            "fr": {
                "dictionary": PLOTLY_FR_DICTIONARY,
                "format": {
                    "days": [
                        "dimanche", "lundi", "mardi", "mercredi",
                        "jeudi", "vendredi", "samedi",
                    ],
                    "shortDays": ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."],
                    "months": [
                        "janvier", "février", "mars", "avril", "mai", "juin",
                        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
                    ],
                    "shortMonths": [
                        "janv.", "févr.", "mars", "avr.", "mai", "juin",
                        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
                    ],
                    "date": "%d/%m/%Y",
                },
            }
        },
        "modeBarButtonsToRemove": [
            "select2d",
            "lasso2d",
            "autoScale2d",
            "toggleSpikelines",
        ],
        "toImageButtonOptions": {
            "format": "png",
            "filename": nom_fichier,
            "height": 900,
            "width": 1600,
            "scale": 2,
        },
    }


def graduations_periodes(evolution: pd.DataFrame, maximum: int = 6):
    periodes = evolution["Période"].astype(str).tolist()
    if len(periodes) <= maximum:
        return periodes

    pas = max(1, (len(periodes) - 1) // (maximum - 1))
    graduations = periodes[::pas]
    if graduations[-1] != periodes[-1]:
        graduations.append(periodes[-1])
    return graduations[:maximum - 1] + [periodes[-1]] if len(graduations) > maximum else graduations


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


# =====================================================
# NORMALISATION DES TYPES D'ÉQUIPEMENT
# =====================================================

# Ce dictionnaire contient uniquement les regroupements métier validés.
# La clé est une version technique sans accent et en minuscules.
# La valeur est le libellé final affiché dans le dashboard.
EQUIPMENT_TYPE_ALIASES = {
    # Ascenseurs
    "lift": "Ascenseur",
    "lifts": "Ascenseur",
    "ascenseur": "Ascenseur",
    "ascenseurs": "Ascenseur",

    # Fermetures automatiques
    "fermeture automatique": "Fermeture automatique",
    "fermetures automatiques": "Fermeture automatique",

    # Chauffage collectif
    "installation de chauffage collectif": "Installation de chauffage collectif",
    "installations de chauffage collectif": "Installation de chauffage collectif",
    "chauffage collectif": "Installation de chauffage collectif",

    # Ventilation
    "ventilation": "Ventilation",

    # VMC
    "vmc sanitaire": "VMC sanitaire",
    "vmc sanitaires": "VMC sanitaire",

    # Aires de jeux
    "aire de jeux": "Aire de jeux",
    "aires de jeux": "Aire de jeux",
}


def cle_normalisation_texte(value) -> str:
    """
    Produit une clé stable pour comparer des libellés :
    - espaces nettoyés ;
    - casse ignorée ;
    - accents retirés ;
    - séparateurs harmonisés.
    """
    if value is None or pd.isna(value):
        return ""

    texte = str(value).strip()
    if not texte:
        return ""

    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )
    texte = texte.lower()

    # Harmonise les séparateurs et les espaces multiples.
    texte = re.sub(r"[_/\\|-]+", " ", texte)
    texte = re.sub(r"\s+", " ", texte).strip()

    return texte


def formater_type_equipement_inconnu(value) -> str:
    """
    Formate proprement une valeur non présente dans le dictionnaire,
    sans inventer de regroupement métier.
    """
    if value is None or pd.isna(value):
        return "Non renseigné"

    texte = re.sub(r"\s+", " ", str(value).strip())
    if not texte:
        return "Non renseigné"

    # Préserve les acronymes fréquents.
    acronymes = {
        "vmc": "VMC",
        "cta": "CTA",
        "ecs": "ECS",
        "ssi": "SSI",
        "vri": "VRI",
        "erp": "ERP",
    }

    mots = []
    for index, mot in enumerate(texte.lower().split()):
        mot_cle = cle_normalisation_texte(mot)

        if mot_cle in acronymes:
            mots.append(acronymes[mot_cle])
        elif index == 0:
            mots.append(mot.capitalize())
        else:
            mots.append(mot)

    return " ".join(mots)


def normaliser_type_equipement(value) -> str:
    """
    Retourne le libellé normalisé d'un type d'équipement.

    Les alias connus sont regroupés explicitement.
    Les autres valeurs sont seulement nettoyées et formatées :
    aucun regroupement métier n'est inventé.
    """
    cle = cle_normalisation_texte(value)

    if not cle or cle in {
        "nan",
        "none",
        "null",
        "undefined",
        "non renseigne",
    }:
        return "Non renseigné"

    if cle in EQUIPMENT_TYPE_ALIASES:
        return EQUIPMENT_TYPE_ALIASES[cle]

    return formater_type_equipement_inconnu(value)


def normaliser_equipements(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute une colonne unique `equipment_type_normalise`.

    Priorité :
    1. equipment_type, car c'est le type métier ;
    2. equipment_asset_type seulement en repli.

    Les colonnes sources sont conservées intactes.
    """
    if df.empty:
        return df.copy()

    df = nettoyer_df(df)

    if "equipment_type" in df.columns:
        source_type = df["equipment_type"].copy()
    else:
        source_type = pd.Series(pd.NA, index=df.index, dtype="object")

    if "equipment_asset_type" in df.columns:
        asset_type = df["equipment_asset_type"].copy()

        source_vide = (
            source_type.isna()
            | source_type.astype(str).str.strip().isin(
                ["", "nan", "None", "<NA>", "Non renseigné"]
            )
        )
        source_type = source_type.where(~source_vide, asset_type)

    df["equipment_type_normalise"] = source_type.map(
        normaliser_type_equipement
    )

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


def normaliser_prestations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = df.copy()

    ref_cols = [
        "contract_reference_3f",
        "contract_reference_prestataire",
        "contract_id_intent",
        "third_party_id",
        "third_party_reference",
        "service_contract_reference",
        "service_code_id_intent",
        "service_code_reference_3f",
        "service_code_reference_prestataire",
    ]

    text_cols = [
        "contract_label",
        "contract_description",
        "contract_topic",
        "contract_status",
        "third_party_label",
        "service_code_label",
        "service_code_description",
        "service_code_work_type",
        "service_code_fixed_rate",
        "sla_periodicity_unit",
        "sla_estimated_intervention_duration_value",
        "sla_estimated_intervention_duration_unit",
        "sla_max_time_to_intervention_unit",
        "sla_max_time_to_recovery_unit",
    ]

    date_cols = [
        "contract_start_date",
        "contract_end_date",
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_last_update_date",
    ]

    num_cols = [
        "contract_found",
        "contract_active_intent",
        "contract_active_end_date_expired",
        "service_code_critical_level",
        "sla_periodicity_value",
        "sla_max_time_to_intervention_value",
        "sla_max_time_to_recovery_value",
        "has_service_code",
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
                .replace({
                    "": "Non renseigné",
                    "nan": "Non renseigné",
                    "undefined": "Non renseigné",
                })
            )

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

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

    serie = df[colonne].dropna().astype(str).str.strip()
    serie = serie[~serie.isin(["", "nan", "None", "<NA>", "Non renseigné"])]
    return serie.unique().tolist()


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
            df_prestations = pd.read_sql_query(text(f"SELECT * FROM {SOURCE_PRESTATIONS}"), conn)
            df_equipements_couverture = pd.read_sql_query(
                text(f"SELECT * FROM {SOURCE_EQUIPEMENTS_COUVERTURE}"), conn
            )
            df_equipements_contrats = pd.read_sql_query(
                text(f"SELECT * FROM {SOURCE_EQUIPEMENTS_CONTRATS}"), conn
            )

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
            if table_exists(conn, SOURCE_ALERTES):
                df_alertes = pd.read_sql_query(
                    text(f"SELECT * FROM {SOURCE_ALERTES}"),
                    conn,
                )
            else:
                df_alertes = pd.DataFrame()

    except SQLAlchemyError as exc:
        raise RuntimeError(f"Erreur PostgreSQL : {exc}") from exc

    df_esi = nettoyer_df(df_esi)
    df_contrats = normaliser_contrats(df_contrats)
    df_prestations = normaliser_prestations(df_prestations)
    df_equipements_couverture = normaliser_equipements(
        df_equipements_couverture
    )
    df_equipements_contrats = normaliser_equipements(
        df_equipements_contrats
    )
    df_creations = normaliser_creations(df_creations)
    df_alertes = (
        nettoyer_df(df_alertes)
        if not df_alertes.empty
        else df_alertes
            )
    df_qualite = nettoyer_df(df_qualite) if not df_qualite.empty else df_qualite
    if not df_qualite.empty and "contract_end_date" in df_qualite.columns:
        df_qualite["contract_end_date"] = pd.to_datetime(
            df_qualite["contract_end_date"], errors="coerce"
        )
    df_qualite_resume = nettoyer_df(df_qualite_resume) if not df_qualite_resume.empty else df_qualite_resume

    return (
        df_global,
        df_esi,
        df_contrats,
        df_prestations,
        df_equipements_couverture,
        df_equipements_contrats,
        df_creations,
        df_qualite,
        df_qualite_resume,
        df_alertes,
    )



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


def filtre_contrat_est_actif(
    filtres_selectionnes,
    statut_selectionne,
    df_esi,
    df_esi_filtre,
    df_contrats,
    df_contrats_filtre,
):
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
        label_visibility="collapsed",
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


def filtrer_esi_depuis_contrats(
    df_esi: pd.DataFrame,
    df_contrats: pd.DataFrame,
    appliquer_filtre_contrat: bool,
):
    if not appliquer_filtre_contrat:
        return df_esi.copy()

    if df_contrats.empty:
        return df_esi.iloc[0:0].copy()

    refs = liste_refs_valides(df_contrats, "esi_reference")
    if not refs:
        return df_esi.iloc[0:0].copy()

    return df_esi[df_esi["esi_reference"].isin(refs)].copy()


def filtrer_prestations_depuis_contrats(
    df_prestations: pd.DataFrame,
    df_contrats_kpi: pd.DataFrame,
    perimetre_filtre_actif: bool,
    statut_selectionne,
) -> pd.DataFrame:
    if df_prestations.empty:
        return df_prestations.copy()

    df = df_prestations.copy()

    if perimetre_filtre_actif:
        refs = set(liste_refs_valides(df_contrats_kpi, "contract_reference"))
        if not refs:
            return df.iloc[0:0].copy()
        if "contract_reference_3f" not in df.columns:
            return df.iloc[0:0].copy()
        df = df[df["contract_reference_3f"].isin(refs)].copy()

    if statut_selectionne == "active":
        df = df[df["contract_status_clean"] == "active"].copy()
    elif statut_selectionne == "inactive":
        df = df[df["contract_status_clean"] != "active"].copy()

    return df


def construire_contrats_uniques_source(
    df_prestations: pd.DataFrame,
    df_contrats_rattaches: pd.DataFrame,
) -> pd.DataFrame:
    """
    Retourne une ligne par contrat Intent.

    La source prestations contient les 576 contrats. Les données de rattachement
    sont utilisées uniquement en complément lorsqu'elles existent, sans créer
    artificiellement de rattachement pour les 9 contrats non rattachés.
    """
    if df_prestations.empty:
        return (
            df_contrats_rattaches.drop_duplicates("contract_reference").copy()
            if not df_contrats_rattaches.empty
            else pd.DataFrame()
        )

    source = df_prestations.copy()
    if "contract_reference_3f" not in source.columns:
        return pd.DataFrame()

    source = source[source["contract_reference_3f"].notna()].copy()
    source = source.sort_values(
        ["contract_reference_3f", "contract_last_update_date"]
        if "contract_last_update_date" in source.columns
        else ["contract_reference_3f"],
        na_position="last",
    ).drop_duplicates("contract_reference_3f", keep="last")

    source = source.rename(
        columns={"contract_reference_3f": "contract_reference"}
    )

    # On complète seulement avec les informations patrimoniales réellement présentes.
    if not df_contrats_rattaches.empty and "contract_reference" in df_contrats_rattaches.columns:
        rattachements = (
            df_contrats_rattaches.sort_values(
                [c for c in ["contract_reference", "esi_reference"] if c in df_contrats_rattaches.columns],
                na_position="last",
            )
            .drop_duplicates("contract_reference")
            .copy()
        )
        colonnes_rattachement = [
            c for c in [
                "contract_reference", "societe", "agence", "groupe",
                "secteur", "esi_reference", "esi_label",
            ]
            if c in rattachements.columns
        ]
        source = source.merge(
            rattachements[colonnes_rattachement],
            on="contract_reference",
            how="left",
        )

    return source


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



def contrats_actifs_expires_depuis_intent(
    df_prestations: pd.DataFrame,
    references_contrats_autorisees: set[str] | None = None,
) -> pd.DataFrame:
    """
    Construit la liste officielle des contrats actifs expirés depuis
    dashboard.contrats_prestations.

    La colonne contract_active_end_date_expired est calculée dans la source
    Intent. Une seule ligne est conservée par référence contrat, même lorsque
    le contrat possède plusieurs prestations.
    """
    if df_prestations is None or df_prestations.empty:
        return pd.DataFrame()

    if "contract_reference_3f" not in df_prestations.columns:
        return pd.DataFrame()

    if "contract_active_end_date_expired" not in df_prestations.columns:
        return pd.DataFrame()

    df = df_prestations.copy()

    df["contract_reference_3f"] = (
        df["contract_reference_3f"]
        .astype("string")
        .str.strip()
    )

    flag_expire = pd.to_numeric(
        df["contract_active_end_date_expired"],
        errors="coerce",
    ).fillna(0)

    df = df[
        df["contract_reference_3f"].notna()
        & df["contract_reference_3f"].ne("")
        & flag_expire.eq(1)
    ].copy()

    if references_contrats_autorisees is not None:
        df = df[
            df["contract_reference_3f"].astype(str).isin(
                references_contrats_autorisees
            )
        ].copy()

    # Conserver la ligne la plus récente lorsque plusieurs prestations
    # existent pour un même contrat.
    colonnes_tri = ["contract_reference_3f"]

    if "contract_last_update_date" in df.columns:
        df["contract_last_update_date"] = pd.to_datetime(
            df["contract_last_update_date"],
            errors="coerce",
        )
        colonnes_tri.append("contract_last_update_date")

    df = (
        df.sort_values(colonnes_tri, na_position="first")
        .drop_duplicates("contract_reference_3f", keep="last")
        .copy()
    )

    # Harmoniser le nom de la référence avec les tableaux contrats existants.
    df["contract_reference"] = df["contract_reference_3f"]

    return df.reset_index(drop=True)

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


def serie_numerique(df: pd.DataFrame, colonne: str) -> pd.Series:
    if colonne not in df.columns:
        return pd.Series(0, index=df.index, dtype="float64")
    return pd.to_numeric(df[colonne], errors="coerce").fillna(0)


def global_value(df_global: pd.DataFrame, col: str, default=0):
    if df_global.empty or col not in df_global.columns:
        return default
    try:
        return df_global.iloc[0][col]
    except Exception:
        return default




# =====================================================
# MÉTIERS ET ÉQUIPEMENTS
# =====================================================


def filtrer_table_par_esi(
    dataframe: pd.DataFrame,
    df_esi_perimetre: pd.DataFrame,
) -> pd.DataFrame:
    """Restreint une table au périmètre réel des ESI sélectionnés."""
    if dataframe.empty or "esi_reference" not in dataframe.columns:
        return dataframe.copy()

    refs = set(liste_refs_valides(df_esi_perimetre, "esi_reference"))
    if not refs:
        return dataframe.iloc[0:0].copy()

    return dataframe[dataframe["esi_reference"].isin(refs)].copy()


def construire_presence_metiers(
    df_contrats: pd.DataFrame,
    total_esi: int,
    tous_les_metiers: list[str],
    top_n: int = 15,
) -> pd.DataFrame:
    """
    Affiche tous les métiers de référence,
    même lorsqu'ils sont absents du périmètre filtré.
    """

    colonnes = ["Métier", "ESI", "Taux"]

    metiers_reference = (
        pd.DataFrame(
            {
                "Métier": tous_les_metiers
            }
        )
        .drop_duplicates()
    )

    if (
        df_contrats.empty
        or "esi_reference" not in df_contrats.columns
        or "contract_topic" not in df_contrats.columns
    ):
        metiers_reference["ESI"] = 0
        metiers_reference["Taux"] = 0.0

        return (
            metiers_reference
            .sort_values(
                ["ESI", "Métier"],
                ascending=[True, True],
            )
            .reset_index(drop=True)
        )

    df = df_contrats[
        df_contrats["esi_reference"].notna()
    ].copy()

    df["contract_topic"] = (
        df["contract_topic"]
        .fillna("Non renseigné")
        .astype(str)
        .str.strip()
        .replace("", "Non renseigné")
    )

    resultat_perimetre = (
        df.groupby(
            "contract_topic",
            as_index=False,
        )
        .agg(
            ESI=("esi_reference", "nunique")
        )
        .rename(
            columns={
                "contract_topic": "Métier"
            }
        )
    )

    resultat = metiers_reference.merge(
        resultat_perimetre,
        on="Métier",
        how="left",
    )

    resultat["ESI"] = (
        resultat["ESI"]
        .fillna(0)
        .astype(int)
    )

    resultat["Taux"] = (
        resultat["ESI"]
        .div(total_esi if total_esi else 1)
        .mul(100)
        .round(1)
    )

    return (
        resultat
        .sort_values(
            ["ESI", "Métier"],
            ascending=[True, True],
        )
        .tail(top_n)
        .reset_index(drop=True)
    )


def construire_repartition_types_equipement(
    df_equipements: pd.DataFrame,
    statut: str | None = "active",
    top_n: int = 12,
) -> pd.DataFrame:
    """
    Répartition du parc et couverture par type d'équipement.

    Un équipement est compté une seule fois, même s'il possède
    plusieurs lignes ou plusieurs liens contractuels.
    """
    colonnes = [
        "Type d’équipement",
        "Équipements",
        "Équipements couverts",
        "Équipements non couverts",
        "Taux de couverture",
        "ESI",
        "Part du parc",
    ]

    if (
        df_equipements.empty
        or "equipment_reference" not in df_equipements.columns
    ):
        return pd.DataFrame(columns=colonnes)

    colonne_type = next(
        (
            candidate
            for candidate in [
                "equipment_type_normalise",
                "equipment_type",
                "equipment_asset_type",
            ]
            if candidate in df_equipements.columns
        ),
        None,
    )

    if colonne_type is None:
        return pd.DataFrame(columns=colonnes)

    df = df_equipements.copy()

    if colonne_type == "equipment_type_normalise":
        df["Type d’équipement"] = (
            df[colonne_type]
            .fillna("Non renseigné")
            .astype(str)
            .str.strip()
            .replace(
                {
                    "": "Non renseigné",
                    "nan": "Non renseigné",
                    "None": "Non renseigné",
                    "<NA>": "Non renseigné",
                }
            )
        )
    else:
        df["Type d’équipement"] = (
            df[colonne_type]
            .map(normaliser_type_equipement)
            .fillna("Non renseigné")
        )

    if statut == "active":
        couverture = (
            serie_numerique(df, "equipment_covered_valid") > 0
        )
    elif statut == "inactive":
        couverture = (
            serie_numerique(df, "nb_contrats_inactifs") > 0
        )
    else:
        couverture = (
            serie_numerique(df, "equipment_has_contract_link") > 0
        )

    df["_equipement_couvert"] = couverture.astype(int)

    # Consolidation préalable : une seule ligne par équipement et par type.
    aggregations_equipement = {
        "_equipement_couvert": "max",
    }
    if "esi_reference" in df.columns:
        aggregations_equipement["esi_reference"] = "first"

    equipements_uniques = (
        df.groupby(
            ["Type d’équipement", "equipment_reference"],
            as_index=False,
            dropna=False,
        )
        .agg(aggregations_equipement)
    )

    aggregations_type = {
        "equipment_reference": "nunique",
        "_equipement_couvert": "sum",
    }
    if "esi_reference" in equipements_uniques.columns:
        aggregations_type["esi_reference"] = "nunique"

    resultat = (
        equipements_uniques
        .groupby("Type d’équipement", as_index=False)
        .agg(aggregations_type)
        .rename(
            columns={
                "equipment_reference": "Équipements",
                "_equipement_couvert": "Équipements couverts",
                "esi_reference": "ESI",
            }
        )
    )

    if "ESI" not in resultat.columns:
        resultat["ESI"] = 0

    resultat["Équipements"] = (
        pd.to_numeric(resultat["Équipements"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    resultat["Équipements couverts"] = (
        pd.to_numeric(
            resultat["Équipements couverts"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )
    resultat["Équipements non couverts"] = (
        resultat["Équipements"]
        - resultat["Équipements couverts"]
    ).clip(lower=0)

    resultat["Taux de couverture"] = (
        resultat["Équipements couverts"]
        .div(resultat["Équipements"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
    )

    total = int(resultat["Équipements"].sum())
    resultat["Part du parc"] = (
        resultat["Équipements"] / total * 100
        if total
        else 0.0
    )

    resultat = resultat.sort_values(
        ["Équipements", "Type d’équipement"],
        ascending=[False, True],
    )

    if len(resultat) > top_n:
        principaux = resultat.head(top_n - 1).copy()
        autres = resultat.iloc[top_n - 1:].copy()

        total_autres = int(autres["Équipements"].sum())
        couverts_autres = int(
            autres["Équipements couverts"].sum()
        )

        ligne_autres = pd.DataFrame(
            {
                "Type d’équipement": ["Autres types"],
                "Équipements": [total_autres],
                "Équipements couverts": [couverts_autres],
                "Équipements non couverts": [
                    max(total_autres - couverts_autres, 0)
                ],
                "Taux de couverture": [
                    (
                        couverts_autres / total_autres * 100
                        if total_autres
                        else 0.0
                    )
                ],
                "ESI": [int(autres["ESI"].sum())],
                "Part du parc": [
                    float(autres["Part du parc"].sum())
                ],
            }
        )

        resultat = pd.concat(
            [principaux, ligne_autres],
            ignore_index=True,
        )

    return resultat.sort_values(
        "Équipements",
        ascending=True,
    ).reset_index(drop=True)


def construire_couverture_reelle_equipements(
    df_equipements: pd.DataFrame,
    statut: str | None,
) -> pd.DataFrame:
    """
    Mesure directement la part des équipements avec ou sans contrat rattaché.

    Tous :
        au moins un contrat directement rattaché à l'équipement.
    Actifs :
        au moins un contrat actif valide directement rattaché.
    Inactifs :
        au moins un contrat inactif directement rattaché.
    """
    colonnes = ["Couverture", "Équipements", "Taux"]

    if (
        df_equipements.empty
        or "equipment_reference" not in df_equipements.columns
    ):
        return pd.DataFrame(columns=colonnes)

    df = (
        df_equipements[
            df_equipements["equipment_reference"].notna()
        ]
        .drop_duplicates("equipment_reference")
        .copy()
    )

    if statut == "active":
        couvert = (
            serie_numerique(df, "equipment_covered_valid") > 0
        )
    elif statut == "inactive":
        couvert = (
            serie_numerique(df, "nb_contrats_inactifs") > 0
        )
    else:
        couvert = (
            serie_numerique(df, "equipment_has_contract_link") > 0
        )

    df["_couvert"] = couvert.astype(int)

    nb_couverts = int(df["_couvert"].sum())
    total = int(df["equipment_reference"].nunique())
    nb_non_couverts = max(total - nb_couverts, 0)

    resultat = pd.DataFrame(
        {
            "Couverture": [
                "Équipements avec contrat",
                "Équipements sans contrat",
            ],
            "Équipements": [
                nb_couverts,
                nb_non_couverts,
            ],
        }
    )
    resultat["Taux"] = (
        resultat["Équipements"] / total * 100
        if total
        else 0.0
    )
    return resultat




# =====================================================
# ÉVOLUTION DES CONTRATS
# =====================================================


def preparer_base_evolution_contrats(
    df_contrats: pd.DataFrame,
    df_prestations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construit une ligne par contrat avec les dates utiles à l'évolution.

    Priorité donnée à dashboard.contrats_prestations, car cette source contient
    les dates de création et de désactivation Intent. Les colonnes manquantes
    sont complétées depuis dashboard.contrats_patrimoine.
    """
    colonnes_sortie = [
        "contract_reference",
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_end_date",
        "contract_status_clean",
    ]

    base = pd.DataFrame(columns=colonnes_sortie)

    if not df_prestations.empty and "contract_reference_3f" in df_prestations.columns:
        p = df_prestations.copy()
        p["contract_reference"] = p["contract_reference_3f"].astype("string")

        for col in [
            "contract_creation_date",
            "contract_deactivation_date",
            "contract_end_date",
        ]:
            if col not in p.columns:
                p[col] = pd.NaT
            p[col] = pd.to_datetime(p[col], errors="coerce")

        if "contract_status_clean" not in p.columns:
            p["contract_status_clean"] = (
                p.get("contract_status", "")
                .fillna("")
                .astype(str)
                .str.lower()
                .str.strip()
            )

        base = (
            p.sort_values(
                ["contract_reference", "contract_last_update_date"]
                if "contract_last_update_date" in p.columns
                else ["contract_reference"],
                na_position="last",
            )
            .drop_duplicates("contract_reference", keep="last")
            [colonnes_sortie]
            .copy()
        )

    if not df_contrats.empty and "contract_reference" in df_contrats.columns:
        c = df_contrats.copy()

        for col in ["contract_end_date"]:
            if col not in c.columns:
                c[col] = pd.NaT
            c[col] = pd.to_datetime(c[col], errors="coerce")

        if "contract_status_clean" not in c.columns:
            c["contract_status_clean"] = (
                c.get("contract_status", "")
                .fillna("")
                .astype(str)
                .str.lower()
                .str.strip()
            )

        c = (
            c.sort_values("contract_reference")
            .drop_duplicates("contract_reference")
            .copy()
        )

        colonnes_c = [
            "contract_reference",
            "contract_end_date",
            "contract_status_clean",
        ]
        c = c[colonnes_c]

        if base.empty:
            base = c.copy()
            base["contract_creation_date"] = pd.NaT
            base["contract_deactivation_date"] = pd.NaT
            base = base[colonnes_sortie]
        else:
            base = base.merge(
                c,
                on="contract_reference",
                how="outer",
                suffixes=("", "_patrimoine"),
            )

            base["contract_end_date"] = base["contract_end_date"].fillna(
                base.get("contract_end_date_patrimoine")
            )
            base["contract_status_clean"] = (
                base["contract_status_clean"]
                .replace("", pd.NA)
                .fillna(base.get("contract_status_clean_patrimoine"))
                .fillna("")
            )

            base = base[colonnes_sortie]

    for col in [
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_end_date",
    ]:
        if col not in base.columns:
            base[col] = pd.NaT

        base[col] = (
            pd.to_datetime(
                base[col],
                errors="coerce",
                utc=True,
            )
            .dt.tz_localize(None)
        )

    base["contract_reference"] = (
        base["contract_reference"]
        .astype("string")
        .str.strip()
    )

    return base[
        base["contract_reference"].notna()
        & (base["contract_reference"] != "")
    ].drop_duplicates("contract_reference")


def construire_periodes_continues(
    base: pd.DataFrame,
    granularite: str,
    nb_mois: int,
) -> pd.DataFrame:
    aujourd_hui = pd.Timestamp(aujourd_hui_france())

    if granularite == "Annuel":
        annee_fin = aujourd_hui.year
        nb_annees = max(2, int((nb_mois + 11) // 12))
        annees = list(range(annee_fin - nb_annees + 1, annee_fin + 1))

        periodes = pd.DataFrame(
            {
                "periode_debut": [pd.Timestamp(year=a, month=1, day=1) for a in annees],
                "periode_fin": [pd.Timestamp(year=a, month=12, day=31) for a in annees],
                "libelle": [str(a) for a in annees],
            }
        )
        periodes.loc[
            periodes["periode_fin"] > aujourd_hui,
            "periode_fin",
        ] = aujourd_hui
        return periodes

    mois_fin = aujourd_hui.to_period("M").to_timestamp()
    mois_debut = mois_fin - pd.DateOffset(months=nb_mois - 1)
    mois = pd.date_range(mois_debut, mois_fin, freq="MS")

    return pd.DataFrame(
        {
            "periode_debut": mois,
            "periode_fin": mois + pd.offsets.MonthEnd(1),
            "libelle": [libelle_mois_fr(m) for m in mois],
        }
    )


def construire_evolution_contrats(
    df_contrats: pd.DataFrame,
    df_prestations: pd.DataFrame,
    granularite: str,
    nb_mois: int,
) -> pd.DataFrame:
    base = preparer_base_evolution_contrats(
        df_contrats=df_contrats,
        df_prestations=df_prestations,
    )
    periodes = construire_periodes_continues(
        base=base,
        granularite=granularite,
        nb_mois=nb_mois,
    )

    lignes = []

    for row in periodes.itertuples(index=False):
        debut = pd.Timestamp(row.periode_debut)
        fin = pd.Timestamp(row.periode_fin)

        crees = int(
            (
                base["contract_creation_date"].notna()
                & (base["contract_creation_date"] >= debut)
                & (base["contract_creation_date"] <= fin)
            ).sum()
        )

        desactives = int(
            (
                base["contract_deactivation_date"].notna()
                & (base["contract_deactivation_date"] >= debut)
                & (base["contract_deactivation_date"] <= fin)
            ).sum()
        )

        existe_fin = (
            base["contract_creation_date"].isna()
            | (base["contract_creation_date"] <= fin)
        )

        actif_fin = (
            existe_fin
            & (
                base["contract_deactivation_date"].isna()
                | (base["contract_deactivation_date"] > fin)
            )
        )

        inactif_fin = (
            existe_fin
            & base["contract_deactivation_date"].notna()
            & (base["contract_deactivation_date"] <= fin)
        )

        actif_expire_fin = (
            actif_fin
            & base["contract_end_date"].notna()
            & (base["contract_end_date"] < fin)
        )

        lignes.append(
            {
                "periode_debut": debut,
                "periode_fin": fin,
                "Période": row.libelle,
                "Créés": crees,
                "Désactivés": desactives,
                "Contrats actifs": int(actif_fin.sum()),
                "Contrats inactifs": int(inactif_fin.sum()),
                "Actifs avec date de fin dépassée": int(actif_expire_fin.sum()),
            }
        )

    return pd.DataFrame(lignes)
# =====================================================
# ÉVOLUTION MENSUELLE DE LA COUVERTURE DES ESI
# =====================================================


def _dates_sans_fuseau(serie: pd.Series) -> pd.Series:
    return (
        pd.to_datetime(
            serie,
            errors="coerce",
            utc=True,
        )
        .dt.tz_convert(None)
    )


def construire_evolution_couverture_esi(
    df_esi_base: pd.DataFrame,
    df_contrats_base: pd.DataFrame,
    df_prestations: pd.DataFrame,
    maille: str,
    nb_mois: int,
    metier: str | None = None,
) -> pd.DataFrame:
    """
    Reconstruit, à la fin de chaque mois, le nombre et le taux
    d'ESI couverts par au moins un contrat actif.

    Le total d'ESI correspond au parc actuel du périmètre filtré.
    """

    colonnes_sortie = [
        "Mois",
        "Période",
        "Maille",
        "Entité",
        "ESI totaux",
        "ESI couverts",
        "ESI non couverts",
        "Taux de couverture",
    ]

    if (
        df_esi_base.empty
        or "esi_reference" not in df_esi_base.columns
        or maille not in df_esi_base.columns
    ):
        return pd.DataFrame(columns=colonnes_sortie)

    # -------------------------------------------------
    # 1. Population actuelle des ESI par maille
    # -------------------------------------------------

    esi = dedupliquer_esi(df_esi_base)

    esi = esi[
        esi["esi_reference"].notna()
    ].copy()

    esi["esi_reference"] = (
        esi["esi_reference"]
        .astype("string")
        .str.strip()
    )

    esi["Entité"] = (
        esi[maille]
        .fillna("Non renseigné")
        .astype(str)
        .str.strip()
        .replace(
            {
                "": "Non renseigné",
                "nan": "Non renseigné",
                "None": "Non renseigné",
                "<NA>": "Non renseigné",
            }
        )
    )

    esi = esi[
        esi["esi_reference"].notna()
        & (esi["esi_reference"] != "")
    ].copy()

    if esi.empty:
        return pd.DataFrame(columns=colonnes_sortie)

    population = (
        esi.groupby(
            "Entité",
            as_index=False,
        )["esi_reference"]
        .nunique()
        .rename(
            columns={
                "esi_reference": "ESI totaux",
            }
        )
    )

    # -------------------------------------------------
    # 2. Création des 12, 24 ou 36 mois continus
    # -------------------------------------------------

    periodes = construire_periodes_continues(
        base=pd.DataFrame(),
        granularite="Mensuel",
        nb_mois=int(nb_mois),
    ).copy()

    # Pour le mois actuel, la date de photographie est aujourd'hui,
    # pas le dernier jour futur du mois.
    aujourd_hui = pd.Timestamp(
        aujourd_hui_france()
    )

    periodes.loc[
        periodes["periode_fin"] > aujourd_hui,
        "periode_fin",
    ] = aujourd_hui

    # -------------------------------------------------
    # 3. Relations contrat x ESI
    # -------------------------------------------------

    colonnes_contrats = [
        colonne
        for colonne in [
            "contract_reference",
            "esi_reference",
            "contract_topic",
            "contract_start_date",
            "contract_end_date",
        ]
        if colonne in df_contrats_base.columns
    ]

    if not {
        "contract_reference",
        "esi_reference",
    }.issubset(colonnes_contrats):
        relations = pd.DataFrame(
            columns=[
                "contract_reference",
                "esi_reference",
                "contract_start_date",
                "contract_end_date",
            ]
        )
    else:
        relations = df_contrats_base[
            colonnes_contrats
        ].copy()
  

    # Dans le mode par métier, seuls les contrats du métier
    # sélectionné participent au calcul de la couverture.
    if metier is not None:
        if "contract_topic" not in relations.columns:
            return pd.DataFrame(
                columns=colonnes_sortie
            )

        relations["contract_topic"] = (
            relations["contract_topic"]
            .fillna("Non renseigné")
            .astype(str)
            .str.strip()
        )

        relations = relations[
            relations["contract_topic"] == metier
        ].copy()

    for colonne in [
        "contract_start_date",
        "contract_end_date",
    ]:

        if colonne not in relations.columns:
            relations[colonne] = pd.NaT

        relations[colonne] = _dates_sans_fuseau(
            relations[colonne]
        )

    relations["contract_reference"] = (
        relations["contract_reference"]
        .astype("string")
        .str.strip()
    )

    relations["esi_reference"] = (
        relations["esi_reference"]
        .astype("string")
        .str.strip()
    )

    relations = relations[
        relations["contract_reference"].notna()
        & relations["esi_reference"].notna()
        & relations["esi_reference"].isin(
            esi["esi_reference"]
        )
    ].drop_duplicates(
        [
            "contract_reference",
            "esi_reference",
        ]
    )

    # -------------------------------------------------
    # 4. Dates provenant de contrats_prestations
    # -------------------------------------------------

    dates_contrats = preparer_base_evolution_contrats(
        df_contrats=df_contrats_base,
        df_prestations=df_prestations,
    ).copy()

    for colonne in [
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_end_date",
    ]:
        if colonne not in dates_contrats.columns:
            dates_contrats[colonne] = pd.NaT

        dates_contrats[colonne] = _dates_sans_fuseau(
            dates_contrats[colonne]
        )

    relations = relations.merge(
        dates_contrats[
            [
                "contract_reference",
                "contract_creation_date",
                "contract_deactivation_date",
                "contract_end_date",
            ]
        ],
        on="contract_reference",
        how="left",
        suffixes=(
            "_rattachement",
            "_source",
        ),
    )

    # Priorité :
    # 1. date de début contractuelle ;
    # 2. date de création dans Intent ;
    # 3. début de la période si aucune date n'existe.
    relations["date_debut_effective"] = (
        relations["contract_start_date"]
        .fillna(
            relations["contract_creation_date"]
        )
        .fillna(
            periodes["periode_debut"].min()
        )
    )

    # La première date connue met fin à la couverture :
    # date de fin contractuelle ou date de désactivation.
    relations["date_fin_effective"] = pd.concat(
        [
            relations[
                "contract_end_date_rattachement"
            ],
            relations[
                "contract_end_date_source"
            ],
            relations[
                "contract_deactivation_date"
            ],
        ],
        axis=1,
    ).min(axis=1)

    # Ajout de l'entité organisationnelle depuis la base ESI.
    relations = relations.merge(
        esi[
            [
                "esi_reference",
                "Entité",
            ]
        ],
        on="esi_reference",
        how="inner",
    )

    # -------------------------------------------------
    # 5. Photographie de la couverture à chaque fin de mois
    # -------------------------------------------------

    lignes = []

    for periode in periodes.itertuples(
        index=False
    ):
        fin_mois = pd.Timestamp(
            periode.periode_fin
        )

        contrats_actifs = relations[
            (
                relations[
                    "date_debut_effective"
                ] <= fin_mois
            )
            & (
                relations[
                    "date_fin_effective"
                ].isna()
                | (
                    relations[
                        "date_fin_effective"
                    ] >= fin_mois
                )
            )
        ]

        couverts = (
            contrats_actifs.groupby(
                "Entité",
                as_index=False,
            )["esi_reference"]
            .nunique()
            .rename(
                columns={
                    "esi_reference": (
                        "ESI couverts"
                    ),
                }
            )
        )

        situation_mois = population.merge(
            couverts,
            on="Entité",
            how="left",
        )

        situation_mois["ESI couverts"] = (
            situation_mois[
                "ESI couverts"
            ]
            .fillna(0)
            .astype(int)
        )

        situation_mois[
            "ESI non couverts"
        ] = (
            situation_mois["ESI totaux"]
            - situation_mois["ESI couverts"]
        ).clip(lower=0)

        situation_mois[
            "Taux de couverture"
        ] = (
            situation_mois["ESI couverts"]
            .div(
                situation_mois[
                    "ESI totaux"
                ].replace(0, pd.NA)
            )
            .mul(100)
            .fillna(0)
            .round(1)
        )

        situation_mois["Mois"] = pd.Timestamp(
            periode.periode_debut
        )

        situation_mois["Période"] = (
            periode.libelle
        )

        situation_mois["Maille"] = maille

        lignes.append(situation_mois)

    if not lignes:
        return pd.DataFrame(
            columns=colonnes_sortie
        )

    historique = pd.concat(
        lignes,
        ignore_index=True,
    )

    return (
        historique[colonnes_sortie]
        .sort_values(
            [
                "Mois",
                "Entité",
            ]
        )
        .reset_index(drop=True)
    )


def afficher_evolution_couverture_esi(
    df_esi_base: pd.DataFrame,
    df_contrats_base: pd.DataFrame,
    df_prestations: pd.DataFrame,
):
    with st.expander(
        "Évolution mensuelle de la couverture",
        expanded=True,
    ):
        section(
            "Évolution mensuelle du taux de couverture",
            (
                "Part des ESI couverts par au moins "
                "un contrat actif à la fin de chaque mois."
            ),)
        
        type_analyse = st.radio(
            "Type d’analyse",
            [
                "Couverture globale",
                "Couverture par métier",
            ],
            horizontal=True,
            key="couverture_evolution_type_analyse",
        )

        col_periode, col_maille = st.columns(
            2,
            gap="large",
        )

        with col_periode:
            periode_selectionnee = st.radio(
                "Période analysée",
                [
                    "12 mois",
                    "24 mois",
                    "36 mois",
                ],
                index=0,
                horizontal=True,
                key="couverture_evolution_periode",
            )

        with col_maille:
            maille_selectionnee = st.selectbox(
                "Maille de comparaison",
                [
                    "Société",
                    "Agence",
                    "Groupe",
                    "Secteur",
                ],
                index=0,
                key="couverture_evolution_maille",
            )

        correspondance_maille = {
            "Société": "societe",
            "Agence": "agence",
            "Groupe": "groupe",
            "Secteur": "secteur",
        }

        metier_selectionne = None

        if type_analyse == "Couverture par métier":
            if "contract_topic" not in df_contrats_base.columns:
                st.info(
                    "La colonne métier n’est pas disponible "
                    "dans les contrats."
                )
                return

            metiers_disponibles = (
                df_contrats_base["contract_topic"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            metiers_disponibles = (
                metiers_disponibles[
                    ~metiers_disponibles.isin(
                        [
                            "",
                            "Non renseigné",
                            "nan",
                            "None",
                            "<NA>",
                        ]
                    )
                ]
                .drop_duplicates()
                .sort_values()
                .tolist()
            )

            if not metiers_disponibles:
                st.info(
                    "Aucun métier disponible sur le "
                    "périmètre sélectionné."
                )
                return

            metier_selectionne = st.selectbox(
                "Métier analysé",
                options=metiers_disponibles,
                key="couverture_evolution_metier",
            )








        historique = (
            construire_evolution_couverture_esi(
                df_esi_base=df_esi_base,
                df_contrats_base=df_contrats_base,
                df_prestations=df_prestations,
                maille=correspondance_maille[
                    maille_selectionnee
                ],
                nb_mois=int(
                    periode_selectionnee.split()[0]
                ),
                metier=metier_selectionne,
            )
        )

        if historique.empty:
            st.info(
                "Aucune donnée exploitable pour "
                "reconstruire cette évolution."
            )
            return
        entites_disponibles = (
            historique["Entité"]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

        if not entites_disponibles:
            st.info(
                "Aucune entité organisationnelle disponible "
                "pour cette maille."
            )
            return

        # Par défaut :
        # toutes les sociétés si elles sont peu nombreuses ;
        # seulement les 5 premières pour les mailles plus détaillées.
        mode_selection = (
            "metier"
            if type_analyse == "Couverture par métier"
            else "globale"
        )

        metier_cle = (
            str(metier_selectionne)
            if metier_selectionne is not None
            else "tous"
        )

        cle_selection_entites = (
            f"couverture_entites_v4_"
            f"{mode_selection}_"
            f"{maille_selectionnee}_"
            f"{metier_cle}"
        )

        # À la première ouverture de cette combinaison,
        # aucune entité n'est sélectionnée.
        if cle_selection_entites not in st.session_state:
            st.session_state[cle_selection_entites] = []

        entites_selectionnees = st.multiselect(
            f"{maille_selectionnee}(s) à comparer",
            options=entites_disponibles,
            placeholder=(
                f"Sélectionner une ou plusieurs "
                f"{maille_selectionnee.lower()}s"
            ),
            key=cle_selection_entites,
        )

        if not entites_selectionnees:
            st.info(
                "Sélectionne au moins une entité à comparer."
            )
            return

        historique = historique[
            historique["Entité"].isin(
                entites_selectionnees
            )
        ].copy()
        # -------------------------------------------------
        # Graphique
        # -------------------------------------------------


        if metier_selectionne is None:
            titre_analyse = (
                "ESI ayant au moins un contrat actif"
            )
        else:
            titre_analyse = (
                "ESI ayant au moins un contrat actif "
                f"du métier « {metier_selectionne} »"
            )

        st.markdown(
            f"""
            <div class="vg-info">
                Analyse : <strong>{_safe(titre_analyse)}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )


        if go is None:
            graphique_simple = historique.pivot(
                index="Période",
                columns="Entité",
                values="Taux de couverture",
            )

            st.line_chart(
                graphique_simple,
                width="stretch",
            )

        else:
            fig = go.Figure()

            entites = (
                historique["Entité"]
                .drop_duplicates()
                .tolist()
            )

            for index, entite in enumerate(
                entites
            ):
                serie_entite = historique[
                    historique["Entité"] == entite
                ].sort_values("Mois")

                fig.add_trace(
                    go.Scatter(
                        x=serie_entite[
                            "Période"
                        ],
                        y=serie_entite[
                            "Taux de couverture"
                        ],
                        mode="lines+markers",
                        name=str(entite),
                        line=dict(
                            width=2.2,
                            color=(
                                PALETTE_3F_GRAPHIQUES[
                                    index
                                    % len(
                                        PALETTE_3F_GRAPHIQUES
                                    )
                                ]
                            ),
                        ),
                        marker=dict(
                            size=5,
                        ),
                        customdata=serie_entite[
                            [
                                "ESI couverts",
                                "ESI totaux",
                                "ESI non couverts",
                            ]
                        ].to_numpy(),
                        hovertemplate=(
                            "<b>%{fullData.name}</b><br>"
                            "Mois : %{x}<br>"
                            "Taux : %{y:.1f} %<br>"
                            "ESI couverts : "
                            "%{customdata[0]:,.0f}<br>"
                            "ESI totaux : "
                            "%{customdata[1]:,.0f}<br>"
                            "ESI non couverts : "
                            "%{customdata[2]:,.0f}"
                            "<extra></extra>"
                        ),
                    )
                )

            periodes_uniques = (
                historique[
                    [
                        "Mois",
                        "Période",
                    ]
                ]
                .drop_duplicates()
                .sort_values("Mois")
            )



            _layout_plotly(
                fig,
                610,
            )

            fig.update_layout(
                hovermode="closest",
                showlegend=True,
                legend=dict(
                    title=maille_selectionnee,
                    orientation="h",
                    yanchor="top",
                    y=-0.22,
                    xanchor="center",
                    x=0.5,
                    font=dict(
                        size=10,
                    ),
                    itemclick="toggle",
                    itemdoubleclick="toggleothers",
                ),
                margin=dict(
                    l=65,
                    r=35,
                    t=15,
                    b=145,
                ),
                xaxis=dict(
                    title=None,
                    type="category",
                    categoryorder="array",
                    categoryarray=(
                        periodes_uniques[
                            "Période"
                        ].tolist()
                    ),
                    tickmode="array",
                    tickvals=(
                        periodes_uniques[
                            "Période"
                        ].tolist()
                    ),
                    ticktext=(
                        periodes_uniques[
                            "Période"
                        ].tolist()
                    ),
                    tickangle=-45,
                    automargin=True,
                    gridcolor=C_GRID,
                ),
                yaxis=dict(
                    title="Taux de couverture",
                    ticksuffix=" %",
                    range=[
                        0,
                        100,
                    ],
                    gridcolor=C_GRID,
                ),
            )

            st.plotly_chart(
                fig,
                width="stretch",
                config=config_plotly(
                    "evolution_mensuelle_couverture_esi"
                ),
            )

        if metier_selectionne is None:
            definition_indicateur = (
                "au moins un contrat actif, tous métiers confondus"
            )
        else:
            definition_indicateur = (
                "au moins un contrat actif du métier "
                f"« {metier_selectionne} »"
            )

        st.caption(
            "Le taux correspond à la part des ESI du périmètre "
            f"ayant {definition_indicateur}. "
            "Le dénominateur reste l’ensemble des ESI de chaque "
            "entité sélectionnée. Les contrats sont reconstruits "
            "à la fin de chaque mois selon leurs dates de début, "
            "de fin et de désactivation."
        )

        # -------------------------------------------------
        # Toutes les données + export Excel
        # -------------------------------------------------

        with st.expander(
            "Consulter toutes les données mensuelles",
            expanded=False,
        ):
            table_historique = historique.copy()

            table_historique["Mois"] = (
                table_historique["Mois"]
                .map(libelle_mois_fr)
            )

            st.dataframe(
                table_historique,
                width="stretch",
                hide_index=True,
                height=460,
            )

            dataframe_download(
                "Télécharger toutes les données en Excel",
                historique,
                "evolution_couverture_esi.xlsx",
                cle="export_evolution_couverture_esi",
            )

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


        periodes_affichees = (
            evolution["Période"]
            .astype(str)
            .tolist()
        )

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
            margin=dict(
                l=55,
                r=18,
                t=50,
                b=110,
            ),
            xaxis=dict(
                title=None,
                type="category",
                categoryorder="array",
                categoryarray=periodes_affichees,
                tickmode="array",
                tickvals=periodes_affichees,
                ticktext=periodes_affichees,
                tickangle=-45,
                tickfont=dict(size=10),
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
            width="stretch",
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

        periodes_affichees = (
            evolution["Période"]
            .astype(str)
            .tolist()
        )

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
            margin=dict(
                l=55,
                r=18,
                t=50,
                b=110,
            ),
            hovermode="x unified",
            xaxis=dict(
                title=None,
                type="category",
                categoryorder="array",
                categoryarray=periodes_affichees,
                tickmode="array",
                tickvals=periodes_affichees,
                ticktext=periodes_affichees,
                tickangle=-45,
                tickfont=dict(size=10),
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
            width="stretch",
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
# COMPOSANTS VISUELS
# =====================================================


def kpi_card(
    label,
    value,
    pill="",
    help_text="",
    accent=C_RED,
    compact=False,
):
    classes = "vg-card vg-card-compact" if compact else "vg-card"
    pill_html = (
        f'<div class="vg-card-pill">{_safe(pill)}</div>'
        if pill
        else ""
    )
    help_html = (
        f'<div class="vg-card-help">{_safe(help_text)}</div>'
        if help_text
        else ""
    )

    st.markdown(
        f"""
        <div class="{classes}" style="--accent:{_safe(accent)};">
            <div class="vg-card-accent"></div>
            <div class="vg-card-label">{_safe(label)}</div>
            <div class="vg-card-value">{_safe(fmt_nombre(value))}</div>
            {pill_html}
            {help_html}
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

def priority_card(
    label: str,
    value: int,
    help_text: str,
    color: str,
):
    st.markdown(
        f"""
        <div class="vg-priority-card" style="--priority-color:{_safe(color)};">
            <div class="vg-priority-head">
                <span class="vg-priority-dot"></span>
                <span class="vg-priority-label">{_safe(label)}</span>
            </div>
            <div class="vg-priority-value">{_safe(fmt_nombre(value))}</div>
            <div class="vg-priority-help">{_safe(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def family_card(
    title: str,
    value: int,
    help_text: str,
    color: str = C_NAVY,
):
    st.markdown(
        f"""
        <div class="vg-family-card" style="--family-color:{_safe(color)};">
            <div class="vg-family-title">{_safe(title)}</div>
            <div class="vg-family-value">{_safe(fmt_nombre(value))}</div>
            <div class="vg-family-help">{_safe(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def impact_alert_card(
    title: str,
    value: int,
    action: str,
    color: str,
    badge: str,
    icon: str = "!",
):
    st.markdown(
        f"""
        <div class="vg-impact-alert-card" style="--alert-color:{_safe(color)};">
            <div class="vg-impact-alert-top">
                <span class="vg-impact-alert-icon">{_safe(icon)}</span>
                <span class="vg-impact-alert-badge">{_safe(badge)}</span>
            </div>
            <div class="vg-impact-alert-value">{_safe(fmt_nombre(value))}</div>
            <div class="vg-impact-alert-title">{_safe(title)}</div>
            <div class="vg-impact-alert-action">{_safe(action)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_zone_title(title: str, color: str):
    st.markdown(
        f"""
        <div class="vg-alert-zone-title" style="--zone-color:{_safe(color)};">
            {_safe(title)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def alerts_hero(
    total: int,
    prioritaires: int,
    a_traiter: int,
    a_controler: int,
):
    # HTML volontairement construit sans indentation en début de ligne :
    # cela évite que Markdown interprète une partie du bloc comme du code.
    contenu = (
        '<div class="vg-alerts-hero">'
        '<div class="vg-alerts-hero-inner">'
        '<div class="vg-alerts-hero-main">'
        '<div class="vg-alerts-hero-kicker">Centre de vigilance</div>'
        '<div class="vg-alerts-hero-line">'
        f'<span class="vg-alerts-hero-value">{_safe(fmt_nombre(total))}</span>'
        '<span class="vg-alerts-hero-title">alertes détectées</span>'
        '</div>'
        '<div class="vg-alerts-hero-help">'
        'Des situations nécessitent une action, une régularisation '
        'ou un contrôle métier sur le périmètre sélectionné.'
        '</div>'
        '</div>'
        '<div class="vg-alerts-hero-stats">'
        '<div class="vg-alerts-hero-stat">'
        '<span class="vg-alerts-hero-stat-label">Prioritaires</span>'
        f'<span class="vg-alerts-hero-stat-value">{_safe(fmt_nombre(prioritaires))}</span>'
        '</div>'
        '<div class="vg-alerts-hero-stat">'
        '<span class="vg-alerts-hero-stat-label">À traiter</span>'
        f'<span class="vg-alerts-hero-stat-value">{_safe(fmt_nombre(a_traiter))}</span>'
        '</div>'
        '<div class="vg-alerts-hero-stat">'
        '<span class="vg-alerts-hero-stat-label">À contrôler</span>'
        f'<span class="vg-alerts-hero-stat-value">{_safe(fmt_nombre(a_controler))}</span>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(contenu, unsafe_allow_html=True)


def alert_detail_intro(
    title: str,
    message: str,
    color: str,
):
    st.markdown(
        f"""
        <div class="vg-alert-detail-intro" style="--detail-color:{_safe(color)};">
            <div class="vg-alert-detail-intro-title">{_safe(title)}</div>
            <div class="vg-alert-detail-intro-help">{_safe(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def anomaly_hero(
    total: int,
):
    contenu = (
        '<div class="vg-anomaly-hero">'
        '<div class="vg-anomaly-hero-main">'
        '<div class="vg-anomaly-hero-kicker">Qualité des rattachements</div>'
        '<div class="vg-anomaly-hero-line">'
        f'<span class="vg-anomaly-hero-value">{_safe(fmt_nombre(total))}</span>'
        '<span class="vg-anomaly-hero-title">anomalies détectées</span>'
        '</div>'
        '<div class="vg-anomaly-hero-help">'
        'Ces objets ne peuvent pas être replacés correctement '
        'dans la hiérarchie patrimoine.'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(contenu, unsafe_allow_html=True)


def anomaly_main_card(
    value: int,
    share: float,
):
    st.markdown(
        f"""
        <div class="vg-anomaly-main-card">
            <div class="vg-anomaly-main-badge">Anomalie principale</div>
            <div class="vg-anomaly-main-value">{_safe(fmt_nombre(value))}</div>
            <div class="vg-anomaly-main-title">Logements sans programme</div>
            <div class="vg-anomaly-main-help">
                Ces logements ne ont rattachés à aucun programme.
            </div>
            <div class="vg-anomaly-main-share">{_safe(fmt_pourcentage(share))} du total</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def anomaly_secondary_card(
    title: str,
    value: int,
    help_text: str,
    color: str,
    icon: str,
):
    st.markdown(
        f"""
        <div class="vg-anomaly-secondary-card" style="--anomaly-color:{_safe(color)};">
            <div class="vg-anomaly-secondary-icon">{_safe(icon)}</div>
            <div class="vg-anomaly-secondary-value">{_safe(fmt_nombre(value))}</div>
            <div class="vg-anomaly-secondary-title">{_safe(title)}</div>
            <div class="vg-anomaly-secondary-help">{_safe(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def anomaly_detail_intro(
    title: str,
    message: str,
    color: str,
):
    st.markdown(
        f"""
        <div class="vg-anomaly-detail-intro" style="--anomaly-detail-color:{_safe(color)};">
            <div class="vg-anomaly-detail-title">{_safe(title)}</div>
            <div class="vg-anomaly-detail-help">{_safe(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def coverage_summary(
    taux_couverture: float,
    nb_esi_couverts: int,
    total_esi: int,
    nb_esi_equipes_non_couverts: int,
    nb_equipements_sans_contrat: int,
):
    phrase = (
        f"{fmt_nombre(nb_esi_couverts)} ESI sur {fmt_nombre(total_esi)} "
        "disposent d’au moins un contrat actif."
    )

    if nb_equipements_sans_contrat > 0:
        complement = (
            f" Toutefois, {fmt_nombre(nb_equipements_sans_contrat)} équipements "
            f"sans contrat sont répartis dans "
            f"{fmt_nombre(nb_esi_equipes_non_couverts)} ESI équipés."
        )
    else:
        complement = (
            " Aucun équipement sans contrat n’est détecté "
            "sur le périmètre sélectionné."
        )

    contenu = (
        '<div class="vg-coverage-summary">'
        '<div class="vg-coverage-summary-kicker">Synthèse de couverture</div>'
        '<div class="vg-coverage-summary-title">'
        f'<strong>{_safe(fmt_pourcentage(taux_couverture))}</strong> '
        'des ESI disposent d’un contrat actif'
        '</div>'
        '<div class="vg-coverage-summary-help">'
        f'{_safe(phrase + complement)}'
        '</div>'
        '</div>'
    )
    st.markdown(contenu, unsafe_allow_html=True)


def coverage_context(
    contrats: int,
    esi: int,
    logements: int,
    equipements: int,
):
    contenu = (
        '<div class="vg-coverage-context">'
        '<span class="vg-coverage-context-label">Périmètre analysé</span>'
        f'<span class="vg-coverage-context-pill">{_safe(fmt_nombre(esi))} ESI</span>'
        f'<span class="vg-coverage-context-pill">{_safe(fmt_nombre(logements))} logements</span>'
        f'<span class="vg-coverage-context-pill">{_safe(fmt_nombre(equipements))} équipements</span>'
        f'<span class="vg-coverage-context-pill">{_safe(fmt_nombre(contrats))} contrats</span>'
        '</div>'
    )
    st.markdown(contenu, unsafe_allow_html=True)


def coverage_reading_card(
    eyebrow: str,
    title: str,
    question: str,
    rate: float,
    covered: int,
    uncovered: int,
    base_label: str,
    color: str,
    gap_color: str,
    covered_label: str,
    uncovered_label: str,
):
    covered_width = max(0.0, min(float(rate), 100.0))
    gap_width = max(0.0, 100.0 - covered_width)

    contenu = (
        f'<div class="vg-coverage-reading-card {"primary" if "Niveau 1" in eyebrow else "secondary"}" '
        f'style="--reading-color:{_safe(color)};--gap-color:{_safe(gap_color)};">'
        f'<div class="vg-coverage-reading-eyebrow">{_safe(eyebrow)}</div>'
        f'<div class="vg-coverage-reading-title">{_safe(title)}</div>'
        f'<div class="vg-coverage-reading-question">{_safe(question)}</div>'
        '<div class="vg-coverage-reading-main">'
        f'<span class="vg-coverage-reading-rate">{_safe(fmt_pourcentage(rate))}</span>'
        f'<span class="vg-coverage-reading-count">{_safe(fmt_nombre(covered))} couverts</span>'
        '</div>'
        '<div class="vg-coverage-progress">'
        f'<div class="vg-coverage-progress-covered" style="width:{covered_width:.2f}%;"></div>'
        f'<div class="vg-coverage-progress-gap" style="width:{gap_width:.2f}%;"></div>'
        '</div>'
        '<div class="vg-coverage-reading-stats">'
        '<div class="vg-coverage-reading-stat">'
        f'<div class="vg-coverage-reading-stat-label">{_safe(covered_label)}</div>'
        f'<div class="vg-coverage-reading-stat-value">{_safe(fmt_nombre(covered))}</div>'
        '</div>'
        '<div class="vg-coverage-reading-stat">'
        f'<div class="vg-coverage-reading-stat-label">{_safe(uncovered_label)}</div>'
        f'<div class="vg-coverage-reading-stat-value">{_safe(fmt_nombre(uncovered))}</div>'
        '</div>'
        '</div>'
        f'<div class="vg-coverage-reading-base">Base : {_safe(base_label)}</div>'
        '</div>'
    )
    st.markdown(contenu, unsafe_allow_html=True)


def park_summary_card(
    label: str,
    value: int,
    rate: float | None,
    color: str,
):
    rate_html = (
        f'<span class="vg-park-rate">{_safe(fmt_pourcentage(rate))}</span>'
        if rate is not None
        else ""
    )
    st.markdown(
        (
            f'<div class="vg-park-card" style="--park-color:{_safe(color)};">'
            f'<div class="vg-park-label">{_safe(label)}</div>'
            '<div class="vg-park-line">'
            f'<span class="vg-park-value">{_safe(fmt_nombre(value))}</span>'
            f'{rate_html}'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def intensity_distribution_html(rows: list[dict]):
    lignes = []
    for row in rows:
        lignes.append(
            (
                '<div class="vg-intensity-row">'
                f'<div class="vg-intensity-label">{_safe(row["label"])}</div>'
                '<div class="vg-intensity-track">'
                f'<div class="vg-intensity-fill" '
                f'style="--intensity-width:{float(row["rate"]):.2f}%;'
                f'--intensity-color:{_safe(row["color"])};"></div>'
                '</div>'
                f'<div class="vg-intensity-value">'
                f'{_safe(fmt_nombre(row["count"]))} · {_safe(fmt_pourcentage(row["rate"]))}'
                '</div>'
                '</div>'
            )
        )
    st.markdown(
        '<div class="vg-intensity-distribution">' + "".join(lignes) + "</div>",
        unsafe_allow_html=True,
    )


def intensity_kpi(
    label: str,
    value: str,
    help_text: str,
    color: str,
):
    st.markdown(
        (
            f'<div class="vg-intensity-kpi" style="--intensity-color:{_safe(color)};">'
            f'<div class="vg-intensity-kpi-label">{_safe(label)}</div>'
            f'<div class="vg-intensity-kpi-value">{_safe(value)}</div>'
            f'<div class="vg-intensity-kpi-help">{_safe(help_text)}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )



def equipment_overview(
    total: int,
    covered: int,
    uncovered: int,
    rate: float,
    definition: str,
):
    contenu = (
        '<div class="vg-equipment-main-card" style="max-width:none;">'
        f'<div class="vg-equipment-ring" style="--ring-rate:{max(0.0, min(rate, 100.0)):.2f};">'
        '<div class="vg-equipment-ring-center">'
        f'<div class="vg-equipment-ring-value">{_safe(fmt_pourcentage(rate))}</div>'
        '<div class="vg-equipment-ring-label">couverts</div>'
        '</div>'
        '</div>'
        '<div>'
        '<div class="vg-equipment-main-title">'
        f'{_safe(fmt_nombre(covered))} équipements couverts sur {_safe(fmt_nombre(total))}'
        '</div>'
        '<div class="vg-equipment-main-help">'
        f'{_safe(fmt_nombre(uncovered))} équipements restent sans contrat actif exploitable. '
        f'Un équipement est considéré comme couvert lorsqu’il possède {_safe(definition)} '
        'directement rattaché dans Intent.'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(contenu, unsafe_allow_html=True)


def equipment_types_panel(
    dataframe: pd.DataFrame,
    total: int,
    maximum: int = 7,
):
    """
    Affiche une barre empilée par catégorie :

    vert = équipements couverts
    rose clair = équipements non couverts

    La longueur totale représente 100 % de la catégorie.
    """
    if dataframe.empty:
        st.info("Aucune donnée de typologie équipement disponible.")
        return

    df = (
        dataframe
        .sort_values("Équipements", ascending=False)
        .head(maximum)
        .copy()
    )

    rows = []

    for _, row in df.iterrows():
        label = str(
            row.get(
                "Type d’équipement",
                "Non renseigné",
            )
        )

        equipment_count_raw = pd.to_numeric(
            row.get("Équipements", 0),
            errors="coerce",
        )
        covered_count_raw = pd.to_numeric(
            row.get("Équipements couverts", 0),
            errors="coerce",
        )

        equipment_count = (
            0
            if pd.isna(equipment_count_raw)
            else int(equipment_count_raw)
        )
        covered_count = (
            0
            if pd.isna(covered_count_raw)
            else int(covered_count_raw)
        )

        covered_count = min(
            max(covered_count, 0),
            max(equipment_count, 0),
        )
        uncovered_count = max(
            equipment_count - covered_count,
            0,
        )

        coverage_rate = (
            covered_count / equipment_count * 100
            if equipment_count
            else 0.0
        )
        uncovered_rate = max(
            100.0 - coverage_rate,
            0.0,
        )

        rows.append(
            '<div class="vg-equipment-type-row">'

            f'<div class="vg-equipment-type-label" '
            f'title="{_safe(label)}">'
            f'{_safe(label)}'
            '</div>'

            '<div class="vg-equipment-type-track" '
            f'title="{_safe(fmt_nombre(covered_count))} couverts et '
            f'{_safe(fmt_nombre(uncovered_count))} non couverts">'

            '<div class="vg-equipment-type-covered" '
            f'style="--covered-width:{coverage_rate:.2f}%;"></div>'

            '<div class="vg-equipment-type-uncovered" '
            f'style="--uncovered-width:{uncovered_rate:.2f}%;"></div>'

            '</div>'

            '<div class="vg-equipment-type-value">'
            '<div class="vg-equipment-type-rate">'
            f'{_safe(fmt_pourcentage(coverage_rate))} couverts'
            '</div>'
            '<div class="vg-equipment-type-detail">'
            f'<strong>{_safe(fmt_nombre(covered_count))} / '
            f'{_safe(fmt_nombre(equipment_count))}</strong><br>'
            f'{_safe(fmt_nombre(uncovered_count))} non couverts'
            '</div>'
            '</div>'

            '</div>'
        )

    contenu = (
        '<div class="vg-equipment-types-panel">'

        '<div class="vg-equipment-types-head">'
        '<div>'
        '<div class="vg-equipment-types-title">'
        'Couverture par type d’équipement'
        '</div>'
        '<div class="vg-equipment-types-subtitle">'
        'Chaque barre représente 100 % de la catégorie : '
        'vert pour les équipements couverts, rose pour les non couverts.'
        '</div>'
        '</div>'
        f'<div class="vg-equipment-types-total">'
        f'{_safe(fmt_nombre(total))} équipements'
        '</div>'
        '</div>'

        '<div class="vg-equipment-types-legend">'
        '<div class="vg-equipment-types-legend-item">'
        '<span class="vg-equipment-types-legend-dot" '
        'style="--legend-color:#4F9B88;"></span>'
        'Couverts'
        '</div>'
        '<div class="vg-equipment-types-legend-item">'
        '<span class="vg-equipment-types-legend-dot" '
        'style="--legend-color:#F3B6C6;"></span>'
        'Non couverts'
        '</div>'
        '</div>'

        + "".join(rows)
        + '</div>'
    )

    st.markdown(
        contenu,
        unsafe_allow_html=True,
    )



def step_header(
    number: int,
    title: str,
    help_text: str,
):
    st.markdown(
        (
            '<div class="vg-step-header">'
            f'<div class="vg-step-number">{_safe(number)}</div>'
            '<div class="vg-step-copy">'
            f'<div class="vg-step-title">{_safe(title)}</div>'
            f'<div class="vg-step-help">{_safe(help_text)}</div>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )



def coverage_insights(
    nb_esi_couverts: int,
    nb_esi_sans_contrat: int,
    nb_esi_equipes_non_couverts: int,
):
    contenu = (
        '<div class="vg-coverage-insights">'

        '<div class="vg-coverage-insight" style="--insight-color:#4F9B88;">'
        '<div class="vg-coverage-insight-icon">✓</div>'
        '<div>'
        f'<div class="vg-coverage-insight-value">{_safe(fmt_nombre(nb_esi_couverts))}</div>'
        '<div class="vg-coverage-insight-text">'
        'ESI disposent d’au moins un contrat actif.'
        '</div>'
        '</div>'
        '</div>'

        '<div class="vg-coverage-insight" style="--insight-color:#D65A83;">'
        '<div class="vg-coverage-insight-icon">!</div>'
        '<div>'
        f'<div class="vg-coverage-insight-value">{_safe(fmt_nombre(nb_esi_sans_contrat))}</div>'
        '<div class="vg-coverage-insight-text">'
        'ESI restent sans contrat actif et nécessitent une vérification.'
        '</div>'
        '</div>'
        '</div>'

        '<div class="vg-coverage-insight" style="--insight-color:#173B69;">'
        '<div class="vg-coverage-insight-icon">◆</div>'
        '<div>'
        f'<div class="vg-coverage-insight-value">{_safe(fmt_nombre(nb_esi_equipes_non_couverts))}</div>'
        '<div class="vg-coverage-insight-text">'
        'ESI équipés ont au moins un équipement sans contrat rattaché.'
        '</div>'
        '</div>'
        '</div>'

        '</div>'
    )
    st.markdown(contenu, unsafe_allow_html=True)


def status_banner(
    title: str,
    help_text: str,
    color: str,
    background: str,
    border: str,
):
    st.markdown(
        f"""
        <div
            class="vg-status-banner"
            style="
                --status-color:{_safe(color)};
                --status-background:{_safe(background)};
                --status-border:{_safe(border)};
            "
        >
            <span class="vg-status-banner-dot"></span>
            <div>
                <div class="vg-status-banner-title">{_safe(title)}</div>
                <div class="vg-status-banner-help">{_safe(help_text)}</div>
            </div>
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
        width="stretch",
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
        width="stretch",
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

def trouver_colonne(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def normaliser_gravite(value) -> str:
    valeur = str(value or "").strip().lower()

    if any(mot in valeur for mot in ["bloquant", "critique", "critical"]):
        return "Bloquante"

    if any(
        mot in valeur
        for mot in ["important", "majeur", "major", "élevé", "eleve", "haute"]
    ):
        return "Importante"

    return "À surveiller"


def compter_objets_distincts(
    df: pd.DataFrame,
    colonne_reference: str | None,
) -> int:
    if df.empty:
        return 0

    if colonne_reference and colonne_reference in df.columns:
        return int(df[colonne_reference].nunique())

    return int(len(df))


def preparer_alertes_table(df_alertes: pd.DataFrame) -> pd.DataFrame:
    if df_alertes.empty:
        return pd.DataFrame()

    df = df_alertes.copy()

    rename_map = {
        "alerte_type": "Alerte",
        "type_alerte": "Alerte",
        "categorie": "Catégorie",
        "priorite": "Priorité",
        "gravite": "Priorité",
        "description": "Description",
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI",
        "contract_reference": "Référence contrat",
        "contract_label": "Libellé contrat",
        "contract_topic": "Métier",
        "third_party_label": "Prestataire",
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "contract_end_date": "Date de fin",
        "jours_avant_echeance": "Jours avant échéance",
    }

    colonnes = [
        colonne
        for colonne in rename_map
        if colonne in df.columns
    ]

    if not colonnes:
        return df

    table = df[colonnes].rename(columns=rename_map).copy()

    if "Priorité" in table.columns:
        table["Priorité"] = table["Priorité"].apply(normaliser_gravite)

    if "Date de fin" in table.columns:
        table["Date de fin"] = table["Date de fin"].apply(fmt_date)

    return table


def preparer_resume_qualite(
    df_qualite_resume: pd.DataFrame,
    df_qualite: pd.DataFrame,
) -> pd.DataFrame:
    if not df_qualite_resume.empty:
        resume = df_qualite_resume.copy()
    elif not df_qualite.empty:
        reference_col = trouver_colonne(
            df_qualite,
            ["objet_reference", "contract_reference", "esi_reference"],
        )

        if reference_col and "anomalie_type" in df_qualite.columns:
            resume = (
                df_qualite.groupby(
                    ["anomalie_type", "objet_type", "gravite"],
                    dropna=False,
                    as_index=False,
                )[reference_col]
                .nunique()
                .rename(columns={reference_col: "nb_objets_distincts"})
            )
        else:
            return pd.DataFrame()
    else:
        return pd.DataFrame()

    count_col = trouver_colonne(
        resume,
        [
            "nombre_objets_distincts",
            "nb_objets_distincts",
            "nombre_occurrences",
            "nb_lignes_detail",
        ],
    )

    if count_col is None:
        resume["Nombre"] = 1
    else:
        resume["Nombre"] = pd.to_numeric(
            resume[count_col],
            errors="coerce",
        ).fillna(0)

    if "gravite" not in resume.columns:
        resume["gravite"] = "À surveiller"

    resume["Niveau"] = resume["gravite"].apply(normaliser_gravite)

    return resume

def dataframe_download(
    label: str,
    df: pd.DataFrame,
    filename: str,
    cle: str | None = None,
):
    if df.empty:
        return

    export = df.copy()

    for colonne in export.columns:
        serie = export[colonne]
        if pd.api.types.is_datetime64_any_dtype(serie):
            serie = pd.to_datetime(serie, errors="coerce")
            try:
                serie = serie.dt.tz_localize(None)
            except (TypeError, AttributeError):
                pass
            export[colonne] = serie

    fichier = BytesIO()
    with pd.ExcelWriter(fichier, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name="Données")
        feuille = writer.sheets["Données"]
        feuille.freeze_panes = "A2"
        feuille.auto_filter.ref = feuille.dimensions

        for cellules in feuille.columns:
            valeurs = [
                len(str(cellule.value)) if cellule.value is not None else 0
                for cellule in cellules
            ]
            largeur = min(max(valeurs, default=0) + 3, 55)
            feuille.column_dimensions[cellules[0].column_letter].width = largeur

    fichier.seek(0)
    nom_excel = filename.rsplit(".", 1)[0] + ".xlsx"

    st.download_button(
        label,
        data=fichier.getvalue(),
        file_name=nom_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=cle,
        width="stretch",
    )


# =====================================================
# PRÉPARATION DES TABLEAUX
# =====================================================


def preparer_contrats_table(
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = [
        "contract_reference",
        "contract_label",
        "contract_description",
        "third_party_label",
        "contract_start_date",
        "contract_end_date",
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_last_update_date",
        "contract_topic",
        "contract_status",
        "societe",
        "agence",
        "groupe",
        "secteur",
        "esi_reference",
        "esi_label",
    ]

    cols = [
        col
        for col in cols
        if col in df.columns
    ]

    out = df[cols].copy()

    # Dates contractuelles : jour uniquement.
    for col in [
        "contract_start_date",
        "contract_end_date",
    ]:
        if col in out.columns:
            out[col] = (
                pd.to_datetime(
                    out[col],
                    errors="coerce",
                )
                .dt.strftime("%d/%m/%Y")
                .fillna("")
            )

    # Dates techniques Intent : date et heure.
    for col in [
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_last_update_date",
    ]:
        if col in out.columns:
            out[col] = (
                pd.to_datetime(
                    out[col],
                    errors="coerce",
                )
                .dt.strftime("%d/%m/%Y %H:%M")
                .fillna("")
            )

    return out.rename(
        columns={
            "contract_reference": "Référence contrat",
            "contract_label": "Libellé contrat",
            "contract_description": "Description contrat",
            "third_party_label": "Prestataire",
            "contract_start_date": "Date de début",
            "contract_end_date": "Date de fin",
            "contract_creation_date": "Date de création Intent",
            "contract_deactivation_date": "Date de désactivation Intent",
            "contract_last_update_date": "Dernière modification",
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


def preparer_prestations_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = [
        "contract_reference_3f",
        "contract_reference_prestataire",
        "contract_id_intent",
        "contract_label",
        "contract_description",
        "third_party_label",
        "third_party_reference",
        "contract_topic",
        "contract_status",
        "contract_start_date",
        "contract_end_date",
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_last_update_date",
        "contract_active_end_date_expired",
        "service_code_id_intent",
        "service_code_reference_3f",
        "service_code_reference_prestataire",
        "service_code_label",
        "service_code_description",
        "service_code_work_type",
        "service_code_critical_level",
        "service_code_fixed_rate",
        "sla_periodicity_value",
        "sla_periodicity_unit",
        "sla_estimated_intervention_duration_value",
        "sla_estimated_intervention_duration_unit",
        "sla_max_time_to_intervention_value",
        "sla_max_time_to_intervention_unit",
        "sla_max_time_to_recovery_value",
        "sla_max_time_to_recovery_unit",
    ]
    cols = [col for col in cols if col in df.columns]
    out = df[cols].copy()

    for col in ["contract_start_date", "contract_end_date"]:
        if col in out.columns:
            out[col] = (
                pd.to_datetime(out[col], errors="coerce")
                .dt.strftime("%d/%m/%Y")
                .fillna("")
            )

    for col in [
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_last_update_date",
    ]:
        if col in out.columns:
            out[col] = (
                pd.to_datetime(out[col], errors="coerce")
                .dt.strftime("%d/%m/%Y %H:%M")
                .fillna("")
            )

    if "service_code_work_type" in out.columns:
        out["service_code_work_type"] = out["service_code_work_type"].replace(
            {
                "corrective": "Curatif",
                "preventive": "Préventif",
                "operational": "Opérationnel",
            }
        )

    if "contract_active_end_date_expired" in out.columns:
        out["contract_active_end_date_expired"] = (
            pd.to_numeric(
                out["contract_active_end_date_expired"],
                errors="coerce",
            )
            .fillna(0)
            .map({1: "Oui", 0: "Non"})
        )

    return out.rename(
        columns={
            "contract_reference_3f": "Référence contrat 3F",
            "contract_reference_prestataire": "Référence contrat prestataire",
            "contract_id_intent": "Identifiant contrat Intent",
            "contract_label": "Libellé contrat",
            "contract_description": "Description contrat",
            "third_party_label": "Prestataire",
            "third_party_reference": "Référence prestataire",
            "contract_topic": "Métier",
            "contract_status": "Statut",
            "contract_start_date": "Date de début",
            "contract_end_date": "Date de fin",
            "contract_creation_date": "Date de création Intent",
            "contract_deactivation_date": "Date de désactivation Intent",
            "contract_last_update_date": "Dernière modification",
            "contract_active_end_date_expired": "Contrat actif expiré",
            "service_code_id_intent": "Identifiant prestation Intent",
            "service_code_reference_3f": "Référence prestation 3F",
            "service_code_reference_prestataire": "Référence prestation prestataire",
            "service_code_label": "Libellé prestation",
            "service_code_description": "Description prestation",
            "service_code_work_type": "Type d’intervention",
            "service_code_critical_level": "Niveau de criticité",
            "service_code_fixed_rate": "Forfait fixe",
            "sla_periodicity_value": "Périodicité SLA",
            "sla_periodicity_unit": "Unité périodicité",
            "sla_estimated_intervention_duration_value": "Durée estimée intervention",
            "sla_estimated_intervention_duration_unit": "Unité durée estimée",
            "sla_max_time_to_intervention_value": "Délai maximal intervention",
            "sla_max_time_to_intervention_unit": "Unité délai intervention",
            "sla_max_time_to_recovery_value": "Délai maximal rétablissement",
            "sla_max_time_to_recovery_unit": "Unité délai rétablissement",
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
    cols = [col for col in cols if col in df.columns]
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


def preparer_equipements_table(df: pd.DataFrame) -> pd.DataFrame:
    """Prépare un tableau lisible sans noms de colonnes dupliqués."""
    if df.empty:
        return pd.DataFrame()

    colonnes_candidates = [
        ("equipment_reference", "Référence équipement"),
        ("equipment_label", "Libellé équipement"),
        ("equipment_type_normalise", "Type d’équipement"),
        ("equipment_type", "Type d’équipement source"),
        ("esi_reference", "Référence ESI"),
        ("esi_label", "Libellé ESI"),
        ("societe", "Société"),
        ("agence", "Agence"),
        ("groupe", "Groupe"),
        ("secteur", "Secteur"),
        ("nb_contrats_actifs", "Contrats actifs"),
        ("equipment_covered_valid", "Couvert par contrat actif"),
    ]

    colonnes_source = []
    renommage = {}
    labels_utilises = set()

    for source_col, label in colonnes_candidates:
        if (
            source_col in df.columns
            and source_col not in colonnes_source
            and label not in labels_utilises
        ):
            colonnes_source.append(source_col)
            renommage[source_col] = label
            labels_utilises.add(label)

    if not colonnes_source:
        return df.copy()

    table = df[colonnes_source].copy().rename(columns=renommage)

    if "Couvert par contrat actif" in table.columns:
        table["Couvert par contrat actif"] = (
            pd.to_numeric(
                table["Couvert par contrat actif"],
                errors="coerce",
            )
            .fillna(0)
            .gt(0)
            .map({True: "Oui", False: "Non"})
        )

    if "Référence équipement" in table.columns:
        table = table.drop_duplicates("Référence équipement")
    else:
        table = table.drop_duplicates()

    return table.reset_index(drop=True)



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
    cols = [col for col in cols if col in df.columns]
    out = df[cols].copy()

    if "contract_end_date" in out.columns:
        out["contract_end_date"] = (
            pd.to_datetime(out["contract_end_date"], errors="coerce")
            .dt.strftime("%d/%m/%Y")
            .fillna("")
        )

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
        masque = masque | (
            df[col]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(recherche, regex=False, na=False)
        )
    return df[masque].copy()


# def afficher_detail_qualite(
#     focus,
#     df_contrats_kpi,
#     df_esi_context,
#     df_qualite,
#     df_global,
# ):
#     if not focus:
#         return

#     st.markdown("---")

#     if focus == "expired":
#         section(
#             "Détail : contrats actifs avec date de fin dépassée",
#             "Contrats exploitables dans le périmètre filtré.",
#         )
#         table = preparer_contrats_table(contrats_actifs_fin_depassee(df_contrats_kpi))
#         if table.empty:
#             st.success("Aucun contrat actif expiré dans le périmètre affiché.")
#         else:
#             st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
#             dataframe_download(
#                 "Télécharger les contrats expirés",
#                 table,
#                 "contrats_actifs_expires.xlsx",
#             )

#     elif focus == "unlinked_contracts":
#         section(
#             "Détail : contrats non rattachés",
#             "Contrats présents en source mais absents de la couverture programme.",
#         )
#         if not df_qualite.empty and "anomalie_type" in df_qualite.columns:
#             table = df_qualite[
#                 df_qualite["anomalie_type"] == "CONTRAT_NON_RATTACHE_PROGRAMME"
#             ].copy()
#         else:
#             table = pd.DataFrame()
#         table = preparer_qualite_table(table)
#         if table.empty:
#             st.info("Aucun détail disponible dans la table qualité.")
#         else:
#             st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
#             dataframe_download(
#                 "Télécharger les contrats non rattachés",
#                 table,
#                 "contrats_non_rattaches.xlsx",
#             )

#     elif focus == "housing":
#         section(
#             "Détail : logements sans programme",
#             "Logements non exploitables dans les calculs de couverture ESI.",
#         )
#         if not df_qualite.empty and "anomalie_type" in df_qualite.columns:
#             table = df_qualite[
#                 df_qualite["anomalie_type"] == "LOGEMENT_SANS_PROGRAMME"
#             ].copy()
#         else:
#             table = pd.DataFrame()
#         table = preparer_qualite_table(table)
#         if table.empty:
#             st.info("Aucun détail disponible dans la table qualité.")
#         else:
#             st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
#             dataframe_download(
#                 "Télécharger les logements sans programme",
#                 table,
#                 "logements_sans_programme.xlsx",
#             )
#             if len(table) > 500:
#                 st.caption(f"Affichage limité à 500 lignes sur {fmt_nombre(len(table))}.")

#     elif focus == "multi_topic":
#         section(
#             "Détail : ESI avec plusieurs contrats actifs sur le même métier",
#             "Ce signal peut révéler des doublons ou des chevauchements de contrats.",
#         )
#         if "esi_multi_meme_metier" not in df_esi_context.columns:
#             st.info("La colonne esi_multi_meme_metier n'est pas disponible.")
#             return
#         table = df_esi_context[
#             pd.to_numeric(
#                 df_esi_context["esi_multi_meme_metier"],
#                 errors="coerce",
#             ).fillna(0) > 0
#         ].copy()
#         table = preparer_esi_table(table)
#         if table.empty:
#             st.success("Aucun ESI multi même métier dans le périmètre affiché.")
#         else:
#             st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
#             dataframe_download(
#                 "Télécharger les ESI multi même métier",
#                 table,
#                 "esi_multi_meme_metier.xlsx",
#             )

#     elif focus == "no_contract":
#         section(
#             "Détail : ESI sans contrat actif",
#             "Programmes sans contrat actif rattaché dans le périmètre affiché.",
#         )
#         table = df_esi_context[
#             serie_numerique(df_esi_context, "nb_contrats_actifs") == 0
#         ].copy()
#         table = preparer_esi_table(table)
#         if table.empty:
#             st.success("Aucun ESI sans contrat actif dans le périmètre affiché.")
#         else:
#             st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
#             dataframe_download(
#                 "Télécharger les ESI sans contrat actif",
#                 table,
#                 "esi_sans_contrat_actif.xlsx",
#             )

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
            [
                "Vue globale",
                "Couverture",
                "Alertes",
                "Anomalies",
            ],
            horizontal=True,
            label_visibility="collapsed",
            key="dashboard_vue_active",
        )

with refresh_col:
    if st.button("Actualiser", width="stretch", key="dashboard_refresh"):
        try:
            get_engine().dispose()
        except Exception:
            pass

        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

try:
    with st.spinner("Chargement des données..."):
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
            df_alertes,
        ) = charger_donnees()
except Exception as exc:
    st.error("Erreur pendant le chargement des données.")
    st.code(str(exc))
    st.stop()

if df_global.empty:
    st.error("La table dashboard.kpi_globale est vide.")
    st.stop()

# Filtres patrimoine dans la barre latérale.
df_esi_filtre, df_contrats_filtre, filtres_selectionnes = render_filtres_patrimoine(
    df_esi=df_esi,
    df_contrats=df_contrats,
)

# =====================================================
# SYNTHÈSE DES ALERTES AVANT LE FILTRE DE STATUT
# =====================================================

# Les alertes opérationnelles suivent le périmètre patrimoine sélectionné,
# mais restent indépendantes du filtre de statut affiché ensuite.
df_esi_alertes_entree = dedupliquer_esi(df_esi_filtre)

# IMPORTANT :
# render_filtres_patrimoine peut retirer les contrats sans rattachement ESI
# même lorsqu'aucun filtre utilisateur n'est réellement sélectionné.
# Pour le total global, on doit donc repartir de df_contrats afin de conserver
# tous les contrats Intent, y compris les contrats non rattachés.
filtre_patrimoine_reel_actif = any(
    valeur_filtre_active(valeur)
    for valeur in (filtres_selectionnes or {}).values()
)

# Sans filtre, tous les contrats présents dans la source Intent sont autorisés.
# Avec un filtre patrimoine, on limite la liste aux références du périmètre.
references_contrats_alertes = None

if (
    filtre_patrimoine_reel_actif
    and not df_contrats_filtre.empty
    and "contract_reference" in df_contrats_filtre.columns
):
    references_contrats_alertes = set(
        df_contrats_filtre["contract_reference"]
        .dropna()
        .astype(str)
        .str.strip()
    )

contrats_expires_entree = contrats_actifs_expires_depuis_intent(
    df_prestations=df_prestations,
    references_contrats_autorisees=references_contrats_alertes,
)

# Sécurité uniquement si la colonne officielle n'est pas disponible.
if contrats_expires_entree.empty and (
    "contract_active_end_date_expired" not in df_prestations.columns
):
    source_contrats_alertes = (
        df_contrats_filtre.copy()
        if filtre_patrimoine_reel_actif
        else df_contrats.copy()
    )
    contrats_expires_entree = contrats_actifs_fin_depassee(
        source_contrats_alertes
    )
nb_contrats_expires_entree = int(
    contrats_expires_entree["contract_reference"].nunique()
    if (
        not contrats_expires_entree.empty
        and "contract_reference" in contrats_expires_entree.columns
    )
    else len(contrats_expires_entree)
)

nb_esi_sans_contrat_entree = int(
    (serie_numerique(df_esi_alertes_entree, "nb_contrats_actifs") == 0).sum()
)

# Définition métier officielle :
# un ESI équipé est non couvert par contrat équipement dès qu'au moins
# un de ses équipements ne possède aucun contrat rattaché.
nb_esi_equipes_non_couverts_entree = int(
    (
        (serie_numerique(df_esi_alertes_entree, "nb_equipements") > 0)
        & (
            serie_numerique(
                df_esi_alertes_entree,
                "nb_equipements_sans_contrat",
            ) > 0
        )
    ).sum()
)

nb_esi_multi_metier_entree = int(
    (serie_numerique(df_esi_alertes_entree, "esi_multi_meme_metier") > 0).sum()
)

contrats_source_entree = construire_contrats_uniques_source(
    df_prestations=df_prestations,
    df_contrats_rattaches=df_contrats,
)
if not contrats_source_entree.empty and "esi_reference" in contrats_source_entree.columns:
    contrats_sans_rattachement_entree = contrats_source_entree[
        contrats_source_entree["esi_reference"].isna()
        | contrats_source_entree["esi_reference"].astype(str).str.strip().isin(
            ["", "nan", "None", "<NA>", "Non renseigné"]
        )
    ].copy()
else:
    contrats_sans_rattachement_entree = pd.DataFrame()

nb_contrats_sans_rattachement_entree = int(
    contrats_sans_rattachement_entree["contract_reference"].nunique()
    if (
        not contrats_sans_rattachement_entree.empty
        and "contract_reference" in contrats_sans_rattachement_entree.columns
    )
    else int(global_value(df_global, "contrats_non_rattaches_programme", 0))
)

nb_situations_alertes = (
    nb_contrats_expires_entree
    + nb_esi_sans_contrat_entree
    + nb_esi_equipes_non_couverts_entree
    + nb_esi_multi_metier_entree
    + nb_contrats_sans_rattachement_entree
)

# Dans Couverture, l'alerte est le premier élément métier affiché.
# if vue_active == "Couverture":
#     if nb_situations_alertes > 0:
#         alerte_col, bouton_alerte_col = st.columns(
#             [5, 1.2],
#             gap="medium",
#             vertical_alignment="center",
#         )
#         with alerte_col:
#             st.markdown(
#                 f"""
#                 <div class="vg-coverage-alert">
#                     <div class="vg-coverage-alert-content">
#                         <div class="vg-coverage-alert-icon">!</div>
#                         <div>
#                             <div class="vg-coverage-alert-title">
#                                 {fmt_nombre(nb_situations_alertes)} signal(s) à vérifier
#                             </div>
#                             <div class="vg-coverage-alert-help">
#                                 Contrats expirés ou non rattachés, ESI non couverts
#                                 et chevauchements contractuels détectés.
#                             </div>
#                         </div>
#                     </div>
#                 </div>
#                 """,
#                 unsafe_allow_html=True,
#             )
#         with bouton_alerte_col:
#             st.button(
#                 "Voir les alertes",
#                 key="ouvrir_alertes_depuis_couverture",
#                 width="stretch",
#                 on_click=ouvrir_onglet_alertes,
#             )
#     else:
#         st.markdown(
#             """
#             <div class="vg-coverage-alert"
#                  style="background:#F1FBF8;border-color:#CFECE3;border-left-color:#008080;">
#                 <div class="vg-coverage-alert-content">
#                     <div class="vg-coverage-alert-icon"
#                          style="color:#008080;border-color:#CFECE3;">✓</div>
#                     <div>
#                         <div class="vg-coverage-alert-title">Aucun signal prioritaire</div>
#                         <div class="vg-coverage-alert-help">
#                             Aucun cas nécessitant une action immédiate n'est détecté.
#                         </div>
#                     </div>
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

# La Vue globale permet de comparer les statuts.
# La page Couverture analyse toujours les contrats actifs.
if vue_active == "Vue globale":
    with st.container(key="contract_status_filter"):
        st.markdown(
            '<div class="vg-mini-title">Statut des contrats</div>',
            unsafe_allow_html=True,
        )

        statut_selectionne = afficher_filtre_statut_contrat()

        st.caption(
            "Les totaux source restent fixes dans la vue globale. "
            "Les détails suivent les filtres sélectionnés."
        )
elif vue_active == "Couverture":
    statut_selectionne = "active"
else:
    statut_selectionne = None

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

# La couverture conserve toujours l'ensemble du parc filtré comme dénominateur.
# Les contrats actifs servent uniquement à déterminer quels ESI sont couverts.
if vue_active == "Couverture":
    df_esi_kpi = df_esi_filtre.copy()
else:
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
            "Couverture des contrats actifs rapportée à l’ensemble du patrimoine.",
        )
    elif statut_selectionne == "inactive":
        section(
            "Vue globale",
            "Périmètre des contrats inactifs et patrimoine associé.",
        )
    else:
        if perimetre_filtre_actif:
            section(
                "Vue globale",
                "Périmètre sélectionné et patrimoine associé.",
            )
        else:
            section(
                "Vue globale",
                (
                    "La réalité présente dans Intent, puis la part "
                    "réellement exploitable pour les analyses de couverture."
                ),
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
    # Tous les contrats avec un filtre actif :
    # contrat, société, agence, groupe, secteur,
    # programme / ESI, métier ou prestataire.
    else:
        contrats_value = len(
            liste_refs_valides(
                df_contrats_kpi,
                "contract_reference",
            )
        )

        programmes_value = len(
            liste_refs_valides(
                df_esi_context,
                "esi_reference",
            )
        )

        logements_value = int(
            serie_numerique(
                df_esi_context,
                "nb_logements",
            ).sum()
        )

        equipements_value = int(
            serie_numerique(
                df_esi_context,
                "nb_equipements",
            ).sum()
        )

        contrats_label = "Contrats concernés"
        programmes_label = "ESI concernés"
        logements_label = "Logements rattachés"
        equipements_label = "Équipements rattachés"

        contrats_pill = ""
        contrats_help = ""

        programmes_pill = ""
        programmes_help = ""

        logements_pill = ""
        logements_help = ""

        equipements_pill = ""
        equipements_help = ""

    cartes_compactes = (
        statut_selectionne in {
            "active",
            "inactive",
        }
        or perimetre_filtre_actif
    )



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
                    width="stretch",
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
                    width="stretch",
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
                for col in [
                    "contract_reference",
                    "esi_reference",
                ]
                if col in df_contrats_kpi.columns
            ]

            source_tableau = (
                df_contrats_kpi.drop_duplicates(
                    cles_dedoublonnage
                ).copy()
                if cles_dedoublonnage
                else df_contrats_kpi.copy()
            )

            # Informations contractuelles complémentaires provenant
            # de dashboard.contrats_prestations.
            if (
                not df_prestations_kpi.empty
                and "contract_reference_3f"
                in df_prestations_kpi.columns
                and "contract_reference"
                in source_tableau.columns
            ):
                colonnes_complementaires = [
                    colonne
                    for colonne in [
                        "contract_reference_3f",
                        "contract_description",
                        "contract_creation_date",
                        "contract_deactivation_date",
                        "contract_last_update_date",
                    ]
                    if colonne
                    in df_prestations_kpi.columns
                ]

                complements_contrats = (
                    df_prestations_kpi[
                        colonnes_complementaires
                    ]
                    .copy()
                )

                # On garde la ligne la plus récente de chaque contrat.
                if (
                    "contract_last_update_date"
                    in complements_contrats.columns
                ):
                    complements_contrats = (
                        complements_contrats
                        .sort_values(
                            [
                                "contract_reference_3f",
                                "contract_last_update_date",
                            ],
                            na_position="last",
                        )
                        .drop_duplicates(
                            "contract_reference_3f",
                            keep="last",
                        )
                    )
                else:
                    complements_contrats = (
                        complements_contrats
                        .drop_duplicates(
                            "contract_reference_3f",
                            keep="last",
                        )
                    )

                complements_contrats = (
                    complements_contrats.rename(
                        columns={
                            "contract_reference_3f":
                            "contract_reference",
                        }
                    )
                )

                # On retire d'abord les éventuelles colonnes existantes
                # pour éviter les suffixes _x et _y.
                colonnes_a_remplacer = [
                    colonne
                    for colonne in [
                        "contract_description",
                        "contract_creation_date",
                        "contract_deactivation_date",
                        "contract_last_update_date",
                    ]
                    if colonne in source_tableau.columns
                ]

                source_tableau = (
                    source_tableau.drop(
                        columns=colonnes_a_remplacer,
                        errors="ignore",
                    )
                    .merge(
                        complements_contrats,
                        on="contract_reference",
                        how="left",
                    )
                )

            table_contrats_complete = (
                preparer_contrats_table(
                    source_tableau
                )
            )

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
        colonnes_contrat_detail = [
            "Description contrat",
            "Date de création Intent",
            "Date de désactivation Intent",
            "Dernière modification",
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
                    colonnes_prestation_principales
                    + colonnes_prestation_detail
                )
                if col in table_contrats_complete.columns
            ]

            colonnes_par_defaut = [
                col
                for col in colonnes_prestation_principales
                if col in colonnes_disponibles
            ]

        elif mode_tableau == "Contrats uniques":
            colonnes_disponibles = [
                col
                for col in (
                    colonnes_contrat
                    + colonnes_contrat_detail
                )
                if col in table_contrats_complete.columns
            ]

            colonnes_par_defaut = [
                col
                for col in colonnes_contrat
                if col in colonnes_disponibles
            ]

        else:
            colonnes_disponibles = [
                col
                for col in (
                    colonnes_contrat
                    + colonnes_contrat_detail
                    + colonnes_rattachement
                )
                if col in table_contrats_complete.columns
            ]

            colonnes_par_defaut = [
                col
                for col in (
                    colonnes_contrat
                    + ["Référence ESI", "Libellé ESI"]
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
            f'<span class="vg-table-summary-value">{format_nombre(nb_contrats_resultat)}</span>'
            f'<span class="vg-table-summary-label">{libelle_contrats}</span>'
            "</div>"
            '<div class="vg-table-summary-separator"></div>'
            '<div class="vg-table-summary-item">'
            f'<span class="vg-table-summary-value">{format_nombre(nb_lignes_resultat)}</span>'
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
                f"{format_nombre(debut + 1)} à "
                f"{format_nombre(min(fin, nb_lignes_resultat))}"
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
            # "Périmètre des contrats actifs et patrimoine associé.",
        )
    elif statut_selectionne == "inactive":
        section(
            "Couverture du patrimoine",
            "Périmètre des contrats inactifs et patrimoine associé.",
        )
    else:
        if perimetre_filtre_actif:
            section(
                "Couverture du patrimoine",
                "Périmètre sélectionné et patrimoine associé.",
            )
        else:
            section(
                "Couverture du patrimoine",
                (
                    "La réalité présente dans Intent, puis la part "
                    "réellement exploitable pour les analyses de couverture."
                ),
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

    # Périmètre obtenu après application d'un ou plusieurs filtres.
    # On affiche uniquement ce que les contrats sélectionnés couvrent,
    # sans introduire ici de notion de taux de couverture.
    else:
        contrats_value = len(
            liste_refs_valides(
                df_contrats_kpi,
                "contract_reference",
            )
        )

        programmes_value = len(
            liste_refs_valides(
                df_esi_context,
                "esi_reference",
            )
        )

        logements_value = int(
            serie_numerique(
                df_esi_context,
                "nb_logements",
            ).sum()
        )

        equipements_value = int(
            serie_numerique(
                df_esi_context,
                "nb_equipements",
            ).sum()
        )

        contrats_label = "Contrats concernés"
        programmes_label = "ESI concernés"
        logements_label = "Logements rattachés"
        equipements_label = "Équipements rattachés"

        contrats_pill = contrats_help = ""
        programmes_pill = programmes_help = ""
        logements_pill = logements_help = ""
        equipements_pill = equipements_help = ""

    # =====================================================
    # SYNTHÈSE MÉTIER DE LA COUVERTURE
    # =====================================================

    df_esi_synthese_couverture = dedupliquer_esi(df_esi_context)
    total_esi_couverture = len(
        liste_refs_valides(
            df_esi_synthese_couverture,
            "esi_reference",
        )
    )

    if statut_selectionne == "inactive":
        refs_contrats_couverture = set(
            liste_refs_valides(
                df_contrats_kpi,
                "esi_reference",
            )
        )
        refs_esi_couverture = set(
            liste_refs_valides(
                df_esi_synthese_couverture,
                "esi_reference",
            )
        )
        nb_esi_couverts_synthese = len(
            refs_contrats_couverture & refs_esi_couverture
        )
    else:
        colonne_couverture_esi = trouver_colonne(
            df_esi_synthese_couverture,
            ["esi_couvert", "nb_contrats_actifs"],
        )
        if colonne_couverture_esi:
            nb_esi_couverts_synthese = int(
                (
                    serie_numerique(
                        df_esi_synthese_couverture,
                        colonne_couverture_esi,
                    ) > 0
                ).sum()
            )
        else:
            nb_esi_couverts_synthese = 0

    nb_esi_sans_contrat_synthese = max(
        total_esi_couverture - nb_esi_couverts_synthese,
        0,
    )
    taux_couverture_synthese = (
        nb_esi_couverts_synthese / total_esi_couverture * 100
        if total_esi_couverture
        else 0.0
    )

    # Un ESI est « équipé non couvert par contrat équipement » lorsqu'il
    # possède au moins un équipement sans aucun contrat rattaché.
    nb_esi_equipes_non_couverts_synthese = int(
        (
            (
                serie_numerique(
                    df_esi_synthese_couverture,
                    "nb_equipements",
                ) > 0
            )
            & (
                serie_numerique(
                    df_esi_synthese_couverture,
                    "nb_equipements_sans_contrat",
                ) > 0
            )
        ).sum()
    )

    couverture_equipements_synthese = (
        construire_couverture_reelle_equipements(
            df_equipements=df_equipements_couverture_kpi,
            statut=statut_selectionne,
        )
    )

    if couverture_equipements_synthese.empty:
        nb_equipements_couverts_synthese = 0
        nb_equipements_sans_contrat_synthese = 0
        total_equipements_synthese = 0
    else:
        ligne_equipements_couverts = couverture_equipements_synthese[
            couverture_equipements_synthese["Couverture"]
            == "Équipements avec contrat"
        ]
        ligne_equipements_sans_contrat = couverture_equipements_synthese[
            couverture_equipements_synthese["Couverture"]
            == "Équipements sans contrat"
        ]

        nb_equipements_couverts_synthese = int(
            ligne_equipements_couverts["Équipements"].sum()
        )
        nb_equipements_sans_contrat_synthese = int(
            ligne_equipements_sans_contrat["Équipements"].sum()
        )
        total_equipements_synthese = int(
            couverture_equipements_synthese["Équipements"].sum()
        )

    taux_equipements_couverts_synthese = (
        nb_equipements_couverts_synthese
        / total_equipements_synthese
        * 100
        if total_equipements_synthese
        else 0.0
    )

    coverage_summary(
        taux_couverture=taux_couverture_synthese,
        nb_esi_couverts=nb_esi_couverts_synthese,
        total_esi=total_esi_couverture,
        nb_esi_equipes_non_couverts=nb_esi_equipes_non_couverts_synthese,
        nb_equipements_sans_contrat=nb_equipements_sans_contrat_synthese,
    )

    coverage_context(
        contrats=contrats_value,
        esi=programmes_value,
        logements=logements_value,
        equipements=equipements_value,
    )

    if statut_selectionne is not None:
        statut_texte = "actifs" if statut_selectionne == "active" else "inactifs"
        # info(
        #     f"Les contrats {statut_texte} sélectionnés sont rattachés à "
        #     f"{fmt_nombre(programmes_value)} ESI, représentant "
        #     f"{fmt_nombre(logements_value)} logements et "
        #     f"{fmt_nombre(equipements_value)} équipements. "
        #     "Seuls les contrats rattachés à un ESI sont inclus."
        # )


    with st.expander(
        "Comprendre la couverture des ESI",
        expanded=True,
    ):
        st.markdown("<br>", unsafe_allow_html=True)
        section(
            "Comprendre la couverture des ESI",
            # "Lire le patrimoine en trois étapes : composition, couverture et intensité contractuelle.",
        )

        st.markdown(
            """
            <div class="vg-reading-note">
                <strong>Lecture :</strong> la couverture contractuelle mesure la présence
                d’au moins un contrat actif sur l’ESI. La couverture par contrat équipement vérifie,
                pour les ESI équipés, que chaque équipement possède au moins un contrat rattaché.
            </div>
            """,
            unsafe_allow_html=True,
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

        def taux_sur(nombre: int, base: int) -> float:
            return nombre / base * 100 if base else 0.0

        nb_esi_avec_equipement = compter_indicateur(
            "esi_avec_equipement"
        )
        nb_esi_sans_equipement = max(
            total_esi_situation - nb_esi_avec_equipement,
            0,
        )

        # La couverture par contrat équipement ne dépend pas du statut Intent :
        # - couvert : ESI équipé dont aucun équipement n'est sans contrat ;
        # - non couvert : ESI équipé ayant au moins un équipement sans contrat.
        masque_esi_equipes = (
            serie_numerique(df_esi_situation, "nb_equipements") > 0
        )
        masque_esi_equipes_non_couverts = (
            masque_esi_equipes
            & (
                serie_numerique(
                    df_esi_situation,
                    "nb_equipements_sans_contrat",
                ) > 0
            )
        )
        masque_esi_equipes_couverts = (
            masque_esi_equipes
            & ~masque_esi_equipes_non_couverts
        )

        nb_esi_avec_contrat_equipement = int(
            masque_esi_equipes_couverts.sum()
        )
        nb_esi_sans_contrat_equipement = int(
            masque_esi_equipes_non_couverts.sum()
        )
        base_esi_equipes = nb_esi_avec_equipement

        colonne_multi_metier = (
            "esi_multi_meme_metier_valide"
            if statut_selectionne == "active"
            else "esi_multi_meme_metier"
        )

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

        taux_contractuel = taux_sur(
            nb_esi_avec_contrat_programme,
            total_esi_situation,
        )
        taux_reel_equipements = taux_sur(
            nb_esi_avec_contrat_equipement,
            base_esi_equipes,
        )

        step_header(
            1,
            "Composition du patrimoine",
            "Répartition des ESI selon la présence ou non d’équipements.",
        )

        parc_cols = st.columns(3)
        with parc_cols[0]:
            park_summary_card(
                "Total des ESI",
                total_esi_situation,
                None,
                "#67AFCF",
            )
        with parc_cols[1]:
            park_summary_card(
                "ESI avec équipements",
                nb_esi_avec_equipement,
                taux_sur(nb_esi_avec_equipement, total_esi_situation),
                "#173B69",
            )
        with parc_cols[2]:
            park_summary_card(
                "ESI sans équipement",
                nb_esi_sans_equipement,
                taux_sur(nb_esi_sans_equipement, total_esi_situation),
                "#D7A93C",
            )

        step_header(
            2,
            "Couverture contractuelle et couverture réelle",
            "Deux lectures complémentaires pour mesurer la qualité de la couverture.",
        )

        col_contractuelle, col_reelle = st.columns(
            2,
            gap="medium",
        )

        with col_contractuelle:
            coverage_reading_card(
                eyebrow="Couverture contractuelle",
                title="ESI disposant d’un contrat actif",
                question="Combien d’ESI disposent d’au moins un contrat actif ?",
                rate=taux_contractuel,
                covered=nb_esi_avec_contrat_programme,
                uncovered=nb_esi_sans_contrat_programme,
                base_label=f"{fmt_nombre(total_esi_situation)} ESI",
                color="#D65A83",
                gap_color="#F2D6E0",
                covered_label="Avec contrat actif",
                uncovered_label="Sans contrat actif",
            )

        with col_reelle:
            coverage_reading_card(
                eyebrow="Couverture par contrat équipement",
                title="ESI équipés couverts par contrat équipement",
                question="Parmi les ESI équipés, combien n’ont aucun équipement sans contrat ?",
                rate=taux_reel_equipements,
                covered=nb_esi_avec_contrat_equipement,
                uncovered=nb_esi_sans_contrat_equipement,
                base_label=f"{fmt_nombre(base_esi_equipes)} ESI équipés analysables",
                color="#4F9B88",
                gap_color="#F2C9D8",
                covered_label="Tous les équipements ont un contrat",
                uncovered_label="Au moins un équipement sans contrat",
            )

        # Un nombre de contrats DISTINCTS par ESI, zéro inclus.
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

        nb_0_contrat = int(
            (repartition_contrats_esi["nb_contrats"] == 0).sum()
        )
        nb_1_a_3 = int(
            repartition_contrats_esi["nb_contrats"].between(1, 3).sum()
        )
        nb_4_plus = int(
            (repartition_contrats_esi["nb_contrats"] >= 4).sum()
        )
        # Multi-contrats même métier :
        # un ESI est compté lorsqu'au moins un métier possède
        # 2 contrats ACTIFS DISTINCTS ou plus sur cet ESI.
        colonnes_multi_requises = {
            "esi_reference",
            "contract_reference",
            "contract_topic",
        }

        if (
            not df_contrats_kpi.empty
            and colonnes_multi_requises.issubset(df_contrats_kpi.columns)
        ):
            contrats_multi_source = df_contrats_kpi[
                df_contrats_kpi["esi_reference"].notna()
                & df_contrats_kpi["contract_reference"].notna()
                & df_contrats_kpi["contract_topic"].notna()
            ].copy()

            contrats_multi_source["contract_topic"] = (
                contrats_multi_source["contract_topic"]
                .astype(str)
                .str.strip()
            )

            contrats_multi_source = contrats_multi_source[
                ~contrats_multi_source["contract_topic"].isin(
                    ["", "nan", "None", "<NA>", "Non renseigné"]
                )
            ].copy()

            multi_par_esi_metier = (
                contrats_multi_source
                .groupby(
                    ["esi_reference", "contract_topic"],
                    as_index=False,
                )
                .agg(
                    nb_contrats_distincts=(
                        "contract_reference",
                        "nunique",
                    )
                )
            )

            esi_multi_meme_metier = multi_par_esi_metier[
                multi_par_esi_metier["nb_contrats_distincts"] >= 2
            ]["esi_reference"].dropna().unique()

            nb_esi_multi_metier = int(len(esi_multi_meme_metier))
        else:
            nb_esi_multi_metier = 0

        step_header(
            3,
            "Intensité contractuelle",
            "Répartition du nombre de contrats actifs distincts par ESI.",
        )

        intensity_distribution_html(
            [
                {
                    "label": "4 contrats actifs ou plus",
                    "count": nb_4_plus,
                    "rate": taux_sur(nb_4_plus, total_esi_situation),
                    "color": "#173B69",
                },
                {
                    "label": "1 à 3 contrats actifs",
                    "count": nb_1_a_3,
                    "rate": taux_sur(nb_1_a_3, total_esi_situation),
                    "color": "#67AFCF",
                },
                {
                    "label": "Aucun contrat actif",
                    "count": nb_0_contrat,
                    "rate": taux_sur(nb_0_contrat, total_esi_situation),
                    "color": "#D65A83",
                },
            ]
        )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        intensite_kpi_cols = st.columns(3)
        with intensite_kpi_cols[0]:
            intensity_kpi(
                "Moyenne",
                f"{moyenne_contrats_esi:.2f}".replace(".", ","),
                "Contrats actifs distincts par ESI, zéro inclus.",
                "#4F9B88",
            )
        with intensite_kpi_cols[1]:
            intensity_kpi(
                "Médiane",
                f"{mediane_contrats_esi:.0f}".replace(".", ","),
                "La moitié des ESI en possède autant ou moins.",
                "#67AFCF",
            )
        with intensite_kpi_cols[2]:
            intensity_kpi(
                "ESI avec plusieurs contrats actifs sur un même métier",
                fmt_nombre(nb_esi_multi_metier),
                "Au moins 2 contrats actifs distincts pour un même métier.",
                "#D65A83",
            )

        st.caption(
            "Les contrats sont dédupliqués par référence pour chaque ESI. "
            "Les ESI sans contrat sont conservés avec la valeur zéro. "
            "Le multi-contrats même métier correspond aux ESI ayant au moins "
            "2 contrats actifs distincts sur un même métier."
        )


    # =====================================================
    # ÉQUIPEMENTS DU PATRIMOINE
    # =====================================================

    with st.expander(
        "Équipements du patrimoine",
        expanded=True,
    ):
        st.markdown("<br>", unsafe_allow_html=True)
        section(
            "Équipements du patrimoine",
            # "Comprendre la composition du parc et les équipements encore sans rattachement contractuel.",
        )

        # Base du périmètre issue des filtres globaux.
        df_equipements_analyse = (
            df_equipements_couverture_kpi.copy()
        )

        colonne_type_analyse = next(
            (
                candidate
                for candidate in [
                    "equipment_type_normalise",
                    "equipment_type",
                    "equipment_asset_type",
                ]
                if candidate in df_equipements_analyse.columns
            ),
            None,
        )

        type_equipement_selectionne = "Tous les types"
        types_disponibles_analyse = []
        serie_types_analyse = pd.Series(
            index=df_equipements_analyse.index,
            dtype="string",
        )

        if colonne_type_analyse is not None:
            if (
                colonne_type_analyse
                == "equipment_type_normalise"
            ):
                serie_types_analyse = (
                    df_equipements_analyse[
                        colonne_type_analyse
                    ]
                    .fillna("Non renseigné")
                    .astype(str)
                    .str.strip()
                    .replace(
                        {
                            "": "Non renseigné",
                            "nan": "Non renseigné",
                            "None": "Non renseigné",
                            "<NA>": "Non renseigné",
                        }
                    )
                )
            else:
                serie_types_analyse = (
                    df_equipements_analyse[
                        colonne_type_analyse
                    ]
                    .map(normaliser_type_equipement)
                    .fillna("Non renseigné")
                    .astype(str)
                    .str.strip()
                    .replace(
                        {
                            "": "Non renseigné",
                            "nan": "Non renseigné",
                            "None": "Non renseigné",
                            "<NA>": "Non renseigné",
                        }
                    )
                )

            types_disponibles_analyse = sorted(
                serie_types_analyse
                .drop_duplicates()
                .tolist()
            )

            options_types_analyse = [
                "Tous les types",
                *types_disponibles_analyse,
            ]

            type_equipement_selectionne = str(
                st.session_state.get(
                    "filtre_analyse_type_equipement",
                    "Tous les types",
                )
                or "Tous les types"
            )

            if (
                type_equipement_selectionne
                not in options_types_analyse
            ):
                type_equipement_selectionne = "Tous les types"
                st.session_state[
                    "filtre_analyse_type_equipement"
                ] = "Tous les types"

            if (
                type_equipement_selectionne
                != "Tous les types"
            ):
                df_equipements_analyse = (
                    df_equipements_analyse.loc[
                        serie_types_analyse
                        == type_equipement_selectionne
                    ]
                    .copy()
                )

        repartition_types = (
            construire_repartition_types_equipement(
                df_equipements=df_equipements_analyse,
                statut=statut_selectionne,
                top_n=12,
            )
        )
        couverture_equipements = (
            construire_couverture_reelle_equipements(
                df_equipements=df_equipements_analyse,
                statut=statut_selectionne,
            )
        )

        def valeur_couverture_equipement(
            libelle: str,
            colonne: str,
            valeur_par_defaut: float = 0.0,
        ) -> float:
            if couverture_equipements.empty:
                return valeur_par_defaut

            valeurs = couverture_equipements.loc[
                couverture_equipements["Couverture"] == libelle,
                colonne,
            ]
            if valeurs.empty:
                return valeur_par_defaut

            valeur = pd.to_numeric(valeurs.iloc[0], errors="coerce")
            return valeur_par_defaut if pd.isna(valeur) else float(valeur)

        total_equipements_couverture = int(
            couverture_equipements["Équipements"].sum()
        ) if not couverture_equipements.empty else 0

        nb_equipements_avec_contrat = int(
            valeur_couverture_equipement(
                "Équipements avec contrat",
                "Équipements",
            )
        )
        nb_equipements_sans_contrat = int(
            valeur_couverture_equipement(
                "Équipements sans contrat",
                "Équipements",
            )
        )
        taux_equipements_avec_contrat = (
            nb_equipements_avec_contrat
            / total_equipements_couverture
            * 100
            if total_equipements_couverture
            else 0.0
        )

        definition_couverture = (
            "un contrat actif valide"
            if statut_selectionne == "active"
            else "un contrat inactif"
            if statut_selectionne == "inactive"
            else "au moins un contrat actif ou inactif"
        )

        if type_equipement_selectionne != "Tous les types":
            definition_couverture = (
                f"{definition_couverture} pour la catégorie "
                f"« {type_equipement_selectionne} »"
            )

        titre_couverture_equipement = (
            "Mesurer la couverture du parc"
            if type_equipement_selectionne == "Tous les types"
            else (
                "Mesurer la couverture — "
                f"{type_equipement_selectionne}"
            )
        )

        step_header(
            1,
            titre_couverture_equipement,
            " ",
        )

        equipment_overview(
            total=total_equipements_couverture,
            covered=nb_equipements_avec_contrat,
            uncovered=nb_equipements_sans_contrat,
            rate=taux_equipements_avec_contrat,
            definition=definition_couverture,
        )

        step_header(
            2,
            "Comprendre la composition du parc",
            "",
        )

        equipment_types_panel(
            dataframe=repartition_types,
            total=total_equipements_couverture,
            maximum=7,
        )

        if colonne_type_analyse is not None:
            st.markdown(
                """
                <div class="vg-equipment-category-bar">
                    <div class="vg-equipment-category-bar-title">
                        Explorer une catégorie
                    </div>
                    <div class="vg-equipment-category-bar-help">
                        La sélection met à jour l’indicateur de couverture,
                        le graphique et le tableau de détail.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.selectbox(
                "Catégorie d’équipement",
                options=[
                    "Tous les types",
                    *types_disponibles_analyse,
                ],
                key="filtre_analyse_type_equipement",
                label_visibility="collapsed",
            )
            if type_equipement_selectionne != "Tous les types":
                st.markdown(
                    f"""
                    <div class="vg-drilldown-summary">
                        <span class="vg-drilldown-pill">
                            {_safe(type_equipement_selectionne)}
                        </span>
                        <span class="vg-drilldown-pill">
                            {fmt_nombre(total_equipements_couverture)} équipements
                        </span>
                        <span class="vg-drilldown-pill">
                            {fmt_pourcentage(taux_equipements_avec_contrat)} couverts
                        </span>
                        <span class="vg-drilldown-pill">
                            {fmt_nombre(nb_equipements_sans_contrat)} non couverts
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        libelle_detail_equipements = (
            "Afficher le détail des équipements"
            if type_equipement_selectionne == "Tous les types"
            else f"Afficher le détail — {type_equipement_selectionne}"
        )

        afficher_detail_equipements = st.toggle(
            libelle_detail_equipements,
            value=False,
            key="afficher_detail_equipements",
        )

        if afficher_detail_equipements:
            # Le détail reprend la catégorie choisie au-dessus.
            detail_equipements = df_equipements_analyse.copy()

            st.markdown(
                '<div class="vg-mini-title">Filtrer le détail</div>',
                unsafe_allow_html=True,
            )

            statut_couverture_selectionne = st.radio(
                "État de couverture",
                options=[
                    "Tous",
                    "Couverts",
                    "Non couverts",
                ],
                horizontal=True,
                key="filtre_statut_couverture_equipement",
                label_visibility="collapsed",
            )

            # Le sens de « couvert » suit le statut contractuel global.
            if statut_selectionne == "active":
                masque_couverture_detail = (
                    serie_numerique(
                        detail_equipements,
                        "equipment_covered_valid",
                    ) > 0
                )
            elif statut_selectionne == "inactive":
                masque_couverture_detail = (
                    serie_numerique(
                        detail_equipements,
                        "nb_contrats_inactifs",
                    ) > 0
                )
            else:
                masque_couverture_detail = (
                    serie_numerique(
                        detail_equipements,
                        "equipment_has_contract_link",
                    ) > 0
                )

            if statut_couverture_selectionne == "Couverts":
                detail_equipements = detail_equipements[
                    masque_couverture_detail
                ].copy()

            elif statut_couverture_selectionne == "Non couverts":
                detail_equipements = detail_equipements[
                    ~masque_couverture_detail
                ].copy()

            colonne_recherche, colonne_effacer = st.columns(
                [0.95, 0.05],
                gap="small",
            )

            with colonne_recherche:
                recherche_equipement = st.text_input(
                    "Rechercher un équipement",
                    placeholder=(
                        "Référence, type, ESI, société, agence..."
                    ),
                    key="recherche_detail_equipement",
                )

            with colonne_effacer:
                if str(
                    recherche_equipement or ""
                ).strip():
                    st.button(
                        "✕",
                        key="effacer_recherche_equipement",
                        on_click=effacer_recherche_equipement,
                    )

            recherche_equipement = str(
                recherche_equipement or ""
            ).strip()

            if recherche_equipement:
                detail_equipements = filtrer_table_recherche(
                    detail_equipements,
                    recherche_equipement,
                )

            table_detail_equipements = preparer_equipements_table(
                detail_equipements
            )

            nb_resultats_detail = len(
                table_detail_equipements
            )

            libelle_statut_detail = {
                "Tous": "tous les états",
                "Couverts": "couverts",
                "Non couverts": "non couverts",
            }.get(
                statut_couverture_selectionne,
                "tous les états",
            )

            st.caption(
                f"{fmt_nombre(nb_resultats_detail)} équipement(s) "
                f"{libelle_statut_detail} affiché(s)."
            )

            st.dataframe(
                table_detail_equipements,
                width="stretch",
                hide_index=True,
                height=430,
            )

            dataframe_download(
                "⬆ Exporter le détail",
                table_detail_equipements,
                (
                    "detail_equipements.xlsx"
                    if type_equipement_selectionne == "Tous les types"
                    else (
                        "detail_equipements_"
                        + re.sub(
                            r"[^a-zA-Z0-9_-]+",
                            "_",
                            type_equipement_selectionne,
                        ).strip("_")
                        + ".xlsx"
                    )
                ),
                cle="export_detail_equipements",
            )



    with st.expander(
        "Couverture par métier",
        expanded=False,
    ):
        # =====================================================
        # MÉTIERS ET ÉQUIPEMENTS
        # =====================================================

        section(
            "Couverture par métier",
            # "Tous les métiers présents sur les ESI du périmètre actif.",
        )

        # -----------------------------------------------------
        # 1. PRÉSENCE DES CONTRATS PAR MÉTIER — PLEINE LARGEUR
        # -----------------------------------------------------
        st.markdown(
            '<div class="vg-mini-title">ESI concernés par métier</div>',
            unsafe_allow_html=True,
        )
        total_esi_metiers = int(
            dedupliquer_esi(df_esi_context)["esi_reference"].nunique()
            if (
                not df_esi_context.empty
                and "esi_reference" in df_esi_context.columns
            )
            else 0
        )
        tous_les_metiers = (
            df_contrats["contract_topic"]
            .fillna("Non renseigné")
            .astype(str)
            .str.strip()
            .replace("", "Non renseigné")
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

        presence_metiers = construire_presence_metiers(
            df_contrats=df_contrats_kpi,
            total_esi=total_esi_metiers,
            tous_les_metiers=tous_les_metiers,
            top_n=10_000,
        )

        st.caption(
            f"Base analysée : {fmt_nombre(total_esi_metiers)} ESI. "
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
                width="stretch",
                config=config_plotly("presence_contrats_par_metier"),
            )

        st.caption(
            "Lecture : chaque barre répond à la question « Mes contrats pour ce métier couvrent combien d'ESI ?». "
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



    afficher_evolution_couverture_esi(
        df_esi_base=df_esi_base,
        df_contrats_base=df_contrats_filtre,
        df_prestations=df_prestations,
    )



# =====================================================
# VUE 3 — ALERTES OPÉRATIONNELLES
# =====================================================

elif vue_active == "Alertes":
    section(
        "Alertes opérationnelles",
        "Prioriser les situations qui nécessitent une action, une régularisation ou un contrôle.",
    )

    # -------------------------------------------------
    # 1. CONTRATS ACTIFS DONT LA DATE DE FIN EST DÉPASSÉE
    # -------------------------------------------------
    # Même calcul et même source que la synthèse utilisée avant le filtre
    # de statut dans Vue globale / Couverture.
    #
    # contrats_expires_entree est construit à partir de df_contrats_filtre :
    # - statut Intent nettoyé = active ;
    # - date de fin renseignée ;
    # - date de fin strictement antérieure à aujourd'hui ;
    # - une seule ligne par contract_reference.
    #
    # Le même DataFrame alimente la carte ET le tableau de détail.
    alertes_contrats_expires = contrats_expires_entree.copy()

    # -------------------------------------------------
    # 2. ESI SANS CONTRAT ACTIF
    # -------------------------------------------------
    alertes_esi_sans_contrat = df_esi_context[
        serie_numerique(df_esi_context, "nb_contrats_actifs") == 0
    ].copy()

    # -------------------------------------------------
    # 3. ESI ÉQUIPÉS AVEC AU MOINS UN ÉQUIPEMENT SANS CONTRAT
    # -------------------------------------------------
    # Définition métier :
    # l'ESI possède au moins un équipement et au moins un de ses équipements
    # ne possède aucun contrat rattaché.
    masque_esi_equipes_non_couverts = (
        (serie_numerique(df_esi_context, "nb_equipements") > 0)
        & (
            serie_numerique(
                df_esi_context,
                "nb_equipements_sans_contrat",
            ) > 0
        )
    )
    alertes_esi_equipes_non_couverts = df_esi_context[
        masque_esi_equipes_non_couverts
    ].copy()

    # Liste précise des équipements sans contrat actif.
    # Cette liste sert à alimenter la carte et le niveau de détail
    # "Équipements sans contrat".
    if not df_equipements_couverture_kpi.empty:
        masque_equipements_sans_contrat = (
            serie_numerique(
                df_equipements_couverture_kpi,
                "equipment_covered_valid",
            ) == 0
        )

        alertes_equipements_sans_contrat = (
            df_equipements_couverture_kpi[
                masque_equipements_sans_contrat
            ]
            .copy()
        )

        if "equipment_reference" in alertes_equipements_sans_contrat.columns:
            references_valides = (
                alertes_equipements_sans_contrat["equipment_reference"]
                .astype("string")
                .str.strip()
            )

            alertes_equipements_sans_contrat = (
                alertes_equipements_sans_contrat[
                    references_valides.notna()
                    & ~references_valides.isin(
                        ["", "nan", "None", "<NA>", "Non renseigné"]
                    )
                ]
                .drop_duplicates(subset=["equipment_reference"])
                .copy()
            )
    else:
        alertes_equipements_sans_contrat = pd.DataFrame()

    # -------------------------------------------------
    # 4. CONTRATS SANS RATTACHEMENT À UN PROGRAMME / ESI
    # -------------------------------------------------
    contrats_source_alertes = construire_contrats_uniques_source(
        df_prestations=df_prestations,
        df_contrats_rattaches=df_contrats,
    )

    if (
        not contrats_source_alertes.empty
        and "esi_reference" in contrats_source_alertes.columns
    ):
        alertes_contrats_sans_rattachement = contrats_source_alertes[
            contrats_source_alertes["esi_reference"].isna()
            | contrats_source_alertes["esi_reference"]
                .astype(str)
                .str.strip()
                .isin(["", "nan", "None", "<NA>", "Non renseigné"])
        ].copy()
    else:
        alertes_contrats_sans_rattachement = pd.DataFrame()

    # -------------------------------------------------
    # 5. PLUSIEURS CONTRATS SUR LE MÊME MÉTIER
    # -------------------------------------------------
    alertes_multi_metier = df_esi_context[
        serie_numerique(df_esi_context, "esi_multi_meme_metier") > 0
    ].copy()

    nb_contrats_expires = int(
        alertes_contrats_expires["contract_reference"].nunique()
        if "contract_reference" in alertes_contrats_expires.columns
        else len(alertes_contrats_expires)
    )

    nb_esi_sans_contrat = int(
        alertes_esi_sans_contrat["esi_reference"].nunique()
        if "esi_reference" in alertes_esi_sans_contrat.columns
        else len(alertes_esi_sans_contrat)
    )

    nb_esi_equipes_non_couverts = int(
        alertes_esi_equipes_non_couverts["esi_reference"].nunique()
        if "esi_reference" in alertes_esi_equipes_non_couverts.columns
        else len(alertes_esi_equipes_non_couverts)
    )

    nb_equipements_sans_contrat = int(
        alertes_equipements_sans_contrat["equipment_reference"].nunique()
        if (
            not alertes_equipements_sans_contrat.empty
            and "equipment_reference"
            in alertes_equipements_sans_contrat.columns
        )
        else len(alertes_equipements_sans_contrat)
    )

    nb_contrats_sans_rattachement = int(
        alertes_contrats_sans_rattachement["contract_reference"].nunique()
        if (
            not alertes_contrats_sans_rattachement.empty
            and "contract_reference" in alertes_contrats_sans_rattachement.columns
        )
        else int(global_value(df_global, "contrats_non_rattaches_programme", 0))
    )

    nb_esi_multi_metier = int(
        alertes_multi_metier["esi_reference"].nunique()
        if "esi_reference" in alertes_multi_metier.columns
        else len(alertes_multi_metier)
    )

    nb_alertes_prioritaires = (
        nb_contrats_expires
        + nb_contrats_sans_rattachement
        + nb_equipements_sans_contrat
    )
    nb_alertes_a_traiter = nb_esi_sans_contrat
    nb_alertes_a_controler = nb_esi_multi_metier

    total_alertes = (
        nb_alertes_prioritaires
        + nb_alertes_a_traiter
        + nb_alertes_a_controler
    )

    if total_alertes == 0:
        status_banner(
            "Aucune alerte détectée",
            "Aucune situation nécessitant une action n'est remontée sur le périmètre sélectionné.",
            C_TEAL,
            "#F1FBF8",
            "#CFECE3",
        )
    else:
        alerts_hero(
            total=total_alertes,
            prioritaires=nb_alertes_prioritaires,
            a_traiter=nb_alertes_a_traiter,
            a_controler=nb_alertes_a_controler,
        )

    # -------------------------------------------------
    # ALERTES PRIORITAIRES
    # -------------------------------------------------
    alert_zone_title("Prioritaires — action recommandée", C_RED)

    ligne_prioritaire = st.columns(3)

    with ligne_prioritaire[0]:
        impact_alert_card(
            "Contrats actifs expirés",
            nb_contrats_expires,
            " ",
            C_RED,
            "Prioritaire",
            "!",
        )

    with ligne_prioritaire[1]:
        impact_alert_card(
            "Contrats sans rattachement",
            nb_contrats_sans_rattachement,
            " ",
            "#D06B2C",
            "Prioritaire",
            "↗",
        )

    with ligne_prioritaire[2]:
        impact_alert_card(
            "Équipements sans contrat",
            nb_equipements_sans_contrat,
            (
                f"Répartis dans {fmt_nombre(nb_esi_equipes_non_couverts)} ESI. "
                " "
            ),
            C_VIOLET,
            "Prioritaire",
            "◆",
        )

    # -------------------------------------------------
    # À TRAITER / À CONTRÔLER
    # -------------------------------------------------
    alert_zone_title("À traiter et à contrôler", "#E5A000")

    ligne_secondaire = st.columns(2)

    with ligne_secondaire[0]:
        impact_alert_card(
            "ESI sans contrat actif",
            nb_esi_sans_contrat,
            " ",
            "#E5A000",
            "À traiter",
            "•",
        )

    with ligne_secondaire[1]:
        impact_alert_card(
            "Multi-contrats même métier",
            nb_esi_multi_metier,
            " ",
            C_NAVY,
            "À contrôler",
            "≡",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    section(
        "Traiter les alertes",
        "Choisis une catégorie pour comprendre la situation et afficher les objets concernés.",
    )

    libelles_alertes = {
        "Expirés": "Contrats actifs expirés",
        "Sans contrat": "ESI sans contrat actif",
        "Non couverts": "ESI équipés avec équipement sans contrat",
        "Non rattachés": "Contrats sans rattachement",
        "Multi-contrats": "Multi-contrats sur un même métier",
    }

    choix_court = st.radio(
        "Catégorie d'alerte",
        list(libelles_alertes.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="alertes_navigation_rapide",
    )
    type_alerte = libelles_alertes[choix_court]

    if type_alerte == "Contrats actifs expirés":
        if "contract_reference_3f" in alertes_contrats_expires.columns:
            table_alerte = preparer_prestations_table(
                alertes_contrats_expires
            )

            # Colonnes affichées uniquement dans le détail des alertes
            colonnes_alertes_contrats_expires = [
                "Référence contrat 3F",
                "Référence contrat prestataire",
                "Libellé contrat",
                "Description contrat",
                "Prestataire",
                "Métier",
                "Statut",
                "Date de début",
                "Date de fin",
            ]

            colonnes_disponibles = [
                colonne
                for colonne in colonnes_alertes_contrats_expires
                if colonne in table_alerte.columns
            ]

            table_alerte = table_alerte[
                colonnes_disponibles
            ].copy()

        else:
            table_alerte = preparer_contrats_table(
                alertes_contrats_expires
            )

            colonnes_alertes_contrats_expires = [
                "Référence contrat",
                "Libellé contrat",
                "Description contrat",
                "Prestataire",
                "Métier",
                "Statut",
                "Date de début",
                "Date de fin",
            ]

            colonnes_disponibles = [
                colonne
                for colonne in colonnes_alertes_contrats_expires
                if colonne in table_alerte.columns
            ]

            table_alerte = table_alerte[
                colonnes_disponibles
            ].copy()
 
        nom_export = "contrats_actifs_expires.xlsx"

        message_vide = (
            "Aucun contrat actif avec une date de fin dépassée."
        )

        detail_title = (
            f"{fmt_nombre(nb_contrats_expires)} contrat(s) "
            "encore actif(s) malgré une date de fin dépassée"
        )

        detail_message = (
            "Ces contrats doivent être prolongés, désactivés ou corrigés "
            "afin que leur statut corresponde à leur période de validité."
        )

        detail_color = C_RED

    elif type_alerte == "ESI sans contrat actif":
        table_alerte = preparer_esi_table(
            alertes_esi_sans_contrat
        )
        table_alerte = table_alerte.drop(
            columns=[
                "ESI couvert",
                "Multi même métier",
            ],
            errors="ignore",
        )
        nom_export = "esi_sans_contrat_actif.xlsx"
        message_vide = "Aucun ESI sans contrat actif."
        detail_title = (
            f"{fmt_nombre(nb_esi_sans_contrat)} ESI "
            "sans contrat actif"
        )
        detail_message = (
            "Vérifiez si l'absence de contrat est normale ou si un "
            "rattachement contractuel doit être créé ou réactivé."
        )
        detail_color = "#E5A000"

    elif type_alerte == "ESI équipés avec équipement sans contrat":
        niveau_detail_non_couvert = st.radio(
            "Niveau de détail",
            [
                "ESI concernés",
                "Équipements sans contrat",
            ],
            horizontal=True,
            key="alertes_niveau_detail_non_couvert",
        )

        if niveau_detail_non_couvert == "ESI concernés":
            table_alerte = preparer_esi_table(
                alertes_esi_equipes_non_couverts
            )
            nom_export = (
                "esi_equipes_avec_equipement_sans_contrat.xlsx"
            )
            message_vide = (
                "Aucun ESI équipé avec un équipement sans contrat."
            )
            detail_title = (
                f"{fmt_nombre(nb_esi_equipes_non_couverts)} ESI équipé(s) "
                f"contiennent {fmt_nombre(nb_equipements_sans_contrat)} "
                "équipement(s) sans contrat"
            )
            detail_message = (
                "Cette vue présente les ESI concernés. "
                "Un même ESI peut contenir plusieurs équipements sans contrat."
            )
            table_alerte = table_alerte.drop(
                columns=[
                    "ESI couvert",
                    "Multi même métier",
                ],
                errors="ignore",
            )
        else:                                                                                               
            table_alerte = preparer_equipements_table(
                alertes_equipements_sans_contrat
            )
            nom_export = "equipements_sans_contrat.xlsx"
            message_vide = (
                "Aucun équipement sans contrat sur le périmètre sélectionné."
            )
            detail_title = (
                f"{fmt_nombre(nb_equipements_sans_contrat)} "
                "équipement(s) sans contrat"
            )
            detail_message = (
                f"Ces équipements sont répartis dans "
                f"{fmt_nombre(nb_esi_equipes_non_couverts)} ESI. "
                "Cette vue identifie précisément les équipements "
                "pour lesquels un contrat doit être créé ou rattaché."
            )

        detail_color = C_VIOLET

    elif type_alerte == "Contrats sans rattachement":
        table_alerte = preparer_contrats_table(
            alertes_contrats_sans_rattachement
        )
        nom_export = "contrats_sans_rattachement.xlsx"
        message_vide = "Aucun contrat sans rattachement à un programme / ESI."
        detail_title = (
            f"{fmt_nombre(nb_contrats_sans_rattachement)} contrat(s) "
            "sans rattachement patrimonial"
        )
        detail_message = (
            "Ces contrats existent dans Intent mais ne sont reliés à aucun "
            "programme ou ESI, ce qui empêche d'analyser correctement leur couverture."
        )
        detail_color = "#D06B2C"

    else:
        table_alerte = preparer_esi_table(
            alertes_multi_metier
        )

        # Colonnes inutiles uniquement dans le détail Multi-contrats
        table_alerte = table_alerte.drop(
            columns=[
                "ESI couvert",
                "Multi même métier",
            ],
            errors="ignore",
        )

        nom_export = "esi_multi_contrats_meme_metier.xlsx"

        message_vide = (
            "Aucun ESI avec plusieurs contrats sur le même métier."
        )

        detail_title = (
            f"{fmt_nombre(nb_esi_multi_metier)} ESI présentent "
            "plusieurs contrats sur un même métier"
        )

        detail_message = (
            "Ces situations ne sont pas automatiquement anormales. "
            "Elles doivent être contrôlées pour identifier les chevauchements "
            "réels et les cas métier légitimes."
        )

        detail_color = C_NAVY

    alert_detail_intro(
        detail_title,
        detail_message,
        detail_color,
    )

    recherche_alerte = st.text_input(
        "Rechercher dans le détail",
        placeholder="Référence, libellé, société, agence, métier ou prestataire.",
        key="alertes_recherche_detail",
    )

    table_alerte = filtrer_table_recherche(
        table_alerte,
        recherche_alerte,
    )

    if table_alerte.empty:
        st.success(message_vide)
    else:
        st.dataframe(
            table_alerte,
            width="stretch",
            hide_index=True,
            height=520,
        )
        dataframe_download(
            "Télécharger le détail des alertes",
            table_alerte,
            nom_export,
            cle="export_detail_alertes",
        )


# =====================================================
# VUE 4 — ANOMALIES DE RATTACHEMENT
# =====================================================

else:
    section(
        "Anomalies de rattachement",
        "Identifier les objets qui ne peuvent pas être replacés correctement dans la hiérarchie patrimoine.",
    )

    # -------------------------------------------------
    # 1. PROGRAMMES SANS LOGEMENT
    # -------------------------------------------------
    anomalies_programmes_sans_logement = df_esi_context[
        serie_numerique(df_esi_context, "nb_logements") == 0
    ].copy()

    # -------------------------------------------------
    # 2. LOGEMENTS ET ÉQUIPEMENTS SANS PROGRAMME
    # -------------------------------------------------
    if not df_qualite.empty and "anomalie_type" in df_qualite.columns:
        types_qualite = (
            df_qualite["anomalie_type"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )

        anomalies_logements_sans_programme = df_qualite[
            types_qualite == "LOGEMENT_SANS_PROGRAMME"
        ].copy()

        anomalies_equipements_sans_programme = df_qualite[
            types_qualite == "EQUIPEMENT_SANS_PROGRAMME"
        ].copy()
    else:
        anomalies_logements_sans_programme = pd.DataFrame()
        anomalies_equipements_sans_programme = pd.DataFrame()

    nb_programmes_sans_logement = int(
        anomalies_programmes_sans_logement["esi_reference"].nunique()
        if "esi_reference" in anomalies_programmes_sans_logement.columns
        else len(anomalies_programmes_sans_logement)
    )

    nb_logements_sans_programme_detail = compter_objets_distincts(
        anomalies_logements_sans_programme,
        trouver_colonne(
            anomalies_logements_sans_programme,
            ["objet_reference", "housing_reference", "logement_reference"],
        ),
    )
    nb_logements_sans_programme = max(
        nb_logements_sans_programme_detail,
        int(global_value(df_global, "logements_sans_programme", 0)),
    )

    nb_equipements_sans_programme_detail = compter_objets_distincts(
        anomalies_equipements_sans_programme,
        trouver_colonne(
            anomalies_equipements_sans_programme,
            ["objet_reference", "equipment_reference"],
        ),
    )
    nb_equipements_sans_programme = max(
        nb_equipements_sans_programme_detail,
        int(global_value(df_global, "equipements_sans_programme", 0)),
    )

    total_anomalies_rattachement = (
        nb_programmes_sans_logement
        + nb_logements_sans_programme
        + nb_equipements_sans_programme
    )

    part_logements_sans_programme = (
        nb_logements_sans_programme
        / total_anomalies_rattachement
        * 100
        if total_anomalies_rattachement
        else 0.0
    )

    if total_anomalies_rattachement == 0:
        status_banner(
            "Aucune anomalie de rattachement détectée",
            "Tous les programmes, logements et équipements sont rattachés comme attendu.",
            C_TEAL,
            "#F1FBF8",
            "#CFECE3",
        )
    else:
        anomaly_hero(
            total=total_anomalies_rattachement,
        )

    # -------------------------------------------------
    # SYNTHÈSE VISUELLE
    # -------------------------------------------------
    colonne_principale, colonne_secondaire = st.columns(
        [1.55, 1],
        gap="medium",
    )

    with colonne_principale:
        anomaly_main_card(
            nb_logements_sans_programme,
            part_logements_sans_programme,
        )

    with colonne_secondaire:
        secondaires = st.columns(2)

        with secondaires[0]:
            anomaly_secondary_card(
                "Programmes sans logement",
                nb_programmes_sans_logement,
                "Programmes présents dans le référentiel mais sans aucun logement rattaché.",
                C_NAVY,
                "P",
            )

        with secondaires[1]:
            anomaly_secondary_card(
                "Équipements sans programme",
                nb_equipements_sans_programme,
                "Équipements sans programme ou ESI identifiable.",
                C_VIOLET,
                "E",
            )

    st.markdown("<br>", unsafe_allow_html=True)

    section(
        "Analyser les anomalies",
        "Sélectionne une catégorie pour afficher les objets concernés et les exporter.",
    )

    libelles_anomalies = {
        "Logements": "Logements sans programme",
        "Programmes": "Programmes sans logement",
        "Équipements": "Équipements sans programme",
    }

    choix_anomalie_court = st.radio(
        "Catégorie d'anomalie",
        list(libelles_anomalies.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="anomalies_navigation_rapide",
    )
    type_anomalie = libelles_anomalies[choix_anomalie_court]

    if type_anomalie == "Logements sans programme":
        table_anomalie = preparer_qualite_table(
            anomalies_logements_sans_programme
        )

        colonnes_logements = [
            "Référence objet",
            "Libellé objet",
            "Description",
        ]

        colonnes_disponibles = [
            colonne
            for colonne in colonnes_logements
            if colonne in table_anomalie.columns
        ]

        table_anomalie = table_anomalie[
            colonnes_disponibles
        ].copy()

        table_anomalie = table_anomalie.rename(
            columns={
                "Référence objet": "Référence logement",
                "Libellé objet": "Libellé logement",
            }
        )


        nom_export_anomalie = "logements_sans_programme.xlsx"
        message_anomalie_vide = (
            "Aucun logement sans programme dans la table de qualité."
        )
        titre_detail_anomalie = (
            f"{fmt_nombre(nb_logements_sans_programme)} logement(s) "
            "sans programme"
        )
        message_detail_anomalie = (
            "Ces logements ne peuvent pas être replacés correctement dans la "
            "hiérarchie patrimoine. Leur programme doit être retrouvé ou corrigé."
        )
        couleur_detail_anomalie = C_RED

    elif type_anomalie == "Programmes sans logement":
        table_anomalie = preparer_esi_table(
            anomalies_programmes_sans_logement
        )
        table_anomalie = table_anomalie.drop(
            columns=[
                "ESI couvert",
                "Multi même métier",
            ],
            errors="ignore",
        )
        nom_export_anomalie = "programmes_sans_logement.xlsx"
        message_anomalie_vide = "Aucun programme sans logement."
        titre_detail_anomalie = (
            f"{fmt_nombre(nb_programmes_sans_logement)} programme(s) "
            "sans logement"
        )
        message_detail_anomalie = (
            "Ces programmes existent dans le référentiel mais aucun logement "
            "ne leur est rattaché. Vérifiez s'ils sont réellement vides ou mal alimentés."
        )
        couleur_detail_anomalie = C_NAVY

    else:
        table_anomalie = preparer_qualite_table(
            anomalies_equipements_sans_programme
        )

        colonnes_equipements = [
            "Référence objet",
            "Libellé objet",
            "Description",
        ]

        colonnes_disponibles = [
            colonne
            for colonne in colonnes_equipements
            if colonne in table_anomalie.columns
        ]

        table_anomalie = table_anomalie[
            colonnes_disponibles
        ].copy()

        table_anomalie = table_anomalie.rename(
            columns={
                "Référence objet": "Référence équipement",
                "Libellé objet": "Libellé équipement",
            }
        )
        nom_export_anomalie = "equipements_sans_programme.xlsx"
        message_anomalie_vide = (
            "Aucun équipement sans programme dans la table de qualité."
        )
        titre_detail_anomalie = (
            f"{fmt_nombre(nb_equipements_sans_programme)} équipement(s) "
            "sans programme"
        )
        message_detail_anomalie = (
            "Ces équipements ne peuvent pas être rattachés à un programme ou "
            "à un ESI identifiable. Leur rattachement patrimonial doit être vérifié."
        )
        couleur_detail_anomalie = C_VIOLET

    anomaly_detail_intro(
        titre_detail_anomalie,
        message_detail_anomalie,
        couleur_detail_anomalie,
    )

    recherche_anomalie = st.text_input(
        "Rechercher dans le détail",
        placeholder="Référence, libellé, société, agence, groupe ou secteur.",
        key="anomalies_recherche_detail",
    )

    table_anomalie = filtrer_table_recherche(
        table_anomalie,
        recherche_anomalie,
    )

    if table_anomalie.empty:
        st.info(message_anomalie_vide)

        if type_anomalie != "Programmes sans logement":
            st.caption(
                "Le compteur global peut rester supérieur à zéro si la vue résumé "
                "contient le volume, mais que dashboard.qualite_donnees ne contient "
                "pas encore le détail correspondant."
            )
    else:
        st.dataframe(
            table_anomalie,
            width="stretch",
            hide_index=True,
            height=520,
        )
        dataframe_download(
            "Télécharger le détail des anomalies",
            table_anomalie,
            nom_export_anomalie,
            cle="export_detail_anomalies",
        )

# =====================================================
# FOOTER TECHNIQUE
# =====================================================

if "date_maj" in df_global.columns:
    date_maj = global_value(df_global, "date_maj", "")
    st.caption(f"Dernière mise à jour des tables dashboard : {date_maj}")
