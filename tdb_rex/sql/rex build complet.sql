-- ============================================================================
-- 00. Schéma rex : paramètres, journal de construction, fonctions utilitaires.
-- Idempotent : peut être relancé sans risque.
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS rex;

-- Seuils modifiables sans toucher au code (alertes paramétrables)
CREATE TABLE IF NOT EXISTS rex.parametre (
    code        text PRIMARY KEY,
    valeur      numeric NOT NULL,
    description text
);
INSERT INTO rex.parametre (code, valeur, description) VALUES
    ('seuil_preventif_retard_jours',  90, 'Une préventive en retard depuis plus de N jours devient une anomalie'),
    ('seuil_curatif_ouvert_jours',    90, 'Une curative encore en cours depuis plus de N jours devient une anomalie'),
    ('seuil_curatif_sans_maj_jours',  30, 'Une curative en cours sans mise à jour depuis plus de N jours devient une anomalie')
ON CONFLICT (code) DO NOTHING;

-- Journal de construction (une ligne par étape)
CREATE TABLE IF NOT EXISTS rex.build_log (
    id         bigserial PRIMARY KEY,
    etape      text        NOT NULL,
    nb_lignes  bigint,
    termine_le timestamptz NOT NULL DEFAULT clock_timestamp()
);

-- Jour calendaire à l'heure de Paris
CREATE OR REPLACE FUNCTION rex.jour_paris(ts timestamptz) RETURNS date
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT (ts AT TIME ZONE 'Europe/Paris')::date $$;
ALTER TABLE rex.build_log ALTER COLUMN termine_le SET DEFAULT clock_timestamp();
-- ============================================================================
-- 10a. Copie brute de la vue des interventions dans rex.src_operations.
-- Étape isolée pour mesurer le coût de la vue. Table non journalisée (UNLOGGED) : écriture plus rapide,
-- elle est reconstruite à chaque build.
-- ============================================================================
SET work_mem = '256MB';
SET max_parallel_workers_per_gather = 4;

DROP TABLE IF EXISTS rex.src_operations;
CREATE UNLOGGED TABLE rex.src_operations AS
SELECT operation_key, reference, operation_source, type, status, event, work_type, critical_level, technical_reason,
       creation_date, last_update_date, first_event_date, event_date, log_date, last_seen_at, event_history,
       provider_id, provider_name, contract_reference, contract_label, contract_topic, service_code, service_label,
       sla_intervention_value, sla_intervention_unit, sla_recovery_value, sla_recovery_unit,
       response_time, resolution_duration,
       societe_reference, societe_label, agence_reference, agence_label, groupe_reference, groupe_label,
       secteur_reference, secteur_label, programme_reference, programme_label,
       asset_reference, equipment_reference
FROM public.vw_operations_hierarchy_current;
CREATE INDEX ON rex.src_operations (reference);
ANALYZE rex.src_operations;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'src_operations', COUNT(*) FROM rex.src_operations;
-- ============================================================================
-- 10b. rex.f_operations : une ligne par intervention (operation_key), toutes sources et tous types de travaux.
-- Règles : les colonnes brutes sont conservées à côté des colonnes calculées.
-- Une colonne calculée vaut NULL quand la donnée ne permet pas de conclure (jamais de valeur inventée).
-- Source : rex.src_operations (copie de public.vw_operations_hierarchy_current, étape 10a).
-- ============================================================================
SET work_mem = '256MB';
SET max_parallel_workers_per_gather = 4;

DROP TABLE IF EXISTS rex.tmp_contrat;
CREATE UNLOGGED TABLE rex.tmp_contrat AS
SELECT DISTINCT ON (reference) reference, status
FROM public.contracts_current
ORDER BY reference, "lastUpdateDate" DESC NULLS LAST;
CREATE UNIQUE INDEX ON rex.tmp_contrat (reference);

DROP TABLE IF EXISTS rex.tmp_doc;
CREATE UNLOGGED TABLE rex.tmp_doc AS
SELECT DISTINCT ON (intervention_reference)
       intervention_reference, document_count, has_document_api, api_error, checked_at
FROM public.intervention_documents_current
ORDER BY intervention_reference, checked_at DESC NULLS LAST;
CREATE UNIQUE INDEX ON rex.tmp_doc (intervention_reference);
ANALYZE rex.tmp_contrat; ANALYZE rex.tmp_doc;

