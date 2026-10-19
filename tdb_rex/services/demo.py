"""Mode démonstration : données fictives, aucune connexion PostgreSQL.
Chaque requête SQL de services/queries.py est reconnue par un fragment de son texte, puis remplacée par un résultat fictif
cohérent (mêmes prestataires dans la liste, les filtres et la fiche). Actif avec la variable d'environnement REX_DEMO=1."""
from datetime import date, timedelta
import zlib

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
TODAY = date.today()

METIERS = ["Chauffage collectif", "Chauffage individuel", "Ascenseur", "Ventilation", "Plomberie", "Espaces verts",
           "Portes automatiques", "Sécurité incendie", "Comptage d'eau", "Assainissement", "Multi technique", "3D",
           "Électricité", "Nettoyage", "Désenfumage", "Robinetterie", "Interphonie"]
NAMES = ["ISERBA", "KONE", "OTIS", "ISTA FRANCE", "IDVERDE", "ORTEC", "VEOLIA EAU", "DALKIA", "CHUBB", "ENGIE Solutions",
         "SCHINDLER", "THYSSENKRUPP", "ELIOR Services", "ONET", "ATALIAN Propreté", "SPIE Facilities", "VINCI Facilities",
         "COFELY", "NOVEO", "ACORUS", "ACE", "ADI", "AED", "CONFOGAZ", "DEKRA", "MICROMATIX", "OMS Synergie", "CHRISTAL",
         "TECHNIFLUIDE", "SOGEA", "RAMERY Services", "HOMETECH", "SERVAL", "CLAIRIS", "BRUNET", "FIDUCIAL", "PROXISERVE",
         "TERIDEAL", "SEMERU", "GIRARD Énergies"]
PROVIDERS = []
for i, n in enumerate(NAMES):
    k = int(rng.integers(1, 4))
    PROVIDERS.append({"id": f"6{i:02d}a1b2c3d4e5f6a7b8c9d", "name": n,
                      "metiers": list(rng.choice(METIERS, size=k, replace=False)),
                      "contrats": int(rng.integers(1, 15))})
PROVIDERS[0]["metiers"] = ["Chauffage collectif", "Ventilation", "Plomberie"]
PROVIDERS[0]["contrats"] = 17
OUTSIDE = [{"id": "5a2942cfd207720cf70b6796", "name": "3F Groupe Action Logement", "interv": 132567},
           {"id": "61781352fafdb35c248750ff", "name": "Vinci Facilities (hors contrat)", "interv": 2}]
BY_ID = {p["id"]: p for p in PROVIDERS}
NAME_OF = {**{p["id"]: p["name"] for p in PROVIDERS}, **{o["id"]: o["name"] for o in OUTSIDE}}
AGENCES = [("A7", "Lyon 7", 34), ("A8", "Lyon 8", 27), ("A6", "Lyon 6", 21), ("AV", "Villeurbanne", 15), ("AX", "Vénissieux", 11)]
AGENCES += [(f"A{i}", f"Agence {i}", int(rng.integers(1, 10))) for i in range(10, 38)]
EQ = [("Chaudière n°2", 13), ("VMC - bâtiment A", 11), ("Ascenseur n°4", 9), ("Colonne d'eau C", 9), ("Chaudière n°1", 8), ("Ascenseur n°1", 7)]
EQ += [(f"EQ-{1000 + i}", int(rng.integers(1, 7))) for i in range(40)]


def _seed(pid):
    return zlib.crc32(str(pid).encode())


def _pid(params):
    value = (params or {}).get("pid") or ((params or {}).get("f_provider_id") or [None])[0]
    return value


