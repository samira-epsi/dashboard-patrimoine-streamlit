# #Test1 Connexion Api
# #from api.auth import get_token
# #token = get_token()
# #print(token[:20])


# #Test2 client pour faire la base de nos endpoints
# from api.client import get

# #data = get(
# #    "/contracts/v1/contracts",
# #    params={
# #        "onlyActive": "false"
# #    }
# #)

# #print(type(data))
# #print(data.keys())


# #Test 3 testons le service contracts pour savoir s'il récupère bien mes contrats avec mes transformation

# #from services.contracts import get_contracts
# #df_contracts = get_contracts()

# #print(df_contracts.head())
# #print(df_contracts.columns)
# #print(df_contracts.info())
# #print(data["total"])
# #print(len(data["_embedded"]["contracts"]))

# #Test 4 testons la pagination des données

# # from api.client import get

# # data = get(
# #     "/contracts/v1/contracts",
# #     params={
# #         "onlyActive": "false"
# #     }
# # )

# # print("Nombre total annoncé par l'API :")
# # print(data.get("total"))

# # print("\nNombre de contrats récupérés :")
# # print(len(data["_embedded"]["contracts"]))

# # print("\nClés de la réponse :")
# # print(data.keys())

# # print("\nLinks disponibles :")
# # print(data.get("_links"))

# #On constate qu'aujourd'hui je récupère que 50lignes alors que j'en ai 562

# #Test 5 testons à nouveau la pagination
# # from services.contracts import get_contracts

# # df_contracts = get_contracts()

# #print(df_contracts.shape)

# # Test 6 testons que mes tables contracts sont bien ajoutés
# # from services.contracts import get_contracts
# # from database.connection import engine
# # from database.loader import (
# #     load_snapshot,
# #     load_current
# # )

# # df_contracts = get_contracts()

# # # Historique
# # load_snapshot(
# #     df_contracts,
# #     "contracts_snapshot",
# #     engine
# # )

# # # Etat actuel
# # load_current(
# #     df_contracts,
# #     "contracts_current",
# #     engine
# # )

# # print("Chargement terminé")


# # TesT 7 testons le code des codes de prestation
# # import pandas as pd
# # from sqlalchemy import create_engine

# # from services.asset_path import (
# #     get_asset_path
# # )
# # from config import DB_URL
# # engine = create_engine(
# #     DB_URL
# # )

# # from services.service_codes import (
# #     get_service_codes
# # )

# # from database.loader import (
# #     load_current,
# #     load_snapshot
# # )

# # # Lecture des contrats depuis PostgreSQL

# # df_contracts = pd.read_sql(
# #     """
# #     SELECT reference
# #     FROM contracts_current
# #     """,
# #     engine
# # )

# # contract_references = (
# #     df_contracts["reference"]
# #     .dropna()
# #     .astype(str)
# #     .tolist()
# # )

# # # Extraction des codes prestations

# # df_service_codes = get_service_codes(
# #     contract_references
# # )

# # print(df_service_codes.shape)

# # print(df_service_codes.head())

# # # Chargement PostgreSQL

# # load_current(
# #     df_service_codes,
# #     "service_codes_current",
# #     engine
# # )

# # load_snapshot(
# #     df_service_codes,
# #     "service_codes_snapshot",
# #     engine
# # )

# # print("Chargement terminé")

# # Test 8 testons le code des programmes
# # from services.programs import get_programs

# # from database.connection import engine

# # from database.loader import (
# #     load_current,
# #     load_snapshot
# # )


# # df_programs = get_programs()

# # print(df_programs.shape)

# # load_current(
# #     df_programs,
# #     "programs_current",
# #     engine
# # )

# # # load_snapshot(
# # #     df_programs,
# # #     "programs_snapshot",
# # #     engine
# # # )

# # # print("Chargement terminé")

# # # Test 9 testons le assets path
# # from services.programs import (
# #     get_programs
# # )

# # from services.asset_path import (
# #     get_asset_path
# # )

# # from database.connection import (
# #     engine
# # )

# # from database.loader import (
# #     load_current,
# #     load_snapshot
# # )


# # # -----------------------------
# # # PROGRAMMES
# # # -----------------------------

# # df_programs = get_programs()

# # # print(
# # #     f"Programmes : {df_programs.shape}"
# # # )

# # # load_current(
# # #     df_programs,
# # #     "programs_current",
# # #     engine
# # # )

# # # load_snapshot(
# # #     df_programs,
# # #     "programs_snapshot",
# # #     engine
# # # )


# # # # -----------------------------
# # # # ASSET PATH
# # # # -----------------------------

# # df_asset_path = get_asset_path(
# #     df_programs
# # )

# # # print(
# # #     f"Asset Path : {df_asset_path.shape}"
# # # )

# # # load_current(
# # #     df_asset_path,
# # #     "asset_path_current",
# # #     engine
# # # )

# # # load_snapshot(
# # #     df_asset_path,
# # #     "asset_path_snapshot",
# # #     engine
# # # )

# # # print(
# # #     "Chargement terminé"
# # # )

# # # ---------------------------------
# # # TEST ASSET NODES
# # # ---------------------------------

# # path_references = (
# #     df_asset_path["path_reference"]
# #     .drop_duplicates()
# #     .tolist()
# # )

# # print(
# #     f"Nombre de path_reference uniques : "
# #     f"{len(path_references)}"
# # )