DROP TABLE IF EXISTS rex.f_operations CASCADE;
CREATE TABLE rex.f_operations AS
WITH
-- niveau 0 : colonnes brutes
s AS (
    SELECT
        h.operation_key, h.reference, h.operation_source, h.type,
        h.status, h.event, h.work_type, h.critical_level, h.technical_reason,
        h.creation_date, rex.jour_paris(h.creation_date) AS jour_creation,
        h.last_update_date, h.first_event_date, h.event_date, h.log_date, h.last_seen_at,
        h.event_history,
        h.provider_id, h.provider_name,
        h.contract_reference, h.contract_label,
        COALESCE(NULLIF(BTRIM(h.contract_topic), ''), 'Non renseigné') AS metier,
        c.status AS contract_status,
        h.service_code, h.service_label,
        h.sla_intervention_value, h.sla_intervention_unit,
        h.sla_recovery_value,     h.sla_recovery_unit,
        h.response_time, h.resolution_duration,
        h.societe_reference,   h.societe_label,
        h.agence_reference,    h.agence_label,
        h.groupe_reference,    h.groupe_label,
        h.secteur_reference,   h.secteur_label,
        h.programme_reference, h.programme_label,
        h.asset_reference, h.equipment_reference,
        d.document_count, d.has_document_api, d.api_error, d.checked_at AS document_checked_at
    FROM rex.src_operations h
    LEFT JOIN rex.tmp_contrat c ON c.reference = h.contract_reference
    LEFT JOIN rex.tmp_doc     d ON d.intervention_reference = h.reference
),
-- niveau 1 : états, SLA convertis, validité des durées, cycle de vie
b AS (
    SELECT s.*,
        COALESCE(s.status IN ('open', 'pending', 'hold'), false)       AS est_en_cours,
        COALESCE(s.status = 'closed', false)                           AS est_cloturee,
        COALESCE(s.status = 'denied' AND s.event = 'canceled', false)  AS est_annulee,
        COALESCE(s.status = 'denied', false)                           AS est_refusee,
        CASE WHEN s.status = 'closed' THEN s.event END                 AS type_cloture,
        CASE WHEN s.status = 'denied' THEN s.event END                 AS type_refus,
        CASE WHEN s.status IN ('closed', 'denied') THEN s.event END    AS type_fin,
        NULL::text                                                     AS motif_cloture,    -- aucun champ source : NULL
        NULL::text                                                     AS motif_annulation, -- aucun champ source : NULL
        COALESCE(s.work_type = 'corrective', false)                    AS est_curative,
        COALESCE(s.work_type = 'preventive', false)                    AS est_preventive,
        COALESCE(s.work_type = 'corrective' AND s.status <> 'denied', false) AS perimetre_curatif,
        COALESCE(s.event IN ('planned', 'client_planned', 'replanned'), false) AS famille_planif,
        substring(s.event_history from '^\[\s*"([^"]*)"')              AS premier_evenement,
        COALESCE(s.event_history LIKE '%"planned"%', false)            AS hist_contient_planned,
        ((length(COALESCE(s.event_history, '')) - length(replace(COALESCE(s.event_history, ''), '"replanned"', '')))
            / length('"replanned"'))                                   AS nb_replanifications,
        -- SLA en millisecondes : heures et jours uniquement (calendaires)
        CASE WHEN s.sla_intervention_value > 0 AND LOWER(BTRIM(s.sla_intervention_unit)) = 'hour' THEN s.sla_intervention_value * 3600000
             WHEN s.sla_intervention_value > 0 AND LOWER(BTRIM(s.sla_intervention_unit)) = 'day'  THEN s.sla_intervention_value * 86400000 END AS sla_intervention_ms,
        CASE WHEN s.sla_recovery_value > 0 AND LOWER(BTRIM(s.sla_recovery_unit)) = 'hour' THEN s.sla_recovery_value * 3600000
             WHEN s.sla_recovery_value > 0 AND LOWER(BTRIM(s.sla_recovery_unit)) = 'day'  THEN s.sla_recovery_value * 86400000 END AS sla_recovery_ms,
        -- SLA en mois : valeur conservée telle quelle (nombre de mois), jamais perdue
        CASE WHEN s.sla_intervention_value > 0 AND LOWER(BTRIM(s.sla_intervention_unit)) = 'month' THEN s.sla_intervention_value END AS sla_intervention_mois,
        CASE WHEN s.sla_recovery_value > 0 AND LOWER(BTRIM(s.sla_recovery_unit)) = 'month' THEN s.sla_recovery_value END AS sla_recovery_mois,
        COALESCE((s.sla_intervention_unit IS NOT NULL AND LOWER(BTRIM(s.sla_intervention_unit)) NOT IN ('hour', 'day', 'month'))
              OR (s.sla_recovery_unit     IS NOT NULL AND LOWER(BTRIM(s.sla_recovery_unit))     NOT IN ('hour', 'day', 'month')), false) AS sla_unite_inconnue,
        -- durées mesurées (millisecondes) : NULL, -1 et 0 ne servent jamais à conclure
        COALESCE(s.response_time > 0, false)        AS pec_valide,
        COALESCE(s.response_time = 0, false)        AS pec_zero,
        COALESCE(s.response_time = -1, false)       AS pec_moins1,
        COALESCE(s.resolution_duration > 0, false)  AS res_valide,
        COALESCE(s.resolution_duration = 0, false)  AS res_zero,
        COALESCE(s.resolution_duration = -1, false) AS res_moins1
    FROM s
),
-- niveau 2 : comparables, dates, indicateurs préventifs de base
c AS (
    SELECT b.*,
        (b.perimetre_curatif AND b.sla_intervention_ms IS NOT NULL AND b.pec_valide) AS pec_comparable,
        (b.perimetre_curatif AND b.sla_recovery_ms     IS NOT NULL AND b.res_valide) AS res_comparable,
        -- hypothèse à confirmer : un mois = un mois calendaire (week-ends compris), mesuré depuis creation_date
        (b.perimetre_curatif AND b.sla_intervention_mois IS NOT NULL AND b.pec_valide) AS pec_comparable_mois,
        (b.perimetre_curatif AND b.sla_recovery_mois     IS NOT NULL AND b.res_valide) AS res_comparable_mois,
        EXTRACT(EPOCH FROM ((b.creation_date + b.sla_intervention_mois * INTERVAL '1 month') - b.creation_date)) * 1000 AS sla_intervention_mois_ms,
        EXTRACT(EPOCH FROM ((b.creation_date + b.sla_recovery_mois     * INTERVAL '1 month') - b.creation_date)) * 1000 AS sla_recovery_mois_ms,
        -- dates préventives : on ne retient une date que si la donnée la porte réellement
        CASE WHEN b.est_preventive AND b.premier_evenement IN ('planned', 'client_planned') AND b.first_event_date >= DATE '2000-01-01'
             THEN b.first_event_date END                                                   AS date_prevue_initiale,
        CASE WHEN b.est_preventive AND b.est_en_cours AND b.famille_planif AND b.event_date >= DATE '2000-01-01'
             THEN b.event_date END                                                         AS date_prevue_finale,
        CASE WHEN b.est_preventive AND b.status = 'closed' AND b.event IN ('done', 'solved') AND b.event_date >= DATE '2000-01-01'
             THEN b.event_date END                                                         AS date_realisation,
        CASE WHEN b.est_annulee AND b.event_date >= DATE '2000-01-01'
             THEN b.event_date END                                                         AS date_annulation,
        (b.est_preventive AND (b.status <> 'denied' OR b.event = 'canceled'))              AS preventive_prevue,
        (b.est_preventive AND b.status = 'closed' AND b.event IN ('done', 'solved'))       AS preventive_realisee,
        (b.est_preventive AND b.status = 'closed' AND b.event NOT IN ('done', 'solved'))   AS preventive_cloturee_non_realisee,
        (b.est_preventive AND b.est_annulee)                                               AS preventive_annulee,
        (b.est_preventive AND b.est_en_cours)                                              AS preventive_restante,
        (b.est_preventive AND b.est_en_cours AND b.famille_planif AND b.event_date < now()) AS preventive_actuellement_en_retard,
        -- rapport (clôturées uniquement)
        CASE WHEN b.status <> 'closed' THEN NULL
             WHEN b.api_error IS NOT NULL THEN 'erreur_api'
             WHEN b.has_document_api IS TRUE THEN 'avec'
             WHEN b.has_document_api IS FALSE THEN 'sans'
             ELSE 'non_verifie' END                                                        AS rapport_statut
    FROM b
),
-- niveau 3 : hors délai et ponctualité
d AS (
    SELECT c.*,
        CASE WHEN c.pec_comparable THEN c.response_time > c.sla_intervention_ms END        AS hors_delai_prise_en_charge,
        CASE WHEN c.res_comparable THEN c.resolution_duration > c.sla_recovery_ms END      AS hors_delai_resolution,
        CASE WHEN c.pec_comparable_mois THEN c.response_time > c.sla_intervention_mois_ms END AS hors_delai_prise_en_charge_mois,
        CASE WHEN c.res_comparable_mois THEN c.resolution_duration > c.sla_recovery_mois_ms END AS hors_delai_resolution_mois,
        (c.pec_comparable OR c.res_comparable)                                             AS global_comparable,
        COALESCE(c.date_prevue_finale, c.date_prevue_initiale)                             AS date_prevue,
        CASE WHEN c.date_prevue_finale IS NOT NULL THEN 'evenement_courant'
             WHEN c.date_prevue_initiale IS NOT NULL THEN 'historique_planned' END         AS date_prevue_source,
        CASE WHEN c.preventive_actuellement_en_retard
             THEN GREATEST(CURRENT_DATE - rex.jour_paris(c.event_date), 0) END             AS jours_retard_actuel
    FROM c
)
SELECT d.*,
    CASE WHEN d.global_comparable
         THEN COALESCE(d.hors_delai_prise_en_charge, false) OR COALESCE(d.hors_delai_resolution, false) END AS hors_delai_global,
    (d.date_prevue IS NOT NULL)                                                            AS date_prevue_connue,
    CASE WHEN d.preventive_realisee AND d.date_prevue IS NOT NULL AND d.date_realisation IS NOT NULL
         THEN rex.jour_paris(d.date_realisation) <= rex.jour_paris(d.date_prevue) END      AS preventive_realisee_dans_delai,
    CASE WHEN d.preventive_realisee AND d.date_prevue IS NOT NULL AND d.date_realisation IS NOT NULL
         THEN rex.jour_paris(d.date_realisation) >  rex.jour_paris(d.date_prevue) END      AS preventive_realisee_en_retard,
    CASE WHEN d.preventive_realisee AND d.date_prevue IS NOT NULL AND d.date_realisation IS NOT NULL
         THEN rex.jour_paris(d.date_realisation) -  rex.jour_paris(d.date_prevue) END      AS jours_retard_realisation
