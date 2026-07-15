from __future__ import annotations

import os
import sys
from getpass import getpass

import pandas as pd
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    Numeric,
    Text,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine, URL


# =====================================================
# CONFIGURATION
# =====================================================

SCHEMA = "dashboard"

# True : appelle automatiquement la procédure locale
# dashboard.refresh_tables_legeres() avant l'envoi.
REFRESH_LOCAL_TABLES = True

LOCAL_REFRESH_PROCEDURE = "dashboard.refresh_tables_legeres"

# Petit lot volontairement :
# contrats_prestations contient beaucoup de colonnes.
CHUNKSIZE = 500


# =====================================================
# TABLES LÉGÈRES À PUBLIER
# =====================================================

TABLES = [
    {
        "source_schema": "dashboard",
        "source_name": "alertes_couverture",
        "target_schema": "dashboard",
        "target_name": "alertes_couverture",
    },
    {
        "source_schema": "dashboard",
        "source_name": "contrats_patrimoine",
        "target_schema": "dashboard",
        "target_name": "contrats_patrimoine",
    },
    {
        "source_schema": "dashboard",
        "source_name": "contrats_prestations",
        "target_schema": "dashboard",
        "target_name": "contrats_prestations",
    },
    {
        "source_schema": "dashboard",
        "source_name": "equipements_contrats",
        "target_schema": "dashboard",
        "target_name": "equipements_contrats",
    },
    {
        "source_schema": "dashboard",
        "source_name": "equipements_couverture",
        "target_schema": "dashboard",
        "target_name": "equipements_couverture",
    },
    {
        "source_schema": "dashboard",
        "source_name": "esi_couverture",
        "target_schema": "dashboard",
        "target_name": "esi_couverture",
    },
    {
        "source_schema": "dashboard",
        "source_name": "kpi_creation_detail",
        "target_schema": "dashboard",
        "target_name": "kpi_creation_detail",
    },
    {
        "source_schema": "dashboard",
        "source_name": "kpi_globale",
        "target_schema": "dashboard",
        "target_name": "kpi_globale",
    },
    {
        "source_schema": "dashboard",
        "source_name": "qualite_donnees",
        "target_schema": "dashboard",
        "target_name": "qualite_donnees",
    },
]


# =====================================================
# INDEX SUPABASE
# =====================================================

