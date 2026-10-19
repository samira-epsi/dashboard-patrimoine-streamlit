# TDB REX 3F | Vue globale

## Lancer sous Windows / Python

```powershell
cd tdb_rex
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
# Remplir .streamlit\secrets.toml
streamlit run app.py
```

## Connexion

Le compte PostgreSQL doit avoir `CONNECT` sur la base, `USAGE` sur `dashboard_operations` et `SELECT` sur les tables concernées. L'application est en lecture seule : elle ne modifie aucune donnée.

## Tables utilisées

- `dashboard_operations.kpi_operations_daily` : indicateurs, graphiques et valeurs des filtres
- `dashboard_operations.pannes_zone_daily` : localisation des pannes
- `dashboard_operations.pannes_equipement_daily` : récurrence par équipement
- `dashboard_operations.operations_light` : liste générale paginée
- `dashboard_operations.curatives_hors_delai_light` : liste hors délai de prise en charge

## Correspondance avec la maquette

- Filtres rapides : Agence, Prestataire, Métier, Contrat. Le filtre Métier utilise `service_code` / `service_label`. Si ton Métier correspond à `work_type`, modifie `DIMENSIONS` dans `services/queries.py`.
- « Plus de filtres » : Société, Groupe, Secteur, Programme, Type de travaux.
- Récurrence par équipement : le prestataire et le programme viennent de la dernière intervention de l'équipement dans `operations_light` (requête `equipment_context`). Si elle échoue, le classement reste affiché sans ces colonnes.
- Série « Préventif non réalisé » : elle apparaît automatiquement dès que `trend()` renvoie une colonne `preventif_non_realise`.
- Les cartes Taux de réalisation préventive et Rapports manquants affichent N/D tant que les règles métier ne sont pas validées.

## Points à confirmer avec le métier

- L'agrégat `nb_operations` est pris comme le volume d'interventions, sans garantie d'unicité de référence entre contrats : à vérifier.
- "Hors délai" dans l'interface = prise en charge hors SLA, numérateur `nb_hors_delai_prise_en_charge` et dénominateur `nb_comparables_prise_en_charge`. Le KPI n'est pas l'union des deux SLA.
- Le taux de réalisation préventive demande de définir quelles interventions sont prévues et réalisées et la logique temporelle ; laissé en N/D.
- Les rapports manquants demandent la jointure et la qualification des documents ; laissé en N/D.
- Les tables pannes ne contiennent pas prestataire, contrat, prestation ou type de travaux : leurs visuels sont masqués lorsque ces filtres sont actifs, au lieu de présenter des résultats faux.
- La dernière date de création des agrégats n'est pas un horodatage de synchronisation.
- Une période sélectionnée signifie : dates de création, pas forcément interventions actives pendant la période.
- Vérifier les index `(jour, ref)` de l'agrégat et des pannes et `(creation_date)` des tables de détail avant ouverture à tous les REX.

Ne mets jamais les mots de passe dans Git.
