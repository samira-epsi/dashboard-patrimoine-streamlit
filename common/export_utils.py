from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st


def dataframe_download(
    label: str,
    df: pd.DataFrame,
    filename: str,
    cle: str | None = None,
):
    if df.empty:
        return

    export = df.copy()

    for colonne in export.columns:
        serie = export[colonne]
        if pd.api.types.is_datetime64_any_dtype(serie):
            serie = pd.to_datetime(serie, errors="coerce")
            try:
                serie = serie.dt.tz_localize(None)
            except (TypeError, AttributeError):
                pass
            export[colonne] = serie

    fichier = BytesIO()
    with pd.ExcelWriter(fichier, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name="Données")
        feuille = writer.sheets["Données"]
        feuille.freeze_panes = "A2"
        feuille.auto_filter.ref = feuille.dimensions

        for cellules in feuille.columns:
            valeurs = [
                len(str(cellule.value)) if cellule.value is not None else 0
                for cellule in cellules
            ]
            largeur = min(max(valeurs, default=0) + 3, 55)
            feuille.column_dimensions[cellules[0].column_letter].width = largeur

    fichier.seek(0)
    nom_excel = filename.rsplit(".", 1)[0] + ".xlsx"

    st.download_button(
        label,
        data=fichier.getvalue(),
        file_name=nom_excel,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=cle,
        width="stretch",
    )
