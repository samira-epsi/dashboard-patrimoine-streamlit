import json
import pandas as pd

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

from api.client import get

OWNER_ID = "5a2942cfd207720cf70b6796"

MAX_WORKERS = 30


def fetch_node(node_reference):

    try:

        if str(node_reference).isdigit():

            lookup_reference = (
                f"SOC_{node_reference}"
            )

        else:

            lookup_reference = (
                str(node_reference)
            )

        data = get(
            f"/assets/v1/assets/{lookup_reference}",
            params={
                "ownerId": OWNER_ID
            },
            retries=3
        )

        data["path_reference"] = (
            node_reference
        )

        return data, None

    except Exception as e:

        return None, (
            node_reference,
            str(e)
        )


def get_asset_nodes(df_asset_path):

    unique_nodes = (
        df_asset_path["path_reference"]
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    total = len(unique_nodes)

    print(
        f"Nombre de noeuds à récupérer : "
        f"{total}"
    )

    rows = []

    failed_nodes = []

    completed = 0

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {

            executor.submit(
                fetch_node,
                node_reference
            ): node_reference

            for node_reference
            in unique_nodes

        }

        for future in as_completed(
            futures
        ):

            completed += 1

            data, error = (
                future.result()
            )

            if data:

                rows.append(data)

            if error:

                failed_nodes.append(
                    error
                )

            if (
                completed % 100 == 0
                or completed == total
            ):

                print(
                    f"{completed}/{total} "
                    f"({round(completed / total * 100, 1)}%)"
                )

    print(
        f"\nNoeuds récupérés : "
        f"{len(rows)}"
    )

    print(
        f"Noeuds en erreur : "
        f"{len(failed_nodes)}"
    )

    if failed_nodes:

        pd.DataFrame(
            failed_nodes,
            columns=[
                "path_reference",
                "error"
            ]
        ).to_csv(
            "failed_nodes.csv",
            index=False
        )

    if not rows:

        return pd.DataFrame()

    df_nodes = pd.json_normalize(
        rows
    )

    colonnes_a_garder = [

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
        "lastUpdateDate"
    ]

    for col in colonnes_a_garder:

        if col not in df_nodes.columns:

            df_nodes[col] = None

    df_nodes = df_nodes[
        colonnes_a_garder
    ]

    df_nodes["contracts"] = (
        df_nodes["contracts"]
        .apply(
            lambda x:
            json.dumps(x)
            if isinstance(
                x,
                list
            )
            else None
        )
    )

    for col in [
        "creationDate",
        "lastUpdateDate"
    ]:

        df_nodes[col] = pd.to_datetime(
            df_nodes[col],
            errors="coerce",
            utc=True
        )

    return df_nodes