from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from config import DB_URL
from common.app_config import setup_page
from common.ui_style import apply_3f_page_style, apply_vue_globale_style

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
# PAGE + STYLE
# =====================================================

# =====================================================
# PAGE + STYLE
# =====================================================

setup_page("Vue Globale", None)
apply_3f_page_style()
apply_vue_globale_style()




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
