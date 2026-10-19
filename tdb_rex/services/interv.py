"""Pages Curatives, Préventives, Performance prestataires et Qualité des rapports, sur le schéma rex.
Curatif : rex.f_curatif_jour (jour = date de création). Préventif : rex.f_preventif_prevu_jour (jour = date prévue, ou
date de création quand la date prévue n'existe pas : date_source le dit). Rapports : colonnes nb_rapport_* et f_operations."""
import pandas as pd

from database import read_sql
from services import fr
from services.vg import flt, where, _types, NO_TOPIC, status_expr

WORK = {"Curatives": "corrective", "Préventives": "preventive"}
ACTIVE = ("open", "pending", "hold")
MS_H = 3_600_000


# ---------------------------------------------------------------- curatif
def status_breakdown(filters, start, end, work_type="corrective"):
    """Curatives par statut : volume, comparables et hors délai. Le statut 'denied' regroupe les refusées (dont annulées)."""
    w, p = where(filters, start, end)
    return read_sql(f"""
        SELECT {status_expr()} AS status, SUM(t.nb_operations)::bigint AS n,
               SUM(t.nb_pec_comparables)::bigint AS comp_pec, SUM(t.nb_pec_hors_delai)::bigint AS late_pec,
               SUM(t.nb_res_comparables)::bigint AS comp_res, SUM(t.nb_res_hors_delai)::bigint AS late_res
        FROM rex.f_curatif_jour t WHERE {w} AND t.status IS NOT NULL GROUP BY 1
    """, p)


def end_types(filters, start, end):
    """Types de fin (event) des curatives clôturées ou refusées : done, solved, partial_repair, occupant_absent,
    canceled, non_contractual, unable. Ce n'est pas un motif libre mais l'événement de fin."""
    w, p = where(filters, start, end)
    return read_sql(f"""
        SELECT t.status, t.type_fin, SUM(t.nb_operations)::bigint AS n
        FROM rex.f_curatif_jour t WHERE {w} AND t.status IN ('closed', 'denied') GROUP BY 1, 2 ORDER BY n DESC
    """, p)


def technical_causes(filters, start, end, work_type="corrective"):
    """Cause technique (champ technical_reason) : une cause, pas un motif de clôture."""
    w, p = where(filters, start, end, date_col="jour_creation")
    p["wt"] = work_type
    return read_sql(f"""
        SELECT COALESCE(NULLIF(TRIM(t.technical_reason), ''), 'Non renseignée') AS cause, COUNT(*)::bigint AS n
        FROM rex.f_operations t WHERE {w} AND t.work_type = :wt AND t.status = 'closed'
        GROUP BY 1 ORDER BY n DESC LIMIT 8
    """, p)


def transparency(filters, start, end):
    """Compteurs de transparence du calcul hors délai (curatives hors refusées)."""
    w, p = where(filters, start, end)
    return read_sql(f"""
        SELECT COALESCE(SUM(nb_operations) FILTER (WHERE status <> 'denied'),0)::bigint AS curatives,
               COALESCE(SUM(nb_sans_sla_intervention) FILTER (WHERE status <> 'denied'),0)::bigint AS sans_sla_pec,
               COALESCE(SUM(nb_sans_sla_resolution) FILTER (WHERE status <> 'denied'),0)::bigint AS sans_sla_res,
               COALESCE(SUM(nb_pec_duree_nulle),0)::bigint AS pec_nulle, COALESCE(SUM(nb_pec_duree_moins1),0)::bigint AS pec_moins1,
               COALESCE(SUM(nb_pec_duree_zero),0)::bigint AS pec_zero,
               COALESCE(SUM(nb_res_duree_nulle),0)::bigint AS res_nulle, COALESCE(SUM(nb_res_duree_moins1),0)::bigint AS res_moins1,
               COALESCE(SUM(nb_res_duree_zero),0)::bigint AS res_zero,
               COALESCE(SUM(nb_pec_comparables_mois),0)::bigint AS pec_mois,
               COALESCE(SUM(nb_sla_unite_inconnue),0)::bigint AS unite_inconnue,
               COALESCE(SUM(nb_pec_comparables),0)::bigint AS comparables_pec
        FROM rex.f_curatif_jour t WHERE {w}
    """, p).iloc[0]


