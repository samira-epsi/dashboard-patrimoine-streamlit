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
# PALETTE OFFICIELLE CHARTE 3F
# Source : CHARTE_3F_V8.pdf, page 32
# =====================================================

C_RED = "#E5114D"           # rouge 3F
C_NAVY = "#173B69"          # bleu foncé 3F
C_VIOLET = "#432ABD"        # violet complémentaire
C_YELLOW = "#FFDC55"        # jaune complémentaire
C_TEAL = "#008080"          # vert / bleu complémentaire
C_BLUE = "#0074FF"          # bleu vif complémentaire
C_BLUE_LIGHT = "#80CDFF"    # bleu ciel complémentaire
C_PINK = "#FFB7E3"          # rose complémentaire

# Déclinaisons d'interface dérivées de la palette officielle
C_RED_DARK = "#BF0F40"
C_NAVY_DEEP = "#102A4C"
C_PINK_SOFT = "#FFF3FA"
C_BLUE_SOFT = "#EFF9FF"
C_CANVAS = "#F7FAFD"
C_GRID = "#E8EEF5"
C_INK = "#17243A"


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
    """
    Formate un nombre avec une espace comme séparateur de milliers.
    Exemple : 8546 -> 8 546
    """
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def inject_style():
    st.markdown(
        """
        <style>
        :root {
            --navy: #173B69;
            --navy-deep: #102A4C;
            --red: #E5114D;
            --red-dark: #BF0F40;
            --violet: #432ABD;
            --blue: #0074FF;
            --blue-light: #80CDFF;
            --blue-soft: #EFF9FF;
            --pink: #FFB7E3;
            --pink-soft: #FFF3FA;
            --teal: #008080;
            --yellow: #FFDC55;

            --ink: #17243A;
            --ink-soft: #52647B;
            --ink-mute: #7A8AA0;
            --line: #DCE7F1;
            --line-soft: #EAF1F7;
            --surface: #FFFFFF;
            --canvas: #F7FAFD;
        }

        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .stApp {
            background: var(--canvas);
        }

        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 2.2rem !important;
            padding-right: 2.2rem !important;
            max-width: 1520px !important;
        }

        hr {
            border: none !important;
            border-top: 1px solid var(--line-soft) !important;
            margin: 22px 0 !important;
        }

        /* ---------- HERO ---------- */
        .vg-hero {
            position: relative;
            overflow: hidden;
            padding: 24px 34px;
            border-radius: 20px;
            background: #FBEAF4;
            border: 1px solid #E7D7E1;
            box-shadow: 0 10px 28px -22px rgba(23,59,105,0.26);
            margin-bottom: 22px;
        }
        .vg-hero:before {
            content: "";
            position: absolute;
            left: 0; top: 0; right: 0;
            height: 4px;
            background: var(--red);
        }
        .vg-hero:after {
            display: none;
        }
        .vg-hero-eyebrow {
            position: relative; z-index: 1;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            color: var(--navy);
            font-size: 11.5px;
            font-weight: 700;
            letter-spacing: 1.4px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }
        .vg-hero-eyebrow:before {
            content: "";
            width: 8px;
            height: 8px;
            background: var(--red);
            border-radius: 50%;
            flex-shrink: 0;
        }
        .vg-hero-title {
            position: relative; z-index: 1;
            color: var(--navy-deep);
            font-size: 32px;
            line-height: 1.08;
            letter-spacing: -0.6px;
            font-weight: 800;
            margin-bottom: 9px;
        }
        .vg-hero-subtitle {
            position: relative; z-index: 1;
            color: #334E70;
            font-size: 14.5px;
            line-height: 1.55;
            font-weight: 500;
            max-width: 940px;
        }

        /* ---------- INFO ---------- */
        .vg-info {
            padding: 12px 16px;
            border-radius: 12px;
            background: #F4F8FB;
            border: 1px solid #DCEAF5;
            color: var(--ink-soft);
            font-size: 12.5px;
            font-weight: 500;
            line-height: 1.5;
            margin: 8px 0 16px 0;
        }

        /* ---------- SECTIONS ---------- */
        .vg-section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 20px;
            font-weight: 800;
            color: var(--navy);
            letter-spacing: -0.3px;
            margin-top: 2px;
            margin-bottom: 3px;
        }
        .vg-section-title:before {
            content: "";
            width: 7px;
            height: 22px;
            border-radius: 99px;
            background: var(--red);
        }
        .vg-section-subtitle {
            color: var(--ink-soft);
            font-size: 13px;
            font-weight: 500;
            line-height: 1.5;
            margin-bottom: 14px;
            max-width: 920px;
        }
        .vg-mini-title {
            color: var(--navy);
            font-size: 14px;
            font-weight: 700;
            margin: 2px 0 10px 0;
        }

        /* ---------- KPI CARDS ---------- */
        .vg-card {
            min-height: 156px;
            border-radius: 16px;
            padding: 20px 20px 18px 20px;
            background: var(--surface);
            border: 1px solid var(--line);
            box-shadow: 0 6px 18px -16px rgba(23,59,105,0.22);
            position: relative;
            overflow: hidden;
            transition: border-color .15s ease, box-shadow .15s ease;
        }
        .vg-card:hover {
            border-color: #C9D5E1;
            box-shadow: 0 8px 22px -18px rgba(23,59,105,0.26);
        }
        .vg-card-accent {
            width: 32px; height: 4px;
            border-radius: 99px;
            background: var(--accent, #173B69);
            margin-bottom: 15px;
        }
        .vg-card-label {
            color: var(--ink-mute);
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 10px;
        }
        .vg-card-value {
            color: var(--ink);
            font-size: 34px;
            font-weight: 800;
            letter-spacing: -1px;
            line-height: 1;
            margin-bottom: 12px;
        }
        .vg-card-pill {
            display: inline-flex;
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
            color: var(--ink-mute);
            font-size: 11.5px;
            font-weight: 500;
            line-height: 1.45;
        }

        /* ---------- ALERT CARDS ---------- */
        .vg-alert-card {
            min-height: 118px;
            border-radius: 14px;
            padding: 16px 18px;
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 4px solid var(--red);
            background: #FFFFFF;
            box-shadow: 0 1px 2px rgba(16,35,59,0.04);
        }
        .vg-alert-title {
            color: var(--ink-soft);
            font-size: 10.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 9px;
        }
        .vg-alert-value {
            color: var(--ink);
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
            line-height: 1;
            margin-bottom: 8px;
        }
        .vg-alert-help {
            color: var(--ink-mute);
            font-size: 11.5px;
            font-weight: 500;
            line-height: 1.4;
        }

        /* ---------- CHARTS + TABLES ---------- */
        div[data-testid="stPlotlyChart"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 12px;
            box-shadow: 0 1px 2px rgba(16,35,59,0.04);
        }
        div[data-testid="stDataFrame"] {
            border-radius: 14px !important;
            overflow: hidden !important;
            border: 1px solid var(--line) !important;
            box-shadow: 0 1px 2px rgba(16,35,59,0.04) !important;
            background: var(--surface) !important;
        }
        div[data-testid="stDataFrame"] [role="columnheader"] {
            background: #F3F6F9 !important;
            color: var(--navy) !important;
            font-weight: 700 !important;
        }

        /* ---------- BUTTONS ---------- */
        .stButton button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid var(--line) !important;
            background: var(--surface) !important;
            color: var(--navy) !important;
            transition: all .15s ease !important;
        }
        .stButton button:hover {
            border-color: var(--navy) !important;
            background: #F4F7FA !important;
        }
        .stDownloadButton button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid var(--red) !important;
            background: var(--red) !important;
            color: #FFFFFF !important;
        }
        .stDownloadButton button:hover {
            background: var(--red-dark) !important;
        }

        /* ---------- NAVIGATION EN BOUTONS ---------- */
        div[role="radiogroup"] {
            gap: 8px !important;
            background: #F2F5F8;
            border: 1px solid #DCE8F2;
            padding: 5px;
            border-radius: 13px;
            width: fit-content;
        }
        div[role="radiogroup"] label {
            background: transparent;
            border-radius: 9px;
            padding: 8px 15px !important;
            margin: 0 !important;
            transition: background .15s ease, box-shadow .15s ease;
        }
        div[role="radiogroup"] label:has(input:checked) {
            background: #173B69 !important;
            box-shadow: none;
        }
        div[role="radiogroup"] label:has(input:checked) p {
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }
        div[role="radiogroup"] label > div:first-child {
            display: none !important;
        }

        /* ---------- EXPANDERS ---------- */
        div[data-testid="stExpander"] {
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
            background: var(--surface) !important;
            box-shadow: 0 6px 18px -16px rgba(23,59,105,0.24);
            overflow: hidden;
        }

        /* ---------- RESPONSIVE ---------- */
        @media screen and (max-width: 1100px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            .vg-hero-title { font-size: 28px; }
            .vg-card-value { font-size: 30px; }
        }
        @media screen and (max-width: 760px) {
            .vg-hero { padding: 24px 20px; border-radius: 16px; }
            .vg-hero-title { font-size: 25px; }
            .vg-section-title { font-size: 18px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        r"""
        <style>
        :root {
            --navy: #173B69;
            --navy-deep: #102A4C;
            --red: #E5114D;
            --pink-soft: #FFF1F6;
            --blue-soft: #EEF6FB;
            --canvas: #F6F8FB;
            --surface: #FFFFFF;
            --line: #DCE4EC;
            --line-soft: #E9EEF3;
            --ink: #17243A;
            --ink-soft: #5E6E82;
            --ink-mute: #8996A8;
        }

        .stApp {
            background: var(--canvas) !important;
        }

        .block-container {
            padding-top: 1.25rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1520px !important;
        }

        .vg-hero {
            position: relative;
            overflow: hidden;
            padding: 28px 34px !important;
            margin-bottom: 18px !important;
            background: var(--navy) !important;
            border: 1px solid var(--navy) !important;
            border-radius: 20px !important;
            box-shadow: 0 12px 30px -24px rgba(16, 42, 76, 0.65) !important;
        }

        .vg-hero::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            height: 5px;
            background: var(--red) !important;
        }

        .vg-hero::after {
            content: "" !important;
            display: block !important;
            position: absolute;
            width: 150px;
            height: 150px;
            right: -70px;
            bottom: -90px;
            border-radius: 50%;
            background: rgba(255, 183, 227, 0.14) !important;
        }

        .vg-hero-eyebrow {
            color: rgba(255, 255, 255, 0.72) !important;
            margin-bottom: 11px !important;
        }

        .vg-hero-eyebrow::before {
            width: 8px !important;
            height: 8px !important;
            border-radius: 50% !important;
            background: #FFB7E3 !important;
        }

        .vg-hero-title {
            color: #FFFFFF !important;
            font-size: 34px !important;
            margin-bottom: 8px !important;
        }

        .vg-hero-subtitle {
            color: rgba(255, 255, 255, 0.80) !important;
            max-width: 900px !important;
        }

        div[role="radiogroup"] {
            gap: 8px !important;
        }

        div[role="radiogroup"] label {
            min-height: 46px !important;
            padding: 8px 17px !important;
            background: #FFFFFF !important;
            color: var(--ink) !important;
            border: 1px solid var(--line) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        div[role="radiogroup"] label:hover {
            background: var(--blue-soft) !important;
            border-color: #BFCFDC !important;
            transform: none !important;
        }

        div[role="radiogroup"] label:has(input:checked) {
            background: var(--navy) !important;
            color: #FFFFFF !important;
            border-color: var(--navy) !important;
            box-shadow: none !important;
        }

        div[role="radiogroup"] label:has(input:checked) p,
        div[role="radiogroup"] label:has(input:checked) span {
            color: #FFFFFF !important;
        }

        .stButton button {
            min-height: 44px !important;
            color: var(--navy) !important;
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        .stButton button:hover {
            color: var(--navy-deep) !important;
            background: var(--blue-soft) !important;
            border-color: #BCCBD8 !important;
            transform: none !important;
        }

        .vg-section-title {
            color: var(--navy) !important;
        }

        .vg-section-title::before {
            width: 5px !important;
            height: 21px !important;
            background: var(--red) !important;
        }

        .vg-info {
            background: var(--blue-soft) !important;
            border: 1px solid #D9E7F0 !important;
            color: var(--ink-soft) !important;
            box-shadow: none !important;
        }

        .vg-card {
            min-height: 148px !important;
            padding: 18px 19px 17px 19px !important;
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 20px -18px rgba(23, 59, 105, 0.30) !important;
            transition: border-color .15s ease, box-shadow .15s ease !important;
        }

        .vg-card:hover {
            transform: none !important;
            border-color: #C2CFDA !important;
            box-shadow: 0 10px 24px -18px rgba(23, 59, 105, 0.34) !important;
        }

        .vg-card-value {
            color: var(--ink) !important;
            font-size: 32px !important;
        }

        .vg-alert-card {
            min-height: 112px !important;
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-left: 4px solid var(--red) !important;
            border-radius: 14px !important;
            box-shadow: 0 7px 18px -17px rgba(23, 59, 105, 0.28) !important;
        }

        details {
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
        }

        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 20px -18px rgba(23, 59, 105, 0.28) !important;
        }

        @media screen and (max-width: 900px) {
            .vg-hero {
                padding: 24px 22px !important;
            }

            .vg-hero-title {
                font-size: 29px !important;
            }

            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        }
        </style>
""",
        unsafe_allow_html=True,
    )



    st.markdown(
        r"""
        <style>
        :root {
            --3f-red: #E5114D;
            --3f-pink-soft: #FFF1F6;
            --3f-blue-light: #80CDFF;
            --text-main: #1B2430;
            --text-soft: #667085;
            --text-muted: #8A94A6;
            --surface: #FFFFFF;
            --canvas: #FAFAFB;
            --border: #E7E3E8;
        }

        .stApp {
            background: var(--canvas) !important;
        }

        .block-container {
            max-width: 1520px !important;
            padding-top: 1.25rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }

        .vg-hero {
            position: relative;
            overflow: hidden;
            padding: 28px 34px !important;
            margin-bottom: 18px !important;
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
            content: "" !important;
            display: block !important;
            position: absolute;
            width: 135px;
            height: 135px;
            right: -70px;
            bottom: -75px;
            border-radius: 50%;
            background: rgba(128, 205, 255, 0.18) !important;
        }

        .vg-hero-eyebrow {
            color: #A33A61 !important;
        }

        .vg-hero-eyebrow::before {
            width: 8px !important;
            height: 8px !important;
            border-radius: 50% !important;
            background: var(--3f-red) !important;
        }

        .vg-hero-title {
            color: var(--text-main) !important;
            font-size: 34px !important;
        }

        .vg-hero-subtitle {
            color: var(--text-soft) !important;
        }

        div[role="radiogroup"] {
            gap: 8px !important;
        }

        div[role="radiogroup"] label {
            min-height: 46px !important;
            padding: 8px 17px !important;
            background: #FFFFFF !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        div[role="radiogroup"] label:hover {
            background: #FFF7FA !important;
            border-color: #E5C9D6 !important;
            transform: none !important;
        }

        div[role="radiogroup"] label:has(input:checked) {
            background: var(--3f-red) !important;
            color: #FFFFFF !important;
            border-color: var(--3f-red) !important;
            box-shadow: none !important;
        }

        div[role="radiogroup"] label:has(input:checked) p,
        div[role="radiogroup"] label:has(input:checked) span {
            color: #FFFFFF !important;
        }

        .stButton button {
            min-height: 44px !important;
            color: #9D174D !important;
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        .stButton button:hover {
            color: var(--3f-red) !important;
            background: #FFF7FA !important;
            border-color: #E7C8D6 !important;
            transform: none !important;
        }

        .vg-section-title {
            color: var(--text-main) !important;
        }

        .vg-section-title::before {
            background: var(--3f-red) !important;
        }

        .vg-section-subtitle {
            color: var(--text-soft) !important;
        }

        .vg-info {
            background: #FFF7FA !important;
            border: 1px solid #EEDCE5 !important;
            color: var(--text-soft) !important;
            box-shadow: none !important;
        }

        .vg-card {
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.22) !important;
        }

        .vg-card:hover {
            transform: none !important;
            border-color: #DCCED5 !important;
            box-shadow: 0 10px 24px -18px rgba(27, 36, 48, 0.28) !important;
        }

        .vg-card-value {
            color: var(--text-main) !important;
        }

        .vg-alert-card {
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-left: 4px solid var(--3f-red) !important;
            border-radius: 14px !important;
            box-shadow: 0 7px 18px -17px rgba(27, 36, 48, 0.22) !important;
        }

        details {
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
        }

        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {
            background: #FFFFFF !important;
            border: 1px solid var(--border) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.22) !important;
        }

        @media screen and (max-width: 900px) {
            .vg-hero {
                padding: 24px 22px !important;
            }

            .vg-hero-title {
                font-size: 29px !important;
            }

            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        r"""
        <style>
        /* =====================================================
           ALIGNEMENT GÉNÉRAL
        ===================================================== */

        .block-container {
            padding-top: 1.15rem !important;
        }

        .vg-hero {
            margin-top: 0 !important;
            margin-bottom: 14px !important;
        }

        /* =====================================================
           NAVIGATION PRINCIPALE = ONGLETS
        ===================================================== */

        .st-key-dashboard_tabs {
            margin-top: 0 !important;
            margin-bottom: 20px !important;
            border-bottom: 1px solid #E7E3E8;
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

            color: #667085 !important;
            background: transparent !important;

            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;

            font-weight: 650 !important;
            transition: color .15s ease !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:hover {
            color: #1B2430 !important;
            background: transparent !important;
            border: 0 !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked) {
            color: #E5114D !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked)::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: -1px;
            height: 3px;
            border-radius: 3px 3px 0 0;
            background: #E5114D;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label p,
        .st-key-dashboard_tabs div[role="radiogroup"] label span {
            color: inherit !important;
            font-weight: inherit !important;
        }

        /* Cache le cercle radio uniquement pour les onglets principaux. */
        .st-key-dashboard_tabs div[role="radiogroup"] label > div:first-child {
            display: none !important;
        }

        /* =====================================================
           BOUTON ACTUALISER ALIGNÉ AUX ONGLETS
        ===================================================== */

        .st-key-dashboard_refresh button {
            min-height: 42px !important;
            margin-bottom: 20px !important;
        }

        /* =====================================================
           FILTRE STATUT = CONTRÔLE COMPACT
        ===================================================== */

        .st-key-contract_status_filter {
            max-width: 760px;
            margin-top: 0 !important;
            margin-bottom: 20px !important;
        }

        .st-key-contract_status_filter .vg-mini-title {
            margin-bottom: 8px !important;
        }

        .st-key-contract_status_filter div[role="radiogroup"] {
            width: fit-content !important;
            gap: 4px !important;
            padding: 5px !important;
            background: #F5F6F8 !important;
            border: 1px solid #E7E3E8 !important;
            border-radius: 12px !important;
        }

        .st-key-contract_status_filter div[role="radiogroup"] label {
            min-height: 42px !important;
            padding: 8px 15px !important;
            border-radius: 9px !important;
        }

        .st-key-contract_status_filter [data-testid="stCaptionContainer"] {
            margin-top: 7px !important;
        }

        /* =====================================================
           CARTES ALIGNÉES ET DE MÊME HAUTEUR
        ===================================================== */

        .vg-card {
            height: 190px !important;
            min-height: 190px !important;
            box-sizing: border-box !important;
            display: flex !important;
            flex-direction: column !important;
        }

        .vg-card-help {
            margin-top: auto !important;
        }

        .vg-alert-card {
            height: 148px !important;
            min-height: 148px !important;
            box-sizing: border-box !important;
        }

        /* Les colonnes Streamlit d'une même ligne s'étirent pareil. */
        div[data-testid="stHorizontalBlock"] {
            align-items: stretch !important;
        }

        div[data-testid="column"] {
            display: flex !important;
            flex-direction: column !important;
        }

        div[data-testid="column"] > div {
            width: 100% !important;
        }

        /* =====================================================
           ESPACEMENTS PLUS SYMÉTRIQUES
        ===================================================== */

        .vg-section {
            margin-top: 8px !important;
        }

        .vg-section-title {
            margin-top: 0 !important;
        }

        @media screen and (max-width: 900px) {
            .st-key-dashboard_tabs div[role="radiogroup"] {
                gap: 16px !important;
                overflow-x: auto !important;
                flex-wrap: nowrap !important;
            }

            .st-key-dashboard_tabs div[role="radiogroup"] label {
                white-space: nowrap !important;
            }

            .vg-card,
            .vg-alert-card {
                height: auto !important;
                min-height: 148px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        r"""
        <style>
        /* =====================================================
           CORRECTION DES ONGLETS PRINCIPAUX
        ===================================================== */

        .st-key-dashboard_tabs div[role="radiogroup"] label {
            color: #667085 !important;
            background: transparent !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label * {
            color: inherit !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked),
        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked) *,
        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked) p,
        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked) span {
            color: #E5114D !important;
            background: transparent !important;
        }

        /* Cache uniquement le rond radio des onglets principaux. */
        .st-key-dashboard_tabs div[role="radiogroup"] label input[type="radio"] {
            display: none !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label
        div[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked)::after {
            background: #E5114D !important;
        }

        /* =====================================================
           CORRECTION DES COLONNES
        ===================================================== */

        /*
        Le flex appliqué à toutes les colonnes déformait les conteneurs
        Plotly et provoquait une barre de défilement dans le donut.
        */
        div[data-testid="column"] {
            display: block !important;
        }

        div[data-testid="column"] > div {
            width: 100% !important;
        }

        /* =====================================================
           CENTRAGE DES GRAPHIQUES
        ===================================================== */

        div[data-testid="stPlotlyChart"] {
            width: 100% !important;
            overflow: hidden !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        div[data-testid="stPlotlyChart"] > div {
            width: 100% !important;
        }

        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container {
            margin-left: auto !important;
            margin-right: auto !important;
        }

        div[data-testid="stPlotlyChart"] .plot-container {
            overflow: hidden !important;
        }

        /* Même hauteur visuelle pour les deux panneaux de graphiques. */
        .st-key-global_graph_status,
        .st-key-global_graph_metier {
            min-height: 470px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        r"""
        <style>
        /* =====================================================
           TABLEAU DES CONTRATS
        ===================================================== */

        .vg-table-summary {
            display: flex;
            align-items: center;
            gap: 18px;

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
            color: #E5114D;
            font-size: 20px;
            font-weight: 800;
            line-height: 1;
        }

        .vg-table-summary-label {
            color: #667085;
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
        }

        /* Les deux contrôles restent propres sans ressembler aux onglets. */
        div[data-testid="stExpander"] div[role="radiogroup"] {
            width: 100% !important;
            gap: 5px !important;
            padding: 5px !important;

            background: #F7F5F7 !important;
            border: 1px solid #E7E3E8 !important;
            border-radius: 12px !important;
        }

        div[data-testid="stExpander"] div[role="radiogroup"] label {
            min-height: 41px !important;
            padding: 8px 12px !important;

            background: #FFFFFF !important;
            color: #1B2430 !important;

            border: 1px solid transparent !important;
            border-radius: 9px !important;
        }

        div[data-testid="stExpander"] div[role="radiogroup"] label:has(input:checked) {
            background: #FFF1F6 !important;
            color: #A3184A !important;
            border-color: #E7C8D6 !important;
        }

        div[data-testid="stExpander"] div[role="radiogroup"] label:has(input:checked) p,
        div[data-testid="stExpander"] div[role="radiogroup"] label:has(input:checked) span {
            color: #A3184A !important;
        }

        @media screen and (max-width: 900px) {
            .vg-table-summary {
                align-items: flex-start;
                flex-wrap: wrap;
                gap: 10px 14px;
            }

            .vg-table-summary-mode {
                width: fit-content;
                margin-left: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        r"""
        <style>
        .vg-column-title {
            margin-bottom: 7px;
            color: #1B2430;
            font-size: 14px;
            font-weight: 700;
        }

        div[data-testid="stPopover"] button {
            min-height: 44px !important;
            color: #A3184A !important;
            background: #FFFFFF !important;
            border: 1px solid #E1DCE2 !important;
            border-radius: 11px !important;
            box-shadow: none !important;
        }

        div[data-testid="stPopover"] button:hover {
            color: #E5114D !important;
            background: #FFF7FA !important;
            border-color: #D7BEC9 !important;
        }

        div[data-testid="stPopoverBody"] {
            min-width: 360px !important;
            max-width: 420px !important;
        }

        .vg-columns-separator {
            height: 1px;
            margin: 10px 0 8px 0;
            background: #EEE7EB;
        }

        div[data-testid="stPopoverBody"] [data-testid="stCheckbox"] {
            margin-bottom: 2px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        r"""
        <style>
        div[data-testid="stPopoverBody"] form {
            margin: 0 !important;
        }

        div[data-testid="stPopoverBody"] form
        [data-testid="stFormSubmitButton"] button {
            min-height: 40px !important;
            border-radius: 10px !important;
        }

        div[data-testid="stPopoverBody"] form
        [data-testid="stFormSubmitButton"] button[kind="primary"] {
            color: #FFFFFF !important;
            background: #E5114D !important;
            border-color: #E5114D !important;
        }

        div[data-testid="stPopoverBody"] form
        [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: #C90F43 !important;
            border-color: #C90F43 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        r"""
        <style>
        /* =====================================================
           PAGINATION DU TABLEAU
        ===================================================== */

        .vg-pagination-current {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 7px;

            min-height: 42px;
            padding: 7px 14px;

            color: #667085;
            background: #FFF7FA;

            border: 1px solid #EEDCE5;
            border-radius: 11px;

            font-size: 12px;
            font-weight: 650;
        }

        .vg-pagination-current strong {
            display: inline-flex;
            align-items: center;
            justify-content: center;

            min-width: 30px;
            height: 28px;
            padding: 0 8px;

            color: #FFFFFF;
            background: #E5114D;

            border-radius: 8px;
            font-size: 13px;
            font-weight: 800;
        }

        .vg-table-summary {
            overflow: hidden;
        }

        .vg-table-summary-mode {
            white-space: nowrap;
        }

        @media screen and (max-width: 800px) {
            .vg-pagination-current {
                padding-left: 8px;
                padding-right: 8px;
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




def serie_numerique(df: pd.DataFrame, colonne: str) -> pd.Series:
    """Retourne une série numérique sûre, même si la colonne est absente."""
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
# COMPOSANTS VISUELS
# =====================================================

def kpi_card(label, value, pill, help_text, accent=C_RED):
    st.markdown(
        f"""
        <div class="vg-card" style="--accent:{_safe(accent)};">
            <div class="vg-card-accent"></div>
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
        st.bar_chart(df.set_index("Indicateur")["Taux"], width="stretch")
        return

    fig = go.Figure()
    # rail de fond (100 %) pour lire la progression d'un coup d'oeil
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
            hovertemplate="<b>%{y}</b><br>Taux : %{x:.1f} %<br>Détail : %{customdata}<extra></extra>",
            marker=dict(color=C_RED),
        )
    )
    _layout_plotly(fig, 300)
    fig.update_layout(
        barmode="overlay",
        bargap=0.42,
        xaxis=dict(range=[0, 100], ticksuffix=" %", gridcolor=C_GRID, zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
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


def afficher_barres_horizontales(df: pd.DataFrame, label_col: str, value_col: str, color=C_RED, height_base=320):
    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    if go is None:
        st.bar_chart(df.set_index(label_col)[value_col], width="stretch")
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
        xaxis=dict(range=[0, max_value * 1.18], gridcolor=C_GRID, zeroline=False, title=None),
        yaxis=dict(title=None, automargin=True),
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
    """
    Télécharge uniquement le DataFrame transmis.

    Pour les gros tableaux, on lui transmet seulement la page affichée
    afin d'éviter de sérialiser tout le jeu de données à chaque rerun.
    """
    if df.empty:
        return

    csv_bytes = df.to_csv(
        index=False,
        lineterminator="\n",
    ).encode("utf-8-sig")

    st.download_button(
        label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        width="stretch",
    )


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
        section("Détail : contrats actifs avec date de fin dépassée", "Contrats exploitables dans le périmètre filtré.")
        table = preparer_contrats_table(contrats_actifs_fin_depassee(df_contrats_kpi))
        if table.empty:
            st.success("Aucun contrat actif expiré dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download("Télécharger les contrats expirés", table, "contrats_actifs_expires.csv")

    elif focus == "unlinked_contracts":
        section("Détail : contrats non rattachés", "Contrats présents en source mais absents de la couverture programme.")
        table = df_qualite[df_qualite.get("anomalie_type", "") == "CONTRAT_NON_RATTACHE_PROGRAMME"].copy() if not df_qualite.empty else pd.DataFrame()
        table = preparer_qualite_table(table)
        if table.empty:
            st.info("Aucun détail disponible dans la table qualité.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download("Télécharger les contrats non rattachés", table, "contrats_non_rattaches.csv")

    elif focus == "housing":
        section("Détail : logements sans programme", "Logements non exploitables dans les calculs de couverture ESI.")
        table = df_qualite[df_qualite.get("anomalie_type", "") == "LOGEMENT_SANS_PROGRAMME"].copy() if not df_qualite.empty else pd.DataFrame()
        table = preparer_qualite_table(table)
        if table.empty:
            st.info("Aucun détail disponible dans la table qualité.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download("Télécharger les logements sans programme", table, "logements_sans_programme.csv")
            if len(table) > 500:
                st.caption(f"Affichage limité à 500 lignes sur {fmt_nombre(len(table))}.")

    elif focus == "multi_topic":
        section("Détail : ESI avec plusieurs contrats actifs sur le même métier", "Ce signal peut révéler des doublons ou des chevauchements de contrats.")
        if "esi_multi_meme_metier" not in df_esi_context.columns:
            st.info("La colonne esi_multi_meme_metier n'est pas disponible.")
            return
        table = df_esi_context[pd.to_numeric(df_esi_context["esi_multi_meme_metier"], errors="coerce").fillna(0) > 0].copy()
        table = preparer_esi_table(table)
        if table.empty:
            st.success("Aucun ESI multi même métier dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download("Télécharger les ESI multi même métier", table, "esi_multi_meme_metier.csv")

    elif focus == "no_contract":
        section("Détail : ESI sans contrat actif", "Programmes sans contrat actif rattaché dans le périmètre affiché.")
        table = df_esi_context[serie_numerique(df_esi_context, "nb_contrats_actifs") == 0].copy()
        table = preparer_esi_table(table)
        if table.empty:
            st.success("Aucun ESI sans contrat actif dans le périmètre affiché.")
        else:
            st.dataframe(table.head(500), width="stretch", hide_index=True, height=360)
            dataframe_download("Télécharger les ESI sans contrat actif", table, "esi_sans_contrat_actif.csv")


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

# Navigation principale : une seule vue visible à la fois.
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
    if st.button(
        "Actualiser",
        width="stretch",
        key="dashboard_refresh",
    ):
        st.cache_data.clear()
        st.rerun()

try:
    with st.spinner("Chargement des données..."):
        df_global, df_esi, df_contrats, df_creations, df_qualite, df_qualite_resume = charger_donnees()
except Exception as e:
    st.error("Erreur pendant le chargement des données.")
    st.code(str(e))
    st.stop()

if df_global.empty:
    st.error("La table dashboard.kpi_globale est vide.")
    st.stop()

# Les filtres patrimoine sont affichés dans la barre latérale.
df_esi_filtre, df_contrats_filtre, filtres_selectionnes = render_filtres_patrimoine(
    df_esi=df_esi,
    df_contrats=df_contrats,
)

# Filtre complémentaire compact dans la zone principale.
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

# Calculs communs à toutes les vues.
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
# VUE 1 — VUE GLOBALE
# =====================================================

if vue_active == "Vue globale":
    section(
        "Vue globale",
        "La réalité présente dans Intent, puis la part réellement exploitable pour les analyses de couverture.",
    )

    if not perimetre_filtre_actif:
        contrats_value = global_value(df_global, "contrats_total")
        contrats_pill = f"{fmt_nombre(global_value(df_global, 'contrats_rattaches_programme'))} exploitables"
        contrats_help = f"{fmt_nombre(global_value(df_global, 'contrats_non_rattaches_programme'))} non rattachés à un programme."

        programmes_value = global_value(df_global, "programmes_total")
        programmes_couverts = int(serie_numerique(df_esi, "esi_couvert").sum())
        programmes_pill = f"{fmt_nombre(programmes_couverts)} couverts"
        programmes_help = "Programmes / ESI présents dans la source patrimoniale."

        logements_value = global_value(df_global, "logements_total")
        logements_pill = f"{fmt_nombre(global_value(df_global, 'logements_rattaches_programme'))} exploitables"
        logements_help = f"{fmt_nombre(global_value(df_global, 'logements_sans_programme'))} sans programme."

        equipements_value = global_value(df_global, "equipements_total")
        equipements_pill = f"{fmt_nombre(global_value(df_global, 'equipements_rattaches_programme'))} exploitables"
        equipements_help = f"{fmt_nombre(global_value(df_global, 'equipements_sans_programme'))} sans programme."
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

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Contrats", contrats_value, contrats_pill, contrats_help, accent=C_NAVY)
    with c2:
        kpi_card("Programmes / ESI", programmes_value, programmes_pill, programmes_help, accent=C_NAVY)
    with c3:
        kpi_card("Logements", logements_value, logements_pill, logements_help, accent=C_PINK)
    with c4:
        kpi_card("Équipements", equipements_value, equipements_pill, equipements_help, accent=C_VIOLET)

    st.markdown("<br>", unsafe_allow_html=True)
    col_statut, col_metier = st.columns([0.82, 1.35])

    with col_statut:
        with st.container(key="global_graph_status"):
            st.markdown(
                '<div class="vg-mini-title">Statut des contrats</div>',
                unsafe_allow_html=True,
            )

            contrats_uniques = (
                df_contrats_kpi
                .drop_duplicates("contract_reference")
                .copy()
            )
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
                            domain=dict(
                                x=[0.08, 0.92],
                                y=[0.06, 0.94],
                            ),
                            sort=False,
                        )
                    ]
                )

                _layout_plotly(fig, 420)

                fig.update_layout(
                    margin=dict(l=18, r=18, t=12, b=12),
                    showlegend=False,
                    uniformtext_minsize=11,
                    uniformtext_mode="hide",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "displayModeBar": False,
                        "responsive": True,
                    },
                )

    with col_metier:
        with st.container(key="global_graph_metier"):
            st.markdown(
                '<div class="vg-mini-title">'
                'Répartition des contrats par métier'
                '</div>',
                unsafe_allow_html=True,
            )

            afficher_barres_horizontales(
                construire_graph_metier(df_contrats_kpi, top_n=10),
                "Métier",
                "Contrats",
                color=C_RED,
                height_base=420,
            )

    with st.expander("Consulter la liste des contrats", expanded=False):
        recherche_contrat = st.text_input(
            "Rechercher un contrat",
            placeholder="Référence, libellé, prestataire, métier...",
            key="global_search_contract",
        )

        mode_col, colonnes_col = st.columns(
            [1.25, 2.75],
            vertical_alignment="top",
        )

        with mode_col:
            mode_tableau = st.radio(
                "Niveau d’affichage",
                [
                    "Contrats uniques",
                    "Contrats et rattachements",
                ],
                horizontal=False,
                key="global_contract_table_mode",
                help=(
                    "Contrats uniques : une ligne par contrat. "
                    "Contrats et rattachements : une ligne par contrat "
                    "et programme couvert."
                ),
            )

        if mode_tableau == "Contrats uniques":
            colonnes_tri = [
                col
                for col in [
                    "contract_reference",
                    "esi_reference",
                ]
                if col in df_contrats_kpi.columns
            ]

            source_tableau = df_contrats_kpi

            if colonnes_tri:
                source_tableau = source_tableau.sort_values(
                    by=colonnes_tri,
                    na_position="last",
                )

            source_tableau = source_tableau.drop_duplicates(
                "contract_reference"
            )

        else:
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
                )
                if cles_dedoublonnage
                else df_contrats_kpi
            )

        table_contrats_complete = preparer_contrats_table(
            source_tableau
        )

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

        colonnes_disponibles = [
            col
            for col in (
                colonnes_contrat
                + colonnes_rattachement
            )
            if col in table_contrats_complete.columns
        ]

        if mode_tableau == "Contrats uniques":
            colonnes_par_defaut = [
                col
                for col in colonnes_contrat
                if col in colonnes_disponibles
            ]
        else:
            colonnes_par_defaut = [
                col
                for col in (
                    colonnes_contrat
                    + [
                        "Référence ESI",
                        "Libellé ESI",
                    ]
                )
                if col in colonnes_disponibles
            ]

        with colonnes_col:
            st.markdown(
                '<div class="vg-column-title">Colonnes affichées</div>',
                unsafe_allow_html=True,
            )

            cle_mode = (
                "uniques"
                if mode_tableau == "Contrats uniques"
                else "rattachements"
            )

            def cle_checkbox_colonne(colonne: str) -> str:
                cle_simple = (
                    colonne
                    .lower()
                    .replace(" ", "_")
                    .replace("é", "e")
                    .replace("è", "e")
                    .replace("ê", "e")
                    .replace("à", "a")
                    .replace("'", "")
                    .replace("/", "_")
                )
                return f"colonne_{cle_mode}_{cle_simple}"

            for colonne in colonnes_disponibles:
                cle_case = cle_checkbox_colonne(colonne)

                if cle_case not in st.session_state:
                    st.session_state[cle_case] = (
                        colonne in colonnes_par_defaut
                    )

            with st.popover(
                "Choisir les colonnes",
                width="stretch",
            ):
                with st.form(
                    key=f"form_colonnes_{cle_mode}",
                    clear_on_submit=False,
                ):
                    bouton_tout, bouton_reset = st.columns(2)

                    with bouton_tout:
                        tout_selectionner = (
                            st.form_submit_button(
                                "Tout sélectionner",
                                width="stretch",
                            )
                        )

                    with bouton_reset:
                        reinitialiser = (
                            st.form_submit_button(
                                "Réinitialiser",
                                width="stretch",
                            )
                        )

                    if tout_selectionner:
                        for colonne in colonnes_disponibles:
                            st.session_state[
                                cle_checkbox_colonne(colonne)
                            ] = True

                    if reinitialiser:
                        for colonne in colonnes_disponibles:
                            st.session_state[
                                cle_checkbox_colonne(colonne)
                            ] = (
                                colonne in colonnes_par_defaut
                            )

                    st.markdown(
                        '<div class="vg-columns-separator"></div>',
                        unsafe_allow_html=True,
                    )

                    for colonne in colonnes_disponibles:
                        st.checkbox(
                            colonne,
                            key=cle_checkbox_colonne(colonne),
                        )

                    st.form_submit_button(
                        "Appliquer",
                        width="stretch",
                        type="primary",
                    )

            colonnes_affichees = [
                colonne
                for colonne in colonnes_disponibles
                if st.session_state.get(
                    cle_checkbox_colonne(colonne),
                    False,
                )
            ]

            st.caption(
                (
                    f"{len(colonnes_affichees)} colonne(s) "
                    "sélectionnée(s)."
                )
                if colonnes_affichees
                else "Aucune colonne sélectionnée."
            )

        if "Référence contrat" in table_contrats_complete.columns:
            nb_contrats_resultat = int(
                table_contrats_complete[
                    "Référence contrat"
                ]
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )
        else:
            nb_contrats_resultat = len(
                table_contrats_complete
            )

        nb_lignes_resultat = len(
            table_contrats_complete
        )

        libelle_contrats = (
            "contrat trouvé"
            if nb_contrats_resultat == 1
            else "contrats trouvés"
        )
        libelle_lignes = (
            "ligne trouvée"
            if nb_lignes_resultat == 1
            else "lignes trouvées"
        )

        resume_html = (
            '<div class="vg-table-summary">'
            '<div class="vg-table-summary-item">'
            f'<span class="vg-table-summary-value">'
            f'{format_nombre(nb_contrats_resultat)}'
            '</span>'
            f'<span class="vg-table-summary-label">'
            f'{libelle_contrats}'
            '</span>'
            '</div>'
            '<div class="vg-table-summary-separator"></div>'
            '<div class="vg-table-summary-item">'
            f'<span class="vg-table-summary-value">'
            f'{format_nombre(nb_lignes_resultat)}'
            '</span>'
            f'<span class="vg-table-summary-label">'
            f'{libelle_lignes}'
            '</span>'
            '</div>'
            f'<div class="vg-table-summary-mode">'
            f'{mode_tableau}'
            '</div>'
            '</div>'
        )

        st.markdown(
            resume_html,
            unsafe_allow_html=True,
        )

        if not colonnes_affichees:
            st.warning(
                "Sélectionne au moins une colonne à afficher."
            )

        elif table_contrats_complete.empty:
            st.info(
                "Aucun résultat ne correspond aux filtres "
                "et à la recherche."
            )

        else:
            TAILLE_PAGE = 500
            nb_pages = max(
                1,
                (
                    nb_lignes_resultat
                    + TAILLE_PAGE
                    - 1
                )
                // TAILLE_PAGE,
            )

            cle_page = f"page_table_contrats_{cle_mode}"

            if cle_page not in st.session_state:
                st.session_state[cle_page] = 1

            st.session_state[cle_page] = max(
                1,
                min(
                    int(st.session_state[cle_page]),
                    nb_pages,
                ),
            )

            page_selectionnee = int(
                st.session_state[cle_page]
            )

            pagination_gauche, pagination_centre, pagination_droite = (
                st.columns(
                    [1, 1.4, 1],
                    vertical_alignment="center",
                )
            )

            with pagination_gauche:
                if st.button(
                    "Précédent",
                    key=f"page_precedente_{cle_mode}",
                    width="stretch",
                    disabled=page_selectionnee <= 1,
                ):
                    st.session_state[cle_page] = (
                        page_selectionnee - 1
                    )
                    st.rerun()

            with pagination_centre:
                st.markdown(
                    (
                        '<div class="vg-pagination-current">'
                        f'<span>Page</span>'
                        f'<strong>{page_selectionnee}</strong>'
                        f'<span>sur {nb_pages}</span>'
                        '</div>'
                    ),
                    unsafe_allow_html=True,
                )

            with pagination_droite:
                if st.button(
                    "Suivant",
                    key=f"page_suivante_{cle_mode}",
                    width="stretch",
                    disabled=page_selectionnee >= nb_pages,
                ):
                    st.session_state[cle_page] = (
                        page_selectionnee + 1
                    )
                    st.rerun()

            debut = (
                page_selectionnee - 1
            ) * TAILLE_PAGE
            fin = debut + TAILLE_PAGE

            table_page = (
                table_contrats_complete
                .iloc[debut:fin][colonnes_affichees]
                .copy()
            )

            for colonne in table_page.columns:
                serie = table_page[colonne]

                if pd.api.types.is_datetime64_any_dtype(
                    serie
                ):
                    table_page[colonne] = (
                        pd.to_datetime(
                            serie,
                            errors="coerce",
                        )
                        .dt.strftime("%d/%m/%Y")
                        .fillna("")
                    )
                else:
                    table_page[colonne] = (
                        serie
                        .where(serie.notna(), "")
                        .astype(str)
                    )

            st.caption(
                f"Page {page_selectionnee} sur "
                f"{nb_pages} · lignes "
                f"{format_nombre(debut + 1)} à "
                f"{format_nombre(min(fin, nb_lignes_resultat))}"
            )

            st.dataframe(
                table_page,
                width="stretch",
                hide_index=True,
                height=430,
            )

            nom_export = (
                "contrats_uniques_complets.csv"
                if mode_tableau == "Contrats uniques"
                else "contrats_rattachements_complets.csv"
            )

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
                table_export_complete = (
                    table_contrats_complete[
                        colonnes_affichees
                    ]
                    .copy()
                )

                st.caption(
                    f"Le fichier contient toutes les lignes filtrées : "
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

# =====================================================
# VUE 2 — COUVERTURE
# =====================================================

elif vue_active == "Couverture":
    section(
        "Couverture du patrimoine",
        "La couverture est calculée uniquement sur le patrimoine exploitable et sur les contrats actifs rattachés à un programme.",
    )

    df_couverture = construire_couverture(df_esi_base, df_esi_context, filtre_contrat_actif)
    cov_map = df_couverture.set_index("Indicateur").to_dict("index") if not df_couverture.empty else {}

    esi_total = int(cov_map.get("Programmes", {}).get("Total", 0))
    esi_couverts = int(cov_map.get("Programmes", {}).get("Couverts", 0))
    esi_sans = max(esi_total - esi_couverts, 0)
    taux_esi = float(cov_map.get("Programmes", {}).get("Taux", 0))
    moyenne_contrats = (
        serie_numerique(df_esi_context, "nb_contrats_actifs").mean()
        if not df_esi_context.empty else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("ESI couverts", esi_couverts, fmt_pourcentage(taux_esi), "Au moins un contrat actif.", accent=C_RED)
    with c2:
        kpi_card("ESI sans contrat actif", esi_sans, "À traiter", "Aucun contrat actif rattaché.", accent=C_RED)
    with c3:
        kpi_card(
            "Logements couverts",
            cov_map.get("Logements", {}).get("Couverts", 0),
            fmt_pourcentage(cov_map.get("Logements", {}).get("Taux", 0)),
            "Logements situés dans des ESI couverts.",
            accent=C_BLUE,
        )
    with c4:
        st.markdown(
            f"""
            <div class="vg-card" style="--accent:{C_VIOLET};">
                <div class="vg-card-accent"></div>
                <div class="vg-card-label">Contrats actifs moyens / ESI</div>
                <div class="vg-card-value">{moyenne_contrats:.1f}</div>
                <div class="vg-card-pill">Moyenne du périmètre</div>
                <div class="vg-card-help">Nombre moyen de contrats actifs rattachés à chaque ESI affiché.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col_cov, col_repartition = st.columns([1, 1.15])

    with col_cov:
        st.markdown('<div class="vg-mini-title">Taux de couverture</div>', unsafe_allow_html=True)
        afficher_couverture(df_couverture)

    with col_repartition:
        st.markdown('<div class="vg-mini-title">Répartition des ESI par nombre de contrats actifs</div>', unsafe_allow_html=True)
        if df_esi_context.empty or "nb_contrats_actifs" not in df_esi_context.columns:
            st.info("Aucune donnée disponible.")
        else:
            repartition = df_esi_context.copy()
            repartition["nb_contrats_actifs"] = pd.to_numeric(
                repartition["nb_contrats_actifs"], errors="coerce"
            ).fillna(0).astype(int)
            repartition["Classe"] = repartition["nb_contrats_actifs"].apply(
                lambda x: "0" if x == 0 else "1" if x == 1 else "2" if x == 2 else "3" if x == 3 else "4 et +"
            )
            ordre = ["0", "1", "2", "3", "4 et +"]
            repartition = (
                repartition.groupby("Classe", as_index=False)["esi_reference"]
                .nunique()
                .rename(columns={"esi_reference": "ESI"})
            )
            repartition["Classe"] = pd.Categorical(repartition["Classe"], categories=ordre, ordered=True)
            repartition = repartition.sort_values("Classe")

            if go is None:
                st.bar_chart(repartition.set_index("Classe")["ESI"], width="stretch")
            else:
                fig = go.Figure(
                    go.Bar(
                        x=repartition["Classe"].astype(str),
                        y=repartition["ESI"],
                        text=repartition["ESI"].apply(fmt_nombre),
                        textposition="outside",
                        marker=dict(color=C_NAVY),
                        hovertemplate="<b>%{x} contrat(s)</b><br>%{y} ESI<extra></extra>",
                    )
                )
                _layout_plotly(fig, 300)
                fig.update_layout(
                    xaxis_title="Nombre de contrats actifs",
                    yaxis_title=None,
                    margin=dict(l=8, r=20, t=10, b=45),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("Consulter le détail des ESI", expanded=False):
        col_search, col_only = st.columns([2.3, 1])
        with col_search:
            recherche_esi = st.text_input(
                "Rechercher un ESI",
                placeholder="Référence, libellé, société, agence, groupe...",
                key="coverage_search_esi",
            )
        with col_only:
            filtre_esi = st.selectbox(
                "Afficher",
                ["Tous les ESI", "ESI couverts", "ESI sans contrat actif", "Multi même métier"],
                key="coverage_filter_esi",
            )

        table_source = df_esi_context.copy()
        if filtre_esi == "ESI couverts":
            table_source = table_source[serie_numerique(table_source, "nb_contrats_actifs") > 0]
        elif filtre_esi == "ESI sans contrat actif":
            table_source = table_source[serie_numerique(table_source, "nb_contrats_actifs") == 0]
        elif filtre_esi == "Multi même métier":
            table_source = table_source[serie_numerique(table_source, "esi_multi_meme_metier") > 0]

        table_esi = filtrer_table_recherche(preparer_esi_table(table_source), recherche_esi)
        st.dataframe(table_esi, width="stretch", hide_index=True, height=460)
        dataframe_download("Télécharger le détail", table_esi, "couverture_esi.csv")


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
    unlinked_contracts = int(global_value(df_global, "contrats_non_rattaches_programme", 0))
    housing_without_program = int(global_value(df_global, "logements_sans_programme", 0))
    multi_meme_metier = int(
        serie_numerique(df_esi_context, "esi_multi_meme_metier").sum()
    )

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        alert_card("Contrats actifs expirés", expired_value, "Statut actif malgré une date de fin dépassée.")
    with q2:
        alert_card("Contrats non rattachés", unlinked_contracts, "Présents en source mais hors couverture programme.")
    with q3:
        alert_card("Logements sans programme", housing_without_program, "Existants mais non exploitables pour la couverture ESI.")
    with q4:
        alert_card("ESI multi même métier", multi_meme_metier, "Plusieurs contrats actifs sur un même métier.")

    st.markdown("<br>", unsafe_allow_html=True)
    section("Choisir une anomalie", "Un seul détail est affiché à la fois pour garder une lecture claire.")

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
        if st.button("Logements sans programme", width="stretch", key="quality_housing"):
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
            st.markdown('<div class="vg-mini-title">Anomalies principales</div>', unsafe_allow_html=True)
            df_q_graph = construire_graph_qualite(df_qualite_resume, df_qualite)
            afficher_barres_horizontales(
                df_q_graph,
                "Anomalie",
                "Objets distincts",
                color=C_VIOLET,
                height_base=320,
            )

        with col_quality_table:
            st.markdown('<div class="vg-mini-title">Résumé qualité</div>', unsafe_allow_html=True)
            if df_qualite_resume.empty:
                st.info("Aucun résumé qualité disponible.")
            else:
                resume = df_qualite_resume.copy()
                cols = [
                    c for c in [
                        "anomalie_type",
                        "objet_type",
                        "gravite",
                        "nb_objets_distincts",
                        "nb_lignes_detail",
                    ] if c in resume.columns
                ]
                resume = resume[cols]
                if "nb_objets_distincts" in resume.columns:
                    resume = resume.sort_values("nb_objets_distincts", ascending=False)
                resume = resume.rename(
                    columns={
                        "anomalie_type": "Type anomalie",
                        "objet_type": "Type objet",
                        "gravite": "Gravité",
                        "nb_objets_distincts": "Objets distincts",
                        "nb_lignes_detail": "Lignes détail",
                    }
                )
                st.dataframe(resume, width="stretch", hide_index=True, height=320)

        recherche_anomalie = st.text_input(
            "Rechercher dans toutes les anomalies",
            placeholder="Référence, type, description, société, agence...",
            key="quality_search_all",
        )
        table_qualite = filtrer_table_recherche(preparer_qualite_table(df_qualite), recherche_anomalie)
        st.dataframe(table_qualite, width="stretch", hide_index=True, height=460)
        dataframe_download("Télécharger les anomalies", table_qualite, "anomalies_patrimoine.csv")


# =====================================================
# FOOTER TECHNIQUE DISCRET
# =====================================================

if "date_maj" in df_global.columns:
    date_maj = global_value(df_global, "date_maj", "")
    st.caption(f"Dernière mise à jour des tables dashboard : {date_maj}")