INDEXES_SQL = [
    # Alertes
    """
    CREATE INDEX ix_alertes_couverture_type
    ON dashboard.alertes_couverture (
        alerte_type,
        priorite
    )
    """,
    """
    CREATE INDEX ix_alertes_couverture_esi
    ON dashboard.alertes_couverture (
        esi_reference
    )
    """,
    """
    CREATE INDEX ix_alertes_couverture_objet
    ON dashboard.alertes_couverture (
        objet_type,
        objet_reference
    )
    """,

    # Contrats et rattachements
    """
    CREATE UNIQUE INDEX ux_contrats_patrimoine
    ON dashboard.contrats_patrimoine (
        contract_reference,
        esi_reference
    )
    """,
    """
    CREATE INDEX ix_contrats_patrimoine_contrat
    ON dashboard.contrats_patrimoine (
        contract_reference
    )
    """,
    """
    CREATE INDEX ix_contrats_patrimoine_esi
    ON dashboard.contrats_patrimoine (
        esi_reference
    )
    """,
    """
    CREATE INDEX ix_contrats_patrimoine_filtres
    ON dashboard.contrats_patrimoine (
        contract_status,
        contract_topic,
        third_party_label
    )
    """,
    """
    CREATE INDEX ix_contrats_patrimoine_organisation
    ON dashboard.contrats_patrimoine (
        societe,
        agence,
        groupe,
        secteur
    )
    """,

    # Codes de prestation
    """
    CREATE UNIQUE INDEX ux_contrats_prestations_id
    ON dashboard.contrats_prestations (
        service_code_id_intent
    )
    WHERE service_code_id_intent IS NOT NULL
    """,
    """
    CREATE INDEX ix_contrats_prestations_contrat
    ON dashboard.contrats_prestations (
        contract_reference_3f
    )
    """,
    """
    CREATE INDEX ix_contrats_prestations_statut_metier
    ON dashboard.contrats_prestations (
        contract_status,
        contract_topic
    )
    """,
    """
    CREATE INDEX ix_contrats_prestations_prestataire
    ON dashboard.contrats_prestations (
        third_party_label
    )
    """,
    """
    CREATE INDEX ix_contrats_prestations_code_3f
    ON dashboard.contrats_prestations (
        service_code_reference_3f
    )
    """,
    """
    CREATE INDEX ix_contrats_prestations_code_prestataire
    ON dashboard.contrats_prestations (
        service_code_reference_prestataire
    )
    """,

    # Équipement × contrat
    """
    CREATE INDEX ix_equipements_contrats_equipement
    ON dashboard.equipements_contrats (
        equipment_reference
    )
    """,
    """
    CREATE INDEX ix_equipements_contrats_esi
    ON dashboard.equipements_contrats (
        esi_reference
    )
    """,
    """
    CREATE INDEX ix_equipements_contrats_contrat
    ON dashboard.equipements_contrats (
        contract_reference
    )
    """,
    """
    CREATE INDEX ix_equipements_contrats_filtres
    ON dashboard.equipements_contrats (
        contract_status,
        contract_topic
    )
    """,

    # Couverture équipement
    """
    CREATE UNIQUE INDEX ux_equipements_couverture_reference
    ON dashboard.equipements_couverture (
        equipment_reference
    )
    """,
    """
    CREATE INDEX ix_equipements_couverture_esi
    ON dashboard.equipements_couverture (
        esi_reference
    )
    """,
    """
    CREATE INDEX ix_equipements_couverture_statut
    ON dashboard.equipements_couverture (
        couverture_status
    )
    """,
    """
    CREATE INDEX ix_equipements_couverture_organisation
    ON dashboard.equipements_couverture (
        societe,
        agence,
        groupe,
        secteur
    )
    """,

    # Couverture ESI
    """
    CREATE UNIQUE INDEX ux_esi_couverture_reference
    ON dashboard.esi_couverture (
        esi_reference
    )
    """,
    """
    CREATE INDEX ix_esi_couverture_organisation
    ON dashboard.esi_couverture (
        societe,
        agence,
        groupe,
        secteur
    )
    """,

    # Créations
    """
    CREATE INDEX ix_kpi_creation_type_date
    ON dashboard.kpi_creation_detail (
        objet_type,
        creation_date
    )
    """,

    # Qualité
    """
    CREATE INDEX ix_qualite_donnees_type
    ON dashboard.qualite_donnees (
        anomalie_type,
        objet_type,
        gravite
    )
    """,
    """
    CREATE INDEX ix_qualite_donnees_objet
    ON dashboard.qualite_donnees (
        objet_reference
    )
    """,
    """
    CREATE INDEX ix_qualite_donnees_organisation
    ON dashboard.qualite_donnees (
        societe,
        agence,
        groupe,
        secteur
    )
    """,
]


# =====================================================
# VUE RÉSUMÉ QUALITÉ SUPABASE
# =====================================================

QUALITE_RESUME_SQL = """
CREATE VIEW dashboard.qualite_donnees_resume AS

SELECT
    anomalie_type,
    objet_type,
    gravite,
    description,

    COUNT(*) AS nombre_occurrences,

    COUNT(
        DISTINCT objet_reference
    ) AS nombre_objets_distincts,

    /* Compatibilité avec ton code Streamlit actuel */
    COUNT(*) AS nb_lignes_detail,

    COUNT(
        DISTINCT objet_reference
    ) AS nb_objets_distincts,

    MAX(date_maj) AS date_maj

FROM dashboard.qualite_donnees

GROUP BY
    anomalie_type,
    objet_type,
    gravite,
    description
"""


# =====================================================
# CONNEXIONS
# =====================================================

def construire_moteur_local(password: str) -> Engine:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username="postgres",
        password=password,
        host="localhost",
        port=5432,
        database="patrimoine",
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 10,
        },
    )


def construire_moteur_supabase(password: str) -> Engine:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username="postgres.ppjnxrqauxiyoyunaobf",
        password=password,
        host="aws-0-eu-west-1.pooler.supabase.com",
        port=5432,
        database="postgres",
        query={
            "sslmode": "require",
        },
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 15,
        },
    )


# =====================================================
# OUTILS SQL
# =====================================================

def table_exists(
    engine: Engine,
    schema: str,
    table_name: str,
) -> bool:
    with engine.connect() as connection:
        resultat = connection.execute(
            text("SELECT to_regclass(:nom_complet)"),
            {
                "nom_complet": f"{schema}.{table_name}",
            },
        ).scalar()

    return resultat is not None


