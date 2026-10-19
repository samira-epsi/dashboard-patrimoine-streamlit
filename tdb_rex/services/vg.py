"""Vue globale sur le schéma rex (tables légères, une requête = un GROUP BY sur une petite table).
Chaque filtre est une colonne des tables de faits : aucun sous-select, aucune jointure de filtrage."""
from datetime import date
import pandas as pd
from database import read_sql

NO_TOPIC = "Non renseigné"
SANS = "__sans__"  # valeur technique de l'entrée « Sans agence » (interventions dont l'agence est vide)
LIB_SANS = "Sans agence"


def status_expr(alias="t"):
    """Statut affiché : denied est scindé en annulée (event canceled) et refusée (non_contractual, unable)."""
    return f"CASE WHEN {alias}.status = 'denied' AND {alias}.type_fin = 'canceled' THEN 'canceled' ELSE {alias}.status END"
STATUS_LABEL = "Statut contrat"
STATUS_VALUES = {"Actifs": ["active"], "Inactifs": ["inactive"]}
GEO_LEVELS = {  # libellé -> (colonne référence, colonne libellé dans rex.d_programme)
    "Société": ("societe_reference", "societe_label"),
    "Agence": ("agence_reference", "agence_label"),
    "Groupe": ("groupe_reference", "groupe_label"),
    "Secteur": ("secteur_reference", "secteur_label"),
    "Programme": ("programme_reference", "programme_label"),
}
COLUMN = {**{k: v[0] for k, v in GEO_LEVELS.items()},
          "Prestataire": "provider_id", "Contrat": "contract_reference"}
TYPES = {"corrective": "Curatif", "preventive": "Préventif"}


_AG_SQL = """SELECT agence_reference::text AS reference, MAX(agence_label) AS libelle
        FROM rex.d_programme WHERE agence_reference IS NOT NULL GROUP BY agence_reference"""  # repli rapide, sans la table d_agence


def _existe(table):
    """True si la petite table de filtres existe (script sql/rex/25_filtres.sql) ; sinon on retombe sur l'ancien calcul, plus lent."""
    try:
        return bool(read_sql("SELECT to_regclass(:t) IS NOT NULL AS ok", {"t": table}).iloc[0]["ok"])
    except Exception:
        return False


def _ag_sql():
    if _existe("rex.d_agence"):
        return "SELECT agence_reference::text AS reference, agence_label AS libelle FROM rex.d_agence"
    return _AG_SQL


def agences_ref():
    """Référentiel des agences : une ligne par CODE (la référence fait foi), avec son libellé le plus fréquent."""
    d = read_sql(_ag_sql() + " ORDER BY 2, 1")
    d["libelle"] = d["libelle"].fillna(d["reference"]).astype(str).str.strip()
    return d


def _desambiguer(out):
    """Deux entrées de même libellé ne se distinguent pas à l'écran : on ajoute leur référence."""
    double = out["libelle"].str.casefold().duplicated(keep=False)
    out.loc[double, "libelle"] = out.loc[double, "libelle"] + " (" + out.loc[double, "reference"] + ")"
    return out


def _end(end):
    return pd.Timestamp(end).date() + pd.Timedelta(days=1)


def flt(filters, alias="t"):
    """Clauses de filtre (sans date) valables sur toute table rex qui porte ces colonnes."""
    clauses, params = [], {}
    for label, selected in filters.items():
        if not selected:
            continue
        if label == STATUS_LABEL:
            clauses.append(f"{alias}.contract_status = ANY(:f_status)")
            params["f_status"] = selected
        elif label == "Métier":
            clauses.append(f"COALESCE({alias}.metier, '{NO_TOPIC}') = ANY(:f_metier)")
            params["f_metier"] = selected
        elif label in COLUMN:
            col = COLUMN[label]
            key = "f_" + col
            if label == "Agence" and SANS in selected:  # « Sans agence » : agence vide, avec ou sans autres agences cochées
                clauses.append(f"({alias}.{col} IS NULL OR {alias}.{col}::text = ANY(:{key}))")
                params[key] = [v for v in selected if v != SANS]
            else:
                clauses.append(f"{alias}.{col}::text = ANY(:{key})")
                params[key] = selected
    return clauses, params


