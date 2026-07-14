from __future__ import annotations

import html
import math
from datetime import datetime
from typing import Callable, Iterable
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
from common.filters import render_filtres_patrimoine
from common.ui_style import apply_3f_page_style
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
SOURCE_PRESTATIONS = "dashboard.contrats_prestations"
SOURCE_EQUIPEMENTS = "dashboard.equipements_couverture"
SOURCE_EQUIPEMENTS_CONTRATS = "dashboard.equipements_contrats"
SOURCE_ALERTES = "dashboard.alertes_couverture"

SOURCES_OBLIGATOIRES = [SOURCE_ESI, SOURCE_CONTRATS]
SOURCES_OPTIONNELLES = [
    SOURCE_GLOBAL,
    SOURCE_CREATIONS,
    SOURCE_QUALITE,
    SOURCE_QUALITE_RESUME,
    SOURCE_PRESTATIONS,
    SOURCE_EQUIPEMENTS,
    SOURCE_EQUIPEMENTS_CONTRATS,
    SOURCE_ALERTES,
]

CACHE_TTL = 3600
SQL_TIMEOUT_MS = 20000
TAILLE_PAGE = 100


# =====================================================
# CHARTE ET PAGE
# =====================================================

C_RED = "#E5114D"
C_RED_DARK = "#C90F43"
C_PINK = "#FFB7E3"
C_PINK_SOFT = "#FFF1F6"
C_BLUE = "#0074FF"
C_BLUE_LIGHT = "#80CDFF"
C_BLUE_SOFT = "#EFF8FE"
C_VIOLET = "#432ABD"
C_TEAL = "#008080"
C_YELLOW = "#FFDC55"
C_INK = "#1B2430"
C_INK_SOFT = "#667085"
C_INK_MUTE = "#8A94A6"
C_LINE = "#E7E3E8"
C_GRID = "#E9EEF3"

setup_page("Vue Globale", None)
apply_3f_page_style()