# ---------------------------------------------------------------- préventif
def prev_summary(filters, start, end):
    """Prévu vs réalisé sur la période (date prévue). prevus = realises + cloturees_non_realisees + restants + annules."""
    w, p = where(filters, start, end)
    return read_sql(f"""
        SELECT COALESCE(SUM(nb_prevus),0)::bigint AS prevus, COALESCE(SUM(nb_realises),0)::bigint AS realises,
               COALESCE(SUM(nb_realises_dans_delai),0)::bigint AS dans_delai, COALESCE(SUM(nb_realises_en_retard),0)::bigint AS en_retard_realise,
               COALESCE(SUM(nb_realises_ponctualite_inconnue),0)::bigint AS ponctualite_inconnue,
               COALESCE(SUM(nb_cloturees_non_realisees),0)::bigint AS cloturees_non_realisees,
               COALESCE(SUM(nb_restants),0)::bigint AS restants, COALESCE(SUM(nb_actuellement_en_retard),0)::bigint AS actuellement_en_retard,
               COALESCE(SUM(nb_annules),0)::bigint AS annules, COALESCE(SUM(nb_refusees_hors_programme),0)::bigint AS hors_programme,
               COALESCE(SUM(nb_replanifications),0)::bigint AS replanifications,
               COALESCE(SUM(nb_prevus) FILTER (WHERE date_source = 'creation_par_defaut'),0)::bigint AS date_defaut,
               COALESCE(SUM(nb_prevus) FILTER (WHERE date_source = 'historique_planned'),0)::bigint AS date_historique,
               COALESCE(SUM(nb_prevus) FILTER (WHERE date_source = 'evenement_courant'),0)::bigint AS date_courante
        FROM rex.f_preventif_prevu_jour t WHERE {w}
    """, p).iloc[0]


def prev_realised_by_date(filters, start, end):
    """Réalisé sur la période de réalisation (autre notion de période) : nombre de passages réalisés par mois."""
    w, p = where(filters, start, end)
    return read_sql(f"""
        SELECT date_trunc('month', t.jour)::date AS periode, SUM(t.nb_realises)::bigint AS realises
        FROM rex.f_preventif_realise_jour t WHERE {w} GROUP BY 1 ORDER BY 1
    """, p)


def prev_monthly_result(filters, start, end, grain="Mensuel"):
    """Préventif par période (date prévue) et par résultat : réalisés, clôturés non réalisés, restants, annulés."""
    trunc = "month" if grain == "Mensuel" else "year"
    w, p = where(filters, start, end)
    df = read_sql(f"""SELECT date_trunc('{trunc}', t.jour)::date AS d, COALESCE(SUM(nb_realises),0)::bigint AS realises,
                             COALESCE(SUM(nb_cloturees_non_realisees),0)::bigint AS non_realises,
                             COALESCE(SUM(nb_restants),0)::bigint AS restants, COALESCE(SUM(nb_annules),0)::bigint AS annules
                      FROM rex.f_preventif_prevu_jour t WHERE {w} GROUP BY 1 ORDER BY 1""", p)
    df["periode"] = fr.mois(df["d"]) if grain == "Mensuel" else pd.to_datetime(df["d"]).dt.strftime("%Y").tolist()
    return df


def monthly_status(filters, start, end, grain="Mensuel"):
    """Curatives par période (date de création) et par statut : colonnes periode, status, n."""
    trunc = "month" if grain == "Mensuel" else "year"
    w, p = where(filters, start, end)
    df = read_sql(f"""SELECT date_trunc('{trunc}', t.jour)::date AS d, {status_expr()} AS status, SUM(t.nb_operations)::bigint AS n
                      FROM rex.f_curatif_jour t WHERE {w} AND t.status IS NOT NULL GROUP BY 1, 2 ORDER BY 1""", p)
    df["periode"] = fr.mois(df["d"]) if grain == "Mensuel" else pd.to_datetime(df["d"]).dt.strftime("%Y").tolist()
    return df[["periode", "status", "n"]]


def monthly(filters, start, end, work_type, indicator, grain="Mensuel"):
    trunc = "month" if grain == "Mensuel" else "year"
    w, p = where(filters, start, end)
    if work_type == "corrective":
        rate = "retard" in indicator or "délai" in indicator
        value = "100.0 * SUM(t.nb_pec_hors_delai) / NULLIF(SUM(t.nb_pec_comparables), 0)" if rate else "SUM(t.nb_operations)"
        base = "SUM(t.nb_pec_comparables)" if rate else "SUM(t.nb_operations)"
        table = "rex.f_curatif_jour"
    else:
        late = "retard" in indicator
        value = "100.0 * SUM(t.nb_realises_en_retard + t.nb_actuellement_en_retard) / NULLIF(SUM(t.nb_realises_dans_delai + t.nb_realises_en_retard + t.nb_actuellement_en_retard), 0)" if late else "SUM(t.nb_prevus)"
        base = "SUM(t.nb_realises_dans_delai + t.nb_realises_en_retard + t.nb_actuellement_en_retard)" if late else "SUM(t.nb_prevus)"
        table = "rex.f_preventif_prevu_jour"
    df = read_sql(f"SELECT date_trunc('{trunc}', t.jour)::date AS periode, {value} AS valeur, {base}::float AS base FROM {table} t "
                  f"WHERE {w} GROUP BY 1 ORDER BY 1", p)
    df["periode"] = fr.mois(df["periode"]) if grain == "Mensuel" else pd.to_datetime(df["periode"]).dt.strftime("%Y").tolist()
    df["valeur"] = df["valeur"].astype(float).round(1)
    return df


