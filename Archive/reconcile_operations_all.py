import csv
import json
import math
import os
import time
import uuid

from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import (
    bindparam,
    create_engine,
    text,
)

from api.client import get
from config import DB_URL

from services.operations_active import (
    ALL_TARGET_COLUMNS,
    API_ROOT_FIELDS,
    OPERATION_KEY_COLUMN,
    api_datetime,
    build_operation_key,
    clean_operations,
    get_error_details,
    get_operations_from_response,
    get_retry_delay,
    quote,
    utc_now,
)


# ============================================================
# CONFIGURATION
# ============================================================

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
)

ACTIVE_TABLE = "operations_active_current"
CLOSED_TABLE = "operations_closed_current"
DENIED_TABLE = "operations_denied_current"

START_DATE = date(2010, 1, 1)

PER_PAGE = 100

# ------------------------------------------------------------
# API
# ------------------------------------------------------------

# Intent :
# 600 requêtes/minute par clientId
# 1 requête = 10 points
# plafond = 6000 points/minute
#
# Nous restons volontairement très en dessous.
REQUESTS_PER_MINUTE = 60

MAX_RETRIES = 10

# On ne refait PAS 4 fois un mois avec doublons.
# Une réponse complète en nombre de lignes est acceptée,
# et les doublons sont tracés dans le CSV.
FULL_FETCH_ATTEMPTS = 2

UPSERT_CHUNK_SIZE = 1000

USE_FIELDS_FILTER = True


# ============================================================
# STATUTS
# ============================================================

STATUS_CONFIG = {

    "open": {
        "table": ACTIVE_TABLE,
        "end_date": lambda: date.today() + timedelta(days=730),
    },

    "pending": {
        "table": ACTIVE_TABLE,
        "end_date": lambda: date.today() + timedelta(days=730),
    },

    "hold": {
        "table": ACTIVE_TABLE,
        "end_date": lambda: date.today() + timedelta(days=730),
    },

    "closed": {
        "table": CLOSED_TABLE,
        "end_date": lambda: date.today(),
    },

    "denied": {
        "table": DENIED_TABLE,
        "end_date": lambda: date.today(),
    },
}


# Pour tester seulement certains statuts :
#
# STATUSES_TO_RUN = ["open"]
# STATUSES_TO_RUN = ["closed"]
#
# Pour tout contrôler :
STATUSES_TO_RUN = [
    "open",
    "pending",
    "hold",
    "closed",
    "denied",
]


# ============================================================
# FICHIER DES ANOMALIES
# ============================================================

LOG_DIR = "logs"

os.makedirs(
    LOG_DIR,
    exist_ok=True,
)

RUN_TIMESTAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

PROBLEM_FILE = os.path.join(
    LOG_DIR,
    f"operations_reconciliation_problems_{RUN_TIMESTAMP}.csv",
)

PROBLEM_COLUMNS = [
    "detected_at",
    "status",
    "period_start",
    "period_end",
    "problem_type",
    "operation_key",
    "reference",
    "contract_reference",
    "event_date",
    "occurrences",
    "source",
    "details",
    "payload_json",
]


def init_problem_file():

    with open(
        PROBLEM_FILE,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=PROBLEM_COLUMNS,
        )

        writer.writeheader()


def json_payload(value):

    try:

        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    except Exception:

        return str(value)


def get_contract_reference(operation):

    if not isinstance(operation, dict):
        return None

    contract = operation.get("contract")

    if isinstance(contract, dict):

        return contract.get("reference")

    return (
        operation.get("contractReference")
        or operation.get("contract.reference")
    )


def write_problem(
    status,
    period_start,
    period_end,
    problem_type,
    operation_key=None,
    reference=None,
    contract_reference=None,
    event_date=None,
    occurrences=None,
    source=None,
    details=None,
    payload=None,
):

    with open(
        PROBLEM_FILE,
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=PROBLEM_COLUMNS,
        )

        writer.writerow({

            "detected_at":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "status":
                status,

            "period_start":
                period_start,

            "period_end":
                period_end,

            "problem_type":
                problem_type,

            "operation_key":
                operation_key,

            "reference":
                reference,

            "contract_reference":
                contract_reference,

            "event_date":
                event_date,

            "occurrences":
                occurrences,

            "source":
                source,

            "details":
                details,

            "payload_json":
                json_payload(payload)
                if payload is not None
                else None,
        })


