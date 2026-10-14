import time
import uuid
from datetime import date, timedelta

from api.client import get
from sqlalchemy import bindparam, create_engine, inspect, text

from config import DB_URL
from services.operations_active import (
    ALL_TARGET_COLUMNS,
    API_ROOT_FIELDS,
    COLUMN_SQL_TYPES,
    NO_CONTRACT_KEY,
    NO_REFERENCE_PREFIX,
    OPERATION_KEY_COLUMN,
    api_datetime,
    api_iso_datetime,
    as_utc,
    build_operation_key,
    clean_operations,
    get_error_details,
    get_operations_from_response,
    get_retry_delay,
    quote,
    should_load_next_page,
    utc_now,
)


# ─── CONFIGURATION ───────────────────────────────────────────

engine = create_engine(DB_URL, pool_pre_ping=True)

TARGET_TABLE = "operations_denied_current"
PROGRESSION_TABLE = "operations_denied_progression"
STATE_TABLE = "operations_denied_sync_state"
PIPELINE_NAME = "operations_denied"

DENIED_STATUS = "denied"

PER_PAGE = 100
BATCH_SIZE = 1_000

# Le volume des opérations refusées est important : on reste volontairement sous la
# cadence du pipeline active. Ne pas lancer les deux pipelines ensemble.
REQUESTS_PER_MINUTE = 180
MAX_RETRIES = 7

WINDOW_DAYS = 7
INITIAL_SYNC_FROM = date(2010, 1, 1)
INITIAL_SYNC_TO = date.today()

DELTA_OVERLAP = timedelta(minutes=10)
DELETE_STALE_AFTER_FULL_BACKFILL = False
USE_FIELDS_FILTER = True


# ─── APPELS API ───────────────────────────────────────────────


class RateLimiter:
    def __init__(self, requests_per_minute):
        self.interval = 60 / requests_per_minute
        self.next_slot = time.monotonic()

    def wait(self):
        delay = self.next_slot - time.monotonic()

        if delay > 0:
            time.sleep(delay)

        self.next_slot = max(
            time.monotonic(),
            self.next_slot,
        ) + self.interval


rate_limiter = RateLimiter(REQUESTS_PER_MINUTE)


def call_intent_api(params):
    for attempt in range(MAX_RETRIES):
        rate_limiter.wait()

        try:
            data = get(
                "/operations/v2/operations",
                params=params,
            )

            if not isinstance(data, dict):
                raise TypeError(
                    "La fonction get() doit renvoyer un dictionnaire JSON."
                )

            return data

        except Exception as error:
            status_code, headers = get_error_details(error)

            network_error = error.__class__.__name__ in {
                "ConnectionError",
                "Timeout",
                "ReadTimeout",
                "ConnectTimeout",
            }

            retryable = (
                status_code in {429, 500, 502, 503, 504}
                or network_error
            )

            if not retryable or attempt == MAX_RETRIES - 1:
                raise

            delay = get_retry_delay(
                headers,
                attempt,
                status_code,
            )

            print(
                f"Erreur API {status_code or 'réseau'} "
                f"— nouvelle tentative dans {delay:.0f} secondes"
            )

            time.sleep(delay)

    raise RuntimeError("Impossible de joindre l'API Intent.")


def build_operation_params(**extra_params):
    params = {
        "page": 1,
        "perPage": PER_PAGE,
    }

    if USE_FIELDS_FILTER:
        params["fields"] = ",".join(API_ROOT_FIELDS)

    params.update(extra_params)

    return params


# ─── INITIALISATION BASE ─────────────────────────────────────


