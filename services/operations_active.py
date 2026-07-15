import pandas as pd
from api.client import get
from sqlalchemy import create_engine, text, inspect
from config import DB_URL
import time

engine = create_engine(DB_URL)

ACTIVE_STATUS = ["open", "pending", "hold"]
BATCH_SIZE = 500


# ─── PROGRESSION ───────────────────────────────────────────

def init_progression_table():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_progression (
                status      VARCHAR(50) PRIMARY KEY,
                last_page   INTEGER NOT NULL,
                done        BOOLEAN DEFAULT FALSE
            )
        """))


def get_progression(status):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT last_page, done
            FROM pipeline_progression
            WHERE status = :status
        """), {"status": status}).fetchone()
    return result


def save_progression(status, last_page, done=False):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO pipeline_progression (status, last_page, done)
            VALUES (:status, :last_page, :done)
            ON CONFLICT (status)
            DO UPDATE SET
                last_page = EXCLUDED.last_page,
                done      = EXCLUDED.done
        """), {"status": status, "last_page": last_page, "done": done})


def clear_progression():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pipeline_progression"))


# ─── NETTOYAGE ─────────────────────────────────────────────

def clean_operations(df):
    columns = {
        "reference":                                    "reference",
        "type":                                         "type",
        "status":                                       "status",
        "creationDate":                                 "creation_date",
        "lastUpdateDate":                               "last_update_date",
        "firstEventDate":                               "first_event_date",
        "eventDate":                                    "event_date",
        "logDate":                                      "log_date",
        "event":                                        "event",
        "workType":                                     "work_type",
        "eventHistory":                                 "event_history",
        "criticalLevel":                                "critical_level",
        "description":                                  "description",
        "technicalReason":                              "technical_reason",
        "issuer.entity.id":                             "provider_id",
        "issuer.entity.label":                          "provider_name",
        "contract.reference":                           "contract_reference",
        "contract.label":                               "contract_label",
        "contract.topic":                               "contract_topic",
        "service.code":                                 "service_code",
        "service.label":                                "service_label",
        "service.description":                          "service_description",
        "service.originalCode":                         "service_original_code",
        "service.sla.maxTimeToIntervention.value":      "sla_intervention_value",
        "service.sla.maxTimeToIntervention.unit":       "sla_intervention_unit",
        "service.sla.maxTimeToRecovery.value":          "sla_recovery_value",
        "service.sla.maxTimeToRecovery.unit":           "sla_recovery_unit",
        "location.assetReference":                      "asset_reference",
        "location.address.way":                         "address",
        "location.address.city":                        "city",
        "location.address.zip":                         "zip_code",
        "location.address.country":                     "country",
        "location.owner.id":                            "owner_id",
        "location.owner.label":                         "owner_name",
        "responseTime":                                 "response_time",
        "resolutionDuration":                           "resolution_duration",
        "equipmentStatus":                              "equipment_status",
        "parentReference":                              "parent_reference",
    }

    existing_columns = {k: v for k, v in columns.items() if k in df.columns}
    df = df[list(existing_columns.keys())].rename(columns=existing_columns)
    return df


# ─── SAUVEGARDE ────────────────────────────────────────────

def save_batch(batch):
    if not batch:
        return

    df = pd.json_normalize(batch)
    df = clean_operations(df)

    if df.empty:
        return

    inspector = inspect(engine)
    table_exists = inspector.has_table("operations_active_current")

    if not table_exists:
        df.to_sql("operations_active_current", engine, if_exists="replace", index=False)
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_operations_reference
                ON operations_active_current(reference)
            """))
        print(f"Table créée : {len(df)} lignes")
        return

    temp_table = "tmp_operations"
    df.to_sql(temp_table, engine, if_exists="replace", index=False)

    columns = list(df.columns)
    update_columns = [col for col in columns if col != "reference"]
    insert_columns = ", ".join(columns)
    update_clause = ", ".join([f"{col}=EXCLUDED.{col}" for col in update_columns])

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO operations_active_current ({insert_columns})
            SELECT {insert_columns} FROM {temp_table}
            ON CONFLICT (reference)
            DO UPDATE SET {update_clause}
        """))
        conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))

    print(f"UPSERT : {len(df)} lignes")


# ─── CHARGEMENT PRINCIPAL ───────────────────────────────────

def get_active_operations():

    init_progression_table()

    batch = []
    total_loaded = 0

    for status in ACTIVE_STATUS:

        progression = get_progression(status)

        # Statut déjà terminé lors d'une exécution précédente
        if progression and progression.done:
            print(f"\n===== {status.upper()} — déjà chargé, ignoré =====")
            continue

        # Reprise sur crash : on repart de la dernière page sauvegardée
        start_page = 1
        if progression and not progression.done:
            start_page = progression.last_page + 1
            print(f"\n===== {status.upper()} — reprise page {start_page} =====")
        else:
            print(f"\n===== {status.upper()} =====")

        page = start_page

        while True:

            data = get(
                "/operations/v2/operations",
                params={"status": status, "page": page, "perPage": 100}
            )

            operations = data.get("_embedded", {}).get("operations", [])

            if not operations:
                # Statut terminé
                save_progression(status, page, done=True)
                break

            batch.extend(operations)
            total_loaded += len(operations)

            print(f"{status} | page {page} | {total_loaded} lignes")

            if len(batch) >= BATCH_SIZE:
                save_batch(batch)
                save_progression(status, page)
                batch = []

            time.sleep(0.2)
            page += 1

    # Dernier batch résiduel
    if batch:
        save_batch(batch)

    # Tout est terminé : on nettoie la progression
    clear_progression()

    print(f"\nTotal chargé : {total_loaded}")