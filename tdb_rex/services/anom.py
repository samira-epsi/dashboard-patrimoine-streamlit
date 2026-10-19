"""Page Anomalies : une page d'actions. Les anomalies par intervention viennent de rex.f_anomalies,
les anomalies de référentiel (contrats, prestataires) des tables de dimension."""
import pandas as pd
from database import read_sql
from services.vg import flt

# code -> (libellé, action attendue, famille)
CATALOG = {
    "PREV_RETARD_ANCIEN": ("Préventive en retard depuis longtemps", "Vérifier si le passage a eu lieu, le clôturer ou l'annuler dans Intent", "Retard"),
    "CUR_OUVERTE_ANCIENNE": ("Curative ouverte depuis longtemps", "Relancer le prestataire, clôturer ou refuser l'intervention", "Retard"),
    "CUR_SANS_MAJ": ("Curative sans mise à jour récente", "Demander un point d'avancement au prestataire", "Retard"),
    "DUREE_MOINS1": ("Durée de prise en charge ou de résolution à -1", "Corriger la saisie ou la remontée de la durée dans la source", "Données incohérentes"),
    "DUREE_ZERO": ("Durée à 0 ms", "Vérifier la remontée de la durée : elle est exclue des calculs", "Données incohérentes"),
    "SANS_TYPE_TRAVAUX": ("Intervention sans type de travaux", "Qualifier le type de travaux (curatif, préventif, rénovation)", "Données incohérentes"),
    "DATE_ABERRANTE": ("Date aberrante", "Corriger la date dans la source", "Données incohérentes"),
    "SANS_PROGRAMME": ("Intervention sans programme", "Rattacher l'intervention à un programme du patrimoine", "Patrimoine"),
    "SLA_EN_MOIS": ("SLA exprimé en mois", "Confirmer la règle de calcul du mois (calendaire par hypothèse)", "Contrats"),
    "CLOTURE_SANS_RAPPORT": ("Clôturée sans rapport", "Demander le rapport au prestataire", "Rapports"),
    "RAPPORT_ERREUR_API": ("Erreur de récupération du rapport", "Relancer la récupération des documents", "Rapports"),
}
GRAVITE = {3: "À traiter", 2: "À qualifier", 1: "Information"}
GEO_PROV = ("Société", "Agence", "Groupe", "Secteur", "Programme", "Prestataire", "Contrat", "Métier")


def _flt(filters, alias="t"):
    f = {k: v for k, v in filters.items() if k in GEO_PROV}
    clauses, params = flt(f, alias)
    types = filters.get("Type de travaux") or []
    if types:  # le type de travaux est une dimension de l'anomalie
        clauses = list(clauses) + [f"{alias}.work_type = ANY(:an_wt)"]
        params = {**params, "an_wt": list(types)}
    return clauses, params


def summary(filters):
    clauses, params = _flt(filters)
    where = " AND ".join(clauses) or "TRUE"
    return read_sql(f"""
        SELECT t.anomalie_code AS code, t.gravite, COUNT(*)::bigint AS n,
               ROUND(AVG(t.anciennete_jours))::int AS anciennete_moy, MAX(t.anciennete_jours)::int AS anciennete_max
        FROM rex.f_anomalies t WHERE {where} GROUP BY 1, 2 ORDER BY t.gravite DESC, n DESC
    """, params)


def concernees(filters):
    """Base de la page : interventions distinctes avec au moins une anomalie, et interventions du périmètre (curatives + passages préventifs, hors période)."""
    from services.vg import _types
    clauses, params = _flt(filters)
    where = " AND ".join(clauses) or "TRUE"
    n_anom = int(read_sql(f"SELECT COUNT(DISTINCT t.reference)::bigint AS n FROM rex.f_anomalies t WHERE {where}", params).iloc[0]["n"])
    gc, gp = flt({k: v for k, v in filters.items() if k in GEO_PROV}, "t")
    gw = " AND ".join(gc) or "TRUE"
    cur, prev = _types(filters)
    total = 0
    if cur:
        total += int(read_sql(f"SELECT COALESCE(SUM(nb_operations),0)::bigint AS n FROM rex.f_curatif_jour t WHERE {gw}", gp).iloc[0]["n"])
    if prev:
        total += int(read_sql(f"SELECT COALESCE(SUM(nb_prevus),0)::bigint AS n FROM rex.f_preventif_prevu_jour t WHERE {gw}", gp).iloc[0]["n"])
    return n_anom, total


