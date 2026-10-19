from pathlib import Path
import sys
import time

import pandas as pd
from sqlalchemy import create_engine, text


# ============================================================
# RACINE DU PROJET
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS PROJET
# ============================================================

from config import DB_URL

from api.client import get

from services.asset_path import get_asset_path
from services.asset_nodes import get_asset_nodes

from database.upsert import upsert_dataframe


# ============================================================
# CONNEXION POSTGRESQL
# ============================================================

engine = create_engine(
    DB_URL
)


# ============================================================
# RECUPERATION DES BATIMENTS
# ============================================================

def get_buildings():

    print("\n========================================")
    print("RECUPERATION DES BATIMENTS")
    print("========================================")

    all_buildings = []

    page = 1

    while True:

        try:

            data = get(
                "/assets/v2/assets",
                params={
                    "type": "building",
                    "category": "Batiment",
                    "page": page,
                    "perPage": 100
                }
            )

        except Exception as e:

            print(
                f"\nERREUR API page {page} : {e}"
            )

            raise

        buildings = (
            data
            .get("_embedded", {})
            .get("assets", [])
        )

        if not buildings:

            print(
                f"Aucun bâtiment retourné "
                f"à la page {page}"
            )

            break

        all_buildings.extend(
            buildings
        )

        if page == 1 or page % 20 == 0:

            print(
                f"Page {page} : "
                f"{len(all_buildings):,} "
                f"bâtiments récupérés"
            )

        links = data.get(
            "_links",
            {}
        )

        if "paginate:next" not in links:

            break

        page += 1

        time.sleep(0.1)

    print(
        f"\nTotal API : "
        f"{len(all_buildings):,} bâtiments"
    )


    # ========================================================
    # NORMALISATION
    # ========================================================

    if not all_buildings:

        return pd.DataFrame()


    df = pd.json_normalize(
        all_buildings
    )


    # ========================================================
    # COLONNES
    # ========================================================

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


    # ========================================================
    # CONTROLES
    # ========================================================

    total = len(df)

    uniques = (
        df["reference"]
        .nunique()
    )

    nulles = (
        df["reference"]
        .isna()
        .sum()
    )

    doublons = (
        df["reference"]
        .duplicated()
        .sum()
    )


    print("\n===== CONTROLES BATIMENTS =====")

    print(
        f"Lignes : {total:,}"
    )

    print(
        f"Références uniques : {uniques:,}"
    )

    print(
        f"Références nulles : {nulles:,}"
    )

    print(
        f"Doublons : {doublons:,}"
    )


    # Suppression éventuelle des doublons exacts
    # sur reference avant chargement

    df = (
        df
        .dropna(
            subset=["reference"]
        )
        .drop_duplicates(
            subset=["reference"],
            keep="last"
        )
        .reset_index(drop=True)
    )


    return df


# ============================================================
# CREATION TABLE BUILDINGS SI ELLE N'EXISTE PAS
# ============================================================

def create_buildings_table():

    print("\n========================================")
    print("VERIFICATION TABLE BUILDINGS_CURRENT")
    print("========================================")

    sql = """
    CREATE TABLE IF NOT EXISTS buildings_current (

        reference TEXT PRIMARY KEY,

        code TEXT,

        label TEXT,

        category TEXT,

        type TEXT,

        "fullPath" TEXT,

        "parentPath" TEXT,

        "creationDate" TIMESTAMPTZ,

        "lastUpdateDate" TIMESTAMPTZ

    );
    """

    with engine.begin() as conn:

        conn.execute(
            text(sql)
        )

    print(
        "Table buildings_current OK"
    )


# ============================================================
# CHARGEMENT BATIMENTS
# ============================================================

def update_buildings():

    df_buildings = (
        get_buildings()
    )


    if df_buildings.empty:

        print(
            "\nERREUR : "
            "aucun bâtiment récupéré."
        )

        return None


    print("\n========================================")
    print("CHARGEMENT BUILDINGS_CURRENT")
    print("========================================")


    upsert_dataframe(
        df=df_buildings,
        table_name="buildings_current",
        key_columns=[
            "reference"
        ],
        engine=engine
    )


    print(
        f"{len(df_buildings):,} "
        f"bâtiments chargés"
    )


    return df_buildings


# ============================================================
# ASSET PATH BATIMENTS
# ============================================================

