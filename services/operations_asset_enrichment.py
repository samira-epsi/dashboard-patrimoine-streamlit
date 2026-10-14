import csv
import os
import time
import threading

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from datetime import datetime

import pandas as pd
import requests

from sqlalchemy import (
    bindparam,
    create_engine,
    text,
)

from api.client import get
from config import DB_URL
from services.asset_path import get_asset_path
from services.asset_nodes import fetch_node


# ============================================================
# CONFIGURATION
# ============================================================

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
)

OWNER_ID = "5a2942cfd207720cf70b6796"

OPERATION_TABLES = (
    "operations_active_current",
    "operations_closed_current",
    "operations_denied_current",
)

ASSET_PATH_TABLE = "asset_path_current"
ASSET_NODES_TABLE = "asset_nodes_current"

# ------------------------------------------------------------
# Asset non identifiable
# ------------------------------------------------------------

UNIDENTIFIED_PATH_REFERENCE = "ASSET_NON_IDENTIFIE"
UNIDENTIFIED_ASSET_TYPE = "ASSET_NON_IDENTIFIE"


# ============================================================
# API / PERFORMANCE
# ============================================================

# Limite Intent connue :
# 600 requêtes/minute.
#
# On reste volontairement à 500 pour garder
# une marge pour les retries éventuels.
REQUESTS_PER_MINUTE = int(
    os.getenv(
        "INTENT_ASSETS_REQUESTS_PER_MINUTE",
        "500",
    )
)

# Nombre de requêtes simultanées maximum.
MAX_WORKERS = int(
    os.getenv(
        "INTENT_ASSETS_MAX_WORKERS",
        "6",
    )
)

API_RETRIES = 3

BATCH_SIZE = int(
    os.getenv(
        "OPERATIONS_ASSET_BATCH_SIZE",
        "200",
    )
)


# ============================================================
# LOGS
# ============================================================

LOG_DIR = "logs"

os.makedirs(
    LOG_DIR,
    exist_ok=True,
)

RUN_STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

ISSUES_FILE = os.path.join(
    LOG_DIR,
    f"operations_asset_enrichment_issues_{RUN_STAMP}.csv",
)

ISSUE_COLUMNS = [
    "detected_at",
    "issue_type",
    "asset_reference",
    "error",
    "action",
]


# ============================================================
# RATE LIMITER GLOBAL THREAD-SAFE
# ============================================================

class RateLimiter:
    """
    Rate limiter partagé entre TOUS les workers.

    Exemple :
        MAX_WORKERS = 6
        REQUESTS_PER_MINUTE = 500

    Les 6 workers ensemble ne dépasseront pas
    environ 500 départs de requêtes/minute.

    Ce n'est PAS 500 requêtes/minute par worker.
    """

    def __init__(
        self,
        requests_per_minute,
    ):

        if requests_per_minute <= 0:
            raise ValueError(
                "REQUESTS_PER_MINUTE doit être supérieur à 0."
            )

        self.interval = (
            60.0
            / requests_per_minute
        )

        self.next_slot = time.monotonic()

        self.lock = threading.Lock()

    def wait(self):
        """
        Réserve un créneau de départ de requête.

        Le calcul du créneau est protégé par un Lock,
        mais le sleep se fait en dehors du Lock.
        """

        with self.lock:

            now = time.monotonic()

            scheduled_time = max(
                now,
                self.next_slot,
            )

            self.next_slot = (
                scheduled_time
                + self.interval
            )

        delay = (
            scheduled_time
            - now
        )

        if delay > 0:
            time.sleep(delay)


rate_limiter = RateLimiter(
    REQUESTS_PER_MINUTE
)


# ============================================================
# OUTILS
# ============================================================

def log(message=""):

    stamp = datetime.now().strftime(
        "%H:%M:%S"
    )

    print(
        f"[{stamp}] {message}",
        flush=True,
    )


