import html
import streamlit as st


# =====================================================
# OUTILS HTML
# =====================================================

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
           NAVIGATION STREAMLIT
        ===================================================== */

        [data-testid="stSidebarNav"] {
            padding-top: 8px !important;
            margin-bottom: 18px !important;
        }

        [data-testid="stSidebarNav"] span {
            font-size: 18px !important;
            font-weight: 950 !important;
            letter-spacing: 0.2px !important;
            color: var(--3f-red) !important;
        }

        [data-testid="stSidebarNav"] a {
            font-size: 16px !important;
            font-weight: 820 !important;
            color: #1F2937 !important;
            padding: 11px 12px !important;
            border-radius: 14px !important;
            transition: all 0.15s ease-in-out !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: linear-gradient(135deg, #FDEBEC 0%, #FFF1F2 100%) !important;
            color: var(--3f-red) !important;
            font-weight: 950 !important;
            box-shadow: 0 8px 18px rgba(181, 18, 27, 0.10);
        }

        [data-testid="stSidebarNav"] a:hover {
            background: #FFF1F2 !important;
            color: var(--3f-red) !important;
            transform: translateX(2px);
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