FROM d;

ALTER TABLE rex.f_operations ADD PRIMARY KEY (operation_key);
CREATE INDEX ON rex.f_operations (work_type, jour_creation);
CREATE INDEX ON rex.f_operations (work_type, status, jour_creation);
CREATE INDEX ON rex.f_operations (provider_id, work_type, jour_creation);
CREATE INDEX ON rex.f_operations (contract_reference);
CREATE INDEX ON rex.f_operations (programme_reference);
CREATE INDEX ON rex.f_operations (agence_reference);
CREATE INDEX ON rex.f_operations (equipment_reference) WHERE equipment_reference IS NOT NULL;
CREATE INDEX ON rex.f_operations (reference text_pattern_ops);
CREATE INDEX ON rex.f_operations (last_update_date) WHERE est_en_cours;
CREATE INDEX ON rex.f_operations (date_prevue) WHERE est_preventive;
CREATE INDEX ON rex.f_operations (rapport_statut) WHERE rapport_statut IS NOT NULL;
ANALYZE rex.f_operations;

INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'f_operations', COUNT(*) FROM rex.f_operations;

DROP TABLE IF EXISTS rex.tmp_contrat;
DROP TABLE IF EXISTS rex.tmp_doc;
-- rex.src_operations est conservée : utile pour auditer. Elle peut être supprimée après le build.
-- ============================================================================
-- 20. Dimensions et tables de liaison.
-- ============================================================================
SET work_mem = '256MB';