def where(filters, start, end, alias="t", date_col="jour", with_type=True):
    """Clause WHERE commune. 'Type de travaux' : géré à part (_types), car il décide quelles tables interroger."""
    clauses, params = flt(filters, alias)
    clauses = [f"{alias}.{date_col} >= :date_start", f"{alias}.{date_col} < :date_end"] + clauses
    params.update({"date_start": start, "date_end": _end(end)})
    return " AND ".join(clauses), params


def _types(filters):
    chosen = filters.get("Type de travaux") or []
    return (not chosen or "corrective" in chosen), (not chosen or "preventive" in chosen)


def total_history():
    return int(read_sql("SELECT reltuples::bigint AS n FROM pg_class WHERE oid = 'rex.f_operations'::regclass").iloc[0]["n"])


def bounds():
    return read_sql("SELECT MIN(jour)::date AS debut, MAX(jour)::date AS fin FROM rex.f_curatif_jour")


def options(label, filters, start, end):
    """Options d'un filtre, croisées avec les autres filtres, depuis rex.r_prestataire_programme (contrat x programme)
    complété par les prestataires et programmes qui n'ont pas de relation (hors contrat)."""
    if label == "Type de travaux":
        return pd.DataFrame({"reference": list(TYPES), "libelle": list(TYPES.values())})
    others = {k: v for k, v in filters.items() if v and k != label and k != "Type de travaux"}
    if others and _existe("rex.f_filtres"):  # croisement complet (petite table rex.f_filtres, voir sql/rex/25_filtres.sql)
        return _options_faits(label, filters, others)
    clauses, params = [], {}
    for k, sel in others.items():
        if k == STATUS_LABEL:
            clauses.append("r.contract_status = ANY(:f_status)"); params["f_status"] = sel
        elif k == "Métier":
            clauses.append(f"COALESCE(r.metier, '{NO_TOPIC}') = ANY(:f_metier)"); params["f_metier"] = sel
        elif k in COLUMN:
            sel = [v for v in sel if v != SANS]
            if not sel:
                continue
            clauses.append(f"r.{COLUMN[k]}::text = ANY(:f_{COLUMN[k]})"); params["f_" + COLUMN[k]] = sel
    cond = (" AND " + " AND ".join(clauses)) if clauses else ""
    if label in GEO_LEVELS:
        ref, name = GEO_LEVELS[label]
        src = "rex.r_prestataire_programme r" + (" JOIN rex.d_programme dp USING (programme_reference)" if label == "Programme" else "")
        lab = f"MAX(dp.{name})" if label == "Programme" else f"MAX(r.{name})"
        sql = f"""SELECT r.{ref}::text AS reference, COALESCE(NULLIF({lab}, ''), r.{ref}::text) AS libelle
                  FROM {src} WHERE r.{ref} IS NOT NULL{cond}
                  GROUP BY r.{ref} ORDER BY libelle, reference"""
        if not clauses:  # sans autre filtre : tous les programmes du référentiel
            d = ref.replace("_reference", "")
            sql = f"""SELECT {ref}::text AS reference, COALESCE(NULLIF(MAX({name}), ''), {ref}::text) AS libelle
                      FROM rex.d_programme WHERE {ref} IS NOT NULL GROUP BY {ref} ORDER BY libelle, reference"""
        if label == "Agence":  # une entrée par code agence (référence), pas par libellé
            sql = f"""SELECT a.reference, a.libelle FROM ({" ".join(_ag_sql().split())}) a""" + (
                f""" WHERE a.reference IN (SELECT DISTINCT r.agence_reference::text FROM rex.r_prestataire_programme r
                     WHERE r.agence_reference IS NOT NULL{cond})""" if clauses else "") + " ORDER BY a.libelle, a.reference"
    elif label == "Prestataire":
        if clauses:
            sql = f"""SELECT r.provider_id::text AS reference, MAX(p.provider_name) AS libelle
                      FROM rex.r_prestataire_programme r JOIN rex.d_prestataire p USING (provider_id)
                      WHERE r.provider_id IS NOT NULL{cond} GROUP BY r.provider_id ORDER BY libelle, reference"""
        else:
            sql = """SELECT provider_id::text AS reference, COALESCE(NULLIF(provider_name, ''), provider_id::text) AS libelle
                     FROM rex.d_prestataire ORDER BY libelle, reference"""
    elif label == "Contrat":
        sql = f"""SELECT r.contract_reference::text AS reference, COALESCE(NULLIF(MAX(c.contract_label), ''), r.contract_reference::text) AS libelle
                  FROM rex.r_prestataire_programme r JOIN rex.d_contrat c USING (contract_reference)
                  WHERE r.contract_reference IS NOT NULL{cond} GROUP BY r.contract_reference ORDER BY libelle, reference"""
        if not clauses:
            sql = """SELECT contract_reference::text AS reference, COALESCE(NULLIF(contract_label, ''), contract_reference::text) AS libelle
                     FROM rex.d_contrat ORDER BY libelle, reference"""
    else:  # Métier
        sql = f"""SELECT COALESCE(r.metier, '{NO_TOPIC}') AS reference, COALESCE(r.metier, '{NO_TOPIC}') AS libelle
                  FROM rex.r_prestataire_programme r WHERE TRUE{cond}
                  GROUP BY 1 ORDER BY (COALESCE(r.metier, '{NO_TOPIC}') = '{NO_TOPIC}'), 1"""
        if not clauses:
            sql = f"""SELECT COALESCE(metier, '{NO_TOPIC}') AS reference, COALESCE(metier, '{NO_TOPIC}') AS libelle
                      FROM rex.d_contrat GROUP BY 1 ORDER BY (COALESCE(metier, '{NO_TOPIC}') = '{NO_TOPIC}'), 1"""
    out = read_sql(sql, params)
    out["reference"] = out["reference"].astype(str)
    out["libelle"] = out["libelle"].fillna(out["reference"]).astype(str).str.strip()
    if label == "Contrat":  # « référence / nom du contrat » : la recherche du filtre trouve l'un comme l'autre
        out["libelle"] = [r if (not n or n == r) else f"{r} / {n}" for r, n in zip(out["reference"], out["libelle"])]
    else:
        out = _desambiguer(out)
    if label == "Agence" and SANS not in set(out["reference"]):  # entrée finale : interventions sans agence
        out = pd.concat([out, pd.DataFrame({"reference": [SANS], "libelle": [LIB_SANS]})], ignore_index=True)
    return out