def normalize_reference(value):

    if value is None:
        return None

    value = str(value).strip()

    value = (
        value
        .strip("\"'")
        .strip()
    )

    if (
        not value
        or value.lower()
        in {
            "nan",
            "none",
            "null",
        }
    ):
        return None

    return value


def is_plausible_asset_reference(
    reference,
):
    """
    Écarte uniquement les références
    manifestement invalides.

    Une référence syntaxiquement plausible mais inconnue
    sera quand même interrogée dans Intent.
    """

    reference = normalize_reference(
        reference
    )

    if reference is None:
        return False

    if len(reference) > 120:
        return False

    if any(
        char.isspace()
        for char in reference
    ):
        return False

    if reference in {
        "-",
        ".",
        "*",
        "/",
        "\\",
        "µ",
    }:
        return False

    if any(
        char in reference
        for char in {
            "<",
            ">",
            '"',
            "*",
        }
    ):
        return False

    # Exemples :
    # 0
    # 00
    # 0000
    # 000000
    #
    # Pas d'appel API.
    if set(reference) == {"0"}:
        return False

    return True


def operation_assets_sql():

    parts = []

    for table in OPERATION_TABLES:

        parts.append(
            f"""
            SELECT asset_reference
            FROM {table}

            WHERE asset_reference IS NOT NULL
              AND BTRIM(asset_reference) <> ''
            """
        )

    return "\nUNION\n".join(
        parts
    )