def fake(sql, params=None):
    s = " ".join(sql.split())
    p = params or {}

    # ---- fiche prestataire
    if "AS name FROM public.contracts_current" in s:
        return pd.DataFrame({"name": [NAME_OF.get(p.get("pid"), p.get("pid"))]})
    if "SELECT MAX(t.provider_name::text) AS name" in s:
        return pd.DataFrame({"name": [NAME_OF.get(p.get("pid"))]})
    if "SELECT DISTINCT c.reference AS contrat" in s:
        pid = _pid(p)
        prov = BY_ID.get(pid)
        if not prov:
            return pd.DataFrame(columns=["contrat", "metier", "statut", "programme"])
        r = np.random.default_rng(_seed(pid))
        rows = []
        for k in range(prov["contrats"]):
            metier = prov["metiers"][k % len(prov["metiers"])]
            statut = "active" if r.random() < .82 else "inactive"
            for j in range(int(r.integers(2, 40))):
                rows.append((f"C-{pid[:3]}-{k:02d}", metier, statut, f"PRG{_seed(f'{pid}{k}{j}') % 9000:04d}"))
        return pd.DataFrame(rows, columns=["contrat", "metier", "statut", "programme"]).drop_duplicates()
    if "vw_housing_hierarchy" in s:
        progs = p["progs"]
        return pd.DataFrame({"programme": progs, "logements": [int(30 + _seed(x) % 90) for x in progs]})
    if "AS late_pec" in s:
        r = np.random.default_rng(_seed(_pid(p) or "x"))
        scale = float(r.uniform(.3, 2.2))
        def row(wt, st_, n, rate=0.0):
            n = int(n * scale)
            comp = int(n * .95) if wt == "corrective" and st_ != "cancelled" else 0
            late = int(comp * rate)
            return (wt, st_, n, comp if st_ != "closed" else 0, late if st_ != "closed" else 0,
                    comp if st_ == "closed" else 0, late if st_ == "closed" else 0)
        rows = [row("corrective", "pending", 16, .30), row("corrective", "open", 38, .22), row("corrective", "in_progress", 41, .17),
                row("corrective", "closed", 1116, .22), row("corrective", "cancelled", 33),
                row("preventive", "scheduled", 31), row("preventive", "in_progress", 14), row("preventive", "pending", 10),
                row("preventive", "closed", 93), row("preventive", "cancelled", 2)]
        return pd.DataFrame(rows, columns=["work_type", "status", "n", "comp_pec", "late_pec", "comp_res", "late_res"])
    if "AS n_interventions" in s:
        ids = [pr["id"] for pr in PROVIDERS] + [o["id"] for o in OUTSIDE]
        vals = [int(40 + _seed(i) % 2400) for i in ids[:-len(OUTSIDE)]] + [o["interv"] for o in OUTSIDE]
        return pd.DataFrame({"provider_id": ids, "n_interventions": vals})
    if "AS late_flag" in s:
        r = np.random.default_rng(_seed(f"{_pid(p)}{p.get('off', 0)}{p.get('wt')}{p.get('st')}"))
        n = int(p.get("lim", 10))
        wts = [p["wt"]] * n if p.get("wt") else list(r.choice(["corrective", "preventive"], size=n))
        sts = [p["st"]] * n if p.get("st") else list(r.choice(["pending", "open", "in_progress", "closed", "closed", "scheduled", "cancelled"], size=n))
        base = pd.Timestamp(TODAY) - pd.Timedelta(days=int(p.get("off", 0)) // 3)
        rows = []
        for i in range(n):
            wt = wts[i]
            flag = (r.choice(["late", "ok", "ok"]) if wt == "corrective" else None)
            rows.append((f"PR-{18000 + int(p.get('off', 0)) + i}", f"ESI{int(r.integers(100, 999))}L", sts[i], wt,
                         base - pd.Timedelta(days=i, hours=int(r.integers(0, 20))), METIERS[int(r.integers(0, 8))],
                         f"C-2024-{int(r.integers(10, 99)):04d}", float(r.uniform(2, 60)) * 3600 if wt == "corrective" else None, flag))
        return pd.DataFrame(rows, columns=["reference", "equipment_reference", "status", "work_type", "creation_date",
                                           "contract_topic", "contract_reference", "response_time", "late_flag"])
    if "PERCENTILE_CONT" in s:
        return pd.DataFrame({"ratio": [3600.0]})
    if "AS pec" in s:
        r = np.random.default_rng(_seed(_pid(p) or "x"))
        return pd.DataFrame({"pec": [float(r.uniform(6, 40)) * 3600], "res": [float(r.uniform(20, 140)) * 3600]})
    if "COUNT(DISTINCT t.equipment_reference)" in s:
        return pd.DataFrame({"n": [int(300 + _seed(_pid(p) or "x") % 4000)]})

    # ---- page Prestataires
    if "AS interventions" in s and "NOT EXISTS" in s:
        return pd.DataFrame({"provider_id": [o["id"] for o in OUTSIDE], "provider_name": [o["name"] for o in OUTSIDE],
                             "interventions": [o["interv"] for o in OUTSIDE]})
    if "AS prestataires_actifs" in s:
        return pd.DataFrame({"prestataires_actifs": [len(PROVIDERS) - 6], "contrats_actifs": [305], "metiers": [16]})
    if "COUNT(DISTINCT h.agence)" in s:
        return pd.DataFrame({"n": [29]})
    if "AS actifs" in s:
        r = np.random.default_rng(11)
        actifs, total = [], []
        for pr in PROVIDERS:
            t = pr["contrats"]
            a = int(round(t * float(r.uniform(.5, 1))))
            actifs.append(a)
            total.append(t)
        return pd.DataFrame({"provider_id": [pr["id"] for pr in PROVIDERS], "provider_name": [pr["name"] for pr in PROVIDERS],
                             "actifs": actifs, "total": total, "metiers": [pr["metiers"] for pr in PROVIDERS]})

    # ---- anomalies
    if "Référence reçue" in s:
        return pd.DataFrame({"Référence reçue": ["78171/78171", "73305/78171"], "Libellé reçu": ["I3F-75 - CT FERMETURES AUTO LOT 1 - KONE"] * 2,
                             "Type d'anomalie": ["Référence composée avec « / »"] * 2, "Interventions": [25, 7]})
    if 'AS "Identifiant"' in s:
        return pd.DataFrame({"Identifiant": [o["id"] for o in OUTSIDE], "Prestataire": [o["name"] for o in OUTSIDE],
                             "Interventions": [o["interv"] for o in OUTSIDE]})
    if 'AS "Référence"' in s:
        return pd.DataFrame({"Référence": ["R1", "R2"], "Libellé": ["Contrat A", "Contrat B"], "Statut": ["active", "inactive"], "Prestataire": ["KONE", "ISTA FRANCE"]})
    if "t.contract_reference IS NULL" in s:
        return pd.DataFrame({"n": [0]})

    # ---- socle commun
    if "MIN(jour)" in s:
        return pd.DataFrame({"debut": [date(2025, 1, 1)], "fin": [TODAY - timedelta(days=1)]})
    if "current_database" in s:
        return pd.DataFrame({"database_name": ["demo"], "checked_at": [pd.Timestamp.now()]})
    if "SELECT COALESCE(SUM(nb_operations),0)" in s:
        return pd.DataFrame({"n": [6_800_000]})
    if "thirdParty.entity.id" in s:  # options du filtre Prestataire
        return pd.DataFrame({"reference": [pr["id"] for pr in PROVIDERS], "libelle": [pr["name"] for pr in PROVIDERS]})
    if "c.topic" in s and "ORDER BY (" in s:
        t = METIERS[:5] + ["Non renseigné"]
        return pd.DataFrame({"reference": t, "libelle": t})
    if "AS libelle" in s and "kpi_operations_daily" in s and "GROUP BY t." in s and "date_trunc" not in s:
        col = s.split("SELECT t.")[1].split("::text")[0]
        n = {"agence_reference": 33, "provider_id": len(PROVIDERS), "service_code": 16, "contract_reference": 598,
             "societe_reference": 4, "groupe_reference": 12, "secteur_reference": 40, "programme_reference": 90, "work_type": 2}.get(col, 5)
        return pd.DataFrame({"reference": [f"{col[:3]}{i}" for i in range(n)], "libelle": [f"{col[:4].title()} {i}" for i in range(n)]})
    if "FROM public.vw_program_hierarchy" in s and "AS libelle" in s:
        return pd.DataFrame({"reference": [f"G{i}" for i in range(12)], "libelle": [f"Libellé {i}" for i in range(12)]})
    if "SUM(t.nb_operations)" in s:
        return pd.DataFrame({"total_operations": [12084], "comparables_pec": [1214], "hors_delai_pec": [143],
                             "comparables_resolution": [1000], "hors_delai_resolution": [90]})
    if "date_trunc" in s:
        if "'year'" in s:
            return pd.DataFrame({"periode": [date(2025, 1, 1), date(2026, 1, 1)], "comparables": [900, 1200], "hors_delai": [130, 143]})
        months = pd.date_range("2025-10-01", "2026-09-01", freq="MS")
        taux = [.13, .16, .15, .12, .11, .14, .15, .125, .12, .11, .12, .118]
        return pd.DataFrame({"periode": [d.date() for d in months], "comparables": [1000] * 12, "hors_delai": [int(1000 * t) for t in taux]})
    if "pannes_zone_daily" in s:
        d = pd.DataFrame(AGENCES, columns=["reference", "libelle", "nb_pannes"])
        d = d.sort_values("nb_pannes", ascending=("ASC" in s)).reset_index(drop=True)
        d["total_pannes"] = int(d["nb_pannes"].sum())
        return d
    if "pannes_equipement_daily" in s:
        d = pd.DataFrame(EQ, columns=["equipment_reference", "nb_pannes"])
        d = d.sort_values("nb_pannes", ascending=("ASC" in s)).reset_index(drop=True)
        d["derniere_panne"] = pd.Timestamp("2026-09-02")
        return d
    if "DISTINCT ON" in s:
        refs = p["refs"]
        return pd.DataFrame({"equipment_reference": refs, "provider_name": [NAMES[i % len(NAMES)] for i in range(len(refs))],
                             "programme_reference": [f"0{521 - i}. Rés. Le Panorama" for i in range(len(refs))],
                             "agence_label": ["Lyon 7"] * len(refs)})
    raise RuntimeError("Mode démonstration : requête non gérée : " + s[:140])