def procedure_exists(
    engine: Engine,
    schema: str,
    procedure_name: str,
) -> bool:
    requete = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_proc p
            JOIN pg_namespace n
              ON n.oid = p.pronamespace
            WHERE n.nspname = :schema
              AND p.proname = :procedure_name
              AND p.prokind = 'p'
        )
        """
    )

    with engine.connect() as connection:
        return bool(
            connection.execute(
                requete,
                {
                    "schema": schema,
                    "procedure_name": procedure_name,
                },
            ).scalar()
        )


def compter_lignes(
    engine: Engine,
    schema: str,
    table_name: str,
) -> int:
    with engine.connect() as connection:
        resultat = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM "{schema}"."{table_name}"
                """
            )
        ).scalar_one()

    return int(resultat)


# =====================================================
# CONSERVATION DES TYPES POSTGRESQL
# =====================================================

def convertir_type_postgresql(data_type: str):
    correspondances = {
        "text": Text(),
        "character varying": Text(),
        "character": Text(),

        "bigint": BigInteger(),
        "integer": Integer(),
        "smallint": Integer(),

        "numeric": Numeric(),
        "decimal": Numeric(),
        "real": Float(),
        "double precision": Float(),

        "boolean": Boolean(),

        "date": Date(),

        "timestamp with time zone":
            DateTime(timezone=True),

        "timestamp without time zone":
            DateTime(timezone=False),
    }

    return correspondances.get(
        data_type,
        Text(),
    )


def recuperer_types_source(
    engine: Engine,
    schema: str,
    table_name: str,
) -> dict:
    requete = text(
        """
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table_name
        ORDER BY ordinal_position
        """
    )

    with engine.connect() as connection:
        colonnes = connection.execute(
            requete,
            {
                "schema": schema,
                "table_name": table_name,
            },
        ).mappings().all()

    if not colonnes:
        raise RuntimeError(
            f"Structure introuvable pour "
            f"{schema}.{table_name}"
        )

    return {
        colonne["column_name"]:
            convertir_type_postgresql(
                colonne["data_type"]
            )
        for colonne in colonnes
    }


# =====================================================
# RAFRAÎCHISSEMENT LOCAL
# =====================================================

def rafraichir_tables_locales(
    local_engine: Engine,
) -> None:
    if not REFRESH_LOCAL_TABLES:
        print(
            "\nRafraîchissement local désactivé."
        )
        return

    schema_procedure, nom_procedure = (
        LOCAL_REFRESH_PROCEDURE.split(".", 1)
    )

    if not procedure_exists(
        local_engine,
        schema_procedure,
        nom_procedure,
    ):
        raise RuntimeError(
            "La procédure locale "
            f"{LOCAL_REFRESH_PROCEDURE}() "
            "n'existe pas.\n"
            "Crée-la d'abord ou mets "
            "REFRESH_LOCAL_TABLES = False."
        )

    print(
        "\nRafraîchissement des tables légères locales..."
    )

    with local_engine.begin() as connection:
        connection.execute(
            text(
                f"CALL {LOCAL_REFRESH_PROCEDURE}()"
            )
        )

    print(
        "Tables légères locales rafraîchies."
    )

    print(
        "Mise à jour des statistiques locales..."
    )

    with local_engine.begin() as connection:
        for item in TABLES:
            source_schema = item["source_schema"]
            source_name = item["source_name"]

            connection.execute(
                text(
                    f"""
                    ANALYZE
                    "{source_schema}"."{source_name}"
                    """
                )
            )

    print(
        "Statistiques locales actualisées."
    )


# =====================================================
# CONTRÔLES LOCAUX
# =====================================================

def verifier_sources_locales(
    local_engine: Engine,
) -> None:
    objets_manquants = []

    for item in TABLES:
        schema = item["source_schema"]
        table_name = item["source_name"]

        if not table_exists(
            local_engine,
            schema,
            table_name,
        ):
            objets_manquants.append(
                f"{schema}.{table_name}"
            )

    if objets_manquants:
        raise RuntimeError(
            "Tables locales manquantes : "
            + ", ".join(objets_manquants)
        )