# # print(
# #     "10 premiers codes :"
# # )

# # print(
# #     path_references[:10]
# # )

# # Test 10 testons le asset_nodes
# # import pandas as pd

# # from services.asset_nodes import (
# #     get_asset_nodes
# # )

# # from database.connection import (
# #     engine
# # )

# # from database.loader import (
# #     load_current,
# #     load_snapshot
# # )

# # df_asset_path = pd.read_sql(
# #     "SELECT * FROM asset_path_current",
# #     engine
# # )

# # df_asset_nodes = get_asset_nodes(
# #     df_asset_path
# # )

# # print(
# #     f"Asset Nodes : "
# #     f"{df_asset_nodes.shape}"
# # )

# # load_current(
# #     df_asset_nodes,
# #     "asset_nodes_current",
# #     engine
# # )

# # load_snapshot(
# #     df_asset_nodes,
# #     "asset_nodes_snapshot",
# #     engine
# # )

# # print(
# #     "Chargement terminé"
# # )

# #Test 11 Testons la récupération de tous nos logements
# # from database.connection import get_engine
# # from database.loader import (
# #     load_current,
# #     load_snapshot
# # )

# # from services.housings import get_housings


# # def main():

# #     engine = get_engine()

# #     print("\n===== HOUSINGS =====")

# #     df_housings = get_housings()

# #     print(
# #         f"Housings : "
# #         f"{df_housings.shape}"
# #     )

# #     print(
# #         "\n===== CURRENT ====="
# #     )

# #     load_current(
# #         df_housings,
# #         "housings_current",
# #         engine
# #     )

# #     print(
# #         "\n===== SNAPSHOT ====="
# #     )

# #     load_snapshot(
# #         df_housings,
# #         "housings_snapshot",
# #         engine
# #     )

# #     print(
# #         "\nChargement terminé"
# #     )


# # if __name__ == "__main__":

# #     main()

# # Test 12 testons le asset path pour les logements
# # from sqlalchemy import text
# # import pandas as pd

# # from database.connection import get_engine
# # from database.loader import (
# #     load_current,
# #     load_snapshot
# # )

# # from services.asset_path import get_asset_path


# # engine = get_engine()

# # # print(
# # #     "\n===== LECTURE HOUSINGS_CURRENT ====="
# # # )

# # df_housings = pd.read_sql(
# #     """
# #     SELECT *
# #     FROM housings_current
# #     """,
# #     engine
# # )

# # print(
# #     f"Housings : "
# #     f"{df_housings.shape}"
# # )

# # print(
# #     "\n===== ASSET PATH ====="
# # )

# # df_asset_path = get_asset_path(
# #     df_housings
# # )

# # print(
# #     f"Asset Path : "
# #     f"{df_asset_path.shape}"
# # )

# # load_current(
# #     df_asset_path,
# #     "housing_asset_path_current",
# #     engine
# # )

# # load_snapshot(
# #     df_asset_path,
# #     "housing_asset_path_snapshot",
# #     engine
# # )

# # print(
# #     "\nTerminé"
# # )
# # df_housing_path = get_asset_path(
# #     df_housings
# # )

# # print(df_housing_path.shape)

# # print(
# #     df_housing_path.head(20)
# # )
# # print(
# #     df_housing_path["path_reference"]
# #     .nunique()
# # )
# # from sqlalchemy import text
# # import pandas as pd

# # df_nodes = pd.read_sql(
# #     text("""
# #     SELECT path_reference
# #     FROM asset_nodes_current
# #     """),
# #     engine
# # )

# # existing_nodes = set(
# #     df_nodes["path_reference"]
# # )

# # housing_nodes = set(
# #     df_housing_path["path_reference"]
# # )

# # missing_nodes = (
# #     housing_nodes
# #     - existing_nodes
# # )

# # print(
# #     f"Noeuds existants : {len(existing_nodes):,}"
# # )

# # print(
# #     f"Noeuds housing : {len(housing_nodes):,}"
# # )

# # print(
# #     f"Noeuds manquants : {len(missing_nodes):,}"
# # )

# # print(
# #     list(missing_nodes)[:50]
# # )

# # print(
# #     df_housing_path["path_order"]
# #     .value_counts()
# #     .sort_index()
# # )

# # for level in sorted(
# #     df_housing_path["path_order"].unique()
# # ):

# #     count = (
# #         df_housing_path[
# #             df_housing_path["path_order"] == level
# #         ]["path_reference"]
# #         .nunique()
# #     )

# #     print(
# #         f"Niveau {level} : "
# #         f"{count:,} noeuds uniques"
# #     )

# # from sqlalchemy import text
# # import pandas as pd

# # from database.connection import get_engine
# # from database.loader import (
# #     load_current,
# #     load_snapshot
# # )

# # from services.asset_path import get_asset_path


# # def main():

# #     engine = get_engine()

# #     print(
# #         "\n===== ASSET PATH EXISTANT ====="
# #     )

# #     df_existing = pd.read_sql(
# #         text("""
# #         SELECT *
# #         FROM asset_path_current
# #         """),
# #         engine
# #     )

# #     print(
# #         f"Asset Path existant : "
# #         f"{df_existing.shape}"
# #     )

# #     print(
# #         "\n===== HOUSINGS ====="
# #     )

