"""Configuration de la Vue globale REX."""
# Palette alignée sur la maquette
BRAND = "#E5114D"        # courbe curatif, accents
BRAND_DARK = "#A92F5E"   # barres des classements
PLUM = "#8E4A8A"         # courbe préventif
INK = "#14131F"
PAGE_SIZE = 100

# Nombre de lignes affichées dans les classements (zone de défilement)
ZONES_LIMIT = 200
EQUIPMENTS_LIMIT = 50

# Les indicateurs suivants nécessitent une validation métier avant activation.
# Passer à True uniquement quand la requête correspondante est branchée dans services/queries.py.
PREVENTIVE_RULE_VALIDATED = False
REPORT_RULE_VALIDATED = False
