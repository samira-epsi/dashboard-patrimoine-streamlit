import time
import pandas as pd

from api.client import get


def get_buildings():

    all_buildings = []

    page = 1

    while True:

        data = get(
            "/assets/v2/assets",
            params={
                "type": "building",
                "category": "Batiment",
                "page": page,
                "perPage": 100
            }
        )

        buildings = (
            data
            .get("_embedded", {})
            .get("assets", [])
        )

        all_buildings.extend(
            buildings
        )

        if page % 50 == 0:

            print(
                f"{len(all_buildings):,} "
                f"bâtiments récupérés"
            )

        if "paginate:next" not in data.get(
            "_links",
            {}
        ):

            break

        page += 1

        time.sleep(0.1)

    print(
        f"\nTotal récupéré : "
        f"{len(all_buildings):,} bâtiments"
    )

    df = pd.json_normalize(
        all_buildings
    )

    colonnes_a_garder = [

        "reference",
        "code",
        "label",

        "category",
        "type",

        "fullPath",
        "parentPath",

        "creationDate",
        "lastUpdateDate"
    ]

    for col in colonnes_a_garder:

        if col not in df.columns:

            df[col] = None

    df = df[
        colonnes_a_garder
    ].copy()


    # ========================================================
    # CONTROLES
    # ========================================================

    total_rows = len(df)

    unique_refs = (
        df["reference"]
        .nunique()
    )

    null_refs = (
        df["reference"]
        .isna()
        .sum()
    )

    duplicate_refs = (
        df["reference"]
        .duplicated()
        .sum()
    )

    print(
        "\n===== CONTROLES BATIMENTS ====="
    )

    print(
        f"Lignes : "
        f"{total_rows:,}"
    )

    print(
        f"References uniques : "
        f"{unique_refs:,}"
    )

    print(
        f"References nulles : "
        f"{null_refs:,}"
    )

    print(
        f"Doublons : "
        f"{duplicate_refs:,}"
    )


    # ========================================================
    # DATES
    # ========================================================

    for col in [
        "creationDate",
        "lastUpdateDate"
    ]:

        df[col] = pd.to_datetime(
            df[col],
            errors="coerce",
            utc=True
        )

    return df