# ============================================================
# RATE LIMITER
# ============================================================

class RateLimiter:

    def __init__(
        self,
        requests_per_minute,
    ):

        self.interval = (
            300 / requests_per_minute
        )

        self.next_slot = (
            time.monotonic()
        )

    def wait(self):

        delay = (
            self.next_slot
            - time.monotonic()
        )

        if delay > 0:

            time.sleep(delay)

        self.next_slot = max(
            time.monotonic(),
            self.next_slot,
        ) + self.interval


rate_limiter = RateLimiter(
    REQUESTS_PER_MINUTE
)


# ============================================================
# API INTENT
# ============================================================

def call_intent_api(params):

    for attempt in range(
        MAX_RETRIES
    ):

        rate_limiter.wait()

        try:

            data = get(
                "/operations/v2/operations",
                params=params,
            )

            if not isinstance(
                data,
                dict,
            ):

                raise TypeError(
                    "La réponse API Intent "
                    "n'est pas un dictionnaire JSON."
                )

            return data

        except Exception as error:

            status_code, headers = (
                get_error_details(
                    error
                )
            )

            network_error = (
                error.__class__.__name__
                in {
                    "ConnectionError",
                    "Timeout",
                    "ReadTimeout",
                    "ConnectTimeout",
                }
            )

            retryable = (
                status_code
                in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }
                or network_error
            )

            if (
                not retryable
                or attempt
                == MAX_RETRIES - 1
            ):

                raise

            delay = get_retry_delay(
                headers,
                attempt,
                status_code,
            )

            print(
                f"\nTentative "
                f"{attempt + 1}/"
                f"{MAX_RETRIES}"
            )

            print(
                f"Erreur : "
                f"{error.__class__.__name__}"
            )

            if status_code:

                print(
                    f"HTTP : "
                    f"{status_code}"
                )

            if status_code == 429:

                print(
                    "⚠️ Limite API Intent atteinte."
                )

            print(
                f"Nouvelle tentative "
                f"dans {delay:.0f}s..."
            )

            time.sleep(delay)

    raise RuntimeError(
        "Impossible de joindre Intent."
    )


def build_operation_params(
    status,
    period_start,
    period_end,
    page=1,
):

    params = {

        "page":
            page,

        "perPage":
            PER_PAGE,

        "status":
            status,

        "from":
            api_datetime(
                period_start
            ),

        "to":
            api_datetime(
                period_end,
                end_of_day=True,
            ),
    }

    if USE_FIELDS_FILTER:

        params["fields"] = ",".join(
            API_ROOT_FIELDS
        )

    return params


# ============================================================
# MOIS
# ============================================================

def iter_months(
    start_date,
    end_date,
):

    current = date(
        start_date.year,
        start_date.month,
        1,
    )

    while current <= end_date:

        if current.month == 12:

            next_month = date(
                current.year + 1,
                1,
                1,
            )

        else:

            next_month = date(
                current.year,
                current.month + 1,
                1,
            )

        month_start = max(
            start_date,
            current,
        )

        month_end = min(
            end_date,
            next_month
            - timedelta(days=1),
        )

        yield (
            month_start,
            month_end,
        )

        current = next_month


# ============================================================
# TOTAL API DU MOIS
# ============================================================

def get_api_month_summary(
    status,
    month_start,
    month_end,
):

    params = build_operation_params(
        status=status,
        period_start=month_start,
        period_end=month_end,
        page=1,
    )

    data = call_intent_api(
        params
    )

    total = data.get(
        "total"
    )

    if total is None:

        raise RuntimeError(
            "Champ total absent "
            "de la réponse API."
        )

    return (
        int(total),
        data,
    )


# ============================================================
# BDD
# ============================================================

def get_db_count(
    table,
    status,
    month_start,
    month_end,
):

    start_value = api_datetime(
        month_start
    )

    end_value = api_datetime(
        month_end,
        end_of_day=True,
    )

    with engine.connect() as conn:

        return conn.execute(
            text(f"""
                SELECT COUNT(*)

                FROM {quote(table)}

                WHERE
                    status = :status

                    AND event_date >=
                        CAST(
                            :start_value
                            AS TIMESTAMPTZ
                        )

                    AND event_date <=
                        CAST(
                            :end_value
                            AS TIMESTAMPTZ
                        )
            """),
            {
                "status":
                    status,

                "start_value":
                    start_value,

                "end_value":
                    end_value,
            },
        ).scalar_one()