-- Programmes : colonne vertébrale = vw_program_hierarchy (tous les programmes), enrichie des références
-- de la hiérarchie issues des interventions et du nombre de logements.
DROP TABLE IF EXISTS rex.d_programme CASCADE;
CREATE TABLE rex.d_programme AS
WITH ops AS (
    SELECT programme_reference,
           MAX(programme_label) AS programme_label,
           MAX(societe_reference) AS societe_reference, MAX(societe_label) AS societe_label,
           MAX(agence_reference)  AS agence_reference,  MAX(agence_label)  AS agence_label,
           MAX(groupe_reference)  AS groupe_reference,  MAX(groupe_label)  AS groupe_label,
           MAX(secteur_reference) AS secteur_reference, MAX(secteur_label) AS secteur_label
    FROM rex.f_operations
    WHERE programme_reference IS NOT NULL
    GROUP BY programme_reference
),
logements AS (
    SELECT program_reference, COUNT(*)::bigint AS nb_logements
    FROM public.vw_housing_hierarchy
    GROUP BY program_reference
)
SELECT COALESCE(o.programme_reference, p.program_reference)       AS programme_reference,
       COALESCE(o.programme_label, p.program_label::text)         AS programme_label,
       o.societe_reference, COALESCE(o.societe_label, p.societe::text) AS societe_label,
       o.agence_reference,  COALESCE(o.agence_label,  p.agence::text)  AS agence_label,
       o.groupe_reference,  COALESCE(o.groupe_label,  p.groupe::text)  AS groupe_label,
       o.secteur_reference, COALESCE(o.secteur_label, p.secteur::text) AS secteur_label,
       COALESCE(l.nb_logements, 0)                                AS nb_logements,
       (o.programme_reference IS NOT NULL)                        AS a_des_interventions
FROM ops o
FULL JOIN public.vw_program_hierarchy p ON p.program_reference = o.programme_reference
LEFT JOIN logements l ON l.program_reference = COALESCE(o.programme_reference, p.program_reference);
ALTER TABLE rex.d_programme ADD PRIMARY KEY (programme_reference);
CREATE INDEX ON rex.d_programme (agence_label);
CREATE INDEX ON rex.d_programme (agence_reference);
ANALYZE rex.d_programme;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'd_programme', COUNT(*) FROM rex.d_programme;

-- Contrats (un par référence)
DROP TABLE IF EXISTS rex.d_contrat CASCADE;
CREATE TABLE rex.d_contrat AS
SELECT DISTINCT ON (c.reference)
       c.reference                                              AS contract_reference,
       c.label                                                  AS contract_label,
       COALESCE(NULLIF(BTRIM(c.topic), ''), 'Non renseigné')    AS metier,
       c.status                                                 AS contract_status,
       c."thirdParty.entity.id"                                 AS provider_id,
       c."thirdParty.entity.label"                              AS provider_name,
       c."startDate"                                            AS date_debut,
       c."endDate"                                              AS date_fin,
       c."deactivationDate"                                     AS date_desactivation
FROM public.contracts_current c
WHERE c.reference IS NOT NULL
ORDER BY c.reference, c."lastUpdateDate" DESC NULLS LAST;
ALTER TABLE rex.d_contrat ADD PRIMARY KEY (contract_reference);
CREATE INDEX ON rex.d_contrat (provider_id);
CREATE INDEX ON rex.d_contrat (metier);
ANALYZE rex.d_contrat;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'd_contrat', COUNT(*) FROM rex.d_contrat;

-- Liaison prestataire / contrat / programme (périmètre contractuel, géographie incluse)
DROP TABLE IF EXISTS rex.r_prestataire_programme CASCADE;
CREATE TABLE rex.r_prestataire_programme AS
SELECT c.provider_id, c.contract_reference, c.metier, c.contract_status,
       cov.program_reference AS programme_reference,
       p.societe_reference, p.societe_label, p.agence_reference, p.agence_label,
       p.groupe_reference,  p.groupe_label,  p.secteur_reference, p.secteur_label,
       COALESCE(p.nb_logements, 0) AS nb_logements
FROM rex.d_contrat c
JOIN (SELECT DISTINCT contract_reference, program_reference FROM public.vw_contract_program_coverage) cov
  ON cov.contract_reference = c.contract_reference
LEFT JOIN rex.d_programme p ON p.programme_reference = cov.program_reference
WHERE c.provider_id IS NOT NULL;
CREATE INDEX ON rex.r_prestataire_programme (provider_id);
CREATE INDEX ON rex.r_prestataire_programme (contract_reference);
CREATE INDEX ON rex.r_prestataire_programme (programme_reference);
CREATE INDEX ON rex.r_prestataire_programme (agence_reference);
ANALYZE rex.r_prestataire_programme;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'r_prestataire_programme', COUNT(*) FROM rex.r_prestataire_programme;

-- Prestataires : tous ceux qui ont un contrat, plus ceux qui ont des interventions sans contrat (hors_contrat)
DROP TABLE IF EXISTS rex.d_prestataire CASCADE;
CREATE TABLE rex.d_prestataire AS
WITH contrats AS (
    SELECT provider_id,
           MAX(provider_name)                                        AS provider_name,
           COUNT(*) FILTER (WHERE contract_status = 'active')        AS nb_contrats_actifs,
           COUNT(*)                                                  AS nb_contrats_total,
           ARRAY_AGG(DISTINCT metier ORDER BY metier) FILTER (WHERE metier <> 'Non renseigné') AS metiers
    FROM rex.d_contrat WHERE provider_id IS NOT NULL
    GROUP BY provider_id
),
couverture AS (
    SELECT provider_id,
           COUNT(*)                          AS nb_esi,
           COUNT(DISTINCT agence_label)      AS nb_agences,
           COALESCE(SUM(nb_logements), 0)    AS nb_logements
    FROM (SELECT DISTINCT provider_id, programme_reference, agence_label, nb_logements FROM rex.r_prestataire_programme) x
    GROUP BY provider_id
),
ops AS (
    SELECT provider_id,
           MAX(provider_name)                                        AS provider_name,
           COUNT(*) FILTER (WHERE work_type = 'corrective')          AS nb_curatives,
           COUNT(*) FILTER (WHERE work_type = 'preventive')          AS nb_preventives,
           COUNT(*)                                                  AS nb_interventions
    FROM rex.f_operations WHERE provider_id IS NOT NULL
    GROUP BY provider_id
)
SELECT COALESCE(c.provider_id, o.provider_id)                        AS provider_id,
       COALESCE(NULLIF(c.provider_name, ''), o.provider_name, c.provider_id) AS provider_name,
       COALESCE(c.nb_contrats_actifs, 0)                             AS nb_contrats_actifs,
       COALESCE(c.nb_contrats_total, 0)                              AS nb_contrats_total,
       COALESCE(c.metiers, ARRAY[]::text[])                          AS metiers,
       COALESCE(v.nb_esi, 0)                                         AS nb_esi,
       COALESCE(v.nb_agences, 0)                                     AS nb_agences,
       COALESCE(v.nb_logements, 0)                                   AS nb_logements,
       COALESCE(o.nb_curatives, 0)                                   AS nb_curatives,
       COALESCE(o.nb_preventives, 0)                                 AS nb_preventives,
       COALESCE(o.nb_interventions, 0)                               AS nb_interventions,
       (c.provider_id IS NULL)                                       AS hors_contrat