def write_issues(issues):

    if not issues:
        return

    file_exists = os.path.exists(
        ISSUES_FILE
    )

    with open(
        ISSUES_FILE,
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=ISSUE_COLUMNS,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(
            issues
        )


# ============================================================
# 1. ASSETS OPERATIONS ABSENTS DE ASSET_PATH_CURRENT
# ============================================================

def get_missing_operation_assets(
    limit=None,
):
    """
    On récupère uniquement les asset_reference
    réellement utilisées dans les interventions
    et absentes de asset_path_current.

    Un asset déjà :
        - rattaché
        - ou ASSET_NON_IDENTIFIE

    n'est donc plus rappelé.
    """

    operation_assets = (
        operation_assets_sql()
    )

    limit_sql = ""
    params = {}

    if limit is not None:

        limit = int(limit)

        if limit <= 0:
            raise ValueError(
                "limit doit être supérieur à 0."
            )

        limit_sql = "LIMIT :limit"

        params["limit"] = limit

    query = f"""
        WITH operation_assets AS (
            {operation_assets}
        ),

        known_assets AS (

            SELECT DISTINCT
                asset_reference

            FROM {ASSET_PATH_TABLE}

            WHERE asset_reference IS NOT NULL
              AND BTRIM(asset_reference) <> ''
        )

        SELECT
            oa.asset_reference

        FROM operation_assets oa

        LEFT JOIN known_assets ka
            ON ka.asset_reference
             = oa.asset_reference

        WHERE ka.asset_reference IS NULL

        ORDER BY
            oa.asset_reference

        {limit_sql}
    """

    with engine.connect() as conn:

        rows = conn.execute(
            text(query),
            params,
        ).scalars().all()

    return [
        ref
        for ref in (
            normalize_reference(value)
            for value in rows
        )
        if ref is not None
    ]


# ============================================================
# 2. RECUPERATION ASSET DIRECT DANS INTENT
# ============================================================

def fetch_operation_asset(
    asset_reference,
):
    """
    Worker élémentaire pour un asset.

    Cette fonction :
        - valide la référence
        - attend son créneau global
        - appelle Assets V1
        - distingue :
            * FOUND
            * 404
            * donnée incomplète
            * vraie erreur technique
    """

    asset_reference = normalize_reference(
        asset_reference
    )

    # --------------------------------------------------------
    # Référence manifestement invalide
    # --------------------------------------------------------

    if not is_plausible_asset_reference(
        asset_reference
    ):

        return None, {
            "detected_at":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "issue_type":
                "INVALID_ASSET_REFERENCE",

            "asset_reference":
                asset_reference,

            "error":
                "Référence manifestement invalide. "
                "Aucun appel API effectué.",

            "action":
                "Classé ASSET_NON_IDENTIFIE.",
        }

    try:

        # ----------------------------------------------------
        # RATE LIMIT GLOBAL
        # ----------------------------------------------------

        rate_limiter.wait()

        # ----------------------------------------------------
        # API INTENT
        # ----------------------------------------------------

        data = get(
            f"/assets/v1/assets/{asset_reference}",
            params={
                "ownerId": OWNER_ID,
            },
            retries=API_RETRIES,
        )

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "La réponse Assets V1 "
                "n'est pas un dictionnaire JSON."
            )

        # On conserve la référence exacte
        # portée par l'intervention.
        data["reference"] = (
            asset_reference
        )

        full_path = data.get(
            "fullPath"
        )

        asset_type = data.get(
            "type"
        )

        # ----------------------------------------------------
        # Asset trouvé mais pas de rattachement
        # ----------------------------------------------------

        if (
            full_path is None
            or not str(full_path).strip()
        ):

            return None, {
                "detected_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "issue_type":
                    "MISSING_FULL_PATH",

                "asset_reference":
                    asset_reference,

                "error":
                    "Assets V1 a trouvé l'asset "
                    "mais n'a pas renvoyé de fullPath.",

                "action":
                    "Classé ASSET_NON_IDENTIFIE.",
            }

        # ----------------------------------------------------
        # Asset trouvé mais type absent
        # ----------------------------------------------------

        if (
            asset_type is None
            or not str(asset_type).strip()
        ):

            return None, {
                "detected_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "issue_type":
                    "MISSING_ASSET_TYPE",

                "asset_reference":
                    asset_reference,

                "error":
                    "Assets V1 a trouvé l'asset "
                    "mais n'a pas renvoyé de type.",

                "action":
                    "Classé ASSET_NON_IDENTIFIE.",
            }

        return data, None

    # --------------------------------------------------------
    # ERREUR HTTP
    # --------------------------------------------------------

    except requests.exceptions.HTTPError as error:

        status_code = None

        if error.response is not None:
            status_code = (
                error.response.status_code
            )

        # ----------------------------------------------------
        # 404 = référence présente dans l'intervention
        # mais absente du référentiel Assets courant.
        # ----------------------------------------------------

        if status_code == 404:

            return None, {
                "detected_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "issue_type":
                    "ASSET_NOT_FOUND",

                "asset_reference":
                    asset_reference,

                "error":
                    "Asset référencé dans l'intervention "
                    "mais introuvable dans Assets V1 "
                    "(HTTP 404).",

                "action":
                    "Classé ASSET_NON_IDENTIFIE.",
            }

        # ----------------------------------------------------
        # Autres HTTP errors
        # ----------------------------------------------------

        return None, {
            "detected_at":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "issue_type":
                "API_ERROR",

            "asset_reference":
                asset_reference,

            "error":
                (
                    f"HTTP {status_code}: "
                    f"{error}"
                ),

            "action":
                "Non classé. "
                "Relancer ultérieurement.",
        }

    # --------------------------------------------------------
    # AUTRES ERREURS
    # --------------------------------------------------------

    except Exception as error:

        return None, {
            "detected_at":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "issue_type":
                "API_ERROR",

            "asset_reference":
                asset_reference,

            "error":
                (
                    f"{error.__class__.__name__}: "
                    f"{error}"
                ),

            "action":
                "Non classé. "
                "Relancer ultérieurement.",
        }


# ============================================================
# 3. RECUPERATION PARALLELE DES ASSETS
# ============================================================