# ---------------------------------------------------------------- listes
def _sla_text(value, unit):
    if value is None or pd.isna(value):
        return None
    unit = {"hour": "h", "day": "j", "month": "mois"}.get(str(unit or "").lower().strip(), str(unit or ""))
    return f"{float(value):g} {unit}".strip()


def interventions_page(filters, start, end, work_type, group, needle, limit, offset, extra=None):
    """Une page d'interventions. group : Actives (open, pending, hold), Inactives (closed, denied) ou Toutes.
    Aucun retard « en cours » n'est calculé : la date de départ du SLA n'est pas confirmée."""
    w, p = where(filters, start, end, date_col="jour_creation")
    w += " AND t.work_type = :wt"
    p["wt"] = work_type
    if work_type == "preventive":  # la période d'un passage préventif est sa date prévue (création si absente), comme dans les indicateurs
        w = w.replace("t.jour_creation", "COALESCE(t.date_prevue, t.creation_date)::date")
        w += " AND t.preventive_prevue"
    if group == "Actives":
        w += " AND t.status IN ('open', 'pending', 'hold')"
    elif group == "Inactives":
        w += " AND t.status IN ('closed', 'denied')"
    if needle and needle.strip():
        w += " AND (t.reference ILIKE :nd OR t.equipment_reference ILIKE :nd OR t.contract_reference ILIKE :nd)"
        p["nd"] = f"%{needle.strip()}%"
    if extra:
        w += "".join(" AND " + c for c in extra["clauses"])
        p.update(extra["params"])
    p.update({"lim": int(limit), "off": int(offset)})
    order = (extra or {}).get("order") or ("t.creation_date DESC" if work_type == "corrective" else "COALESCE(t.date_prevue, t.creation_date) DESC")
    df = read_sql(f"""
        SELECT t.reference, t.equipment_reference AS esi, {status_expr()} AS status, t.type_fin, t.creation_date AS ouverture,
               t.date_prevue, t.date_prevue_source, t.jours_retard_actuel,
               t.sla_intervention_value AS sla_value, t.sla_intervention_unit AS sla_unit,
               t.sla_recovery_value AS slar_value, t.sla_recovery_unit AS slar_unit,
               CASE WHEN t.response_time > 0 THEN t.response_time / {MS_H}.0 END AS pec_heures,
               t.pec_comparable, t.hors_delai_global, t.global_comparable, t.hors_delai_prise_en_charge AS late_pec,
               t.hors_delai_resolution AS late_res, CASE WHEN t.resolution_duration > 0 THEN t.resolution_duration / {MS_H}.0 END AS res_heures, t.preventive_realisee_en_retard,
               t.preventive_actuellement_en_retard, t.preventive_realisee, t.date_realisation, t.jours_retard_realisation,
               t.preventive_realisee_dans_delai, t.preventive_restante, t.preventive_cloturee_non_realisee, t.preventive_annulee,
               t.motif_cloture, t.motif_annulation, t.technical_reason,
               t.metier, t.provider_name, t.contract_reference
        FROM rex.f_operations t WHERE {w} ORDER BY {order}, t.reference LIMIT :lim OFFSET :off
    """, p)
    df["sla"] = [_sla_text(a, b) for a, b in zip(df["sla_value"], df["sla_unit"])]
    df["sla_res"] = [_sla_text(a, b) for a, b in zip(df["slar_value"], df["slar_unit"])]
    if work_type == "corrective":
        df["late"] = [True if h is True else (False if g is True else None) for h, g in zip(df["hors_delai_global"], df["global_comparable"])]
    else:
        df["late"] = [True if (a is True or b is True) else (False if r is True else None)
                      for a, b, r in zip(df["preventive_realisee_en_retard"], df["preventive_actuellement_en_retard"], df["preventive_realisee"])]
    if work_type == "preventive":
        df["ponct"] = [_ponct(r) for r in df.itertuples()]
        df["late"] = [True if c in ("real_retard", "non_real_retard") else (False if c == "real_ok" else None) for c in df["ponct"]]
        df["overrun_days"] = [(r.jours_retard_realisation if r.ponct == "real_retard" else r.jours_retard_actuel if r.ponct == "non_real_retard" else None)
                              for r in df.itertuples()]
    else:
        df["ponct"] = None
        df["overrun_days"] = None
    df["motif"] = [m if (isinstance(m, str) and m.strip()) else (a if (isinstance(a, str) and a.strip()) else None)
                   for m, a in zip(df["motif_cloture"], df["motif_annulation"])]
    df["cause"] = [c if (isinstance(c, str) and c.strip()) else None for c in df["technical_reason"]]
    total = int(read_sql(f"SELECT COUNT(*)::bigint AS n FROM rex.f_operations t WHERE {w}",
                         {k: v for k, v in p.items() if k not in ("lim", "off")}).iloc[0]["n"])
    keep = ["reference", "esi", "status", "type_fin", "ouverture", "date_prevue", "date_prevue_source", "sla", "sla_res", "pec_heures",
            "res_heures", "late_pec", "late_res", "late", "overrun_days", "ponct", "date_realisation", "motif", "cause", "metier", "provider_name", "contract_reference"]
    return df[keep], total


