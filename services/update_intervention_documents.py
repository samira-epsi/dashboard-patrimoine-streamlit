from pathlib import Path
import sys
import time
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from sqlalchemy import create_engine, text


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS PROJET
# ============================================================

from config import DB_URL
from api.client import get


# ============================================================
# CONFIGURATION
# ============================================================

# Nombre d'interventions récupérées depuis PostgreSQL à chaque batch
BATCH_SIZE = 5000

# Nombre d'appels exécutés en parallèle
MAX_WORKERS = 10

# Limite volontaire
REQUESTS_PER_MINUTE = 400

# 400 / 60 = 6.6667 requêtes / seconde
REQUESTS_PER_SECOND = REQUESTS_PER_MINUTE / 60

# Intervalle minimum entre deux départs de requêtes
MIN_INTERVAL = 1 / REQUESTS_PER_SECOND


# ============================================================
# RATE LIMITER GLOBAL
# ============================================================

rate_lock = threading.Lock()

last_request_time = 0.0


def wait_for_rate_limit():

    global last_request_time

    with rate_lock:

        now = time.monotonic()

        elapsed = (
            now
            - last_request_time
        )

        if elapsed < MIN_INTERVAL:

            time.sleep(
                MIN_INTERVAL - elapsed
            )

        last_request_time = (
            time.monotonic()
        )


# ============================================================
# DATABASE
# ============================================================

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# ============================================================
# CREATION TABLE
# ============================================================

def create_table():

    print("\n========================================")
    print("VERIFICATION TABLE")
    print("========================================")

    sql = """
    CREATE TABLE IF NOT EXISTS public.intervention_documents_current (

        intervention_reference TEXT PRIMARY KEY,

        document_count INTEGER,

        has_document_api BOOLEAN,

        document_names TEXT,

        checked_at TIMESTAMPTZ,

        api_error TEXT

    );
    """

    with engine.begin() as conn:

        conn.execute(
            text(sql)
        )

    print(
        "Table intervention_documents_current OK"
    )


# ============================================================
# RECUPERATION DU PROCHAIN BATCH
# ============================================================

def get_next_batch():

    sql = f"""
    SELECT DISTINCT
        o.reference AS intervention_reference

    FROM public.operations_closed_current o

    LEFT JOIN public.intervention_documents_current d
        ON o.reference = d.intervention_reference

    WHERE
        o.reference IS NOT NULL
        AND d.intervention_reference IS NULL

    LIMIT {BATCH_SIZE}
    """

    df = pd.read_sql(
        sql,
        engine
    )

    return df


# ============================================================
# EXTRACTION NOM DES DOCUMENTS
# ============================================================

def extract_document_names(
    documents
):

    names = []

    for document in documents:

        if not isinstance(
            document,
            dict
        ):
            continue

        name = (
            document.get("fileName")
            or document.get("filename")
            or document.get("title")
            or document.get("name")
            or document.get("label")
        )

        if name:

            names.append(
                str(name)
            )

    if not names:

        return None

    return " | ".join(
        names
    )


# ============================================================
# APPEL API
# ============================================================

def fetch_documents(
    intervention_reference
):

    intervention_reference = str(
        intervention_reference
    )

    try:

        # --------------------------------------------
        # RATE LIMIT GLOBAL
        # --------------------------------------------

        wait_for_rate_limit()

        # --------------------------------------------
        # API
        # --------------------------------------------

        data = get(
            "/documents/v1/documents",
            params={
                "elementType":
                    "intervention",

                "elementReference":
                    intervention_reference
            }
        )

        # --------------------------------------------
        # DOCUMENTS
        # --------------------------------------------

        documents = []

        if isinstance(
            data,
            dict
        ):

            embedded = data.get(
                "_embedded",
                {}
            )

            if isinstance(
                embedded,
                dict
            ):

                documents = (
                    embedded.get(
                        "documents",
                        []
                    )
                    or []
                )

        # --------------------------------------------
        # RESULTAT
        # --------------------------------------------

        document_count = len(
            documents
        )

        document_names = (
            extract_document_names(
                documents
            )
        )

        return {

            "intervention_reference":
                intervention_reference,

            "document_count":
                document_count,

            "has_document_api":
                document_count > 0,

            "document_names":
                document_names,

            "checked_at":
                datetime.now(
                    timezone.utc
                ),

            "api_error":
                None
        }

    except Exception as e:

        return {

            "intervention_reference":
                intervention_reference,

            "document_count":
                None,

            "has_document_api":
                None,

            "document_names":
                None,

            "checked_at":
                datetime.now(
                    timezone.utc
                ),

            "api_error":
                str(e)
        }


# ============================================================
# SAUVEGARDE POSTGRESQL
# ============================================================