def get_db_keys(
    table,
    status,
    month_start,
    month_end,
):

    start_value = api_datetime(
        month_start
    )

    end_value = api_datetime(
        month_end,
        end_of_day=True,
    )

    with engine.connect() as conn:

        rows = conn.execute(
            text(f"""
                SELECT
                    {quote(OPERATION_KEY_COLUMN)}

                FROM {quote(table)}

                WHERE
                    status = :status

                    AND event_date >=
                        CAST(
                            :start_value
                            AS TIMESTAMPTZ
                        )

                    AND event_date <=
                        CAST(
                            :end_value
                            AS TIMESTAMPTZ
                        )

                    AND
                    {quote(OPERATION_KEY_COLUMN)}
                    IS NOT NULL
            """),
            {
                "status":
                    status,

                "start_value":
                    start_value,

                "end_value":
                    end_value,
            },
        )

        return {
            row[0]
            for row in rows
        }


# ============================================================
# RECUPERATION LIGNES BDD
# ============================================================

def get_db_rows_by_keys(
    table,
    operation_keys,
):

    operation_keys = list(
        operation_keys
    )

    if not operation_keys:

        return []

    statement = text(f"""
        SELECT *

        FROM {quote(table)}

        WHERE
            {quote(OPERATION_KEY_COLUMN)}
            IN :operation_keys
    """).bindparams(

        bindparam(
            "operation_keys",
            expanding=True,
        )
    )

    rows = []

    for start in range(
        0,
        len(operation_keys),
        500,
    ):

        chunk = operation_keys[
            start:
            start + 500
        ]

        with engine.connect() as conn:

            result = conn.execute(
                statement,
                {
                    "operation_keys":
                        chunk
                },
            ).mappings().all()

            rows.extend(
                dict(row)
                for row in result
            )

    return rows


# ============================================================
# NETTOYAGE NUL
# ============================================================

def remove_nul_characters(
    value
):

    if isinstance(
        value,
        str,
    ):

        return value.replace(
            "\x00",
            " ",
        )

    if isinstance(
        value,
        list,
    ):

        return [
            remove_nul_characters(
                item
            )
            for item in value
        ]

    if isinstance(
        value,
        dict,
    ):

        return {
            key:
                remove_nul_characters(
                    item
                )

            for key, item
            in value.items()
        }

    return value


# ============================================================
# TELECHARGEMENT COMPLET DU MOIS
# ============================================================

def fetch_complete_month(
    status,
    month_start,
    month_end,
    first_page_data=None,
):

    for attempt in range(
        1,
        FULL_FETCH_ATTEMPTS + 1,
    ):

        print(
            f"\n        Extraction "
            f"{attempt}/"
            f"{FULL_FETCH_ATTEMPTS}"
        )

        # --------------------------------------------
        # PAGE 1
        # --------------------------------------------

        if (
            attempt == 1
            and first_page_data
            is not None
        ):

            data = (
                first_page_data
            )

        else:

            params = (
                build_operation_params(
                    status=status,
                    period_start=month_start,
                    period_end=month_end,
                    page=1,
                )
            )

            data = (
                call_intent_api(
                    params
                )
            )

        api_total = int(
            data.get(
                "total",
                0,
            )
        )

        if api_total == 0:

            return (
                [],
                0,
            )

        expected_pages = (
            math.ceil(
                api_total
                / PER_PAGE
            )
        )

        operations = (
            get_operations_from_response(
                data
            )
        )

        all_operations = list(
            operations
        )

        print(
            f"        page 1/"
            f"{expected_pages} "
            f"→ {len(operations)}"
        )

        population_changed = False

        # --------------------------------------------
        # PAGES 2...
        # --------------------------------------------

        for page in range(
            2,
            expected_pages + 1,
        ):

            params = (
                build_operation_params(
                    status=status,
                    period_start=month_start,
                    period_end=month_end,
                    page=page,
                )
            )

            page_data = (
                call_intent_api(
                    params
                )
            )

            page_total = int(
                page_data.get(
                    "total",
                    api_total,
                )
            )

            if (
                page_total
                != api_total
            ):

                print(
                    "        ⚠️ Le total "
                    "API a changé pendant "
                    "la pagination."
                )

                population_changed = (
                    True
                )

                break

            page_operations = (
                get_operations_from_response(
                    page_data
                )
            )

            all_operations.extend(
                page_operations
            )

            print(
                f"        page "
                f"{page}/"
                f"{expected_pages} "
                f"→ "
                f"{len(page_operations)}"
            )

        if population_changed:

            time.sleep(3)

            continue

        raw_count = len(
            all_operations
        )

        print(
            "\n"
            f"        Total API     : "
            f"{api_total}"
        )

        print(
            f"        Lignes reçues : "
            f"{raw_count}"
        )

        # --------------------------------------------
        # IMPORTANT :
        # on valide le nombre BRUT reçu.
        #
        # 975 lignes API peuvent contenir
        # 973 operation_key uniques.
        # Ce n'est PAS une erreur de pagination
        # à elle seule.
        # --------------------------------------------

        if raw_count == api_total:

            return (
                all_operations,
                api_total,
            )

        print(
            "        ⚠️ Nombre de "
            "lignes reçues différent "
            "du total API."
        )

        time.sleep(3)

    raise RuntimeError(
        f"Pagination incomplète : "
        f"{status} | "
        f"{month_start} → "
        f"{month_end}"
    )