# #     df_housings = pd.read_sql(
# #         text("""
# #         SELECT *
# #         FROM housings_current
# #         """),
# #         engine
# #     )

# #     print(
# #         f"Housings : "
# #         f"{df_housings.shape}"
# #     )

# #     print(
# #         "\n===== CONSTRUCTION PATH ====="
# #     )

# #     df_housing_path = get_asset_path(
# #         df_housings
# #     )

# #     print(
# #         f"Housing Path : "
# #         f"{df_housing_path.shape}"
# #     )

# #     print(
# #         "\n===== FUSION ====="
# #     )

# #     df_asset_path = pd.concat(
# #         [
# #             df_existing,
# #             df_housing_path
# #         ],
# #         ignore_index=True
# #     )

# #     before = len(
# #         df_asset_path
# #     )

# #     df_asset_path = (
# #         df_asset_path
# #         .drop_duplicates()
# #     )

# #     after = len(
# #         df_asset_path
# #     )

# #     print(
# #         f"Doublons supprimés : "
# #         f"{before - after:,}"
# #     )

# #     print(
# #         f"Asset Path final : "
# #         f"{df_asset_path.shape}"
# #     )

# #     print(
# #         "\n===== CURRENT ====="
# #     )

# #     load_current(
# #         df_asset_path,
# #         "asset_path_current",
# #         engine
# #     )

# #     print(
# #         "\n===== SNAPSHOT ====="
# #     )

# #     load_snapshot(
# #         df_asset_path,
# #         "asset_path_snapshot",
# #         engine
# #     )

# #     print(
# #         "\nChargement terminé"
# #     )


# # if __name__ == "__main__":

# #     main()



# # Autre code pour tester le housing

# # from datetime import datetime
# # from sqlalchemy import text

# # snapshot_date = datetime.now()

# # print("\n===== HOUSINGS =====")

# # df_housings = pd.read_sql(
# #     "SELECT * FROM housings_current",
# #     engine
# # )

# # print("Housings :", df_housings.shape)

# # print("\n===== HOUSING PATH =====")

# # df_housing_path = get_asset_path(df_housings)

# # print("Housing Path :", df_housing_path.shape)

# # print("\n===== UPSERT CURRENT =====")

# # housing_refs = df_housing_path["asset_reference"].dropna().unique().tolist()

# # with engine.begin() as conn:

# #     conn.execute(
# #         text("""
# #             DELETE FROM asset_path_current
# #             WHERE asset_reference = ANY(:refs)
# #         """),
# #         {"refs": housing_refs}
# #     )

# # print(f"Housing supprimés : {len(housing_refs)}")

# # df_housing_path.to_sql(
# #     "asset_path_current",
# #     engine,
# #     if_exists="append",
# #     index=False
# # )

# # print("Housing Path insérés")

# # print("\n===== SNAPSHOT =====")

# # df_housing_path_snapshot = df_housing_path.copy()

# # df_housing_path_snapshot["snapshot_date"] = snapshot_date

# # df_housing_path_snapshot.to_sql(
# #     "asset_path_snapshot",
# #     engine,
# #     if_exists="append",
# #     index=False
# # )

# # print("asset_path_snapshot enrichie")

# # print(f"Snapshot date : {snapshot_date}")

# # from datetime import datetime

# # snapshot_date = datetime.now()

# # from services.asset_nodes import get_asset_nodes

# # print("\n===== ASSET PATH HOUSINGS =====")

# # df_housing_path = get_asset_path(df_housings)

# # print("Housing Path :", df_housing_path.shape)

# # print("\n===== HOUSING NODES =====")

# # df_housing_nodes = get_asset_nodes(
# #     df_housing_path
# # )


# # print("Housing Nodes :", df_housing_nodes.shape)

# # print("\n===== NODES EXISTANTS =====")

# # df_existing_nodes = pd.read_sql(
# #     "SELECT * FROM asset_nodes_current",
# #     engine
# # )

# # print(
# #     "Nodes existants :",
# #     df_existing_nodes.shape
# # )

# # print(df_housing_path["path_reference"].nunique())

# # print(
# #     df_housing_path["path_reference"]
# #     .drop_duplicates()
# #     .head(100)
# #     .tolist()
# # )
# # print("\n===== UPSERT CURRENT =====")

# # df_nodes_current = pd.concat(
# #     [
# #         df_existing_nodes,
# #         df_housing_nodes
# #     ],
# #     ignore_index=True
# # )

# # before = len(df_nodes_current)

# # df_nodes_current = (
# #     df_nodes_current
# #     .drop_duplicates(
# #         subset=["path_reference"],
# #         keep="last"
# #     )
# # )

# # after = len(df_nodes_current)

# # print(
# #     "Doublons supprimés :",
# #     before - after
# # )

# # print(
# #     "Nodes final :",
# #     df_nodes_current.shape
# # )

# # df_nodes_current.to_sql(
# #     "asset_nodes_current",
# #     engine,
# #     if_exists="replace",
# #     index=False
# # )

# # print(
# #     "asset_nodes_current enrichie"
# # )

# # print("\n===== SNAPSHOT =====")

# # df_housing_nodes_snapshot = (
# #     df_housing_nodes.copy()
# # )

# # df_housing_nodes_snapshot[
# #     "snapshot_date"
# # ] = snapshot_date

# # df_housing_nodes_snapshot.to_sql(
# #     "asset_nodes_snapshot",
# #     engine,
# #     if_exists="append",
# #     index=False
# # )