def _options_faits(label, filters, others):
    """Options d'un filtre quand d'autres filtres sont actifs : valeurs réellement présentes dans les mêmes tables de faits
    que les chiffres (curatif et/ou préventif selon le type de travaux), avec les mêmes règles de filtre.
    Une intervention sans agence peut avoir une société : choisir « Sans agence » réduit bien les autres listes."""
    cur, prev = _types(filters)
    clauses, params = flt(others, "t")
    cond = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    if label == "Métier":
        expr = f"COALESCE(t.metier, '{NO_TOPIC}')"
    elif label == "Agence":
        expr = f"COALESCE(t.agence_reference::text, '{SANS}')"
    else:
        expr = f"t.{COLUMN[label]}::text"
    chosen = filters.get("Type de travaux") or []
    if chosen:
        clauses.append("t.work_type = ANY(:f_wt)")
        params["f_wt"] = chosen
    cond = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    vals = f"SELECT DISTINCT {expr} AS reference FROM rex.f_filtres t{cond}"
    if label == "Agence":
        lab = _ag_sql()
    elif label in GEO_LEVELS:
        ref, name = GEO_LEVELS[label]
        lab = f"SELECT {ref}::text AS reference, MAX({name}) AS libelle FROM rex.d_programme WHERE {ref} IS NOT NULL GROUP BY {ref}"
    elif label == "Prestataire":
        lab = "SELECT provider_id::text AS reference, MAX(provider_name) AS libelle FROM rex.d_prestataire GROUP BY provider_id"
    elif label == "Contrat":
        lab = "SELECT contract_reference::text AS reference, MAX(contract_label) AS libelle FROM rex.d_contrat GROUP BY contract_reference"
    else:
        lab = "SELECT NULL::text AS reference, NULL::text AS libelle WHERE FALSE"
    out = read_sql(f"""SELECT r.reference, COALESCE(NULLIF(l.libelle, ''), r.reference) AS libelle
                       FROM ({vals}) r LEFT JOIN ({" ".join(lab.split())}) l USING (reference)
                       WHERE r.reference IS NOT NULL ORDER BY libelle, reference""", params)
    out["reference"] = out["reference"].astype(str)
    out["libelle"] = out["libelle"].fillna(out["reference"]).astype(str).str.strip()
    if label == "Contrat":
        out["libelle"] = [r if (not n or n == r) else f"{r} / {n}" for r, n in zip(out["reference"], out["libelle"])]
    else:
        out.loc[out["reference"] == SANS, "libelle"] = LIB_SANS
        out = _desambiguer(out)
    return out