def _ponct(r):
    """Même règle que l'expression SQL de colf (liste préventive) : un seul état de ponctualité par passage."""
    if r.preventive_annulee is True:
        return "annule"
    if r.preventive_realisee is True:
        return "real_retard" if r.preventive_realisee_en_retard is True else "real_ok" if r.preventive_realisee_dans_delai is True else "real_inconnue"
    if r.preventive_actuellement_en_retard is True:
        return "non_real_retard"
    if r.preventive_restante is True:
        return "a_venir"
    return "clot_non_real" if r.preventive_cloturee_non_realisee is True else "autre"


# ---------------------------------------------------------------- performance prestataires
def compare_providers(filters, start, end, work_type, provider_ids=None, top=5):
    """Une ligne par prestataire : contrats, ESI, logements, agences, métiers, interventions."""
    scoped = {**filters}
    if provider_ids:
        scoped["Prestataire"] = list(provider_ids)
    geo = any(scoped.get(k) for k in ("Société", "Agence", "Groupe", "Secteur", "Programme"))
    clauses, params = flt(scoped, "c")
    clauses = ["c.provider_id IS NOT NULL"] + clauses
    if geo:
        contracts = read_sql(f"""
            SELECT c.provider_id::text AS provider_id, COALESCE(NULLIF(MAX(p.provider_name), ''), c.provider_id::text) AS provider_name,
                   COUNT(DISTINCT c.contract_reference) FILTER (WHERE c.contract_status = 'active')::bigint AS actifs,
                   COUNT(DISTINCT c.contract_reference)::bigint AS total,
                   COUNT(DISTINCT c.programme_reference)::bigint AS esi,
                   COUNT(DISTINCT c.agence_reference)::bigint AS agences,
                   (SELECT COALESCE(SUM(x.nb_logements), 0) FROM (SELECT DISTINCT r.programme_reference, r.nb_logements
                        FROM rex.r_prestataire_programme r WHERE r.provider_id = c.provider_id) x)::bigint AS logements,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT NULLIF(c.metier, '{NO_TOPIC}')), NULL) AS metiers
            FROM rex.r_prestataire_programme c JOIN rex.d_prestataire p ON p.provider_id = c.provider_id
            WHERE {" AND ".join(clauses)} GROUP BY c.provider_id
        """, params)
    else:
        contracts = read_sql(f"""
            SELECT p.provider_id::text AS provider_id, COALESCE(NULLIF(p.provider_name, ''), p.provider_id::text) AS provider_name,
                   COUNT(DISTINCT c.contract_reference) FILTER (WHERE c.contract_status = 'active')::bigint AS actifs,
                   COUNT(DISTINCT c.contract_reference)::bigint AS total,
                   MAX(p.nb_esi)::bigint AS esi, (SELECT COUNT(DISTINCT r.agence_reference)
                    FROM rex.r_prestataire_programme r WHERE r.provider_id = p.provider_id AND r.agence_reference IS NOT NULL)::bigint AS agences, MAX(p.nb_logements)::bigint AS logements,
                   ARRAY_REMOVE(ARRAY_AGG(DISTINCT NULLIF(c.metier, '{NO_TOPIC}')), NULL) AS metiers
            FROM rex.d_contrat c JOIN rex.d_prestataire p ON p.provider_id = c.provider_id
            WHERE {" AND ".join(clauses)} GROUP BY p.provider_id, p.provider_name
        """, params)
    w, p2 = where(scoped, start, end)
    table, col = ("rex.f_curatif_jour", "nb_operations") if work_type == "corrective" else ("rex.f_preventif_prevu_jour", "nb_prevus")
    counts = read_sql(f"SELECT t.provider_id::text AS provider_id, SUM(t.{col})::bigint AS interventions FROM {table} t "
                      f"WHERE {w} AND t.provider_id IS NOT NULL GROUP BY 1", p2)
    df = contracts.merge(counts, on="provider_id", how="left").fillna({"interventions": 0})
    df["interventions"] = df["interventions"].astype("int64")
    df = df.sort_values("interventions", ascending=False)
    return df if provider_ids else df.head(top)


