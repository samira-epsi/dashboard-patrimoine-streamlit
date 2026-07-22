from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# ============================================================
# CONFIGURATION GÉNÉRALE
# ============================================================

PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
LOG_DIR = PIPELINE_DIR / "logs"
LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RUN_ID = str(uuid.uuid4())

# Ton rafraîchissement peut prendre environ 40 minutes.
# On autorise donc jusqu'à 4 heures par étape.
DEFAULT_TIMEOUT_SECONDS = 4 * 60 * 60


# ============================================================
# DESCRIPTION D'UNE ÉTAPE
# ============================================================

@dataclass(frozen=True)
class PipelineStep:
    name: str
    script: Path
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    enabled: bool = True


# ============================================================
# ÉTAPES DE TON PIPELINE
# ============================================================

PIPELINE_STEPS = [
    PipelineStep(
        name="Extraction et mise à jour Intent",
        script=PIPELINE_DIR / "les_different_code_main.py",
    ),
    PipelineStep(
        name="Rafraîchissement dashboard et publication Supabase",
        script=PIPELINE_DIR / "push_dashboard_to_supabase.py",
    ),
]


# ============================================================
# LOGS
# ============================================================

def configurer_logger() -> tuple[logging.Logger, Path]:
    """
    Affiche les logs dans le terminal et les enregistre
    également dans un fichier.
    """

    horodatage = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    fichier_log = (
        LOG_DIR
        / f"pipeline_{horodatage}.log"
    )

    logger = logging.getLogger(
        "pipeline_dashboard"
    )

    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    format_logs = logging.Formatter(
        fmt=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler_terminal = logging.StreamHandler(
        sys.stdout
    )
    handler_terminal.setFormatter(
        format_logs
    )

    handler_fichier = logging.FileHandler(
        fichier_log,
        encoding="utf-8",
    )
    handler_fichier.setFormatter(
        format_logs
    )

    logger.addHandler(
        handler_terminal
    )
    logger.addHandler(
        handler_fichier
    )

    return logger, fichier_log


# ============================================================
# UTILITAIRES
# ============================================================

def formater_duree(
    duree_secondes: float,
) -> str:
    """
    Transforme une durée en texte lisible.
    """

    total = int(duree_secondes)

    heures, reste = divmod(
        total,
        3600,
    )

    minutes, secondes = divmod(
        reste,
        60,
    )

    if heures > 0:
        return (
            f"{heures} h "
            f"{minutes} min "
            f"{secondes} s"
        )

    if minutes > 0:
        return (
            f"{minutes} min "
            f"{secondes} s"
        )

    return f"{secondes} s"


def verifier_scripts() -> None:
    """
    Vérifie que tous les fichiers nécessaires existent
    avant de démarrer.
    """

    scripts_manquants = []

    for etape in PIPELINE_STEPS:
        if not etape.enabled:
            continue

        if not etape.script.exists():
            scripts_manquants.append(
                str(etape.script)
            )

    if scripts_manquants:
        raise FileNotFoundError(
            "Les scripts suivants sont introuvables :\n"
            + "\n".join(
                scripts_manquants
            )
        )


def construire_environnement() -> dict[str, str]:
    """
    Prépare les variables d'environnement transmises
    aux scripts exécutés.
    """

    environnement = os.environ.copy()

    environnement[
        "PIPELINE_RUN_ID"
    ] = RUN_ID

    environnement[
        "PIPELINE_STARTED_AT"
    ] = datetime.now().astimezone().isoformat()

    environnement[
        "PYTHONUNBUFFERED"
    ] = "1"

    return environnement


# ============================================================
# EXÉCUTION D'UN SCRIPT
# ============================================================

def executer_etape(
    etape: PipelineStep,
    logger: logging.Logger,
    environnement: dict[str, str],
) -> None:
    """
    Lance un script Python.
    Les sorties sont affichées et enregistrées en direct.
    """

    logger.info("")
    logger.info("=" * 72)
    logger.info(
        "DÉBUT DE L'ÉTAPE : %s",
        etape.name,
    )
    logger.info(
        "Script : %s",
        etape.script,
    )
    logger.info("=" * 72)

    debut = time.perf_counter()

    commande = [
        sys.executable,
        "-u",
        str(etape.script),
    ]

    processus = subprocess.Popen(
        commande,
        cwd=str(PROJECT_ROOT),
        env=environnement,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=None,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    try:
        if processus.stdout is not None:
            for ligne in processus.stdout:
                ligne = ligne.rstrip()

                if ligne:
                    logger.info(
                        "[%s] %s",
                        etape.name,
                        ligne,
                    )

        code_retour = processus.wait(
            timeout=etape.timeout_seconds
        )

    except subprocess.TimeoutExpired as erreur:
        processus.kill()
        processus.wait()

        duree = (
            time.perf_counter()
            - debut
        )

        raise RuntimeError(
            f"L'étape « {etape.name} » "
            f"a dépassé la durée maximale de "
            f"{formater_duree(etape.timeout_seconds)}. "
            f"Elle a été arrêtée après "
            f"{formater_duree(duree)}."
        ) from erreur

    except KeyboardInterrupt:
        logger.warning(
            "Interruption de l'étape « %s ».",
            etape.name,
        )

        processus.terminate()

        try:
            processus.wait(
                timeout=10
            )

        except subprocess.TimeoutExpired:
            processus.kill()
            processus.wait()

        raise

    duree = (
        time.perf_counter()
        - debut
    )

    if code_retour != 0:
        raise RuntimeError(
            f"L'étape « {etape.name} » "
            f"a échoué avec le code "
            f"{code_retour}. "
            f"Durée : {formater_duree(duree)}."
        )

    logger.info(
        "SUCCÈS : %s",
        etape.name,
    )

    logger.info(
        "Durée de l'étape : %s",
        formater_duree(duree),
    )


# ============================================================
# EXÉCUTION DU PIPELINE COMPLET
# ============================================================

def executer_pipeline(
    logger: logging.Logger,
) -> None:
    """
    Exécute toutes les étapes dans l'ordre.

    Si l'extraction échoue, la publication Supabase
    n'est pas lancée.
    """

    verifier_scripts()

    environnement = (
        construire_environnement()
    )

    debut_pipeline = (
        time.perf_counter()
    )

    nombre_etapes_executees = 0

    logger.info("#" * 72)
    logger.info("DÉMARRAGE DU PIPELINE PATRIMOINE")
    logger.info("Run ID : %s", RUN_ID)
    logger.info(
        "Dossier du projet : %s",
        PROJECT_ROOT,
    )
    logger.info(
        "Interpréteur Python : %s",
        sys.executable,
    )
    logger.info("#" * 72)

    for etape in PIPELINE_STEPS:
        if not etape.enabled:
            logger.info(
                "Étape désactivée : %s",
                etape.name,
            )
            continue

        executer_etape(
            etape=etape,
            logger=logger,
            environnement=environnement,
        )

        nombre_etapes_executees += 1

    duree_totale = (
        time.perf_counter()
        - debut_pipeline
    )

    logger.info("")
    logger.info("#" * 72)
    logger.info(
        "PIPELINE TERMINÉ AVEC SUCCÈS"
    )
    logger.info(
        "Run ID : %s",
        RUN_ID,
    )
    logger.info(
        "Étapes exécutées : %s",
        nombre_etapes_executees,
    )
    logger.info(
        "Durée totale : %s",
        formater_duree(duree_totale),
    )
    logger.info("#" * 72)


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main() -> int:
    logger, fichier_log = (
        configurer_logger()
    )

    logger.info(
        "Fichier de logs : %s",
        fichier_log,
    )

    try:
        executer_pipeline(
            logger
        )

        return 0

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning(
            "Pipeline annulé par l'utilisateur."
        )

        return 130

    except Exception:
        logger.exception("")
        logger.error("#" * 72)
        logger.error(
            "ÉCHEC DU PIPELINE"
        )
        logger.error(
            "Run ID : %s",
            RUN_ID,
        )
        logger.error(
            "Les étapes suivantes "
            "n'ont pas été exécutées."
        )
        logger.error("#" * 72)

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )