import json
import pandas as pd

from api.client import get


def get_programs():

    all_programs = []

    page = 1

    while True:

        data = get(
            "/assets/v2/assets",
            params={
                "category": "Programme",
                "page": page,
                "perPage": 50
            }
        )

        programs = data["_embedded"]["assets"]

        all_programs.extend(programs)

        print(
            f"Page {page} récupérée - "
            f"{len(programs)} programmes"
        )

        if "paginate:next" not in data["_links"]:
            break

        page += 1

    print(
        f"Total récupéré : "
        f"{len(all_programs)} programmes"
    )

    df_programs = pd.json_normalize(
        all_programs
    )

    colonnes_a_garder = [

        # Identifiants
        "reference",
        "code",
        "label",

        # Métier
        "category",
        "type",

        # Hiérarchie patrimoniale
        "fullPath",
        "parentPath",

        # Référence métier 3F
        "tags.3f_reference",

        # Informations programme
        "tags.type_programme",
        "tags.copropriete",

        # Dates métier
        "tags.date_fin_construction",
        "tags.date_premiere_mise_en_location",

        # Géolocalisation
        "tags.intent_latitude",
        "tags.intent_longitude",

        # Adresse
        "tags.intent_address_city",
        "tags.intent_address_zip",

        # Sortie patrimoine
        "tags.intent_decommissioning_date",
        "tags.motif_sortie",
        "tags.sorti_le",

        # Contrats associés
        "contracts",

        # Historisation
        "creationDate",
        "lastUpdateDate"
    ]

    for col in colonnes_a_garder:

        if col not in df_programs.columns:

            df_programs[col] = None

    df_programs = df_programs[
        colonnes_a_garder
    ]

    # Conversion des listes de contrats
    df_programs["contracts"] = (
        df_programs["contracts"]
        .apply(
            lambda x:
            json.dumps(x)
            if isinstance(x, list)
            else None
        )
    )

    date_columns = [
        "creationDate",
        "lastUpdateDate"
    ]

    for col in date_columns:

        df_programs[col] = pd.to_datetime(
            df_programs[col],
            errors="coerce",
            utc=True
        )

    return df_programs