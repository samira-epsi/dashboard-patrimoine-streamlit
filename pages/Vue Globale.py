import html
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
            margin: 0 0 14px 0 !important;
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
            overflow: hidden !important;
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

    except SQLAlchemyError as exc:
        raise RuntimeError(f"Erreur PostgreSQL : {exc}") from exc

    df_esi = nettoyer_df(df_esi)
    df_contrats = normaliser_contrats(df_contrats)
    df_prestations = normaliser_prestations(df_prestations)
    df_equipements_couverture = nettoyer_df(df_equipements_couverture)
    df_equipements_contrats = nettoyer_df(df_equipements_contrats)
    df_creations = normaliser_creations(df_creations)
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
    top_n: int = 15,
) -> pd.DataFrame:
    """
    Une présence métier = au moins un contrat DISTINCT du métier sur l'ESI.
    Le pourcentage est calculé sur tous les ESI du périmètre.
    """
    colonnes = ["Métier", "ESI", "Taux"]
    if (
        df_contrats.empty
        or "esi_reference" not in df_contrats.columns
        or "contract_topic" not in df_contrats.columns
    ):
        return pd.DataFrame(columns=colonnes)

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

    resultat = (
        df.groupby("contract_topic", as_index=False)
        .agg(ESI=("esi_reference", "nunique"))
        .rename(columns={"contract_topic": "Métier"})
    )
    resultat["Taux"] = (
        resultat["ESI"] / total_esi * 100
        if total_esi
        else 0.0
    )

    return (
        resultat.sort_values(["ESI", "Métier"], ascending=[False, True])
        .head(top_n)
        .sort_values("ESI", ascending=True)
        .reset_index(drop=True)
    )