def inject_style() -> None:
    st.markdown(
        r"""
        <style>
        :root {
            --red: #E5114D;
            --red-dark: #C90F43;
            --pink-soft: #FFF1F6;
            --blue-soft: #EFF8FE;
            --blue-light: #80CDFF;
            --ink: #1B2430;
            --ink-soft: #667085;
            --ink-mute: #8A94A6;
            --line: #E7E3E8;
            --surface: #FFFFFF;
            --canvas: #FAFAFB;
        }

        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .stApp {
            background: var(--canvas) !important;
        }

        .block-container {
            max-width: 1540px !important;
            padding-top: 1.15rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-bottom: 3rem !important;
        }

        .vg-hero {
            position: relative;
            overflow: hidden;
            padding: 27px 34px;
            margin-bottom: 12px;
            background: var(--pink-soft);
            border: 1px solid #E8D8E1;
            border-radius: 20px;
            box-shadow: 0 10px 26px -22px rgba(27, 36, 48, 0.24);
        }

        .vg-hero::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            height: 5px;
            background: var(--red);
        }

        .vg-hero::after {
            content: "";
            position: absolute;
            width: 150px;
            height: 150px;
            right: -70px;
            bottom: -85px;
            border-radius: 50%;
            background: rgba(128, 205, 255, 0.18);
        }

        .vg-hero-eyebrow {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
            color: #A33A61;
            font-size: 11.5px;
            font-weight: 750;
            letter-spacing: 1.3px;
            text-transform: uppercase;
        }

        .vg-hero-eyebrow::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--red);
        }

        .vg-hero-title {
            position: relative;
            z-index: 1;
            margin-bottom: 8px;
            color: var(--ink);
            font-size: 34px;
            line-height: 1.08;
            font-weight: 820;
            letter-spacing: -0.7px;
        }

        .vg-hero-subtitle {
            position: relative;
            z-index: 1;
            max-width: 980px;
            color: var(--ink-soft);
            font-size: 14px;
            line-height: 1.55;
            font-weight: 520;
        }

        .st-key-dashboard_tabs {
            margin-bottom: 20px !important;
            border-bottom: 1px solid var(--line);
        }

        .st-key-dashboard_tabs div[role="radiogroup"] {
            display: flex !important;
            align-items: flex-end !important;
            gap: 27px !important;
            padding: 0 4px !important;
            background: transparent !important;
            border: 0 !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label {
            position: relative !important;
            min-height: 48px !important;
            padding: 13px 2px 12px 2px !important;
            color: var(--ink-soft) !important;
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            font-weight: 680 !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked),
        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked) * {
            color: var(--red) !important;
        }

        .st-key-dashboard_tabs div[role="radiogroup"] label:has(input:checked)::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: -1px;
            height: 3px;
            border-radius: 3px 3px 0 0;
            background: var(--red);
        }

        .st-key-dashboard_tabs input[type="radio"] {
            display: none !important;
        }

        .vg-section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 5px;
            margin-bottom: 3px;
            color: var(--ink);
            font-size: 20px;
            font-weight: 820;
            letter-spacing: -0.3px;
        }

        .vg-section-title::before {
            content: "";
            width: 5px;
            height: 21px;
            border-radius: 99px;
            background: var(--red);
        }

        .vg-section-subtitle {
            max-width: 1050px;
            margin-bottom: 15px;
            color: var(--ink-soft);
            font-size: 13px;
            line-height: 1.5;
        }

        .vg-mini-title {
            margin: 2px 0 10px 0;
            color: var(--ink);
            font-size: 14px;
            font-weight: 760;
        }

        .vg-info {
            margin: 8px 0 16px 0;
            padding: 12px 15px;
            color: var(--ink-soft);
            background: var(--blue-soft);
            border: 1px solid #D9E8F1;
            border-radius: 12px;
            font-size: 12.5px;
            line-height: 1.5;
        }

        .vg-card {
            min-height: 178px;
            height: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            padding: 18px 19px 17px 19px;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.25);
        }

        .vg-card-accent {
            width: 34px;
            height: 4px;
            margin-bottom: 14px;
            border-radius: 99px;
            background: var(--accent, #E5114D);
        }

        .vg-card-label {
            margin-bottom: 9px;
            color: var(--ink-mute);
            font-size: 10.8px;
            font-weight: 760;
            letter-spacing: 0.55px;
            text-transform: uppercase;
        }

        .vg-card-value {
            margin-bottom: 10px;
            color: var(--ink);
            font-size: 32px;
            line-height: 1;
            font-weight: 840;
            letter-spacing: -0.8px;
        }

        .vg-card-pill {
            display: inline-flex;
            width: fit-content;
            margin-bottom: 9px;
            padding: 4px 9px;
            color: var(--accent, #E5114D);
            background: #FFF7FA;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 750;
        }

        .vg-card-help {
            margin-top: auto;
            color: var(--ink-mute);
            font-size: 11.4px;
            line-height: 1.42;
        }

        .vg-alert-card {
            min-height: 130px;
            height: 100%;
            box-sizing: border-box;
            padding: 15px 17px;
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 4px solid var(--accent, #E5114D);
            border-radius: 14px;
            box-shadow: 0 7px 18px -17px rgba(27, 36, 48, 0.24);
        }

        .vg-alert-title {
            margin-bottom: 8px;
            color: var(--ink-soft);
            font-size: 10.7px;
            font-weight: 760;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .vg-alert-value {
            margin-bottom: 8px;
            color: var(--ink);
            font-size: 28px;
            line-height: 1;
            font-weight: 840;
        }

        .vg-alert-help {
            color: var(--ink-mute);
            font-size: 11.4px;
            line-height: 1.4;
        }

        .vg-table-summary {
            display: flex;
            align-items: center;
            gap: 18px;
            margin: 9px 0 14px 0;
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
            color: var(--red);
            font-size: 20px;
            font-weight: 840;
        }

        .vg-table-summary-label {
            color: var(--ink-soft);
            font-size: 12px;
            font-weight: 680;
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
            font-weight: 740;
            white-space: nowrap;
        }

        .vg-pagination-current {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            min-height: 48px;
            height: 48px;
            padding: 6px 14px;
            background: #FFF7FA;
            border: 1px solid #EEDCE5;
            border-radius: 12px;
            box-sizing: border-box;
        }

        .vg-pagination-label {
            justify-self: end;
            margin-right: 9px;
            color: var(--ink-soft);
            font-size: 12px;
            font-weight: 700;
        }

        .vg-pagination-current strong {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 38px;
            height: 34px;
            padding: 0 10px;
            color: #FFFFFF;
            background: var(--red);
            border-radius: 9px;
            font-size: 14px;
            font-weight: 820;
        }

        .vg-pagination-total {
            justify-self: start;
            margin-left: 9px;
            color: var(--ink-soft);
            font-size: 12px;
            font-weight: 700;
        }

        .vg-search-active {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin: 7px 0 10px 0;
            padding: 7px 10px;
            color: #A3184A;
            background: var(--pink-soft);
            border: 1px solid #E7C8D6;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 740;
        }

        .vg-search-active-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--red);
        }

        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {
            overflow: hidden;
            background: #FFFFFF;
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: 0 8px 20px -18px rgba(27, 36, 48, 0.24);
        }

        div[data-testid="stPlotlyChart"] {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 8px;
        }

        div[data-testid="stPlotlyChart"] > div,
        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container {
            width: 100% !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }

        div[data-testid="stExpander"] {
            overflow: hidden;
            background: #FFFFFF;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
            box-shadow: 0 6px 18px -17px rgba(27, 36, 48, 0.22);
        }

        .stButton button,
        div[data-testid="stPopover"] button {
            min-height: 44px !important;
            color: #9D174D !important;
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-radius: 11px !important;
            box-shadow: none !important;
            font-weight: 680 !important;
        }

        .stButton button:hover,
        div[data-testid="stPopover"] button:hover {
            color: var(--red) !important;
            background: #FFF7FA !important;
            border-color: #DDBCCB !important;
        }

        .stDownloadButton button {
            min-height: 44px !important;
            color: #FFFFFF !important;
            background: var(--red) !important;
            border: 1px solid var(--red) !important;
            border-radius: 11px !important;
            font-weight: 720 !important;
        }

        .stDownloadButton button:hover {
            background: var(--red-dark) !important;
            border-color: var(--red-dark) !important;
        }

        div[role="radiogroup"] {
            gap: 6px !important;
        }

        div[role="radiogroup"] label {
            min-height: 42px !important;
            padding: 8px 13px !important;
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-radius: 10px !important;
        }

        div[role="radiogroup"] label:has(input:checked) {
            color: #A3184A !important;
            background: var(--pink-soft) !important;
            border-color: #E7C8D6 !important;
        }

        div[role="radiogroup"] label:has(input:checked) * {
            color: #A3184A !important;
        }

        div[data-testid="stHorizontalBlock"] {
            align-items: stretch !important;
        }

        @media screen and (max-width: 1050px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }

            .vg-hero-title {
                font-size: 29px;
            }

            .st-key-dashboard_tabs div[role="radiogroup"] {
                gap: 16px !important;
                overflow-x: auto !important;
                flex-wrap: nowrap !important;
            }

            .st-key-dashboard_tabs div[role="radiogroup"] label {
                white-space: nowrap !important;
            }
        }

        @media screen and (max-width: 760px) {
            .vg-hero {
                padding: 24px 20px;
                border-radius: 16px;
            }

            .vg-card,
            .vg-alert-card {
                min-height: 145px;
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


    st.markdown(
        r"""
        <style>
        /* Traduction de l’instruction native du champ de recherche */
        .st-key-global_search_contract [data-testid="InputInstructions"] {
            font-size: 0 !important;
        }

        .st-key-global_search_contract [data-testid="InputInstructions"]::after {
            content: "Appuyez sur Entrée pour appliquer";
            color: #8A94A6;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_style()


# =====================================================
# OUTILS GÉNÉRAUX
# =====================================================


def safe(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def fmt_nombre(value: object, decimales: int = 0) -> str:
    try:
        nombre = float(value)
        if pd.isna(nombre):
            return "0"
        if decimales:
            return f"{nombre:,.{decimales}f}".replace(",", " ").replace(".", ",")
        return f"{int(round(nombre)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def fmt_pourcentage(value: object, decimales: int = 1) -> str:
    try:
        return f"{float(value):.{decimales}f} %".replace(".", ",")
    except (TypeError, ValueError):
        return "0,0 %"


def fmt_date(value: object, avec_heure: bool = False) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
        date = pd.to_datetime(value)
        return date.strftime("%d/%m/%Y %H:%M") if avec_heure else date.strftime("%d/%m/%Y")
    except Exception:
        return ""


def aujourd_hui_france() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(ZoneInfo("Europe/Paris")).date())


def nettoyer_texte(serie: pd.Series, valeur_vide: str = "Non renseigné") -> pd.Series:
    return (
        serie.fillna(valeur_vide)
        .astype(str)
        .str.strip()
        .replace(
            {
                "": valeur_vide,
                "nan": valeur_vide,
                "None": valeur_vide,
                "<NA>": valeur_vide,
                "undefined": valeur_vide,
            }
        )
    )


def normaliser_reference(serie: pd.Series) -> pd.Series:
    return (
        serie.astype("string")
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    )


def serie_numerique(df: pd.DataFrame, colonne: str) -> pd.Series:
    if colonne not in df.columns:
        return pd.Series(0, index=df.index, dtype="float64")
    return pd.to_numeric(df[colonne], errors="coerce").fillna(0)


def liste_refs_valides(df: pd.DataFrame, colonne: str) -> list[str]:
    if df.empty or colonne not in df.columns:
        return []
    serie = normaliser_reference(df[colonne]).dropna()
    return serie.astype(str).drop_duplicates().tolist()


def refs_ont_change(df_base: pd.DataFrame, df_filtre: pd.DataFrame, colonne: str) -> bool:
    return set(liste_refs_valides(df_base, colonne)) != set(liste_refs_valides(df_filtre, colonne))


def taux(nombre: float, total: float) -> float:
    return round(nombre / total * 100, 2) if total else 0.0


def libelle_code(code: object) -> str:
    texte = str(code or "").strip()
    if not texte:
        return "Non renseigné"
    return texte.replace("_", " ").capitalize()


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="vg-hero">
            <div class="vg-hero-eyebrow">Patrimoine 3F</div>
            <div class="vg-hero-title">{safe(title)}</div>
            <div class="vg-hero-subtitle">{safe(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="vg-section-title">{safe(title)}</div>
        <div class="vg-section-subtitle">{safe(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )


def info(text_value: str) -> None:
    st.markdown(
        f'<div class="vg-info">{safe(text_value)}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(
    label: str,
    value: object,
    pill: str,
    help_text: str,
    accent: str = C_RED,
    decimales: int = 0,
) -> None:
    st.markdown(
        f"""
        <div class="vg-card" style="--accent:{safe(accent)};">
            <div class="vg-card-accent"></div>
            <div class="vg-card-label">{safe(label)}</div>
            <div class="vg-card-value">{safe(fmt_nombre(value, decimales))}</div>
            <div class="vg-card-pill">{safe(pill)}</div>
            <div class="vg-card-help">{safe(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_card(
    title: str,
    value: object,
    help_text: str,
    accent: str = C_RED,
    decimales: int = 0,
) -> None:
    st.markdown(
        f"""
        <div class="vg-alert-card" style="--accent:{safe(accent)};">
            <div class="vg-alert-title">{safe(title)}</div>
            <div class="vg-alert-value">{safe(fmt_nombre(value, decimales))}</div>
            <div class="vg-alert-help">{safe(help_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def table_summary(
    valeur_1: object,
    libelle_1: str,
    valeur_2: object | None = None,
    libelle_2: str | None = None,
    mode: str | None = None,
) -> None:
    bloc_2 = ""
    if valeur_2 is not None and libelle_2:
        bloc_2 = (
            '<div class="vg-table-summary-separator"></div>'
            '<div class="vg-table-summary-item">'
            f'<span class="vg-table-summary-value">{safe(fmt_nombre(valeur_2))}</span>'
            f'<span class="vg-table-summary-label">{safe(libelle_2)}</span>'
            "</div>"
        )

    bloc_mode = (
        f'<div class="vg-table-summary-mode">{safe(mode)}</div>'
        if mode
        else ""
    )

    st.markdown(
        (
            '<div class="vg-table-summary">'
            '<div class="vg-table-summary-item">'
            f'<span class="vg-table-summary-value">{safe(fmt_nombre(valeur_1))}</span>'
            f'<span class="vg-table-summary-label">{safe(libelle_1)}</span>'
            "</div>"
            f"{bloc_2}{bloc_mode}</div>"
        ),
        unsafe_allow_html=True,
    )


def dataframe_download(label: str, df: pd.DataFrame, filename: str) -> None:
    if df.empty:
        return
    data = df.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
    st.download_button(
        label,
        data=data,
        file_name=filename,
        mime="text/csv",
        width="stretch",
    )


def filtrer_table_recherche(df: pd.DataFrame, recherche: str) -> pd.DataFrame:
    if df.empty or not str(recherche or "").strip():
        return df.copy()
    terme = str(recherche).strip().lower()
    masque = pd.Series(False, index=df.index)
    for colonne in df.columns:
        masque |= (
            df[colonne]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(terme, regex=False, na=False)
        )
    return df[masque].copy()


def appliquer_recherche_contrats(
    recherche: str,
    df_contrats: pd.DataFrame,
    df_prestations: pd.DataFrame,
    df_master: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, set[str]]:
    terme = str(recherche or "").strip()
    if not terme:
        refs = set(liste_refs_valides(df_master, "contract_reference"))
        refs.update(liste_refs_valides(df_contrats, "contract_reference"))
        return df_contrats.copy(), df_prestations.copy(), df_master.copy(), refs

    refs: set[str] = set()
    for frame, colonne_ref in [
        (df_contrats, "contract_reference"),
        (df_prestations, "contract_reference_3f"),
        (df_master, "contract_reference"),
    ]:
        if frame.empty or colonne_ref not in frame.columns:
            continue
        trouves = filtrer_table_recherche(frame, terme)
        refs.update(liste_refs_valides(trouves, colonne_ref))

    contrats = (
        df_contrats[df_contrats["contract_reference"].astype(str).isin(refs)].copy()
        if "contract_reference" in df_contrats.columns
        else df_contrats.iloc[0:0].copy()
    )
    prestations = (
        df_prestations[
            df_prestations["contract_reference_3f"].astype(str).isin(refs)
        ].copy()
        if "contract_reference_3f" in df_prestations.columns
        else df_prestations.iloc[0:0].copy()
    )
    master = (
        df_master[df_master["contract_reference"].astype(str).isin(refs)].copy()
        if "contract_reference" in df_master.columns
        else df_master.iloc[0:0].copy()
    )
    return contrats, prestations, master, refs


def afficher_table_paginated(
    df: pd.DataFrame,
    key: str,
    filename: str,
    hauteur: int = 470,
) -> None:
    if df.empty:
        st.info("Aucune ligne ne correspond aux filtres sélectionnés.")
        return

    nombre_lignes = len(df)
    nombre_pages = max(1, math.ceil(nombre_lignes / TAILLE_PAGE))
    cle_page = f"page_{key}"
    cle_signature = f"signature_{key}"
    signature = f"{nombre_lignes}|{'|'.join(map(str, df.columns))}"

    if st.session_state.get(cle_signature) != signature:
        st.session_state[cle_signature] = signature
        st.session_state[cle_page] = 1

    page = max(1, min(int(st.session_state.get(cle_page, 1)), nombre_pages))
    st.session_state[cle_page] = page

    gauche, centre, droite = st.columns([1, 1.35, 1], vertical_alignment="center")
    with gauche:
        if st.button(
            "‹  Précédent",
            key=f"precedent_{key}",
            width="stretch",
            disabled=page <= 1,
        ):
            st.session_state[cle_page] = page - 1
            st.rerun()

    with centre:
        st.markdown(
            (
                '<div class="vg-pagination-current">'
                '<span class="vg-pagination-label">Page</span>'
                f"<strong>{page}</strong>"
                f'<span class="vg-pagination-total">sur {nombre_pages}</span>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    with droite:
        if st.button(
            "Suivant  ›",
            key=f"suivant_{key}",
            width="stretch",
            disabled=page >= nombre_pages,
        ):
            st.session_state[cle_page] = page + 1
            st.rerun()

    debut = (page - 1) * TAILLE_PAGE
    fin = min(debut + TAILLE_PAGE, nombre_lignes)
    page_df = df.iloc[debut:fin].copy()

    st.caption(
        f"Lignes {fmt_nombre(debut + 1)} à {fmt_nombre(fin)} sur {fmt_nombre(nombre_lignes)}."
    )
    st.dataframe(page_df, width="stretch", hide_index=True, height=hauteur)
    dataframe_download("Télécharger toutes les lignes filtrées", df, filename)


def selectionner_colonnes(
    colonnes_disponibles: list[str],
    colonnes_defaut: list[str],
    key: str,
) -> list[str]:
    colonnes_defaut = [c for c in colonnes_defaut if c in colonnes_disponibles]
    state_key = f"colonnes_selectionnees_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = colonnes_defaut.copy()

    selection = [
        c for c in st.session_state[state_key] if c in colonnes_disponibles
    ]

    with st.popover("Choisir les colonnes", use_container_width=True):
        with st.form(f"form_colonnes_{key}"):
            choix: list[str] = []
            for index, colonne in enumerate(colonnes_disponibles):
                coche = st.checkbox(
                    colonne,
                    value=colonne in selection,
                    key=f"check_{key}_{index}",
                )
                if coche:
                    choix.append(colonne)

            c1, c2, c3 = st.columns(3)
            with c1:
                appliquer = st.form_submit_button("Appliquer", type="primary", width="stretch")
            with c2:
                tout = st.form_submit_button("Tout sélectionner", width="stretch")
            with c3:
                reset = st.form_submit_button("Réinitialiser", width="stretch")

            if tout:
                st.session_state[state_key] = colonnes_disponibles.copy()
                st.rerun()
            if reset:
                st.session_state[state_key] = colonnes_defaut.copy()
                st.rerun()
            if appliquer:
                st.session_state[state_key] = choix
                st.rerun()

    return [c for c in st.session_state[state_key] if c in colonnes_disponibles]


def layout_plotly(fig, height: int, showlegend: bool = False) -> None:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=24, t=14, b=28),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color=C_INK),
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="white", font_color=C_INK),
    )


def config_graphique_exportable(nom_fichier: str) -> dict:
    """Affiche uniquement le bouton de téléchargement PNG de Plotly."""
    return {
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": [
            "zoom2d",
            "pan2d",
            "select2d",
            "lasso2d",
            "zoomIn2d",
            "zoomOut2d",
            "autoScale2d",
            "resetScale2d",
            "hoverClosestCartesian",
            "hoverCompareCartesian",
            "toggleSpikelines",
        ],
        "toImageButtonOptions": {
            "format": "png",
            "filename": nom_fichier,
            "width": 1600,
            "height": 900,
            "scale": 2,
        },
    }


# =====================================================
# CONNEXION ET CHARGEMENT
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


def table_exists(conn, source: str) -> bool:
    return conn.execute(
        text("SELECT to_regclass(:source)"), {"source": source}
    ).scalar() is not None


def tester_connexion() -> tuple[bool, str | None]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, str(exc)


def lire_source(conn, source: str, obligatoire: bool = False) -> pd.DataFrame:
    if not table_exists(conn, source):
        if obligatoire:
            raise RuntimeError(f"Source SQL manquante : {source}")
        return pd.DataFrame()
    return pd.read_sql_query(text(f"SELECT * FROM {source}"), conn)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def charger_donnees() -> dict[str, pd.DataFrame]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text(f"SET statement_timeout = {SQL_TIMEOUT_MS}"))
            donnees = {
                "global": lire_source(conn, SOURCE_GLOBAL),
                "esi": lire_source(conn, SOURCE_ESI, obligatoire=True),
                "contrats": lire_source(conn, SOURCE_CONTRATS, obligatoire=True),
                "creations": lire_source(conn, SOURCE_CREATIONS),
                "qualite": lire_source(conn, SOURCE_QUALITE),
                "qualite_resume": lire_source(conn, SOURCE_QUALITE_RESUME),
                "prestations": lire_source(conn, SOURCE_PRESTATIONS),
                "equipements": lire_source(conn, SOURCE_EQUIPEMENTS),
                "equipements_contrats": lire_source(conn, SOURCE_EQUIPEMENTS_CONTRATS),
                "alertes": lire_source(conn, SOURCE_ALERTES),
            }
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Erreur PostgreSQL : {exc}") from exc

    return donnees


# =====================================================
# NORMALISATION DES DONNÉES
# =====================================================


COLONNES_REFERENCES = {
    "esi_reference",
    "contract_reference",
    "contract_reference_3f",
    "contract_reference_prestataire",
    "equipment_reference",
    "objet_reference",
    "service_code_id_intent",
    "service_code_reference_3f",
    "service_code_reference_prestataire",
    "third_party_id",
}

COLONNES_TEXTE = {
    "esi_label",
    "societe",
    "agence",
    "groupe",
    "secteur",
    "contract_label",
    "contract_description",
    "contract_status",
    "contract_topic",
    "third_party_label",
    "equipment_label",
    "equipment_type",
    "couverture_status",
    "objet_type",
    "objet_label",
    "anomalie_type",
    "gravite",
    "description",
    "alerte_type",
    "priorite",
    "service_code_label",
    "service_code_description",
    "service_code_work_type",
}

COLONNES_DATES = {
    "contract_start_date",
    "contract_end_date",
    "contract_creation_date",
    "contract_deactivation_date",
    "contract_last_update_date",
    "creation_date",
    "date_maj",
}

COLONNES_NUMERIQUES = {
    "nb_logements",
    "nb_equipements",
    "nb_contrats_total",
    "nb_contrats_actifs",
    "nb_contrats_inactifs",
    "nb_contrats_actifs_valides",
    "nb_prestataires_actifs",
    "nb_contrats_actifs_date_depassee",
    "nb_equipements_avec_contrat",
    "nb_equipements_avec_contrat_actif_intent",
    "nb_equipements_couverts_valides",
    "nb_equipements_avec_contrat_actif_expire",
    "nb_equipements_avec_seulement_contrat_non_actif",
    "nb_equipements_sans_contrat",
    "esi_couvert",
    "esi_couvert_valide",
    "esi_multi_couvert",
    "esi_multi_meme_metier",
    "esi_multi_meme_metier_valide",
    "esi_sans_contrat",
    "esi_sans_contrat_valide",
    "esi_sans_aucun_contrat",
    "esi_sans_equipement",
    "esi_avec_equipement",
    "esi_avec_equipement_sans_aucun_contrat",
    "esi_avec_equipement_et_contrat",
    "esi_avec_equipement_couvert_valide",
    "esi_avec_equipement_sans_contrat_equipement",
    "esi_avec_equipement_sans_couverture_valide",
    "taux_equipements_couverts_valides",
    "nb_contrats_rattaches",
    "nb_contrats_actifs_intent",
    "nb_contrats_couvrants_valides",
    "nb_contrats_actifs_expires",
    "equipment_has_contract_link",
    "equipment_has_active_contract_intent",
    "equipment_covered_valid",
    "equipment_has_active_expired_contract",
    "equipment_has_only_non_active_contracts",
    "equipment_without_contract",
    "nombre_occurrences",
    "nombre_objets_distincts",
    "nombre_alertes",
    "nombre_objets",
}


def normaliser_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    for colonne in out.columns:
        if colonne in COLONNES_REFERENCES:
            out[colonne] = normaliser_reference(out[colonne])
        elif colonne in COLONNES_TEXTE:
            out[colonne] = nettoyer_texte(out[colonne])
        elif colonne in COLONNES_DATES:
            out[colonne] = pd.to_datetime(out[colonne], errors="coerce")
        elif colonne in COLONNES_NUMERIQUES:
            out[colonne] = pd.to_numeric(out[colonne], errors="coerce").fillna(0)
    return out


def normaliser_contrats(df: pd.DataFrame) -> pd.DataFrame:
    out = normaliser_df(df)
    if out.empty:
        return out
    if "contract_status" not in out.columns:
        out["contract_status"] = "Non renseigné"
    out["contract_status_clean"] = (
        out["contract_status"].fillna("").astype(str).str.strip().str.lower()
    )
    for colonne in [
        "contract_start_date",
        "contract_end_date",
        "contract_creation_date",
        "contract_deactivation_date",
        "contract_last_update_date",
    ]:
        if colonne not in out.columns:
            out[colonne] = pd.NaT
        out[colonne] = pd.to_datetime(out[colonne], errors="coerce")
    return out


def construire_master_contrats(
    df_prestations: pd.DataFrame,
    df_contrats: pd.DataFrame,
) -> pd.DataFrame:
    if not df_prestations.empty and "contract_reference_3f" in df_prestations.columns:
        colonnes = [
            "contract_reference_3f",
            "contract_reference_prestataire",
            "contract_id_intent",
            "contract_label",
            "contract_description",
            "contract_topic",
            "contract_status",
            "third_party_id",
            "third_party_label",
            "third_party_reference",
            "contract_start_date",
            "contract_end_date",
            "contract_creation_date",
            "contract_deactivation_date",
            "contract_last_update_date",
            "contract_found",
            "contract_active_intent",
            "contract_active_end_date_expired",
        ]
        colonnes = [c for c in colonnes if c in df_prestations.columns]
        master = df_prestations[colonnes].copy()
        master = master.rename(columns={"contract_reference_3f": "contract_reference"})
        master = master[master["contract_reference"].notna()].copy()
        master = master.sort_values(
            [c for c in ["contract_reference", "contract_last_update_date"] if c in master.columns],
            ascending=[True, False][: len([c for c in ["contract_reference", "contract_last_update_date"] if c in master.columns])],
            na_position="last",
        )
        master = master.drop_duplicates("contract_reference")
        return normaliser_contrats(master)

    master = df_contrats.copy()
    if not master.empty and "contract_reference" in master.columns:
        master = master.sort_values("contract_reference").drop_duplicates("contract_reference")
    return normaliser_contrats(master)


def enrichir_rattachements_dates(
    df_contrats: pd.DataFrame,
    df_master: pd.DataFrame,
) -> pd.DataFrame:
    if df_contrats.empty or df_master.empty or "contract_reference" not in df_contrats.columns:
        return df_contrats.copy()

    colonnes_master = [
        c
        for c in [
            "contract_reference",
            "contract_reference_prestataire",
            "contract_description",
            "contract_creation_date",
            "contract_deactivation_date",
            "contract_last_update_date",
            "third_party_reference",
        ]
        if c in df_master.columns
    ]
    supplement = df_master[colonnes_master].drop_duplicates("contract_reference")
    out = df_contrats.merge(
        supplement,
        on="contract_reference",
        how="left",
        suffixes=("", "_master"),
    )
    for colonne in colonnes_master:
        if colonne == "contract_reference":
            continue
        colonne_master = f"{colonne}_master"
        if colonne_master in out.columns:
            if colonne in out.columns:
                out[colonne] = out[colonne].combine_first(out[colonne_master])
                out = out.drop(columns=[colonne_master])
            else:
                out = out.rename(columns={colonne_master: colonne})
    return normaliser_contrats(out)


def dedupliquer_esi(df_esi: pd.DataFrame) -> pd.DataFrame:
    if df_esi.empty or "esi_reference" not in df_esi.columns:
        return df_esi.drop_duplicates().copy()
    work = df_esi[df_esi["esi_reference"].notna()].copy()
    if work.empty:
        return work
    agregations: dict[str, str] = {}
    for colonne in work.columns:
        if colonne == "esi_reference":
            continue
        agregations[colonne] = "max" if colonne in COLONNES_NUMERIQUES else "first"
    return work.groupby("esi_reference", as_index=False).agg(agregations)


def ajouter_niveau_couverture(df_esi: pd.DataFrame) -> pd.DataFrame:
    out = dedupliquer_esi(df_esi)
    if out.empty:
        return out
    nb_equipements = serie_numerique(out, "nb_equipements")
    nb_couverts = serie_numerique(out, "nb_equipements_couverts_valides")
    out["niveau_couverture_equipements"] = "ESI sans équipement"
    out.loc[(nb_equipements > 0) & (nb_couverts == 0), "niveau_couverture_equipements"] = (
        "Aucun équipement couvert"
    )
    out.loc[
        (nb_equipements > 0) & (nb_couverts > 0) & (nb_couverts < nb_equipements),
        "niveau_couverture_equipements",
    ] = "Équipements partiellement couverts"
    out.loc[
        (nb_equipements > 0) & (nb_couverts >= nb_equipements),
        "niveau_couverture_equipements",
    ] = "Tous les équipements couverts"
    return out


# =====================================================
# FILTRES ET PÉRIMÈTRE
# =====================================================


def afficher_filtre_statut_contrat() -> str | None:
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


def filtrer_contrats_par_statut(df: pd.DataFrame, statut: str | None) -> pd.DataFrame:
    out = normaliser_contrats(df)
    if out.empty or statut is None:
        return out
    if statut == "active":
        return out[out["contract_status_clean"] == "active"].copy()
    return out[out["contract_status_clean"] != "active"].copy()


def contrats_actifs_valides(df: pd.DataFrame) -> pd.DataFrame:
    out = normaliser_contrats(df)
    if out.empty:
        return out
    aujourd_hui = aujourd_hui_france()
    return out[
        (out["contract_status_clean"] == "active")
        & (
            out["contract_end_date"].isna()
            | (out["contract_end_date"] >= aujourd_hui)
        )
    ].copy()


def filtrer_source_par_perimetre(
    df: pd.DataFrame,
    refs_esi: set[str],
    refs_contrats: set[str],
    filtre_actif: bool,
    colonne_esi: str = "esi_reference",
    colonne_contrat: str | None = None,
) -> pd.DataFrame:
    if df.empty or not filtre_actif:
        return df.copy()
    masque = pd.Series(True, index=df.index)
    a_filtre = False
    if colonne_esi in df.columns and refs_esi:
        masque &= df[colonne_esi].astype(str).isin(refs_esi)
        a_filtre = True
    if colonne_contrat and colonne_contrat in df.columns and refs_contrats:
        masque &= df[colonne_contrat].astype(str).isin(refs_contrats)
        a_filtre = True
    return df[masque].copy() if a_filtre else df.copy()


def effacer_recherche_contrat() -> None:
    st.session_state["global_search_contract"] = ""


# =====================================================
# TABLEAUX PRÉPARÉS
# =====================================================


MAPPING_CONTRATS = {
    "contract_reference": "Référence contrat 3F",
    "contract_reference_prestataire": "Référence contrat prestataire",
    "contract_id_intent": "Identifiant contrat Intent",
    "contract_label": "Libellé contrat",
    "contract_description": "Description contrat",
    "third_party_label": "Prestataire",
    "third_party_reference": "Référence prestataire",
    "third_party_id": "Identifiant prestataire",
    "contract_start_date": "Date de début",
    "contract_end_date": "Date de fin",
    "contract_creation_date": "Date de création Intent",
    "contract_deactivation_date": "Date de désactivation Intent",
    "contract_last_update_date": "Dernière modification Intent",
    "contract_topic": "Métier",
    "contract_status": "Statut",
    "contract_active_end_date_expired": "Actif avec date de fin dépassée",
    "societe": "Société",
    "agence": "Agence",
    "groupe": "Groupe",
    "secteur": "Secteur",
    "esi_reference": "Référence ESI",
    "esi_label": "Libellé ESI",
}

MAPPING_PRESTATIONS = {
    "contract_reference_3f": "Référence contrat 3F",
    "contract_reference_prestataire": "Référence contrat prestataire",
    "contract_id_intent": "Identifiant contrat Intent",
    "contract_label": "Libellé contrat",
    "contract_description": "Description contrat",
    "contract_topic": "Métier",
    "contract_status": "Statut",
    "third_party_label": "Prestataire",
    "third_party_reference": "Référence prestataire",
    "third_party_id": "Identifiant prestataire",
    "contract_start_date": "Date de début",
    "contract_end_date": "Date de fin",
    "contract_creation_date": "Date de création Intent",
    "contract_deactivation_date": "Date de désactivation Intent",
    "contract_last_update_date": "Dernière modification Intent",
    "service_code_id_intent": "Identifiant prestation Intent",
    "service_code_reference_3f": "Référence prestation 3F",
    "service_code_reference_prestataire": "Référence prestation prestataire",
    "service_code_label": "Libellé prestation",
    "service_code_description": "Description prestation",
    "service_code_work_type": "Type de travail",
    "service_code_critical_level": "Niveau de criticité",
    "service_code_fixed_rate": "Forfait fixe",
    "sla_periodicity_value": "Périodicité SLA - valeur",
    "sla_periodicity_unit": "Périodicité SLA - unité",
    "sla_estimated_intervention_duration_value": "Durée estimée - valeur",
    "sla_estimated_intervention_duration_unit": "Durée estimée - unité",
    "sla_max_time_to_intervention_value": "Délai maximal intervention - valeur",
    "sla_max_time_to_intervention_unit": "Délai maximal intervention - unité",
    "sla_max_time_to_recovery_value": "Délai maximal rétablissement - valeur",
    "sla_max_time_to_recovery_unit": "Délai maximal rétablissement - unité",
    "has_service_code": "Code de prestation présent",
}


def formatter_dates_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for colonne in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[colonne]) or colonne.startswith("Date ") or "modification" in colonne.lower():
            serie = pd.to_datetime(out[colonne], errors="coerce")
            if serie.notna().any():
                out[colonne] = serie.dt.strftime("%d/%m/%Y").fillna("")
    return out


def preparer_table_contrats(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    colonnes = [c for c in MAPPING_CONTRATS if c in df.columns]
    out = df[colonnes].copy().rename(columns=MAPPING_CONTRATS)
    return formatter_dates_table(out)


def preparer_table_prestations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    colonnes = [c for c in MAPPING_PRESTATIONS if c in df.columns]
    out = df[colonnes].copy().rename(columns=MAPPING_PRESTATIONS)
    return formatter_dates_table(out)


def preparer_table_esi(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    mapping = {
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI",
        "nb_logements": "Logements",
        "nb_equipements": "Équipements",
        "nb_equipements_couverts_valides": "Équipements couverts",
        "nb_equipements_sans_contrat": "Équipements sans contrat",
        "nb_contrats_total": "Contrats totaux",
        "nb_contrats_actifs": "Contrats actifs Intent",
        "nb_contrats_actifs_valides": "Contrats actifs valides",
        "nb_contrats_inactifs": "Contrats inactifs",
        "taux_equipements_couverts_valides": "Taux de couverture équipements (%)",
        "niveau_couverture_equipements": "Niveau de couverture",
        "esi_sans_aucun_contrat": "Sans aucun contrat",
        "esi_multi_meme_metier_valide": "Plusieurs contrats valides même métier",
    }
    colonnes = [c for c in mapping if c in df.columns]
    out = df[colonnes].copy().rename(columns=mapping)
    for colonne in out.columns:
        if colonne.startswith("Taux"):
            out[colonne] = pd.to_numeric(out[colonne], errors="coerce").round(2)
    return out


def preparer_table_equipements(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    mapping = {
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI",
        "equipment_reference": "Référence équipement",
        "equipment_label": "Libellé équipement",
        "equipment_type": "Type équipement",
        "nb_contrats_rattaches": "Contrats rattachés",
        "nb_contrats_actifs_intent": "Contrats actifs Intent",
        "nb_contrats_couvrants_valides": "Contrats couvrants valides",
        "nb_contrats_actifs_expires": "Contrats actifs expirés",
        "nb_contrats_inactifs": "Contrats inactifs",
        "couverture_status": "Statut de couverture",
    }
    colonnes = [c for c in mapping if c in df.columns]
    return df[colonnes].copy().rename(columns=mapping)


def preparer_table_qualite(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    mapping = {
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
        "service_code_id": "Identifiant prestation",
        "service_code_3f": "Code prestation 3F",
        "service_code_prestataire": "Code prestation prestataire",
        "source_table": "Source",
        "regle_controle": "Règle de contrôle",
        "date_maj": "Date de détection",
    }
    colonnes = [c for c in mapping if c in df.columns]
    return formatter_dates_table(df[colonnes].copy().rename(columns=mapping))


def preparer_table_alertes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    mapping = {
        "alerte_type": "Type alerte",
        "objet_type": "Type objet",
        "objet_reference": "Référence objet",
        "objet_label": "Libellé objet",
        "priorite": "Priorité",
        "description": "Description",
        "societe": "Société",
        "agence": "Agence",
        "groupe": "Groupe",
        "secteur": "Secteur",
        "esi_reference": "Référence ESI",
        "esi_label": "Libellé ESI",
        "equipment_reference": "Référence équipement",
        "equipment_label": "Libellé équipement",
        "nb_equipements": "Équipements",
        "nb_equipements_couverts_valides": "Équipements couverts",
        "nb_equipements_non_couverts": "Équipements non couverts",
        "taux_couverture_equipements": "Taux couverture équipements (%)",
        "nb_contrats_actifs": "Contrats actifs",
        "date_maj": "Date de détection",
    }
    colonnes = [c for c in mapping if c in df.columns]
    return formatter_dates_table(df[colonnes].copy().rename(columns=mapping))


# =====================================================
# CALCULS COUVERTURE
# =====================================================


def calcul_synthese_couverture(df_esi: pd.DataFrame) -> dict[str, float]:
    esi = ajouter_niveau_couverture(df_esi)
    total = len(esi)
    equipes = int((serie_numerique(esi, "nb_equipements") > 0).sum())
    sans_equipement = total - equipes
    au_moins_un_couvert = int(
        (serie_numerique(esi, "nb_equipements_couverts_valides") > 0).sum()
    )
    complets = int(
        (esi.get("niveau_couverture_equipements", "") == "Tous les équipements couverts").sum()
    )
    partiels = int(
        (esi.get("niveau_couverture_equipements", "") == "Équipements partiellement couverts").sum()
    )
    aucun = int(
        (esi.get("niveau_couverture_equipements", "") == "Aucun équipement couvert").sum()
    )
    sans_aucun_contrat = int(serie_numerique(esi, "esi_sans_aucun_contrat").gt(0).sum())
    equipes_sans_aucun_contrat = int(
        serie_numerique(esi, "esi_avec_equipement_sans_aucun_contrat").gt(0).sum()
    )
    multi = int(
        serie_numerique(
            esi,
            "esi_multi_meme_metier_valide"
            if "esi_multi_meme_metier_valide" in esi.columns
            else "esi_multi_meme_metier",
        )
        .gt(0)
        .sum()
    )
    nb_total_contrats = serie_numerique(
        esi,
        "nb_contrats_total"
        if "nb_contrats_total" in esi.columns
        else "nb_contrats_actifs",
    )
    moyenne_tous = float(nb_total_contrats.mean()) if total else 0.0
    moyenne_avec = float(nb_total_contrats[nb_total_contrats > 0].mean()) if (nb_total_contrats > 0).any() else 0.0
    return {
        "total": total,
        "equipes": equipes,
        "sans_equipement": sans_equipement,
        "au_moins_un_couvert": au_moins_un_couvert,
        "complets": complets,
        "partiels": partiels,
        "aucun": aucun,
        "sans_aucun_contrat": sans_aucun_contrat,
        "equipes_sans_aucun_contrat": equipes_sans_aucun_contrat,
        "multi": multi,
        "moyenne_tous": moyenne_tous,
        "moyenne_avec": moyenne_avec,
        "taux_equipes": taux(equipes, total),
        "taux_au_moins_un": taux(au_moins_un_couvert, equipes),
        "taux_complets": taux(complets, equipes),
        "taux_partiels": taux(partiels, equipes),
        "taux_aucun": taux(aucun, equipes),
        "taux_sans_equipement": taux(sans_equipement, total),
        "taux_sans_aucun_contrat": taux(sans_aucun_contrat, total),
        "taux_multi": taux(multi, total),
    }


INDICATEURS_ORGANISATION: dict[
    str,
    tuple[
        str,
        Callable[[pd.DataFrame], pd.Series] | None,
        Callable[[pd.DataFrame], pd.Series] | None,
    ],
] = {
    "ESI avec au moins un équipement": (
        "taux",
        lambda df: serie_numerique(df, "nb_equipements") > 0,
        None,
    ),
    "ESI sans équipement": (
        "taux",
        lambda df: serie_numerique(df, "nb_equipements") == 0,
        None,
    ),
    "ESI avec au moins un équipement couvert": (
        "taux",
        lambda df: serie_numerique(df, "nb_equipements_couverts_valides") > 0,
        lambda df: serie_numerique(df, "nb_equipements") > 0,
    ),
    "ESI dont tous les équipements sont couverts": (
        "taux",
        lambda df: (
            (serie_numerique(df, "nb_equipements") > 0)
            & (
                serie_numerique(df, "nb_equipements_couverts_valides")
                >= serie_numerique(df, "nb_equipements")
            )
        ),
        lambda df: serie_numerique(df, "nb_equipements") > 0,
    ),
    "ESI partiellement couverts": (
        "taux",
        lambda df: (
            (serie_numerique(df, "nb_equipements_couverts_valides") > 0)
            & (
                serie_numerique(df, "nb_equipements_couverts_valides")
                < serie_numerique(df, "nb_equipements")
            )
        ),
        lambda df: serie_numerique(df, "nb_equipements") > 0,
    ),
    "ESI équipés sans aucun équipement couvert": (
        "taux",
        lambda df: (
            (serie_numerique(df, "nb_equipements") > 0)
            & (serie_numerique(df, "nb_equipements_couverts_valides") == 0)
        ),
        lambda df: serie_numerique(df, "nb_equipements") > 0,
    ),
    "ESI sans aucun contrat": (
        "taux",
        lambda df: serie_numerique(df, "esi_sans_aucun_contrat") > 0,
        None,
    ),
    "ESI avec plusieurs contrats sur le même métier": (
        "taux",
        lambda df: serie_numerique(
            df,
            "esi_multi_meme_metier_valide"
            if "esi_multi_meme_metier_valide" in df.columns
            else "esi_multi_meme_metier",
        )
        > 0,
        None,
    ),
    "Nombre moyen de contrats par ESI": ("moyenne", None, None),
}


def construire_comparaison_organisation(
    df_esi: pd.DataFrame,
    maille: str,
    indicateur: str,
) -> pd.DataFrame:
    esi = ajouter_niveau_couverture(df_esi)
    if esi.empty or maille not in esi.columns:
        return pd.DataFrame()
    type_indicateur, condition, condition_base = INDICATEURS_ORGANISATION[indicateur]
    work = esi.copy()
    work[maille] = nettoyer_texte(work[maille])
    lignes: list[dict[str, object]] = []
    for entite, groupe in work.groupby(maille, dropna=False):
        total_esi = groupe["esi_reference"].nunique()
        if type_indicateur == "moyenne":
            colonne = "nb_contrats_total" if "nb_contrats_total" in groupe.columns else "nb_contrats_actifs"
            valeur = float(serie_numerique(groupe, colonne).mean()) if total_esi else 0.0
            lignes.append(
                {
                    "Entité": entite,
                    "Total ESI": total_esi,
                    "Base de calcul": total_esi,
                    "Nombre": None,
                    "Valeur": round(valeur, 2),
                    "Unité": "contrat(s) par ESI",
                }
            )
        else:
            masque_base = (
                condition_base(groupe)
                if condition_base
                else pd.Series(True, index=groupe.index)
            )
            base = groupe[masque_base].copy()
            base_calcul = base["esi_reference"].nunique()
            masque = condition(base) if condition else pd.Series(False, index=base.index)
            nombre = int(masque.sum())
            lignes.append(
                {
                    "Entité": entite,
                    "Total ESI": total_esi,
                    "Base de calcul": base_calcul,
                    "Nombre": nombre,
                    "Valeur": round(taux(nombre, base_calcul), 2),
                    "Unité": "%",
                }
            )
    return pd.DataFrame(lignes).sort_values(["Valeur", "Total ESI"], ascending=[False, False])


def afficher_comparaison_organisation(df: pd.DataFrame, indicateur: str) -> None:
    if df.empty:
        st.info("Aucune donnée disponible pour cette comparaison.")
        return
    graphe = df.sort_values("Valeur", ascending=True).tail(25)
    if go is None:
        st.bar_chart(graphe.set_index("Entité")["Valeur"], width="stretch")
        return
    type_indicateur = INDICATEURS_ORGANISATION[indicateur][0]
    textes = (
        graphe["Valeur"].map(lambda x: f"{x:.1f} %")
        if type_indicateur == "taux"
        else graphe["Valeur"].map(lambda x: f"{x:.2f}")
    )
    custom = graphe[["Nombre", "Base de calcul", "Total ESI"]].astype(object).values
    hover = (
        "<b>%{y}</b><br>Taux : %{x:.1f} %<br>Nombre : %{customdata[0]} / %{customdata[1]}<br>Total ESI : %{customdata[2]}<extra></extra>"
        if type_indicateur == "taux"
        else "<b>%{y}</b><br>Moyenne : %{x:.2f}<br>Total ESI : %{customdata[2]}<extra></extra>"
    )
    fig = go.Figure(
        go.Bar(
            x=graphe["Valeur"],
            y=graphe["Entité"],
            orientation="h",
            text=textes,
            textposition="outside",
            marker=dict(color=C_RED),
            customdata=custom,
            hovertemplate=hover,
            cliponaxis=False,
        )
    )
    layout_plotly(fig, max(390, 31 * len(graphe) + 100))
    fig.update_layout(
        xaxis=dict(
            title="Taux (%)" if type_indicateur == "taux" else "Nombre moyen de contrats",
            gridcolor=C_GRID,
            range=[0, 105] if type_indicateur == "taux" else None,
        ),
        yaxis=dict(title=None, automargin=True),
        margin=dict(l=12, r=65, t=14, b=45),
    )
    st.plotly_chart(fig, use_container_width=True, config=config_graphique_exportable("comparaison_organisationnelle"))


def construire_couverture_metier(
    df_esi: pd.DataFrame,
    df_contrats: pd.DataFrame,
) -> pd.DataFrame:
    if df_esi.empty or df_contrats.empty or "contract_topic" not in df_contrats.columns:
        return pd.DataFrame()
    total_esi = len(liste_refs_valides(df_esi, "esi_reference"))
    actifs = contrats_actifs_valides(df_contrats)
    if actifs.empty:
        return pd.DataFrame()
    actifs["contract_topic"] = nettoyer_texte(actifs["contract_topic"], "Métier non renseigné")
    out = (
        actifs.dropna(subset=["esi_reference"])
        .groupby("contract_topic", as_index=False)
        .agg(
            **{
                "ESI couverts": ("esi_reference", "nunique"),
                "Contrats actifs valides": ("contract_reference", "nunique"),
            }
        )
        .rename(columns={"contract_topic": "Métier"})
    )
    out["Total ESI"] = total_esi
    out["Taux d’ESI couverts (%)"] = (
        out["ESI couverts"].div(total_esi if total_esi else 1).mul(100).round(2)
    )
    return out.sort_values("ESI couverts", ascending=False)


def afficher_couverture_metier(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Aucune couverture contractuelle par métier disponible.")
        return
    graphe = df.head(20).sort_values("Taux d’ESI couverts (%)", ascending=True)
    if go is None:
        st.bar_chart(graphe.set_index("Métier")["Taux d’ESI couverts (%)"], width="stretch")
        return
    fig = go.Figure(
        go.Bar(
            x=graphe["Taux d’ESI couverts (%)"],
            y=graphe["Métier"],
            orientation="h",
            text=graphe["Taux d’ESI couverts (%)"].map(lambda x: f"{x:.1f} %"),
            textposition="outside",
            marker=dict(color=C_RED),
            customdata=graphe[["ESI couverts", "Total ESI", "Contrats actifs valides"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "ESI couverts : %{customdata[0]} / %{customdata[1]}<br>"
                "Taux : %{x:.1f} %<br>"
                "Contrats actifs valides : %{customdata[2]}<extra></extra>"
            ),
            cliponaxis=False,
        )
    )
    layout_plotly(fig, max(420, 31 * len(graphe) + 100))
    fig.update_layout(
        xaxis=dict(title="Part du patrimoine (%)", gridcolor=C_GRID, range=[0, 105]),
        yaxis=dict(title=None, automargin=True),
        margin=dict(l=12, r=65, t=14, b=45),
    )
    st.plotly_chart(fig, use_container_width=True, config=config_graphique_exportable("couverture_par_metier"))


def construire_historique_couverture(
    df_esi: pd.DataFrame,
    df_contrats: pd.DataFrame,
    maille: str,
    entites: list[str],
    nb_mois: int,
) -> pd.DataFrame:
    esi = dedupliquer_esi(df_esi)
    contrats = normaliser_contrats(df_contrats)
    colonnes_dates = {"contract_creation_date", "contract_deactivation_date", "contract_end_date"}
    if esi.empty or contrats.empty or not colonnes_dates.issubset(contrats.columns):
        return pd.DataFrame()
    if contrats["contract_creation_date"].notna().sum() == 0:
        return pd.DataFrame()

    fin = aujourd_hui_france().to_period("M").to_timestamp("M")
    debut = (fin - pd.DateOffset(months=max(nb_mois - 1, 0))).to_period("M").to_timestamp("M")
    mois = pd.date_range(debut, fin, freq="ME")

    if maille == "Patrimoine filtré":
        groupes = {"Patrimoine filtré": set(liste_refs_valides(esi, "esi_reference"))}
    else:
        if maille not in esi.columns:
            return pd.DataFrame()
        work = esi.copy()
        work[maille] = nettoyer_texte(work[maille])
        groupes = {
            entite: set(liste_refs_valides(groupe, "esi_reference"))
            for entite, groupe in work.groupby(maille)
            if not entites or entite in entites
        }

    lignes: list[dict[str, object]] = []
    for entite, refs_esi in groupes.items():
        sous_contrats = contrats[contrats["esi_reference"].astype(str).isin(refs_esi)].copy()
        total_esi = len(refs_esi)
        for fin_mois in mois:
            actifs = sous_contrats[
                sous_contrats["contract_creation_date"].notna()
                & (sous_contrats["contract_creation_date"] <= fin_mois)
                & (
                    sous_contrats["contract_deactivation_date"].isna()
                    | (sous_contrats["contract_deactivation_date"] > fin_mois)
                )
                & (
                    sous_contrats["contract_end_date"].isna()
                    | (sous_contrats["contract_end_date"] >= fin_mois)
                )
            ]
            nb_couverts = actifs["esi_reference"].nunique()
            lignes.append(
                {
                    "Mois": fin_mois,
                    "Entité": entite,
                    "ESI couverts": int(nb_couverts),
                    "Total ESI": total_esi,
                    "Taux de couverture (%)": round(taux(nb_couverts, total_esi), 2),
                }
            )
    return pd.DataFrame(lignes)


def afficher_historique_couverture(df: pd.DataFrame) -> None:
    if df.empty:
        st.info(
            "L’historique nécessite les dates de création et de désactivation des contrats."
        )
        return
    if go is None:
        pivot = df.pivot(index="Mois", columns="Entité", values="Taux de couverture (%)")
        st.line_chart(pivot, width="stretch")
        return
    fig = go.Figure()
    for entite, groupe in df.groupby("Entité"):
        fig.add_trace(
            go.Scatter(
                x=groupe["Mois"],
                y=groupe["Taux de couverture (%)"],
                mode="lines+markers",
                name=str(entite),
                customdata=groupe[["ESI couverts", "Total ESI"]],
                hovertemplate=(
                    f"<b>{safe(entite)}</b><br>%{{x|%b %Y}}<br>"
                    "Taux : %{y:.1f} %<br>"
                    "ESI couverts : %{customdata[0]} / %{customdata[1]}<extra></extra>"
                ),
            )
        )
    layout_plotly(fig, 410, showlegend=True)
    fig.update_layout(
        xaxis=dict(title=None, gridcolor=C_GRID, tickformat="%b %Y"),
        yaxis=dict(title="Taux de couverture (%)", gridcolor=C_GRID, range=[0, 105]),
        margin=dict(l=12, r=22, t=44, b=45),
    )
    st.plotly_chart(fig, use_container_width=True, config=config_graphique_exportable("evolution_couverture"))


def construire_cycle_vie_contrats(
    df_master: pd.DataFrame,
    granularite: str,
    nb_mois: int,
) -> pd.DataFrame:
    contrats = normaliser_contrats(df_master)
    if contrats.empty or contrats["contract_creation_date"].notna().sum() == 0:
        return pd.DataFrame()

    aujourd_hui = aujourd_hui_france()
    if granularite == "Mensuel":
        fin = aujourd_hui.to_period("M").to_timestamp("M")
        debut = (fin - pd.DateOffset(months=max(nb_mois - 1, 0))).to_period("M").to_timestamp("M")
        fins = pd.date_range(debut, fin, freq="ME")
        debuts = pd.DatetimeIndex([date.to_period("M").to_timestamp() for date in fins])
    else:
        annee_min = int(contrats["contract_creation_date"].dropna().dt.year.min())
        annees = range(annee_min, int(aujourd_hui.year) + 1)
        debuts = pd.DatetimeIndex([pd.Timestamp(year=annee, month=1, day=1) for annee in annees])
        fins = pd.DatetimeIndex([pd.Timestamp(year=annee, month=12, day=31) for annee in annees])

    lignes: list[dict[str, object]] = []
    for debut_periode, fin_periode in zip(debuts, fins):
        crees = int(
            contrats["contract_creation_date"].between(debut_periode, fin_periode, inclusive="both").sum()
        )
        desactives = int(
            contrats["contract_deactivation_date"].between(debut_periode, fin_periode, inclusive="both").sum()
        )
        existants = contrats[
            contrats["contract_creation_date"].notna()
            & (contrats["contract_creation_date"] <= fin_periode)
        ]
        actifs = existants[
            existants["contract_deactivation_date"].isna()
            | (existants["contract_deactivation_date"] > fin_periode)
        ]
        inactifs = existants[
            existants["contract_deactivation_date"].notna()
            & (existants["contract_deactivation_date"] <= fin_periode)
        ]
        actifs_expires = actifs[
            actifs["contract_end_date"].notna()
            & (actifs["contract_end_date"] < fin_periode)
        ]
        lignes.append(
            {
                "Période": fin_periode,
                "Contrats créés": crees,
                "Contrats désactivés": desactives,
                "Contrats actifs": actifs["contract_reference"].nunique(),
                "Contrats inactifs": inactifs["contract_reference"].nunique(),
                "Actifs avec date de fin dépassée": actifs_expires["contract_reference"].nunique(),
            }
        )
    return pd.DataFrame(lignes)


def afficher_cycle_flux(df: pd.DataFrame, granularite: str) -> None:
    if df.empty:
        st.info("Aucun historique de création et de désactivation disponible.")
        return
    if go is None:
        st.bar_chart(df.set_index("Période")[["Contrats créés", "Contrats désactivés"]])
        return
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Période"], y=df["Contrats créés"], name="Créés", marker_color=C_RED))
    fig.add_trace(go.Bar(x=df["Période"], y=df["Contrats désactivés"], name="Désactivés", marker_color=C_BLUE_LIGHT))
    layout_plotly(fig, 360, showlegend=True)
    fig.update_layout(
        barmode="group",
        xaxis=dict(title=None, gridcolor=C_GRID, tickformat="%Y" if granularite == "Annuel" else "%b %Y"),
        yaxis=dict(title="Nombre de contrats", gridcolor=C_GRID),
        margin=dict(l=12, r=22, t=44, b=45),
    )
    st.plotly_chart(fig, use_container_width=True, config=config_graphique_exportable("evolution_contrats_crees_desactives"))


def afficher_cycle_stock(df: pd.DataFrame, granularite: str) -> None:
    if df.empty:
        st.info("Aucun historique de statut disponible.")
        return
    if go is None:
        st.line_chart(
            df.set_index("Période")[[
                "Contrats actifs",
                "Contrats inactifs",
                "Actifs avec date de fin dépassée",
            ]]
        )
        return
    fig = go.Figure()
    for colonne, couleur in [
        ("Contrats actifs", C_RED),
        ("Contrats inactifs", C_BLUE_LIGHT),
        ("Actifs avec date de fin dépassée", C_VIOLET),
    ]:
        fig.add_trace(
            go.Scatter(
                x=df["Période"],
                y=df[colonne],
                mode="lines+markers",
                name=colonne,
                line=dict(width=3, color=couleur),
            )
        )
    layout_plotly(fig, 360, showlegend=True)
    fig.update_layout(
        xaxis=dict(title=None, gridcolor=C_GRID, tickformat="%Y" if granularite == "Annuel" else "%b %Y"),
        yaxis=dict(title="Nombre de contrats", gridcolor=C_GRID),
        margin=dict(l=12, r=22, t=44, b=45),
    )
    st.plotly_chart(fig, use_container_width=True, config=config_graphique_exportable("evolution_stock_contrats"))


# =====================================================
# GRAPHIQUES GÉNÉRAUX
# =====================================================


def afficher_donut_statuts(df_master: pd.DataFrame) -> None:
    master = normaliser_contrats(df_master)
    if master.empty:
        st.info("Aucun contrat disponible.")
        return
    actifs = int((master["contract_status_clean"] == "active").sum())
    inactifs = int((master["contract_status_clean"] != "active").sum())
    expires = int(
        (
            (master["contract_status_clean"] == "active")
            & master["contract_end_date"].notna()
            & (master["contract_end_date"] < aujourd_hui_france())
        ).sum()
    )
    if go is None:
        st.dataframe(
            pd.DataFrame(
                {"Statut": ["Actifs", "Inactifs", "Actifs expirés"], "Contrats": [actifs, inactifs, expires]}
            ),
            width="stretch",
            hide_index=True,
        )
        return
    fig = go.Figure(
        go.Pie(
            labels=["Actifs", "Inactifs"],
            values=[actifs, inactifs],
            hole=0.67,
            marker=dict(colors=[C_RED, "#F1DCE3"], line=dict(color="#FFFFFF", width=2)),
            textinfo="label+value",
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>%{value} contrat(s)<extra></extra>",
            sort=False,
        )
    )
    fig.add_annotation(
        text=f"<b>{fmt_nombre(expires)}</b><br><span style='font-size:10px'>actifs expirés</span>",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color=C_VIOLET, size=16),
    )
    layout_plotly(fig, 390)
    fig.update_layout(margin=dict(l=15, r=15, t=12, b=12))
    st.plotly_chart(fig, use_container_width=True, config=config_graphique_exportable("repartition_statut_contrats"))


def construire_repartition_metier(df_master: pd.DataFrame) -> pd.DataFrame:
    master = normaliser_contrats(df_master)
    if master.empty or "contract_topic" not in master.columns:
        return pd.DataFrame()
    master["contract_topic"] = nettoyer_texte(master["contract_topic"], "Métier non renseigné")
    return (
        master.groupby("contract_topic", as_index=False)["contract_reference"]
        .nunique()
        .rename(columns={"contract_topic": "Métier", "contract_reference": "Contrats"})
        .sort_values("Contrats", ascending=False)
    )


def afficher_barres_horizontales(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    color: str = C_RED,
    top_n: int | None = None,
    nom_export: str = "graphique_dashboard",
) -> None:
    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    graphe = df.copy().sort_values(value_col, ascending=False)
    if top_n is not None:
        graphe = graphe.head(top_n)
    graphe = graphe.sort_values(value_col, ascending=True)

    if go is None:
        st.bar_chart(graphe.set_index(label_col)[value_col], width="stretch")
        return

    fig = go.Figure(
        go.Bar(
            x=graphe[value_col],
            y=graphe[label_col],
            orientation="h",
            text=graphe[value_col].map(fmt_nombre),
            textposition="outside",
            marker=dict(color=color),
            hovertemplate="<b>%{y}</b><br>Nombre : %{x}<extra></extra>",
            cliponaxis=False,
        )
    )

    layout_plotly(fig, max(390, 36 * len(graphe) + 100))
    valeur_max = max(float(graphe[value_col].max()), 1.0)
    fig.update_layout(
        xaxis=dict(
            title=None,
            gridcolor=C_GRID,
            range=[0, valeur_max * 1.18],
        ),
        yaxis=dict(title=None, automargin=True),
        margin=dict(l=12, r=60, t=14, b=35),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config=config_graphique_exportable(nom_export),
    )


# =====================================================
# PAGE ET DONNÉES COMMUNES
# =====================================================


hero(
    "Pilotage du patrimoine",
    "Contrats, couverture réelle des équipements, codes de prestation, qualité des données et évolution dans le temps.",
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
        donnees = charger_donnees()
except Exception as exc:
    st.error("Erreur pendant le chargement des données.")
    st.code(str(exc))
    st.stop()

for cle, frame in donnees.items():
    donnees[cle] = normaliser_df(frame)

df_global = donnees["global"]
df_esi = ajouter_niveau_couverture(donnees["esi"])
df_contrats = normaliser_contrats(donnees["contrats"])
df_creations = normaliser_df(donnees["creations"])
df_qualite = normaliser_df(donnees["qualite"])
df_qualite_resume = normaliser_df(donnees["qualite_resume"])
df_prestations = normaliser_df(donnees["prestations"])
df_equipements = normaliser_df(donnees["equipements"])
df_equipements_contrats = normaliser_df(donnees["equipements_contrats"])
df_alertes = normaliser_df(donnees["alertes"])
df_master = construire_master_contrats(df_prestations, df_contrats)
df_contrats = enrichir_rattachements_dates(df_contrats, df_master)

# Filtres patrimoine partagés avec le reste de l'application.
df_esi_filtre, df_contrats_filtre, filtres_selectionnes = render_filtres_patrimoine(
    df_esi=df_esi,
    df_contrats=df_contrats,
)
df_esi_filtre = ajouter_niveau_couverture(df_esi_filtre)
df_contrats_filtre = normaliser_contrats(df_contrats_filtre)

with st.container(key="contract_status_filter"):
    st.markdown('<div class="vg-mini-title">Statut des contrats</div>', unsafe_allow_html=True)
    statut_selectionne = afficher_filtre_statut_contrat()
    st.caption(
        "Ce filtre agit sur la vue globale et la liste des contrats. "
        "La couverture des équipements utilise toujours les contrats actifs dont la date de fin n’est pas dépassée."
    )

recherche_globale = str(st.session_state.get("global_search_contract", "") or "").strip()

# Détection du périmètre après les filtres latéraux.
perimetre_actif = (
    refs_ont_change(df_esi, df_esi_filtre, "esi_reference")
    or refs_ont_change(df_contrats, df_contrats_filtre, "contract_reference")
)
refs_esi_filtre = set(liste_refs_valides(df_esi_filtre, "esi_reference"))
refs_contrats_filtre = set(liste_refs_valides(df_contrats_filtre, "contract_reference"))

# Les nouvelles tables suivent le périmètre organisationnel et contractuel.
df_prestations_filtre = filtrer_source_par_perimetre(
    df_prestations,
    refs_esi_filtre,
    refs_contrats_filtre,
    perimetre_actif,
    colonne_esi="esi_reference",
    colonne_contrat="contract_reference_3f",
)
df_master_filtre = filtrer_source_par_perimetre(
    df_master,
    refs_esi_filtre,
    refs_contrats_filtre,
    perimetre_actif,
    colonne_esi="esi_reference",
    colonne_contrat="contract_reference",
)

# En l’absence de filtre, le master conserve aussi les contrats non rattachés.
if not perimetre_actif:
    df_master_filtre = df_master.copy()
    df_prestations_filtre = df_prestations.copy()

# Recherche globale contrat / code de prestation.
(
    df_contrats_recherche,
    df_prestations_recherche,
    df_master_recherche,
    refs_recherche,
) = appliquer_recherche_contrats(
    recherche_globale,
    df_contrats_filtre,
    df_prestations_filtre,
    df_master_filtre,
)

if recherche_globale:
    refs_esi_recherche = set(liste_refs_valides(df_contrats_recherche, "esi_reference"))
    df_esi_contexte = df_esi_filtre[
        df_esi_filtre["esi_reference"].astype(str).isin(refs_esi_recherche)
    ].copy()
else:
    df_esi_contexte = df_esi_filtre.copy()

# Le statut choisi ne s'applique qu'aux contrats affichés dans la vue globale.
df_contrats_affiches = filtrer_contrats_par_statut(df_contrats_recherche, statut_selectionne)
df_master_affiche = filtrer_contrats_par_statut(df_master_recherche, statut_selectionne)
if statut_selectionne is not None and not df_prestations_recherche.empty:
    statut_prest = nettoyer_texte(df_prestations_recherche["contract_status"]).str.lower()
    if statut_selectionne == "active":
        df_prestations_affichees = df_prestations_recherche[statut_prest == "active"].copy()
    else:
        df_prestations_affichees = df_prestations_recherche[statut_prest != "active"].copy()
else:
    df_prestations_affichees = df_prestations_recherche.copy()

# Les tables équipement et les alertes suivent les ESI actuellement visibles.
filtre_esi_actif = perimetre_actif or bool(recherche_globale)
refs_esi_contexte = set(liste_refs_valides(df_esi_contexte, "esi_reference"))
df_equipements_filtre = filtrer_source_par_perimetre(
    df_equipements,
    refs_esi_contexte,
    set(),
    filtre_esi_actif,
    colonne_esi="esi_reference",
)
df_equipements_contrats_filtre = filtrer_source_par_perimetre(
    df_equipements_contrats,
    refs_esi_contexte,
    refs_recherche,
    filtre_esi_actif,
    colonne_esi="esi_reference",
    colonne_contrat="contract_reference",
)
df_alertes_filtre = filtrer_source_par_perimetre(
    df_alertes,
    refs_esi_contexte,
    set(),
    filtre_esi_actif,
    colonne_esi="esi_reference",
)

# Les anomalies rattachées à un ESI suivent le périmètre ; les anomalies globales
# restent visibles tant qu'aucun filtre organisationnel n'est actif.
if not df_qualite.empty and filtre_esi_actif and "esi_reference" in df_qualite.columns:
    df_qualite_filtre = df_qualite[
        df_qualite["esi_reference"].astype(str).isin(refs_esi_contexte)
    ].copy()
else:
    df_qualite_filtre = df_qualite.copy()


# =====================================================
# VUE 1 — VUE GLOBALE
# =====================================================


if vue_active == "Vue globale":
    section(
        "Vue globale",
        "Les volumes du patrimoine, la situation des contrats et la liste complète avec les rattachements et les codes de prestation.",
    )

    contrats_total = len(liste_refs_valides(df_master_affiche, "contract_reference"))
    esi_total = len(liste_refs_valides(df_esi_contexte, "esi_reference"))
    logements_total = int(serie_numerique(df_esi_contexte, "nb_logements").sum())
    equipements_total = int(serie_numerique(df_esi_contexte, "nb_equipements").sum())
    prestataires_total = (
        df_master_affiche["third_party_id"].dropna().nunique()
        if "third_party_id" in df_master_affiche.columns
        else 0
    )
    contrats_rattaches = len(liste_refs_valides(df_contrats_affiches, "contract_reference"))
    contrats_non_rattaches = max(contrats_total - contrats_rattaches, 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card(
            "Contrats",
            contrats_total,
            f"{fmt_nombre(contrats_rattaches)} rattachés",
            f"{fmt_nombre(contrats_non_rattaches)} contrat(s) sans programme dans ce périmètre.",
            C_RED,
        )
    with c2:
        kpi_card(
            "Programmes / ESI",
            esi_total,
            f"{fmt_nombre(int(serie_numerique(df_esi_contexte, 'esi_couvert_valide').gt(0).sum()))} couverts",
            "Programmes correspondant aux filtres actuels.",
            C_BLUE,
        )
    with c3:
        kpi_card(
            "Logements",
            logements_total,
            "Rattachés aux ESI",
            "Somme des logements exploitables dans le périmètre.",
            C_PINK,
        )
    with c4:
        kpi_card(
            "Équipements",
            equipements_total,
            f"{fmt_nombre(int(serie_numerique(df_esi_contexte, 'nb_equipements_couverts_valides').sum()))} couverts",
            "Équipements rattachés aux programmes du périmètre.",
            C_VIOLET,
        )
    with c5:
        kpi_card(
            "Prestataires",
            prestataires_total,
            "Prestataires distincts",
            "Calculés à partir des contrats affichés.",
            C_TEAL,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    graphique_statut, graphique_metier = st.columns([0.85, 1.25])
    with graphique_statut:
        st.markdown('<div class="vg-mini-title">Statut des contrats</div>', unsafe_allow_html=True)
        afficher_donut_statuts(df_master_affiche)
    with graphique_metier:
        st.markdown(
            '<div class="vg-mini-title">Répartition des contrats par métier</div>',
            unsafe_allow_html=True,
        )
        afficher_barres_horizontales(
            construire_repartition_metier(df_master_affiche),
            "Métier",
            "Contrats",
            C_RED,
            top_n=None,
            nom_export="repartition_contrats_par_metier",
        )

    with st.expander("Consulter la liste des contrats", expanded=False):
        recherche_col, effacer_col = st.columns([5, 1], vertical_alignment="bottom")
        with recherche_col:
            recherche_widget = st.text_input(
                "Rechercher un contrat",
                placeholder="Référence contrat, prestation, libellé, prestataire, métier...",
                key="global_search_contract",
                help=(
                    "La recherche agit sur les indicateurs, les graphiques, les ESI et les trois niveaux du tableau."
                ),
            )
        with effacer_col:
            st.button(
                "Effacer",
                key="effacer_recherche_contrat",
                width="stretch",
                on_click=effacer_recherche_contrat,
                disabled=not bool(recherche_widget),
            )

        if recherche_widget:
            st.markdown(
                (
                    '<div class="vg-search-active">'
                    '<span class="vg-search-active-dot"></span>'
                    '<span>Recherche appliquée à tout le tableau de bord</span>'
                    "</div>"
                ),
                unsafe_allow_html=True,
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
                key="global_contract_table_mode",
                help=(
                    "Contrats uniques : une ligne par contrat. "
                    "Rattachements : une ligne par contrat et ESI. "
                    "Codes de prestation : une ligne par contrat et code de prestation."
                ),
            )

        if mode_tableau == "Contrats uniques":
            source_tableau = df_master_affiche.copy()
            table_complete = preparer_table_contrats(source_tableau)
            defaults = [
                "Référence contrat 3F",
                "Référence contrat prestataire",
                "Libellé contrat",
                "Prestataire",
                "Date de début",
                "Date de fin",
                "Métier",
                "Statut",
            ]
            nom_export = "contrats_uniques.csv"
            cle_mode = "contrats_uniques"
            nombre_contrats_table = len(liste_refs_valides(source_tableau, "contract_reference"))
        elif mode_tableau == "Contrats et rattachements":
            source_tableau = df_contrats_affiches.drop_duplicates(
                [c for c in ["contract_reference", "esi_reference"] if c in df_contrats_affiches.columns]
            )
            table_complete = preparer_table_contrats(source_tableau)
            defaults = [
                "Référence contrat 3F",
                "Libellé contrat",
                "Prestataire",
                "Métier",
                "Statut",
                "Société",
                "Agence",
                "Groupe",
                "Secteur",
                "Référence ESI",
                "Libellé ESI",
            ]
            nom_export = "contrats_rattachements.csv"
            cle_mode = "contrats_rattachements"
            nombre_contrats_table = len(liste_refs_valides(source_tableau, "contract_reference"))
        else:
            source_tableau = df_prestations_affichees.copy()
            table_complete = preparer_table_prestations(source_tableau)
            defaults = [
                "Référence contrat 3F",
                "Référence contrat prestataire",
                "Libellé contrat",
                "Prestataire",
                "Métier",
                "Statut",
                "Référence prestation 3F",
                "Référence prestation prestataire",
                "Libellé prestation",
                "Type de travail",
            ]
            nom_export = "contrats_codes_prestation.csv"
            cle_mode = "contrats_prestations"
            nombre_contrats_table = len(liste_refs_valides(source_tableau, "contract_reference_3f"))

        with colonnes_col:
            st.markdown('<div class="vg-mini-title">Colonnes affichées</div>', unsafe_allow_html=True)
            colonnes_affichees = selectionner_colonnes(
                table_complete.columns.tolist(),
                defaults,
                cle_mode,
            )
            st.caption(f"{fmt_nombre(len(colonnes_affichees))} colonne(s) sélectionnée(s).")

        table_summary(
            nombre_contrats_table,
            "contrat(s) trouvé(s)",
            len(table_complete),
            "ligne(s) trouvée(s)",
            mode_tableau,
        )

        if not colonnes_affichees:
            st.warning("Sélectionne au moins une colonne à afficher.")
        else:
            afficher_table_paginated(
                table_complete[colonnes_affichees].copy(),
                key=cle_mode,
                filename=nom_export,
                hauteur=470,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "Évolution des contrats dans Intent",
        "Créations, désactivations et stock de contrats actifs ou inactifs selon les dates enregistrées dans Intent.",
    )

    cycle_col1, cycle_col2 = st.columns([1, 1])
    with cycle_col1:
        granularite_cycle = st.radio(
            "Granularité",
            ["Mensuel", "Annuel"],
            horizontal=True,
            key="cycle_granularite",
        )
    with cycle_col2:
        nb_mois_cycle = st.radio(
            "Période mensuelle",
            [12, 24, 36],
            horizontal=True,
            key="cycle_nb_mois",
            disabled=granularite_cycle == "Annuel",
            format_func=lambda valeur: f"{valeur} mois",
        )

    historique_cycle = construire_cycle_vie_contrats(
        df_master_recherche if recherche_globale else df_master_filtre,
        granularite_cycle,
        int(nb_mois_cycle),
    )
    flux_col, stock_col = st.columns(2)
    with flux_col:
        st.markdown('<div class="vg-mini-title">Flux de contrats</div>', unsafe_allow_html=True)
        afficher_cycle_flux(historique_cycle, granularite_cycle)
    with stock_col:
        st.markdown('<div class="vg-mini-title">Stock de contrats</div>', unsafe_allow_html=True)
        afficher_cycle_stock(historique_cycle, granularite_cycle)
    if not historique_cycle.empty:
        dataframe_download(
            "Télécharger l’évolution des contrats",
            formatter_dates_table(historique_cycle),
            "evolution_contrats_intent.csv",
        )


# =====================================================
# VUE 2 — COUVERTURE
# =====================================================


elif vue_active == "Couverture":
    section(
        "Couverture du patrimoine",
        "La couverture réelle repose sur le lien ESI → équipement → contrat, sans déduire artificiellement une correspondance entre métier et type d’équipement.",
    )

    synthese = calcul_synthese_couverture(df_esi_contexte)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        kpi_card(
            "ESI avec équipement",
            synthese["equipes"],
            fmt_pourcentage(synthese["taux_equipes"], 2),
            f"Sur {fmt_nombre(synthese['total'])} ESI au total.",
            C_BLUE,
        )
    with k2:
        kpi_card(
            "Au moins un équipement couvert",
            synthese["au_moins_un_couvert"],
            fmt_pourcentage(synthese["taux_au_moins_un"], 2),
            f"Parmi les {fmt_nombre(synthese['equipes'])} ESI équipés.",
            C_RED,
        )
    with k3:
        kpi_card(
            "Tous les équipements couverts",
            synthese["complets"],
            fmt_pourcentage(synthese["taux_complets"], 2),
            "Tous les équipements de l’ESI ont au moins un contrat actif valide.",
            C_TEAL,
        )
    with k4:
        kpi_card(
            "Couverture partielle",
            synthese["partiels"],
            fmt_pourcentage(synthese["taux_partiels"], 2),
            "Une partie seulement des équipements est couverte.",
            C_YELLOW,
        )
    with k5:
        kpi_card(
            "Aucun équipement couvert",
            synthese["aucun"],
            fmt_pourcentage(synthese["taux_aucun"], 2),
            "ESI équipé sans couverture contractuelle valide sur ses équipements.",
            C_VIOLET,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        alert_card(
            "ESI sans équipement",
            synthese["sans_equipement"],
            fmt_pourcentage(synthese["taux_sans_equipement"], 2),
            C_BLUE_LIGHT,
        )
    with s2:
        alert_card(
            "ESI sans aucun contrat",
            synthese["sans_aucun_contrat"],
            fmt_pourcentage(synthese["taux_sans_aucun_contrat"], 2),
            C_RED,
        )
    with s3:
        alert_card(
            "Plusieurs contrats même métier",
            synthese["multi"],
            fmt_pourcentage(synthese["taux_multi"], 2),
            C_VIOLET,
        )
    with s4:
        alert_card(
            "Contrats moyens par ESI",
            synthese["moyenne_tous"],
            f"{synthese['moyenne_avec']:.2f} parmi les ESI avec contrat",
            C_TEAL,
            decimales=2,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "Comparaison par maille organisationnelle",
        "Choisis la maille et l’indicateur à comparer. Le graphique affiche le taux et le nombre d’ESI concernés.",
    )
    org_col1, org_col2 = st.columns([1, 2])
    with org_col1:
        maille_label = st.selectbox(
            "Maille de comparaison",
            ["Société", "Agence", "Groupe", "Secteur"],
            key="coverage_maille",
        )
    with org_col2:
        indicateur_org = st.selectbox(
            "Indicateur comparé",
            list(INDICATEURS_ORGANISATION.keys()),
            key="coverage_indicateur_org",
        )
    maille_colonne = {
        "Société": "societe",
        "Agence": "agence",
        "Groupe": "groupe",
        "Secteur": "secteur",
    }[maille_label]
    comparaison_org = construire_comparaison_organisation(
        df_esi_contexte,
        maille_colonne,
        indicateur_org,
    )
    afficher_comparaison_organisation(comparaison_org, indicateur_org)
    if not comparaison_org.empty:
        dataframe_download(
            "Télécharger la comparaison organisationnelle",
            comparaison_org,
            "comparaison_couverture_organisation.csv",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "Couverture contractuelle par métier",
        "Pour chaque métier : nombre et pourcentage d’ESI possédant au moins un contrat actif dont la date de fin n’est pas dépassée.",
    )
    couverture_metier = construire_couverture_metier(df_esi_contexte, df_contrats_recherche)
    afficher_couverture_metier(couverture_metier)
    if not couverture_metier.empty:
        dataframe_download(
            "Télécharger la couverture par métier",
            couverture_metier,
            "couverture_esi_par_metier.csv",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "Évolution mensuelle de la couverture",
        "Reconstruction à partir des dates de création, désactivation et fin des contrats. La maille organisationnelle utilisée est la maille actuelle des ESI.",
    )
    hist_col1, hist_col2 = st.columns([1, 1])
    with hist_col1:
        periode_couverture = st.radio(
            "Période",
            [12, 24, 36],
            horizontal=True,
            key="coverage_historique_mois",
            format_func=lambda valeur: f"{valeur} mois",
        )
    with hist_col2:
        maille_historique_label = st.selectbox(
            "Maille historique",
            ["Patrimoine filtré", "Société", "Agence", "Groupe", "Secteur"],
            key="coverage_historique_maille",
        )

    maille_historique_colonne = {
        "Patrimoine filtré": "Patrimoine filtré",
        "Société": "societe",
        "Agence": "agence",
        "Groupe": "groupe",
        "Secteur": "secteur",
    }[maille_historique_label]

    entites_selectionnees: list[str] = []
    if maille_historique_colonne != "Patrimoine filtré":
        options_entites = (
            nettoyer_texte(df_esi_contexte[maille_historique_colonne])
            .value_counts()
            .index.tolist()
        )
        defaults_entites = options_entites[: min(4, len(options_entites))]
        entites_selectionnees = st.multiselect(
            "Entités comparées",
            options=options_entites,
            default=defaults_entites,
            max_selections=6,
            placeholder="Sélectionner jusqu’à 6 entités",
            key="coverage_historique_entites",
        )

    historique_couverture = construire_historique_couverture(
        df_esi_contexte,
        df_contrats_recherche,
        maille_historique_colonne,
        entites_selectionnees,
        int(periode_couverture),
    )
    afficher_historique_couverture(historique_couverture)
    if not historique_couverture.empty:
        dataframe_download(
            "Télécharger l’évolution de la couverture",
            formatter_dates_table(historique_couverture),
            "evolution_mensuelle_couverture_esi.csv",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "Listes exportables",
        "Sélectionne la population à analyser. L’export reprend toutes les lignes du périmètre filtré.",
    )
    liste_col1, liste_col2 = st.columns([1.25, 2.75], vertical_alignment="bottom")
    with liste_col1:
        population = st.selectbox(
            "Population affichée",
            [
                "Tous les ESI",
                "ESI avec au moins un équipement",
                "ESI sans équipement",
                "ESI avec au moins un équipement couvert",
                "ESI dont tous les équipements sont couverts",
                "ESI partiellement couverts",
                "ESI équipés sans aucun équipement couvert",
                "ESI équipés sans aucun contrat",
                "ESI sans aucun contrat",
                "ESI avec plusieurs contrats sur le même métier",
                "Équipements sans couverture valide",
                "Équipements couverts par un contrat actif valide",
            ],
            key="coverage_population_export",
        )
    with liste_col2:
        recherche_liste = st.text_input(
            "Rechercher dans la liste",
            placeholder="Référence, libellé, société, agence, groupe, secteur...",
            key="coverage_recherche_liste",
        )

    esi_liste = ajouter_niveau_couverture(df_esi_contexte)
    nom_fichier_liste = "liste_couverture.csv"
    if population == "Tous les ESI":
        table_liste = preparer_table_esi(esi_liste)
    elif population == "ESI avec au moins un équipement":
        table_liste = preparer_table_esi(esi_liste[serie_numerique(esi_liste, "nb_equipements") > 0])
    elif population == "ESI sans équipement":
        table_liste = preparer_table_esi(esi_liste[serie_numerique(esi_liste, "nb_equipements") == 0])
    elif population == "ESI avec au moins un équipement couvert":
        table_liste = preparer_table_esi(
            esi_liste[serie_numerique(esi_liste, "nb_equipements_couverts_valides") > 0]
        )
    elif population == "ESI dont tous les équipements sont couverts":
        table_liste = preparer_table_esi(
            esi_liste[esi_liste["niveau_couverture_equipements"] == "Tous les équipements couverts"]
        )
    elif population == "ESI partiellement couverts":
        table_liste = preparer_table_esi(
            esi_liste[esi_liste["niveau_couverture_equipements"] == "Équipements partiellement couverts"]
        )
    elif population == "ESI équipés sans aucun équipement couvert":
        table_liste = preparer_table_esi(
            esi_liste[esi_liste["niveau_couverture_equipements"] == "Aucun équipement couvert"]
        )
    elif population == "ESI équipés sans aucun contrat":
        table_liste = preparer_table_esi(
            esi_liste[serie_numerique(esi_liste, "esi_avec_equipement_sans_aucun_contrat") > 0]
        )
    elif population == "ESI sans aucun contrat":
        table_liste = preparer_table_esi(
            esi_liste[serie_numerique(esi_liste, "esi_sans_aucun_contrat") > 0]
        )
    elif population == "ESI avec plusieurs contrats sur le même métier":
        colonne_multi = (
            "esi_multi_meme_metier_valide"
            if "esi_multi_meme_metier_valide" in esi_liste.columns
            else "esi_multi_meme_metier"
        )
        table_liste = preparer_table_esi(esi_liste[serie_numerique(esi_liste, colonne_multi) > 0])
    elif population == "Équipements sans couverture valide":
        if df_equipements_filtre.empty:
            table_liste = pd.DataFrame()
        elif "equipment_covered_valid" in df_equipements_filtre.columns:
            table_liste = preparer_table_equipements(
                df_equipements_filtre[serie_numerique(df_equipements_filtre, "equipment_covered_valid") == 0]
            )
        elif "couverture_status" in df_equipements_filtre.columns:
            table_liste = preparer_table_equipements(
                df_equipements_filtre[
                    df_equipements_filtre["couverture_status"]
                    != "Couvert par un contrat actif valide"
                ]
            )
        else:
            table_liste = pd.DataFrame()
        nom_fichier_liste = "equipements_sans_couverture_valide.csv"
    else:
        if df_equipements_filtre.empty:
            table_liste = pd.DataFrame()
        elif "equipment_covered_valid" in df_equipements_filtre.columns:
            table_liste = preparer_table_equipements(
                df_equipements_filtre[serie_numerique(df_equipements_filtre, "equipment_covered_valid") > 0]
            )
        elif "couverture_status" in df_equipements_filtre.columns:
            table_liste = preparer_table_equipements(
                df_equipements_filtre[
                    df_equipements_filtre["couverture_status"]
                    == "Couvert par un contrat actif valide"
                ]
            )
        else:
            table_liste = pd.DataFrame()
        nom_fichier_liste = "equipements_couverts_valides.csv"

    table_liste = filtrer_table_recherche(table_liste, recherche_liste)
    table_summary(len(table_liste), "ligne(s) correspondant à la population", mode=population)
    afficher_table_paginated(
        table_liste,
        key="coverage_liste_exportable",
        filename=nom_fichier_liste,
        hauteur=500,
    )


# =====================================================
# VUE 3 — QUALITÉ ET ANOMALIES
# =====================================================


else:
    section(
        "Qualité et anomalies",
        "Les incohérences de données sont séparées des alertes métier de couverture pour ne pas mélanger erreur technique et situation patrimoniale à analyser.",
    )

    sous_vue = st.radio(
        "Type de suivi",
        ["Anomalies de données", "Alertes de couverture"],
        horizontal=True,
        key="quality_subview",
    )

    if sous_vue == "Anomalies de données":
        qualite = df_qualite_filtre.copy()
        if qualite.empty:
            st.success("Aucune anomalie de données dans le périmètre affiché.")
        else:
            gravite = nettoyer_texte(qualite["gravite"]).str.lower() if "gravite" in qualite.columns else pd.Series("", index=qualite.index)
            critiques = qualite.loc[gravite == "critique", "objet_reference"].nunique() if "objet_reference" in qualite.columns else int((gravite == "critique").sum())
            hautes = qualite.loc[gravite == "haute", "objet_reference"].nunique() if "objet_reference" in qualite.columns else int((gravite == "haute").sum())
            moyennes = qualite.loc[gravite == "moyenne", "objet_reference"].nunique() if "objet_reference" in qualite.columns else int((gravite == "moyenne").sum())
            total_objets = qualite["objet_reference"].nunique() if "objet_reference" in qualite.columns else len(qualite)
            sans_prestation = (
                qualite.loc[
                    qualite["anomalie_type"] == "CONTRAT_ACTIF_SANS_CODE_PRESTATION",
                    "objet_reference",
                ].nunique()
                if "anomalie_type" in qualite.columns and "objet_reference" in qualite.columns
                else 0
            )

            q1, q2, q3, q4 = st.columns(4)
            with q1:
                alert_card("Objets en anomalie", total_objets, "Objets distincts concernés.", C_RED)
            with q2:
                alert_card("Critiques", critiques, "Références orphelines ou incohérences fortes.", C_VIOLET)
            with q3:
                alert_card("Hautes", hautes, "Données empêchant ou fragilisant l’analyse.", C_RED)
            with q4:
                alert_card("Contrats actifs sans prestation", sans_prestation, "Contrats actifs sans code de prestation.", C_TEAL)

            st.markdown("<br>", unsafe_allow_html=True)
            resume = (
                qualite.groupby(["anomalie_type", "gravite"], as_index=False)
                .agg(
                    **{
                        "Nombre d’occurrences": ("objet_reference", "count"),
                        "Objets distincts": ("objet_reference", "nunique"),
                    }
                )
                .rename(columns={"anomalie_type": "Type anomalie", "gravite": "Gravité"})
                .sort_values("Objets distincts", ascending=False)
            )
            resume["Anomalie"] = resume["Type anomalie"].map(libelle_code)

            graphe_col, resume_col = st.columns([1.1, 1])
            with graphe_col:
                st.markdown('<div class="vg-mini-title">Anomalies principales</div>', unsafe_allow_html=True)
                afficher_barres_horizontales(
                    resume[["Anomalie", "Objets distincts"]],
                    "Anomalie",
                    "Objets distincts",
                    C_VIOLET,
                    top_n=10,
                    nom_export="anomalies_principales",
                )
            with resume_col:
                st.markdown('<div class="vg-mini-title">Résumé des contrôles</div>', unsafe_allow_html=True)
                st.dataframe(
                    resume[["Anomalie", "Gravité", "Nombre d’occurrences", "Objets distincts"]],
                    width="stretch",
                    hide_index=True,
                    height=390,
                )

            filtres_q1, filtres_q2, filtres_q3 = st.columns([1.15, 1.15, 2.7], vertical_alignment="bottom")
            with filtres_q1:
                types_options = sorted(qualite["anomalie_type"].dropna().astype(str).unique().tolist())
                type_anomalie = st.selectbox(
                    "Anomalie affichée",
                    ["Toutes les anomalies"] + types_options,
                    format_func=lambda valeur: "Toutes les anomalies" if valeur == "Toutes les anomalies" else libelle_code(valeur),
                    key="quality_type_anomalie",
                )
            with filtres_q2:
                gravites_options = sorted(qualite["gravite"].dropna().astype(str).unique().tolist())
                gravites_choisies = st.multiselect(
                    "Gravités",
                    options=gravites_options,
                    default=gravites_options,
                    placeholder="Toutes les gravités",
                    key="quality_gravites",
                )
            with filtres_q3:
                recherche_qualite = st.text_input(
                    "Rechercher dans les anomalies",
                    placeholder="Référence, description, société, agence, ESI, code de prestation...",
                    key="quality_search",
                )

            detail = qualite.copy()
            if type_anomalie != "Toutes les anomalies":
                detail = detail[detail["anomalie_type"] == type_anomalie].copy()
            if gravites_choisies:
                detail = detail[detail["gravite"].isin(gravites_choisies)].copy()
            detail_table = filtrer_table_recherche(preparer_table_qualite(detail), recherche_qualite)
            table_summary(len(detail_table), "anomalie(s) affichée(s)", mode=type_anomalie)
            afficher_table_paginated(
                detail_table,
                key="quality_anomalies",
                filename="anomalies_donnees.csv",
                hauteur=500,
            )

    else:
        alertes = df_alertes_filtre.copy()
        if alertes.empty:
            st.info(
                "La table dashboard.alertes_couverture est absente ou vide. "
                "Charge la table légère issue de dashboard.alertes_couverture_next."
            )
        else:
            def compter_alerte(code: str) -> int:
                sous = alertes[alertes["alerte_type"] == code]
                return sous["objet_reference"].nunique() if "objet_reference" in sous.columns else len(sous)

            a1, a2, a3, a4, a5 = st.columns(5)
            with a1:
                alert_card("ESI sans contrat actif", compter_alerte("ESI_SANS_CONTRAT_ACTIF"), "Aucun contrat actif rattaché.", C_RED)
            with a2:
                alert_card("ESI sans aucun contrat", compter_alerte("ESI_SANS_AUCUN_CONTRAT"), "Aucun contrat actif ou inactif.", C_VIOLET)
            with a3:
                alert_card("Aucune couverture équipement", compter_alerte("ESI_EQUIPE_AUCUNE_COUVERTURE"), "ESI équipé sans équipement couvert.", C_RED)
            with a4:
                alert_card("Couverture partielle", compter_alerte("ESI_PARTIELLEMENT_COUVERT"), "Une partie des équipements reste non couverte.", C_YELLOW)
            with a5:
                alert_card("Multi-contrats même métier", compter_alerte("ESI_MULTI_CONTRATS_MEME_METIER"), "Chevauchements potentiels à analyser.", C_TEAL)

            st.markdown("<br>", unsafe_allow_html=True)
            resume_alertes = (
                alertes.groupby(["alerte_type", "objet_type", "priorite"], as_index=False)
                .agg(
                    **{
                        "Nombre d’alertes": ("objet_reference", "count"),
                        "Objets distincts": ("objet_reference", "nunique"),
                    }
                )
                .rename(
                    columns={
                        "alerte_type": "Type alerte",
                        "objet_type": "Type objet",
                        "priorite": "Priorité",
                    }
                )
                .sort_values("Objets distincts", ascending=False)
            )
            resume_alertes["Alerte"] = resume_alertes["Type alerte"].map(libelle_code)

            graphe_alertes, table_alertes_resume = st.columns([1.1, 1])
            with graphe_alertes:
                st.markdown('<div class="vg-mini-title">Alertes principales</div>', unsafe_allow_html=True)
                afficher_barres_horizontales(
                    resume_alertes[["Alerte", "Objets distincts"]],
                    "Alerte",
                    "Objets distincts",
                    C_RED,
                    top_n=10,
                    nom_export="alertes_principales",
                )
            with table_alertes_resume:
                st.markdown('<div class="vg-mini-title">Résumé des alertes</div>', unsafe_allow_html=True)
                st.dataframe(
                    resume_alertes[["Alerte", "Type objet", "Priorité", "Nombre d’alertes", "Objets distincts"]],
                    width="stretch",
                    hide_index=True,
                    height=390,
                )

            f1, f2 = st.columns([1.2, 2.8], vertical_alignment="bottom")
            with f1:
                options_alertes = sorted(alertes["alerte_type"].dropna().astype(str).unique().tolist())
                type_alerte = st.selectbox(
                    "Alerte affichée",
                    ["Toutes les alertes"] + options_alertes,
                    format_func=lambda valeur: "Toutes les alertes" if valeur == "Toutes les alertes" else libelle_code(valeur),
                    key="quality_type_alerte",
                )
            with f2:
                recherche_alerte = st.text_input(
                    "Rechercher dans les alertes",
                    placeholder="Référence, libellé, société, agence, ESI, équipement...",
                    key="quality_search_alertes",
                )

            detail_alertes = alertes.copy()
            if type_alerte != "Toutes les alertes":
                detail_alertes = detail_alertes[detail_alertes["alerte_type"] == type_alerte].copy()
            table_alertes = filtrer_table_recherche(
                preparer_table_alertes(detail_alertes),
                recherche_alerte,
            )
            table_summary(len(table_alertes), "alerte(s) affichée(s)", mode=type_alerte)
            afficher_table_paginated(
                table_alertes,
                key="quality_alertes",
                filename="alertes_couverture.csv",
                hauteur=500,
            )


# =====================================================
# FOOTER
# =====================================================


dates_maj: list[pd.Timestamp] = []
for frame in [df_global, df_qualite, df_alertes]:
    if not frame.empty and "date_maj" in frame.columns:
        serie_dates = pd.to_datetime(frame["date_maj"], errors="coerce").dropna()
        if not serie_dates.empty:
            dates_maj.append(serie_dates.max())

if dates_maj:
    st.caption(f"Dernière mise à jour des données dashboard : {fmt_date(max(dates_maj), avec_heure=True)}")
else:
    st.caption("Données issues des tables légères du schéma dashboard.")
