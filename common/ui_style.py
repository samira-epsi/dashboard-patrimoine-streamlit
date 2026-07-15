import html
import streamlit as st


# =====================================================
# OUTILS HTML
# =====================================================
from common.charts_style import C_RED

def _safe(value) -> str:
    """Évite les soucis si un texte contient des caractères HTML."""
    if value is None:
        return ""
    return html.escape(str(value))


# =====================================================
# STYLE GLOBAL 3F
# =====================================================

def apply_3f_page_style():
    """
    Style global réutilisable pour toutes les pages Streamlit.
    Gère :
    - largeur de page
    - fond général
    - sidebar
    - navigation Streamlit
    - filtres
    - KPI cards
    - métriques Streamlit
    - graphiques
    - tableaux
    - boutons
    - alertes
    - responsive
    """

    st.markdown(
        """
        <style>
        /* =====================================================
           VARIABLES DESIGN 3F
        ===================================================== */
        /* Masquer l’ancienne interface pendant les recalculs Streamlit */
        [data-stale="true"] {
            opacity: 0 !important;
            visibility: hidden !important;
            pointer-events: none !important;
        }

        [data-stale="true"] * {
            visibility: hidden !important;
        }
        :root {
            --3f-red: #B5121B;
            --3f-red-dark: #8F0E15;
            --3f-red-soft: #FDEBEC;
            --3f-red-light: #FFF1F2;

            --3f-blue: #0057A8;
            --3f-blue-dark: #003F7D;
            --3f-blue-soft: #EAF3FF;

            --3f-green: #16A34A;
            --3f-green-soft: #ECFDF3;

            --3f-orange: #EA580C;
            --3f-orange-soft: #FFF7ED;

            --3f-purple: #7C3AED;
            --3f-purple-soft: #F3E8FF;

            --bg-main: #F8FAFC;
            --bg-card: #FFFFFF;

            --text-main: #0F172A;
            --text-muted: #64748B;
            --text-soft: #94A3B8;

            --border: #E2E8F0;
            --border-soft: #EDF2F7;

            --shadow-sm: 0 6px 16px rgba(15, 23, 42, 0.05);
            --shadow-md: 0 14px 34px rgba(15, 23, 42, 0.08);
            --shadow-red: 0 16px 34px rgba(181, 18, 27, 0.20);
            --radius-md: 16px;
            --radius-lg: 22px;
            --radius-xl: 28px;
        }

        /* =====================================================
           BASE STREAMLIT
        ===================================================== */

        html, body, [class*="css"] {
            font-family: Inter, Arial, sans-serif;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(181, 18, 27, 0.075) 0, transparent 34%),
                radial-gradient(circle at top right, rgba(0, 87, 168, 0.07) 0, transparent 32%),
                linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
        }

        .main {
            background: transparent;
        }

        .block-container {
            max-width: 100%;
            padding-top: 1.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
            padding-bottom: 3rem;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        hr {
            margin-top: 1.6rem !important;
            margin-bottom: 1.4rem !important;
            border-color: #E5E7EB !important;
        }

        /* =====================================================
           TEXTES ET TITRES
        ===================================================== */

        h1, h2, h3 {
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        h2 {
            font-size: 28px !important;
            font-weight: 900 !important;
            margin-top: 0.6rem !important;
            margin-bottom: 0.8rem !important;
        }

        h3 {
            font-size: 21px !important;
            font-weight: 850 !important;
        }

        p, span, div {
            color: inherit;
        }

        .page-title {
            font-size: 46px;
            font-weight: 950;
            color: var(--text-main);
            letter-spacing: -1.2px;
            line-height: 1.02;
            margin-bottom: 8px;
        }

        .page-subtitle {
            color: var(--text-muted);
            font-size: 15px;
            font-weight: 650;
            margin-bottom: 20px;
            line-height: 1.5;
        }

        .section-title {
            font-size: 24px;
            font-weight: 920;
            color: var(--text-main);
            margin-top: 6px;
            margin-bottom: 4px;
        }

        .section-subtitle {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 16px;
        }

        /* =====================================================
           HERO HEADER
        ===================================================== */

        .page-hero {
            position: relative;
            overflow: hidden;
            padding: 28px 30px;
            border-radius: var(--radius-xl);
            background:
                radial-gradient(circle at top right, rgba(255, 255, 255, 0.25) 0, transparent 32%),
                linear-gradient(135deg, #B5121B 0%, #D64550 46%, #8F0E15 100%);
            box-shadow: var(--shadow-red);
            margin-bottom: 24px;
            border: 1px solid rgba(255, 255, 255, 0.22);
        }

        .page-hero::after {
            content: "";
            position: absolute;
            right: -80px;
            top: -80px;
            width: 240px;
            height: 240px;
            background: rgba(255, 255, 255, 0.12);
            border-radius: 999px;
        }

        .page-hero-title {
            position: relative;
            z-index: 1;
            color: #FFFFFF;
            font-size: 42px;
            font-weight: 950;
            letter-spacing: -1px;
            line-height: 1.05;
            margin-bottom: 8px;
        }

        .page-hero-subtitle {
            position: relative;
            z-index: 1;
            color: rgba(255, 255, 255, 0.88);
            font-size: 15px;
            font-weight: 650;
            line-height: 1.5;
            max-width: 980px;
        }

        /* =====================================================
           SIDEBAR
        ===================================================== */

        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at top left, rgba(181, 18, 27, 0.08) 0, transparent 32%),
                linear-gradient(180deg, #FFF8F8 0%, #FFFFFF 58%, #F8FAFC 100%);
            border-right: 1px solid #E5E7EB;
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1.1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            padding-bottom: 1rem;
        }

        [data-testid="stSidebar"] label {
            font-weight: 850 !important;
            color: #1F2937 !important;
            font-size: 13px !important;
            margin-bottom: 4px !important;
        }

        [data-testid="stSidebar"] small {
            color: var(--text-muted) !important;
        }

        /* =====================================================
           APPLICATION MONOPAGE
        ===================================================== */

        /*
        Le logo défini avec st.logo() ou dans setup_page()
        reste visible. Seul le menu automatique Streamlit
        « app / Vue Globale » est masqué.
        */

        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        [data-testid="stSidebarHeader"] {
            min-height: 92px !important;
            padding-top: 14px !important;
            padding-left: 18px !important;
            padding-right: 18px !important;
        }

        [data-testid="stSidebarHeader"] img {
            object-fit: contain !important;
        }

        [data-testid="stSidebarUserContent"] {
            padding-top: 0.25rem !important;
        }

        /* =====================================================
           BLOC FILTRES
        ===================================================== */

        .filters-header {
            padding: 16px 16px 14px 16px;
            border-radius: 20px;
            background:
                radial-gradient(circle at top right, rgba(255,255,255,0.25) 0, transparent 34%),
                linear-gradient(135deg, #B5121B 0%, #D64550 100%);
            color: white;
            box-shadow: var(--shadow-red);
            margin-bottom: 16px;
            border: 1px solid rgba(255,255,255,0.20);
        }

        .filters-title {
            font-size: 22px;
            font-weight: 950;
            line-height: 1.1;
            margin-bottom: 6px;
            color: #FFFFFF;
        }

        .filters-subtitle {
            font-size: 12px;
            font-weight: 650;
            opacity: 0.92;
            line-height: 1.35;
            color: #FFFFFF;
        }

        .filter-meta {
            font-size: 11.5px;
            color: #6B7280;
            margin-top: -8px;
            margin-bottom: 12px;
            padding-left: 2px;
            font-weight: 650;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            border-radius: 14px !important;
            border: 1px solid #E5E7EB !important;
            background: #FFFFFF !important;
            min-height: 44px !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.045) !important;
            transition: all 0.15s ease-in-out !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
            border-color: #D64550 !important;
            box-shadow: 0 8px 20px rgba(181, 18, 27, 0.08) !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
            border-color: var(--3f-red) !important;
            box-shadow: 0 0 0 3px rgba(181, 18, 27, 0.10) !important;
        }

        [data-testid="stSidebar"] span[data-baseweb="tag"] {
            background: #FDEBEC !important;
            color: var(--3f-red) !important;
            border-radius: 999px !important;
            border: 1px solid #F6CBCD !important;
            font-weight: 850 !important;
        }

        /* =====================================================
           INPUTS MAIN
        ===================================================== */

        div[data-baseweb="select"] > div {
            border-radius: 14px !important;
            border: 1px solid #E5E7EB !important;
            min-height: 43px !important;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.035) !important;
        }

        input {
            border-radius: 14px !important;
        }

        textarea {
            border-radius: 14px !important;
        }

        /* =====================================================
           BOUTONS
        ===================================================== */

        .stButton button {
            border-radius: 14px !important;
            border: 1px solid #E5E7EB !important;
            background: #FFFFFF !important;
            color: #1F2937 !important;
            font-weight: 850 !important;
            min-height: 42px !important;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.045) !important;
            transition: all 0.15s ease-in-out !important;
        }

        .stButton button:hover {
            border-color: var(--3f-red) !important;
            color: var(--3f-red) !important;
            background: #FFF1F2 !important;
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(181, 18, 27, 0.10) !important;
        }

        .stButton button:active {
            transform: translateY(0);
        }

        [data-testid="stSidebar"] .stButton button {
            width: 100%;
            border-radius: 14px !important;
            border: 1px solid #E5E7EB !important;
            background: #FFFFFF !important;
            color: var(--3f-red) !important;
            font-weight: 850 !important;
            min-height: 42px !important;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            border-color: #D64550 !important;
            color: #9F0F17 !important;
            background: #FFF1F2 !important;
        }

        /* =====================================================
           RADIO / PILLS
        ===================================================== */

        [role="radiogroup"] {
            gap: 10px;
        }

        [role="radiogroup"] label {
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 999px;
            padding: 8px 14px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
            transition: all 0.15s ease-in-out;
        }

        [role="radiogroup"] label:hover {
            background: #FFF1F2;
            border-color: #F3B7BC;
        }

        [role="radiogroup"] label:has(input:checked) {
            background: #FDEBEC;
            border-color: #D64550;
            color: var(--3f-red);
            font-weight: 850;
        }

        /* =====================================================
           KPI STREAMLIT METRIC
        ===================================================== */

        div[data-testid="stMetric"] {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid var(--border);
            padding: 18px 18px 16px 18px;
            border-radius: 22px;
            box-shadow: var(--shadow-md);
            min-height: 132px;
        }

        div[data-testid="stMetric"]::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
            background: linear-gradient(180deg, var(--3f-red), #D64550);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--text-muted) !important;
            font-size: 13px !important;
            font-weight: 800 !important;
            letter-spacing: 0.01em;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text-main) !important;
            font-size: 34px !important;
            font-weight: 950 !important;
            letter-spacing: -0.8px;
        }

        div[data-testid="stMetricDelta"] {
            color: var(--3f-green) !important;
            font-size: 13px !important;
            font-weight: 850 !important;
        }

        div[data-testid="stMetricDelta"] svg {
            display: none;
        }

        /* =====================================================
           KPI CARDS CUSTOM
        ===================================================== */

        .kpi-card {
            position: relative;
            overflow: hidden;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFDFF 100%);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 20px 20px 18px 20px;
            box-shadow: var(--shadow-md);
            min-height: 148px;
            transition: all 0.18s ease-in-out;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
        }

        .kpi-card::after {
            content: "";
            position: absolute;
            width: 140px;
            height: 140px;
            right: -72px;
            top: -72px;
            border-radius: 999px;
            background: rgba(181, 18, 27, 0.08);
        }

        .kpi-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
        }

        .kpi-label {
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 850;
            line-height: 1.25;
        }

        .kpi-icon {
            width: 38px;
            height: 38px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 950;
            font-size: 15px;
            color: #FFFFFF;
            background: linear-gradient(135deg, #B5121B, #D64550);
            box-shadow: 0 10px 20px rgba(181, 18, 27, 0.22);
        }

        .kpi-value {
            color: var(--text-main);
            font-size: 36px;
            font-weight: 950;
            letter-spacing: -1px;
            line-height: 1.05;
            margin-bottom: 8px;
        }

        .kpi-delta {
            display: inline-flex;
            align-items: center;
            width: fit-content;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 850;
            background: var(--3f-green-soft);
            color: var(--3f-green);
            border: 1px solid #BBF7D0;
        }

        .kpi-help {
            margin-top: 10px;
            color: var(--text-soft);
            font-size: 11.5px;
            font-weight: 600;
            line-height: 1.35;
        }

        .kpi-card.blue .kpi-icon {
            background: linear-gradient(135deg, #0057A8, #2383D9);
            box-shadow: 0 10px 20px rgba(0, 87, 168, 0.20);
        }

        .kpi-card.blue::after {
            background: rgba(0, 87, 168, 0.08);
        }

        .kpi-card.green .kpi-icon {
            background: linear-gradient(135deg, #16A34A, #22C55E);
            box-shadow: 0 10px 20px rgba(22, 163, 74, 0.18);
        }

        .kpi-card.green::after {
            background: rgba(22, 163, 74, 0.08);
        }

        .kpi-card.orange .kpi-icon {
            background: linear-gradient(135deg, #EA580C, #FB923C);
            box-shadow: 0 10px 20px rgba(234, 88, 12, 0.18);
        }

        .kpi-card.orange::after {
            background: rgba(234, 88, 12, 0.08);
        }

        .kpi-card.purple .kpi-icon {
            background: linear-gradient(135deg, #7C3AED, #A78BFA);
            box-shadow: 0 10px 20px rgba(124, 58, 237, 0.18);
        }

        .kpi-card.purple::after {
            background: rgba(124, 58, 237, 0.08);
        }

        /* =====================================================
           CARDS / BLOCS
        ===================================================== */

        .info-box {
            padding: 15px 16px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--border);
            border-radius: 16px;
            color: #334155;
            font-size: 13px;
            font-weight: 650;
            margin-bottom: 18px;
            box-shadow: var(--shadow-sm);
        }

        .panel-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 18px 18px 16px 18px;
            box-shadow: var(--shadow-md);
            margin-bottom: 16px;
        }

        .panel-title {
            font-size: 17px;
            font-weight: 900;
            color: var(--text-main);
            margin-bottom: 4px;
        }

        .panel-subtitle {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 12px;
        }

        .quality-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 850;
            border: 1px solid var(--border);
            background: #FFFFFF;
            color: var(--text-main);
        }

        .quality-badge.red {
            background: var(--3f-red-soft);
            color: var(--3f-red);
            border-color: #F6CBCD;
        }

        .quality-badge.green {
            background: var(--3f-green-soft);
            color: var(--3f-green);
            border-color: #BBF7D0;
        }

        .quality-badge.blue {
            background: var(--3f-blue-soft);
            color: var(--3f-blue);
            border-color: #BFDBFE;
        }

        .quality-badge.orange {
            background: var(--3f-orange-soft);
            color: var(--3f-orange);
            border-color: #FED7AA;
        }

        /* =====================================================
           ALERTES STREAMLIT
        ===================================================== */

        div[data-testid="stAlert"] {
            border-radius: 18px !important;
            border: 1px solid var(--border) !important;
            box-shadow: var(--shadow-sm) !important;
        }

        div[data-testid="stAlert"] p {
            font-weight: 650 !important;
            line-height: 1.45 !important;
        }

        /* =====================================================
           EXPANDERS
        ===================================================== */

        details {
            border-radius: 18px !important;
            border: 1px solid #E5E7EB !important;
            background: #FFFFFF !important;
            box-shadow: var(--shadow-sm) !important;
            overflow: hidden;
        }

        details summary {
            font-weight: 850 !important;
            color: var(--text-main) !important;
            padding: 12px 14px !important;
        }

        details:hover {
            border-color: #F3B7BC !important;
        }

        /* =====================================================
           TABLEAUX / DATAFRAMES
        ===================================================== */

        [data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        [data-testid="stTable"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        /* =====================================================
           GRAPHIQUES
        ===================================================== */

        [data-testid="stPlotlyChart"] {
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 12px;
            box-shadow: var(--shadow-md);
        }

        [data-testid="stVegaLiteChart"] {
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 12px;
            box-shadow: var(--shadow-md);
        }

        [data-testid="stArrowVegaLiteChart"] {
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 12px;
            box-shadow: var(--shadow-md);
        }

        /* =====================================================
           TABS
        ===================================================== */

        button[data-baseweb="tab"] {
            border-radius: 999px !important;
            padding: 8px 16px !important;
            font-weight: 850 !important;
            color: var(--text-muted) !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: #FDEBEC !important;
            color: var(--3f-red) !important;
        }

        div[data-baseweb="tab-list"] {
            gap: 8px;
        }

        /* =====================================================
           CAPTIONS
        ===================================================== */

        [data-testid="stCaptionContainer"] {
            color: var(--text-muted) !important;
            font-weight: 600 !important;
        }

        /* =====================================================
           SPINNER
        ===================================================== */

        [data-testid="stSpinner"] {
            color: var(--3f-red) !important;
            font-weight: 800 !important;
        }

        /* =====================================================
           RESPONSIVE
        ===================================================== */

        @media screen and (max-width: 1200px) {
            .block-container {
                padding-left: 1.3rem;
                padding-right: 1.3rem;
            }

            .page-hero-title {
                font-size: 36px;
            }

            .page-title {
                font-size: 38px;
            }

            .kpi-value {
                font-size: 31px;
            }
        }

        @media screen and (max-width: 768px) {
            .block-container {
                padding-left: 0.9rem;
                padding-right: 0.9rem;
                padding-top: 1rem;
            }

            .page-hero {
                padding: 22px 20px;
                border-radius: 22px;
            }

            .page-hero-title {
                font-size: 30px;
            }

            .page-hero-subtitle {
                font-size: 13px;
            }

            .page-title {
                font-size: 32px;
            }

            div[data-testid="stMetric"] {
                min-height: 112px;
            }

            div[data-testid="stMetricValue"] {
                font-size: 28px !important;
            }

            .kpi-card {
                min-height: 132px;
                padding: 17px;
            }

            .kpi-value {
                font-size: 28px;
            }

            [data-testid="stPlotlyChart"] {
                padding: 8px;
                border-radius: 18px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# COMPOSANTS RÉUTILISABLES
# =====================================================

def page_header(title: str, subtitle: str = ""):
    """
    Header principal de page.
    Compatible avec ton code actuel.
    """

    title = _safe(title)
    subtitle = _safe(subtitle)

    if subtitle:
        st.markdown(
            f"""
            <div class="page-hero">
                <div class="page-hero-title">{title}</div>
                <div class="page-hero-subtitle">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="page-title">{title}</div>
            """,
            unsafe_allow_html=True
        )


def section_header(title: str, subtitle: str = ""):
    """
    Petit titre propre pour structurer une page.
    """

    title = _safe(title)
    subtitle = _safe(subtitle)

    if subtitle:
        st.markdown(
            f"""
            <div class="section-title">{title}</div>
            <div class="section-subtitle">{subtitle}</div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="section-title">{title}</div>
            """,
            unsafe_allow_html=True
        )


def info_box(text: str):
    """
    Bloc d'information propre.
    """

    text = _safe(text)

    st.markdown(
        f"""
        <div class="info-box">{text}</div>
        """,
        unsafe_allow_html=True
    )


def panel_start(title: str = "", subtitle: str = ""):
    """
    Ouvre visuellement un bloc.
    À utiliser seulement si tu veux écrire du HTML custom autour.
    """

    title = _safe(title)
    subtitle = _safe(subtitle)

    html_title = f'<div class="panel-title">{title}</div>' if title else ""
    html_subtitle = f'<div class="panel-subtitle">{subtitle}</div>' if subtitle else ""

    st.markdown(
        f"""
        <div class="panel-card">
            {html_title}
            {html_subtitle}
        """,
        unsafe_allow_html=True
    )


def panel_end():
    """
    Ferme un panel ouvert avec panel_start.
    """

    st.markdown(
        """
        </div>
        """,
        unsafe_allow_html=True
    )


def kpi_card(
    label: str,
    value,
    delta: str = "",
    help_text: str = "",
    tone: str = "red",
    icon: str = ""
):
    """
    Carte KPI custom plus sexy que st.metric.

    tone possibles :
    - red
    - blue
    - green
    - orange
    - purple
    """

    allowed_tones = {"red", "blue", "green", "orange", "purple"}
    tone = tone if tone in allowed_tones else "red"

    label = _safe(label)
    value = _safe(value)
    delta = _safe(delta)
    help_text = _safe(help_text)
    icon = _safe(icon)

    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    help_html = f'<div class="kpi-help">{help_text}</div>' if help_text else ""
    icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ""

    st.markdown(
        f"""
        <div class="kpi-card {tone}">
            <div class="kpi-top">
                <div class="kpi-label">{label}</div>
                {icon_html}
            </div>
            <div class="kpi-value">{value}</div>
            {delta_html}
            {help_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def quality_badge(label: str, tone: str = "blue"):
    """
    Petit badge pour les états qualité.
    """

    allowed_tones = {"red", "blue", "green", "orange"}
    tone = tone if tone in allowed_tones else "blue"

    label = _safe(label)

    st.markdown(
        f"""
        <span class="quality-badge {tone}">{label}</span>
        """,
        unsafe_allow_html=True
    )



# =====================================================
# STYLE SPÉCIFIQUE — VUE GLOBALE
# =====================================================
#
# Cette partie reprend le rendu déjà validé dans Vue Globale.
# Elle est séparée du fonctionnel afin que la page ne contienne
# plus de CSS ni de composants HTML.


def format_nombre(value) -> str:
    """Formate un nombre entier avec des espaces comme séparateurs."""
    try:
        return f"{int(float(value or 0)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def fmt_nombre(value) -> str:
    """Alias utilisé par les composants historiques de Vue Globale."""
    return format_nombre(value)


def apply_vue_globale_style():
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


        /* LOGO ET CHARGEMENT DE LA PAGE */
        [data-testid="stSidebarHeader"] img {
            max-height: 64px !important;
            width: auto !important;
            object-fit: contain !important;
        }

        .vg-loading-card {
            display: flex;
            align-items: center;
            gap: 15px;
            width: 100%;
            box-sizing: border-box;
            margin: 10px 0 18px 0;
            padding: 16px 18px;
            background: #FFFFFF;
            border: 1px solid #E7E3E8;
            border-radius: 15px;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.24);
        }

        .vg-loading-mark {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            flex: 0 0 auto;
        }

        .vg-loading-mark span {
            width: 7px;
            height: 24px;
            border-radius: 999px;
            background: #E5114D;
            animation: vg-loading-pulse 1s ease-in-out infinite;
        }

        .vg-loading-mark span:nth-child(2) {
            height: 17px;
            background: #80CDFF;
            animation-delay: .12s;
        }

        .vg-loading-mark span:nth-child(3) {
            height: 11px;
            background: #432ABD;
            animation-delay: .24s;
        }

        .vg-loading-title {
            color: #17243A;
            font-size: 13px;
            font-weight: 800;
            line-height: 1.3;
        }

        .vg-loading-subtitle {
            color: #8A94A6;
            font-size: 11.5px;
            font-weight: 600;
            line-height: 1.4;
            margin-top: 2px;
        }

        @keyframes vg-loading-pulse {
            0%, 100% {
                transform: scaleY(.72);
                opacity: .55;
            }
            50% {
                transform: scaleY(1);
                opacity: 1;
            }
        }


        /* CHARGEMENT DE LA PAGE */
        .vg-loading-shell {
            display: flex;
            width: 100%;
            min-height: 180px;
            align-items: center;
            justify-content: center;
            padding: 20px 0 28px;
        }

        .vg-loading-card {
            display: flex;
            width: min(520px, 92vw);
            align-items: center;
            gap: 16px;
            box-sizing: border-box;
            padding: 20px 22px;
            background: #FFFFFF;
            border: 1px solid #E7E3E8;
            border-radius: 18px;
            box-shadow: 0 14px 34px -24px rgba(23, 59, 105, 0.30);
        }

        .vg-loading-logo {
            display: grid;
            width: 48px;
            height: 48px;
            flex: 0 0 48px;
            place-items: center;
            color: #FFFFFF;
            background: #E5114D;
            border-radius: 14px;
            font-size: 17px;
            font-weight: 900;
            letter-spacing: -0.5px;
        }

        .vg-loading-content {
            min-width: 0;
            flex: 1;
        }

        .vg-loading-title {
            color: #17243A;
            font-size: 14px;
            font-weight: 850;
            line-height: 1.3;
        }

        .vg-loading-subtitle {
            margin-top: 3px;
            color: #8A94A6;
            font-size: 11.5px;
            font-weight: 600;
            line-height: 1.4;
        }

        .vg-loading-progress {
            position: relative;
            overflow: hidden;
            height: 5px;
            margin-top: 12px;
            background: #F2E8EC;
            border-radius: 999px;
        }

        .vg-loading-progress span {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 42%;
            background: linear-gradient(
                90deg,
                #E5114D,
                #FFB7E3,
                #80CDFF
            );
            border-radius: inherit;
            animation: vg-loading-slide 1.15s ease-in-out infinite;
        }

        @keyframes vg-loading-slide {
            0% {
                left: -42%;
            }
            100% {
                left: 100%;
            }
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

        /* COUVERTURE DES ÉQUIPEMENTS */
        .vg-equipment-coverage {
            display: grid;
            grid-template-columns: minmax(0, 1.25fr) minmax(220px, 0.75fr);
            gap: 16px;
            align-items: stretch;
            margin-top: 4px;
        }

        .vg-equipment-coverage-main,
        .vg-equipment-stat {
            box-sizing: border-box;
            background: #FFFFFF;
            border: 1px solid #E4E1E3;
            border-radius: 18px;
            box-shadow: none;
        }

        .vg-equipment-coverage-main {
            display: flex;
            min-height: 390px;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px 24px 20px;
        }

        .vg-equipment-gauge {
            --coverage: 0%;
            position: relative;
            display: grid;
            width: min(270px, 78%);
            aspect-ratio: 1;
            place-items: center;
            border-radius: 50%;
            background:
                conic-gradient(
                    from -90deg,
                    #E5114D 0 var(--coverage),
                    #F0EEE8 var(--coverage) 100%
                );
        }

        .vg-equipment-gauge::after {
            content: "";
            position: absolute;
            inset: 17px;
            border-radius: 50%;
            background: #FFFFFF;
        }

        .vg-equipment-gauge-inner {
            position: relative;
            z-index: 1;
            text-align: center;
        }

        .vg-equipment-gauge-rate {
            color: #E5114D;
            font-size: clamp(42px, 4.2vw, 58px);
            font-weight: 850;
            letter-spacing: -2px;
            line-height: 1;
        }

        .vg-equipment-gauge-label {
            margin-top: 8px;
            color: #5F5F60;
            font-size: 15px;
            font-weight: 700;
        }

        .vg-equipment-gauge-total {
            width: 100%;
            margin-top: 18px;
            color: #173B69;
            font-size: 18px;
            font-weight: 850;
        }

        .vg-equipment-gauge-note {
            width: 100%;
            margin-top: 8px;
            color: #7C8491;
            font-size: 11.5px;
            font-weight: 600;
            line-height: 1.4;
        }

        .vg-equipment-coverage-stats {
            display: grid;
            grid-template-rows: 1fr 1fr;
            gap: 16px;
        }

        .vg-equipment-stat {
            display: flex;
            min-height: 185px;
            flex-direction: column;
            justify-content: center;
            padding: 24px 26px;
        }

        .vg-equipment-stat-covered {
            background: #FFF5F8;
            border: 2px solid #E5114D;
        }

        .vg-equipment-stat-uncovered {
            background: #FFFFFF;
            border-color: #DDDAD1;
        }

        .vg-equipment-stat-label {
            color: #173B69;
            font-size: 15px;
            font-weight: 850;
        }

        .vg-equipment-stat-value {
            margin-top: 14px;
            color: #173B69;
            font-size: clamp(38px, 3.7vw, 54px);
            font-weight: 850;
            letter-spacing: -1.5px;
            line-height: 1;
        }

        .vg-equipment-stat-covered .vg-equipment-stat-value {
            color: #E5114D;
        }

        .vg-equipment-stat-help {
            margin-top: 18px;
            color: #5F6368;
            font-size: 13.5px;
            font-weight: 600;
        }

        @media screen and (max-width: 1100px) {
            .vg-equipment-coverage {
                grid-template-columns: 1fr;
            }

            .vg-equipment-coverage-stats {
                grid-template-columns: 1fr 1fr;
                grid-template-rows: none;
            }

            .vg-equipment-stat {
                min-height: 150px;
            }
        }

        @media screen and (max-width: 620px) {
            .vg-equipment-coverage-main {
                min-height: 340px;
                padding: 20px 16px;
            }

            .vg-equipment-coverage-stats {
                grid-template-columns: 1fr;
            }

            .vg-equipment-stat {
                min-height: 132px;
                padding: 20px;
            }

            .vg-equipment-gauge {
                width: min(235px, 78vw);
            }

            .vg-equipment-gauge-total,
            .vg-equipment-gauge-note {
                text-align: center;
            }
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


def vg_hero(title: str, subtitle: str):
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


def vg_section(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="vg-section-title">{_safe(title)}</div>
        <div class="vg-section-subtitle">{_safe(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )


def vg_info(message: str):
    st.markdown(
        f'<div class="vg-info">{_safe(message)}</div>',
        unsafe_allow_html=True,
    )


def vg_kpi_card(
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


def vg_alert_card(title, value, help_text):
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