def _cnt(col, status=None):
    return f"COALESCE(SUM(t.{col}) FILTER (WHERE t.status = '{status}'), 0)" if status else f"SUM(t.{col})"


# libellé affiché : (numérateur SQL, dénominateur SQL ou None pour un volume, sens). Sens : "good" plus haut = mieux,
# "bad" plus bas = mieux, "vol" volume neutre. Les taux ont toujours leur base : un taux sur trop peu de cas n'est pas tracé.
_OUV = "COALESCE(SUM(t.nb_operations) FILTER (WHERE t.status IN ('open','pending','hold')), 0)"
INDICATEURS = {
    "corrective": {
        "Taux hors délai contractuel": ("SUM(t.nb_pec_hors_delai)", "SUM(t.nb_pec_comparables)", "bad"),
        "Part encore en cours": (_OUV, "SUM(t.nb_operations)", "bad"),
        "Part annulées ou refusées": ("SUM(t.nb_annulees + t.nb_refusees_autres)", "SUM(t.nb_operations)", "bad"),
        "Volume d'interventions": ("SUM(t.nb_operations)", None, "vol"),
    },
    "preventive": {
        "Taux de réalisation": ("SUM(t.nb_realises)", "SUM(t.nb_prevus)", "good"),
        "Taux de retard": ("SUM(t.nb_realises_en_retard + t.nb_actuellement_en_retard)", "SUM(t.nb_realises_dans_delai + t.nb_realises_en_retard + t.nb_actuellement_en_retard)", "bad"),
        "Part restant à réaliser": ("SUM(t.nb_restants)", "SUM(t.nb_prevus)", "bad"),
        "Part annulés": ("SUM(t.nb_annules)", "SUM(t.nb_prevus)", "bad"),
        "Volume de passages prévus": ("SUM(t.nb_prevus)", None, "vol"),
    },
}
INDIC_HELP = {
    "Taux hors délai contractuel": "Interventions prises en charge hors du délai du contrat, sur celles dont le délai est comparable.",
    "Part encore en cours": "Interventions ouvertes, en cours ou en attente, sur toutes les interventions créées.",
    "Part annulées ou refusées": "Interventions annulées ou refusées, sur toutes les interventions créées.",
    "Volume d'interventions": "Nombre d'interventions créées.",
    "Taux de réalisation": "Passages réalisés sur les passages prévus.",
    "Taux de retard": "Passages en retard (réalisés après la date prévue, ou pas faits alors que la date est dépassée) sur les passages dont on peut juger la ponctualité.",
    "Part restant à réaliser": "Passages ni réalisés, ni clôturés, ni annulés, sur les passages prévus.",
    "Part annulés": "Passages annulés sur les passages prévus.",
    "Volume de passages prévus": "Nombre de passages prévus.",
}
INDIC_BASE = {"Taux de retard": "passages dont la ponctualité est jugeable", "Taux hors délai contractuel": "interventions dont le délai est comparable", "Part encore en cours": "interventions créées",
              "Part annulées ou refusées": "interventions créées", "Volume d'interventions": "interventions créées"}  # préventif : « passages prévus »
MIN_BASE = 20  # en dessous, un taux n'est pas assez solide pour être tracé ni classé
TABLE_INDIC = {"corrective": "rex.f_curatif_jour", "preventive": "rex.f_preventif_prevu_jour"}


def _ind_sql(work_type, indicator):
    """(valeur, base, numérateur, est un taux, sens). Pour un volume : valeur = base = numérateur."""
    num, den, sens = INDICATEURS[work_type][indicator]
    if den is None:
        return f"{num}::float", f"{num}::float", f"{num}::float", False, sens
    return f"100.0 * {num} / NULLIF({den}, 0)", f"{den}::float", f"{num}::float", True, sens


