# Code pour maj et executer le service.contract

from sqlalchemy import create_engine, text
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from config import DB_URL
from services.contracts import get_contracts

engine = create_engine(DB_URL)

df_contracts = get_contracts()

with engine.begin() as conn:
    conn.execute(
        text("DELETE FROM contracts_current")
    )

df_contracts.to_sql(
    "contracts_current",
    engine,
    if_exists="append",
    index=False
)


# //////////////////////////Fin


# Code Maj Code De Prestation

import pandas as pd
from sqlalchemy import create_engine

from services.asset_path import (
    get_asset_path
)
from config import DB_URL
engine = create_engine(
    DB_URL
)

from services.service_codes import (
    get_service_codes
)

from database.loader import (
    load_current,
    load_snapshot
)

# Lecture des contrats depuis PostgreSQL

df_contracts = pd.read_sql(
    """
    SELECT reference
    FROM contracts_current
    """,
    engine
)

contract_references = (
    df_contracts["reference"]
    .dropna()
    .astype(str)
    .tolist()
)

# Extraction des codes prestations

df_service_codes = get_service_codes(
    contract_references
)

print(df_service_codes.shape)

print(df_service_codes.head())

# Chargement PostgreSQL

load_current(
    df_service_codes,
    "service_codes_current",
    engine
)

load_snapshot(
    df_service_codes,
    "service_codes_snapshot",
    engine
)

print("Chargement terminé")

# Fin /////////////////////////////////


# Code pour récupérer et mettre à jour la table programme
import pandas as pd

from services.programs import get_programs
from database.upsert import upsert_dataframe
from config import DB_URL
engine = create_engine(DB_URL)

print("\n===== PROGRAMMES =====")

df_programs = get_programs()

print(df_programs.shape)

upsert_dataframe(
    df=df_programs,
    table_name="programs_current",
    key_columns= ["reference"],
    engine=engine
)

# Fin /////////////////////////

# Code pour mettre à jour la table asset path si y'a de nouveaux programmes

import pandas as pd

from services.programs import get_programs
from database.upsert import upsert_dataframe
from config import DB_URL
engine = create_engine(DB_URL)

df_programs_without_path = pd.read_sql(
    """
    SELECT p.*
    FROM programs_current p
    LEFT JOIN (
        SELECT DISTINCT asset_reference
        FROM asset_path_current
    ) ap
        ON p.reference = ap.asset_reference
    WHERE ap.asset_reference IS NULL
    """,
    engine
)
print(df_programs_without_path.shape)

print("\n===== ASSET PATH =====")

df_asset_path = get_asset_path(
    df_programs_without_path
)

print(
    f"Asset Path : {df_asset_path.shape}"
)

upsert_dataframe(
    df=df_asset_path,
    table_name="asset_path_current",
    key_columns=[
        "asset_reference",
        "path_reference"
    ],
    engine=engine
)

print(
    "Asset Path mis à jour"
)

# fin ///////////////////////////////////////////////

# Code pour mettre à jour la table asset node pour les nouveaux programme

import pandas as pd

from services.asset_nodes import get_asset_nodes

from config import DB_URL
engine = create_engine(DB_URL)
from database.upsert import upsert_dataframe


print("\n===== PATHS SANS NODE =====")

df_missing_paths = pd.read_sql(
    """
    SELECT DISTINCT ap.path_reference
    FROM asset_path_current ap

    LEFT JOIN asset_nodes_current an
        ON ap.path_reference = an.path_reference

    WHERE an.path_reference IS NULL
    """,
    engine
)

print(
    f"Nodes manquants : {df_missing_paths.shape}"
)

if not df_missing_paths.empty:

    df_nodes = get_asset_nodes(
        df_missing_paths
    )

    print(
        f"Nodes récupérés : "
        f"{df_nodes.shape}"
    )

    upsert_dataframe(
        df=df_nodes,
        table_name="asset_nodes_current",
        key_columns=["path_reference"],
        engine=engine
    )

    print(
        "Nodes mis à jour"
    )

else:

    print(
        "Aucun node manquant"
    )

    # Fin////////////////////////////////////////////////////

    # Code pour récupèrer les logements

import pandas as pd

from services.asset_nodes import get_asset_nodes

from config import DB_URL
engine = create_engine(DB_URL)
from database.upsert import upsert_dataframe

from services.housings import get_housings

df_housings = get_housings()

upsert_dataframe(
    df=df_housings,
    table_name="housings_current",
    key_columns=["reference"],
    engine=engine
)


# Fin///////////////////////////////////////////////
# Code pour assets path de logements

import pandas as pd

from services.asset_nodes import get_asset_nodes

from config import DB_URL
engine = create_engine(DB_URL)
from database.upsert import upsert_dataframe