def fetch_assets_parallel(
    references,
):
    """
    Récupère un batch d'assets avec plusieurs workers.

    Important :
    le rate limiter est GLOBAL.

    Donc :
        6 workers
        != 6 x 500 req/min

    Les 6 workers partagent le plafond de 500/min.
    """

    payloads = []
    unidentified_paths = []
    issues = []

    total = len(
        references
    )

    if total == 0:
        return (
            payloads,
            unidentified_paths,
            issues,
        )

    completed = 0

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_to_reference = {
            executor.submit(
                fetch_operation_asset,
                reference,
            ): reference

            for reference
            in references
        }

        for future in as_completed(
            future_to_reference
        ):

            reference = (
                future_to_reference[
                    future
                ]
            )

            completed += 1

            try:

                data, issue = (
                    future.result()
                )

            except Exception as error:

                data = None

                issue = {
                    "detected_at":
                        datetime.now()
                        .isoformat(
                            timespec="seconds"
                        ),

                    "issue_type":
                        "WORKER_ERROR",

                    "asset_reference":
                        reference,

                    "error":
                        (
                            f"{error.__class__.__name__}: "
                            f"{error}"
                        ),

                    "action":
                        "Non classé. "
                        "Relancer ultérieurement.",
                }

            # ------------------------------------------------
            # Asset valide
            # ------------------------------------------------

            if data is not None:

                payloads.append(
                    data
                )

            # ------------------------------------------------
            # Asset réellement non identifiable
            # ------------------------------------------------

            elif should_mark_as_unidentified(
                issue
            ):

                unidentified = (
                    build_unidentified_asset_path(
                        reference
                    )
                )

                if unidentified is not None:

                    unidentified_paths.append(
                        unidentified
                    )

            # ------------------------------------------------
            # Issue
            # ------------------------------------------------

            if issue is not None:

                issues.append(
                    issue
                )

            # ------------------------------------------------
            # Progression
            # ------------------------------------------------

            if (
                completed % 50 == 0
                or completed == total
            ):

                log(
                    f"  Assets API : "
                    f"{completed}/{total}"
                )

    return (
        payloads,
        unidentified_paths,
        issues,
    )


# ============================================================
# 4. ASSET NON IDENTIFIE
# ============================================================

def build_unidentified_asset_path(
    asset_reference,
):
    """
    Conserve toujours la vraie asset_reference.

    Exemple :

        asset_reference =
            000000000027100

        path_reference =
            ASSET_NON_IDENTIFIE
    """

    asset_reference = normalize_reference(
        asset_reference
    )

    if asset_reference is None:
        return None

    return {
        "asset_reference":
            asset_reference,

        "asset_type":
            UNIDENTIFIED_ASSET_TYPE,

        "path_reference":
            UNIDENTIFIED_PATH_REFERENCE,

        "path_order":
            1,
    }


def should_mark_as_unidentified(
    issue,
):
    """
    Seuls les cas confirmés deviennent
    ASSET_NON_IDENTIFIE.

    Une panne API / réseau ne doit jamais
    transformer une donnée en "non identifiée".
    """

    if not issue:
        return False

    return (
        issue.get(
            "issue_type"
        )
        in {
            "INVALID_ASSET_REFERENCE",
            "ASSET_NOT_FOUND",
            "MISSING_FULL_PATH",
            "MISSING_ASSET_TYPE",
        }
    )


