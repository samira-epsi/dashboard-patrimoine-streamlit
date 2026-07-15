import pandas as pd

from api.client import get


def get_contracts():

    all_contracts = []

    page = 1

    while True:

        data = get(
            "/contracts/v1/contracts",
            params={
                "onlyActive": "false",
                "page": page,
                "perPage": 50
            }
        )

        contracts = data["_embedded"]["contracts"]

        all_contracts.extend(contracts)

        print(
            f"Page {page} récupérée - "
            f"{len(contracts)} contrats"
        )

        # S'il n'y a pas de page suivante,
        # on arrête la boucle
        if "paginate:next" not in data["_links"]:
            break

        page += 1

    print(
        f"Total récupéré : {len(all_contracts)} contrats"
    )

    df_contracts = pd.json_normalize(all_contracts)

    colonnes_a_garder = [
        "id",                       # Id du contrat dans intent
        "label",                    # Nom du contrat
        "description",
        "topic",                    # métier (ex: ascenseur, plomberie)
        "status",                   # active, inactive
        "reference",                # référence du contrat
        "thirdParty.entity.id",     # id du prestataire dans intent
        "thirdParty.entity.label",  # nom du prestataire
        "thirdParty.reference",     # référence du contrat chez le prestataire
        "startDate",                # date de début du contrat
        "endDate",                  # date de fin du contrat
        "creationDate",             # date de création du contrat dans intent
        "lastUpdateDate",           # dernière modification du contrat
        "deactivationDate"          # date de désactivation du contrat
    ]

    df_contracts = df_contracts[colonnes_a_garder]

    date_columns = [
        "startDate",
        "endDate",
        "creationDate",
        "lastUpdateDate",
        "deactivationDate"
    ]

    for col in date_columns:
        df_contracts[col] = pd.to_datetime(
            df_contracts[col],
            errors="coerce",
            # Les dates de l'API utilisent plusieurs fuseaux horaires.
            # utc=True permet de les normaliser dans un fuseau unique (UTC)
            # et de les convertir en datetime Pandas.
            utc=True
        )

    return df_contracts