def global_kpis(filters, start, end):
    cur, prev = _types(filters)
    w, p = where(filters, start, end)
    k = read_sql(f"""
        SELECT COALESCE(SUM(nb_operations),0)::bigint            AS curatives,
               COALESCE(SUM(nb_pec_comparables),0)::bigint       AS comparables_pec,
               COALESCE(SUM(nb_pec_hors_delai),0)::bigint        AS hors_delai_pec,
               COALESCE(SUM(nb_res_comparables),0)::bigint       AS comparables_resolution,
               COALESCE(SUM(nb_res_hors_delai),0)::bigint        AS hors_delai_resolution,
               COALESCE(SUM(nb_sans_sla_intervention) FILTER (WHERE status <> 'denied'),0)::bigint AS sans_sla,
               COALESCE(SUM(nb_pec_duree_nulle + nb_pec_duree_moins1),0)::bigint AS pec_inexploitable,
               COALESCE(SUM(nb_pec_duree_zero),0)::bigint        AS pec_zero,
               COALESCE(SUM(nb_pec_comparables_mois),0)::bigint  AS pec_mois,
               COALESCE(SUM(nb_operations) FILTER (WHERE status <> 'denied'),0)::bigint AS curatives_hors_refus,
               COALESCE(SUM(nb_annulees),0)::bigint              AS annulees,
               COALESCE(SUM(nb_operations) FILTER (WHERE status IN ('open','pending','hold')),0)::bigint AS actives,
               COALESCE(SUM(nb_rapport_avec),0)::bigint AS c_rapport_avec, COALESCE(SUM(nb_rapport_sans),0)::bigint AS c_rapport_sans,
               COALESCE(SUM(nb_rapport_non_verifie + nb_rapport_erreur),0)::bigint AS c_rapport_inconnu,
               COALESCE(SUM(nb_annulees + nb_refusees_autres),0)::bigint AS annul_refus
        FROM rex.f_curatif_jour t WHERE {w}
    """, p).iloc[0].to_dict() if cur else {}
    pw, pp = where(filters, start, end)
    pv = read_sql(f"""
        SELECT COALESCE(SUM(nb_prevus),0)::bigint AS prevus, COALESCE(SUM(nb_realises),0)::bigint AS realises,
               COALESCE(SUM(nb_realises_en_retard),0)::bigint AS realises_en_retard,
               COALESCE(SUM(nb_realises_dans_delai),0)::bigint AS realises_dans_delai,
               COALESCE(SUM(nb_actuellement_en_retard),0)::bigint AS en_retard,
               COALESCE(SUM(nb_prevus) FILTER (WHERE date_source = 'creation_par_defaut'),0)::bigint AS prevus_date_defaut,
               COALESCE(SUM(nb_rapport_avec),0)::bigint AS rapport_avec, COALESCE(SUM(nb_rapport_sans),0)::bigint AS rapport_sans,
               COALESCE(SUM(nb_rapport_non_verifie + nb_rapport_erreur),0)::bigint AS rapport_inconnu
        FROM rex.f_preventif_prevu_jour t WHERE {pw}
    """, pp).iloc[0].to_dict() if prev else {}
    keys = ["curatives", "comparables_pec", "hors_delai_pec", "comparables_resolution", "hors_delai_resolution",
            "sans_sla", "pec_inexploitable", "pec_zero", "pec_mois", "curatives_hors_refus", "annulees", "actives", "annul_refus", "c_rapport_avec", "c_rapport_sans", "c_rapport_inconnu"]
    pkeys = ["prevus", "realises", "realises_en_retard", "realises_dans_delai", "en_retard", "prevus_date_defaut",
             "rapport_avec", "rapport_sans", "rapport_inconnu"]
    out = {key: int(k.get(key, 0) or 0) for key in keys}
    out.update({key: int(pv.get(key, 0) or 0) for key in pkeys})
    for key in ("avec", "sans", "inconnu"):  # rapports : curatives et préventives, comme la page Qualité des rapports
        out[f"rapport_{key}"] = out[f"rapport_{key}"] + out.pop(f"c_rapport_{key}")
    out["total_operations"] = out["curatives"] + out["prevus"]
    return pd.Series(out)