FROM contrats c
FULL JOIN ops o ON o.provider_id = c.provider_id
LEFT JOIN couverture v ON v.provider_id = COALESCE(c.provider_id, o.provider_id);
ALTER TABLE rex.d_prestataire ADD PRIMARY KEY (provider_id);
ANALYZE rex.d_prestataire;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'd_prestataire', COUNT(*) FROM rex.d_prestataire;

-- Équipements ayant au moins une intervention : dernier contexte connu (remplace le DISTINCT ON de 10 s)
DROP TABLE IF EXISTS rex.d_equipement CASCADE;
CREATE TABLE rex.d_equipement AS
WITH dernier AS (
    SELECT DISTINCT ON (equipment_reference)
           equipment_reference, provider_id, provider_name, programme_reference, programme_label,
           agence_reference, agence_label, creation_date AS derniere_intervention
    FROM rex.f_operations
    WHERE equipment_reference IS NOT NULL
    ORDER BY equipment_reference, creation_date DESC
),
eq AS (
    SELECT DISTINCT ON (reference) reference, label, type, "fullPath" AS chemin
    FROM public.equipment_current
    ORDER BY reference, "lastUpdateDate" DESC NULLS LAST
)
SELECT d.*, e.label AS equipment_label, e.type AS equipment_type, e.chemin AS equipment_chemin
FROM dernier d
LEFT JOIN eq e ON e.reference = d.equipment_reference;
ALTER TABLE rex.d_equipement ADD PRIMARY KEY (equipment_reference);
ANALYZE rex.d_equipement;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'd_equipement', COUNT(*) FROM rex.d_equipement;
-- ============================================================================
-- 25. Petites tables pour les filtres (rapides : quelques milliers de lignes au lieu de 7,7 M).
-- À lancer une fois dans pgAdmin, puis à garder dans le build (après 10_f_operations.sql).
-- ============================================================================
SET work_mem = '256MB';

-- Une ligne par CODE agence (la référence fait foi) ; libellé = le plus fréquent pour ce code.
DROP TABLE IF EXISTS rex.d_agence;
CREATE TABLE rex.d_agence AS
SELECT agence_reference, (ARRAY_AGG(agence_label ORDER BY n DESC))[1] AS agence_label, SUM(n)::bigint AS nb_interventions
FROM (SELECT agence_reference, agence_label, COUNT(*) AS n
      FROM rex.f_operations WHERE agence_reference IS NOT NULL GROUP BY 1, 2) x
GROUP BY agence_reference;
ALTER TABLE rex.d_agence ADD PRIMARY KEY (agence_reference);
ANALYZE rex.d_agence;

-- Combinaisons de valeurs de filtre réellement présentes dans les interventions : sert à croiser les listes des filtres.
DROP TABLE IF EXISTS rex.f_filtres;
CREATE TABLE rex.f_filtres AS
SELECT DISTINCT work_type, societe_reference, agence_reference, groupe_reference, secteur_reference,
       programme_reference, provider_id, contract_reference, metier, contract_status
FROM rex.f_operations
WHERE work_type IN ('corrective', 'preventive');
CREATE INDEX ON rex.f_filtres (work_type);
CREATE INDEX ON rex.f_filtres (agence_reference);
CREATE INDEX ON rex.f_filtres (provider_id);
CREATE INDEX ON rex.f_filtres (contract_reference);
CREATE INDEX ON rex.f_filtres (programme_reference);
ANALYZE rex.f_filtres;

INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'd_agence', COUNT(*) FROM rex.d_agence;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'f_filtres', COUNT(*) FROM rex.f_filtres;
-- ============================================================================
-- 30. Tables agrégées par jour. Le tableau de bord somme les jours entre date_debut et date_fin :
-- période libre, semaine, mois, année.  Aucune ligne n'est supprimée parce qu'un niveau de hiérarchie est NULL.
-- Chaque filtre est une colonne : aucune jointure à la lecture.
-- ============================================================================
SET work_mem = '256MB';