# ============================================================
# UPSERT
# ============================================================

def save_operations(
    table,
    operations,
):

    if not operations:

        return 0

    cleaned = [

        remove_nul_characters(
            operation
        )

        for operation
        in operations
    ]

    df = clean_operations(
        cleaned,
        utc_now(),
    )

    if df.empty:

        return 0

    df = df.drop_duplicates(
        subset=[
            OPERATION_KEY_COLUMN
        ],
        keep="last",
    )

    # Sécurité NUL après transformation
    text_columns = (
        df.select_dtypes(
            include=["object"]
        ).columns
    )

    for column in text_columns:

        df[column] = df[
            column
        ].map(
            lambda value:
                value.replace(
                    "\x00",
                    " ",
                )
                if isinstance(
                    value,
                    str,
                )
                else value
        )

    temp_table = (
        "tmp_reconcile_"
        + uuid.uuid4().hex[:16]
    )

    insert_columns = ", ".join(

        quote(column)

        for column
        in ALL_TARGET_COLUMNS
    )

    update_columns = [

        column

        for column
        in ALL_TARGET_COLUMNS

        if column
        != OPERATION_KEY_COLUMN
    ]

    update_clause = ", ".join(

        f"{quote(column)} = "
        f"EXCLUDED.{quote(column)}"

        for column
        in update_columns
    )

    with engine.begin() as conn:

        conn.execute(
            text(f"""
                CREATE TEMPORARY TABLE
                {quote(temp_table)}
                (
                    LIKE {quote(table)}
                    INCLUDING DEFAULTS
                )
                ON COMMIT DROP
            """)
        )

        df.to_sql(
            temp_table,
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=200,
        )

        conn.execute(
            text(f"""
                INSERT INTO {quote(table)}
                (
                    {insert_columns}
                )

                SELECT
                    {insert_columns}

                FROM {quote(temp_table)}

                ON CONFLICT
                (
                    {quote(OPERATION_KEY_COLUMN)}
                )

                DO UPDATE SET
                    {update_clause}
            """)
        )

    return len(df)


# ============================================================
# AUTRES TABLES
# ============================================================

def other_tables(
    target_table
):

    tables = {
        ACTIVE_TABLE,
        CLOSED_TABLE,
        DENIED_TABLE,
    }

    return (
        tables
        - {target_table}
    )


def delete_keys_from_table(
    table,
    keys,
):

    keys = list(
        set(keys)
    )

    if not keys:

        return 0

    statement = text(f"""
        DELETE FROM {quote(table)}

        WHERE
            {quote(OPERATION_KEY_COLUMN)}
            IN :keys
    """).bindparams(

        bindparam(
            "keys",
            expanding=True,
        )
    )

    deleted = 0

    for start in range(
        0,
        len(keys),
        500,
    ):

        chunk = keys[
            start:
            start + 500
        ]

        with engine.begin() as conn:

            result = conn.execute(
                statement,
                {
                    "keys": chunk
                },
            )

            deleted += (
                result.rowcount
                or 0
            )

    return deleted


