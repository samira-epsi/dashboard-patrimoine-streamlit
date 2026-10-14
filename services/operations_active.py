import json
import hashlib
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from api.client import get
from sqlalchemy import bindparam, create_engine, inspect, text

from config import DB_URL


# ─── CONFIGURATION ───────────────────────────────────────────

engine = create_engine(DB_URL, pool_pre_ping=True)

TARGET_TABLE = "operations_active_current"
PROGRESSION_TABLE = "operations_active_progression"
STATE_TABLE = "operations_active_sync_state"
PIPELINE_NAME = "operations_active"
OPERATION_KEY_COLUMN = "operation_key"
NO_CONTRACT_KEY = "__NO_CONTRACT__"
NO_REFERENCE_PREFIX = "__NO_REFERENCE__"

ACTIVE_STATUS = ("open", "pending", "hold")
INACTIVE_STATUS = ("closed", "denied")

PER_PAGE = 100
BATCH_SIZE = 1_000
REQUESTS_PER_MINUTE = 300
MAX_RETRIES = 7

# Une semaine par requête métier : plus doux pour l'API qu'un historique géant.
WINDOW_DAYS = 7

# Modifie cette date uniquement si tu connais la première date utile d'Intent.
INITIAL_SYNC_FROM = date(2010, 1, 1)
INITIAL_SYNC_TO = date.today() + timedelta(days=730)

# Les dix dernières minutes sont relues à chaque mise à jour.
DELTA_OVERLAP = timedelta(minutes=10)

# À laisser à False tant que tu n'as pas comparé tes volumes avec Intent.
DELETE_STALE_AFTER_FULL_BACKFILL = False

# Si Intent refuse le paramètre fields avec une erreur 400, passe à False.
USE_FIELDS_FILTER = True


# ─── CHAMPS INTENT ───────────────────────────────────────────

API_ROOT_FIELDS = [
    "reference",
    "type",
    "status",
    "creationDate",
    "lastUpdateDate",
    "firstEventDate",
    "eventDate",
    "logDate",
    "event",
    "workType",
    "eventHistory",
    "criticalLevel",
    "description",
    "technicalReason",
    "issuer",
    "contract",
    "service",
    "location",
    "responseTime",
    "resolutionDuration",
    "equipmentStatus",
    "parentReference",
]

OPERATION_COLUMNS = {
    "reference": "reference",
    "type": "type",
    "status": "status",
    "creationDate": "creation_date",
    "lastUpdateDate": "last_update_date",
    "firstEventDate": "first_event_date",
    "eventDate": "event_date",
    "logDate": "log_date",
    "event": "event",
    "workType": "work_type",
    "eventHistory": "event_history",
    "criticalLevel": "critical_level",
    "description": "description",
    "technicalReason": "technical_reason",
    "issuer.entity.id": "provider_id",
    "issuer.entity.label": "provider_name",
    "contract.reference": "contract_reference",
    "contract.label": "contract_label",
    "contract.topic": "contract_topic",
    "service.code": "service_code",
    "service.label": "service_label",
    "service.description": "service_description",
    "service.originalCode": "service_original_code",
    "service.sla.maxTimeToIntervention.value": "sla_intervention_value",
    "service.sla.maxTimeToIntervention.unit": "sla_intervention_unit",
    "service.sla.maxTimeToRecovery.value": "sla_recovery_value",
    "service.sla.maxTimeToRecovery.unit": "sla_recovery_unit",
    "location.assetReference": "asset_reference",
    "location.address.way": "address",
    "location.address.city": "city",
    "location.address.zip": "zip_code",
    "location.address.country": "country",
    "location.owner.id": "owner_id",
    "location.owner.label": "owner_name",
    "responseTime": "response_time",
    "resolutionDuration": "resolution_duration",
    "equipmentStatus": "equipment_status",
    "parentReference": "parent_reference",
}

TARGET_COLUMNS = list(OPERATION_COLUMNS.values()) + [OPERATION_KEY_COLUMN]
ALL_TARGET_COLUMNS = TARGET_COLUMNS + ["last_seen_at"]

FLOAT_COLUMNS = {
    "sla_intervention_value",
    "sla_recovery_value",
    "response_time",
    "resolution_duration",
}