def construire_repartition_types_equipement(
    df_equipements: pd.DataFrame,
    top_n: int = 12,
) -> pd.DataFrame:
    """
    Répartition du parc par type d'équipement.
    Une ligne source = un équipement distinct.
    """
    colonnes = ["Type d’équipement", "Équipements", "ESI", "Part du parc"]
    if df_equipements.empty:
        return pd.DataFrame(columns=colonnes)

    colonne_type = None
    for candidate in ["equipment_type", "equipment_asset_type"]:
        if candidate in df_equipements.columns:
            colonne_type = candidate
            break

    if colonne_type is None or "equipment_reference" not in df_equipements.columns:
        return pd.DataFrame(columns=colonnes)

    df = df_equipements.copy()
    df["Type d’équipement"] = (
        df[colonne_type]
        .fillna("Non renseigné")
        .astype(str)
        .str.strip()
        .replace("", "Non renseigné")
    )

    # Un équipement ne doit compter qu'une seule fois, même s'il existe plusieurs liens.
    df = df.drop_duplicates("equipment_reference")

    agg = {
        "equipment_reference": "nunique",
    }
    if "esi_reference" in df.columns:
        agg["esi_reference"] = "nunique"

    resultat = (
        df.groupby("Type d’équipement", as_index=False)
        .agg(agg)
        .rename(
            columns={
                "equipment_reference": "Équipements",
                "esi_reference": "ESI",
            }
        )
    )
    if "ESI" not in resultat.columns:
        resultat["ESI"] = 0

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
        autres = resultat.iloc[top_n - 1:]
        ligne_autres = pd.DataFrame(
            {
                "Type d’équipement": ["Autres types"],
                "Équipements": [int(autres["Équipements"].sum())],
                "ESI": [int(autres["ESI"].sum())],
                "Part du parc": [float(autres["Part du parc"].sum())],
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
    Classe chaque ESI équipé selon le lien réel équipement → contrat :
    aucun, partiel ou total.

    Tous      : tout contrat directement rattaché.
    Actifs    : contrat actif valide.
    Inactifs  : au moins un contrat inactif rattaché.
    """
    colonnes = ["Niveau de couverture", "ESI", "Taux"]
    requis = {"esi_reference", "equipment_reference"}
    if df_equipements.empty or not requis.issubset(df_equipements.columns):
        return pd.DataFrame(columns=colonnes)

    df = df_equipements.drop_duplicates("equipment_reference").copy()

    if statut == "active":
        indicateur = (
            serie_numerique(df, "equipment_covered_valid") > 0
        )
    elif statut == "inactive":
        indicateur = (
            serie_numerique(df, "nb_contrats_inactifs") > 0
        )
    else:
        indicateur = (
            serie_numerique(df, "equipment_has_contract_link") > 0
        )

    df["_couvert"] = indicateur.astype(int)

    par_esi = (
        df.groupby("esi_reference", as_index=False)
        .agg(
            nb_equipements=("equipment_reference", "nunique"),
            nb_equipements_couverts=("_couvert", "sum"),
        )
    )

    par_esi["Niveau de couverture"] = "Une partie des équipements avec contrat"
    par_esi.loc[
        par_esi["nb_equipements_couverts"] == 0,
        "Niveau de couverture",
    ] = "Aucun équipement avec contrat"
    par_esi.loc[
        (
            par_esi["nb_equipements"] > 0
        )
        & (
            par_esi["nb_equipements_couverts"]
            == par_esi["nb_equipements"]
        ),
        "Niveau de couverture",
    ] = "Tous les équipements avec contrat"

    ordre = [
        "Aucun équipement avec contrat",
        "Une partie des équipements avec contrat",
        "Tous les équipements avec contrat",
    ]

    resultat = (
        par_esi["Niveau de couverture"]
        .value_counts()
        .reindex(ordre, fill_value=0)
        .rename_axis("Niveau de couverture")
        .reset_index(name="ESI")
    )
    total = int(resultat["ESI"].sum())
    resultat["Taux"] = (
        resultat["ESI"] / total * 100
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
        base[col] = pd.to_datetime(base[col], errors="coerce")

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


def dataframe_download(label: str, df: pd.DataFrame, filename: str):
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
        width="stretch",
    )


# =====================================================
# PRÉPARATION DES TABLEAUX
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
    cols = [col for col in cols if col in df.columns]
    out = df[cols].copy()

    for col in ["contract_start_date", "contract_end_date"]:
        if col in out.columns:
            out[col] = (
                pd.to_datetime(out[col], errors="coerce")
                .dt.strftime("%d/%m/%Y")
                .fillna("")
            )

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


def afficher_detail_qualite(
    focus,
    df_contrats_kpi,
    df_esi_context,
    df_qualite,
    df_global,
):
    if not focus:
        return

    st.markdown("---")

    if focus == "expired":
        section(
            "Détail : contrats actifs avec date de fin dépassée",
            "Contrats exploitables dans le périmètre filtré.",
        )
        table = preparer_contrats_table(contrats_actifs_fin_depassee(df_contrats_kpi))
        if table.empty:
            st.success("Aucun contrat actif expiré dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download(
                "Télécharger les contrats expirés",
                table,
                "contrats_actifs_expires.xlsx",
            )

    elif focus == "unlinked_contracts":
        section(
            "Détail : contrats non rattachés",
            "Contrats présents en source mais absents de la couverture programme.",
        )
        if not df_qualite.empty and "anomalie_type" in df_qualite.columns:
            table = df_qualite[
                df_qualite["anomalie_type"] == "CONTRAT_NON_RATTACHE_PROGRAMME"
            ].copy()
        else:
            table = pd.DataFrame()
        table = preparer_qualite_table(table)
        if table.empty:
            st.info("Aucun détail disponible dans la table qualité.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download(
                "Télécharger les contrats non rattachés",
                table,
                "contrats_non_rattaches.xlsx",
            )

    elif focus == "housing":
        section(
            "Détail : logements sans programme",
            "Logements non exploitables dans les calculs de couverture ESI.",
        )
        if not df_qualite.empty and "anomalie_type" in df_qualite.columns:
            table = df_qualite[
                df_qualite["anomalie_type"] == "LOGEMENT_SANS_PROGRAMME"
            ].copy()
        else:
            table = pd.DataFrame()
        table = preparer_qualite_table(table)
        if table.empty:
            st.info("Aucun détail disponible dans la table qualité.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download(
                "Télécharger les logements sans programme",
                table,
                "logements_sans_programme.xlsx",
            )
            if len(table) > 500:
                st.caption(f"Affichage limité à 500 lignes sur {fmt_nombre(len(table))}.")

    elif focus == "multi_topic":
        section(
            "Détail : ESI avec plusieurs contrats actifs sur le même métier",
            "Ce signal peut révéler des doublons ou des chevauchements de contrats.",
        )
        if "esi_multi_meme_metier" not in df_esi_context.columns:
            st.info("La colonne esi_multi_meme_metier n'est pas disponible.")
            return
        table = df_esi_context[
            pd.to_numeric(
                df_esi_context["esi_multi_meme_metier"],
                errors="coerce",
            ).fillna(0) > 0
        ].copy()
        table = preparer_esi_table(table)
        if table.empty:
            st.success("Aucun ESI multi même métier dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download(
                "Télécharger les ESI multi même métier",
                table,
                "esi_multi_meme_metier.xlsx",
            )

    elif focus == "no_contract":
        section(
            "Détail : ESI sans contrat actif",
            "Programmes sans contrat actif rattaché dans le périmètre affiché.",
        )
        table = df_esi_context[
            serie_numerique(df_esi_context, "nb_contrats_actifs") == 0
        ].copy()
        table = preparer_esi_table(table)
        if table.empty:
            st.success("Aucun ESI sans contrat actif dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download(
                "Télécharger les ESI sans contrat actif",
                table,
                "esi_sans_contrat_actif.xlsx",
            )


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

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "Équipements du patrimoine",
        "Quels équipements sont présents et, parmi les ESI équipés, lesquels disposent réellement de contrats sur leurs équipements ?",
    )

    col_types, col_couverture_equipements = st.columns(
        [1.3, 0.9],
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
                    {fmt_nombre(int(repartition_types["Équipements"].sum()) if not repartition_types.empty else 0)} équipements
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if repartition_types.empty:
            st.info("Aucun type d’équipement disponible sur ce périmètre.")
        elif go is None:
            st.bar_chart(
                repartition_types.set_index(
                    "Type d’équipement"
                )["Équipements"],
                width="stretch",
            )
        else:
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
                            PALETTE_3F_GRAPHIQUES[
                                index % len(PALETTE_3F_GRAPHIQUES)
                            ]
                            for index in range(len(repartition_types))
                        ],
                        line=dict(color="#FFFFFF", width=1.5),
                    ),
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Équipements : %{x:,}<br>"
                        "Présents sur %{customdata[0]:,} ESI<br>"
                        "Part du parc : %{customdata[1]:.1f} %"
                        "<extra></extra>"
                    ),
                )
            )
            hauteur_types = max(
                380,
                min(590, 39 * len(repartition_types) + 105),
            )
            _layout_plotly(fig_types, hauteur_types)
            fig_types.update_layout(
                xaxis=dict(
                    title="Nombre d’équipements",
                    gridcolor=C_GRID,
                    tickfont=dict(size=11),
                    rangemode="tozero",
                ),
                yaxis=dict(
                    title=None,
                    automargin=True,
                    tickfont=dict(size=11.5),
                ),
                margin=dict(l=18, r=112, t=10, b=50),
                bargap=0.34,
                showlegend=False,
            )
            st.plotly_chart(
                fig_types,
                use_container_width=True,
                config=config_plotly("repartition_types_equipement"),
            )

    with col_couverture_equipements:
        total_esi_equipes = int(
            couverture_equipements["ESI"].sum()
        ) if not couverture_equipements.empty else 0

        st.markdown(
            f"""
            <div class="vg-chart-intro">
                <div class="vg-chart-question">
                    Les équipements des ESI sont-ils couverts ?
                </div>
                <div class="vg-chart-base">
                    {fmt_nombre(total_esi_equipes)} ESI équipés
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if couverture_equipements.empty:
            st.info("Aucune donnée de couverture équipement disponible.")
        elif go is None:
            st.bar_chart(
                couverture_equipements.set_index(
                    "Niveau de couverture"
                )["ESI"],
                width="stretch",
            )
        else:
            couleurs_couverture = {
                "Aucun équipement avec contrat": "#D83B55",
                "Une partie des équipements avec contrat": "#F4D84E",
                "Tous les équipements avec contrat": "#2F7C6D",
            }

            fig_couverture_equipements = go.Figure(
                go.Pie(
                    labels=couverture_equipements["Niveau de couverture"],
                    values=couverture_equipements["ESI"],
                    hole=0.67,
                    sort=False,
                    direction="clockwise",
                    textinfo="percent",
                    textposition="inside",
                    textfont=dict(size=13, color="#FFFFFF"),
                    marker=dict(
                        colors=[
                            couleurs_couverture.get(label, C_NAVY)
                            for label in couverture_equipements[
                                "Niveau de couverture"
                            ]
                        ],
                        line=dict(color="#FFFFFF", width=4),
                    ),
                    customdata=couverture_equipements["Taux"],
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "ESI : %{value:,}<br>"
                        "Part des ESI équipés : %{customdata:.1f} %"
                        "<extra></extra>"
                    ),
                )
            )

            fig_couverture_equipements.add_annotation(
                text=(
                    f"<b>{fmt_nombre(total_esi_equipes)}</b>"
                    "<br><span style='font-size:11px'>ESI équipés</span>"
                ),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(color=C_INK, size=20),
            )
            _layout_plotly(fig_couverture_equipements, 370)
            fig_couverture_equipements.update_layout(
                showlegend=False,
                margin=dict(l=15, r=15, t=5, b=5),
            )
            st.plotly_chart(
                fig_couverture_equipements,
                use_container_width=True,
                config=config_plotly(
                    "couverture_reelle_des_equipements"
                ),
            )

            lignes_legende = []
            for _, ligne in couverture_equipements.iterrows():
                label = str(ligne["Niveau de couverture"])
                couleur = couleurs_couverture.get(label, C_NAVY)
                lignes_legende.append(
                    f"""
                    <div class="vg-coverage-legend-item">
                        <span class="vg-coverage-dot" style="--dot:{couleur};"></span>
                        <span class="vg-coverage-label">{_safe(label)}</span>
                        <span class="vg-coverage-value">
                            {fmt_nombre(ligne["ESI"])} · {fmt_pourcentage(ligne["Taux"])}
                        </span>
                    </div>
                    """
                )

            st.markdown(
                '<div class="vg-coverage-legend">'
                + "".join(lignes_legende)
                + "</div>",
                unsafe_allow_html=True,
            )

        statut_couverture = (
            "contrats actifs valides"
            if statut_selectionne == "active"
            else "contrats inactifs"
            if statut_selectionne == "inactive"
            else "tous les contrats rattachés"
        )
        st.caption(
            f"Lecture selon les {statut_couverture}. Une couverture partielle signifie "
            "que certains équipements de l’ESI possèdent un contrat, mais pas tous."
        )

    # -----------------------------------------------------
    # DRILL-DOWN ÉQUIPEMENTS
    # -----------------------------------------------------
    with st.expander(
        "Explorer les équipements",
        expanded=False,
    ):
        options_types = (
            repartition_types["Type d’équipement"]
            .astype(str)
            .tolist()
            if not repartition_types.empty
            else []
        )
        options_types = [
            option for option in options_types
            if option != "Autres types"
        ]

        type_selectionne = st.selectbox(
            "Type d’équipement",
            ["Tous les types"] + options_types,
            key="coverage_drilldown_type_equipement",
        )

        detail_equipements = df_equipements_couverture_kpi.copy()
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

        detail_equipements = detail_equipements.drop_duplicates(
            "equipment_reference"
        ) if "equipment_reference" in detail_equipements.columns else detail_equipements

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
            "nb_contrats_total": "Contrats rattachés",
            "nb_contrats_actifs_valides": "Contrats actifs valides",
            "nb_contrats_inactifs": "Contrats inactifs",
        }
        disponibles = [
            colonne for colonne in colonnes_detail
            if colonne in detail_equipements.columns
        ]
        table_detail_equipements = (
            detail_equipements[disponibles]
            .rename(columns=colonnes_detail)
            .copy()
        )

        nb_detail_equipements = (
            table_detail_equipements["Référence équipement"].nunique()
            if "Référence équipement" in table_detail_equipements.columns
            else len(table_detail_equipements)
        )
        nb_detail_esi = (
            table_detail_equipements["Référence ESI"].nunique()
            if "Référence ESI" in table_detail_equipements.columns
            else 0
        )

        st.markdown(
            f"""
            <div class="vg-drilldown-summary">
                <span class="vg-drilldown-pill">
                    {fmt_nombre(nb_detail_equipements)} équipements
                </span>
                <span class="vg-drilldown-pill">
                    {fmt_nombre(nb_detail_esi)} ESI concernés
                </span>
                <span class="vg-drilldown-pill">
                    {_safe(type_selectionne)}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.dataframe(
            table_detail_equipements,
            width="stretch",
            hide_index=True,
            height=420,
        )
        dataframe_download(
            "Télécharger le détail en Excel",
            table_detail_equipements,
            "detail_equipements.xlsx",
            cle="export_detail_equipements",
        )


    # =====================================================
    # MÉTIERS ET ÉQUIPEMENTS
    # =====================================================

    st.markdown("<br>", unsafe_allow_html=True)
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


    with st.expander(
        "Explorer un métier",
        expanded=False,
    ):
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
