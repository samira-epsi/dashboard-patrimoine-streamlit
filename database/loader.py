from datetime import datetime, UTC

import pandas as pd
from sqlalchemy import inspect, text


def log_etl_run(
    table_name,
    row_count,
    engine
):
    """
    Enregistre chaque chargement ETL dans la table etl_run_log.
    """

    log_df = pd.DataFrame(
        [
            {
                "run_date": datetime.now(UTC),
                "table_name": table_name,
                "row_count": row_count
            }
        ]
    )

    log_df.to_sql(
        name="etl_run_log",
        con=engine,
        if_exists="append",
        index=False
    )


def load_snapshot(
    df,
    table_name,
    engine
):
    """
    Ajoute les données à une table historique sans supprimer
    les anciens snapshots.
    """

    if df is None:
        raise ValueError(
            f"Le DataFrame envoyé à {table_name} est None."
        )

    if df.empty:
        print(
            f"⚠️ {table_name} : DataFrame vide, "
            "aucune donnée ajoutée."
        )
        return

    df_to_load = df.copy()

    df_to_load["snapshot_date"] = datetime.now(UTC)

    df_to_load.to_sql(
        name=table_name,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi"
    )

    log_etl_run(
        table_name=table_name,
        row_count=len(df_to_load),
        engine=engine
    )

    print(
        f"[OK] {len(df_to_load):,} lignes ajoutées dans "
        f"{table_name}"
    )


def load_current(
    df,
    table_name,
    engine,
    schema="public"
):
    """
    Remplace les données d'une table current sans supprimer
    la table elle-même.

    La table est vidée avec TRUNCATE puis les nouvelles données
    sont insérées avec append.

    Cela conserve les vues PostgreSQL qui dépendent de la table.
    """

    if df is None:
        raise ValueError(
            f"Le DataFrame envoyé à {table_name} est None."
        )

    if df.empty:
        print(
            f"⚠️ {table_name} : DataFrame vide, "
            "chargement annulé pour éviter de vider la table."
        )
        return

    df_to_load = df.copy()

    inspector = inspect(engine)

    table_exists = inspector.has_table(
        table_name=table_name,
        schema=schema
    )

    if not table_exists:
        # Premier chargement : la table n'existe pas encore.
        df_to_load.to_sql(
            name=table_name,
            con=engine,
            schema=schema,
            if_exists="fail",
            index=False,
            chunksize=5000,
            method="multi"
        )

    else:
        # La transaction garantit que le TRUNCATE et l'insertion
        # sont validés ensemble.
        with engine.begin() as connection:
            connection.execute(
                text(
                    f'TRUNCATE TABLE "{schema}"."{table_name}"'
                )
            )

            df_to_load.to_sql(
                name=table_name,
                con=connection,
                schema=schema,
                if_exists="append",
                index=False,
                chunksize=5000,
                method="multi"
            )

    log_etl_run(
        table_name=table_name,
        row_count=len(df_to_load),
        engine=engine
    )

    print(
        f"✅ {len(df_to_load):,} lignes chargées dans "
        f"{schema}.{table_name}"
    )