INTEGER_COLUMNS = {
    "critical_level",
}

DATETIME_COLUMNS = {
    "creation_date",
    "last_update_date",
    "first_event_date",
    "event_date",
    "log_date",
}

COLUMN_SQL_TYPES = {column: "TEXT" for column in TARGET_COLUMNS}

for column in FLOAT_COLUMNS:
    COLUMN_SQL_TYPES[column] = "DOUBLE PRECISION"

for column in INTEGER_COLUMNS:
    COLUMN_SQL_TYPES[column] = "INTEGER"

for column in DATETIME_COLUMNS:
    COLUMN_SQL_TYPES[column] = "TIMESTAMPTZ"

COLUMN_SQL_TYPES["last_seen_at"] = "TIMESTAMPTZ"


# ─── OUTILS ──────────────────────────────────────────────────

def quote(identifier):
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


def utc_now():
    return datetime.now(timezone.utc)


def as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def api_datetime(day, end_of_day=False):
    if end_of_day:
        return f"{day.isoformat()}T23:59:59.999Z"

    return f"{day.isoformat()}T00:00:00.000Z"


def api_iso_datetime(value):
    return as_utc(value).isoformat().replace("+00:00", "Z")


def json_safe_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


def identity_value(value):
    """Retourne une valeur stable pour fabriquer une clé technique."""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value or "").strip()


def build_operation_key(operation):
    """
    Une ligne métier correspond à une opération dans son contexte contractuel.
    Le contrat reste NULL en base lorsqu'il est absent ; le marqueur ne sert
    qu'à la clé technique, afin que les UPSERT restent fiables.
    """
    reference = identity_value(operation.get("reference"))
    contract = operation.get("contract") or {}
    contract_reference = identity_value(
        contract.get("reference") if isinstance(contract, dict) else None
    )

    if reference:
        contract_part = contract_reference or NO_CONTRACT_KEY
        return f"ref:{reference}|contract:{contract_part}"

    # Intent n'a fourni aucun identifiant métier : on conserve malgré tout la
    # ligne avec une empreinte stable du payload reçu.
    payload = json.dumps(
        operation,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{NO_REFERENCE_PREFIX}|{digest}"


def normalise_float(series):
    return pd.to_numeric(
        series.astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False),
        errors="coerce",
    ).astype("float64")


def normalise_integer(series):
    numeric = pd.to_numeric(
        series.astype("string").str.strip(),
        errors="coerce",
    )

    return numeric.round().astype("Int64")


# ─── LIMITATION DU DÉBIT ─────────────────────────────────────

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


def get_error_details(error):
    response = getattr(error, "response", None)

    if response is None:
        return None, {}

    return (
        getattr(response, "status_code", None),
        getattr(response, "headers", {}) or {},
    )


def get_retry_delay(headers, attempt, status_code):
    if status_code == 429:
        retry_after = headers.get("Retry-After")

        try:
            return max(float(retry_after), 1)
        except (TypeError, ValueError):
            return 60

    return min(120, 5 * (2 ** attempt))


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
                status       VARCHAR(50) NOT NULL,
                window_start DATE NOT NULL,
                window_end   DATE NOT NULL,
                last_page    INTEGER NOT NULL DEFAULT 0,
                done         BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (status, window_start, window_end)
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

        # Migration des lignes déjà présentes : elles avaient auparavant une
        # unicité fondée uniquement sur reference.
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

        # L'ancien index empêchait de conserver une même opération sous deux
        # contrats différents.
        conn.execute(text(f"""
            DROP INDEX IF EXISTS
            {quote("idx_operations_active_reference")}
        """))

        conn.execute(text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS
            {quote("idx_operations_active_operation_key")}
            ON {quote(TARGET_TABLE)} ({quote(OPERATION_KEY_COLUMN)})
        """))


# ─── ÉTAT DU PIPELINE ─────────────────────────────────────────

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


def get_window_progress(status, window_start, window_end):
    with engine.connect() as conn:
        return conn.execute(text(f"""
            SELECT last_page, done
            FROM {quote(PROGRESSION_TABLE)}
            WHERE
                status = :status
                AND window_start = :window_start
                AND window_end = :window_end
        """), {
            "status": status,
            "window_start": window_start,
            "window_end": window_end,
        }).mappings().fetchone()


def save_window_progress(
    status,
    window_start,
    window_end,
    last_page,
    done=False,
):
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {quote(PROGRESSION_TABLE)} (
                status,
                window_start,
                window_end,
                last_page,
                done,
                updated_at
            )
            VALUES (
                :status,
                :window_start,
                :window_end,
                :last_page,
                :done,
                NOW()
            )
            ON CONFLICT (status, window_start, window_end)
            DO UPDATE SET
                last_page = EXCLUDED.last_page,
                done = EXCLUDED.done,
                updated_at = NOW()
        """), {
            "status": status,
            "window_start": window_start,
            "window_end": window_end,
            "last_page": last_page,
            "done": done,
        })


