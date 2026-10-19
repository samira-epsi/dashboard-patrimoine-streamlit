"""Pages Prestataires et fiche prestataire sur le schéma rex."""
import pandas as pd
from database import read_sql
from services.interv import _sla_text
from services.vg import flt, where, _types, NO_TOPIC, GEO_LEVELS, status_expr

GEO = set(GEO_LEVELS)
MS_PER_HOUR = 3_600_000


def _scope(filters):
    """Source des contrats du périmètre : rex.d_contrat, ou rex.r_prestataire_programme dès qu'un filtre géographique est actif."""
    geo = any(filters.get(k) for k in GEO)
    source = "rex.r_prestataire_programme c" if geo else "rex.d_contrat c"
    clauses, params = flt({k: v for k, v in filters.items() if k != "Type de travaux"}, "c")
    clauses = ["c.provider_id IS NOT NULL", "c.contract_reference IS NOT NULL"] + clauses
    return source, clauses, params


def providers_counts(filters, start, end):
    """Interventions par prestataire : curatives créées + préventives prévues sur la période, filtres actifs."""
    cur, prev = _types(filters)
    out = {}
    if cur:
        w, p = where(filters, start, end)
        df = read_sql(f"SELECT t.provider_id::text AS pid, SUM(t.nb_operations)::bigint AS n FROM rex.f_curatif_jour t "
                      f"WHERE {w} AND t.provider_id IS NOT NULL GROUP BY 1", p)
        out = dict(zip(df["pid"], df["n"]))
    if prev:
        w, p = where(filters, start, end)
        df = read_sql(f"SELECT t.provider_id::text AS pid, SUM(t.nb_prevus)::bigint AS n FROM rex.f_preventif_prevu_jour t "
                      f"WHERE {w} AND t.provider_id IS NOT NULL GROUP BY 1", p)
        for k, v in zip(df["pid"], df["n"]):
            out[k] = out.get(k, 0) + int(v)
    return out


def providers_interventions(filters, start, end):
    return providers_counts(filters, start, end)


def providers_list(filters):
    source, clauses, params = _scope(filters)
    data = read_sql(f"""
        SELECT c.provider_id::text AS provider_id,
               COALESCE(NULLIF(MAX(p.provider_name), ''), c.provider_id::text) AS provider_name,
               COUNT(DISTINCT c.contract_reference) FILTER (WHERE c.contract_status = 'active')::bigint AS actifs,
               COUNT(DISTINCT c.contract_reference)::bigint AS total,
               ARRAY_REMOVE(ARRAY_AGG(DISTINCT NULLIF(c.metier, '{NO_TOPIC}')), NULL) AS metiers
        FROM {source} JOIN rex.d_prestataire p ON p.provider_id = c.provider_id
        WHERE {" AND ".join(clauses)}
        GROUP BY c.provider_id ORDER BY provider_name, provider_id
    """, params)
    data["hors_contrat"] = False
    data["interventions"] = 0
    # Prestataires qui ont des interventions mais aucun contrat : visibles quand aucun filtre ne les exclut.
    excluded = any(filters.get(k) for k in GEO | {"Métier", "Contrat", "Statut contrat"})
    if not excluded:
        only = filters.get("Prestataire")
        extra = read_sql("""SELECT provider_id::text AS provider_id, COALESCE(NULLIF(provider_name, ''), provider_id::text) AS provider_name,
                                   nb_interventions AS interventions
                            FROM rex.d_prestataire WHERE hors_contrat AND nb_interventions > 0""")
        if only:
            extra = extra[extra["provider_id"].isin([str(x) for x in only])]
        if len(extra):
            extra = extra.assign(actifs=0, total=0, hors_contrat=True)
            extra["metiers"] = [[] for _ in range(len(extra))]
            data = pd.concat([data, extra], ignore_index=True).sort_values(["provider_name", "provider_id"]).reset_index(drop=True)
    return data


