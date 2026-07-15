from __future__ import annotations

import pandas as pd
import streamlit as st

from common.ui_style import vg_alert_card as alert_card
from common.export_utils import dataframe_download
from common.vue_globale_data import *


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