def init_tables():
    target_definition = ", ".join(
        f"{quote(column)} {column_type}"
        for column, column_type in COLUMN_SQL_TYPES.items()
    )

    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {quote(TARGET_TABLE)} (
                {target_definition}
            )
        """))

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {quote(PROGRESSION_TABLE)} (
                window_start DATE NOT NULL,
                window_end   DATE NOT NULL,
                last_page    INTEGER NOT NULL DEFAULT 0,
                done         BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (window_start, window_end)
            )
        """))

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {quote(STATE_TABLE)} (
                pipeline_name    VARCHAR(100) PRIMARY KEY,
                sync_started_at  TIMESTAMPTZ,
                initial_complete BOOLEAN NOT NULL DEFAULT FALSE,
                last_success_at  TIMESTAMPTZ,
                updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

    inspector = inspect(engine)
    existing_columns = {
        column["name"]
        for column in inspector.get_columns(TARGET_TABLE)
    }

    with engine.begin() as conn:
        for column, column_type in COLUMN_SQL_TYPES.items():
            if column not in existing_columns:
                conn.execute(text(f"""
                    ALTER TABLE {quote(TARGET_TABLE)}
                    ADD COLUMN IF NOT EXISTS
                    {quote(column)} {column_type}
                """))

        # Migration si une ancienne version de la table existait déjà.
        conn.execute(text(f"""
            UPDATE {quote(TARGET_TABLE)}
            SET {quote(OPERATION_KEY_COLUMN)} = CASE
                WHEN NULLIF(BTRIM({quote("reference")}), '') IS NULL
                    THEN '{NO_REFERENCE_PREFIX}|legacy:' || ctid::text
                ELSE
                    'ref:' || BTRIM({quote("reference")})
                    || '|contract:'
                    || COALESCE(
                        NULLIF(BTRIM({quote("contract_reference")}), ''),
                        '{NO_CONTRACT_KEY}'
                    )
            END
            WHERE
                {quote(OPERATION_KEY_COLUMN)} IS NULL
                OR BTRIM({quote(OPERATION_KEY_COLUMN)}) = ''
        """))

        conn.execute(text(f"""
            DROP INDEX IF EXISTS
            {quote("idx_operations_denied_reference")}
        """))

        conn.execute(text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS
            {quote("idx_operations_denied_operation_key")}
            ON {quote(TARGET_TABLE)} ({quote(OPERATION_KEY_COLUMN)})
        """))


# ─── ÉTAT ET REPRISE ─────────────────────────────────────────


def get_sync_state():
    with engine.connect() as conn:
        return conn.execute(text(f"""
            SELECT
                sync_started_at,
                initial_complete,
                last_success_at
            FROM {quote(STATE_TABLE)}
            WHERE pipeline_name = :pipeline_name
        """), {
            "pipeline_name": PIPELINE_NAME,
        }).mappings().fetchone()


def begin_or_resume_initial_sync(force_full=False):
    state = get_sync_state()

    if state and not state["initial_complete"] and not force_full:
        return as_utc(state["sync_started_at"])

    sync_started_at = utc_now()

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {quote(STATE_TABLE)} (
                pipeline_name,
                sync_started_at,
                initial_complete,
                last_success_at,
                updated_at
            )
            VALUES (
                :pipeline_name,
                :sync_started_at,
                FALSE,
                NULL,
                NOW()
            )
            ON CONFLICT (pipeline_name)
            DO UPDATE SET
                sync_started_at = EXCLUDED.sync_started_at,
                initial_complete = FALSE,
                last_success_at = NULL,
                updated_at = NOW()
        """), {
            "pipeline_name": PIPELINE_NAME,
            "sync_started_at": sync_started_at,
        })

        conn.execute(text(f"""
            DELETE FROM {quote(PROGRESSION_TABLE)}
        """))

    return sync_started_at


def mark_initial_sync_complete(sync_started_at):
    with engine.begin() as conn:
        conn.execute(text(f"""
            UPDATE {quote(STATE_TABLE)}
            SET
                initial_complete = TRUE,
                last_success_at = :sync_started_at,
                updated_at = NOW()
            WHERE pipeline_name = :pipeline_name
        """), {
            "pipeline_name": PIPELINE_NAME,
            "sync_started_at": sync_started_at,
        })

        conn.execute(text(f"""
            DELETE FROM {quote(PROGRESSION_TABLE)}
        """))


def update_incremental_watermark(run_started_at):
    with engine.begin() as conn:
        conn.execute(text(f"""
            UPDATE {quote(STATE_TABLE)}
            SET
                last_success_at = :run_started_at,
                updated_at = NOW()
            WHERE pipeline_name = :pipeline_name
        """), {
            "pipeline_name": PIPELINE_NAME,
            "run_started_at": run_started_at,
        })


def get_window_progress(window_start, window_end):
    with engine.connect() as conn:
        return conn.execute(text(f"""
            SELECT last_page, done
            FROM {quote(PROGRESSION_TABLE)}
            WHERE
                window_start = :window_start
                AND window_end = :window_end
        """), {
            "window_start": window_start,
            "window_end": window_end,
        }).mappings().fetchone()


