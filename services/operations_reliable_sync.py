import csv
import json
import math
import os
import sys
import time
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import bindparam, create_engine, text

from api.client import get
from config import DB_URL
from services.operations_active import (
    ALL_TARGET_COLUMNS,
    API_ROOT_FIELDS,
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
    utc_now,
)

# ============================================================
# CONFIGURATION
# ============================================================

engine = create_engine(DB_URL, pool_pre_ping=True)

ACTIVE_TABLE = "operations_active_current"
CLOSED_TABLE = "operations_closed_current"
DENIED_TABLE = "operations_denied_current"

TABLE_BY_STATUS = {
    "open": ACTIVE_TABLE,
    "pending": ACTIVE_TABLE,
    "hold": ACTIVE_TABLE,
    "closed": CLOSED_TABLE,
    "denied": DENIED_TABLE,
}

STATUSES = tuple(TABLE_BY_STATUS)
ALL_CURRENT_TABLES = tuple(sorted(set(TABLE_BY_STATUS.values())))

HISTORY_START = date(2010, 1, 1)
ACTIVE_END_OFFSET_DAYS = 730

PER_PAGE = 100
REQUESTS_PER_MINUTE = int(os.getenv("INTENT_REQUESTS_PER_MINUTE", "120"))
MAX_RETRIES = 10
UPSERT_CHUNK_SIZE = 1000
DELTA_OVERLAP = timedelta(minutes=15)
USE_FIELDS_FILTER = True

STATE_TABLE = "operations_reliable_sync_state"
RUN_LOG_TABLE = "operations_reliable_sync_runs"
RECON_TABLE = "operations_reconciliation_state"
ARCHIVE_TABLE = "operations_orphan_archive"

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
RUN_DAY = datetime.now().strftime("%Y%m%d")
PROBLEM_FILE = os.path.join(LOG_DIR, f"operations_reliable_sync_{RUN_DAY}.csv")

PROBLEM_COLUMNS = [
    "detected_at",
    "run_id",
    "status",
    "period_start",
    "period_end",
    "problem_type",
    "operation_key",
    "reference",
    "contract_reference",
    "event_date",
    "source",
    "details",
    "automatic_action",
    "user_action",
    "payload_json",
]


def log(message=""):
    """Affichage console horodaté et immédiat."""
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


# ============================================================
# OUTILS GENERAUX
# ============================================================


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def remove_nul(value):
    if isinstance(value, str):
        return value.replace("\x00", " ")
    if isinstance(value, list):
        return [remove_nul(item) for item in value]
    if isinstance(value, dict):
        return {key: remove_nul(item) for key, item in value.items()}
    return value


def parse_api_datetime(value):
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def get_contract_reference(operation):
    contract = operation.get("contract") if isinstance(operation, dict) else None
    if isinstance(contract, dict):
        return contract.get("reference")
    if isinstance(operation, dict):
        return operation.get("contractReference") or operation.get("contract.reference")
    return None


def dedupe_latest_operations(operations):
    """Une seule version par operation_key, la plus récemment mise à jour."""
    by_key = {}
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            continue
        key = build_operation_key(operation)
        candidate = (
            parse_api_datetime(operation.get("lastUpdateDate")),
            index,
            operation,
        )
        previous = by_key.get(key)
        if previous is None or candidate[:2] >= previous[:2]:
            by_key[key] = candidate
    return {key: value[2] for key, value in by_key.items()}


def index_operations_by_reference(operations):
    """Indexe les opérations API par référence d'intervention."""
    by_reference = {}

    for operation in operations:
        if not isinstance(operation, dict):
            continue

        reference = operation.get("reference")
        if not reference:
            continue

        by_reference.setdefault(str(reference), []).append(operation)

    return by_reference


def choose_latest_operation(operations):
    """Choisit la version API ayant le lastUpdateDate le plus récent."""
    operations = [op for op in operations if isinstance(op, dict)]
    if not operations:
        return None

    return max(
        operations,
        key=lambda op: parse_api_datetime(op.get("lastUpdateDate")),
    )


def iter_months(start_date, end_date):
    current = date(start_date.year, start_date.month, 1)
    while current <= end_date:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)
        month_start = max(start_date, current)
        month_end = min(end_date, next_month - timedelta(days=1))
        yield month_start, month_end
        current = next_month


def init_problem_file():
    """
    Un seul fichier CSV de problèmes par jour.
    Les différents runs sont distingués grâce au run_id.
    Le fichier existant n'est jamais écrasé.
    """
    if os.path.exists(PROBLEM_FILE) and os.path.getsize(PROBLEM_FILE) > 0:
        return

    with open(PROBLEM_FILE, "w", newline="", encoding="utf-8-sig") as file:
        csv.DictWriter(file, fieldnames=PROBLEM_COLUMNS).writeheader()



def get_log_actions(problem_type):
    actions = {
        "API_DUPLICATE": (
            "Aucune duplication en base : dédoublonnage par operation_key.",
            "Aucune action immédiate. Surveiller si le même doublon revient souvent."
        ),
        "MISSING_IN_DB": (
            "Réparation automatique par UPSERT dans la table current correspondant au statut API.",
            "Aucune action si la réconciliation finit certifiée. Vérifier seulement si l'anomalie revient."
        ),
        "EXTRA_IN_DB": (
            "Recherche de la même référence dans PostgreSQL, puis dans Intent si nécessaire.",
            "Lire la ligne suivante liée à cette opération : EXTRA_REASSIGNED, EXTRA_REFRESHED, EXTRA_ARCHIVED_NOT_FOUND ou EXTRA_UNRESOLVED."
        ),
        "EXTRA_REFRESHED": (
            "Opération retrouvée dans Intent, réactualisée et routée vers la bonne table selon son statut actuel.",
            "Aucune action si le statut/date correspondent à Intent."
        ),
        "EXTRA_REASSIGNED": (
            "La même référence d'intervention a été retrouvée dans Intent avec une autre clé métier, un autre contrat et/ou un autre statut. La version API actuelle est routée puis l'ancienne ligne est archivée et retirée de la table current.",
            "Aucune action si le nouveau contrat/statut correspond bien à Intent."
        ),
        "EXTRA_ARCHIVED_NOT_FOUND": (
            "Intent a confirmé total=0 pour la recherche exacte par référence. L'ancienne ligne est archivée puis retirée des tables current.",
            "Aucune action si le run se termine correctement."
        ),
        "EXTRA_UNRESOLVED": (
            "Aucune modification automatique de la donnée current.",
            "Vérifier manuellement reference + contract_reference dans Intent/Postman et décider du statut à appliquer."
        ),
        "UNKNOWN_STATUS": (
            "Aucun routage effectué et checkpoint non validé.",
            "Identifier le nouveau statut Intent et l'ajouter à TABLE_BY_STATUS avant de relancer."
        ),
        "RECONCILIATION_ERROR": (
            "Le mois n'est pas certifié et l'erreur est conservée dans le log.",
            "Corriger l'erreur API/BDD puis relancer la réconciliation ou la certification."
        ),
    }
    return actions.get(problem_type, (
        "Anomalie enregistrée dans le journal.",
        "Examiner la ligne si le run n'est pas certifié ou si l'anomalie persiste."
    ))

