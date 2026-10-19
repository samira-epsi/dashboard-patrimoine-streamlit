
"""
RAFRAÎCHISSEMENT DES TABLES LÉGÈRES POSTGRESQL

Fonctionnement :
1. Connexion à PostgreSQL via le .env principal
2. Vérification de la procédure de rafraîchissement
3. Exécution de dashboard.refresh_tables_legeres()
4. Vérification de l'existence des 9 tables
5. Contrôle des doublons sur les grains importants
6. Affichage des volumes de chaque table
7. Mise à jour des statistiques PostgreSQL (ANALYZE)
8. Vérification finale et bilan d'exécution

Aucune connexion Supabase.
Aucun transfert de données.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# =====================================================
# CONFIGURATION
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

SCHEMA = "dashboard"

LOCAL_REFRESH_PROCEDURE = "dashboard.refresh_tables_legeres"

REFRESH_LOCAL_TABLES = True

# Tables légères à contrôler
TABLES = [
    "alertes_couverture",
    "contrats_patrimoine",
    "contrats_prestations",
    "equipements_contrats",
    "equipements_couverture",
    "esi_couverture",
    "kpi_creation_detail",
    "kpi_globale",
    "qualite_donnees",
]


# =====================================================
# CONNEXION POSTGRESQL
# =====================================================

def construire_moteur_local() -> Engine:
    """Connexion PostgreSQL depuis le .env principal."""

    db_url = os.getenv("DB_URL")

    if not db_url:
        raise RuntimeError(
            "Variable DB_URL introuvable. "
            f"Vérifie le fichier {PROJECT_ROOT / '.env'}"
        )

    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": 10
        },
    )

    return engine


def verifier_connexion(engine: Engine) -> None:
    """Teste la connexion et affiche la base utilisée."""

    print("\nTest de connexion PostgreSQL...")

    with engine.connect() as connection:
        resultat = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    print(f"Connexion réussie : {resultat}")


# =====================================================
# OUTILS SQL
# =====================================================

def table_exists(
    engine: Engine,
    schema: str,
    table_name: str,
) -> bool:
    """Vérifie qu'une table existe."""

    with engine.connect() as connection:
        resultat = connection.execute(
            text("SELECT to_regclass(:nom_complet)"),
            {
                "nom_complet": f"{schema}.{table_name}"
            },
        ).scalar()

    return resultat is not None


def procedure_exists(
    engine: Engine,
    schema: str,
    procedure_name: str,
) -> bool:
    """Vérifie qu'une procédure PostgreSQL existe."""

    requete = text("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_proc p
            JOIN pg_namespace n
                ON n.oid = p.pronamespace
            WHERE n.nspname = :schema
              AND p.proname = :procedure_name
              AND p.prokind = 'p'
              AND p.pronargs = 0
        )
    """)

    with engine.connect() as connection:
        resultat = connection.execute(
            requete,
            {
                "schema": schema,
                "procedure_name": procedure_name,
            },
        ).scalar_one()

    return bool(resultat)


def compter_lignes(
    engine: Engine,
    schema: str,
    table_name: str,
) -> int:
    """Compte les lignes d'une table."""

    with engine.connect() as connection:
        resultat = connection.execute(
            text(
                f'SELECT COUNT(*) '
                f'FROM "{schema}"."{table_name}"'
            )
        ).scalar_one()

    return int(resultat)


# =====================================================
# RAFRAÎCHISSEMENT DES TABLES LÉGÈRES
# =====================================================

def rafraichir_tables_locales(
    engine: Engine,
) -> None:
    """Exécute la procédure de rafraîchissement."""

    if not REFRESH_LOCAL_TABLES:
        print("\nRafraîchissement désactivé.")
        return

    schema_procedure, nom_procedure = (
        LOCAL_REFRESH_PROCEDURE.split(".", 1)
    )

    if not procedure_exists(
        engine,
        schema_procedure,
        nom_procedure,
    ):
        raise RuntimeError(
            "La procédure "
            f"{LOCAL_REFRESH_PROCEDURE}() "
            "n'existe pas."
        )

    print("\nRafraîchissement des tables légères...")

    debut = time.perf_counter()

    with engine.begin() as connection:
        connection.execute(
            text(
                f"CALL {LOCAL_REFRESH_PROCEDURE}()"
            )
        )

    duree = time.perf_counter() - debut

    print(
        "Tables légères rafraîchies avec succès "
        f"en {duree:.2f} secondes."
    )


# =====================================================
# VÉRIFICATION DES TABLES
# =====================================================

def verifier_sources_locales(
    engine: Engine,
) -> None:
    """Contrôle la présence des 9 tables légères."""

    print("\nVérification des tables...")

    objets_manquants = []

    for table_name in TABLES:

        if table_exists(
            engine,
            SCHEMA,
            table_name,
        ):
            print(f"  OK : {SCHEMA}.{table_name}")

        else:
            objets_manquants.append(
                f"{SCHEMA}.{table_name}"
            )

    if objets_manquants:
        raise RuntimeError(
            "Tables manquantes : "
            + ", ".join(objets_manquants)
        )

    print("\nToutes les tables sont présentes.")


