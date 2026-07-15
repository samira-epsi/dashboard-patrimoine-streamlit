from __future__ import annotations

# =====================================================
# PALETTE ET STYLE DES GRAPHIQUES 3F
# =====================================================

C_RED = "#E5114D"
C_NAVY = "#173B69"
C_VIOLET = "#432ABD"
C_YELLOW = "#FFDC55"
C_TEAL = "#008080"
C_BLUE = "#0074FF"
C_BLUE_LIGHT = "#80CDFF"
C_PINK = "#FFB7E3"

C_RED_DARK = "#BF0F40"
C_NAVY_DEEP = "#102A4C"
C_PINK_SOFT = "#FFF3FA"
C_BLUE_SOFT = "#EFF9FF"
C_CANVAS = "#F7FAFD"
C_GRID = "#E8EEF5"
C_INK = "#17243A"


PALETTE_3F_GRAPHIQUES = [
    "#173B69",  # bleu marine
    "#63B9DF",  # bleu ciel
    "#2F7C6D",  # vert profond
    "#432ABD",  # violet
    "#E89BC7",  # rose poudré
    "#F4D84E",  # jaune
    "#D83B55",  # rouge framboise
    "#4C6FB1",  # bleu moyen
]


PLOTLY_FR_DICTIONARY = {
    "Download plot as a PNG": "Télécharger en PNG",
    "Download plot": "Télécharger le graphique",
    "Zoom": "Zoomer",
    "Pan": "Déplacer",
    "Zoom in": "Zoom avant",
    "Zoom out": "Zoom arrière",
    "Autoscale": "Ajustement automatique",
    "Reset axes": "Réinitialiser les axes",
    "Reset camera to default": "Réinitialiser la vue",
    "Reset camera to last save": "Restaurer la dernière vue",
    "Orbit rotation": "Rotation orbitale",
    "Turntable rotation": "Rotation horizontale",
    "Show closest data on hover": "Afficher la donnée la plus proche",
    "Compare data on hover": "Comparer les données",
    "Toggle Spike Lines": "Afficher ou masquer les lignes de repère",
    "Snapshot succeeded": "Image téléchargée",
    "Sorry, there was a problem downloading your snapshot!": (
        "Le téléchargement de l’image a échoué."
    ),
}


def config_plotly(nom_fichier: str, afficher_barre: bool = True) -> dict:
    return {
        "displayModeBar": afficher_barre,
        "displaylogo": False,
        "responsive": True,
        "locale": "fr",
        "locales": {
            "fr": {
                "dictionary": PLOTLY_FR_DICTIONARY,
                "format": {
                    "days": [
                        "dimanche", "lundi", "mardi", "mercredi",
                        "jeudi", "vendredi", "samedi",
                    ],
                    "shortDays": ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."],
                    "months": [
                        "janvier", "février", "mars", "avril", "mai", "juin",
                        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
                    ],
                    "shortMonths": [
                        "janv.", "févr.", "mars", "avr.", "mai", "juin",
                        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
                    ],
                    "date": "%d/%m/%Y",
                },
            }
        },
        "modeBarButtonsToRemove": [
            "select2d",
            "lasso2d",
            "autoScale2d",
            "toggleSpikelines",
        ],
        "toImageButtonOptions": {
            "format": "png",
            "filename": nom_fichier,
            "height": 900,
            "width": 1600,
            "scale": 2,
        },
    }


def _layout_plotly(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=24, t=10, b=18),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color=C_INK),
        showlegend=False,
    )
    return fig