def providers_kpis(filters):
    source, clauses, params = _scope(filters)
    k = read_sql(f"""
        SELECT COUNT(DISTINCT c.provider_id) FILTER (WHERE c.contract_status = 'active')::bigint AS prestataires,
               COUNT(DISTINCT c.contract_reference) FILTER (WHERE c.contract_status = 'active')::bigint AS contrats,
               COUNT(DISTINCT NULLIF(c.metier, '{NO_TOPIC}'))::bigint AS metiers
        FROM {source} WHERE {" AND ".join(clauses)}
    """, params).iloc[0]
    geo_source = "rex.r_prestataire_programme c"
    clauses_g = ["c.provider_id IS NOT NULL", "c.contract_reference IS NOT NULL", "c.agence_reference IS NOT NULL"]
    more, params_g = flt({k2: v for k2, v in filters.items() if k2 != "Type de travaux"}, "c")
    agences = read_sql(f"SELECT COUNT(DISTINCT c.agence_reference)::bigint AS n FROM {geo_source} "
                       f"WHERE {' AND '.join(clauses_g + more)}", params_g).iloc[0]["n"]
    return {"prestataires": int(k["prestataires"]), "contrats": int(k["contrats"]), "metiers": int(k["metiers"]),
            "agences": int(agences)}


def provider_label(provider_id):
    df = read_sql("SELECT COALESCE(NULLIF(provider_name, ''), provider_id::text) AS name FROM rex.d_prestataire WHERE provider_id::text = :pid",
                  {"pid": str(provider_id)})
    return str(df.iloc[0]["name"]) if len(df) else str(provider_id)


def _with_provider(provider_id, filters):
    return {**{k: v for k, v in (filters or {}).items() if k != "Prestataire"}, "Prestataire": [str(provider_id)]}


def provider_coverage(provider_id, filters):
    """Une ligne par (contrat, programme) : colonnes contrat, metier, statut, programme."""
    f = _with_provider(provider_id, filters)
    geo = any(f.get(k) for k in GEO)
    clauses, params = flt({k: v for k, v in f.items() if k != "Type de travaux"}, "c")
    clauses = ["c.contract_reference IS NOT NULL"] + clauses
    if geo:
        sql = f"""SELECT DISTINCT c.contract_reference AS contrat, COALESCE(c.metier, '{NO_TOPIC}') AS metier,
                         c.contract_status AS statut, c.programme_reference AS programme
                  FROM rex.r_prestataire_programme c WHERE {" AND ".join(clauses)}"""
    else:
        sql = f"""SELECT DISTINCT c.contract_reference AS contrat, COALESCE(c.metier, '{NO_TOPIC}') AS metier,
                         c.contract_status AS statut, r.programme_reference AS programme
                  FROM rex.d_contrat c LEFT JOIN rex.r_prestataire_programme r
                       ON r.contract_reference = c.contract_reference AND r.provider_id = c.provider_id
                  WHERE {" AND ".join(clauses)}"""
    return read_sql(sql, params)


def contract_details(refs):
    """Libellé, dates et statut des contrats donnés (référence)."""
    refs = [r for r in refs if r]
    if not refs:
        return pd.DataFrame(columns=["contrat", "libelle", "debut", "fin", "desactivation"])
    return read_sql("SELECT contract_reference AS contrat, contract_label AS libelle, date_debut AS debut, "
                    "date_fin AS fin, date_desactivation AS desactivation FROM rex.d_contrat "
                    "WHERE contract_reference = ANY(:r)", {"r": refs})


def housings_by_program(programmes):
    programmes = [p for p in programmes if p]
    if not programmes:
        return pd.DataFrame(columns=["programme", "logements"])
    return read_sql("SELECT programme_reference AS programme, COALESCE(nb_logements, 0)::bigint AS logements "
                    "FROM rex.d_programme WHERE programme_reference = ANY(:p)", {"p": programmes})