def verifier_grains_localement(
    local_engine: Engine,
) -> None:
    controles = [
        {
            "nom": "ESI",
            "requete": """
                SELECT
                    COUNT(*)
                    - COUNT(DISTINCT esi_reference)
                FROM dashboard.esi_couverture
            """,
        },
        {
            "nom": "Équipements",
            "requete": """
                SELECT
                    COUNT(*)
                    - COUNT(DISTINCT equipment_reference)
                FROM dashboard.equipements_couverture
            """,
        },
        {
            "nom": "Contrat × ESI",
            "requete": """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        contract_reference,
                        esi_reference
                    FROM dashboard.contrats_patrimoine
                    GROUP BY
                        contract_reference,
                        esi_reference
                    HAVING COUNT(*) > 1
                ) doublons
            """,
        },
    ]

    with local_engine.connect() as connection:
        for controle in controles:
            nombre_doublons = int(
                connection.execute(
                    text(controle["requete"])
                ).scalar_one()
            )

            if nombre_doublons != 0:
                raise RuntimeError(
                    f"Contrôle du grain échoué pour "
                    f"{controle['nom']} : "
                    f"{nombre_doublons} doublon(s)."
                )

            print(
                f"Contrôle grain {controle['nom']} : OK"
            )


def afficher_volumes_locaux(
    local_engine: Engine,
) -> None:
    print("\nVolumes locaux à publier :")

    for item in TABLES:
        nombre = compter_lignes(
            local_engine,
            item["source_schema"],
            item["source_name"],
        )

        print(
            f"  {item['source_schema']}."
            f"{item['source_name']} : "
            f"{nombre:,} ligne(s)"
        )


# =====================================================
# CHARGEMENT DES TABLES TEMPORAIRES SUPABASE
# =====================================================

def nettoyer_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    dataframe = dataframe.copy()

    # Évite certains problèmes pandas / psycopg2
    # avec pd.NA dans les colonnes texte.
    for colonne in dataframe.columns:
        if (
            pd.api.types.is_object_dtype(
                dataframe[colonne]
            )
            or pd.api.types.is_string_dtype(
                dataframe[colonne]
            )
        ):
            dataframe[colonne] = dataframe[
                colonne
            ].where(
                dataframe[colonne].notna(),
                None,
            )

    return dataframe