def write_problem(
    run_id,
    problem_type,
    *,
    status=None,
    period_start=None,
    period_end=None,
    operation_key=None,
    reference=None,
    contract_reference=None,
    event_date=None,
    source=None,
    details=None,
    payload=None,
):
    automatic_action, user_action = get_log_actions(problem_type)

    with open(PROBLEM_FILE, "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=PROBLEM_COLUMNS)
        writer.writerow({
            "detected_at": datetime.now().isoformat(timespec="seconds"),
            "run_id": run_id,
            "status": status,
            "period_start": period_start,
            "period_end": period_end,
            "problem_type": problem_type,
            "operation_key": operation_key,
            "reference": reference,
            "contract_reference": contract_reference,
            "event_date": event_date,
            "source": source,
            "details": details,
            "automatic_action": automatic_action,
            "user_action": user_action,
            "payload_json": safe_json(payload) if payload is not None else None,
        })

# ============================================================
# RATE LIMIT + API
# ============================================================


class RateLimiter:
    def __init__(self, requests_per_minute):
        self.interval = 60 / requests_per_minute
        self.next_slot = time.monotonic()

    def wait(self):
        delay = self.next_slot - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self.next_slot = max(time.monotonic(), self.next_slot) + self.interval


rate_limiter = RateLimiter(REQUESTS_PER_MINUTE)


def call_intent_api(path="/operations/v2/operations", params=None, allow_404=False):
    params = params or {}

    for attempt in range(MAX_RETRIES):
        rate_limiter.wait()
        try:
            data = get(path, params=params)
            if not isinstance(data, dict):
                raise TypeError("La réponse API Intent n'est pas un dictionnaire JSON.")
            return data

        except Exception as error:
            status_code, headers = get_error_details(error)

            if allow_404 and status_code == 404:
                return None

            network_error = error.__class__.__name__ in {
                "ConnectionError", "Timeout", "ReadTimeout", "ConnectTimeout"
            }
            retryable = status_code in {429, 500, 502, 503, 504} or network_error

            if not retryable or attempt == MAX_RETRIES - 1:
                log(
                    f"❌ API échec définitif | path={path} | "
                    f"status={status_code or error.__class__.__name__} | {error}"
                )
                raise

            delay = get_retry_delay(headers, attempt, status_code)
            log(
                f"⚠️ API {status_code or error.__class__.__name__} | "
                f"nouvelle tentative dans {delay:.0f}s "
                f"({attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(delay)

    raise RuntimeError("Impossible de joindre Intent.")


def build_list_params(**extra):
    params = {"page": 1, "perPage": PER_PAGE}
    if USE_FIELDS_FILTER:
        params["fields"] = ",".join(API_ROOT_FIELDS)
    params.update(extra)
    return params


def get_api_total(status, period_start, period_end):
    params = build_list_params(
        page=1,
        perPage=1,
        status=status,
        **{
            "from": api_datetime(period_start),
            "to": api_datetime(period_end, end_of_day=True),
        },
    )
    try:
        data = call_intent_api(params=params)
    except Exception as error:
        status_code, _ = get_error_details(error)
        if status_code != 400:
            raise
        params["perPage"] = PER_PAGE
        data = call_intent_api(params=params)

    if data.get("total") is None:
        raise RuntimeError("Champ total absent de la réponse Intent.")
    return int(data["total"])


def fetch_one_complete_pass(base_params):
    """
    Lit une passe complète d'une requête paginée.

    Le total Intent peut évoluer pendant la lecture car le jeu de données est vivant.
    On ne plante donc pas si le total bouge :
      - si le total augmente, on étend le nombre de pages à lire ;
      - s'il diminue, on conserve le maximum déjà observé ;
      - une page vide arrête proprement la passe.

    Cette fonction ne cherche pas à figer une API vivante.
    Le DAILY l'utilise en une seule passe complète.
    RECONCILE/CERTIFY peuvent ajouter leurs propres passes de contrôle.
    """
    first_params = dict(base_params)
    first_params["page"] = 1
    first_params["perPage"] = PER_PAGE

    log(
        "→ Première page API | "
        f"status={first_params.get('status')} | "
        f"since={first_params.get('since')} | "
        f"from={first_params.get('from')} | "
        f"to={first_params.get('to')}"
    )

    first = call_intent_api(params=first_params)
    observed_total = int(first.get("total", 0) or 0)
    max_total = observed_total
    operations = list(get_operations_from_response(first))

    if observed_total == 0:
        log("← API total=0 | aucune opération")
        return operations, 0

    expected_pages = max(1, math.ceil(max_total / PER_PAGE))
    log(
        f"← Première page reçue | total={observed_total} | "
        f"pages prévues={expected_pages} | lignes page 1={len(operations)}"
    )

    page = 2
    while page <= expected_pages:
        params = dict(base_params)
        params["page"] = page
        params["perPage"] = PER_PAGE

        log(f"→ Lecture page {page}/{expected_pages}")
        data = call_intent_api(params=params)

        page_total = int(data.get("total", observed_total) or 0)
        page_operations = list(get_operations_from_response(data))

        if page_total != observed_total:
            log(
                f"ℹ️ Population API modifiée pendant la passe : "
                f"{observed_total} → {page_total}"
            )
            observed_total = page_total
            if page_total > max_total:
                max_total = page_total
                expected_pages = max(
                    expected_pages,
                    math.ceil(max_total / PER_PAGE),
                )

        if not page_operations:
            log(
                f"ℹ️ Page {page} vide. Fin de passe anticipée "
                f"(max total observé={max_total})."
            )
            break

        operations.extend(page_operations)
        log(
            f"← Page {page}/{expected_pages} reçue | "
            f"{len(page_operations)} lignes | cumul={len(operations)}"
        )
        page += 1

    log(
        f"✓ Passe terminée | lignes brutes reçues={len(operations)} | "
        f"max total observé={max_total}"
    )
    return operations, max_total


def fetch_daily_delta_once(base_params, run_id):
    """
    DAILY : une seule passe complète sur le delta.

    La source Intent peut évoluer pendant la pagination.
    On accepte donc que le total bouge pendant la lecture.

    Sécurités :
      - une seule passe API ;
      - détection et journalisation des doublons ;
      - dédoublonnage par operation_key ;
      - conservation de la version ayant le lastUpdateDate le plus récent ;
      - si l'appel API ou la pagination échoue, une exception remonte et le
        checkpoint n'avance pas ;
      - si l'écriture PostgreSQL échoue, le checkpoint n'avance pas non plus.

    Le contrôle d'exhaustivité historique reste le rôle de RECONCILE/CERTIFY.
    """
    log("===== DELTA | PASSE UNIQUE DAILY =====")

    raw_operations, max_total_observed = fetch_one_complete_pass(base_params)

    key_counts = Counter(
        build_operation_key(op)
        for op in raw_operations
        if isinstance(op, dict)
    )
    duplicate_keys = {
        key: count
        for key, count in key_counts.items()
        if count > 1
    }

    for key, count in duplicate_keys.items():
        sample = next(
            op for op in raw_operations
            if isinstance(op, dict) and build_operation_key(op) == key
        )
        write_problem(
            run_id,
            "API_DUPLICATE",
            status=sample.get("status"),
            operation_key=key,
            reference=sample.get("reference"),
            contract_reference=get_contract_reference(sample),
            event_date=sample.get("eventDate"),
            source="API",
            details=(
                f"operation_key reçue {count} fois "
                "pendant la passe unique DAILY"
            ),
            payload=None,
        )

    latest_by_key = dedupe_latest_operations(raw_operations)
    unique_operations = list(latest_by_key.values())

    log(
        f"DELTA | passe unique terminée | brut={len(raw_operations)} | "
        f"uniques={len(unique_operations)} | "
        f"doublons={len(duplicate_keys)} | "
        f"max total API observé={max_total_observed}"
    )

    if duplicate_keys:
        log(
            f"ℹ️ {len(duplicate_keys)} operation_key dupliquée(s) détectée(s). "
            "Une seule version sera conservée par operation_key."
        )

    return unique_operations, len(raw_operations), max_total_observed


def fetch_reconciliation_set_once(base_params, run_id, context):
    """
    RECONCILE / CERTIFY : une seule passe complète sur la période.

    Contrairement au DAILY, la requête est bornée par statut + période.
    On lit toutes les pages une seule fois, on journalise les doublons API,
    puis on dédoublonne par operation_key en gardant la version ayant le
    lastUpdateDate le plus récent.

    Si l'appel API ou une page échoue, l'exception remonte et aucune décision
    n'est prise pour cette période.
    """
    log(f"===== {context} | PASSE UNIQUE =====")

    operations, max_total_observed = fetch_one_complete_pass(base_params)

    key_counts = Counter(
        build_operation_key(op)
        for op in operations
        if isinstance(op, dict)
    )
    duplicate_keys = {
        key: count
        for key, count in key_counts.items()
        if count > 1
    }

    for key, count in duplicate_keys.items():
        sample = next(
            op for op in operations
            if isinstance(op, dict) and build_operation_key(op) == key
        )
        write_problem(
            run_id,
            "API_DUPLICATE",
            status=sample.get("status"),
            operation_key=key,
            reference=sample.get("reference"),
            contract_reference=get_contract_reference(sample),
            event_date=sample.get("eventDate"),
            source="API",
            details=(
                f"operation_key reçue {count} fois "
                f"({context}, passe unique)"
            ),
            payload=None,
        )

    latest_by_key = dedupe_latest_operations(operations)

    log(
        f"{context} | passe unique terminée | "
        f"brut={len(operations)} | uniques={len(latest_by_key)} | "
        f"doublons={len(duplicate_keys)} | "
        f"max total API observé={max_total_observed}"
    )

    return list(latest_by_key.values()), max_total_observed


# ============================================================
# BASE : TABLES TECHNIQUES / INDEX
# ============================================================


def init_support_tables():
    init_problem_file()

    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {quote(STATE_TABLE)} (
                pipeline_name VARCHAR(100) PRIMARY KEY,
                last_success_at TIMESTAMPTZ,
                last_run_started_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {quote(RUN_LOG_TABLE)} (
                run_id VARCHAR(64) PRIMARY KEY,
                mode VARCHAR(30) NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                finished_at TIMESTAMPTZ,
                success BOOLEAN,
                operations_received BIGINT NOT NULL DEFAULT 0,
                operations_upserted BIGINT NOT NULL DEFAULT 0,
                details TEXT
            )
        """))

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {quote(RECON_TABLE)} (
                status VARCHAR(30) NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                certified BOOLEAN NOT NULL DEFAULT FALSE,
                api_total INTEGER,
                api_unique INTEGER,
                db_unique INTEGER,
                missing_count INTEGER,
                extra_count INTEGER,
                checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (status, period_start, period_end)
            )
        """))

        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {quote(ARCHIVE_TABLE)} (
                id BIGSERIAL PRIMARY KEY,
                operation_key TEXT,
                source_table TEXT NOT NULL,
                archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                reason TEXT NOT NULL,
                row_data JSONB NOT NULL
            )
        """))

    # Index de performance pour les contrôles mensuels.
    # CREATE INDEX (non CONCURRENTLY) est utilisé ici pour rester compatible dans le script.
    with engine.begin() as conn:
        for table in ALL_CURRENT_TABLES:
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {quote(f'idx_{table}_status_event_date')}
                ON {quote(table)} ({quote('status')}, {quote('event_date')})
            """))
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {quote(f'idx_{table}_operation_key_lookup')}
                ON {quote(table)} ({quote(OPERATION_KEY_COLUMN)})
            """))
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {quote(f'idx_{table}_reference_lookup')}
                ON {quote(table)} ({quote('reference')})
            """))