def provider_status(provider_id, filters, start, end):
    """Par type de travaux et statut : volume, comparables et hors délai (prise en charge et résolution)."""
    f = _with_provider(provider_id, filters)
    w, p = where(f, start, end, date_col="jour_creation")
    chosen = f.get("Type de travaux") or []
    if chosen:
        w += " AND t.work_type = ANY(:f_wt)"
        p["f_wt"] = chosen
    return read_sql(f"""
        SELECT t.work_type, {status_expr()} AS status, COUNT(*)::bigint AS n,
               COUNT(*) FILTER (WHERE t.pec_comparable)::bigint AS comp_pec,
               COUNT(*) FILTER (WHERE t.hors_delai_prise_en_charge)::bigint AS late_pec,
               COUNT(*) FILTER (WHERE t.res_comparable)::bigint AS comp_res,
               COUNT(*) FILTER (WHERE t.hors_delai_resolution)::bigint AS late_res
        FROM rex.f_operations t
        WHERE {w} AND t.work_type IN ('corrective', 'preventive')
        GROUP BY t.work_type, 2
    """, p)


def provider_prev(provider_id, filters, start, end):
    """Préventif du prestataire sur la période (date prévue) : prévus, réalisés, en retard."""
    w, p = where(_with_provider(provider_id, filters), start, end)
    return read_sql(f"""
        SELECT COALESCE(SUM(nb_prevus),0)::bigint AS prevus, COALESCE(SUM(nb_realises),0)::bigint AS realises,
               COALESCE(SUM(nb_realises_en_retard),0)::bigint AS realises_en_retard,
               COALESCE(SUM(nb_actuellement_en_retard),0)::bigint AS en_retard,
               COALESCE(SUM(nb_prevus) FILTER (WHERE date_source = 'creation_par_defaut'),0)::bigint AS date_defaut
        FROM rex.f_preventif_prevu_jour t WHERE {w}
    """, p).iloc[0]


def provider_delays(provider_id, filters, start, end):
    """Délais moyens (heures) des curatives du prestataire. Les durées à 0, -1 ou absentes sont exclues."""
    w, p = where(_with_provider(provider_id, filters), start, end, date_col="jour_creation")
    row = read_sql(f"""
        SELECT AVG(t.response_time) FILTER (WHERE t.response_time > 0) / {MS_PER_HOUR}.0 AS pec,
               AVG(t.resolution_duration) FILTER (WHERE t.resolution_duration > 0) / {MS_PER_HOUR}.0 AS res
        FROM rex.f_operations t WHERE {w} AND t.perimetre_curatif
    """, p).iloc[0]
    return (float(row["pec"]) if pd.notna(row["pec"]) else None, float(row["res"]) if pd.notna(row["res"]) else None)


def provider_equipments(provider_id, filters):
    """Équipements distincts du prestataire (toutes ses interventions, curatives et préventives, filtres patrimoine),
    et nombre d'interventions sans équipement."""
    f = _with_provider(provider_id, {k: v for k, v in (filters or {}).items() if k in GEO})
    clauses, params = flt(f, "t")
    r = read_sql(f"""
        SELECT COUNT(DISTINCT t.equipment_reference)::bigint AS equipements,
               COUNT(*) FILTER (WHERE t.equipment_reference IS NULL)::bigint AS sans_equipement,
               COUNT(*)::bigint AS interventions
        FROM rex.f_operations t WHERE {' AND '.join(clauses)} AND t.work_type IN ('corrective', 'preventive')
    """, params).iloc[0]
    return {"equipements": int(r["equipements"]), "sans_equipement": int(r["sans_equipement"]), "interventions": int(r["interventions"])}