def update_building_asset_paths():

    print("\n========================================")
    print("BATIMENTS SANS ASSET PATH")
    print("========================================")


    df_missing = pd.read_sql(
        """
        SELECT b.*

        FROM buildings_current b

        LEFT JOIN (

            SELECT DISTINCT
                asset_reference

            FROM asset_path_current

        ) ap

            ON b.reference =
               ap.asset_reference

        WHERE ap.asset_reference
              IS NULL
        """,
        engine
    )


    print(
        f"Bâtiments sans asset path : "
        f"{len(df_missing):,}"
    )


    if df_missing.empty:

        print(
            "Tous les bâtiments "
            "ont déjà un asset path."
        )

        return


    print("\n========================================")
    print("RECUPERATION ASSET PATH")
    print("========================================")


    df_paths = get_asset_path(
        df_missing
    )


    if df_paths is None:

        print(
            "get_asset_path a retourné None."
        )

        return


    if df_paths.empty:

        print(
            "Aucun asset path retourné."
        )

        return


    print(
        f"Relations asset path récupérées : "
        f"{len(df_paths):,}"
    )


    upsert_dataframe(
        df=df_paths,
        table_name="asset_path_current",
        key_columns=[
            "asset_reference",
            "path_reference"
        ],
        engine=engine
    )


    print(
        "Asset paths bâtiments chargés."
    )


# ============================================================
# ASSET NODES MANQUANTS
# ============================================================

def update_asset_nodes():

    print("\n========================================")
    print("ASSET NODES MANQUANTS")
    print("========================================")


    df_missing_nodes = pd.read_sql(
        """
        SELECT DISTINCT

            ap.path_reference

        FROM asset_path_current ap

        LEFT JOIN asset_nodes_current an

            ON ap.path_reference =
               an.path_reference

        WHERE an.path_reference
              IS NULL
        """,
        engine
    )


    print(
        f"Nodes manquants : "
        f"{len(df_missing_nodes):,}"
    )


    if df_missing_nodes.empty:

        print(
            "Aucun asset node manquant."
        )

        return


    print("\n========================================")
    print("RECUPERATION ASSET NODES")
    print("========================================")


    df_nodes = get_asset_nodes(
        df_missing_nodes
    )


    if df_nodes is None:

        print(
            "get_asset_nodes a retourné None."
        )

        return


    if df_nodes.empty:

        print(
            "Aucun asset node retourné."
        )

        return


    print(
        f"Nodes récupérés : "
        f"{len(df_nodes):,}"
    )


    upsert_dataframe(
        df=df_nodes,
        table_name="asset_nodes_current",
        key_columns=[
            "path_reference"
        ],
        engine=engine
    )


    print(
        "Asset nodes chargés."
    )


# ============================================================
# CONTROLES FINAUX
# ============================================================

def final_checks():

    print("\n========================================")
    print("CONTROLES FINAUX")
    print("========================================")


    # --------------------------------------------------------
    # NOMBRE DE BATIMENTS
    # --------------------------------------------------------

    df = pd.read_sql(
        """
        SELECT

            COUNT(*) AS total,

            COUNT(
                DISTINCT reference
            ) AS references_uniques

        FROM buildings_current
        """,
        engine
    )


    print("\nBATIMENTS")

    print(
        df.to_string(
            index=False
        )
    )


    # --------------------------------------------------------
    # BATIMENTS AVEC PATH
    # --------------------------------------------------------

    df = pd.read_sql(
        """
        SELECT

            COUNT(
                DISTINCT b.reference
            ) AS total_batiments,

            COUNT(
                DISTINCT ap.asset_reference
            ) AS batiments_avec_path

        FROM buildings_current b

        LEFT JOIN asset_path_current ap

            ON b.reference =
               ap.asset_reference
        """,
        engine
    )


    print("\nASSET PATH")

    print(
        df.to_string(
            index=False
        )
    )


    # --------------------------------------------------------
    # PATHS / NODES
    # --------------------------------------------------------

    df = pd.read_sql(
        """
        SELECT

            COUNT(
                DISTINCT ap.path_reference
            ) AS paths,

            COUNT(
                DISTINCT an.path_reference
            ) AS nodes

        FROM asset_path_current ap

        INNER JOIN buildings_current b

            ON ap.asset_reference =
               b.reference

        LEFT JOIN asset_nodes_current an

            ON ap.path_reference =
               an.path_reference
        """,
        engine
    )


    print("\nASSET NODES")

    print(
        df.to_string(
            index=False
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("########################################")
    print("#     MISE A JOUR DES BATIMENTS       #")
    print("########################################")


    # 1
    create_buildings_table()


    # 2
    df_buildings = update_buildings()


    if df_buildings is None:

        print(
            "\nARRÊT : aucun bâtiment."
        )

        return


    # 3
    update_building_asset_paths()


    # 4
    update_asset_nodes()


    # 5
    final_checks()


    print("\n")
    print("########################################")
    print("#       TRAITEMENT TERMINE             #")
    print("########################################")
    print("\n")


# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":

    main()