-- ---------------------------------------------------------------- CURATIF (jour = date de création)
DROP TABLE IF EXISTS rex.f_curatif_jour CASCADE;
CREATE TABLE rex.f_curatif_jour AS
SELECT
    jour_creation AS jour,
    status, type_fin,
    societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
    provider_id, contract_reference, metier, contract_status,
    COUNT(*)                                                                AS nb_operations,
    COUNT(*) FILTER (WHERE est_annulee)                                     AS nb_annulees,
    COUNT(*) FILTER (WHERE est_refusee AND NOT est_annulee)                 AS nb_refusees_autres,
    -- prise en charge et résolution (SLA en heures et jours)
    COUNT(*) FILTER (WHERE pec_comparable)                                  AS nb_pec_comparables,
    COUNT(*) FILTER (WHERE hors_delai_prise_en_charge)                      AS nb_pec_hors_delai,
    COUNT(*) FILTER (WHERE res_comparable)                                  AS nb_res_comparables,
    COUNT(*) FILTER (WHERE hors_delai_resolution)                           AS nb_res_hors_delai,
    COUNT(*) FILTER (WHERE global_comparable)                               AS nb_global_comparables,
    COUNT(*) FILTER (WHERE hors_delai_global)                               AS nb_global_hors_delai,
    -- SLA exprimés en mois (hypothèse : mois calendaire), séparés pour rester transparents
    COUNT(*) FILTER (WHERE pec_comparable_mois)                             AS nb_pec_comparables_mois,
    COUNT(*) FILTER (WHERE hors_delai_prise_en_charge_mois)                 AS nb_pec_hors_delai_mois,
    COUNT(*) FILTER (WHERE res_comparable_mois)                             AS nb_res_comparables_mois,
    COUNT(*) FILTER (WHERE hors_delai_resolution_mois)                      AS nb_res_hors_delai_mois,
    -- transparence : pourquoi une intervention n'est pas comparable
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_intervention_ms IS NULL AND sla_intervention_mois IS NULL) AS nb_sans_sla_intervention,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_recovery_ms     IS NULL AND sla_recovery_mois     IS NULL) AS nb_sans_sla_resolution,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_unite_inconnue)        AS nb_sla_unite_inconnue,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_intervention_ms IS NOT NULL AND response_time IS NULL) AS nb_pec_duree_nulle,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_intervention_ms IS NOT NULL AND pec_moins1) AS nb_pec_duree_moins1,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_intervention_ms IS NOT NULL AND pec_zero)    AS nb_pec_duree_zero,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_recovery_ms IS NOT NULL AND resolution_duration IS NULL) AS nb_res_duree_nulle,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_recovery_ms IS NOT NULL AND res_moins1)      AS nb_res_duree_moins1,
    COUNT(*) FILTER (WHERE perimetre_curatif AND sla_recovery_ms IS NOT NULL AND res_zero)        AS nb_res_duree_zero,
    -- rapports (clôturées)
    COUNT(*) FILTER (WHERE rapport_statut = 'avec')                         AS nb_rapport_avec,
    COUNT(*) FILTER (WHERE rapport_statut = 'sans')                         AS nb_rapport_sans,
    COUNT(*) FILTER (WHERE rapport_statut = 'non_verifie')                  AS nb_rapport_non_verifie,
    COUNT(*) FILTER (WHERE rapport_statut = 'erreur_api')                   AS nb_rapport_erreur
FROM rex.f_operations
WHERE work_type = 'corrective'
GROUP BY jour_creation, status, type_fin,
         societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
         provider_id, contract_reference, metier, contract_status;
CREATE INDEX ON rex.f_curatif_jour (jour);
CREATE INDEX ON rex.f_curatif_jour (provider_id, jour);
CREATE INDEX ON rex.f_curatif_jour (agence_reference, jour);
CREATE INDEX ON rex.f_curatif_jour (programme_reference);
CREATE INDEX ON rex.f_curatif_jour (contract_reference);
CREATE INDEX ON rex.f_curatif_jour (status, jour);
ANALYZE rex.f_curatif_jour;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'f_curatif_jour', COUNT(*) FROM rex.f_curatif_jour;