def save_window_progress(window_start, window_end, last_page, done=False):
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {quote(PROGRESSION_TABLE)} (
                window_start,
                window_end,
                last_page,
                done,
                updated_at
            )
            VALUES (
                :window_start,
                :window_end,
                :last_page,
                :done,
                NOW()
            )
            ON CONFLICT (window_start, window_end)
            DO UPDATE SET
                last_page = EXCLUDED.last_page,
                done = EXCLUDED.done,
                updated_at = NOW()
        """), {
            "window_start": window_start,
            "window_end": window_end,
            "last_page": last_page,
            "done": done,
        })


# ─── UPSERT ET SUPPRESSION LOCALE ────────────────────────────


def remove_nul_characters(value):
    """
    Supprime récursivement les caractères NUL interdits par PostgreSQL.
    Les interventions et les champs sont conservés.
    """
    if isinstance(value, str):
        return value.replace("\x00", " ")

    if isinstance(value, list):
        return [remove_nul_characters(item) for item in value]

    if isinstance(value, dict):
        return {
            key: remove_nul_characters(item)
            for key, item in value.items()
        }

    return value


def save_denied_batch(batch, last_seen_at):
    # Nettoyage avant la transformation : traite aussi les listes et objets JSON.
    cleaned_batch = [
        remove_nul_characters(operation)
        for operation in batch
    ]

    df = clean_operations(cleaned_batch, last_seen_at)

    # Sécurité supplémentaire après la transformation en DataFrame.
    text_columns = df.select_dtypes(include=["object"]).columns
    for column in text_columns:
        df[column] = df[column].map(
            lambda value: value.replace("\x00", " ")
            if isinstance(value, str)
            else value
        )

    if df.empty:
        return 0

    temp_table = f"tmp_operations_denied_{uuid.uuid4().hex[:16]}"

    insert_columns = ", ".join(
        quote(column)
        for column in ALL_TARGET_COLUMNS
    )

    update_columns = [
        column
        for column in ALL_TARGET_COLUMNS
        if column != OPERATION_KEY_COLUMN
    ]

    update_clause = ", ".join(
        f"{quote(column)} = EXCLUDED.{quote(column)}"
        for column in update_columns
    )

    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TEMPORARY TABLE {quote(temp_table)}
            (LIKE {quote(TARGET_TABLE)} INCLUDING DEFAULTS)
            ON COMMIT DROP
        """))

        df.to_sql(
            temp_table,
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=200,
        )

        conn.execute(text(f"""
            INSERT INTO {quote(TARGET_TABLE)} ({insert_columns})
            SELECT {insert_columns}
            FROM {quote(temp_table)}
            ON CONFLICT ({quote(OPERATION_KEY_COLUMN)})
            DO UPDATE SET {update_clause}
        """))

    print(f"UPSERT denied : {len(df)} lignes")
    return len(df)


def delete_no_longer_denied(operations):
    operation_keys = sorted({
        build_operation_key(operation)
        for operation in operations
        if isinstance(operation, dict)
    })

    if not operation_keys:
        return 0

    statement = text(f"""
        DELETE FROM {quote(TARGET_TABLE)}
        WHERE {quote(OPERATION_KEY_COLUMN)} IN :operation_keys
    """).bindparams(
        bindparam("operation_keys", expanding=True)
    )

    deleted = 0

    for start in range(0, len(operation_keys), 1_000):
        chunk = operation_keys[start:start + 1_000]

        with engine.begin() as conn:
            result = conn.execute(
                statement,
                {"operation_keys": chunk},
            )
            deleted += result.rowcount

    return deleted


# ─── FENÊTRES ET PAGINATION ───────────────────────────────────


def iter_windows(start_date, end_date):
    current_start = start_date

    while current_start <= end_date:
        current_end = min(
            current_start + timedelta(days=WINDOW_DAYS - 1),
            end_date,
        )

        yield current_start, current_end
        current_start = current_end + timedelta(days=1)


# ─── CHARGEMENT INITIAL ──────────────────────────────────────