def start_run(mode):
    run_id = uuid.uuid4().hex
    started_at = utc_now()
    log(f"▶ Démarrage run | mode={mode} | run_id={run_id}")
    log(f"  Heure de début : {started_at.isoformat()}")

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {quote(RUN_LOG_TABLE)}
            (run_id, mode, started_at, success)
            VALUES (:run_id, :mode, :started_at, NULL)
        """), {"run_id": run_id, "mode": mode, "started_at": started_at})

    return run_id, started_at


def finish_run(run_id, success, received=0, upserted=0, details=None):
    log(
        f"■ Fin run | run_id={run_id} | success={success} | "
        f"reçues={received} | upsert={upserted}"
    )
    if details:
        log(f"  Détail : {details}")

    with engine.begin() as conn:
        conn.execute(text(f"""
            UPDATE {quote(RUN_LOG_TABLE)}
            SET finished_at = NOW(), success = :success,
                operations_received = :received,
                operations_upserted = :upserted,
                details = :details
            WHERE run_id = :run_id
        """), {
            "run_id": run_id,
            "success": success,
            "received": received,
            "upserted": upserted,
            "details": details,
        })


#  Je ne veux plus qu'on se base sur les anciens appels states en fall back car ils ne sont pas fiables
# def get_reliable_checkpoint():
#     with engine.connect() as conn:
#         row = conn.execute(text(f"""
#             SELECT last_success_at
#             FROM {quote(STATE_TABLE)}
#             WHERE pipeline_name = 'operations_all'
#         """)).mappings().fetchone()
#     if row and row["last_success_at"]:
#         return as_utc(row["last_success_at"])

#     # # Bootstrap sûr depuis les anciens pipelines : on prend la date la plus ancienne.
#     # inspector = inspect(engine)
#     # candidates = []
#     # for table in (
#     #     "operations_active_sync_state",
#     #     "operations_closed_sync_state",
#     #     "operations_denied_sync_state",
#     # ):
#     #     if not inspector.has_table(table):
#     #         continue
#     #     with engine.connect() as conn:
#     #         value = conn.execute(text(f"SELECT MIN(last_success_at) FROM {quote(table)}")).scalar()
#     #     if value:
#     #         candidates.append(as_utc(value))

#     # if candidates:
#     #     checkpoint = min(candidates)
#     #     print(f"Bootstrap checkpoint depuis anciens pipelines : {checkpoint.isoformat()}")
#     #     return checkpoint

#     return None