-- ---------------------------------------------------------------- PRÉVENTIF : programme prévu (jour = date prévue)
-- date_source dit d'où vient le jour : evenement_courant, historique_planned, ou creation_par_defaut
-- (la date prévue n'existe pas dans la donnée : on classe par date de création et on le dit).
DROP TABLE IF EXISTS rex.f_preventif_prevu_jour CASCADE;
CREATE TABLE rex.f_preventif_prevu_jour AS
SELECT
    COALESCE(rex.jour_paris(date_prevue), jour_creation)                    AS jour,
    COALESCE(date_prevue_source, 'creation_par_defaut')                     AS date_source,
    societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
    provider_id, contract_reference, metier, contract_status,
    COUNT(*) FILTER (WHERE preventive_prevue)                               AS nb_prevus,
    COUNT(*) FILTER (WHERE preventive_realisee)                             AS nb_realises,
    COUNT(*) FILTER (WHERE preventive_realisee_dans_delai)                  AS nb_realises_dans_delai,
    COUNT(*) FILTER (WHERE preventive_realisee_en_retard)                   AS nb_realises_en_retard,
    COUNT(*) FILTER (WHERE preventive_realisee AND preventive_realisee_dans_delai IS NULL) AS nb_realises_ponctualite_inconnue,
    COUNT(*) FILTER (WHERE preventive_restante)                             AS nb_restants,
    COUNT(*) FILTER (WHERE preventive_actuellement_en_retard)               AS nb_actuellement_en_retard,
    COUNT(*) FILTER (WHERE preventive_annulee)                              AS nb_annules,
    COUNT(*) FILTER (WHERE preventive_cloturee_non_realisee)                AS nb_cloturees_non_realisees,
    COUNT(*) FILTER (WHERE est_refusee AND NOT est_annulee)                 AS nb_refusees_hors_programme,
    SUM(nb_replanifications) FILTER (WHERE preventive_prevue)               AS nb_replanifications,
    COUNT(*) FILTER (WHERE preventive_realisee AND rapport_statut = 'avec')        AS nb_rapport_avec,
    COUNT(*) FILTER (WHERE preventive_realisee AND rapport_statut = 'sans')        AS nb_rapport_sans,
    COUNT(*) FILTER (WHERE preventive_realisee AND rapport_statut = 'non_verifie') AS nb_rapport_non_verifie,
    COUNT(*) FILTER (WHERE preventive_realisee AND rapport_statut = 'erreur_api')  AS nb_rapport_erreur
FROM rex.f_operations
WHERE work_type = 'preventive'
GROUP BY 1, 2, societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
         provider_id, contract_reference, metier, contract_status;
CREATE INDEX ON rex.f_preventif_prevu_jour (jour);
CREATE INDEX ON rex.f_preventif_prevu_jour (provider_id, jour);
CREATE INDEX ON rex.f_preventif_prevu_jour (agence_reference, jour);
CREATE INDEX ON rex.f_preventif_prevu_jour (programme_reference);
CREATE INDEX ON rex.f_preventif_prevu_jour (contract_reference);
ANALYZE rex.f_preventif_prevu_jour;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'f_preventif_prevu_jour', COUNT(*) FROM rex.f_preventif_prevu_jour;

-- ---------------------------------------------------------------- PRÉVENTIF : activité réalisée (jour = date de réalisation)
DROP TABLE IF EXISTS rex.f_preventif_realise_jour CASCADE;
CREATE TABLE rex.f_preventif_realise_jour AS
SELECT
    rex.jour_paris(date_realisation)                                        AS jour,
    societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
    provider_id, contract_reference, metier, contract_status,
    COUNT(*)                                                                AS nb_realises,
    COUNT(*) FILTER (WHERE preventive_realisee_dans_delai)                  AS nb_realises_dans_delai,
    COUNT(*) FILTER (WHERE preventive_realisee_en_retard)                   AS nb_realises_en_retard,
    COUNT(*) FILTER (WHERE preventive_realisee_dans_delai IS NULL)          AS nb_ponctualite_inconnue
FROM rex.f_operations
WHERE preventive_realisee AND date_realisation IS NOT NULL
GROUP BY 1, societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
         provider_id, contract_reference, metier, contract_status;
CREATE INDEX ON rex.f_preventif_realise_jour (jour);
CREATE INDEX ON rex.f_preventif_realise_jour (provider_id, jour);
CREATE INDEX ON rex.f_preventif_realise_jour (agence_reference, jour);
ANALYZE rex.f_preventif_realise_jour;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'f_preventif_realise_jour', COUNT(*) FROM rex.f_preventif_realise_jour;

-- ---------------------------------------------------------------- ÉQUIPEMENTS (curatives non refusées ayant un équipement)
DROP TABLE IF EXISTS rex.f_equipement_jour CASCADE;
CREATE TABLE rex.f_equipement_jour AS
SELECT
    jour_creation                                                           AS jour,
    equipment_reference,
    societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
    provider_id, contract_reference, metier, contract_status,
    COUNT(*)                                                                AS nb_pannes,
    MAX(creation_date)                                                      AS derniere_panne
FROM rex.f_operations
WHERE perimetre_curatif AND equipment_reference IS NOT NULL
GROUP BY jour_creation, equipment_reference,
         societe_reference, agence_reference, groupe_reference, secteur_reference, programme_reference,
         provider_id, contract_reference, metier, contract_status;
CREATE INDEX ON rex.f_equipement_jour (jour);
CREATE INDEX ON rex.f_equipement_jour (equipment_reference);
CREATE INDEX ON rex.f_equipement_jour (provider_id, jour);
CREATE INDEX ON rex.f_equipement_jour (agence_reference, jour);
ANALYZE rex.f_equipement_jour;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'f_equipement_jour', COUNT(*) FROM rex.f_equipement_jour;
-- ============================================================================
-- 40. rex.f_anomalies : une ligne par intervention et par anomalie, pour la page Anomalies (page d'actions).
-- Les seuils viennent de rex.parametre. Les cas massifs sans action unitaire possible (curatives sans SLA,
-- clôturées non vérifiées, interventions sans équipement) restent des compteurs dans les tables agrégées.
-- gravite : 3 = à traiter, 2 = à qualifier, 1 = information
-- ============================================================================
SET work_mem = '256MB';

DROP TABLE IF EXISTS rex.f_anomalies CASCADE;
CREATE TABLE rex.f_anomalies AS
WITH p AS (
    SELECT (SELECT valeur FROM rex.parametre WHERE code = 'seuil_preventif_retard_jours')::int AS seuil_prev,
           (SELECT valeur FROM rex.parametre WHERE code = 'seuil_curatif_ouvert_jours')::int   AS seuil_ouvert,
           (SELECT valeur FROM rex.parametre WHERE code = 'seuil_curatif_sans_maj_jours')::int AS seuil_maj
),
base AS (
    SELECT o.operation_key, o.reference, o.work_type, o.status, o.event,
           o.societe_reference, o.agence_reference, o.groupe_reference, o.secteur_reference, o.programme_reference,
           o.provider_id, o.provider_name, o.contract_reference, o.metier, o.equipment_reference,
           o.creation_date, o.last_update_date, o.event_date, o.first_event_date
    FROM rex.f_operations o
),
a AS (
    -- 1. Préventives en retard depuis longtemps
    SELECT o.operation_key, 'PREV_RETARD_ANCIEN'::text AS anomalie_code, 'Retard'::text AS famille,
           CASE WHEN o.jours_retard_actuel > 365 THEN 2 ELSE 3 END AS gravite,
           CASE WHEN o.jours_retard_actuel > 1095 THEN 'Prévue il y a plus de 3 ans, jamais clôturée'
                WHEN o.jours_retard_actuel > 365  THEN 'Prévue il y a plus d''un an, jamais clôturée'
                ELSE 'Date prévue dépassée de plus de ' || (SELECT seuil_prev FROM p) || ' jours' END AS detail,
           o.jours_retard_actuel AS anciennete_jours,
           o.event_date AS date_reference
    FROM rex.f_operations o
    WHERE o.preventive_actuellement_en_retard AND o.jours_retard_actuel > (SELECT seuil_prev FROM p)
    UNION ALL
    -- 2. Curatives en cours depuis longtemps
    SELECT o.operation_key, 'CUR_OUVERTE_ANCIENNE', 'Retard', 3,
           'Curative encore en cours depuis plus de ' || (SELECT seuil_ouvert FROM p) || ' jours',
           (CURRENT_DATE - rex.jour_paris(o.creation_date)), o.creation_date
    FROM rex.f_operations o
    WHERE o.est_curative AND o.est_en_cours
      AND o.creation_date < now() - ((SELECT seuil_ouvert FROM p) || ' days')::interval
    UNION ALL
    -- 3. Curatives en cours sans mise à jour
    SELECT o.operation_key, 'CUR_SANS_MAJ', 'Retard', 2,
           'Aucune mise à jour depuis plus de ' || (SELECT seuil_maj FROM p) || ' jours',
           (CURRENT_DATE - rex.jour_paris(o.last_update_date)), o.last_update_date
    FROM rex.f_operations o
    WHERE o.est_curative AND o.est_en_cours
      AND o.last_update_date < now() - ((SELECT seuil_maj FROM p) || ' days')::interval
    UNION ALL
    -- 4. Dates aberrantes
    SELECT o.operation_key, 'DATE_ABERRANTE', 'Données incohérentes', 2,
           'Date avant 2000 ou dans plus de 2 ans (événement ou premier événement)',
           NULL::int, COALESCE(o.event_date, o.first_event_date)
    FROM rex.f_operations o
    WHERE (o.est_curative OR o.est_preventive)
      AND (o.event_date < DATE '2000-01-01' OR o.first_event_date < DATE '2000-01-01' OR o.creation_date < DATE '2000-01-01'
           OR o.event_date > now() + INTERVAL '2 years')
    UNION ALL
    -- 5. Durée technique à -1
    SELECT o.operation_key, 'DUREE_MOINS1', 'Données incohérentes', 1,
           'Durée mesurée à -1 (valeur technique non exploitable)', NULL::int, o.creation_date
    FROM rex.f_operations o
    WHERE (o.est_curative OR o.est_preventive) AND (o.pec_moins1 OR o.res_moins1)
    UNION ALL
    -- 6. Durée à 0
    SELECT o.operation_key, 'DUREE_ZERO', 'Données incohérentes', 1,
           'Durée mesurée à 0 ms (exclue des calculs de délai)', NULL::int, o.creation_date
    FROM rex.f_operations o
    WHERE (o.est_curative OR o.est_preventive) AND (o.pec_zero OR o.res_zero)
    UNION ALL
    -- 7. SLA exprimé en mois : conservé, évalué à part
    SELECT o.operation_key, 'SLA_EN_MOIS', 'Contrats', 1,
           'SLA exprimé en mois (' || COALESCE(o.sla_intervention_mois, o.sla_recovery_mois) || ' mois) : suivi à part',
           NULL::int, o.creation_date
    FROM rex.f_operations o
    WHERE o.est_curative AND (o.sla_intervention_mois IS NOT NULL OR o.sla_recovery_mois IS NOT NULL)
    UNION ALL
    -- 8. Unité de SLA inconnue
    SELECT o.operation_key, 'SLA_UNITE_INCONNUE', 'Contrats', 2,
           'Unité de SLA non reconnue : ' || COALESCE(o.sla_intervention_unit, o.sla_recovery_unit),
           NULL::int, o.creation_date
    FROM rex.f_operations o
    WHERE (o.est_curative OR o.est_preventive) AND o.sla_unite_inconnue
    UNION ALL
    -- 9. Type de travaux absent
    SELECT o.operation_key, 'SANS_TYPE_TRAVAUX', 'Données incohérentes', 2,
           'Type de travaux (work_type) absent : l''intervention n''entre dans aucun indicateur', NULL::int, o.creation_date
    FROM rex.f_operations o
    WHERE o.work_type IS NULL
    UNION ALL
    -- 10. Rattachement patrimoine incomplet
    SELECT o.operation_key, 'SANS_PROGRAMME', 'Patrimoine', 2,
           'Intervention non rattachée à un programme', NULL::int, o.creation_date
    FROM rex.f_operations o
    WHERE (o.est_curative OR o.est_preventive) AND o.programme_reference IS NULL
    UNION ALL
    -- 11. Rapports
    SELECT o.operation_key, 'CLOTURE_SANS_RAPPORT', 'Rapports', 3,
           'Intervention clôturée sans rapport dans Intent', NULL::int, o.event_date
    FROM rex.f_operations o
    WHERE (o.est_curative OR o.est_preventive) AND o.rapport_statut = 'sans'
    UNION ALL
    SELECT o.operation_key, 'RAPPORT_ERREUR_API', 'Rapports', 2,
           'Contrôle du rapport en erreur : ' || LEFT(o.api_error, 120), NULL::int, o.document_checked_at
    FROM rex.f_operations o
    WHERE (o.est_curative OR o.est_preventive) AND o.rapport_statut = 'erreur_api'
)
SELECT a.operation_key, b.reference, a.anomalie_code, a.famille, a.gravite::smallint AS gravite, a.detail,
       a.anciennete_jours, a.date_reference,
       b.work_type, b.status, b.event,
       b.societe_reference, b.agence_reference, b.groupe_reference, b.secteur_reference, b.programme_reference,
       b.provider_id, b.provider_name, b.contract_reference, b.metier, b.equipment_reference
FROM a
JOIN base b USING (operation_key);

CREATE INDEX ON rex.f_anomalies (anomalie_code);
CREATE INDEX ON rex.f_anomalies (famille, gravite);
CREATE INDEX ON rex.f_anomalies (provider_id, anomalie_code);
CREATE INDEX ON rex.f_anomalies (agence_reference, anomalie_code);
CREATE INDEX ON rex.f_anomalies (operation_key);
ANALYZE rex.f_anomalies;
INSERT INTO rex.build_log (etape, nb_lignes) SELECT 'f_anomalies', COUNT(*) FROM rex.f_anomalies;