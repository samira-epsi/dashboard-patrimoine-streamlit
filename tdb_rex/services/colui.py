"""Menu déroulant sur l'en-tête de chaque colonne d'une liste, comme dans Excel : tri, filtre par valeurs, recherche, renseigné ou non.
L'état vit dans st.session_state (clés cm_<liste>_...) ; la liste lit l'état puis le transmet à services.colf.appliquer."""
import re
import streamlit as st
from services import colf, picker


def _poids(cols_css):
    return [float(x) for x in re.findall(r"([\d.]+)fr", cols_css)]


def etat(liste, cles):
    """Lit l'état courant des filtres et du tri de la liste (utilisable avant ou après le dessin de l'en-tête)."""
    ss = st.session_state
    v = {k: ss.get(f"cm_{liste}_v_{k}") or [] for k in cles}
    t = {k: ss.get(f"cm_{liste}_t_{k}") or "" for k in cles}
    n = {k: ss.get(f"cm_{liste}_n_{k}") or [] for k in cles}
    return {"v": {k: x for k, x in v.items() if x}, "t": {k: x for k, x in t.items() if x.strip()},
            "n": {k: x for k, x in n.items() if x}, "tri": ss.get(f"cm_{liste}_tri")}


def _effacer(liste, k):
    ss = st.session_state
    for kind in ("v", "t", "n"):
        ss.pop(f"cm_{liste}_{kind}_{k}", None)
        ss[f"cm_{liste}_{kind}_{k}"] = "" if kind == "t" else []
    if (ss.get(f"cm_{liste}_tri") or (None,))[0] == k:
        ss[f"cm_{liste}_tri"] = None


def _trier(liste, k, sens):
    st.session_state[f"cm_{liste}_tri"] = (k, sens)


def tout_effacer(liste, cles):
    for k in cles:
        _effacer(liste, k)


def en_tete(liste, colonnes, cols_css, valeurs=None):
    """Dessine la ligne d'en-têtes alignée sur la grille de la liste.
    colonnes : [(clé de colf.COLS, libellé affiché)] ; valeurs : {clé: {valeur: libellé}} pour le filtre par valeurs.
    Retourne l'état courant (à passer à colf.appliquer)."""
    valeurs = valeurs or {}
    cles = [k for k, _ in colonnes]
    st.session_state.setdefault(f"cm_{liste}_tri", None)
    ss = st.session_state
    with st.container(key=f"colhead_{liste}"):
        zones = st.columns(_poids(cols_css), gap="small", vertical_alignment="center")
        for zone, (k, label) in zip(zones, colonnes):
            c = colf.COLS[k]
            actif = bool(ss.get(f"cm_{liste}_v_{k}") or (ss.get(f"cm_{liste}_t_{k}") or "").strip() or ss.get(f"cm_{liste}_n_{k}")
                         or (ss.get(f"cm_{liste}_tri") or (None,))[0] == k)
            with zone, st.container(key=f"ch_{liste}_{k}"):
                menu = st.popover(label.upper(), use_container_width=True)
                if actif:
                    st.markdown('<span class="chon"></span>', unsafe_allow_html=True)
                with menu:
                    if c.get("tri"):
                        asc, desc = colf.SENS[c["sens"]]
                        cur = ss.get(f"cm_{liste}_tri")
                        st.button(("✓ " if cur == (k, "asc") else "") + asc, key=f"cm_{liste}_a_{k}", on_click=_trier, args=(liste, k, "asc"), width="stretch")
                        st.button(("✓ " if cur == (k, "desc") else "") + desc, key=f"cm_{liste}_d_{k}", on_click=_trier, args=(liste, k, "desc"), width="stretch")
                    if k in valeurs:
                        picker.select(f"cm_{liste}_v_{k}", valeurs[k], placeholder="Rechercher une valeur...")
                    if c.get("t"):
                        st.text_input("Contient", key=f"cm_{liste}_t_{k}", placeholder="Contient...")
                    if c.get("n"):
                        st.multiselect("Présence", list(c["n"]), key=f"cm_{liste}_n_{k}", placeholder="Tous")
                    st.button("Effacer le filtre", key=f"cm_{liste}_x_{k}", on_click=_effacer, args=(liste, k), icon=":material/filter_alt_off:",
                              disabled=not actif, width="stretch")
    return etat(liste, cles)


def resume(liste, cles):
    """Nombre de colonnes filtrées, et bouton pour tout effacer (affiché au-dessus de la liste)."""
    e = etat(liste, cles)
    n = len(e["v"]) + len(e["t"]) + len(e["n"])
    return n, e