# ─── NETTOYAGE ───────────────────────────────────────────────

def clean_operations(batch, last_seen_at):
    if not batch:
        return pd.DataFrame(columns=ALL_TARGET_COLUMNS)

    raw_df = pd.json_normalize(batch, sep=".")
    cleaned_df = pd.DataFrame(index=raw_df.index)

    for api_column, database_column in OPERATION_COLUMNS.items():
        if api_column in raw_df.columns:
            cleaned_df[database_column] = raw_df[api_column]
        else:
            cleaned_df[database_column] = None

    cleaned_df[OPERATION_KEY_COLUMN] = [
        build_operation_key(operation)
        for operation in batch
    ]

    for column in DATETIME_COLUMNS:
        cleaned_df[column] = pd.to_datetime(
            cleaned_df[column],
            errors="coerce",
            utc=True,
        )

    for column in FLOAT_COLUMNS:
        cleaned_df[column] = normalise_float(cleaned_df[column])

    for column in INTEGER_COLUMNS:
        cleaned_df[column] = normalise_integer(cleaned_df[column])

    text_columns = [
        column
        for column in TARGET_COLUMNS
        if (
            column not in DATETIME_COLUMNS
            and column not in FLOAT_COLUMNS
            and column not in INTEGER_COLUMNS
        )
    ]

    for column in text_columns:
        cleaned_df[column] = cleaned_df[column].map(json_safe_value)

    # Uniquement les doublons stricts : même opération et même contrat.
    # Les mêmes références liées à des contrats différents sont conservées.
    cleaned_df = cleaned_df.drop_duplicates(
        subset=[OPERATION_KEY_COLUMN],
        keep="last",
    )

    cleaned_df["last_seen_at"] = pd.Timestamp(last_seen_at)

    return cleaned_df[ALL_TARGET_COLUMNS]


# ─── UPSERT ──────────────────────────────────────────────────

def save_active_batch(batch, last_seen_at):
    df = clean_operations(batch, last_seen_at)

    if df.empty:
        return 0

    # Cette table temporaire reprend exactement les types de la vraie table.
    # C'est ce qui évite les erreurs TEXT -> DOUBLE PRECISION.
    temp_table = f"tmp_operations_{uuid.uuid4().hex[:16]}"

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

    print(f"UPSERT : {len(df)} lignes")
    return len(df)


def delete_inactive_operations(operations):
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


# ─── API ET PAGINATION ───────────────────────────────────────

def build_operation_params(**extra_params):
    params = {
        "page": 1,
        "perPage": PER_PAGE,
    }

    if USE_FIELDS_FILTER:
        params["fields"] = ",".join(API_ROOT_FIELDS)

    params.update(extra_params)

    return params


def get_operations_from_response(data):
    operations = data.get(
        "_embedded",
        {},
    ).get(
        "operations",
        [],
    )

    if not isinstance(operations, list):
        raise TypeError(
            "La réponse Intent ne contient pas une liste d'opérations."
        )

    return operations


def response_has_next_page(data):
    links = data.get("_links")

    if not isinstance(links, dict):
        return None

    next_link = links.get("next")

    if isinstance(next_link, dict):
        return bool(next_link.get("href"))

    return bool(next_link)