def insert_unidentified_asset_paths(
    rows,
):

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        rows
    )

    df = (
        df
        .drop_duplicates(
            subset=[
                "asset_reference",
            ],
            keep="last",
        )
        .reset_index(
            drop=True
        )
    )

    if df.empty:
        return df

    asset_references = (
        df[
            "asset_reference"
        ]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    if not asset_references:
        return pd.DataFrame()

    statement = text(
        f"""
        SELECT DISTINCT
            asset_reference

        FROM {ASSET_PATH_TABLE}

        WHERE asset_reference
              IN :asset_references
        """
    ).bindparams(
        bindparam(
            "asset_references",
            expanding=True,
        )
    )

    with engine.connect() as conn:

        existing = set(
            conn.execute(
                statement,
                {
                    "asset_references":
                        asset_references
                },
            ).scalars().all()
        )

    if existing:

        existing = {
            str(value)
            for value in existing
        }

        df = df[
            ~df[
                "asset_reference"
            ]
            .astype(str)
            .isin(existing)
        ].copy()

    if df.empty:
        return df

    df.to_sql(
        ASSET_PATH_TABLE,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    return df


# ============================================================
# 5. GET_ASSET_PATH + INSERTION
# ============================================================

def build_and_insert_asset_paths(
    asset_payloads,
):
    """
    Transforme les assets trouvés en chemins patrimoine.

    Exemple :

    asset_reference
        ↓
    fullPath
        ↓
    société
    agence
    groupe
    secteur
    programme
    bâtiment
    logement
    """

    if not asset_payloads:
        return pd.DataFrame()

    df_assets = pd.json_normalize(
        asset_payloads
    )

    for column in [
        "reference",
        "fullPath",
        "type",
    ]:

        if column not in df_assets.columns:
            df_assets[column] = None

    df_path = get_asset_path(
        df_assets[
            [
                "reference",
                "fullPath",
                "type",
            ]
        ].copy()
    )

    if df_path.empty:
        return df_path

    df_path = (
        df_path
        .drop_duplicates(
            subset=[
                "asset_reference",
                "path_reference",
                "path_order",
            ],
            keep="last",
        )
        .reset_index(
            drop=True
        )
    )

    asset_references = (
        df_path[
            "asset_reference"
        ]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    if not asset_references:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Recontrôle avant insertion
    # --------------------------------------------------------

    statement = text(
        f"""
        SELECT DISTINCT
            asset_reference

        FROM {ASSET_PATH_TABLE}

        WHERE asset_reference
              IN :asset_references
        """
    ).bindparams(
        bindparam(
            "asset_references",
            expanding=True,
        )
    )

    with engine.connect() as conn:

        existing = set(
            conn.execute(
                statement,
                {
                    "asset_references":
                        asset_references
                },
            ).scalars().all()
        )

    if existing:

        existing = {
            str(value)
            for value in existing
        }

        df_path = df_path[
            ~df_path[
                "asset_reference"
            ]
            .astype(str)
            .isin(existing)
        ].copy()

    if df_path.empty:
        return df_path

    # --------------------------------------------------------
    # Ecriture BDD
    #
    # Toujours dans le thread principal.
    # --------------------------------------------------------

    df_path.to_sql(
        ASSET_PATH_TABLE,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    return df_path


# ============================================================
# 6. NODES DU PATH ABSENTS DE ASSET_NODES_CURRENT
# ============================================================

def get_missing_nodes_from_path(
    df_path,
):
    """
    Ne contrôle que les nodes présents
    dans les paths du batch courant.
    """

    if (
        df_path is None
        or df_path.empty
    ):
        return []

    path_references = (
        df_path[
            "path_reference"
        ]
        .dropna()
        .astype(str)
        .str.strip()
    )

    path_references = (
        path_references[
            (
                path_references != ""
            )
            & (
                path_references
                != UNIDENTIFIED_PATH_REFERENCE
            )
        ]
        .drop_duplicates()
        .tolist()
    )

    if not path_references:
        return []

    statement = text(
        f"""
        SELECT DISTINCT
            path_reference

        FROM {ASSET_NODES_TABLE}

        WHERE path_reference
              IN :path_references
        """
    ).bindparams(
        bindparam(
            "path_references",
            expanding=True,
        )
    )

    with engine.connect() as conn:

        existing = set(
            conn.execute(
                statement,
                {
                    "path_references":
                        path_references
                },
            ).scalars().all()
        )

    return [
        reference

        for reference
        in path_references

        if reference
        not in existing
    ]


# ============================================================
# 7. WORKER NODE
# ============================================================

def fetch_node_worker(
    node_reference,
):
    """
    Wrapper thread-safe autour de fetch_node().

    Même rate limiter GLOBAL que les assets.
    """

    try:

        rate_limiter.wait()

        data, error = fetch_node(
            node_reference
        )

        return (
            node_reference,
            data,
            error,
        )

    except Exception as error:

        return (
            node_reference,
            None,
            (
                f"{error.__class__.__name__}: "
                f"{error}"
            ),
        )


# ============================================================
# 8. NETTOYAGE NODES
# ============================================================

def clean_node_dataframe(
    rows,
):
    """
    Même structure finale que asset_nodes.py.
    """

    if not rows:
        return pd.DataFrame()

    df_nodes = pd.json_normalize(
        rows
    )

    columns_to_keep = [
        "path_reference",
        "reference",
        "code",
        "label",
        "category",
        "type",
        "fullPath",
        "parentPath",
        "contracts",
        "tags.3f_reference",
        "owner.id",
        "owner.label",
        "creationDate",
        "lastUpdateDate",
    ]

    for column in columns_to_keep:

        if column not in df_nodes.columns:
            df_nodes[column] = None

    df_nodes = df_nodes[
        columns_to_keep
    ]

    import json

    df_nodes["contracts"] = (
        df_nodes[
            "contracts"
        ]
        .apply(
            lambda value:
                json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                )
                if isinstance(
                    value,
                    list,
                )
                else None
        )
    )

    for column in [
        "creationDate",
        "lastUpdateDate",
    ]:

        df_nodes[column] = (
            pd.to_datetime(
                df_nodes[column],
                errors="coerce",
                utc=True,
            )
        )

    return df_nodes


# ============================================================
# 9. RECUPERATION PARALLELE DES NODES
# ============================================================

def insert_missing_nodes(
    df_path,
):
    """
    Récupère les nodes manquants avec plusieurs workers.

    Les écritures PostgreSQL restent séquentielles.
    """

    missing_nodes = (
        get_missing_nodes_from_path(
            df_path
        )
    )

    if not missing_nodes:
        return 0

    log(
        f"Nodes parents à récupérer : "
        f"{len(missing_nodes):,}"
    )

    rows = []
    failed = []

    total = len(
        missing_nodes
    )

    completed = 0

    # --------------------------------------------------------
    # API EN PARALLELE
    # --------------------------------------------------------

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_to_reference = {
            executor.submit(
                fetch_node_worker,
                node_reference,
            ): node_reference

            for node_reference
            in missing_nodes
        }

        for future in as_completed(
            future_to_reference
        ):

            completed += 1

            node_reference = (
                future_to_reference[
                    future
                ]
            )

            try:

                (
                    returned_reference,
                    data,
                    error,
                ) = future.result()

                node_reference = (
                    returned_reference
                )

            except Exception as exc:

                data = None

                error = (
                    f"{exc.__class__.__name__}: "
                    f"{exc}"
                )

            if data is not None:
                rows.append(
                    data
                )

            if error is not None:
                failed.append(
                    (
                        node_reference,
                        error,
                    )
                )

            if (
                completed % 50 == 0
                or completed == total
            ):

                log(
                    f"  Nodes API : "
                    f"{completed}/{total}"
                )

    # --------------------------------------------------------
    # LOG ERREURS NODES
    # --------------------------------------------------------

    if failed:

        node_issues = [
            {
                "detected_at":
                    datetime.now()
                    .isoformat(
                        timespec="seconds"
                    ),

                "issue_type":
                    "NODE_API_ERROR",

                "asset_reference":
                    node_reference,

                "error":
                    str(error),

                "action":
                    "Contrôler ce node dans Intent "
                    "puis relancer.",
            }

            for (
                node_reference,
                error,
            )
            in failed
        ]

        write_issues(
            node_issues
        )

    # --------------------------------------------------------
    # DATAFRAME
    # --------------------------------------------------------

    df_nodes = clean_node_dataframe(
        rows
    )

    if df_nodes.empty:
        return 0

    df_nodes = (
        df_nodes
        .dropna(
            subset=[
                "path_reference",
            ]
        )
        .drop_duplicates(
            subset=[
                "path_reference",
            ],
            keep="last",
        )
        .reset_index(
            drop=True
        )
    )

    if df_nodes.empty:
        return 0

    refs = (
        df_nodes[
            "path_reference"
        ]
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    # --------------------------------------------------------
    # Anti-doublon avant écriture
    # --------------------------------------------------------

    statement = text(
        f"""
        SELECT DISTINCT
            path_reference

        FROM {ASSET_NODES_TABLE}

        WHERE path_reference
              IN :path_references
        """
    ).bindparams(
        bindparam(
            "path_references",
            expanding=True,
        )
    )

    with engine.connect() as conn:

        existing = set(
            conn.execute(
                statement,
                {
                    "path_references":
                        refs
                },
            ).scalars().all()
        )

    if existing:

        existing = {
            str(value)
            for value in existing
        }

        df_nodes = df_nodes[
            ~df_nodes[
                "path_reference"
            ]
            .astype(str)
            .isin(existing)
        ].copy()

    if df_nodes.empty:
        return 0

    # --------------------------------------------------------
    # PostgreSQL
    #
    # Toujours hors workers.
    # --------------------------------------------------------

    df_nodes.to_sql(
        ASSET_NODES_TABLE,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )

    return len(
        df_nodes
    )


# ============================================================
# CONTROLE FINAL
# ============================================================

def print_final_control():

    operation_assets = (
        operation_assets_sql()
    )

    query = f"""
        WITH operation_assets AS (

            {operation_assets}
        ),

        known_assets AS (

            SELECT DISTINCT
                asset_reference,
                path_reference

            FROM {ASSET_PATH_TABLE}

            WHERE asset_reference IS NOT NULL
              AND BTRIM(asset_reference) <> ''
        )

        SELECT

            COUNT(
                DISTINCT oa.asset_reference
            ) AS total_assets,

            COUNT(
                DISTINCT oa.asset_reference
            ) FILTER (
                WHERE ka.asset_reference
                      IS NOT NULL
            ) AS assets_avec_path,

            COUNT(
                DISTINCT oa.asset_reference
            ) FILTER (
                WHERE ka.asset_reference
                      IS NULL
            ) AS assets_sans_path,

            COUNT(
                DISTINCT oa.asset_reference
            ) FILTER (
                WHERE ka.path_reference
                      = :unidentified
            ) AS assets_non_identifies

        FROM operation_assets oa

        LEFT JOIN known_assets ka
            ON ka.asset_reference
             = oa.asset_reference
    """

    with engine.connect() as conn:

        result = conn.execute(
            text(query),
            {
                "unidentified":
                    UNIDENTIFIED_PATH_REFERENCE
            },
        ).mappings().one()

    log(
        "============================================================"
    )

    log(
        "CONTROLE FINAL"
    )

    log(
        "============================================================"
    )

    log(
        f"Assets uniques opérations : "
        f"{result['total_assets']:,}"
    )

    log(
        f"Assets présents dans "
        f"{ASSET_PATH_TABLE} : "
        f"{result['assets_avec_path']:,}"
    )

    log(
        f"Assets non identifiés : "
        f"{result['assets_non_identifies']:,}"
    )

    log(
        f"Assets encore absents : "
        f"{result['assets_sans_path']:,}"
    )


# ============================================================
# PIPELINE
# ============================================================

def run_operations_asset_enrichment(
    limit=None,
):

    log(
        "============================================================"
    )

    log(
        "ENRICHISSEMENT PATRIMOINE DES OPERATIONS"
    )

    log(
        "============================================================"
    )

    log(
        f"Mode PARALLELE | "
        f"{MAX_WORKERS} workers | "
        f"{REQUESTS_PER_MINUTE} req/min max GLOBAL"
    )

    log(
        "Limite Intent : 600 req/min. "
        "Marge conservée."
    )

    log(
        "Ne pas lancer en parallèle "
        "avec un autre pipeline Intent."
    )

    # ========================================================
    # REFERENCES A TRAITER
    # ========================================================

    missing_assets = (
        get_missing_operation_assets(
            limit=limit
        )
    )

    log(
        f"Asset_reference absents de "
        f"{ASSET_PATH_TABLE} : "
        f"{len(missing_assets):,}"
    )

    if not missing_assets:

        log(
            "Aucun nouvel asset à enrichir."
        )

        print_final_control()

        return

    # ========================================================
    # COMPTEURS
    # ========================================================

    total_assets_inserted = 0
    total_unidentified_inserted = 0
    total_nodes_inserted = 0
    total_issues = 0

    total_batches = (
        len(missing_assets)
        + BATCH_SIZE
        - 1
    ) // BATCH_SIZE

    # ========================================================
    # BATCHES
    # ========================================================

    for (
        batch_no,
        start,
    ) in enumerate(
        range(
            0,
            len(missing_assets),
            BATCH_SIZE,
        ),
        start=1,
    ):

        batch_refs = (
            missing_assets[
                start:
                start + BATCH_SIZE
            ]
        )

        log(
            f"Batch "
            f"{batch_no}/{total_batches} "
            f"| {len(batch_refs):,} asset(s)"
        )

        # ====================================================
        # ASSETS API PARALLELE
        # ====================================================

        (
            payloads,
            unidentified_paths,
            issues,
        ) = fetch_assets_parallel(
            batch_refs
        )

        # ====================================================
        # LOG ANOMALIES
        # ====================================================

        if issues:

            write_issues(
                issues
            )

            total_issues += (
                len(issues)
            )

        # ====================================================
        # ASSETS VALIDES
        # ====================================================

        df_path = (
            build_and_insert_asset_paths(
                payloads
            )
        )

        if not df_path.empty:

            inserted_assets = (
                df_path[
                    "asset_reference"
                ]
                .nunique()
            )

            total_assets_inserted += (
                inserted_assets
            )

            log(
                f"  Assets ajoutés dans "
                f"{ASSET_PATH_TABLE} : "
                f"{inserted_assets:,}"
            )

            # ================================================
            # NODES PARALLELES
            # ================================================

            nodes_inserted = (
                insert_missing_nodes(
                    df_path
                )
            )

            total_nodes_inserted += (
                nodes_inserted
            )

            log(
                f"  Nodes ajoutés dans "
                f"{ASSET_NODES_TABLE} : "
                f"{nodes_inserted:,}"
            )

        else:

            log(
                "  Aucun asset path valide "
                "dans ce batch."
            )

        # ====================================================
        # ASSETS NON IDENTIFIES
        # ====================================================

        df_unidentified = (
            insert_unidentified_asset_paths(
                unidentified_paths
            )
        )

        if not df_unidentified.empty:

            unidentified_inserted = (
                df_unidentified[
                    "asset_reference"
                ]
                .nunique()
            )

            total_unidentified_inserted += (
                unidentified_inserted
            )

            log(
                f"  Assets classés "
                f"ASSET_NON_IDENTIFIE : "
                f"{unidentified_inserted:,}"
            )

    # ========================================================
    # CONTROLE FINAL
    # ========================================================

    print_final_control()

    log(
        "============================================================"
    )

    log(
        "ENRICHISSEMENT TERMINE"
    )

    log(
        "============================================================"
    )

    log(
        f"Assets avec rattachement ajoutés : "
        f"{total_assets_inserted:,}"
    )

    log(
        f"Assets non identifiés ajoutés : "
        f"{total_unidentified_inserted:,}"
    )

    log(
        f"Nodes ajoutés : "
        f"{total_nodes_inserted:,}"
    )

    log(
        f"Anomalies détectées : "
        f"{total_issues:,}"
    )

    if total_issues:

        log(
            f"Voir : "
            f"{ISSUES_FILE}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        run_operations_asset_enrichment()

    except KeyboardInterrupt:

        log(
            "Programme arrêté par Ctrl+C."
        )

        raise SystemExit(
            130
        )