def get_reliable_checkpoint():
    with engine.connect() as conn:
        row = conn.execute(text(f"""
            SELECT last_success_at
            FROM {quote(STATE_TABLE)}
            WHERE pipeline_name = 'operations_all'
        """)).mappings().fetchone()

    if row and row["last_success_at"]:
        return as_utc(row["last_success_at"])

    return None


def save_checkpoint(last_success_at, run_started_at):
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {quote(STATE_TABLE)}
            (pipeline_name, last_success_at, last_run_started_at, updated_at)
            VALUES ('operations_all', :last_success_at, :run_started_at, NOW())
            ON CONFLICT (pipeline_name)
            DO UPDATE SET
                last_success_at = EXCLUDED.last_success_at,
                last_run_started_at = EXCLUDED.last_run_started_at,
                updated_at = NOW()
        """), {
            "last_success_at": last_success_at,
            "run_started_at": run_started_at,
        })

# ============================================================
# BASE : LECTURE / ECRITURE DES OPERATIONS
# ============================================================


def get_db_count(table, status, period_start, period_end):
    start_value = api_datetime(period_start)
    end_value = api_datetime(period_end, end_of_day=True)
    with engine.connect() as conn:
        return conn.execute(text(f"""
            SELECT COUNT(*)
            FROM {quote(table)}
            WHERE status = :status
              AND event_date >= CAST(:start_value AS TIMESTAMPTZ)
              AND event_date <= CAST(:end_value AS TIMESTAMPTZ)
        """), {
            "status": status,
            "start_value": start_value,
            "end_value": end_value,
        }).scalar_one()


def get_db_keys(table, status, period_start, period_end):
    start_value = api_datetime(period_start)
    end_value = api_datetime(period_end, end_of_day=True)
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT {quote(OPERATION_KEY_COLUMN)}
            FROM {quote(table)}
            WHERE status = :status
              AND event_date >= CAST(:start_value AS TIMESTAMPTZ)
              AND event_date <= CAST(:end_value AS TIMESTAMPTZ)
              AND {quote(OPERATION_KEY_COLUMN)} IS NOT NULL
        """), {
            "status": status,
            "start_value": start_value,
            "end_value": end_value,
        })
        return {row[0] for row in rows}


def get_db_rows_by_keys(table, keys):
    keys = list(set(keys))
    if not keys:
        return []

    statement = text(f"""
        SELECT *
        FROM {quote(table)}
        WHERE {quote(OPERATION_KEY_COLUMN)} IN :keys
    """).bindparams(bindparam("keys", expanding=True))

    rows = []
    for start in range(0, len(keys), 500):
        chunk = keys[start:start + 500]
        with engine.connect() as conn:
            result = conn.execute(statement, {"keys": chunk}).mappings().all()
        rows.extend(dict(row) for row in result)
    return rows


def dataframe_for_operations(operations, seen_at):
    cleaned = [remove_nul(operation) for operation in operations if isinstance(operation, dict)]
    df = clean_operations(cleaned, seen_at)
    if df.empty:
        return df
    return df.drop_duplicates(subset=[OPERATION_KEY_COLUMN], keep="last")


def _upsert_dataframe_in_transaction(conn, table, df):
    if df.empty:
        return 0

    temp_table = f"tmp_operations_{uuid.uuid4().hex[:16]}"
    insert_columns = ", ".join(quote(column) for column in ALL_TARGET_COLUMNS)
    update_columns = [column for column in ALL_TARGET_COLUMNS if column != OPERATION_KEY_COLUMN]
    update_clause = ", ".join(
        f"{quote(column)} = EXCLUDED.{quote(column)}" for column in update_columns
    )

    conn.execute(text(f"""
        CREATE TEMPORARY TABLE {quote(temp_table)}
        (LIKE {quote(table)} INCLUDING DEFAULTS)
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
        INSERT INTO {quote(table)} ({insert_columns})
        SELECT {insert_columns}
        FROM {quote(temp_table)}
        ON CONFLICT ({quote(OPERATION_KEY_COLUMN)})
        DO UPDATE SET {update_clause}
    """))

    return len(df)


def _delete_keys_in_transaction(conn, table, keys):
    keys = list(set(keys))
    if not keys:
        return 0

    statement = text(f"""
        DELETE FROM {quote(table)}
        WHERE {quote(OPERATION_KEY_COLUMN)} IN :keys
    """).bindparams(bindparam("keys", expanding=True))

    deleted = 0
    for start in range(0, len(keys), 500):
        chunk = keys[start:start + 500]
        result = conn.execute(statement, {"keys": chunk})
        deleted += result.rowcount or 0
    return deleted


def route_operations_atomic(operations, run_id, seen_at=None):
    """
    Route les opérations vers la table correspondant au statut actuel.

    Chaque chunk est transactionnel : UPSERT dans la bonne table + suppression
    des anciennes copies dans les autres tables. Si le script plante ensuite,
    le prochain run peut rejouer les mêmes données sans risque (idempotence).
    """
    seen_at = seen_at or utc_now()
    latest = dedupe_latest_operations(operations)

    log(
        f"Routage BDD | brut reçu={len(operations)} | "
        f"uniques après dédoublonnage={len(latest)}"
    )

    grouped = {table: [] for table in ALL_CURRENT_TABLES}
    unknown = []

    for key, operation in latest.items():
        status = operation.get("status")
        target = TABLE_BY_STATUS.get(status)
        if not target:
            unknown.append((key, operation))
            continue
        grouped[target].append(operation)

    if unknown:
        for key, operation in unknown:
            write_problem(
                run_id,
                "UNKNOWN_STATUS",
                status=operation.get("status"),
                operation_key=key,
                reference=operation.get("reference"),
                contract_reference=get_contract_reference(operation),
                event_date=operation.get("eventDate"),
                source="API",
                details="Statut non géré. Checkpoint non validé.",
                payload=operation,
            )
        raise RuntimeError(f"{len(unknown)} opération(s) avec statut non géré.")

    for table, batch in grouped.items():
        if batch:
            log(f"  {table} : {len(batch)} opération(s)")

    upserted = 0

    for target_table, batch in grouped.items():
        if not batch:
            continue

        for start in range(0, len(batch), UPSERT_CHUNK_SIZE):
            chunk = batch[start:start + UPSERT_CHUNK_SIZE]
            df = dataframe_for_operations(chunk, seen_at)
            if df.empty:
                continue

            keys = df[OPERATION_KEY_COLUMN].dropna().tolist()

            with engine.begin() as conn:
                count = _upsert_dataframe_in_transaction(conn, target_table, df)

                deleted_elsewhere = 0
                for other_table in ALL_CURRENT_TABLES:
                    if other_table != target_table:
                        deleted_elsewhere += _delete_keys_in_transaction(
                            conn,
                            other_table,
                            keys,
                        )

            upserted += count
            log(
                f"  ✓ {target_table} | UPSERT={count} | "
                f"anciennes copies supprimées={deleted_elsewhere} | "
                f"progression={min(start + len(chunk), len(batch))}/{len(batch)}"
            )

    log(f"✓ Routage BDD terminé | total UPSERT={upserted}")
    return upserted


