import pandas as pd


def get_asset_path(df_assets):

    rows = []

    for _, row in df_assets.iterrows():

        asset_reference = (
            row.get("reference")
        )

        full_path = (
            row.get("fullPath")
        )

        asset_type = (
            row.get("type")
        )

        if pd.isna(full_path):

            rows.append(
                {
                    "asset_reference": asset_reference,
                    "asset_type": asset_type,
                    "path_reference": None,
                    "path_order": None
                }
            )

            continue

        path_parts = [

            part.strip()

            for part in str(
                full_path
            ).split("/")

            if part
            and str(part).strip()

        ]

        # Retire l'asset lui-même
        path_parts = path_parts[:-1]

        if len(path_parts) == 0:

            rows.append(
                {
                    "asset_reference": asset_reference,
                    "asset_type": asset_type,
                    "path_reference": None,
                    "path_order": None
                }
            )

            continue

        for order, path_reference in enumerate(
            path_parts,
            start=1
        ):

            rows.append(
                {
                    "asset_reference": asset_reference,
                    "asset_type": asset_type,
                    "path_reference": path_reference,
                    "path_order": order
                }
            )

    return pd.DataFrame(rows)