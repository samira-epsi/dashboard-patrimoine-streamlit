"""Traduction en français de tout ce qui vient de la base : statuts, types de travaux, types de fin, noms de colonnes.
Un seul endroit à compléter si une nouvelle valeur apparaît dans la source."""
import pandas as pd

STATUT = {"open": "Ouverte", "pending": "En cours", "hold": "En attente", "closed": "Clôturée", "denied": "Refusée", "canceled": "Annulée"}
STATUT_CONTRAT = {"active": "Actif", "inactive": "Inactif"}
TYPE_TRAVAUX = {"corrective": "Curative", "preventive": "Préventive", "renovation": "Rénovation"}
TYPE_FIN = {"done": "Réalisée", "solved": "Résolue", "partial_repair": "Réparation partielle", "occupant_absent": "Occupant absent",
            "non_contractual": "Hors contrat", "unable": "Impossible à réaliser"}
CAUSE = {"technical_failure": "Panne technique", "external_reason": "Cause externe", "false_alert": "Fausse alerte", "abnormal_use": "Usage anormal",
         "time_worn": "Usure normale", "other_pm": "Autre (PM)", "other_sp": "Autre (SP)", "Non renseignée": "Non renseignée"}
TYPE_FIN.update({"occupant_denial": "Refus de l'occupant", "temporary_repair": "Réparation provisoire", "dismissed": "Classée sans suite",
                 "formal_notice": "Mise en demeure", "canceled": "Annulée"})
DELAI = {"late": "Hors délai", "ok": "Dans les délais"}
VALEURS = {**CAUSE, **STATUT, **STATUT_CONTRAT, **TYPE_TRAVAUX, **TYPE_FIN, **DELAI}

COLONNES = {
    "reference": "Référence", "equipment_reference": "Équipement", "equipment_label": "Libellé équipement", "esi": "Équipement",
    "status": "Statut", "statut": "Statut", "work_type": "Type", "creation_date": "Créée le", "ouverture": "Ouverture",
    "date_prevue": "Date prévue", "date_prevue_source": "Origine de la date prévue", "contract_topic": "Métier", "metier": "Métier",
    "contract_reference": "Contrat", "contrat": "Contrat", "programme": "Programme", "pec_heures": "Prise en charge (h)",
    "res_heures": "Résolution (h)", "late_flag": "Délai", "delai": "Délai", "sla": "SLA intervention", "sla_pec": "SLA intervention",
    "sla_res": "SLA résolution", "type_fin": "Type de fin", "objet": "Objet", "provider_name": "Prestataire", "prestataire": "Prestataire",
    "motif": "Motif de clôture ou d'annulation", "cause": "Cause technique", "ponct": "Ponctualité", "date_realisation": "Réalisée le",
    "overrun_days": "Jours de retard", "type": "Type", "agence": "Agence", "date": "Date", "mois": "Mois", "annee": "Année",
}


def traduire(df):
    """Renomme les colonnes encore en anglais et traduit les valeurs connues (statuts, types...). N'altère pas l'original."""
    if df is None or not hasattr(df, "columns"):
        return df
    df = df.copy()
    noms, vus = [], set()
    for c in df.columns:
        nom = COLONNES.get(str(c), c)
        if nom in vus:  # deux colonnes de même libellé : la seconde garde son nom d'origine
            nom = c if c not in vus else f"{c} (2)"
        vus.add(nom)
        noms.append(nom)
    df.columns = noms
    for i in range(df.shape[1]):
        s = df.iloc[:, i]
        if s.dtype == object:
            vals = {v for v in s.dropna().unique() if isinstance(v, str)}
            if vals and vals <= set(VALEURS):
                df.isetitem(i, s.map(lambda v: VALEURS.get(v, v) if isinstance(v, str) else v))
    return df


def libelle(valeur, table=None):
    """Libellé français d'une valeur de la source ; une valeur inconnue devient un texte lisible (sans tiret bas) plutôt que du code brut."""
    if valeur is None:
        return valeur
    v = str(valeur)
    t = {**VALEURS, **(table or {})}
    if v in t:
        return t[v]
    return v.replace("_", " ").capitalize() if v.islower() or "_" in v else v


MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def mois(dates, annee=True):
    """Libellés de mois en français (« août 25 ») pour les axes de graphiques ; jamais de noms anglais (aug, sep...)."""
    d = pd.to_datetime(pd.Series(dates))
    return [f"{MOIS[x.month - 1]} {str(x.year)[2:]}" if annee else MOIS[x.month - 1] for x in d]


def duree(heures, vide="–"):
    """Durée lisible : minutes sous 1 h, heures sous 24 h, jours au-delà (1 décimale sous 10 jours)."""
    import pandas as pd
    if heures is None or pd.isna(heures):
        return vide
    h = float(heures)
    if h < 1:
        return f"{round(h * 60)} min"
    if h < 24:
        return (f"{h:.1f}".replace(".", ",").removesuffix(",0")) + " h"
    j = h / 24
    return (f"{j:.1f}".replace(".", ",").removesuffix(",0") if j < 10 else f"{j:.0f}") + " j"