def should_load_next_page(data, operations):
    """
    Détermine s'il faut demander la page suivante.

    Intent ne fournit pas toujours _links.next de manière exploitable.
    Une page pleine (PER_PAGE opérations) peut donc cacher une page suivante :
    on la demande systématiquement. Au pire, une unique requête vide est faite
    lorsqu'un résultat contient exactement PER_PAGE opérations.
    """
    next_page = response_has_next_page(data)

    return next_page is True or len(operations) >= PER_PAGE


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

def sync_one_initial_window(
    status,
    window_start,
    window_end,
    sync_started_at,
):
    progression = get_window_progress(
        status,
        window_start,
        window_end,
    )

    if progression and progression["done"]:
        return 0

    page = progression["last_page"] + 1 if progression else 1
    batch = []
    loaded = 0

    while True:
        params = build_operation_params(
            status=status,
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
                save_active_batch(batch, sync_started_at)

            save_window_progress(
                status,
                window_start,
                window_end,
                page,
                done=True,
            )

            return loaded

        batch.extend(operations)
        loaded += len(operations)

        print(
            f"{status} | {window_start} → {window_end} | "
            f"page {page} | {loaded} lignes"
        )

        if len(batch) >= BATCH_SIZE:
            save_active_batch(batch, sync_started_at)

            save_window_progress(
                status,
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
            save_active_batch(batch, sync_started_at)

        save_window_progress(
            status,
            window_start,
            window_end,
            page,
            done=True,
        )

        return loaded


def run_initial_backfill(sync_started_at):
    total_loaded = 0

    for status in ACTIVE_STATUS:
        print(f"\n===== STATUT : {status.upper()} =====")

        for window_start, window_end in iter_windows(
            INITIAL_SYNC_FROM,
            INITIAL_SYNC_TO,
        ):
            total_loaded += sync_one_initial_window(
                status,
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
            f"Opérations retirées de la table active : "
            f"{result.rowcount}"
        )

    mark_initial_sync_complete(sync_started_at)

    print(
        f"\nChargement initial terminé : "
        f"{total_loaded} lignes traitées"
    )


# ─── MISE À JOUR INCRÉMENTALE ────────────────────────────────

def run_incremental_sync(last_success_at):
    if last_success_at is None:
        raise RuntimeError(
            "Aucune date de synchronisation disponible."
        )

    run_started_at = utc_now()
    since = as_utc(last_success_at) - DELTA_OVERLAP

    print(
        "\n===== SYNCHRONISATION INCRÉMENTALE "
        f"DEPUIS {api_iso_datetime(since)} ====="
    )

    page = 1
    total_active = 0
    total_deleted = 0

    while True:
        params = build_operation_params(
            page=page,
            since=api_iso_datetime(since),
        )

        data = call_intent_api(params)
        operations = get_operations_from_response(data)

        if not operations:
            break

        active_operations = [
            operation
            for operation in operations
            if operation.get("status") in ACTIVE_STATUS
        ]

        inactive_operations = [
            operation
            for operation in operations
            if operation.get("status") in INACTIVE_STATUS
        ]

        total_active += save_active_batch(
            active_operations,
            run_started_at,
        )

        total_deleted += delete_inactive_operations(
            inactive_operations
        )

        print(
            f"delta | page {page} | "
            f"{len(operations)} modifications lues"
        )

        if should_load_next_page(data, operations):
            page += 1
            continue

        break

    update_incremental_watermark(run_started_at)

    print(
        "\nSynchronisation incrémentale terminée : "
        f"{total_active} opérations actives mises à jour, "
        f"{total_deleted} opérations retirées."
    )


# ─── FONCTION APPELÉE PAR main.py ────────────────────────────

def get_active_operations(force_full=False):
    """
    Premier lancement :
        get_active_operations()

    Lancements suivants :
        get_active_operations()
        -> récupère uniquement les modifications récentes.

    Pour relancer entièrement l'historique :
        get_active_operations(force_full=True)
    """
    init_tables()
    state = get_sync_state()

    if force_full or not state or not state["initial_complete"]:
        sync_started_at = begin_or_resume_initial_sync(
            force_full=force_full
        )

        print(
            "\n===== CHARGEMENT INITIAL DES OPÉRATIONS ACTIVES ====="
        )

        run_initial_backfill(sync_started_at)

    else:
        run_incremental_sync(state["last_success_at"])


if __name__ == "__main__":
    get_active_operations()
