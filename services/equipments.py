import time
import pandas as pd

from api.client import get


def get_equipments():

    all_equipments = []

    page = 1

    while True:

        data = get(
            "/assets/v2/assets",
            params={
                "ownerId": "5a2942cfd207720cf70b6796",
                "type": "equipment",
                "page": page,
                "perPage": 100
            }
        )

        equipments = (
            data["_embedded"]["assets"]
        )

        all_equipments.extend(
            equipments
        )

        if page % 20 == 0:

            print(
                f"{len(all_equipments):,} équipements récupérés"
            )

        if "paginate:next" not in data["_links"]:

            break

        page += 1

        time.sleep(0.1)

    print(
        f"\nTotal récupéré : "
        f"{len(all_equipments):,} équipements"
    )

    df = pd.json_normalize(
        all_equipments
    )

    colonnes_a_garder = [

        "reference",
        "label",

        "type",

        "fullPath",

        "installationPath",
        "installationReference",

        "contracts",

        "tags.intent_type",

        "tags.intent_address_way",
        "tags.intent_address_zip",
        "tags.intent_address_city",

        "creationDate",
        "lastUpdateDate"
    ]

    for col in colonnes_a_garder:

        if col not in df.columns:

            df[col] = None

    df = df[
        colonnes_a_garder
    ]

    for col in [

        "creationDate",
        "lastUpdateDate"

    ]:

        df[col] = pd.to_datetime(
            df[col],
            errors="coerce",
            utc=True
        )

    print(
        f"Equipements : "
        f"{len(df):,}"
    )

    return df