# # print(
# #     "asset_nodes_snapshot enrichie"
# # )

# # print(
# #     f"Snapshot date : {snapshot_date}"
# # )



# # print("\n===== HOUSINGS =====")

# # df_housings = pd.read_sql(
# #     "SELECT * FROM housings_current",
# #     engine
# # )

# # print("Housings :", df_housings.shape)

# # print("\n===== HOUSING PATH =====")

# # df_housing_path = get_asset_path(
# #     df_housings
# # )

# # print(
# #     "Housing Path :",
# #     df_housing_path.shape

# # )

# # print("\n===== DIAGNOSTIC NODES =====")

# # print(
# #     "Nombre de lignes asset_path :",
# #     len(df_housing_path)
# # )

# # print(
# #     "Nombre de noeuds uniques :",
# #     df_housing_path["path_reference"].nunique()
# # )

# # print(
# #     df_housing_path
# #     .groupby("path_order")
# #     ["path_reference"]
# #     .nunique()
# # )
# # print(df_housing_path.shape)

# # print(
# #     df_housing_path["path_reference"]
# #     .nunique()
# # )

# # print(
# #     df_housing_path
# #     .groupby("path_order")
# #     ["path_reference"]
# #     .nunique()
# # )
# # df_nodes_existing = pd.read_sql(
# #     "SELECT path_reference FROM asset_nodes_current",
# #     engine
# # )

# # print(
# #     "Nodes existants :",
# #     df_nodes_existing["path_reference"].nunique()
# # )
# # nodes_to_fetch = (
# #     set(df_housing_path["path_reference"])
# #     - set(df_nodes_existing["path_reference"])
# # )

# # print(
# #     "Nodes à récupérer :",
# #     len(nodes_to_fetch)
# # )

# # from datetime import datetime
# # from services.asset_nodes import get_asset_nodes
# # snapshot_date = datetime.now()

# # print("\n===== HOUSINGS =====")

# # df_housings = pd.read_sql(
# #     "SELECT * FROM housings_current",
# #     engine
# # )

# # print(
# #     "Housings :",
# #     df_housings.shape
# # )

# # print("\n===== HOUSING PATH =====")

# # df_housing_path = get_asset_path(
# #     df_housings
# # )

# # print(
# #     "Housing Path :",
# #     df_housing_path.shape
# # )

# # print("\n===== NODES EXISTANTS =====")

# # df_nodes_existing = pd.read_sql(
# #     """
# #     SELECT *
# #     FROM asset_nodes_current
# #     """,
# #     engine
# # )

# # print(
# #     "Nodes existants :",
# #     df_nodes_existing.shape
# # )

# # print("\n===== RECHERCHE NODES MANQUANTS =====")

# # nodes_to_fetch = (
# #     set(
# #         df_housing_path["path_reference"]
# #     )
# #     -
# #     set(
# #         df_nodes_existing["path_reference"]
# #     )
# # )

# # print(
# #     "Nodes à récupérer :",
# #     len(nodes_to_fetch)
# # )

# # df_missing_nodes = pd.DataFrame(
# #     {
# #         "path_reference":
# #         list(nodes_to_fetch)
# #     }
# # )

# # print("\n===== RECUPERATION NODES =====")

# # df_housing_nodes = get_asset_nodes(
# #     df_missing_nodes
# # )

# # print(
# #     "Housing Nodes :",
# #     df_housing_nodes.shape
# # )

# # print("\n===== MAJ CURRENT =====")

# # df_nodes_current = pd.concat(
# #     [
# #         df_nodes_existing,
# #         df_housing_nodes
# #     ],
# #     ignore_index=True
# # )

# # before = len(df_nodes_current)

# # df_nodes_current = (
# #     df_nodes_current
# #     .drop_duplicates(
# #         subset=["path_reference"],
# #         keep="last"
# #     )
# # )

# # after = len(df_nodes_current)

# # print(
# #     "Doublons supprimés :",
# #     before - after
# # )

# # print(
# #     "Nodes final :",
# #     df_nodes_current.shape
# # )


# # df_nodes_current.to_sql(
# #     "asset_nodes_current",
# #     engine,
# #     if_exists="replace",
# #     index=False
# # )

# # print(
# #     "asset_nodes_current enrichie"
# # )

# # print("\n===== SNAPSHOT =====")

# # df_housing_nodes_snapshot = (
# #     df_housing_nodes.copy()
# # )

# # df_housing_nodes_snapshot[
# #     "snapshot_date"
# # ] = snapshot_date

# # df_housing_nodes_snapshot.to_sql(
# #     "asset_nodes_snapshot",
# #     engine,
# #     if_exists="append",
# #     index=False
# # )

# # print(
# #     "asset_nodes_snapshot enrichie"
# # )

# # print(
# #     f"Snapshot date : {snapshot_date}"
# # )




# # Test pour récupérer et stocker les noeuf et ça marcheeeeeeeeeeeeeeeeee

# # from datetime import datetime
# # import pandas as pd

# # from services.asset_nodes import get_asset_nodes

# # snapshot_date = datetime.now()

# # print("\n===== HOUSINGS =====")

# # df_housings = pd.read_sql(
# #     "SELECT * FROM housings_current",
# #     engine
# # )

# # print(
# #     "Housings :",
# #     df_housings.shape
# # )