def clean_other_tables_for_missing(
    target_table,
    keys,
):

    if not keys:

        return

    for table in other_tables(
        target_table
    ):

        rows = get_db_rows_by_keys(
            table,
            keys,
        )

        if not rows:

            continue

        for row in rows:

            write_problem(
                status=row.get(
                    "status"
                ),
                period_start=None,
                period_end=None,
                problem_type=(
                    "STALE_OTHER_TABLE"
                ),
                operation_key=row.get(
                    OPERATION_KEY_COLUMN
                ),
                reference=row.get(
                    "reference"
                ),
                contract_reference=row.get(
                    "contract_reference"
                ),
                event_date=row.get(
                    "event_date"
                ),
                occurrences=1,
                source=table,
                details=(
                    "Même operation_key trouvée "
                    "dans une autre table current. "
                    "Suppression de la copie obsolète."
                ),
                payload=row,
            )

        deleted = (
            delete_keys_from_table(
                table,
                keys,
            )
        )

        if deleted:

            print(
                f"    🧹 {deleted} "
                f"ancienne(s) copie(s) "
                f"supprimée(s) de "
                f"{table}"
            )


# ============================================================
# TRACE DES DOUBLONS API
# ============================================================

def trace_api_duplicates(
    status,
    month_start,
    month_end,
    operations,
):

    keys = [

        build_operation_key(
            operation
        )

        for operation
        in operations
    ]

    counts = Counter(
        keys
    )

    duplicate_keys = {

        key: count

        for key, count
        in counts.items()

        if count > 1
    }

    if not duplicate_keys:

        return set()

    print(
        f"    ⚠️ "
        f"{len(duplicate_keys)} "
        f"operation_key dupliquée(s) "
        f"dans l'API"
    )

    for key, count in (
        duplicate_keys.items()
    ):

        duplicate_operations = [

            operation

            for operation
            in operations

            if build_operation_key(
                operation
            ) == key
        ]

        first = (
            duplicate_operations[0]
        )

        write_problem(
            status=status,
            period_start=month_start,
            period_end=month_end,
            problem_type="API_DUPLICATE",
            operation_key=key,
            reference=first.get(
                "reference"
            ),
            contract_reference=(
                get_contract_reference(
                    first
                )
            ),
            event_date=first.get(
                "eventDate"
            ),
            occurrences=count,
            source="API",
            details=(
                f"Cette operation_key "
                f"apparaît {count} fois "
                f"parmi les lignes API."
            ),
            payload=duplicate_operations,
        )

    return set(
        duplicate_keys.keys()
    )


# ============================================================
# RECONCILIATION D'UN MOIS
# ============================================================