# =====================================================
# CONTRÔLE DES DOUBLONS
# =====================================================

def verifier_grains_localement(
    engine: Engine,
) -> None:
    """Vérifie les grains importants des tables."""

    print("\nContrôle des doublons...")

    controles = [
        {
            "nom": "ESI",
            "requete": """
                SELECT
                    COUNT(*) - COUNT(DISTINCT esi_reference)
                FROM dashboard.esi_couverture
            """,
        },
        {
            "nom": "Équipements",
            "requete": """
                SELECT
                    COUNT(*) - COUNT(DISTINCT equipment_reference)
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

    with engine.connect() as connection:

        for controle in controles:

            nombre_doublons = int(
                connection.execute(
                    text(controle["requete"])
                ).scalar_one()
            )

            if nombre_doublons != 0:
                raise RuntimeError(
                    f"Contrôle échoué pour "
                    f"{controle['nom']} : "
                    f"{nombre_doublons} doublon(s)."
                )

            print(
                f"  OK : {controle['nom']}"
            )

    print("\nAucun doublon détecté sur les grains contrôlés.")


# =====================================================
# CONTRÔLE DES VOLUMES
# =====================================================

def afficher_volumes_locaux(
    engine: Engine,
) -> dict[str, int]:
    """Affiche et retourne les volumes des tables."""

    print("\nVolumes des tables légères :")

    volumes = {}

    for table_name in TABLES:

        nombre = compter_lignes(
            engine,
            SCHEMA,
            table_name,
        )

        volumes[table_name] = nombre

        print(
            f"  {SCHEMA}.{table_name} : "
            f"{nombre:,} ligne(s)"
        )

    print(
        f"\nNombre de tables : {len(volumes)}"
    )

    return volumes


# =====================================================
# OPTIMISATION POSTGRESQL
# =====================================================

def actualiser_statistiques(
    engine: Engine,
) -> None:
    """Exécute ANALYZE pour les tables légères."""

    print("\nActualisation des statistiques PostgreSQL...")

    for table_name in TABLES:

        with engine.begin() as connection:
            connection.execute(
                text(
                    f'ANALYZE "{SCHEMA}"."{table_name}"'
                )
            )

        print(
            f"  ANALYZE OK : {SCHEMA}.{table_name}"
        )

    print("\nStatistiques PostgreSQL actualisées.")


# =====================================================
# VÉRIFICATION FINALE
# =====================================================

def verifier_tables_finales(
    engine: Engine,
    volumes_attendus: dict[str, int],
) -> None:
    """Revérifie les volumes après les opérations."""

    print("\nContrôle final PostgreSQL :")

    erreur_detectee = False

    for table_name, volume_attendu in (
        volumes_attendus.items()
    ):

        volume_actuel = compter_lignes(
            engine,
            SCHEMA,
            table_name,
        )

        statut = (
            "OK"
            if volume_actuel == volume_attendu
            else "ERREUR"
        )

        print(
            f"  {SCHEMA}.{table_name} : "
            f"{volume_actuel:,} ligne(s) "
            f"[{statut}]"
        )

        if volume_actuel != volume_attendu:
            erreur_detectee = True

    if erreur_detectee:
        raise RuntimeError(
            "Un ou plusieurs volumes ont changé "
            "pendant les contrôles."
        )

    print("\nContrôle final terminé avec succès.")


# =====================================================
# PROGRAMME PRINCIPAL
# =====================================================

def main() -> None:

    debut_global = time.perf_counter()

    print("=" * 60)
    print("RAFRAÎCHISSEMENT DES TABLES LÉGÈRES")
    print("=" * 60)

    engine = construire_moteur_local()

    try:

        # 1. Tester la connexion PostgreSQL
        verifier_connexion(engine)

        # 2. Rafraîchir les tables légères
        rafraichir_tables_locales(engine)

        # 3. Vérifier l'existence des tables
        verifier_sources_locales(engine)

        # 4. Contrôler les doublons
        verifier_grains_localement(engine)

        # 5. Afficher les volumes
        volumes = afficher_volumes_locaux(engine)

        # 6. Actualiser les statistiques SQL
        actualiser_statistiques(engine)

        # 7. Contrôle final
        verifier_tables_finales(
            engine,
            volumes,
        )

        duree_totale = (
            time.perf_counter() - debut_global
        )

        print("\n" + "=" * 60)
        print("RAFRAÎCHISSEMENT TERMINÉ AVEC SUCCÈS")
        print(f"Tables contrôlées : {len(TABLES)}")
        print(f"Durée totale : {duree_totale:.2f} secondes")
        print("=" * 60)

    finally:
        engine.dispose()


# =====================================================
# EXÉCUTION
# =====================================================

if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nRafraîchissement annulé par l'utilisateur."
        )
        sys.exit(1)

    except Exception as erreur:
        print("\nÉCHEC DU RAFRAÎCHISSEMENT")
        print(str(erreur))
        sys.exit(1)
