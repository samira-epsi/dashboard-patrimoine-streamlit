"""Point d'entrée des requêtes de l'application. Toutes lisent le schéma rex (tables légères, pré-calculées la nuit).
Vue globale : services/vg.py. Prestataires et fiche : services/prov.py. Anomalies : services/anom.py.
Curatives, Préventives, Qualité des rapports : services/interv.py."""
from services.vg import (STATUS_LABEL, STATUS_VALUES, NO_TOPIC, total_history, bounds, options,  # noqa: F401
                         global_kpis, trend, zones, equipments, equipment_context, details, details_total)
from services.prov import (providers_list, providers_kpis, providers_interventions, provider_label,  # noqa: F401
                           provider_coverage, contract_details, housings_by_program, provider_status, provider_prev, provider_delays,
                           provider_equipments, provider_equipment_list, provider_interventions, provider_interventions_total)

# Libellés des filtres affichés dans l'en-tête, dans l'ordre.
DIMENSIONS = {
    "Société": ("societe_reference", "societe_label"),
    "Agence": ("agence_reference", "agence_label"),
    "Groupe": ("groupe_reference", "groupe_label"),
    "Secteur": ("secteur_reference", "secteur_label"),
    "Programme": ("programme_reference", "programme_label"),
    "Prestataire": ("provider_id", "provider_name"),
    "Métier": ("metier", "metier"),
    "Contrat": ("contract_reference", "contract_label"),
    "Type de travaux": ("work_type", "work_type"),
}