def trend(filters, start, end, granularity):
    """Série par mois ou par année : numérateurs et dénominateurs de tous les indicateurs de performance (les taux sont calculés à l'affichage)."""
    cur, prev = _types(filters)
    grain = "month" if granularity == "Mensuel" else "year"
    w, p = where(filters, start, end)
    frames = []
    if cur:
        frames.append(read_sql(f"""
            SELECT date_trunc('{grain}', t.jour)::date AS periode,
                   SUM(nb_pec_comparables)::bigint AS comparables, SUM(nb_pec_hors_delai)::bigint AS hors_delai,
                   SUM(nb_res_comparables)::bigint AS res_comparables, SUM(nb_res_hors_delai)::bigint AS res_hors_delai,
                   SUM(nb_rapport_avec)::bigint AS rap_avec, SUM(nb_rapport_sans)::bigint AS rap_sans
            FROM rex.f_curatif_jour t WHERE {w} GROUP BY 1
        """, p))
    if prev:
        frames.append(read_sql(f"""
            SELECT date_trunc('{grain}', t.jour)::date AS periode,
                   SUM(nb_prevus)::bigint AS prevus, SUM(nb_realises)::bigint AS realises,
                   SUM(nb_cloturees_non_realisees + nb_actuellement_en_retard)::bigint AS non_realises,
                   SUM(nb_realises_en_retard + nb_actuellement_en_retard)::bigint AS retard,
                   SUM(nb_realises_dans_delai + nb_realises_en_retard + nb_actuellement_en_retard)::bigint AS jugeables,
                   SUM(nb_rapport_avec)::bigint AS rap_avec, SUM(nb_rapport_sans)::bigint AS rap_sans
            FROM rex.f_preventif_prevu_jour t WHERE {w} GROUP BY 1
        """, p))
    if not frames:
        return pd.DataFrame(columns=["periode"])
    df = pd.concat(frames).groupby("periode", as_index=False).sum().sort_values("periode").reset_index(drop=True)
    return df


def zones(filters, start, end, level="Agence", limit=200, descending=True):
    ref, name = GEO_LEVELS[level]
    cur, _ = _types(filters)
    if not cur:
        return pd.DataFrame(columns=["reference", "libelle", "nb_pannes", "total_pannes"]), None
    w, p = where(filters, start, end)
    p["limit"] = limit
    direction = "DESC" if descending else "ASC"
    agence = level == "Agence"  # les interventions sans agence forment une ligne « Sans agence » au lieu de disparaître
    grp = f"COALESCE(t.{ref}::text, '{SANS}')" if agence else f"t.{ref}::text"
    notnull = "" if agence else f" AND t.{ref} IS NOT NULL"
    df = read_sql(f"""
        WITH agg AS (
            SELECT {grp} AS reference, SUM(t.nb_operations)::bigint AS nb_pannes
            FROM rex.f_curatif_jour t
            WHERE {w} AND t.status <> 'denied'{notnull}
            GROUP BY {grp}
        ), lab AS (
            SELECT {ref}::text AS reference, MAX({name}) AS libelle FROM rex.d_programme WHERE {ref} IS NOT NULL GROUP BY {ref}
        )
        SELECT a.reference, COALESCE(NULLIF(l.libelle, ''), a.reference) AS libelle, a.nb_pannes,
               SUM(a.nb_pannes) OVER ()::bigint AS total_pannes
        FROM agg a LEFT JOIN lab l USING (reference)
        ORDER BY nb_pannes {direction}, libelle LIMIT :limit
    """, p)
    if agence and len(df):  # libellé = le plus fréquent du code ; « Sans agence » ; codes ajoutés si deux libellés sont identiques
        m = dict(zip(*[agences_ref()[c] for c in ("reference", "libelle")]))
        m[SANS] = LIB_SANS
        df["libelle"] = [m.get(r, l) for r, l in zip(df["reference"], df["libelle"])]
        df = _desambiguer(df)
    return df, None


