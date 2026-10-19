"""Filtres et tris par colonne des listes d'interventions (menu déroulant sur chaque en-tête, comme dans Excel).
Tout est calculé côté base : une liste peut contenir des millions de lignes, on ne filtre jamais en mémoire.
Les listes lisent rex.f_operations (alias t) : une colonne = une expression SQL commune à toutes les listes."""
from services.vg import status_expr

_DELAI = "CASE WHEN t.hors_delai_global THEN 'late' WHEN t.global_comparable THEN 'ok' ELSE 'sans' END"
# Ponctualité d'un passage préventif : un seul état par passage, du plus précis au plus général.
_DELAI_PREV = ("CASE WHEN t.preventive_annulee THEN 'annule' "
               "WHEN t.preventive_realisee AND COALESCE(t.preventive_realisee_en_retard, false) THEN 'real_retard' "
               "WHEN t.preventive_realisee AND COALESCE(t.preventive_realisee_dans_delai, false) THEN 'real_ok' "
               "WHEN t.preventive_realisee THEN 'real_inconnue' "
               "WHEN COALESCE(t.preventive_actuellement_en_retard, false) THEN 'non_real_retard' "
               "WHEN COALESCE(t.preventive_restante, false) THEN 'a_venir' "
               "WHEN COALESCE(t.preventive_cloturee_non_realisee, false) THEN 'clot_non_real' ELSE 'autre' END")
PONCT_LIB = {"real_ok": "Réalisé dans le délai", "real_retard": "Réalisé en retard", "real_inconnue": "Réalisé, ponctualité inconnue",
             "non_real_retard": "Non réalisé, en retard", "a_venir": "Non réalisé, pas encore en retard",
             "clot_non_real": "Clôturé sans être réalisé", "annule": "Annulé", "autre": "Autre"}

# sens : txt, date ou num (libellés du tri). n : libellés (renseigné, non renseigné). t : recherche « contient ».
# tri : la colonne se trie. filtre : expression utilisée pour le filtre par valeurs, si elle diffère de l'affichage.
COLS = {
    "reference": {"expr": "t.reference", "sens": "txt", "tri": True, "t": True},
    "equipement": {"expr": "t.equipment_reference", "sens": "txt", "tri": True, "t": True, "n": ("Avec équipement", "Sans équipement")},
    "statut": {"expr": status_expr(), "sens": "txt", "tri": True},
    "type": {"expr": "t.work_type", "sens": "txt", "tri": True},
    "delai": {"expr": _DELAI, "tri": False},
    "delai_prev": {"expr": _DELAI_PREV, "tri": False},
    "metier": {"expr": "COALESCE(t.metier, 'Non renseigné')", "sens": "txt", "tri": True},
    "prestataire": {"expr": "t.provider_name", "filtre": "t.provider_id::text", "sens": "txt", "tri": True},
    "contrat": {"expr": "t.contract_reference", "sens": "txt", "tri": True, "t": True},
    "programme": {"expr": "COALESCE(t.programme_label, t.programme_reference)", "sens": "txt", "tri": True, "t": True},
    "creation": {"expr": "t.creation_date", "sens": "date", "tri": True},
    "prevue": {"expr": "COALESCE(t.date_prevue, t.creation_date)", "sens": "date", "tri": True},
    "cloturee": {"expr": "COALESCE(t.event_date, t.creation_date)", "sens": "date", "tri": True},
    "pec": {"expr": "CASE WHEN t.response_time > 0 THEN t.response_time END", "sens": "num", "tri": True, "n": ("Mesurée", "Non mesurée")},
    "res": {"expr": "CASE WHEN t.resolution_duration > 0 THEN t.resolution_duration END", "sens": "num", "tri": True, "n": ("Mesurée", "Non mesurée")},
    "sla_pec": {"expr": "t.sla_intervention_value", "tri": False, "n": ("Avec SLA", "Sans SLA")},
    "sla_res": {"expr": "t.sla_recovery_value", "tri": False, "n": ("Avec SLA", "Sans SLA")},
    "fin": {"expr": "t.type_fin", "sens": "txt", "tri": True, "n": ("Avec type de fin", "Sans type de fin")},
    "motif": {"expr": "COALESCE(t.motif_cloture, t.motif_annulation)", "sens": "txt", "tri": True, "t": True, "n": ("Avec motif", "Sans motif")},
    "cause": {"expr": "COALESCE(NULLIF(TRIM(t.technical_reason), ''), 'Non renseignée')", "sens": "txt", "tri": True},
    "retard": {"expr": "COALESCE(t.jours_retard_realisation, t.jours_retard_actuel)", "sens": "num", "tri": True},
    "realisation": {"expr": "t.date_realisation", "sens": "date", "tri": True, "n": ("Réalisé", "Pas réalisé")},
    "rapport": {"expr": "COALESCE(t.rapport_statut, 'non_verifie')", "sens": "txt", "tri": True},
}
SENS = {"txt": ("De A à Z", "De Z à A"), "date": ("Du plus ancien au plus récent", "Du plus récent au plus ancien"),
        "num": ("Du plus petit au plus grand", "Du plus grand au plus petit")}


def _like(txt):
    return "%" + txt.strip().replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"


def appliquer(etat, cles):
    """etat : {"v": {clé: [valeurs]}, "t": {clé: texte}, "n": {clé: [libellés]}, "tri": (clé, "asc"|"desc") ou None}.
    Retourne {"clauses": [...], "params": {...}, "order": str ou None}, à ajouter au WHERE et à l'ORDER BY de la liste."""
    clauses, params = [], {}
    for k in cles:
        c = COLS[k]
        vals = (etat.get("v") or {}).get(k)
        if vals:
            clauses.append(f"{c.get('filtre', c['expr'])} = ANY(:cf_v_{k})")
            params[f"cf_v_{k}"] = [str(v) for v in vals]
        txt = ((etat.get("t") or {}).get(k) or "").strip()
        if txt:
            clauses.append(f"{c['expr']} ILIKE :cf_t_{k}")
            params[f"cf_t_{k}"] = _like(txt)
        n = (etat.get("n") or {}).get(k) or []
        if c.get("n") and len(n) == 1:
            clauses.append(f"{c['expr']} IS NOT NULL" if n[0] == c["n"][0] else f"{c['expr']} IS NULL")
    order = None
    tri = etat.get("tri")
    if tri and tri[0] in cles and COLS[tri[0]].get("tri"):
        order = f"{COLS[tri[0]]['expr']} {'ASC' if tri[1] == 'asc' else 'DESC'} NULLS LAST"
    return {"clauses": clauses, "params": params, "order": order}


def vide():
    return {"clauses": [], "params": {}, "order": None}