def reconcile_month(
    status,
    table,
    month_start,
    month_end,
):

    print(
        "\n"
        "===================================================="
    )

    print(
        f"{status.upper()} | "
        f"{month_start:%Y-%m}"
    )

    print(
        "===================================================="
    )

    # --------------------------------------------------------
    # 1. UNE SEULE REQUETE API
    # --------------------------------------------------------

    api_total, first_page = (
        get_api_month_summary(
            status,
            month_start,
            month_end,
        )
    )

    db_count = get_db_count(
        table,
        status,
        month_start,
        month_end,
    )

    print(
        f"API = {api_total} "
        f"| BDD = {db_count}"
    )

    # --------------------------------------------------------
    # 2. VOLUME IDENTIQUE
    # --------------------------------------------------------

    if api_total == db_count:

        print(
            "✅ Mois OK "
            "→ aucun téléchargement"
        )

        return {
            "result":
                "COUNT_OK",

            "api":
                api_total,

            "db":
                db_count,
        }

    # --------------------------------------------------------
    # TRACE DU MOIS
    # --------------------------------------------------------

    write_problem(
        status=status,
        period_start=month_start,
        period_end=month_end,
        problem_type=(
            "MONTH_COUNT_MISMATCH"
        ),
        occurrences=(
            api_total - db_count
        ),
        source="API/BDD",
        details=(
            f"API={api_total} | "
            f"BDD={db_count}"
        ),
    )

    print(
        f"⚠️ Écart de "
        f"{api_total - db_count}"
    )

    print(
        "Téléchargement complet "
        "du mois..."
    )

    # --------------------------------------------------------
    # 3. EXTRACTION DU MOIS
    # --------------------------------------------------------

    operations, api_total = (
        fetch_complete_month(
            status,
            month_start,
            month_end,
            first_page_data=first_page,
        )
    )

    # --------------------------------------------------------
    # 4. DOUBLONS API
    # --------------------------------------------------------

    duplicate_keys = (
        trace_api_duplicates(
            status,
            month_start,
            month_end,
            operations,
        )
    )

    # --------------------------------------------------------
    # 5. DICTIONNAIRE UNIQUE API
    # --------------------------------------------------------

    api_by_key = {}

    for operation in operations:

        key = build_operation_key(
            operation
        )

        # Même comportement que clean_operations :
        # on conserve la dernière occurrence.
        api_by_key[
            key
        ] = operation

    api_keys = set(
        api_by_key.keys()
    )

    db_keys_before = (
        get_db_keys(
            table,
            status,
            month_start,
            month_end,
        )
    )

    missing = (
        api_keys
        - db_keys_before
    )

    extras = (
        db_keys_before
        - api_keys
    )

    print(
        "\n"
        "===== COMPARAISON EXACTE ====="
    )

    print(
        f"API brut      : "
        f"{api_total}"
    )

    print(
        f"API unique    : "
        f"{len(api_keys)}"
    )

    print(
        f"BDD unique    : "
        f"{len(db_keys_before)}"
    )

    print(
        f"Manquantes    : "
        f"{len(missing)}"
    )

    print(
        f"En trop BDD   : "
        f"{len(extras)}"
    )

    # --------------------------------------------------------
    # 6. TRACE DES MANQUANTES
    # --------------------------------------------------------

    for key in sorted(
        missing
    ):

        operation = (
            api_by_key[key]
        )

        write_problem(
            status=status,
            period_start=month_start,
            period_end=month_end,
            problem_type="MISSING_IN_DB",
            operation_key=key,
            reference=operation.get(
                "reference"
            ),
            contract_reference=(
                get_contract_reference(
                    operation
                )
            ),
            event_date=operation.get(
                "eventDate"
            ),
            occurrences=1,
            source="API",
            details=(
                "Présente dans l'API "
                "mais absente de la BDD."
            ),
            payload=operation,
        )

    # --------------------------------------------------------
    # 7. TRACE DES EXTRAS
    # --------------------------------------------------------

    extra_rows = (
        get_db_rows_by_keys(
            table,
            extras,
        )
    )

    for row in extra_rows:

        write_problem(
            status=status,
            period_start=month_start,
            period_end=month_end,
            problem_type="EXTRA_IN_DB",
            operation_key=row.get(
                OPERATION_KEY_COLUMN
            ),
            reference=row.get(
                "reference"
            ),
            contract_reference=row.get(
                "contract_reference"
            ),
            event_date=row.get(
                "event_date"
            ),
            occurrences=1,
            source=table,
            details=(
                "Présente dans PostgreSQL "
                "mais absente des clés "
                "récupérées sur l'API."
            ),
            payload=row,
        )

    # --------------------------------------------------------
    # IMPORTANT :
    #
    # ON NE SUPPRIME PAS AUTOMATIQUEMENT LES EXTRAS.
    #
    # Avec les doublons / pagination Intent,
    # une opération peut paraître absente alors que
    # l'API a simplement renvoyé deux fois une autre ligne.
    #
    # Elles sont donc tracées pour investigation.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # 8. AJOUT DES MANQUANTES
    # --------------------------------------------------------

    inserted = 0

    if missing:

        missing_operations = [

            api_by_key[key]

            for key in missing
        ]

        for start in range(
            0,
            len(missing_operations),
            UPSERT_CHUNK_SIZE,
        ):

            chunk = (
                missing_operations[
                    start:
                    start
                    + UPSERT_CHUNK_SIZE
                ]
            )

            inserted += (
                save_operations(
                    table,
                    chunk,
                )
            )

        # Si une opération était dans closed/denied
        # alors qu'elle est maintenant open/pending/hold
        # (ou inversement), on retire l'ancienne copie.
        clean_other_tables_for_missing(
            target_table=table,
            keys=missing,
        )

    # --------------------------------------------------------
    # 9. CONTROLE APRES REPARATION
    # --------------------------------------------------------

    db_keys_after = (
        get_db_keys(
            table,
            status,
            month_start,
            month_end,
        )
    )

    missing_after = (
        api_keys
        - db_keys_after
    )

    extras_after = (
        db_keys_after
        - api_keys
    )

    print(
        "\n"
        "===== APRES REPARATION ====="
    )

    print(
        f"Ajoutées      : "
        f"{inserted}"
    )

    print(
        f"Manquantes    : "
        f"{len(missing_after)}"
    )

    print(
        f"En trop BDD   : "
        f"{len(extras_after)}"
    )

    # --------------------------------------------------------
    # RESULTAT
    # --------------------------------------------------------

    if missing_after:

        print(
            "❌ Des interventions "
            "API restent absentes."
        )

        result = "FAILED"

    elif (
        duplicate_keys
        or extras_after
    ):

        print(
            "⚠️ Données réparées, "
            "mais anomalies à analyser."
        )

        result = "REVIEW_REQUIRED"

    else:

        print(
            "✅ Mois réconcilié"
        )

        result = "REPAIRED_OK"

    return {

        "result":
            result,

        "api_total":
            api_total,

        "api_unique":
            len(api_keys),

        "db_before":
            db_count,

        "missing":
            len(missing),

        "extras":
            len(extras),

        "duplicates":
            len(duplicate_keys),

        "inserted":
            inserted,
    }