def provider_equipment_list(provider_id, filters, start, end, limit=15):
    """Équipements concernés par les interventions du prestataire sur la période : volumes et dernière intervention."""
    w, p = where(_with_provider(provider_id, filters), start, end, date_col="jour_creation")
    p["lim"] = int(limit)
    return read_sql(f"""
        SELECT t.equipment_reference AS equipement, MAX(e.equipment_label) AS libelle, MAX(e.equipment_type) AS type,
               COUNT(*) FILTER (WHERE t.work_type = 'corrective')::bigint AS curatives,
               COUNT(*) FILTER (WHERE t.work_type = 'preventive')::bigint AS preventives,
               MAX(t.creation_date) AS derniere
        FROM rex.f_operations t LEFT JOIN rex.d_equipement e ON e.equipment_reference = t.equipment_reference
        WHERE {w} AND t.equipment_reference IS NOT NULL AND t.work_type IN ('corrective', 'preventive')
        GROUP BY t.equipment_reference ORDER BY COUNT(*) DESC, t.equipment_reference LIMIT :lim
    """, p)


def _pi_where(provider_id, filters, start, end, category, status, needle, equip, extra):
    w, p = where(_with_provider(provider_id, filters), start, end, date_col="jour_creation")
    w += " AND t.work_type IN ('corrective', 'preventive')"
    if category in ("corrective", "preventive"):
        w += " AND t.work_type = :wt"
        p["wt"] = category
    if status:
        w += f" AND {status_expr()} = :st"
        p["st"] = status
    if equip == "Avec équipement":
        w += " AND t.equipment_reference IS NOT NULL"
    elif equip == "Sans équipement":
        w += " AND t.equipment_reference IS NULL"
    if needle and needle.strip():
        w += " AND (t.reference ILIKE :nd OR t.equipment_reference ILIKE :nd OR t.contract_reference ILIKE :nd)"
        p["nd"] = f"%{needle.strip()}%"
    if extra:
        w += "".join(" AND " + c for c in extra["clauses"])
        p.update(extra["params"])
    return w, p


def provider_interventions_total(provider_id, filters, start, end, category=None, status=None, needle=None, equip=None, extra=None):
    w, p = _pi_where(provider_id, filters, start, end, category, status, needle, equip, extra)
    return int(read_sql(f"SELECT COUNT(*)::bigint AS n FROM rex.f_operations t WHERE {w}", p).iloc[0]["n"])


def provider_interventions(provider_id, filters, start, end, category=None, status=None, needle=None, limit=10, offset=0, equip=None, extra=None):
    w, p = _pi_where(provider_id, filters, start, end, category, status, needle, equip, extra)
    p.update({"lim": int(limit), "off": int(offset)})
    df = read_sql(f"""
        SELECT t.reference, t.equipment_reference, {status_expr()} AS status, t.work_type, t.creation_date, t.metier AS contract_topic,
               t.contract_reference, t.type_fin, COALESCE(t.motif_cloture, t.motif_annulation) AS motif, t.technical_reason AS cause,
               CASE WHEN t.response_time > 0 THEN t.response_time / {MS_PER_HOUR}.0 END AS pec_heures,
               CASE WHEN t.resolution_duration > 0 THEN t.resolution_duration / {MS_PER_HOUR}.0 END AS res_heures,
               t.sla_intervention_value, t.sla_intervention_unit, t.sla_recovery_value, t.sla_recovery_unit,
               t.hors_delai_prise_en_charge AS late_pec, t.hors_delai_resolution AS late_res,
               CASE WHEN t.hors_delai_global THEN 'late'
                    WHEN t.global_comparable THEN 'ok' END AS late_flag
        FROM rex.f_operations t WHERE {w}
        ORDER BY {(extra or {}).get("order") or "t.creation_date DESC"}, t.reference
        LIMIT :lim OFFSET :off
    """, p)
    df["pec_heures"] = df["pec_heures"].astype(float)
    df["res_heures"] = df["res_heures"].astype(float)
    df["sla_pec"] = [_sla_text(a, b) for a, b in zip(df["sla_intervention_value"], df["sla_intervention_unit"])]
    df["sla_res"] = [_sla_text(a, b) for a, b in zip(df["sla_recovery_value"], df["sla_recovery_unit"])]
    return df