def _prev_window(start, end):
    """Période de même durée, juste avant la période filtrée."""
    s, e = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    days = (e - s).days + 1
    return (s - pd.Timedelta(days=days)).date(), (s - pd.Timedelta(days=1)).date()


def providers_ranking(filters, start, end, work_type, provider_ids, indicator):
    """Classement des prestataires sur toute la période : valeur, base (dénominateur ou volume), numérateur,
    et valeur sur la période précédente de même durée (pour la tendance). Retourne (données, est un taux, sens)."""
    val, base, num, is_rate, sens = _ind_sql(work_type, indicator)
    out = None
    for tag, (s0, e0) in (("", (start, end)), ("prev_", _prev_window(start, end))):
        w, p = where({**filters, "Prestataire": list(provider_ids)}, s0, e0)
        df = read_sql(f"SELECT t.provider_id::text AS provider_id, {val} AS {tag}valeur, {base} AS {tag}base, {num} AS {tag}num "
                      f"FROM {TABLE_INDIC[work_type]} t WHERE {w} GROUP BY 1", p)
        out = df if out is None else out.merge(df, on="provider_id", how="left")
    for c in out.columns:
        if c != "provider_id":
            out[c] = out[c].astype(float)
    out["valeur"] = out["valeur"].round(1)
    out["prev_valeur"] = out["prev_valeur"].round(1)
    return out, is_rate, sens


def providers_trend(filters, start, end, work_type, provider_ids, indicator, compare=True):
    """Indicateur par prestataire et par mois (par année au-delà de 36 mois), avec en option la période précédente de même durée.
    Les points d'un taux calculés sur moins de MIN_BASE cas sont retirés. Retourne (données, nombre de points, est un taux, libellés)."""
    freq = "M" if (pd.Period(end, "M") - pd.Period(start, "M")).n < 36 else "Y"
    cur = list(pd.period_range(pd.Timestamp(start), pd.Timestamp(end), freq=freq))
    n = len(cur)
    val, base, num, is_rate, _ = _ind_sql(work_type, indicator)
    series = [("Période filtrée", cur)]
    if compare:
        series.insert(0, ("Période précédente", list(pd.period_range(end=cur[0].start_time - pd.Timedelta(days=1), periods=n, freq=freq))))
    rows = []
    for serie, ps in series:
        s, e = ps[0].start_time.date(), ps[-1].end_time.date()
        w, p = where({**filters, "Prestataire": list(provider_ids)}, s, e)
        trunc = "month" if freq == "M" else "year"
        df = read_sql(f"SELECT t.provider_id::text AS provider_id, date_trunc('{trunc}', t.jour)::date AS debut, {val} AS valeur, {base} AS base, {num} AS num "
                      f"FROM {TABLE_INDIC[work_type]} t WHERE {w} GROUP BY 1, 2", p)
        pos = {pd.Timestamp(x.start_time).date(): i for i, x in enumerate(ps)}
        df["idx"] = [pos.get(pd.Timestamp(d).date()) for d in df["debut"]]
        df = df.dropna(subset=["idx"])
        df["idx"] = df["idx"].astype(int)
        df["serie"] = serie
        df["label"] = (fr.mois([ps[i].start_time for i in df["idx"]]) if freq == "M" else [str(ps[i].year) for i in df["idx"]])
        rows.append(df)
    out = pd.concat(rows, ignore_index=True)
    out["valeur"] = out["valeur"].astype(float).round(1)
    out["base"], out["num"] = out["base"].astype(float), out["num"].astype(float)
    if is_rate:
        out.loc[out["base"] < MIN_BASE, "valeur"] = float("nan")
    labels = fr.mois([x.start_time for x in cur]) if freq == "M" else [str(x.year) for x in cur]
    return out[["provider_id", "serie", "idx", "label", "valeur", "base", "num"]], n, is_rate, labels


def planned_vs_done(filters, start, end):
    """Préventif réalisé vs prévu par prestataire. Réalisé = clôturé done ou solved ; prévu = programme de la période."""
    w, p = where(filters, start, end)
    return read_sql(f"""
        SELECT t.provider_id::text AS provider_id, COALESCE(NULLIF(MAX(d.provider_name), ''), t.provider_id::text) AS provider_name,
               SUM(t.nb_realises)::bigint AS realises, SUM(t.nb_prevus)::bigint AS prevus,
               SUM(t.nb_cloturees_non_realisees)::bigint AS non_realises, SUM(t.nb_restants)::bigint AS restants,
               SUM(t.nb_annules)::bigint AS annules, SUM(t.nb_actuellement_en_retard)::bigint AS en_retard
        FROM rex.f_preventif_prevu_jour t LEFT JOIN rex.d_prestataire d ON d.provider_id = t.provider_id
        WHERE {w} AND t.provider_id IS NOT NULL
        GROUP BY t.provider_id HAVING SUM(t.nb_prevus) > 0
        ORDER BY prevus DESC LIMIT 12
    """, p)