def archive_and_delete_extra(table, row, reason):
    key = row.get(OPERATION_KEY_COLUMN)
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {quote(ARCHIVE_TABLE)}
            (operation_key, source_table, reason, row_data)
            VALUES (:operation_key, :source_table, :reason, CAST(:row_data AS JSONB))
        """), {
            "operation_key": key,
            "source_table": table,
            "reason": reason,
            "row_data": safe_json(row),
        })
        _delete_keys_in_transaction(conn, table, [key])

# ============================================================
# MISE A JOUR INCREMENTALE FIABLE
# ============================================================


def run_incremental_sync():
    """
    DAILY fiable et simple :

      1. lit le dernier checkpoint fiable ;
      2. recule de 15 minutes pour créer un overlap de sécurité ;
      3. effectue UNE seule passe complète sur l'API ;
      4. dédoublonne par operation_key en gardant la version la plus récente ;
      5. route et UPSERT dans les tables current ;
      6. avance le checkpoint à l'heure de DÉBUT du run uniquement si
         récupération API + écriture PostgreSQL se sont terminées correctement.

    Si le run échoue, le checkpoint reste inchangé et la période sera relue.
    """
    run_id, run_started_at = start_run("daily")
    received = 0
    upserted = 0

    try:
        log("Lecture du checkpoint PostgreSQL...")
        checkpoint = get_reliable_checkpoint()

        if checkpoint is None:
            raise RuntimeError(
                "Aucun checkpoint disponible dans operations_reliable_sync_state "
                "pour pipeline_name='operations_all'."
            )

        if checkpoint > run_started_at + timedelta(minutes=5):
            raise RuntimeError(
                f"Checkpoint incohérent dans le futur : {checkpoint.isoformat()}"
            )

        log(f"✓ Checkpoint trouvé : {checkpoint.isoformat()}")

        since = checkpoint - DELTA_OVERLAP
        log(f"Marge de sécurité : {DELTA_OVERLAP}")
        log(f"→ Intent since={api_iso_datetime(since)}")
        log(
            f"Point de coupure du run : {run_started_at.isoformat()} | "
            "le prochain DAILY relira 15 minutes avant ce point."
        )

        base_params = build_list_params(
            since=api_iso_datetime(since)
        )

        operations, received, max_total_observed = fetch_daily_delta_once(
            base_params,
            run_id,
        )

        log(
            f"Extraction DAILY terminée | brut reçu={received} | "
            f"opérations uniques={len(operations)} | "
            f"max total API observé={max_total_observed}"
        )

        upserted = route_operations_atomic(
            operations,
            run_id,
            seen_at=run_started_at,
        )

        save_checkpoint(run_started_at, run_started_at)
        log(f"✓ Nouveau checkpoint : {run_started_at.isoformat()}")

        finish_run(
            run_id,
            True,
            received=received,
            upserted=upserted,
            details=(
                f"DAILY 1 passe réussi. "
                f"Checkpoint avancé à {run_started_at.isoformat()}. "
                f"max_total_api={max_total_observed}"
            ),
        )

        log(
            f"✅ DAILY terminé | brut reçu={received} | "
            f"uniques={len(operations)} | UPSERT={upserted} | "
            f"checkpoint={run_started_at.isoformat()}"
        )

        return {
            "run_id": run_id,
            "received": received,
            "unique": len(operations),
            "upserted": upserted,
            "checkpoint": run_started_at,
            "max_total_api": max_total_observed,
        }

    except KeyboardInterrupt:
        finish_run(
            run_id,
            False,
            received=received,
            upserted=upserted,
            details="Interruption utilisateur. Checkpoint inchangé.",
        )
        log("⛔ Interruption utilisateur | checkpoint inchangé.")
        raise

    except Exception as error:
        finish_run(
            run_id,
            False,
            received=received,
            upserted=upserted,
            details=(
                f"{error.__class__.__name__}: {error}. "
                "Checkpoint inchangé."
            ),
        )
        log(f"❌ DAILY en échec : {error}")
        log("✓ Sécurité : le checkpoint n'a pas avancé.")
        raise


# ============================================================
# GESTION DES EXTRA_IN_DB
# ============================================================


def get_db_rows_by_references(references):
    """
    Recherche EN LOT les références dans toutes les tables current.

    Cela évite une requête PostgreSQL par EXTRA.
    """
    references = sorted({
        str(reference)
        for reference in references
        if reference is not None and str(reference).strip()
    })

    if not references:
        return {}

    by_reference = {}

    for table in ALL_CURRENT_TABLES:
        statement = text(f"""
            SELECT *
            FROM {quote(table)}
            WHERE {quote('reference')} IN :references
        """).bindparams(bindparam("references", expanding=True))

        for start in range(0, len(references), 500):
            chunk = references[start:start + 500]

            with engine.connect() as conn:
                rows = conn.execute(
                    statement,
                    {"references": chunk},
                ).mappings().all()

            for row in rows:
                item = dict(row)
                item["_source_table"] = table
                reference = item.get("reference")

                if reference is not None:
                    by_reference.setdefault(str(reference), []).append(item)

    return by_reference


def search_operation_by_reference_in_intent(reference, cache=None):
    """
    Recherche une intervention dans Intent par référence.

    Endpoint validé dans Postman :
      GET /operations/v2/operations?reference=<REFERENCE>

    FOUND       : au moins une ligne porte exactement la référence.
    NOT_FOUND   : Intent retourne total=0.
    UNRESOLVED  : réponse positive mais aucune référence exacte.
    ERROR       : l'appel API a échoué.

    ERROR et UNRESOLVED ne déclenchent jamais de suppression.
    """
    if not reference:
        return "UNRESOLVED", None, "Référence vide."

    reference = str(reference)

    if cache is not None and reference in cache:
        return cache[reference]

    params = {
        "page": 1,
        "perPage": PER_PAGE,
        "reference": reference,
    }

    try:
        data = call_intent_api(
            path="/operations/v2/operations",
            params=params,
        )
    except Exception as error:
        result = (
            "ERROR",
            None,
            f"{error.__class__.__name__}: {error}",
        )
        if cache is not None:
            cache[reference] = result
        return result

    operations = list(get_operations_from_response(data))

    exact_matches = [
        operation
        for operation in operations
        if isinstance(operation, dict)
        and str(operation.get("reference")) == reference
    ]

    if exact_matches:
        candidate = choose_latest_operation(exact_matches)
        result = (
            "FOUND",
            candidate,
            f"{len(exact_matches)} résultat(s) exact(s) trouvé(s).",
        )
        if cache is not None:
            cache[reference] = result
        return result

    try:
        total = int(data.get("total", 0) or 0)
    except Exception:
        total = None

    if total == 0:
        result = (
            "NOT_FOUND",
            None,
            "Intent retourne total=0 pour la recherche exacte par référence.",
        )
        if cache is not None:
            cache[reference] = result
        return result

    result = (
        "UNRESOLVED",
        None,
        (
            f"Intent retourne total={total}, mais aucune ligne ne porte "
            f"exactement la référence {reference}."
        ),
    )

    if cache is not None:
        cache[reference] = result

    return result


def archive_extra_with_log(
    run_id,
    source_table,
    row,
    period_start,
    period_end,
    *,
    problem_type,
    reason,
    details,
    payload=None,
):
    """
    Archive d'abord la ligne complète, puis la retire de la table current.
    """
    archive_and_delete_extra(
        source_table,
        row,
        reason=reason,
    )

    write_problem(
        run_id,
        problem_type,
        status=row.get("status"),
        period_start=period_start,
        period_end=period_end,
        operation_key=row.get(OPERATION_KEY_COLUMN),
        reference=row.get("reference"),
        contract_reference=row.get("contract_reference"),
        event_date=row.get("event_date"),
        source=source_table,
        details=details,
        payload=payload if payload is not None else row,
    )


def keep_extra_unresolved(
    run_id,
    source_table,
    row,
    period_start,
    period_end,
    details,
):
    """
    Cas non concluant : aucune suppression.
    """
    write_problem(
        run_id,
        "EXTRA_UNRESOLVED",
        status=row.get("status"),
        period_start=period_start,
        period_end=period_end,
        operation_key=row.get(OPERATION_KEY_COLUMN),
        reference=row.get("reference"),
        contract_reference=row.get("contract_reference"),
        event_date=row.get("event_date"),
        source=source_table,
        details=details,
        payload=row,
    )

    log(
        f"⚠️ EXTRA conservée | "
        f"reference={row.get('reference')} | "
        f"contract={row.get('contract_reference')} | "
        f"raison={details}"
    )

    return "UNRESOLVED"


def operation_belongs_to_period(
    operation,
    status,
    period_start,
    period_end,
):
    """
    Vérifie qu'une opération confirmée individuellement par Intent
    appartient bien au statut + mois actuellement certifiés.

    C'est important lorsqu'une EXTRA a changé de statut ou de eventDate :
    dans ce cas elle doit être routée, mais elle ne doit plus être comptée
    dans le référentiel du mois/statut en cours.
    """
    if not isinstance(operation, dict):
        return False

    if operation.get("status") != status:
        return False

    event_date = parse_api_datetime(
        operation.get("eventDate")
    )

    if event_date == datetime.min.replace(tzinfo=timezone.utc):
        return False

    period_start_dt = datetime.combine(
        period_start,
        datetime.min.time(),
        tzinfo=timezone.utc,
    )

    period_end_exclusive = datetime.combine(
        period_end + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )

    return (
        period_start_dt
        <= event_date
        < period_end_exclusive
    )


def resolve_extra_row(
    run_id,
    source_table,
    row,
    period_start,
    period_end,
    db_reference_index,
    intent_reference_cache,
    verify_with_intent=False,
):
    """
    Résout une EXTRA sans supprimer à l'aveugle.

    RECONCILE rapide :
      - si une autre version unique existe déjà en BDD, elle peut être utilisée
        directement comme avant.

    CERTIFY :
      - même si une autre version existe déjà en BDD, on demande quand même
        confirmation à Intent ;
      - seule une réponse Intent FOUND / NOT_FOUND permet de conclure ;
      - ERROR / UNRESOLVED bloque la certification.

    Retourne un dictionnaire contenant :
      state
      confirmed_operation
      confirmed_key
    """
    old_key = row.get(OPERATION_KEY_COLUMN)
    reference = row.get("reference")
    old_contract = row.get("contract_reference")
    old_status = row.get("status")

    if not reference:
        keep_extra_unresolved(
            run_id,
            source_table,
            row,
            period_start,
            period_end,
            "EXTRA sans référence exploitable.",
        )

        return {
            "state": "UNRESOLVED",
            "confirmed_operation": None,
            "confirmed_key": None,
        }

    reference = str(reference)

    # ========================================================
    # 1. Recherche PostgreSQL
    # ========================================================

    db_matches = [
        candidate
        for candidate in db_reference_index.get(reference, [])
        if candidate.get(OPERATION_KEY_COLUMN) != old_key
    ]

    if len(db_matches) == 1:
        candidate = db_matches[0]

        new_key = candidate.get(OPERATION_KEY_COLUMN)
        new_contract = candidate.get("contract_reference")
        new_status = candidate.get("status")
        new_table = candidate.get("_source_table")

        if not verify_with_intent:
            log(
                f"↪ EXTRA {reference} retrouvée en BDD | "
                f"contrat {old_contract} -> {new_contract} | "
                f"statut {old_status} -> {new_status}"
            )

            archive_extra_with_log(
                run_id,
                source_table,
                row,
                period_start,
                period_end,
                problem_type="EXTRA_REASSIGNED",
                reason=(
                    "Même référence déjà présente dans PostgreSQL sous une autre "
                    f"operation_key. ancienne_key={old_key}; nouvelle_key={new_key}; "
                    f"ancienne_table={source_table}; nouvelle_table={new_table}; "
                    f"ancien_contrat={old_contract}; nouveau_contrat={new_contract}; "
                    f"ancien_statut={old_status}; nouveau_statut={new_status}"
                ),
                details=(
                    "Même référence déjà présente en BDD sous une autre version. "
                    f"ancienne_key={old_key}; nouvelle_key={new_key}; "
                    f"contrat={old_contract}->{new_contract}; "
                    f"statut={old_status}->{new_status}."
                ),
                payload=candidate,
            )

            return {
                "state": "REASSIGNED_DB",
                "confirmed_operation": None,
                "confirmed_key": None,
            }

        log(
            f"ℹ️ CERTIFY | EXTRA {reference} retrouvée en BDD sous une autre "
            "version, mais validation Intent obligatoire avant certification."
        )

    elif len(db_matches) > 1:
        log(
            f"ℹ️ EXTRA {reference} | "
            f"{len(db_matches)} versions BDD trouvées. "
            "Vérification Intent nécessaire."
        )

    # ========================================================
    # 2. Recherche Intent exacte par référence
    # ========================================================

    log(
        f"→ Intent recherche reference={reference} | "
        f"ancien contrat={old_contract}"
    )

    state, candidate, details = search_operation_by_reference_in_intent(
        reference,
        cache=intent_reference_cache,
    )

    if state == "FOUND":
        new_key = build_operation_key(candidate)
        new_contract = get_contract_reference(candidate)
        new_status = candidate.get("status")

        log(
            f"← Intent FOUND {reference} | "
            f"contrat={new_contract} | statut={new_status}"
        )

        # La version Intent confirmée devient la référence de vérité.
        route_operations_atomic(
            [candidate],
            run_id,
            seen_at=utc_now(),
        )

        if new_key == old_key:
            write_problem(
                run_id,
                "EXTRA_REFRESHED",
                status=new_status,
                period_start=period_start,
                period_end=period_end,
                operation_key=old_key,
                reference=reference,
                contract_reference=old_contract,
                event_date=candidate.get("eventDate"),
                source=source_table,
                details=(
                    "Intent confirme que la même operation_key existe toujours. "
                    "La ligne a été rafraîchie et devient une clé confirmée "
                    "pour le contrôle final."
                ),
                payload=candidate,
            )

            return {
                "state": "REFRESHED",
                "confirmed_operation": candidate,
                "confirmed_key": new_key,
            }

        archive_extra_with_log(
            run_id,
            source_table,
            row,
            period_start,
            period_end,
            problem_type="EXTRA_REASSIGNED",
            reason=(
                "Intent retrouve la même référence sous une nouvelle operation_key. "
                f"ancienne_key={old_key}; nouvelle_key={new_key}; "
                f"ancien_contrat={old_contract}; nouveau_contrat={new_contract}; "
                f"ancien_statut={old_status}; nouveau_statut={new_status}"
            ),
            details=(
                "Intent retrouve la même référence sous une nouvelle version. "
                f"ancienne_key={old_key}; nouvelle_key={new_key}; "
                f"contrat={old_contract}->{new_contract}; "
                f"statut={old_status}->{new_status}."
            ),
            payload=candidate,
        )

        return {
            "state": "REASSIGNED_API",
            "confirmed_operation": candidate,
            "confirmed_key": new_key,
        }

    if state == "NOT_FOUND":
        log(
            f"← Intent NOT_FOUND {reference} | "
            "archive de l'ancienne ligne"
        )

        archive_extra_with_log(
            run_id,
            source_table,
            row,
            period_start,
            period_end,
            problem_type="EXTRA_ARCHIVED_NOT_FOUND",
            reason=(
                "Recherche Intent exacte par référence : total=0. "
                f"reference={reference}; ancien_contrat={old_contract}"
            ),
            details=(
                "Intent retourne total=0 pour cette référence. "
                "L'ancienne ligne a été archivée puis retirée de la table current."
            ),
            payload=row,
        )

        return {
            "state": "ARCHIVED",
            "confirmed_operation": None,
            "confirmed_key": None,
        }

    keep_extra_unresolved(
        run_id,
        source_table,
        row,
        period_start,
        period_end,
        f"Recherche Intent non concluante : {details}",
    )

    return {
        "state": "UNRESOLVED",
        "confirmed_operation": None,
        "confirmed_key": None,
    }


# ============================================================
# RECONCILIATION MENSUELLE
# ============================================================


def reconcile_month(run_id, status, month_start, month_end, strict=False):
    table = TABLE_BY_STATUS[status]

    api_total = get_api_total(
        status,
        month_start,
        month_end,
    )

    db_count = get_db_count(
        table,
        status,
        month_start,
        month_end,
    )

    log(
        f"{status.upper()} {month_start:%Y-%m} | "
        f"API brut={api_total} | BDD={db_count}"
    )

    # RECONCILE rapide :
    # si les volumes sont identiques, on ne télécharge pas tout le mois.
    # CERTIFY, lui, compare toujours les clés.
    if not strict and api_total == db_count:
        return {
            "checked": True,
            "certified": False,
            "skipped": True,
        }

    base_params = build_list_params(
        status=status,
        **{
            "from": api_datetime(month_start),
            "to": api_datetime(
                month_end,
                end_of_day=True,
            ),
        },
    )

    operations, api_total_observed = (
        fetch_reconciliation_set_once(
            base_params,
            run_id,
            context=(
                f"{status} "
                f"{month_start:%Y-%m}"
            ),
        )
    )

    api_by_key = dedupe_latest_operations(
        operations
    )

    # Clés obtenues dans la pagination mensuelle.
    api_keys = set(
        api_by_key
    )

    db_keys_before = get_db_keys(
        table,
        status,
        month_start,
        month_end,
    )

    missing = (
        api_keys
        - db_keys_before
    )

    extras = (
        db_keys_before
        - api_keys
    )

    log(
        f"  Comparaison exacte | "
        f"API uniques pagination={len(api_keys)} | "
        f"BDD uniques={len(db_keys_before)} | "
        f"manquantes={len(missing)} | "
        f"extras={len(extras)}"
    )

    # ========================================================
    # 1. MISSING_IN_DB
    # ========================================================

    # Présente dans Intent, absente de PostgreSQL :
    # réparation automatique, car la présence API est une preuve positive.
    for key in sorted(missing):
        operation = api_by_key[key]

        write_problem(
            run_id,
            "MISSING_IN_DB",
            status=status,
            period_start=month_start,
            period_end=month_end,
            operation_key=key,
            reference=operation.get("reference"),
            contract_reference=get_contract_reference(
                operation
            ),
            event_date=operation.get("eventDate"),
            source="API",
            details=(
                "Présente dans Intent, absente de PostgreSQL. "
                "Réparation automatique par UPSERT."
            ),
            payload=operation,
        )

    if missing:
        route_operations_atomic(
            [
                api_by_key[key]
                for key in missing
            ],
            run_id,
            seen_at=utc_now(),
        )

    # ========================================================
    # 2. EXTRA_IN_DB
    # ========================================================

    extra_rows = get_db_rows_by_keys(
        table,
        extras,
    )

    # Recherche PostgreSQL EN LOT pour toutes les références EXTRA du mois.
    db_reference_index = get_db_rows_by_references(
        row.get("reference")
        for row in extra_rows
    )

    # Une même référence n'est jamais redemandée deux fois à Intent
    # pendant le traitement du mois.
    intent_reference_cache = {}

    # Clés confirmées individuellement par Intent mais absentes
    # de la pagination mensuelle à cause des doublons / pagination vivante.
    confirmed_extra_keys = set()

    # Une EXTRA non résolue bloque toujours la certification.
    unresolved_extra_keys = set()

    for row in extra_rows:
        old_key = row.get(
            OPERATION_KEY_COLUMN
        )

        write_problem(
            run_id,
            "EXTRA_IN_DB",
            status=status,
            period_start=month_start,
            period_end=month_end,
            operation_key=old_key,
            reference=row.get("reference"),
            contract_reference=row.get(
                "contract_reference"
            ),
            event_date=row.get("event_date"),
            source=table,
            details=(
                "Présente dans PostgreSQL mais operation_key absente du jeu API "
                "mensuel. Résolution par référence : BDD puis Intent. "
                "En mode CERTIFY, une confirmation Intent est obligatoire."
            ),
            payload=row,
        )

        resolution = resolve_extra_row(
            run_id,
            table,
            row,
            month_start,
            month_end,
            db_reference_index,
            intent_reference_cache,
            verify_with_intent=strict,
        )

        resolution_state = resolution.get(
            "state"
        )

        if resolution_state == "UNRESOLVED":
            if old_key:
                unresolved_extra_keys.add(
                    old_key
                )
            continue

        confirmed_operation = resolution.get(
            "confirmed_operation"
        )

        confirmed_key = resolution.get(
            "confirmed_key"
        )

        # Si Intent a confirmé individuellement une opération,
        # elle complète le jeu mensuel initial UNIQUEMENT si elle appartient
        # toujours au statut + mois que l'on est en train de certifier.
        if (
            confirmed_operation
            and confirmed_key
            and operation_belongs_to_period(
                confirmed_operation,
                status,
                month_start,
                month_end,
            )
        ):
            confirmed_extra_keys.add(
                confirmed_key
            )

    # ========================================================
    # 3. REFERENTIEL INTENT EFFECTIF
    # ========================================================

    # La pagination mensuelle peut contenir des doublons et donc omettre
    # certaines operation_key.
    #
    # Une opération retrouvée par recherche exacte de référence est une preuve
    # Intent positive. Elle complète donc le référentiel utilisé pour le
    # contrôle final.
    effective_api_keys = (
        api_keys
        | confirmed_extra_keys
    )

    # ========================================================
    # 4. RECONTROLE FINAL APRES CORRECTIONS
    # ========================================================

    db_keys_after = get_db_keys(
        table,
        status,
        month_start,
        month_end,
    )

    missing_after = (
        effective_api_keys
        - db_keys_after
    )

    extras_after = (
        db_keys_after
        - effective_api_keys
    )

    # Si une ligne UNRESOLVED a disparu à la suite d'un autre déplacement,
    # elle ne doit plus bloquer. On ne conserve que les unresolved encore
    # réellement présents dans le périmètre courant.
    unresolved_after = (
        unresolved_extra_keys
        & db_keys_after
    )

    certified = (
        not missing_after
        and not extras_after
        and not unresolved_after
    )

    # ========================================================
    # 5. ENREGISTREMENT ETAT DE CERTIFICATION
    # ========================================================

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {quote(RECON_TABLE)}
            (
                status,
                period_start,
                period_end,
                certified,
                api_total,
                api_unique,
                db_unique,
                missing_count,
                extra_count,
                checked_at
            )
            VALUES
            (
                :status,
                :period_start,
                :period_end,
                :certified,
                :api_total,
                :api_unique,
                :db_unique,
                :missing_count,
                :extra_count,
                NOW()
            )
            ON CONFLICT (
                status,
                period_start,
                period_end
            )
            DO UPDATE SET
                certified = EXCLUDED.certified,
                api_total = EXCLUDED.api_total,
                api_unique = EXCLUDED.api_unique,
                db_unique = EXCLUDED.db_unique,
                missing_count = EXCLUDED.missing_count,
                extra_count = EXCLUDED.extra_count,
                checked_at = NOW()
        """), {
            "status": status,
            "period_start": month_start,
            "period_end": month_end,
            "certified": certified,

            # api_total reste le total brut observé pendant la pagination.
            "api_total": api_total_observed,

            # api_unique représente désormais le référentiel Intent effectif :
            # pagination dédoublonnée + confirmations exactes individuelles.
            "api_unique": len(
                effective_api_keys
            ),

            "db_unique": len(
                db_keys_after
            ),
            "missing_count": len(
                missing_after
            ),
            "extra_count": len(
                extras_after
            ),
        })

    log(
        f"  → Après traitement | "
        f"API pagination={len(api_keys)} | "
        f"confirmées individuellement={len(confirmed_extra_keys)} | "
        f"API effectives={len(effective_api_keys)} | "
        f"BDD uniques={len(db_keys_after)} | "
        f"manquantes restantes={len(missing_after)} | "
        f"extras restantes={len(extras_after)} | "
        f"non résolues={len(unresolved_after)} | "
        f"certifié={certified}"
    )

    return {
        "checked": True,
        "certified": certified,
        "missing": len(missing),
        "extras": len(extras),
        "confirmed_extras": len(
            confirmed_extra_keys
        ),
        "unresolved": len(
            unresolved_after
        ),
        "missing_after": len(
            missing_after
        ),
        "extras_after": len(
            extras_after
        ),
        "api_unique_effective": len(
            effective_api_keys
        ),
    }


