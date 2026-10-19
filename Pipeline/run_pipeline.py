
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =====================================================
# CONFIGURATION
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

ENV = os.environ.copy()

ENV["PYTHONPATH"] = os.pathsep.join(
    filter(
        None,
        [
            str(PROJECT_ROOT),
            ENV.get("PYTHONPATH", ""),
        ],
    )
)


# =====================================================
# OUTILS
# =====================================================

def log(message):
    print(message, flush=True)


def lancer_module(module, *arguments):
    commande = [
        sys.executable,
        "-m",
        module,
        *arguments,
    ]

    log(f"\n▶ Exécution : {module}")
    log(f"Arguments : {' '.join(arguments) or 'aucun'}")

    debut = time.perf_counter()

    subprocess.run(
        commande,
        cwd=PROJECT_ROOT,
        env=ENV,
        check=True,
    )

    duree = time.perf_counter() - debut

    log(f"✓ {module} terminé en {duree:.1f}s")


def rafraichir_rex():
    db_url = os.getenv("DB_URL")

    if not db_url:
        raise RuntimeError(
            "DB_URL absent du fichier .env"
        )

    log("\n▶ Rafraîchissement du dashboard REX")

    debut = time.perf_counter()

    engine = create_engine(
        db_url,
        pool_pre_ping=True,
    )

    try:
        with engine.begin() as connexion:
            connexion.execute(
                text("CALL rex.refresh_dashboard()")
            )
    finally:
        engine.dispose()

    duree = time.perf_counter() - debut

    log(f"✓ Tables REX actualisées en {duree:.1f}s")


# =====================================================
# TDB 1 : PATRIMOINE
# =====================================================

def pipeline_patrimoine():
    log("\n" + "=" * 60)
    log("TDB 1 : PATRIMOINE")
    log("=" * 60)

    lancer_module(
        "Pipeline.les_different_code_main"
    )

    lancer_module(
        "Pipeline.update_data_tdb"
    )

    log("\n✓ TDB 1 TERMINÉ")


# =====================================================
# TDB 2 : REX
# =====================================================

def pipeline_rex(mode):
    log("\n" + "=" * 60)
    log("TDB 2 : REX")
    log(f"Mode opérations : {mode}")
    log("=" * 60)

    # 1. Synchronisation des interventions
    lancer_module(
        "Pipeline.update_operation",
        mode,
    )

    # 2. Enrichissement patrimoine
    lancer_module(
        "services.operations_asset_enrichment"
    )

    # 3. Reconstruction des indicateurs
    rafraichir_rex()

    log("\n✓ TDB 2 TERMINÉ")


# =====================================================
# ARGUMENTS DE LA COMMANDE
# =====================================================

def lire_arguments():
    parser = argparse.ArgumentParser(
        description="Orchestrateur des dashboards Patrimoine et REX"
    )

    parser.add_argument(
        "dashboard",
        choices=["patrimoine", "rex", "all"],
        help="Dashboard à actualiser",
    )

    parser.add_argument(
        "mode",
        nargs="?",
        choices=["daily", "reconcile", "certify"],
        default="daily",
        help="Mode de synchronisation des interventions REX",
    )

    return parser.parse_args()


# =====================================================
# PIPELINE PRINCIPAL
# =====================================================

def main():
    args = lire_arguments()

    debut = time.perf_counter()

    log("\n" + "=" * 60)
    log("ORCHESTRATEUR GLOBAL DATA")
    log(f"Dashboard demandé : {args.dashboard}")

    if args.dashboard in {"rex", "all"}:
        log(f"Mode interventions : {args.mode}")

    log("=" * 60)

    if args.dashboard in {"patrimoine", "all"}:
        pipeline_patrimoine()

    if args.dashboard in {"rex", "all"}:
        pipeline_rex(args.mode)

    duree = time.perf_counter() - debut

    log("\n" + "=" * 60)
    log("PIPELINE TERMINÉ AVEC SUCCÈS")
    log(f"Durée totale : {duree:.1f}s")
    log("=" * 60)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        log("\nPipeline interrompu par l'utilisateur.")
        sys.exit(130)

    except Exception as erreur:
        log(f"\nÉCHEC DU PIPELINE : {erreur}")
        sys.exit(1)