# ---------------------------------------------------------------- qualité des rapports
def reports_by_provider(filters, start, end):
    """Rapports des interventions clôturées dont les documents ont été vérifiés (avec + sans). Les non vérifiées sont comptées à part."""
    cur, prev = _types(filters)
    parts = []
    if cur:
        w, p = where(filters, start, end)
        parts.append(read_sql(f"""SELECT t.provider_id::text AS provider_id, SUM(nb_rapport_avec)::bigint AS avec, SUM(nb_rapport_sans)::bigint AS sans,
                                        SUM(nb_rapport_non_verifie + nb_rapport_erreur)::bigint AS inconnu
                                 FROM rex.f_curatif_jour t WHERE {w} AND t.provider_id IS NOT NULL GROUP BY 1""", p))
    if prev:
        w, p = where(filters, start, end)
        parts.append(read_sql(f"""SELECT t.provider_id::text AS provider_id, SUM(nb_rapport_avec)::bigint AS avec, SUM(nb_rapport_sans)::bigint AS sans,
                                        SUM(nb_rapport_non_verifie + nb_rapport_erreur)::bigint AS inconnu
                                 FROM rex.f_preventif_prevu_jour t WHERE {w} AND t.provider_id IS NOT NULL GROUP BY 1""", p))
    if not parts:
        return pd.DataFrame(columns=["provider_name", "total", "avec_rapport", "inconnu"])
    df = pd.concat(parts).groupby("provider_id", as_index=False).sum()
    names = read_sql("SELECT provider_id::text AS provider_id, COALESCE(NULLIF(provider_name, ''), provider_id::text) AS provider_name FROM rex.d_prestataire")
    df = df.merge(names, on="provider_id", how="left")
    df["total"] = df["avec"] + df["sans"]
    df = df[df["total"] > 0].rename(columns={"avec": "avec_rapport"})
    return df.sort_values("total", ascending=False).head(12)[["provider_name", "total", "avec_rapport", "inconnu"]]


def reports_missing_by_metier(filters, start, end):
    cur, prev = _types(filters)
    parts = []
    for table, ok in (("rex.f_curatif_jour", cur), ("rex.f_preventif_prevu_jour", prev)):
        if ok:
            w, p = where(filters, start, end)
            parts.append(read_sql(f"SELECT COALESCE(t.metier, '{NO_TOPIC}') AS metier, SUM(nb_rapport_sans)::bigint AS n "
                                  f"FROM {table} t WHERE {w} GROUP BY 1", p))
    if not parts:
        return pd.DataFrame(columns=["metier", "n"])
    df = pd.concat(parts).groupby("metier", as_index=False).sum()
    return df[df["n"] > 0].sort_values("n", ascending=False).head(10)


def _reports_parts(filters, start, end, select, group=""):
    """Somme les compteurs de rapport des deux tables de faits (curatif + préventif) selon le type de travaux choisi."""
    cur, prev = _types(filters)
    parts = []
    for table, ok in (("rex.f_curatif_jour", cur), ("rex.f_preventif_prevu_jour", prev)):
        if ok:
            w, p = where(filters, start, end)
            parts.append(read_sql(f"SELECT {select} FROM {table} t WHERE {w}{group}", p))
    return parts


_RAP = ("SUM(nb_rapport_avec)::bigint AS avec, SUM(nb_rapport_sans)::bigint AS sans, "
        "SUM(nb_rapport_non_verifie + nb_rapport_erreur)::bigint AS inconnu")


def reports_summary(filters, start, end):
    parts = _reports_parts(filters, start, end, _RAP)
    out = {"avec": 0, "sans": 0, "inconnu": 0}
    for df in parts:
        for k in out:
            out[k] += int(df[k].fillna(0).iloc[0]) if len(df) else 0
    return out


def reports_monthly(filters, start, end):
    """Par mois : avec, sans, inconnu et taux de conformité (avec / (avec + sans))."""
    parts = _reports_parts(filters, start, end, f"date_trunc('month', t.jour)::date AS d, {_RAP}", " GROUP BY 1")
    if not parts:
        return pd.DataFrame(columns=["periode", "avec", "sans", "inconnu", "taux", "verifiees"])
    df = pd.concat(parts).groupby("d", as_index=False).sum().sort_values("d")
    df["verifiees"] = df["avec"] + df["sans"]
    df["taux"] = 100.0 * df["avec"] / df["verifiees"].where(df["verifiees"] > 0)
    df["periode"] = fr.mois(df["d"])
    return df