print("\n===== HOUSINGS SANS ASSET PATH =====")

df_housings_without_path = pd.read_sql(
    """
    SELECT h.*
    FROM housings_current h

    LEFT JOIN (
        SELECT DISTINCT asset_reference
        FROM asset_path_current
    ) ap
        ON h.reference = ap.asset_reference

    WHERE ap.asset_reference IS NULL
    """,
    engine
)

print(
    f"Housings sans asset path : "
    f"{df_housings_without_path.shape}"
)

if not df_housings_without_path.empty:

    print("\n===== CONSTRUCTION ASSET PATH =====")

    df_asset_path = get_asset_path(
        df_housings_without_path
    )

    print(
        f"Asset Path : "
        f"{df_asset_path.shape}"
    )

    upsert_dataframe(
        df=df_asset_path,
        table_name="asset_path_current",
        key_columns=[
            "asset_reference",
            "path_reference"
        ],
        engine=engine
    )

    print(
        "Asset Path mis à jour"
    )

else:

    print(
        "Tous les logements ont déjà un asset path"
    )
    # Fin/////////////////////////////////////////////////

    # Code pour les asset nodes logement
import pandas as pd

from services.asset_nodes import get_asset_nodes

from config import DB_URL
engine = create_engine(DB_URL)
from database.upsert import upsert_dataframe
print("\n===== PATHS SANS NODE =====")

df_missing_paths = pd.read_sql(
    """
    SELECT DISTINCT ap.path_reference
    FROM asset_path_current ap

    LEFT JOIN asset_nodes_current an
        ON ap.path_reference = an.path_reference

    WHERE an.path_reference IS NULL
    """,
    engine
)

print(
    f"Nodes manquants : "
    f"{df_missing_paths.shape}"
)

if not df_missing_paths.empty:

    df_nodes = get_asset_nodes(
        df_missing_paths
    )

    print(
        f"Nodes récupérés : "
        f"{df_nodes.shape}"
    )

    upsert_dataframe(
        df=df_nodes,
        table_name="asset_nodes_current",
        key_columns=["path_reference"],
        engine=engine
    )

    print(
        "Asset Nodes mis à jour"
    )

else:

    print(
        "Aucun node manquant"
    )

    
# FIN////////////////////////////////////////

# Code pour update les équipements
# Y'a les autres import de d'habitude mais asy

from services.equipments import get_equipments
from database.upsert import upsert_dataframe


print("\n===== EQUIPMENTS =====")

df_equipment = get_equipments()

print(
    f"Equipments : {df_equipment.shape}"
)

upsert_dataframe(
    df=df_equipment,
    table_name="equipment_current",
    key_columns=["reference"],
    engine=engine
)

print(
    "Equipments mis à jour"
)

# Fin/////////////////////////////

# Code pour asset path equipment
import pandas as pd



print("\n===== EQUIPMENTS SANS ASSET PATH =====")

df_equipment_without_path = pd.read_sql(
    """
    SELECT e.*
    FROM equipment_current e

    LEFT JOIN (
        SELECT DISTINCT asset_reference
        FROM asset_path_current
    ) ap
        ON e.reference = ap.asset_reference

    WHERE ap.asset_reference IS NULL
    """,
    engine
)

print(
    f"Equipments sans asset path : "
    f"{df_equipment_without_path.shape}"
)

from services.asset_path import get_asset_path

df_asset_path = get_asset_path(
    df_equipment_without_path
)

print(
    f"Asset Path : {df_asset_path.shape}"
)

upsert_dataframe(
    df=df_asset_path,
    table_name="asset_path_current",
    key_columns=[
        "asset_reference",
        "path_reference"
    ],
    engine=engine
)
import pandas as pd

from services.asset_nodes import get_asset_nodes

from database.upsert import upsert_dataframe


print("\n===== PATHS SANS NODE =====")

df_missing_paths = pd.read_sql(
    """
    SELECT DISTINCT ap.path_reference
    FROM asset_path_current ap

    LEFT JOIN asset_nodes_current an
        ON ap.path_reference = an.path_reference

    WHERE an.path_reference IS NULL
    """,
    engine
)

print(
    f"Nodes manquants : "
    f"{df_missing_paths.shape}"
)

if not df_missing_paths.empty:

    df_nodes = get_asset_nodes(
        df_missing_paths
    )

    print(
        f"Nodes récupérés : "
        f"{df_nodes.shape}"
    )

    upsert_dataframe(
        df=df_nodes,
        table_name="asset_nodes_current",
        key_columns=["path_reference"],
        engine=engine
    )

    print(
        "Asset Nodes mis à jour"
    )

else:

    print(
        "Aucun node manquant"
    )