def month_already_certified(status, month_start, month_end):
    with engine.connect() as conn:
        row = conn.execute(text(f"""
            SELECT certified
            FROM {quote(RECON_TABLE)}
            WHERE status = :status
              AND period_start = :period_start
              AND period_end = :period_end
        """), {
            "status": status,
            "period_start": month_start,
            "period_end": month_end,
        }).mappings().fetchone()
    return bool(row and row["certified"])


def run_reconciliation(strict=False, resume=True):
    mode = "certify" if strict else "reconcile"
    run_id, started_at = start_run(mode)
    checked = certified = errors = 0

    try:
        for status in STATUSES:
            end_date = (
                date.today() + timedelta(days=ACTIVE_END_OFFSET_DAYS)
                if status in {"open", "pending", "hold"}
                else date.today()
            )

            for month_start, month_end in iter_months(HISTORY_START, end_date):
                # En mode certification, les mois passés déjà certifiés peuvent être sautés.
                # Le mois courant/futur est toujours recontrôlé car il peut évoluer.
                if (
                    strict
                    and resume
                    and month_end < date.today()
                    and month_already_certified(status, month_start, month_end)
                ):
                    continue

                try:
                    result = reconcile_month(
                        run_id,
                        status,
                        month_start,
                        month_end,
                        strict=strict,
                    )
                    checked += 1
                    certified += int(bool(result.get("certified")))
                except Exception as error:
                    errors += 1
                    write_problem(
                        run_id,
                        "RECONCILIATION_ERROR",
                        status=status,
                        period_start=month_start,
                        period_end=month_end,
                        source="SCRIPT",
                        details=f"{error.__class__.__name__}: {error}",
                    )
                    log(f"❌ {status} {month_start:%Y-%m}: {error}")
                    if strict:
                        # Certification = on n'ignore pas silencieusement une erreur.
                        raise

        success = errors == 0
        finish_run(
            run_id,
            success,
            details=f"checked={checked}; certified={certified}; errors={errors}",
        )
        return {"checked": checked, "certified": certified, "errors": errors}

    except Exception as error:
        finish_run(
            run_id,
            False,
            details=f"Interrompu: {error.__class__.__name__}: {error}",
        )
        raise