# # print("\n===== HOUSING PATH =====")

# # df_housing_path = get_asset_path(
# #     df_housings
# # )

# # print(
# #     "Housing Path :",
# #     df_housing_path.shape
# # )

# # print("\n===== NODES EXISTANTS =====")

# # df_nodes_existing = pd.read_sql(
# #     """
# #     SELECT path_reference
# #     FROM asset_nodes_current
# #     """,
# #     engine
# # )

# # print(
# #     "Nodes existants :",
# #     df_nodes_existing.shape
# # )

# # print("\n===== RECHERCHE NODES MANQUANTS =====")

# # nodes_to_fetch = (
# #     set(
# #         df_housing_path["path_reference"]
# #     )
# #     -
# #     set(
# #         df_nodes_existing["path_reference"]
# #     )
# # )

# # print(
# #     "Nodes à récupérer :",
# #     len(nodes_to_fetch)
# # )

# # if len(nodes_to_fetch) == 0:

# #     print(
# #         "Aucun noeud à récupérer"
# #     )

# # else:

# #     df_missing_nodes = pd.DataFrame(
# #         {
# #             "path_reference":
# #             list(nodes_to_fetch)
# #         }
# #     )

# #     print(
# #         "\n===== RECUPERATION NODES ====="
# #     )

# #     df_housing_nodes = get_asset_nodes(
# #         df_missing_nodes
# #     )

# #     print(
# #         "Housing Nodes :",
# #         df_housing_nodes.shape
# #     )

# #     print(
# #         "\n===== INSERT CURRENT ====="
# #     )

# #     df_housing_nodes.to_sql(
# #         "asset_nodes_current",
# #         engine,
# #         if_exists="append",
# #         index=False
# #     )

# #     print(
# #         "asset_nodes_current enrichie"
# #     )

# #     print(
# #         "\n===== SNAPSHOT ====="
# #     )

# #     df_housing_nodes_snapshot = (
# #         df_housing_nodes.copy()
# #     )

# #     df_housing_nodes_snapshot[
# #         "snapshot_date"
# #     ] = snapshot_date

# #     df_housing_nodes_snapshot.to_sql(
# #         "asset_nodes_snapshot",
# #         engine,
# #         if_exists="append",
# #         index=False
# #     )

# #     print(
# #         "asset_nodes_snapshot enrichie"
# #     )

# # print(
# #     f"Snapshot date : {snapshot_date}"
# # )

# # Fin de tesstttttttttttttttttttt


# # Test pour récupérer la liste des équipements
# # from datetime import datetime
# # from config import DB_URL
# # from sqlalchemy import create_engine

# # from services.equipments import (
# #     get_equipments
# # )


# # engine = create_engine(
# #     DB_URL
# # )


# # def main():

# #     print(
# #         "\n===== EQUIPMENTS ====="
# #     )

# #     df_equipment = (
# #         get_equipments()
# #     )

# #     print(
# #         f"Equipments : "
# #         f"{df_equipment.shape}"
# #     )

# #     print(
# #         "\n===== EQUIPMENT CURRENT ====="
# #     )

# #     df_equipment.to_sql(
# #         "equipment_current",
# #         engine,
# #         if_exists="replace",
# #         index=False
# #     )

# #     print(
# #         "equipment_current chargé"
# #     )

# #     print(
# #         "\n===== EQUIPMENT SNAPSHOT ====="
# #     )

# #     df_equipment_snapshot = (
# #         df_equipment.copy()
# #     )

# #     df_equipment_snapshot[
# #         "snapshot_date"
# #     ] = datetime.now()

# #     df_equipment_snapshot.to_sql(
# #         "equipment_snapshot",
# #         engine,
# #         if_exists="append",
# #         index=False
# #     )

# #     print(
# #         "equipment_snapshot chargé"
# #     )

# #     print(
# #         "\n===== FIN ====="
# #     )


# # if __name__ == "__main__":

# #     main()


# #  Test pour récupèrer asset path des équipements il marcheeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
# # import pandas as pd

# from sqlalchemy import create_engine

# from services.asset_path import (
#     get_asset_path
# )
# from config import DB_URL
# engine = create_engine(
#     DB_URL
# )


# # print(
# #     "\n===== EQUIPMENT CURRENT ====="
# # )

# # df_equipment = pd.read_sql(
# #     """
# #     SELECT *
# #     FROM equipment_current
# #     """,
# #     engine
# # )

# # print(
# #     f"Equipments : "
# #     f"{df_equipment.shape}"
# # )

# # print(
# #     "\n===== ASSET PATH EXISTANT ====="
# # )

# # df_asset_path_existing = pd.read_sql(
# #     """
# #     SELECT *
# #     FROM asset_path_current
# #     """,
# #     engine
# # )

# # before = len(
# #     df_asset_path_existing
# # )

# # print(
# #     f"Asset Path existant : "
# #     f"{df_asset_path_existing.shape}"
# # )

# # print(
# #     "\n===== CONSTRUCTION PATH ====="
# # )

# # df_asset_path_new = get_asset_path(
# #     df_equipment
# # )

# # print(
# #     f"Nouveaux chemins générés : "
# #     f"{df_asset_path_new.shape}"
# # )

# # print(
# #     "\n===== RECHERCHE DES NOUVEAUX CHEMINS ====="
# # )

