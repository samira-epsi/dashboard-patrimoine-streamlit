import pandas as pd

from api.client import get


def get_service_codes(contract_references):

    all_service_codes = []

    total_contracts = len(contract_references)

    for index, contract_reference in enumerate(
        contract_references,
        start=1
    ):

        print(
            f"Contrat {index}/{total_contracts} "
            f"({contract_reference})"
        )

        try:

            data = get(
                f"/contracts/v1/contracts/{contract_reference}"
            )

            if "serviceCodes" not in data:
                continue

            service_codes = data["serviceCodes"]

            if len(service_codes) == 0:
                continue

            df_tmp = pd.json_normalize(
                service_codes
            )

            df_tmp["contract_reference"] = (
                contract_reference
            )

            all_service_codes.append(
                df_tmp
            )

        except Exception as e:

            print(
                f"Erreur contrat "
                f"{contract_reference}"
            )

            print(e)

    if not all_service_codes:

        return pd.DataFrame()

    df_service_codes = pd.concat(
        all_service_codes,
        ignore_index=True
    )

    colonnes_a_garder = [

        "contract_reference",

        "id",
        "code",
        "thirdPartyCode",

        "label",
        "description",

        "workType",
        "criticalLevel",
        "fixedRate",

        "sla.periodicity.value",
        "sla.periodicity.unit",

        "sla.estimatedInterventionDuration.value",
        "sla.estimatedInterventionDuration.unit",

        "sla.maxTimeToIntervention.value",
        "sla.maxTimeToIntervention.unit",

        "sla.maxTimeToRecovery.value",
        "sla.maxTimeToRecovery.unit"
    ]

    for col in colonnes_a_garder:

        if col not in df_service_codes.columns:

            df_service_codes[col] = None

    df_service_codes = (
        df_service_codes[
            colonnes_a_garder
        ]
    )

    return df_service_codes