def charger_tables_temporaires(
    local_engine: Engine,
    supabase_engine: Engine,
) -> dict[str, int]:
    volumes_attendus: dict[str, int] = {}

    with supabase_engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE SCHEMA IF NOT EXISTS
                "{SCHEMA}"
                """
            )
        )

    for item in TABLES:
        source_schema = item["source_schema"]
        source_name = item["source_name"]

        target_schema = item["target_schema"]
        target_name = item["target_name"]

        table_temporaire = (
            f"__sync_{target_name}"
        )

        print(
            f"\nLecture locale : "
            f"{source_schema}.{source_name}"
        )

        dataframe = pd.read_sql_query(
            text(
                f"""
                SELECT *
                FROM "{source_schema}"."{source_name}"
                """
            ),
            local_engine,
        )

        dataframe = nettoyer_dataframe(
            dataframe
        )

        nombre_local = len(dataframe)

        print(
            f"  {nombre_local:,} ligne(s) récupérée(s)"
        )

        types_colonnes = recuperer_types_source(
            local_engine,
            source_schema,
            source_name,
        )

        print(
            f"Chargement temporaire Supabase : "
            f"{target_schema}.{table_temporaire}"
        )

        dataframe.to_sql(
            name=table_temporaire,
            con=supabase_engine,
            schema=target_schema,
            if_exists="replace",
            index=False,
            chunksize=CHUNKSIZE,
            method="multi",
            dtype=types_colonnes,
        )

        nombre_supabase = compter_lignes(
            supabase_engine,
            target_schema,
            table_temporaire,
        )

        if nombre_supabase != nombre_local:
            raise RuntimeError(
                f"Écart de lignes pour {target_name} : "
                f"local={nombre_local:,}, "
                f"Supabase={nombre_supabase:,}"
            )

        volumes_attendus[target_name] = (
            nombre_local
        )

        print(
            f"  Contrôle réussi : "
            f"{nombre_supabase:,} ligne(s)"
        )

    return volumes_attendus


# =====================================================
# REMPLACEMENT SÉCURISÉ DES TABLES SUPABASE
# =====================================================

def remplacer_tables_finales(
    supabase_engine: Engine,
) -> None:
    print(
        "\nRemplacement sécurisé des tables Supabase..."
    )

    with supabase_engine.begin() as connection:
        # Dépend de qualite_donnees.
        connection.execute(
            text(
                """
                DROP VIEW IF EXISTS
                    dashboard.qualite_donnees_resume
                """
            )
        )

        for item in TABLES:
            target_schema = item["target_schema"]
            target_name = item["target_name"]

            table_temporaire = (
                f"__sync_{target_name}"
            )

            connection.execute(
                text(
                    f"""
                    DROP TABLE IF EXISTS
                    "{target_schema}"."{target_name}"
                    """
                )
            )

            connection.execute(
                text(
                    f"""
                    ALTER TABLE
                    "{target_schema}"."{table_temporaire}"
                    RENAME TO "{target_name}"
                    """
                )
            )

        print(
            "Recréation des index..."
        )

        for requete_index in INDEXES_SQL:
            connection.execute(
                text(requete_index)
            )

        print(
            "Recréation de la vue résumé qualité..."
        )

        connection.execute(
            text(QUALITE_RESUME_SQL)
        )

        print(
            "Mise à jour des statistiques Supabase..."
        )

        for item in TABLES:
            target_schema = item["target_schema"]
            target_name = item["target_name"]

            connection.execute(
                text(
                    f"""
                    ANALYZE
                    "{target_schema}"."{target_name}"
                    """
                )
            )

    print(
        "Remplacement Supabase terminé."
    )


# =====================================================
# CONTRÔLE FINAL
# =====================================================

def verifier_tables_finales(
    supabase_engine: Engine,
    volumes_attendus: dict[str, int],
) -> None:
    print(
        "\nContrôle final Supabase :"
    )

    erreur_detectee = False

    for table_name, volume_attendu in (
        volumes_attendus.items()
    ):
        volume_supabase = compter_lignes(
            supabase_engine,
            SCHEMA,
            table_name,
        )

        statut = (
            "OK"
            if volume_supabase == volume_attendu
            else "ERREUR"
        )

        print(
            f"  dashboard.{table_name} : "
            f"{volume_supabase:,} ligne(s) "
            f"[{statut}]"
        )

        if volume_supabase != volume_attendu:
            erreur_detectee = True

    if erreur_detectee:
        raise RuntimeError(
            "Au moins une table Supabase contient "
            "un nombre de lignes incorrect."
        )

    if not table_exists(
        supabase_engine,
        "dashboard",
        "qualite_donnees_resume",
    ):
        raise RuntimeError(
            "La vue dashboard.qualite_donnees_resume "
            "n'a pas été créée."
        )

    print(
        "  dashboard.qualite_donnees_resume : OK"
    )


# =====================================================
# PROGRAMME PRINCIPAL
# =====================================================

def main() -> None:
    local_password = (
        os.getenv("LOCAL_DB_PASSWORD")
        or getpass(
            "Mot de passe PostgreSQL local : "
        )
    )

    supabase_password = (
        os.getenv("SUPABASE_DB_PASSWORD")
        or getpass(
            "Mot de passe Supabase : "
        )
    )

    local_engine = construire_moteur_local(
        local_password
    )

    supabase_engine = construire_moteur_supabase(
        supabase_password
    )

    try:
        print(
            "\nTest de la connexion PostgreSQL locale..."
        )

        with local_engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        print(
            "Connexion locale réussie."
        )

        print(
            "\nTest de la connexion Supabase..."
        )

        with supabase_engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        print(
            "Connexion Supabase réussie."
        )

        # 1. Actualise les tables légères depuis les vues _next.
        rafraichir_tables_locales(
            local_engine
        )

        # 2. Vérifie que les 9 tables existent.
        verifier_sources_locales(
            local_engine
        )

        # 3. Vérifie les grains importants.
        verifier_grains_localement(
            local_engine
        )

        # 4. Affiche les volumes avant transfert.
        afficher_volumes_locaux(
            local_engine
        )

        # 5. Charge d'abord les tables temporaires.
        volumes_attendus = (
            charger_tables_temporaires(
                local_engine,
                supabase_engine,
            )
        )

        # 6. Remplace les tables finales seulement
        # si tous les chargements temporaires ont réussi.
        remplacer_tables_finales(
            supabase_engine
        )

        # 7. Vérifie chaque table finale.
        verifier_tables_finales(
            supabase_engine,
            volumes_attendus,
        )

        print(
            "\nSynchronisation terminée avec succès."
        )

    finally:
        local_engine.dispose()
        supabase_engine.dispose()


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nSynchronisation annulée par l'utilisateur."
        )
        sys.exit(1)

    except Exception as erreur:
        print(
            "\nÉCHEC DE LA SYNCHRONISATION"
        )
        print(
            str(erreur)
        )
        sys.exit(1)