# # existing_keys = set(
# #     zip(
# #         df_asset_path_existing[
# #             "asset_reference"
# #         ],
# #         df_asset_path_existing[
# #             "path_reference"
# #         ],
# #         df_asset_path_existing[
# #             "path_order"
# #         ]
# #     )
# # )

# # df_asset_path_to_insert = (
# #     df_asset_path_new[
# #         ~df_asset_path_new.apply(
# #             lambda r:
# #             (
# #                 r["asset_reference"],
# #                 r["path_reference"],
# #                 r["path_order"]
# #             )
# #             in existing_keys,
# #             axis=1
# #         )
# #     ]
# # )

# # print(
# #     f"Nouveaux chemins réels : "
# #     f"{len(df_asset_path_to_insert):,}"
# # )

# # print(
# #     f"Déjà présents : "
# #     f"{len(df_asset_path_new) - len(df_asset_path_to_insert):,}"
# # )

# # print(
# #     "\n===== INSERT CURRENT ====="
# # )

# # if len(df_asset_path_to_insert) > 0:

# #     df_asset_path_to_insert.to_sql(
# #         "asset_path_current",
# #         engine,
# #         if_exists="append",
# #         index=False,
# #         chunksize=5000,
# #         method="multi"
# #     )

# #     print(
# #         f"{len(df_asset_path_to_insert):,} lignes ajoutées"
# #     )

# # else:

# #     print(
# #         "Aucune ligne à ajouter"
# #     )

# # after = pd.read_sql(
# #     """
# #     SELECT COUNT(*) AS nb
# #     FROM asset_path_current
# #     """,
# #     engine
# # ).iloc[0]["nb"]

# # print(
# #     "\n===== CONTROLES ====="
# # )

# # print(
# #     f"Lignes avant : "
# #     f"{before:,}"
# # )

# # print(
# #     f"Lignes après : "
# #     f"{after:,}"
# # )

# # print(
# #     f"Lignes ajoutées : "
# #     f"{after-before:,}"
# # )

# # print(
# #     "\n===== SNAPSHOT ====="
# # )

# # df_asset_path_snapshot = (
# #     df_asset_path_to_insert.copy()
# # )

# # df_asset_path_snapshot[
# #     "snapshot_date"
# # ] = pd.Timestamp.utcnow()

# # if len(df_asset_path_snapshot) > 0:

# #     df_asset_path_snapshot.to_sql(
# #         "asset_path_snapshot",
# #         engine,
# #         if_exists="append",
# #         index=False,
# #         chunksize=5000,
# #         method="multi"
# #     )

# #     print(
# #         f"Snapshot ajouté : "
# #         f"{df_asset_path_snapshot.shape}"
# #     )

# # else:

# #     print(
# #         "Aucune ligne ajoutée au snapshot"
# #     )

# # print(
# #     "\n===== TERMINE ====="
# # )




# # fin de testttttttttttttttttttttt*



# # Testons les noeuds pour les équipement
# # from datetime import datetime
# # import pandas as pd

# # from services.asset_nodes import get_asset_nodes
# # from services.asset_path import get_asset_path


# # snapshot_date = datetime.now()

# # print("\n===== EQUIPMENTS =====")

# # df_equipment = pd.read_sql(
# #     """
# #     SELECT *
# #     FROM equipment_current
# #     """,
# #     engine
# # )

# # print(
# #     "Equipments :",
# #     df_equipment.shape
# # )

# # print("\n===== EQUIPMENT PATH =====")

# # df_equipment_path = get_asset_path(
# #     df_equipment
# # )

# # print(
# #     "Equipment Path :",
# #     df_equipment_path.shape
# # )

# # print("\n===== NODES EXISTANTS =====")

# # df_nodes_existing = pd.read_sql(
# #     """
# #     SELECT path_reference
# #     FROM asset_nodes_current
# #     """,
# #     engine
# # )

# # print(
# #     "Nodes existants :",
# #     df_nodes_existing.shape
# # )

# # print("\n===== RECHERCHE NODES MANQUANTS =====")

# # nodes_to_fetch = (

# #     set(
# #         df_equipment_path[
# #             "path_reference"
# #         ]
# #         .dropna()
# #     )

# #     -

# #     set(
# #         df_nodes_existing[
# #             "path_reference"
# #         ]
# #         .dropna()
# #     )

# # )

# # print(
# #     "Nodes à récupérer :",
# #     len(nodes_to_fetch)
# # )

# # if len(nodes_to_fetch) == 0:

# #     print(
# #         "Aucun noeud à récupérer"
# #     )

# # else:

# #     df_missing_nodes = pd.DataFrame(
# #         {
# #             "path_reference":
# #             list(nodes_to_fetch)
# #         }
# #     )

# #     print(
# #         "\n===== RECUPERATION NODES ====="
# #     )

# #     df_equipment_nodes = (
# #         get_asset_nodes(
# #             df_missing_nodes
# #         )
# #     )

# #     print(
# #         "Equipment Nodes :",
# #         df_equipment_nodes.shape
# #     )

# #     print(
# #         "\n===== INSERT CURRENT ====="
# #     )

# #     df_equipment_nodes.to_sql(
# #         "asset_nodes_current",
# #         engine,
# #         if_exists="append",
# #         index=False
# #     )

# #     print(
# #         "asset_nodes_current enrichie"
# #     )