def equipments(filters, start, end, limit=50, descending=True):
    cur, _ = _types(filters)
    if not cur:
        return pd.DataFrame(columns=["equipment_reference", "nb_pannes", "derniere_panne"]), None
    w, p = where(filters, start, end)
    p["limit"] = limit
    direction = "DESC" if descending else "ASC"
    df = read_sql(f"""
        SELECT t.equipment_reference, SUM(t.nb_pannes)::bigint AS nb_pannes, MAX(t.derniere_panne) AS derniere_panne
        FROM rex.f_equipement_jour t WHERE {w}
        GROUP BY t.equipment_reference
        ORDER BY nb_pannes {direction}, equipment_reference LIMIT :limit
    """, p)
    return df, None


def equipment_context(refs, start, end):
    if not refs:
        return pd.DataFrame(columns=["equipment_reference", "provider_name", "programme_reference", "agence_label"])
    return read_sql("""
        SELECT equipment_reference, provider_name, programme_reference, agence_label,
               equipment_label, equipment_type
        FROM rex.d_equipement WHERE equipment_reference = ANY(:refs)
    """, {"refs": list(refs)})


def _details_where(filters, start, end, category, needle, extra=None):
    w, p = where(filters, start, end, date_col="jour_creation")
    if extra:
        w += "".join(" AND " + c for c in extra["clauses"])
        p.update(extra["params"])
    if category == "PEC hors délai":
        w += " AND t.hors_delai_prise_en_charge IS TRUE"
    elif category == "Sans équipement":
        w += " AND t.equipment_reference IS NULL"
    if needle and needle.strip():
        w += " AND (t.reference ILIKE :needle OR t.equipment_reference ILIKE :needle OR t.contract_reference ILIKE :needle)"
        p["needle"] = "%" + needle.strip().replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"
    chosen = filters.get("Type de travaux") or []
    w += " AND t.work_type IN ('corrective', 'preventive')"
    if chosen:
        w += " AND t.work_type = ANY(:f_wt)"
        p["f_wt"] = chosen
    return w, p


def details(filters, start, end, category="Toutes", limit=100, offset=0, needle=None, extra=None):
    """Liste des interventions (référence en premier). category : Toutes, PEC hors délai, Sans équipement."""
    w, p = _details_where(filters, start, end, category, needle, extra)
    p.update({"page_limit": int(limit), "page_offset": int(offset)})
    return read_sql(f"""
        SELECT t.reference, t.work_type, {status_expr()} AS status, t.creation_date, t.equipment_reference,
               e.equipment_label, t.provider_name, t.contract_reference, t.metier, t.agence_label, t.programme_reference,
               t.sla_intervention_value, t.sla_intervention_unit, t.sla_recovery_value, t.sla_recovery_unit,
               CASE WHEN t.response_time > 0 THEN t.response_time / 3600000.0 END AS pec_heures,
               CASE WHEN t.resolution_duration > 0 THEN t.resolution_duration / 3600000.0 END AS res_heures,
               CASE WHEN t.hors_delai_global THEN 'Hors délai' WHEN t.global_comparable THEN 'Dans les délais' END AS delai,
               t.type_fin, COALESCE(t.motif_cloture, t.motif_annulation) AS motif
        FROM rex.f_operations t LEFT JOIN rex.d_equipement e ON e.equipment_reference = t.equipment_reference
        WHERE {w}
        ORDER BY {(extra or {}).get("order") or "t.creation_date DESC NULLS LAST"}, t.reference
        LIMIT :page_limit OFFSET :page_offset
    """, p), None


def details_total(filters, start, end, category="Toutes", needle=None, extra=None):
    w, p = _details_where(filters, start, end, category, needle, extra)
    return int(read_sql(f"SELECT COUNT(*)::bigint AS n FROM rex.f_operations t WHERE {w}", p).iloc[0]["n"])