def reports_by(filters, start, end, dim):
    """Conformité par prestataire ou par métier : avec, sans, inconnu, vérifiées, taux. Toutes les lignes (le tri et la coupe se font à l'affichage)."""
    col = "t.provider_id::text" if dim == "prestataire" else f"COALESCE(t.metier, '{NO_TOPIC}')"
    parts = _reports_parts(filters, start, end, f"{col} AS k, {_RAP}", " GROUP BY 1")
    parts = [d for d in parts if len(d)]
    if not parts:
        return pd.DataFrame(columns=["name", "avec", "sans", "inconnu", "verifiees", "taux"])
    df = pd.concat(parts).groupby("k", as_index=False).sum()
    if dim == "prestataire":
        names = read_sql("SELECT provider_id::text AS k, COALESCE(NULLIF(provider_name, ''), provider_id::text) AS name FROM rex.d_prestataire")
        df = df.merge(names, on="k", how="left")
        df["name"] = df["name"].fillna(df["k"])
    else:
        df["name"] = df["k"]
    df["verifiees"] = df["avec"] + df["sans"]
    df = df[(df["verifiees"] > 0) | (df["inconnu"] > 0)]
    df["taux"] = 100.0 * df["avec"] / df["verifiees"].where(df["verifiees"] > 0)
    return df[["name", "avec", "sans", "inconnu", "verifiees", "taux"]]


def reports_list(filters, start, end, mode, needle, limit, offset, extra=None):
    """Interventions clôturées avec ou sans rapport. mode : Tous, Avec rapport, Sans rapport, Non vérifié."""
    w, p = where(filters, start, end, date_col="jour_creation")
    chosen = filters.get("Type de travaux") or []
    w += " AND t.status = 'closed' AND t.work_type IN ('corrective', 'preventive')"
    if chosen:
        w += " AND t.work_type = ANY(:f_wt)"
        p["f_wt"] = chosen
    if needle and needle.strip():
        w += " AND (t.reference ILIKE :nd OR t.equipment_reference ILIKE :nd OR t.programme_label ILIKE :nd)"
        p["nd"] = f"%{needle.strip()}%"
    if extra:
        w += "".join(" AND " + c for c in extra["clauses"])
        p.update(extra["params"])
    counts_df = read_sql(f"SELECT COALESCE(t.rapport_statut, 'non_verifie') AS s, COUNT(*)::bigint AS n FROM rex.f_operations t WHERE {w} GROUP BY 1", p)
    c = dict(zip(counts_df["s"], counts_df["n"]))
    counts = {"Avec rapport": int(c.get("avec", 0)), "Sans rapport": int(c.get("sans", 0)),
              "Non vérifié": int(c.get("non_verifie", 0) + c.get("erreur_api", 0))}
    counts["Tous"] = sum(counts.values())
    cond = {"Avec rapport": " AND t.rapport_statut = 'avec'", "Sans rapport": " AND t.rapport_statut = 'sans'",
            "Non vérifié": " AND COALESCE(t.rapport_statut, 'non_verifie') IN ('non_verifie', 'erreur_api')"}.get(mode, "")
    p.update({"lim": int(limit), "off": int(offset)})
    df = read_sql(f"""
        SELECT t.equipment_reference AS esi, COALESCE(t.programme_label, t.programme_reference) AS residence,
               COALESCE(t.service_label, t.reference) AS objet, t.work_type, t.metier, t.provider_name,
               COALESCE(t.event_date, t.creation_date) AS cloturee, t.rapport_statut, t.document_count, t.reference
        FROM rex.f_operations t WHERE {w}{cond}
        ORDER BY {(extra or {}).get("order") or "COALESCE(t.event_date, t.creation_date) DESC"}, t.reference LIMIT :lim OFFSET :off
    """, p)
    df["type"] = df["work_type"].map({"corrective": "Curatif", "preventive": "Préventif"})
    def etat(r):
        if r.rapport_statut == "avec":
            return f"{int(r.document_count or 0)} document(s)"
        return None if r.rapport_statut == "sans" else "À vérifier"
    df["rapport"] = [etat(r) for r in df.itertuples()]
    df["rapport_statut"] = df["rapport_statut"].fillna("non_verifie")
    return df, counts.get(mode, counts["Tous"]), counts