def save_results(
    results
):

    if not results:
        return

    sql = """
    INSERT INTO public.intervention_documents_current (

        intervention_reference,
        document_count,
        has_document_api,
        document_names,
        checked_at,
        api_error

    )

    VALUES (

        :intervention_reference,
        :document_count,
        :has_document_api,
        :document_names,
        :checked_at,
        :api_error

    )

    ON CONFLICT (
        intervention_reference
    )

    DO UPDATE SET

        document_count =
            EXCLUDED.document_count,

        has_document_api =
            EXCLUDED.has_document_api,

        document_names =
            EXCLUDED.document_names,

        checked_at =
            EXCLUDED.checked_at,

        api_error =
            EXCLUDED.api_error
    """

    with engine.begin() as conn:

        conn.execute(
            text(sql),
            results
        )


# ============================================================
# TRAITEMENT D'UN BATCH
# ============================================================

def process_batch(
    df_batch
):

    references = (
        df_batch[
            "intervention_reference"
        ]
        .dropna()
        .astype(str)
        .tolist()
    )

    total = len(
        references
    )

    results = []

    print(
        f"{total:,} interventions "
        f"dans le batch"
    )

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {

            executor.submit(
                fetch_documents,
                reference
            ): reference

            for reference
            in references
        }

        done = 0

        for future in as_completed(
            futures
        ):

            try:

                result = (
                    future.result()
                )

            except Exception as e:

                reference = (
                    futures[future]
                )

                result = {

                    "intervention_reference":
                        str(reference),

                    "document_count":
                        None,

                    "has_document_api":
                        None,

                    "document_names":
                        None,

                    "checked_at":
                        datetime.now(
                            timezone.utc
                        ),

                    "api_error":
                        str(e)
                }

            results.append(
                result
            )

            done += 1

            if done % 500 == 0:

                print(
                    f"{done:,}/{total:,} "
                    f"traitées"
                )

    return results


# ============================================================
# STATISTIQUES BATCH
# ============================================================

def print_batch_stats(
    results
):

    avec = sum(

        1
        for r in results

        if (
            r["has_document_api"]
            is True
        )
    )

    sans = sum(

        1
        for r in results

        if (
            r["has_document_api"]
            is False
        )
    )

    erreurs = sum(

        1
        for r in results

        if (
            r["api_error"]
            is not None
        )
    )

    print(
        f"Avec documents : "
        f"{avec:,}"
    )

    print(
        f"Sans document : "
        f"{sans:,}"
    )

    print(
        f"Erreurs API : "
        f"{erreurs:,}"
    )


# ============================================================
# CONTROLE GLOBAL
# ============================================================

def global_stats():

    df = pd.read_sql(
        """
        SELECT

            COUNT(*) AS total_controles,

            COUNT(*) FILTER (
                WHERE has_document_api = TRUE
            ) AS avec_document,

            COUNT(*) FILTER (
                WHERE has_document_api = FALSE
            ) AS sans_document,

            COUNT(*) FILTER (
                WHERE api_error IS NOT NULL
            ) AS erreurs

        FROM public.intervention_documents_current
        """,
        engine
    )

    print("\n========================================")
    print("ETAT GLOBAL")
    print("========================================")

    print(
        df.to_string(
            index=False
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("############################################")
    print("# DOCUMENTS INTERVENTIONS CLOTUREES        #")
    print("############################################")

    print(
        f"\nLimite configurée : "
        f"{REQUESTS_PER_MINUTE} requêtes/minute"
    )

    print(
        f"Workers : "
        f"{MAX_WORKERS}"
    )

    print(
        f"Batch : "
        f"{BATCH_SIZE:,}"
    )

    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    create_table()

    total_processed = 0

    batch_number = 1

    # --------------------------------------------------------
    # BOUCLE
    # --------------------------------------------------------

    while True:

        print("\n========================================")
        print(
            f"BATCH {batch_number}"
        )
        print("========================================")

        # --------------------------------------------
        # PROCHAIN BATCH
        # --------------------------------------------

        df_batch = (
            get_next_batch()
        )

        # --------------------------------------------
        # PLUS RIEN
        # --------------------------------------------

        if df_batch.empty:

            print(
                "\nPlus aucune nouvelle "
                "intervention à contrôler."
            )

            break

        # --------------------------------------------
        # TRAITEMENT
        # --------------------------------------------

        start_time = (
            time.time()
        )

        results = (
            process_batch(
                df_batch
            )
        )

        # --------------------------------------------
        # SAUVEGARDE
        # --------------------------------------------

        print(
            "\nSauvegarde PostgreSQL..."
        )

        save_results(
            results
        )

        # --------------------------------------------
        # STATS
        # --------------------------------------------

        total_processed += (
            len(results)
        )

        elapsed = (
            time.time()
            - start_time
        )

        print("\nBatch terminé")

        print_batch_stats(
            results
        )

        print(
            f"Durée batch : "
            f"{elapsed / 60:.1f} min"
        )

        print(
            f"Total traité depuis lancement : "
            f"{total_processed:,}"
        )

        # --------------------------------------------
        # ETAT GLOBAL TOUS LES 10 BATCHES
        # --------------------------------------------

        if batch_number % 10 == 0:

            global_stats()

        batch_number += 1

    # --------------------------------------------------------
    # FIN
    # --------------------------------------------------------

    global_stats()

    print("\n")
    print("############################################")
    print("# TRAITEMENT TERMINE                       #")
    print("############################################")


# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":

    main()