# #     print(
# #         "\n===== SNAPSHOT ====="
# #     )

# #     df_equipment_nodes_snapshot = (
# #         df_equipment_nodes.copy()
# #     )

# #     df_equipment_nodes_snapshot[
# #         "snapshot_date"
# #     ] = snapshot_date

# #     df_equipment_nodes_snapshot.to_sql(
# #         "asset_nodes_snapshot",
# #         engine,
# #         if_exists="append",
# #         index=False
# #     )

# #     print(
# #         "asset_nodes_snapshot enrichie"
# #     )

# # print(
# #     f"Snapshot date : {snapshot_date}"
# # )





# # Passons au test des interventions
# # 


# # Autre test
# # from sqlalchemy import create_engine
# # from config import DB_URL
# # from services.operations_active import get_active_operations

# # engine = create_engine(DB_URL)

# # print("\n=================================")
# # print("     CHARGEMENT INTERVENTIONS")
# # print("=================================")
# # print("\nStatuts à charger :")
# # print("- open")
# # print("- pending")
# # print("- hold")

# # try:
# #     get_active_operations()

# #     print("\n=================================")
# #     print(" CHARGEMENT TERMINE AVEC SUCCES")
# #     print("=================================")

# # except Exception as e:
# #     print("\n=================================")
# #     print(" ERREUR DE CHARGEMENT")
# #     print("=================================")
# #     print(e)


























































# # from sqlalchemy import create_engine, text
# # from config import DB_URL
# # from services.contracts import get_contracts

# # engine = create_engine(DB_URL)

# # df_contracts = get_contracts()

# # with engine.begin() as conn:
# #     conn.execute(
# #         text("DELETE FROM contracts_current")
# #     )

# # df_contracts.to_sql(
# #     "contracts_current",
# #     engine,
# #     if_exists="append",
# #     index=False
# # )



# # import pandas as pd

# # from services.programs import get_programs
# # from database.upsert import upsert_dataframe
# # from config import DB_URL
# # engine = create_engine(DB_URL)

# # print("\n===== PROGRAMMES =====")

# # df_programs = get_programs()

# # print(df_programs.shape)

# # upsert_dataframe(
# #     df=df_programs,
# #     table_name="programs_current",
# #     key_column="reference",
# #     engine=engine
# # )
# # import pandas as pd

# # from services.programs import get_programs
# # from database.upsert import upsert_dataframe
# # from config import DB_URL
# # engine = create_engine(DB_URL)

# # df_programs_without_path = pd.read_sql(
# #     """
# #     SELECT p.*
# #     FROM programs_current p
# #     LEFT JOIN (
# #         SELECT DISTINCT asset_reference
# #         FROM asset_path_current
# #     ) ap
# #         ON p.reference = ap.asset_reference
# #     WHERE ap.asset_reference IS NULL
# #     """,
# #     engine
# # )
# # print(df_programs_without_path.shape)

# # print("\n===== ASSET PATH =====")

# # df_asset_path = get_asset_path(
# #     df_programs_without_path
# # )

# # print(
# #     f"Asset Path : {df_asset_path.shape}"
# # )

# # upsert_dataframe(
# #     df=df_asset_path,
# #     table_name="asset_path_current",
# #     key_columns=[
# #         "asset_reference",
# #         "path_reference"
# #     ],
# #     engine=engine
# # )

# # print(
# #     "Asset Path mis à jour"
# # )







# import pandas as pd

# from services.asset_nodes import get_asset_nodes

# from config import DB_URL
# engine = create_engine(DB_URL)
# from database.upsert import upsert_dataframe


# # print("\n===== PATHS SANS NODE =====")

# # df_missing_paths = pd.read_sql(
# #     """
# #     SELECT DISTINCT ap.path_reference
# #     FROM asset_path_current ap

# #     LEFT JOIN asset_nodes_current an
# #         ON ap.path_reference = an.path_reference

# #     WHERE an.path_reference IS NULL
# #     """,
# #     engine
# # )

# # print(
# #     f"Nodes manquants : {df_missing_paths.shape}"
# # )

# # if not df_missing_paths.empty:

# #     df_nodes = get_asset_nodes(
# #         df_missing_paths
# #     )

# #     print(
# #         f"Nodes récupérés : "
# #         f"{df_nodes.shape}"
# #     )

# #     upsert_dataframe(
# #         df=df_nodes,
# #         table_name="asset_nodes_current",
# #         key_columns=["path_reference"],
# #         engine=engine
# #     )

# #     print(
# #         "Nodes mis à jour"
# #     )

# # else:

# #     print(
# #         "Aucun node manquant"
# #     )


# # from services.housings import get_housings

# # df_housings = get_housings()

# # upsert_dataframe(
# #     df=df_housings,
# #     table_name="housings_current",
# #     key_columns=["reference"],
# #     engine=engine
# # )


# # print("\n===== HOUSINGS SANS ASSET PATH =====")

# # df_housings_without_path = pd.read_sql(
# #     """
# #     SELECT h.*
# #     FROM housings_current h

# #     LEFT JOIN (
# #         SELECT DISTINCT asset_reference
# #         FROM asset_path_current
# #     ) ap
# #         ON h.reference = ap.asset_reference

# #     WHERE ap.asset_reference IS NULL
# #     """,
# #     engine
# # )

# # print(
# #     f"Housings sans asset path : "
# #     f"{df_housings_without_path.shape}"
# # )