def by_provider(filters, code=None):
    clauses, params = _flt(filters)
    if code:
        clauses.append("t.anomalie_code = :code")
        params["code"] = code
    where = " AND ".join(clauses) or "TRUE"
    return read_sql(f"""
        SELECT COALESCE(NULLIF(MAX(t.provider_name), ''), t.provider_id::text, 'Sans prestataire') AS prestataire,
               COUNT(*)::bigint AS n, COUNT(*) FILTER (WHERE t.gravite = 3)::bigint AS a_traiter
        FROM rex.f_anomalies t WHERE {where} GROUP BY t.provider_id ORDER BY n DESC LIMIT 15
    """, params)


def detail(filters, code, needle, limit, offset):
    clauses, params = _flt(filters)
    clauses.append("t.anomalie_code = :code")
    params["code"] = code
    if needle and needle.strip():
        clauses.append("(t.reference ILIKE :nd OR t.equipment_reference ILIKE :nd OR t.contract_reference ILIKE :nd)")
        params["nd"] = f"%{needle.strip()}%"
    where = " AND ".join(clauses)
    p = {**params, "lim": int(limit), "off": int(offset)}
    df = read_sql(f"""
        SELECT t.reference AS "Référence", t.gravite AS "Gravité", t.detail AS "Détail", t.anciennete_jours AS "Ancienneté (jours)",
               t.date_reference AS "Date de référence", t.work_type AS "Type", t.status AS "Statut",
               t.provider_name AS "Prestataire", t.contract_reference AS "Contrat", t.metier AS "Métier",
               t.programme_reference AS "Programme", t.equipment_reference AS "Équipement"
        FROM rex.f_anomalies t WHERE {where}
        ORDER BY t.gravite DESC, t.anciennete_jours DESC NULLS LAST, t.reference LIMIT :lim OFFSET :off
    """, p)
    total = int(read_sql(f"SELECT COUNT(*)::bigint AS n FROM rex.f_anomalies t WHERE {where}", params).iloc[0]["n"])
    return df, total


def referentiel(filters):
    """Anomalies du référentiel : prestataires sans contrat, contrats sans programme, contrats sans métier."""
    out = {}
    out["prestataire_hors_contrat"] = read_sql("""
        SELECT provider_id::text AS "Identifiant", COALESCE(NULLIF(provider_name, ''), provider_id::text) AS "Prestataire",
               nb_interventions AS "Interventions"
        FROM rex.d_prestataire WHERE hors_contrat AND nb_interventions > 0 ORDER BY nb_interventions DESC
    """)
    out["contrat_sans_programme"] = read_sql("""
        SELECT c.contract_reference AS "Référence", c.contract_label AS "Libellé", c.contract_status AS "Statut", c.provider_name AS "Prestataire"
        FROM rex.d_contrat c
        WHERE NOT EXISTS (SELECT 1 FROM rex.r_prestataire_programme r WHERE r.contract_reference = c.contract_reference)
        ORDER BY c.contract_label, c.contract_reference
    """)
    out["contrat_sans_metier"] = read_sql(f"""
        SELECT c.contract_reference AS "Référence", c.contract_label AS "Libellé", c.contract_status AS "Statut", c.provider_name AS "Prestataire"
        FROM rex.d_contrat c WHERE c.metier IS NULL OR c.metier = '{'Non renseigné'}'
        ORDER BY c.contract_label, c.contract_reference
    """)
    return out