# ============================================================
# RECONCILIATION COMPLETE
# ============================================================

def reconcile_all_operations():

    init_problem_file()

    print(
        "\n"
        "===================================================="
    )

    print(
        "RECONCILIATION OPERATIONS INTENT"
    )

    print(
        "===================================================="
    )

    print(
        f"Cadence API : "
        f"{REQUESTS_PER_MINUTE} "
        f"requêtes/minute"
    )

    print(
        f"Fichier anomalies : "
        f"{PROBLEM_FILE}"
    )

    total_months = 0
    ok_months = 0
    repaired_months = 0
    review_months = 0
    failed_months = 0
    error_months = 0

    for status in (
        STATUSES_TO_RUN
    ):

        config = (
            STATUS_CONFIG[
                status
            ]
        )

        table = (
            config["table"]
        )

        end_date = (
            config["end_date"]()
        )

        print(
            "\n\n"
            "####################################################"
        )

        print(
            f"STATUT : "
            f"{status.upper()}"
        )

        print(
            f"TABLE  : "
            f"{table}"
        )

        print(
            f"PERIODE : "
            f"{START_DATE}"
            f" → "
            f"{end_date}"
        )

        print(
            "####################################################"
        )

        for (
            month_start,
            month_end,
        ) in iter_months(
            START_DATE,
            end_date,
        ):

            total_months += 1

            try:

                result = (
                    reconcile_month(
                        status,
                        table,
                        month_start,
                        month_end,
                    )
                )

                state = result[
                    "result"
                ]

                if state == "COUNT_OK":

                    ok_months += 1

                elif state == "REPAIRED_OK":

                    repaired_months += 1

                elif state == "REVIEW_REQUIRED":

                    review_months += 1

                else:

                    failed_months += 1

            except Exception as error:

                error_months += 1

                print(
                    "\n"
                    f"❌ ERREUR "
                    f"{status} | "
                    f"{month_start:%Y-%m}"
                )

                print(
                    f"{error.__class__.__name__}: "
                    f"{error}"
                )

                write_problem(
                    status=status,
                    period_start=month_start,
                    period_end=month_end,
                    problem_type="ERROR",
                    source="SCRIPT",
                    details=(
                        f"{error.__class__.__name__}: "
                        f"{error}"
                    ),
                )

                # IMPORTANT :
                # on ne bloque pas toute la synchro.
                # On passe au mois suivant.
                continue

    print(
        "\n\n"
        "===================================================="
    )

    print(
        "RECONCILIATION TERMINEE"
    )

    print(
        "===================================================="
    )

    print(
        f"Mois analysés       : "
        f"{total_months}"
    )

    print(
        f"Mois OK             : "
        f"{ok_months}"
    )

    print(
        f"Mois réparés        : "
        f"{repaired_months}"
    )

    print(
        f"A vérifier          : "
        f"{review_months}"
    )

    print(
        f"Echecs              : "
        f"{failed_months}"
    )

    print(
        f"Erreurs API/script  : "
        f"{error_months}"
    )

    print(
        "\nFichier anomalies :"
    )

    print(
        PROBLEM_FILE
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    reconcile_all_operations()