# # if not df_housings_without_path.empty:

# #     print("\n===== CONSTRUCTION ASSET PATH =====")

# #     df_asset_path = get_asset_path(
# #         df_housings_without_path
# #     )

# #     print(
# #         f"Asset Path : "
# #         f"{df_asset_path.shape}"
# #     )

# #     upsert_dataframe(
# #         df=df_asset_path,
# #         table_name="asset_path_current",
# #         key_columns=[
# #             "asset_reference",
# #             "path_reference"
# #         ],
# #         engine=engine
# #     )

# #     print(
# #         "Asset Path mis à jour"
# #     )

# # else:

# #     print(
# #         "Tous les logements ont déjà un asset path"
# #     )



# # print("\n===== PATHS SANS NODE =====")

# # df_missing_paths = pd.read_sql(
# #     """
# #     SELECT DISTINCT ap.path_reference
# #     FROM asset_path_current ap

# #     LEFT JOIN asset_nodes_current an
# #         ON ap.path_reference = an.path_reference

# #     WHERE an.path_reference IS NULL
# #     """,
# #     engine
# # )

# # print(
# #     f"Nodes manquants : "
# #     f"{df_missing_paths.shape}"
# # )

# # if not df_missing_paths.empty:

# #     df_nodes = get_asset_nodes(
# #         df_missing_paths
# #     )

# #     print(
# #         f"Nodes récupérés : "
# #         f"{df_nodes.shape}"
# #     )

# #     upsert_dataframe(
# #         df=df_nodes,
# #         table_name="asset_nodes_current",
# #         key_columns=["path_reference"],
# #         engine=engine
# #     )

# #     print(
# #         "Asset Nodes mis à jour"
# #     )

# # else:

# #     print(
# #         "Aucun node manquant"
# #     )


# # from services.equipments import get_equipments
# # from database.upsert import upsert_dataframe


# # print("\n===== EQUIPMENTS =====")

# # df_equipment = get_equipments()

# # print(
# #     f"Equipments : {df_equipment.shape}"
# # )

# # upsert_dataframe(
# #     df=df_equipment,
# #     table_name="equipment_current",
# #     key_columns=["reference"],
# #     engine=engine
# # )

# # print(
# #     "Equipments mis à jour"
# # )

# # import pandas as pd



# # print("\n===== EQUIPMENTS SANS ASSET PATH =====")

# # df_equipment_without_path = pd.read_sql(
# #     """
# #     SELECT e.*
# #     FROM equipment_current e

# #     LEFT JOIN (
# #         SELECT DISTINCT asset_reference
# #         FROM asset_path_current
# #     ) ap
# #         ON e.reference = ap.asset_reference

# #     WHERE ap.asset_reference IS NULL
# #     """,
# #     engine
# # )

# # print(
# #     f"Equipments sans asset path : "
# #     f"{df_equipment_without_path.shape}"
# # )

# # from services.asset_path import get_asset_path

# # df_asset_path = get_asset_path(
# #     df_equipment_without_path
# # )

# # print(
# #     f"Asset Path : {df_asset_path.shape}"
# # )

# # upsert_dataframe(
# #     df=df_asset_path,
# #     table_name="asset_path_current",
# #     key_columns=[
# #         "asset_reference",
# #         "path_reference"
# #     ],
# #     engine=engine
# # )
# # import pandas as pd

# # from services.asset_nodes import get_asset_nodes

# # from database.upsert import upsert_dataframe


# # print("\n===== PATHS SANS NODE =====")

# # df_missing_paths = pd.read_sql(
# #     """
# #     SELECT DISTINCT ap.path_reference
# #     FROM asset_path_current ap

# #     LEFT JOIN asset_nodes_current an
# #         ON ap.path_reference = an.path_reference

# #     WHERE an.path_reference IS NULL
# #     """,
# #     engine
# # )

# # print(
# #     f"Nodes manquants : "
# #     f"{df_missing_paths.shape}"
# # )

# # if not df_missing_paths.empty:

# #     df_nodes = get_asset_nodes(
# #         df_missing_paths
# #     )

# #     print(
# #         f"Nodes récupérés : "
# #         f"{df_nodes.shape}"
# #     )

# #     upsert_dataframe(
# #         df=df_nodes,
# #         table_name="asset_nodes_current",
# #         key_columns=["path_reference"],
# #         engine=engine
# #     )

# #     print(
# #         "Asset Nodes mis à jour"
# #     )

# # else:

# #     print(
# #         "Aucun node manquant"
# #     )


# # import time
# # from api.client import get


# # PAGES = [
# #     8700,
# #     8801,
# #     8820,
# #     8830,
# #     8849,
# #     8900,
# #     9000
# # ]


# # for page in PAGES:

# #     print(f"\n===== TEST PAGE {page} =====")

# #     try:

# #         data = get(
# #             "/operations/v2/operations",
# #             params={
# #                 "status": "closed",
# #                 "page": page,
# #                 "perPage": 100
# #             },
# #             retries=3,
# #             timeout=(10, 120)
# #         )

# #         operations = (
# #             data
# #             .get("_embedded", {})
# #             .get("operations", [])
# #         )

# #         print(f"OK page {page} : {len(operations)} lignes")

# #     except Exception as e:

# #         print(f"ECHEC page {page}")
# #         print(e)

# #     time.sleep(5)