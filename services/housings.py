import time
import pandas as pd

from api.client import get


def get_housings():

    all_housings = []

    page = 1

    while True:

        data = get(
            "/assets/v2/assets",
            params={
                "category": "Logement",
                "page": page,
                "perPage": 100
            }
        )

        housings = data["_embedded"]["assets"]

        all_housings.extend(
            housings
        )

        if page % 50 == 0:

            print(
                f"{len(all_housings):,} logements récupérés"
            )

        if "paginate:next" not in data["_links"]:

            break

        page += 1

        time.sleep(0.1)

    print(
        f"\nTotal récupéré : "
        f"{len(all_housings):,} logements"
    )

    df = pd.json_normalize(
        all_housings
    )

    colonnes_a_garder = [

        "reference",
        "code",
        "label",

        "category",
        "type",

        "fullPath",
        "parentPath",

        "tags.typologie",

        "tags.surface_habitable",
        "tags.surface_reelle",
        "tags.surface_utile",

        "tags.etage",

        "tags.mode_chauffage",
        "tags.type_chauffage",

        "tags.categorie_financement",

        "tags.temoin_ascenseur",
        "tags.accessibilite_handicapes",

        "tags.contrat_multitechnique",

        "tags.intent_address_way",
        "tags.intent_address_zip",
        "tags.intent_address_city",

        "tags.date_mise_en_location",
        "tags.intent_commissioning_date",

        "creationDate",
        "lastUpdateDate"
    ]

    for col in colonnes_a_garder:

        if col not in df.columns:

            df[col] = None

    df = df[
        colonnes_a_garder
    ]

    # -----------------------
    # CONTROLES QUALITE
    # -----------------------

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
        total_rows
        - unique_refs
    )

    print(
        "\n===== CONTROLES ====="
    )

    print(
        f"Lignes : {total_rows:,}"
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

    if duplicate_refs > 0:

        print(
            "\nATTENTION : "
            "des doublons existent"
        )

    if null_refs > 0:

        print(
            "\nATTENTION : "
            "des references sont nulles"
        )

    # -----------------------
    # CONVERSION DATES
    # -----------------------

    for col in [

        "creationDate",

        "lastUpdateDate",

        "tags.intent_commissioning_date"

    ]:

        df[col] = pd.to_datetime(
            df[col],
            errors="coerce",
            utc=True
        )

    return df