# ============================================================
# ORCHESTRATION
# ============================================================


def run_daily():
    """Mise à jour quotidienne en une seule passe API, avec overlap et checkpoint."""
    return run_incremental_sync()


def run_fast_reconcile():
    """
    Rapide : compare les volumes mois par mois et ne télécharge en une seule
    passe que les mois avec écart. Les écarts sont comparés par operation_key.
    """
    return run_reconciliation(strict=False, resume=False)


def run_full_certification():
    """
    Contrôle exhaustif de l'historique par operation_key, avec une seule passe
    complète par statut et par mois.

    IMPORTANT : la certification ne modifie PAS le checkpoint du DAILY.
    Le checkpoint de mise à jour est géré uniquement par le système DAILY.
    """
    return run_reconciliation(strict=True, resume=True)


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "daily").lower()

    log("============================================================")
    log("PIPELINE OPERATIONS INTENT")
    log("============================================================")
    log(f"Mode demandé : {mode}")
    log(f"Débit API : {REQUESTS_PER_MINUTE} requêtes/minute")
    log(f"Fichier de log : {PROBLEM_FILE}")
    log("Initialisation des tables techniques et index...")

    init_support_tables()
    log("✓ Initialisation terminée")

    if mode == "daily":
        log("Stratégie DAILY : 1 passe API + dédoublonnage + UPSERT + checkpoint.")
        run_daily()
    elif mode == "reconcile":
        log("Stratégie RECONCILE : 1 passe si écart ; EXTRA résolues par référence, BDD puis Intent.")
        run_fast_reconcile()
    elif mode == "certify":
        log("Stratégie CERTIFY : 1 passe complète par statut/mois + comparaison exacte des operation_key.")
        run_full_certification()
    else:
        raise SystemExit("Mode attendu: daily | reconcile | certify")



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("⛔ Programme arrêté par Ctrl+C.")
        raise SystemExit(130)

