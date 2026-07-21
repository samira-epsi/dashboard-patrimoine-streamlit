from sqlalchemy import text


def upsert_dataframe(
    df,
    table_name,
    key_columns,
    engine
):

    if df.empty:
        print("DataFrame vide")
        return

    temp_table = f"{table_name}_temp"

    print(
        f"Création table temporaire : {temp_table}"
    )

    df.to_sql(
        temp_table,
        engine,
        if_exists="replace",
        index=False
    )

    columns = df.columns.tolist()

    update_columns = [
        col
        for col in columns
        if col not in key_columns
    ]

    insert_columns = ", ".join(
        [f'"{col}"' for col in columns]
    )

    select_columns = ", ".join(
        [f't."{col}"' for col in columns]
    )

    conflict_columns = ", ".join(
        [f'"{col}"' for col in key_columns]
    )

    update_set = ", ".join(
        [
            f'"{col}" = EXCLUDED."{col}"'
            for col in update_columns
        ]
    )

    sql = f"""
        INSERT INTO {table_name}
        ({insert_columns})

        SELECT
        {select_columns}
        FROM {temp_table} t

        ON CONFLICT ({conflict_columns})
        DO UPDATE SET
        {update_set}
    """

    with engine.begin() as conn:

        conn.execute(
            text(sql)
        )

        conn.execute(
            text(
                f'DROP TABLE IF EXISTS "{temp_table}"'
            )
        )

    print(
        f"Upsert terminé : {len(df)} lignes"
    )