def sync_one_initial_window(window_start, window_end, sync_started_at):
    progression = get_window_progress(window_start, window_end)

    if progression and progression["done"]:
        return 0

    page = progression["last_page"] + 1 if progression else 1
    batch = []
    loaded = 0

    while True:
        params = build_operation_params(
            status=DENIED_STATUS,
            page=page,
            **{
                "from": api_datetime(window_start),
                "to": api_datetime(window_end, end_of_day=True),
            },
        )

        data = call_intent_api(params)
        operations = get_operations_from_response(data)

        if not operations:
            if batch:
                save_denied_batch(batch, sync_started_at)

            save_window_progress(
                window_start,
                window_end,
                page,
                done=True,
            )

            return loaded

        batch.extend(operations)
        loaded += len(operations)

        print(
            f"denied | {window_start} → {window_end} | "
            f"page {page} | {loaded} lignes"
        )

        if len(batch) >= BATCH_SIZE:
            save_denied_batch(batch, sync_started_at)

            save_window_progress(
                window_start,
                window_end,
                page,
                done=False,
            )

            batch = []

        if should_load_next_page(data, operations):
            page += 1
            continue

        if batch:
            save_denied_batch(batch, sync_started_at)

        save_window_progress(
            window_start,
            window_end,
            page,
            done=True,
        )

        return loaded


def run_initial_backfill(sync_started_at):
    total_loaded = 0

    print("\n===== STATUT : DENIED =====")

    for window_start, window_end in iter_windows(
        INITIAL_SYNC_FROM,
        INITIAL_SYNC_TO,
    ):
        total_loaded += sync_one_initial_window(
            window_start,
            window_end,
            sync_started_at,
        )

    if DELETE_STALE_AFTER_FULL_BACKFILL:
        with engine.begin() as conn:
            result = conn.execute(text(f"""
                DELETE FROM {quote(TARGET_TABLE)}
                WHERE
                    last_seen_at IS NULL
                    OR last_seen_at < :sync_started_at
            """), {
                "sync_started_at": sync_started_at,
            })

        print(
            f"Opérations retirées de la table denied : "
            f"{result.rowcount}"
        )

    mark_initial_sync_complete(sync_started_at)

    print(
        f"\nChargement initial denied terminé : "
        f"{total_loaded} lignes traitées"
    )


# ─── SYNCHRONISATION INCRÉMENTALE ─────────────────────────────


def run_incremental_sync(last_success_at):
    if last_success_at is None:
        raise RuntimeError(
            "Aucune date de synchronisation disponible."
        )

    run_started_at = utc_now()
    since = as_utc(last_success_at) - DELTA_OVERLAP

    print(
        "\n===== SYNCHRONISATION DENIED "
        f"DEPUIS {api_iso_datetime(since)} ====="
    )

    page = 1
    total_denied = 0
    total_removed = 0

    while True:
        params = build_operation_params(
            page=page,
            since=api_iso_datetime(since),
        )

        data = call_intent_api(params)
        operations = get_operations_from_response(data)

        if not operations:
            break

        denied_operations = [
            operation
            for operation in operations
            if operation.get("status") == DENIED_STATUS
        ]

        no_longer_denied_operations = [
            operation
            for operation in operations
            if operation.get("status") != DENIED_STATUS
        ]

        total_denied += save_denied_batch(
            denied_operations,
            run_started_at,
        )

        total_removed += delete_no_longer_denied(
            no_longer_denied_operations
        )

        print(
            f"delta denied | page {page} | "
            f"{len(operations)} modifications lues"
        )

        if should_load_next_page(data, operations):
            page += 1
            continue

        break

    update_incremental_watermark(run_started_at)

    print(
        "\nSynchronisation denied terminée : "
        f"{total_denied} opérations refusées mises à jour, "
        f"{total_removed} opérations retirées."
    )


# ─── FONCTION APPELÉE PAR main.py ────────────────────────────


def get_denied_operations(force_full=False):
    """
    Premier lancement :
        get_denied_operations()

    Lancements suivants :
        get_denied_operations()
        -> récupère uniquement les opérations modifiées depuis le dernier succès.

    Pour relancer entièrement l'historique denied :
        get_denied_operations(force_full=True)
    """
    init_tables()
    state = get_sync_state()

    if force_full or not state or not state["initial_complete"]:
        sync_started_at = begin_or_resume_initial_sync(
            force_full=force_full
        )

        print(
            "\n===== CHARGEMENT INITIAL DES OPÉRATIONS REFUSÉES ====="
        )

        run_initial_backfill(sync_started_at)

    else:
        run_incremental_sync(state["last_success_at"])


if __name__ == "__main__":
    get_denied_operations()
