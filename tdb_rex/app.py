"""Vue globale REX 3F. Exécuter : streamlit run app.py"""
import re
from services import picker
from datetime import date, datetime, timedelta
from html import escape
from io import BytesIO
from pathlib import Path
import base64
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from config import BRAND, BRAND_DARK, PLUM, PAGE_SIZE, ZONES_LIMIT, EQUIPMENTS_LIMIT
BRAND_DARK, PLUM = "#E5114D", "#173B69"  # palette unifiée : rouge, marine
from database import check_connection, read_sql
from services import queries as q
from services import fr
from services import colf, colui

st.set_page_config(page_title="Pilotage REX | Vue globale", page_icon="📊", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(f"<style>{(Path(__file__).parent / 'styles' / 'theme.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)
from services.loader import render_loader  # noqa: E402
render_loader()
from services.traduction import render_traduction  # noqa: E402
render_traduction()

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_LONG = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre",
             "Octobre", "Novembre", "Décembre"]
FEMININ = {"Société", "Agence"}
NBSP = "\u00a0"


# ---------------------------------------------------------------- utilitaires
def as_int(value):
    return int(value) if pd.notna(value) else 0


def as_pct(n, d):
    return 100 * n / d if d else None


def fr_int(n):
    return f"{int(n):,}".replace(",", NBSP)


def fr_pct(x, decimals=1):
    return f"{x:.{decimals}f}".replace(".", ",") + NBSP + "%"


def fr_date(d, fmt="%d/%m/%Y"):
    return pd.Timestamp(d).strftime(fmt) if pd.notna(d) else ""


def tip(text):
    """Bulle d'aide au survol. \\n dans le texte = retour à la ligne."""
    return f'<span class="info" tabindex="0" data-tip="{escape(text, quote=True).replace(chr(10), "&#10;")}">i</span>'


def card_title(title, description, info=None):
    extra = tip(info) if info else ""
    st.markdown(f'<div class="card-title">{escape(title)}{extra}</div>'
                f'<div class="card-desc">{escape(description)}</div>', unsafe_allow_html=True)


def _flip_list(skey):
    st.session_state[skey] = not st.session_state.get(skey, False)


def list_header(key, title, description, info=None, default=False):
    """Titre d'une liste d'interventions avec un bouton Afficher / Masquer. Retourne True si la liste est ouverte :
    fermée, elle n'est pas chargée (la base n'est pas interrogée)."""
    skey = f"lopen_{key}"
    ouverte = st.session_state.get(skey, default)
    st.session_state.setdefault(skey, default)
    h1, h2 = st.columns([6, 1.5], vertical_alignment="center")
    with h1:
        card_title(title, description, info)
    with h2:
        st.button("Masquer" if ouverte else "Afficher", key=f"lbtn_{key}", on_click=_flip_list, args=(skey,), width="stretch",
                  icon=":material/expand_less:" if ouverte else ":material/expand_more:", type="tertiary")
    return ouverte


def note(message):
    st.markdown(f'<div class="note">{escape(message)}</div>', unsafe_allow_html=True)


def naive_dates(df):
    """Excel refuse les dates avec fuseau : conversion en heure de Paris puis suppression du fuseau.
    Gère aussi les colonnes de type object (fuseaux mixtes été/hiver renvoyés par PostgreSQL)."""
    df = df.copy()
    for col in df.columns:
        series = df[col]
        if isinstance(series.dtype, pd.DatetimeTZDtype):
            df[col] = series.dt.tz_convert("Europe/Paris").dt.tz_localize(None)
        elif series.dtype == object:
            sample = series.dropna()
            if len(sample) and isinstance(sample.iloc[0], datetime) and sample.iloc[0].tzinfo is not None:
                df[col] = pd.to_datetime(series, utc=True).dt.tz_convert("Europe/Paris").dt.tz_localize(None)
    return df


def _fichier(df, fmt):
    buffer = BytesIO()
    if fmt == "CSV":
        df.to_csv(buffer, index=False, sep=";", encoding="utf-8-sig")  # séparateur « ; » et BOM : s'ouvre directement dans Excel en français
    else:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="REX")
    return buffer.getvalue()


def download_xlsx(df, file_name, key, label="Exporter", loader=None, sig=None, total=None):
    """Bouton d'export avec choix des colonnes. Chaque tableau du tableau de bord passe par ici.
    loader : fonction sans argument qui renvoie TOUS les résultats filtrés (sinon on exporte ce qui est affiché) ; sig : signature des filtres,
    pour ne pas réutiliser un export préparé avec d'autres filtres."""
    table = fr.traduire(naive_dates(df))
    prete = st.session_state.get(f"xd_{key}")
    with st.popover(label, icon=":material/download:", width="content" if label else "stretch", help="Choisir les colonnes à exporter"):
        st.markdown('<div class="xp-t">Exporter</div>', unsafe_allow_html=True)
        tout = False
        if loader is not None:
            tout_lbl = "Tous les résultats filtrés" + (f" ({fr_int(total)})" if total is not None else "")
            portee = st.radio("Lignes", [f"Page affichée ({fr_int(len(table))})", tout_lbl], key=f"xs_{key}", label_visibility="collapsed")
            tout = portee.startswith("Tous")
            if tout:
                if prete is not None and prete.get("sig") == sig:
                    table = fr.traduire(naive_dates(prete["df"]))
                else:
                    if st.button("Préparer l'export complet", key=f"xp_{key}", icon=":material/sync:", width="stretch"):
                        with st.spinner("Préparation..."):
                            st.session_state[f"xd_{key}"] = {"sig": sig, "df": loader()}
                        st.rerun()
                    nb = f"{fr_int(min(total, 100000))} lignes" if total is not None else "Jusqu'à 100 000 lignes"
                    lim = " (limite de 100 000 lignes atteinte, affine les filtres pour tout exporter)" if (total is not None and total > 100000) else ""
                    st.caption(nb + " à préparer" + lim + ". Cela peut prendre quelques secondes.")
        noms = [str(c) for c in table.columns]
        cle = f"xc_{key}_{abs(hash(tuple(noms)))}"
        choisies = st.multiselect("Colonnes", noms, default=noms, key=cle, placeholder="Toutes les colonnes")
        fmt = st.radio("Format", ["Excel", "CSV"], horizontal=True, key=f"xf_{key}", label_visibility="collapsed")
        pret = (not tout) or (prete is not None and prete.get("sig") == sig)
        sortie = table[[c for c in noms if c in (choisies or noms)]]
        nb_lignes = len(sortie) if pret else (min(total, 100000) if total is not None else 0)
        st.caption(f"{len(sortie.columns)} colonne{'s' if len(sortie.columns) > 1 else ''} sur {len(noms)}, {fr_int(nb_lignes)} ligne{'s' if nb_lignes > 1 else ''}"
                   + ("" if pret else " (à préparer)"))
        st.download_button("Télécharger", data=_fichier(sortie, fmt) if pret else b"", file_name=file_name.rsplit(".", 1)[0] + (".csv" if fmt == "CSV" else ".xlsx"),
                           key=f"xdl_{key}", icon=":material/download:", disabled=not pret or not len(sortie.columns), width="stretch", type="primary",
                           mime="text/csv" if fmt == "CSV" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


ICON = {
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "check": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M9 16l2 2 4-4"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 15h6"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>'
            '<rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "users": '<circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1"/>'
             '<path d="M16 4a4 4 0 0 1 0 8M22 21v-1a6 6 0 0 0-4-5.6"/>',
    "wrench": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.2L3 17.8V21h3.2l6.3-6.3a4 4 0 0 0 5.2-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
}


def svg(name, size=20):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICON[name]}</svg>')


LOGO_PATH = Path(__file__).resolve().parent / "assets" / "LOGO 3F.png"

logo_base64 = base64.b64encode(
    LOGO_PATH.read_bytes()
).decode("utf-8")

LOGO = f'<img src="data:image/png;base64,{logo_base64}" class="brand-logo" alt="Logo 3F">'

# ---------------------------------------------------------------- graphiques
# Indicateurs de l'évolution : clé -> (libellé, numérateur, dénominateur, couleur, base en toutes lettres, couleur translucide)
TREND_IND = {
    "pec": ("Prise en charge hors délai", "hors_delai", "comparables", "#E5114D", "curatives comparables", "rgba(229,17,77,%s)"),
    "res": ("Résolution hors délai", "res_hors_delai", "res_comparables", "#0074FF", "curatives comparables en résolution", "rgba(0,116,255,%s)"),
    "real": ("Préventif réalisé", "realises", "prevus", "#008080", "passages prévus", "rgba(0,128,128,%s)"),
    "retard": ("Préventif en retard", "retard", "jugeables", "#F5A524", "passages jugeables", "rgba(245,165,36,%s)"),
    "nonreal": ("Préventif non réalisé", "non_realises", "prevus", "#173B69", "passages prévus", "rgba(23,59,105,%s)"),
    "rap": ("Rapports manquants", "rap_sans", "rap_total", "#8A91A6", "clôturées vérifiées", "rgba(138,145,166,%s)"),
}
TREND_DEFAULT = "pec"


def trend_export(t):
    """Tableau d'export de l'évolution : une colonne lisible par chiffre, en français, regroupées par indicateur (chiffre, base, pourcentage)."""
    def pct(a, b):
        a, b = pd.to_numeric(t[a], errors="coerce"), pd.to_numeric(t[b], errors="coerce")
        return (a / b.where(b > 0) * 100).round(1)
    tot_rap = pd.to_numeric(t["rap_avec"], errors="coerce") + pd.to_numeric(t["rap_sans"], errors="coerce")
    out = pd.DataFrame({
        "Période": t["periode"],
        "Curatives comparables (base)": t["comparables"],
        "Prises en charge hors délai": t["hors_delai"],
        "% prise en charge hors délai": pct("hors_delai", "comparables"),
        "Curatives comparables en résolution (base)": t["res_comparables"],
        "Résolues hors délai": t["res_hors_delai"],
        "% résolution hors délai": pct("res_hors_delai", "res_comparables"),
        "Passages préventifs prévus (base)": t["prevus"],
        "Passages réalisés": t["realises"],
        "% réalisés": pct("realises", "prevus"),
        "Passages non réalisés": t["non_realises"],
        "% non réalisés": pct("non_realises", "prevus"),
        "Passages jugeables (base)": t["jugeables"],
        "Passages en retard": t["retard"],
        "% en retard": pct("retard", "jugeables"),
        "Clôturées vérifiées (base)": tot_rap,
        "Sans rapport": t["rap_sans"],
        "% sans rapport": (pd.to_numeric(t["rap_sans"], errors="coerce") / tot_rap.where(tot_rap > 0) * 100).round(1),
    })
    return out


# Sens de lecture : "bad" = plus c'est bas, mieux c'est ; "good" = plus c'est haut, mieux c'est
TREND_SENS = {"pec": "bad", "res": "bad", "real": "good", "retard": "bad", "nonreal": "bad", "rap": "bad"}
TREND_PHRASE = {"pec": "des curatives sont prises en charge hors délai", "res": "des curatives sont résolues hors délai",
                "real": "des passages préventifs prévus sont réalisés", "retard": "des passages préventifs sont en retard",
                "nonreal": "des passages préventifs prévus ne sont pas réalisés", "rap": "des clôturées vérifiées n'ont pas de rapport"}


def trend_series(df, granularity, key):
    """Taux du mois (ou de l'année) pour un indicateur : libellés, valeurs, numérateurs et dénominateurs."""
    df = df.copy()
    df["periode"] = pd.to_datetime(df["periode"])
    df["rap_total"] = df.get("rap_avec", 0) + df.get("rap_sans", 0)
    _, num, den, *_r = TREND_IND[key]
    if num not in df.columns or den not in df.columns:
        return None
    df = df[df[den] > 0].reset_index(drop=True)
    if not len(df):
        return None
    df["v"] = 100.0 * df[num] / df[den]
    monthly = granularity == "Mensuel"
    df["label"] = [f"{MOIS_LONG[d.month - 1]} {d.year}" if monthly else str(d.year) for d in df["periode"]]
    df["short"] = [f"{MOIS[d.month - 1]} {str(d.year)[2:]}" if monthly else str(d.year) for d in df["periode"]]
    df["n"], df["d"] = df[num], df[den]
    return df[["label", "short", "v", "n", "d"]]


def trend_story(ser, key):
    """Phrase d'ouverture en langage simple : où en est-on, et est-ce mieux ou moins bien qu'au début ?"""
    sens = TREND_SENS[key]
    last, first = ser.iloc[-1], ser.iloc[0]
    avg = 100.0 * ser["n"].sum() / ser["d"].sum()
    diff = last["v"] - first["v"]
    stable = abs(diff) < 1.5 or len(ser) < 2
    better = (diff < 0) if sens == "bad" else (diff > 0)
    tone = "flat" if stable else ("good" if better else "bad")
    verdict = "C'est stable." if stable else ("C'est mieux." if better else "C'est moins bien.")
    ref = f"contre {first['v']:.0f} % en {first['label'].lower()}" if len(ser) > 1 else ""
    head = f"<b>{last['v']:.0f} % {TREND_PHRASE[key]} en {last['label'].lower()}</b>" + (f", {ref}. {verdict}" if ref else ".")
    best_i, worst_i = (ser["v"].idxmin(), ser["v"].idxmax()) if sens == "bad" else (ser["v"].idxmax(), ser["v"].idxmin())
    sub = (f"Moyenne sur la période : {avg:.0f} %. Meilleur mois : {ser.loc[best_i, 'label'].lower()} ({ser.loc[best_i, 'v']:.0f} %). "
           f"Moins bon : {ser.loc[worst_i, 'label'].lower()} ({ser.loc[worst_i, 'v']:.0f} %).") if len(ser) > 2 else f"Moyenne sur la période : {avg:.0f} %."
    return tone, head, sub, avg


def trend_figure(ser, key, avg):
    """Une seule courbe : le taux, la moyenne en pointillés, vert quand c'est mieux que la moyenne, rouge quand c'est moins bien."""
    sens = TREND_SENS[key]
    x, y = ser["short"].tolist(), ser["v"].round(1).tolist()
    good_c, bad_c = "#008080", "#E5114D"
    def tone(v):
        if abs(v - avg) < 0.5:
            return "#173B69"
        return good_c if ((v < avg) == (sens == "bad")) else bad_c
    up, lo = [max(v, avg) for v in y], [min(v, avg) for v in y]
    up_c, lo_c = ("rgba(229,17,77,.13)", "rgba(0,128,128,.15)") if sens == "bad" else ("rgba(0,128,128,.15)", "rgba(229,17,77,.13)")
    base = [avg] * len(y)
    fig = go.Figure()
    fig.add_scatter(x=x, y=base, mode="lines", line=dict(color="#9AA0B3", width=1, dash="dash"), hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=up, mode="lines", line=dict(width=0, shape="spline"), fill="tonexty", fillcolor=up_c, hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=base, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=lo, mode="lines", line=dict(width=0, shape="spline"), fill="tonexty", fillcolor=lo_c, hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=y, mode="lines+markers+text", line=dict(color="#173B69", width=3, shape="spline", smoothing=.6),
                    marker=dict(size=9, color="#fff", line=dict(color=[tone(v) for v in y], width=3)),
                    text=[f"{v:.0f} %" for v in y] if len(y) <= 16 else None, textposition="top center", textfont=dict(size=11, color="#173B69"),
                    customdata=list(zip(ser["label"], ser["n"], ser["d"])),
                    hovertemplate="<b>%{customdata[0]}</b><br>%{y:.1f} %<br>%{customdata[1]:,.0f} sur %{customdata[2]:,.0f}<extra></extra>", showlegend=False)
    span = max(max(y) - min(y), 10)
    fig.update_layout(height=300, margin=dict(l=4, r=10, t=14, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Nunito, Segoe UI, Arial, sans-serif", color="#5F566A", size=13), hovermode="x",
                      hoverlabel=dict(bgcolor="#173B69", bordercolor="#173B69", font=dict(family="Nunito, Segoe UI, Arial, sans-serif", color="#fff", size=13)),
                      xaxis=dict(showgrid=False, type="category", tickangle=-45 if len(x) > 8 else 0, tickfont=dict(size=12, color="#5F566A"), showline=False, zeroline=False),
                      yaxis=dict(ticksuffix=" %", gridcolor="#EEE8EF", zeroline=False, showline=False, nticks=5,
                                 range=[max(0, min(y) - span * .35), min(100, max(y) + span * .35)]))
    return fig
    return fig


def rank_zone_rows(df, level):
    total = as_int(df["total_pannes"].iloc[0]) if len(df) else 0
    top = max(as_int(df["nb_pannes"].max()), 1)
    rows = []
    for r in df.itertuples():
        width = max(100 * r.nb_pannes / top, 2)
        pct = 100 * r.nb_pannes / total if total else 0
        share = "&lt;1" + NBSP + "%" if 0 < pct < 0.5 else f"{round(pct)}{NBSP}%"
        rows.append(f'<div class="rk-row zone"><span class="rk-name" title="{escape(r.libelle)}">{escape(r.libelle)}</span>'
                    f'<span class="rk-track"><span class="rk-fill" style="width:{width:.1f}%"></span></span>'
                    f'<span class="rk-num">{format(as_int(r.nb_pannes), ",").replace(",", NBSP)}</span>'
                    f'<span class="rk-share">{share}</span></div>')
    head = (f'<div class="rk-head zone"><span>{escape(level.upper())}</span><span></span>'
            f'<span class="r">INTERVENTIONS</span><span class="r">PART</span></div>')
    return head + '<div class="rk-scroll">' + "".join(rows) + "</div>"


def rank_equipment_rows(df):
    top = max(as_int(df["nb_pannes"].max()), 1)
    rows = []
    for i, r in enumerate(df.itertuples(), start=1):
        parts = [str(x) for x in (r.programme_reference, r.agence_label) if pd.notna(x) and str(x)]
        sub = " · ".join(parts) if parts else (f"Dernière intervention le {fr_date(r.derniere_panne)}" if pd.notna(r.derniere_panne) else "")
        provider = escape(str(r.provider_name)) if pd.notna(r.provider_name) else ""
        width = max(100 * r.nb_pannes / top, 4)
        rows.append(f'<div class="rk-row eq"><span class="eq-rank">{i}.</span>'
                    f'<span class="eq-main"><b title="{escape(str(r.equipment_reference))}">{escape(str(r.equipment_reference))}</b>'
                    f'<small>{escape(sub)}</small></span>'
                    f'<span class="eq-bar"><span class="rk-fill" style="width:{width:.1f}%"></span><i>{r.nb_pannes}</i></span>'
                    f'<span class="eq-prov" title="{provider}">{provider}</span></div>')
    head = '<div class="rk-head eq"><span></span><span>ÉQUIPEMENT</span><span>INTERVENTIONS</span><span class="r">PRESTATAIRE</span></div>'
    return head + '<div class="rk-scroll">' + "".join(rows) + "</div>"


# ---------------------------------------------------------------- connexion
try:
    check_connection()
    raw_bounds = q.bounds().iloc[0]
    if pd.isna(raw_bounds["debut"]) or pd.isna(raw_bounds["fin"]):
        st.error("La table rex.f_curatif_jour ne contient aucune date. Le build du schéma rex a-t-il été exécuté ?")
        st.stop()
    earliest = pd.to_datetime(raw_bounds["debut"]).date()
    latest = pd.to_datetime(raw_bounds["fin"]).date()
except Exception as exc:
    st.error("Connexion PostgreSQL impossible. Vérifie .streamlit/secrets.toml, le serveur et les droits de lecture.")
    st.code(f"{type(exc).__name__}: {exc}")
    st.stop()

try:
    history_total = q.total_history()
except Exception:
    history_total = None

DEFAULT_PERIOD = (max(earliest, latest - timedelta(days=365)), latest)
PERIOD_MAX = max(latest, date.today())
if "per_from" not in st.session_state:
    st.session_state.per_from, st.session_state.per_to = DEFAULT_PERIOD


def set_period(debut, fin):
    st.session_state.per_from = max(debut, earliest)
    st.session_state.per_to = min(fin, PERIOD_MAX)
    sync_period_text()


def sync_period_text():
    st.session_state.per_from_txt = st.session_state.per_from.strftime("%d/%m/%Y")
    st.session_state.per_to_txt = st.session_state.per_to.strftime("%d/%m/%Y")


def parse_period_text(which):
    """Saisie au clavier (JJ/MM/AAAA, JJ-MM-AAAA ou JJMMAAAA) : une saisie invalide remet la date précédente."""
    raw = re.sub(r"[^0-9]", "", st.session_state.get(f"per_{which}_txt", ""))
    try:
        if len(raw) == 8:
            d = date(int(raw[4:]), int(raw[2:4]), int(raw[:2]))
        elif len(raw) == 6:
            d = date(2000 + int(raw[4:]), int(raw[2:4]), int(raw[:2]))
        else:
            raise ValueError
        st.session_state[f"per_{which}"] = min(max(d, earliest), PERIOD_MAX)
    except ValueError:
        pass
    sync_period_text()


if "per_from_txt" not in st.session_state:
    sync_period_text()


def reset_filters():
    for name in q.DIMENSIONS:
        st.session_state[f"flt_{name}"] = []
    st.session_state["flt_statut"] = "Tous"
    st.session_state.per_from, st.session_state.per_to = DEFAULT_PERIOD
    sync_period_text()


# ---------------------------------------------------------------- menu latéral
PAGES = ["Vue globale", "Prestataires", "Curatives", "Préventives", "Qualité des rapports", "Anomalies"]
if "page" not in st.session_state:  # l'adresse retient la page : après Actualiser (F5) on revient où on était
    _qp = st.query_params.get("page")
    st.session_state.page = _qp if _qp in PAGES else "Vue globale"


if "provider_id" not in st.session_state:
    st.session_state.provider_id = st.query_params.get("prestataire") if st.session_state.page == "Prestataires" else None


PAGE_TITLES = {
    "Curatives": ("Interventions curatives", "Suivi des interventions correctives, délais et comparatif des prestataires"),
    "Préventives": ("Interventions préventives", "Suivi des passages planifiés et comparatif des prestataires"),
    "Qualité des rapports": ("Qualité des rapports", "Conformité des rapports d’intervention déposés dans Intent"),
}


def set_page(page):
    st.session_state.page = page
    if st.session_state.get("provider_id") and st.session_state.get("flt_Prestataire") == [st.session_state.provider_id]:
        st.session_state["_pending_provider_filter"] = None  # la fiche se ferme : le filtre qu'elle imposait aussi
    st.session_state.provider_id = None  # un clic sur le menu ferme la fiche ouverte


PAGE_LABEL = {}  # nom affiché ; la clé interne de la page ne change pas (adresse, session)


def nav_button(page, icon, key, sub=False):
    on = st.session_state.page == page
    with st.container(key=f"nav_{'on' if on else 'off'}_{'sub_' if sub else ''}{key}"):
        st.button(PAGE_LABEL.get(page, page), icon=icon, on_click=set_page, args=(page,), key=f"navbtn_{key}", type="tertiary", width="stretch")


with st.sidebar:
    st.markdown(
        f'<div class="brand">{LOGO}<div class="brand-name">Pilotage de l’activité<br>patrimoine</div></div>'
        , unsafe_allow_html=True)
    nav_button("Vue globale", ":material/grid_view:", "vue")
    nav_button("Prestataires", ":material/groups:", "prestataires")
    st.markdown(f'<div class="nav-item soon" title="Interventions">{svg("wrench", 19)}<span>Interventions</span>'
                f'<span class="chev">{svg("chevron", 16)}</span></div>', unsafe_allow_html=True)
    for _p, _k in (("Curatives", "cur"), ("Préventives", "prev"), ("Qualité des rapports", "qual")):
        nav_button(_p, None, _k, sub=True)
    st.markdown('<div class="nav-section" style="margin-top:1rem">QUALITÉ DES DONNÉES</div>', unsafe_allow_html=True)
    nav_button("Anomalies", ":material/report:", "anomalies")
    with st.container(key="sync_card"):
        st.markdown('<div class="sync-title"><span class="sync-dot"></span>Données Intent</div>'
                    f'<div class="sync-sub">Données au {latest:%d/%m/%Y}</div>', unsafe_allow_html=True)
        if st.button("Actualiser", icon=":material/refresh:", width="stretch", key="refresh"):
            read_sql.clear()
            st.rerun()

# ---------------------------------------------------------------- en-tête
if st.session_state.page == "Prestataires" and st.session_state.provider_id:
    try:
        _crumb_name = q.provider_label(st.session_state.provider_id)
    except Exception:
        _crumb_name = st.session_state.provider_id
    st.markdown(f'<div class="crumb">Pilotage REX <span>›</span> Prestataires <span>›</span> <b>{escape(_crumb_name)}</b></div>',
                unsafe_allow_html=True)
else:
    st.markdown(f'<div class="crumb">Pilotage REX <span>›</span> <b>{PAGE_LABEL.get(st.session_state.page, st.session_state.page)}</b></div>', unsafe_allow_html=True)

history = f" • {history_total / 1e6:.1f}".replace(".", ",") + " M d’interventions historisées" if history_total else ""
if st.session_state.page == "Prestataires" and st.session_state.provider_id:
    pass  # la bannière de la fiche tient lieu de titre
elif st.session_state.page == "Prestataires":
    st.markdown('<h1 class="page-title">Prestataires</h1>'
                '<div class="page-sub">Contrats, métiers et couverture des prestataires sur le périmètre filtré</div>',
                unsafe_allow_html=True)
elif st.session_state.page in PAGE_TITLES:
    _t, _s = PAGE_TITLES[st.session_state.page]
    st.markdown(f'<h1 class="page-title">{_t}</h1><div class="page-sub">{_s}</div>', unsafe_allow_html=True)
elif st.session_state.page == "Anomalies":
    st.markdown('<h1 class="page-title">Anomalies de données</h1>'
                '<div class="page-sub">Rattachements incohérents entre les interventions et le référentiel patrimoine</div>',
                unsafe_allow_html=True)
else:
    st.markdown('<h1 class="page-title">Vue globale de l’exploitation</h1>'
                f'<div class="page-sub">Contrats et interventions issus d’Intent{history}</div>', unsafe_allow_html=True)

# if latest < date.today() - timedelta(days=7):
    # st.warning(f"La dernière date de création présente dans les agrégats est le {latest:%d/%m/%Y}. "
            #    "Vérifie la fraîcheur de l'alimentation.")

# ---------------------------------------------------------------- filtres
_d1, _d2 = st.session_state.get("per_from"), st.session_state.get("per_to")
if isinstance(_d1, date) and isinstance(_d2, date):
    start, end = min(_d1, _d2), max(_d1, _d2)  # dates inversées : on remet dans l'ordre
    st.session_state["_last_period"] = (start, end)
else:  # une date vidée : on garde la dernière période complète
    start, end = st.session_state.get("_last_period", DEFAULT_PERIOD)

# Synchronisation fiche prestataire et filtre Prestataire du haut. Une fiche ouverte pose le filtre ; changer le filtre
# change la fiche (un seul prestataire) ou ramène à la liste (aucun ou plusieurs). Les changements demandés par un bouton
# passent par _pending_provider_filter, car un filtre déjà affiché ne peut plus être modifié dans le même passage.
_pending = st.session_state.pop("_pending_provider_filter", "__none__")
if _pending != "__none__":
    st.session_state["flt_Prestataire"] = [] if _pending is None else [str(_pending)]
elif st.session_state.page == "Prestataires" and st.session_state.get("provider_id"):
    _sel = st.session_state.get("flt_Prestataire", [])
    if _sel != [st.session_state.provider_id]:
        if len(_sel) == 1:
            st.session_state.provider_id = str(_sel[0])
            st.session_state.prov_switch = str(_sel[0])
        else:
            st.session_state.provider_id = None

# Options de chaque filtre, croisées avec les autres sélections. Les valeurs devenues absentes sont retirées.
current = {n: st.session_state.get(f"flt_{n}", []) for n in q.DIMENSIONS}
current = {n: v for n, v in current.items() if v}
STATUS_CHOICES = ["Tous"] + list(q.STATUS_VALUES)
contract_status = st.session_state.get("flt_statut", "Tous")
if contract_status in q.STATUS_VALUES:
    current[q.STATUS_LABEL] = q.STATUS_VALUES[contract_status]
names_by_filter, option_errors = {}, {}
for name in q.DIMENSIONS:
    try:
        opts = q.options(name, current, start, end)
        names_by_filter[name] = dict(zip(opts["reference"], opts["libelle"]))
    except Exception as exc:
        names_by_filter[name] = {}
        option_errors[name] = str(exc)
    key = f"flt_{name}"
    st.session_state[key] = [v for v in st.session_state.get(key, []) if v in names_by_filter[name]]


def chip_label(name):
    chosen = st.session_state[f"flt_{name}"]
    names = names_by_filter[name]
    if not chosen:
        if name == "Contrat" and contract_status != "Tous":
            value = f"{contract_status} ({len(names)})"
        else:
            value = f"{'Toutes' if name in FEMININ else 'Tous'} ({len(names)})"
    elif len(chosen) == 1:
        value = names[chosen[0]]
        value = value if len(value) <= 12 else value[:11] + "…"
    else:
        value = f"{len(chosen)} sélectionnés"
    return f":gray[{name}]  **{value}**"


def filter_select(name, collapsed=True):
    """Même sélecteur pour tous les filtres : recherche en direct, liste à cocher, pastilles de sélection."""
    picker.select(f"flt_{name}", names_by_filter[name], placeholder=f"Rechercher {name.lower()}...", split=(name == "Contrat"))
    if name in option_errors:
        st.error(f"Filtre {name} indisponible : {option_errors[name]}")


QUICK = ["Agence", "Prestataire", "Métier", "Contrat"]
MORE = ["Société", "Groupe", "Secteur", "Programme", "Type de travaux"]
more_active = sum(1 for n in MORE if st.session_state[f"flt_{n}"])

with st.container(key="filterbar"):
    cols = st.columns([2.1, 1.3, 1.4, 1.2, 1.3, 1.45, 1.3], vertical_alignment="center")
    with cols[0].container(key="chip_period"):
        with st.popover(f"Période  **{start:%d/%m/%y} - {end:%d/%m/%y}**", icon=":material/calendar_month:",
                        width="stretch"):
            _L = pd.Timestamp(latest)
            presets = [("30 derniers jours", (latest - timedelta(days=29), latest)),
                       ("3 derniers mois", ((_L - pd.DateOffset(months=3)).date(), latest)),
                       ("6 derniers mois", ((_L - pd.DateOffset(months=6)).date(), latest)),
                       ("12 derniers mois", ((_L - pd.DateOffset(months=12)).date(), latest)),
                       (f"Année {latest.year}", (date(latest.year, 1, 1), latest)),
                       (f"Année {latest.year - 1}", (date(latest.year - 1, 1, 1), date(latest.year - 1, 12, 31))),
                       ("Tout l'historique", (earliest, latest))]
            for pair in range(0, len(presets), 2):
                for col, (lbl, (a_, b_)) in zip(st.columns(2), presets[pair:pair + 2]):
                    col.button(lbl, key=f"per_{pair}_{lbl}", on_click=set_period, args=(a_, b_), width="stretch")
            d1, d2 = st.columns(2)
            d1.text_input("Du", key="per_from_txt", on_change=parse_period_text, args=("from",), placeholder="JJ/MM/AAAA")
            d2.text_input("Au", key="per_to_txt", on_change=parse_period_text, args=("to",), placeholder="JJ/MM/AAAA")
            st.caption("Saisis une date au clavier puis Entrée (JJ/MM/AAAA), ou choisis un raccourci. La période porte sur la date de création des interventions.")
    for col, name in zip(cols[1:5], QUICK):
        with col.container(key=f"chip_{name}"):
            with st.popover(chip_label(name), width="stretch"):
                if name == "Contrat":
                    st.markdown('<div class="pop-label">Statut du contrat</div>', unsafe_allow_html=True)
                    st.radio("Statut du contrat", STATUS_CHOICES, key="flt_statut", horizontal=True,
                             label_visibility="collapsed")
                    st.markdown('<div class="pop-label">Contrats</div>', unsafe_allow_html=True)
                filter_select(name)
    with cols[5].container(key="chip_more"):
        with st.popover(f"Plus de filtres{f' ({more_active})' if more_active else ''}", icon=":material/tag:",
                        width="stretch"):
            for name in MORE:
                total = len(names_by_filter[name])
                chosen = len(st.session_state[f"flt_{name}"])
                with st.expander(name, expanded=chosen > 0):  # replié par défaut, ouvert dès qu'il y a une sélection
                    st.caption(f"{chosen} sélectionné{'s' if chosen > 1 else ''} sur {total}" if chosen else
                               f"{'Toutes' if name in FEMININ else 'Tous'} ({total})")
                    filter_select(name)
    with cols[6].container(key="chip_reset"):
        st.button("Réinitialiser", icon=":material/restart_alt:", on_click=reset_filters, width="stretch")

filters = {n: st.session_state[f"flt_{n}"] for n in q.DIMENSIONS if st.session_state[f"flt_{n}"]}
if st.session_state.get("flt_statut", "Tous") in q.STATUS_VALUES:
    filters[q.STATUS_LABEL] = q.STATUS_VALUES[st.session_state["flt_statut"]]


GRAVITE_TONE = {3: "#E5114D", 2: "#C98A14", 1: "#7B7385"}


def render_anomalies():
    """Page d'actions : chaque anomalie dit ce qu'il faut faire, et la liste détaillée est exportable."""
    from services import anom
    try:
        summ = anom.summary(filters)
    except Exception as exc:
        st.error(f"Anomalies indisponibles : {exc}")
        return
    with st.container(key="card_anomalies"):
        card_title("Anomalies de données", "Interventions à corriger ou à qualifier. Les filtres géographiques, prestataire, contrat, métier et type de travaux s'appliquent ; "
                   "la période, non : une anomalie reste ouverte tant qu'elle n'est pas corrigée.",
                   "Les seuils d'ancienneté viennent de rex.parametre. Les cas massifs sans action unitaire possible (curatives sans SLA, "
                   "interventions sans équipement) restent des compteurs dans les indicateurs.")
        if not len(summ):
            note("Aucune anomalie sur ce périmètre.")
            return
        a_traiter = int(summ.loc[summ["gravite"] == 3, "n"].sum())
        a_qualifier = int(summ.loc[summ["gravite"] == 2, "n"].sum())
        info = int(summ.loc[summ["gravite"] == 1, "n"].sum())
        tiles = [("À traiter", fr_int(a_traiter), "gravité 3 : action attendue"),
                 ("À qualifier", fr_int(a_qualifier), "gravité 2 : à vérifier"),
                 ("Information", fr_int(info), "gravité 1 : à connaître")]
        for col, (label, value, sub) in zip(st.columns(3), tiles):
            col.markdown(f'<div class="an-tile"><div class="an-label">{escape(label)}</div>'
                         f'<div class="an-value">{value}</div><div class="an-sub">{escape(sub)}</div></div>', unsafe_allow_html=True)
        rows = []
        for r in summ.itertuples():
            label, action, famille = anom.CATALOG.get(r.code, (r.code, "", ""))
            tone = GRAVITE_TONE.get(int(r.gravite), "#7B7385")
            rows.append(f'<div class="pf-lrow"><span><b>{escape(label)}</b><br><small>{escape(famille)}</small></span>'
                        f'<span><span class="pf-spill" style="background:{tone}22;color:{tone}">● {anom.GRAVITE.get(int(r.gravite), "")}</span></span>'
                        f'<span><b>{fr_int(int(r.n))}</b></span><span>{int(r.anciennete_moy) if pd.notna(r.anciennete_moy) else "–"} j</span>'
                        f'<span>{int(r.anciennete_max) if pd.notna(r.anciennete_max) else "–"} j</span><span>{escape(action)}</span></div>')
        st.markdown('<div class="pf-ltable" style="--cols:2.2fr 1fr .8fr .8fr .8fr 3fr"><div class="pf-lrow head"><span>ANOMALIE</span><span>GRAVITÉ</span>'
                    '<span>NOMBRE</span><span>ANCIENNETÉ MOY.</span><span>ANCIENNETÉ MAX</span><span>ACTION</span></div>' + "".join(rows) + "</div>",
                    unsafe_allow_html=True)

    codes = list(summ["code"].unique())
    with st.container(key="card_anomalies_detail"):
        c1, c2, c3 = st.columns([3, 3, 0.6], vertical_alignment="center")
        with c1:
            code = st.selectbox("Anomalie", codes, key="an_code", label_visibility="collapsed",
                                format_func=lambda v: f"{anom.CATALOG.get(v, (v,))[0]} ({fr_int(int(summ.loc[summ['code'] == v, 'n'].sum()))})")
        with c2:
            needle = st.text_input("Recherche", key="an_search", label_visibility="collapsed", icon=":material/search:",
                                   placeholder="Rechercher une référence, un équipement, un contrat...")
        sig = (code, needle, repr(filters))
        if st.session_state.get("an_sig") != sig:
            st.session_state.an_sig = sig
            st.session_state.an_page = 1
        per_page = 15
        page_no = int(st.session_state.get("an_page", 1))
        try:
            df, total = anom.detail(filters, code, needle, per_page, (page_no - 1) * per_page)
            by_prov = anom.by_provider(filters, code)
        except Exception as exc:
            st.error(f"Détail indisponible : {exc}")
            return
        with c3:
            if len(df):
                download_xlsx(df, f"rex_anomalie_{code}_p{page_no}.xlsx", "export_an_detail", label="",
                              loader=lambda: anom.detail(filters, code, needle, 100000, 0)[0], sig=repr(sig), total=total)
        st.caption(anom.CATALOG.get(code, ("", "", ""))[1])
        if len(df):
            st.dataframe(fr.traduire(df), width="stretch", hide_index=True, height=420)
            pages = max(1, -(-total // per_page))
            f1, f2, f3, f4 = st.columns([5, 0.5, 1.6, 0.5], vertical_alignment="center")
            f1.caption(f"{(page_no - 1) * per_page + 1} à {(page_no - 1) * per_page + len(df)} sur {fr_int(total)} · export : choisis les colonnes dans le bouton de téléchargement")
            if f2.button("‹", key="an_prev", disabled=page_no <= 1):
                st.session_state.an_page = page_no - 1
                st.rerun()
            f3.markdown(f'<div class="pf-pageno">Page {page_no} / {fr_int(pages)}</div>', unsafe_allow_html=True)
            if f4.button("›", key="an_next", disabled=page_no >= pages):
                st.session_state.an_page = page_no + 1
                st.rerun()
        else:
            note("Aucune anomalie de ce type sur ce périmètre.")
    with st.container(key="card_anomalies_prov"):
        card_title("Prestataires les plus concernés", "Pour cibler les relances : nombre d'interventions concernées par prestataire.")
        if len(by_prov):
            top = int(by_prov["n"].max())
            st.markdown('<div class="iv-prow q head"><span>PRESTATAIRE</span><span>VOLUME</span><span>NB</span></div>' + "".join(
                f'<div class="iv-prow q"><span class="iv-prov"><b>{escape(str(r.prestataire))}</b></span>'
                f'<span class="iv-pbar red"><i style="width:{100 * r.n / top:.0f}%"></i></span><b>{fr_int(int(r.n))}</b></div>'
                for r in by_prov.itertuples()), unsafe_allow_html=True)
        else:
            note("Aucun prestataire concerné.")
    with st.container(key="card_anomalies_ref"):
        card_title("Anomalies du référentiel", "Contrats et prestataires à corriger à la source, indépendamment de la période et des filtres.")
        try:
            ref = anom.referentiel(filters)
        except Exception as exc:
            st.error(f"Référentiel indisponible : {exc}")
            return
        tabs = st.tabs(["Prestataire hors contrat", "Contrat sans programme", "Contrat sans métier"])
        for tab, name, why in ((tabs[0], "prestataire_hors_contrat", "Prestataires qui ont des interventions mais aucun contrat."),
                               (tabs[1], "contrat_sans_programme", "Contrats sans programme rattaché."),
                               (tabs[2], "contrat_sans_metier", "Contrats dont le métier (topic) est vide.")):
            with tab:
                st.caption(why)
                if len(ref[name]):
                    st.dataframe(fr.traduire(ref[name]), width="stretch", hide_index=True, height=260)
                    download_xlsx(ref[name], f"rex_anomalie_{name}.xlsx", f"export_{name}", label="Exporter")
                else:
                    note("Aucune anomalie.")


CARDS_MAX_PAGE = 12  # cartes : 12 par page
LIST_MAX_PAGE = 20   # liste : 20 lignes par page
AVATAR_COLORS = ["#2F6FE4", "#0A9396", "#C9459A", "#2E9E5E", "#7B5BD6", "#E0762A", "#1BA7D6", "#4458B8", "#C98A14", "#4F7CAC"]
TAG_TONES = [("#E4EDFC", "#1F4FB0"), ("#DDF3F1", "#0B6B6F"), ("#FBE3F1", "#9A2C74"), ("#E2F4E8", "#1E7A46"),
             ("#ECE6FB", "#5A3BB5"), ("#FDEBDD", "#B35417"), ("#DFF3FA", "#0E6E90"), ("#E6E9FA", "#3544A0")]


def provider_initials(name):
    words = [w for w in str(name).replace("-", " ").split() if w]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return str(name)[:2].upper()


def provider_card(row):
    name = str(row.provider_name)
    metiers = [m for m in (row.metiers or []) if m]
    tags = "".join(f'<span class="pv-tag">{escape(m)}</span>' for m in metiers[:2])
    if len(metiers) > 2:
        tags += f'<span class="pv-tag more">+{len(metiers) - 2}</span>'
    total, active = int(row.total), int(row.actifs)
    pct = 100 * active / total if total else 0
    hors = bool(getattr(row, "hors_contrat", False))
    if hors:
        state, label = "none", "Sans contrat"
    elif active:
        state, label = "on", "Actif"
    else:
        state, label = "off", "Inactif"
    empty_tags = "Aucun contrat dans le référentiel" if hors else "Métier non renseigné"
    return (f'<div class="pv-card {state}">'
            f'<div class="pv-head"><span class="pv-mono {state}">{escape(provider_initials(name))}</span>'
            f'<span class="pv-name"><b title="{escape(name)}">{escape(name)}</b><em class="pv-st {state}">{label}</em></span></div>'
            f'<div class="pv-tags">{tags or "<span class=pv-none>" + empty_tags + "</span>"}</div>'
            f'<div class="pv-foot"><div class="pv-count"><b>{active}</b><span>/ {total} contrats actifs</span></div>'
            f'<div class="pv-bar"><i class="{state}" style="width:{pct:.0f}%"></i></div>'
            f'<div class="pv-interv">{fr_int(int(row.interventions))} interventions</div></div></div>'
            '<span class="pv-open">Voir la fiche</span>')


def provider_row(row, vmax):
    """Ligne de la vue Liste : monogramme, statut, métiers, contrats actifs en barre, interventions en barre."""
    name = str(row.provider_name)
    metiers = [m for m in (row.metiers or []) if m]
    tags = "".join(f'<span class="pv-tag">{escape(m)}</span>' for m in metiers[:3])
    if len(metiers) > 3:
        tags += f'<span class="pv-tag more">+{len(metiers) - 3}</span>'
    total, active = int(row.total), int(row.actifs)
    pct = 100 * active / total if total else 0
    hors = bool(getattr(row, "hors_contrat", False))
    state, label = ("none", "Sans contrat") if hors else (("on", "Actif") if active else ("off", "Inactif"))
    n = int(row.interventions)
    w = 100 * n / vmax if vmax else 0
    return (f'<div class="pl-row {state}">'
            f'<div class="pl-id"><span class="pv-mono {state}">{escape(provider_initials(name))}</span>'
            f'<span class="pl-name"><b title="{escape(name)}">{escape(name)}</b><em class="pv-st {state}">{label}</em></span></div>'
            f'<div class="pl-tags">{tags or "<span class=pv-none>" + ("Aucun contrat" if hors else "Métier non renseigné") + "</span>"}</div>'
            f'<div class="pl-ct"><span class="pl-num"><b>{active}</b><em> / {total}</em></span><span class="pv-bar"><i class="{state}" style="width:{pct:.0f}%"></i></span></div>'
            f'<div class="pl-iv"><span class="pl-num"><b>{fr_int(n)}</b></span><span class="pv-bar"><i class="iv" style="width:{w:.0f}%"></i></span></div>'
            f'<span class="pl-go">&rsaquo;</span></div>')


def provider_table(df):
    """Mêmes informations que la carte : prestataire, statut, métiers, contrats actifs / total, interventions."""
    def statut(r):
        return "Sans contrat" if r.hors_contrat else ("Actif" if r.actifs else "Inactif")
    out = pd.DataFrame({
        "Prestataire": df["provider_name"].values,
        "Statut": [statut(r) for r in df.itertuples()],
        "Métiers": df["metiers"].apply(lambda m: ", ".join(m or [])).values,
        "Contrats actifs": [f"{int(r.actifs)} / {int(r.total)}" for r in df.itertuples()],
        "Interventions": df["interventions"].astype("int64").values,
    })
    return out


def render_providers():
    try:
        kp = q.providers_kpis(filters)
        data = q.providers_list(filters)
        counts = q.providers_interventions(filters, start, end)
    except Exception as exc:
        st.error(f"Prestataires indisponibles : {exc}")
        return
    data["interventions"] = data["provider_id"].map(counts).fillna(0).astype("int64")  # période et filtres actifs
    tiles = [("white lead", "users", fr_int(kp["prestataires"]), "Prestataires actifs"),
             ("white", "file", fr_int(kp["contrats"]), "Contrats actifs"),
             ("white", "grid", fr_int(kp["metiers"]), "Métiers couverts"),
             ("white", "calendar", fr_int(kp["agences"]), "Agences concernées")]
    for col, (tone, icon, value, label) in zip(st.columns(4), tiles):
        col.markdown(f'<div class="pv-kpi {tone}"><span class="pv-kpi-icon">{svg(icon, 22)}</span>'
                     f'<span><b>{value}</b><small>{label}</small></span></div>', unsafe_allow_html=True)

    with st.container(key="card_providers"):
        h1, h2, h3, h4 = st.columns([3.2, 2.6, 1.7, 0.7], vertical_alignment="center")
        with h1:
            card_title("Liste des prestataires", f"{fr_int(len(data))} prestataires sur le périmètre filtré, dont {fr_int(kp['prestataires'])} avec au moins un contrat actif"
                       + (f" et {fr_int(int(data['hors_contrat'].sum()))} sans contrat" if data["hors_contrat"].any() else ""))
        with h2:
            needle = st.text_input("Rechercher", key="prov_search", label_visibility="collapsed",
                                   icon=":material/search:", placeholder="Rechercher un prestataire, un métier...")
        with h3:
            sort = st.selectbox("Trier par", ["Nom A-Z", "Contrats actifs (décroissant)", "Contrats actifs (croissant)"],
                                key="prov_sort", label_visibility="collapsed", format_func=lambda v: f"Trier : {v}")
        with h4:
            if len(data):
                download_xlsx(provider_table(data), "rex_prestataires.xlsx", "export_prestataires", label="")
        view = st.segmented_control("Affichage", ["Cartes", "Liste"], default="Cartes", key="prov_view",
                                   label_visibility="collapsed") or "Cartes"

        shown = data
        if needle.strip():
            n = needle.strip().lower()
            shown = shown[shown["provider_name"].str.lower().str.contains(n, regex=False)
                          | shown["metiers"].apply(lambda m: any(n in str(x).lower() for x in (m or [])))]
        if sort.endswith("(décroissant)"):
            shown = shown.sort_values(["actifs", "provider_name"], ascending=[False, True])
        elif sort.endswith("(croissant)"):
            shown = shown.sort_values(["actifs", "provider_name"], ascending=[True, True])

        if not len(shown):
            note("Aucun prestataire sur ce périmètre.")
            return
        per = LIST_MAX_PAGE if view == "Liste" else CARDS_MAX_PAGE
        pages = max(1, -(-len(shown) // per))
        page_no = 1
        if pages > 1:
            page_no = st.session_state.get("prov_page") or 1
            page_no = min(max(int(page_no), 1), pages)
        chunk = shown.iloc[(page_no - 1) * per: page_no * per]
        if view == "Liste":
            vmax = int(shown["interventions"].max() or 0)
            st.markdown('<div class="pl-head"><span>Prestataire</span><span>Métiers</span><span>Contrats actifs</span>'
                        '<span>Interventions</span><span></span></div>', unsafe_allow_html=True)
            for r in chunk.itertuples():
                with st.container(key=f"pvr_{r.provider_id}"):
                    st.markdown(provider_row(r, vmax), unsafe_allow_html=True)
                    st.button("Voir la fiche", key=f"pvrb_{r.provider_id}", on_click=open_provider, args=(r.provider_id,))
        else:
            rows = list(chunk.itertuples())
            for i in range(0, len(rows), 4):
                for col, r in zip(st.columns(4), rows[i:i + 4]):
                    with col, st.container(key=f"pvc_{r.provider_id}"):
                        st.markdown(provider_card(r), unsafe_allow_html=True)
                        st.button("Voir la fiche", key=f"pvb_{r.provider_id}", on_click=open_provider, args=(r.provider_id,))
        f1, f2 = st.columns([3, 2], vertical_alignment="center")
        f1.caption(f"{len(chunk)} prestataires sur {fr_int(len(shown))} · l'export Excel reprend la liste complète avec les filtres actifs")
        if pages > 1:
            with f2:
                st.segmented_control("Page", list(range(1, pages + 1)), default=1, key="prov_page",
                                     label_visibility="collapsed")


# ---------------------------------------------------------------- fiche prestataire
# open = ouverte, pending = en cours, hold = en attente, closed = clôturée,
# denied = refusée (non_contractual, unable) ou annulée (event canceled), séparées à l'affichage.
STATUS_FR = {"open": "Ouvertes", "pending": "En cours", "hold": "En attente", "closed": "Clôturées",
             "canceled": "Annulées", "denied": "Refusées"}
STATUS_TONE = {"open": "#2F6FE4", "pending": "#7B5BD6", "hold": "#E0762A", "closed": "#0A7C6E",
               "canceled": "#B5B0BE", "denied": "#7B7385"}
STATUS_ORDER = ["open", "pending", "hold", "closed", "canceled", "denied"]
STATUS_DONE = {"closed"}
STATUS_INACTIVE = {"closed", "canceled", "denied"}


def open_provider(provider_id):
    st.session_state.provider_id = str(provider_id)
    st.session_state.prov_switch = str(provider_id)
    st.session_state["_pending_provider_filter"] = str(provider_id)
    st.session_state.prov_tbl_n = st.session_state.get("prov_tbl_n", 0) + 1


def close_provider():
    st.session_state.provider_id = None
    st.session_state["_pending_provider_filter"] = None


def switch_provider():
    st.session_state.provider_id = st.session_state.get("prov_switch")
    st.session_state["_pending_provider_filter"] = st.session_state.get("prov_switch")


def fmt_duration(hours):
    return fr.duree(hours, "n/d")


def status_cards(df, work_type):
    """Cartes par statut (actifs / inactifs) pour un type de travaux. Retourne le HTML et les totaux."""
    sub = df[df["work_type"] == work_type].copy()
    total = int(sub["n"].sum())
    sub["rank"] = sub["status"].map(lambda s: STATUS_ORDER.index(s) if s in STATUS_ORDER else 50)
    sub = sub.sort_values(["rank", "status"])

    def card(r):
        s = str(r.status)
        label = STATUS_FR.get(s, s.replace("_", " ").capitalize())
        color = STATUS_TONE.get(s, "#5F566A")
        n = int(r.n)
        share = 100 * n / total if total else 0
        late, comp = (int(r.late_res), int(r.comp_res)) if s in STATUS_DONE else (int(r.late_pec), int(r.comp_pec))
        delay = ""
        if work_type == "corrective" and s not in ("denied", "canceled") and comp:
            ontime = max(comp - late, 0)
            delay = (f'<div class="pf-bar"><i style="width:{100 * ontime / comp:.0f}%"></i></div>'
                     f'<div class="pf-leg"><span class="ok"></span>{fr_int(ontime)} dans les délais</div>'
                     f'<div class="pf-leg"><span class="late"></span>{fr_int(late)} hors délai</div>')
        else:
            delay = f'<div class="pf-bar plain"><i style="width:{share:.0f}%;background:{color}"></i></div>'
        return (f'<div class="pf-status" style="border-top-color:{color}">'
                f'<span class="pf-pill" style="background:{color}22;color:{color}">● {escape(label)}</span>'
                f'<div class="pf-num"><b>{fr_int(n)}</b><small>{fr_pct(share)}</small></div>{delay}</div>')

    active = sub[~sub["status"].isin(STATUS_INACTIVE)]
    inactive = sub[sub["status"].isin(STATUS_INACTIVE)]
    html = ('<div class="pf-groups">'
            f'<div class="pf-group"><div class="pf-ghead">ACTIVES <b>{fr_int(active["n"].sum())}</b></div>'
            f'<div class="pf-cards">{"".join(card(r) for r in active.itertuples()) or '<div class="pf-empty">Aucune intervention active sur cette période.</div>'}</div></div>'
            f'<div class="pf-group"><div class="pf-ghead">INACTIVES <b>{fr_int(inactive["n"].sum())}</b></div>'
            f'<div class="pf-cards">{"".join(card(r) for r in inactive.itertuples()) or '<div class="pf-empty">Aucune intervention terminée sur cette période.</div>'}</div></div></div>')
    return html, total, sub


PANEL_TONE = {"open": "#0074FF", "pending": "#432ABD", "hold": "#FFB020", "closed": "#008080", "canceled": "#C9CFE0", "denied": "#8A91A6"}


def status_panel(kind, big, big_label, big_sub, stats, sub, total):
    """Panneau organisé : chiffre clé, repères, barre de statuts, puis tableau Actives / Terminées avec sous-totaux."""
    sub = sub.copy()
    sub["rank"] = sub["status"].map(lambda s: STATUS_ORDER.index(s) if s in STATUS_ORDER else 50)
    sub = sub.sort_values("rank")
    segs = "".join(f'<i style="width:{100 * int(r.n) / total:.2f}%;background:{PANEL_TONE.get(r.status, "#8A91A6")}"></i>'
                   for r in sub.itertuples() if total)
    curative = kind == "bad"

    def delays(r):
        s = str(r.status)
        if not curative or s in ("denied", "canceled"):
            return 0, 0
        late, comp = (int(r.late_res), int(r.comp_res)) if s in STATUS_DONE else (int(r.late_pec), int(r.comp_pec))
        return max(comp - late, 0), late

    def cells(ok, late):
        if not curative:
            return ""
        if not (ok or late):
            return '<span class="pf3-mut">–</span><span class="pf3-mut">–</span>'
        return f'<span class="pf3-ok">{fr_int(ok)}</span><span class="pf3-late">{fr_int(late)}</span>'

    def group(title, part):
        if not len(part):
            return ""
        n = int(part["n"].sum())
        d = [delays(r) for r in part.itertuples()]
        rows = "".join(
            f'<div class="pf3-row"><span class="pf3-st"><u style="background:{PANEL_TONE.get(r.status, "#8A91A6")}"></u>'
            f'{escape(STATUS_FR.get(r.status, str(r.status).capitalize()))}</span><b>{fr_int(int(r.n))}</b>'
            f'<span class="pf3-mut">{fr_pct(100 * int(r.n) / total)}</span>{cells(*dl)}</div>'
            for r, dl in zip(part.itertuples(), d))
        return (f'<div class="pf3-grp"><span>{title}</span><b>{fr_int(n)}</b><span class="pf3-mut">{fr_pct(100 * n / total)}</span>'
                f'{cells(sum(x[0] for x in d), sum(x[1] for x in d))}</div>{rows}')

    active = sub[~sub["status"].isin(STATUS_INACTIVE)]
    done = sub[sub["status"].isin(STATUS_INACTIVE)]
    head = ('<div class="pf3-head"><span>Statut</span><span>Total</span><span>Part</span>'
            + ('<span>Dans délai</span><span>Hors délai</span>' if curative else '') + '</div>')
    kpis = "".join(f'<div><b>{v}</b><small>{k}</small></div>' for k, v in stats)
    return (f'<div class="pf2-top"><div class="pf2-big {kind}"><b>{big}</b><span>{big_label}</span></div>'
            f'<div class="pf2-sub">{big_sub}</div></div>'
            f'<div class="pf2-kpis">{kpis}</div><div class="pf2-bar">{segs}</div>'
            f'<div class="pf3 {"c" if curative else "p"}">{head}{group("En cours", active)}{group("Terminées", done)}</div>')


def render_provider_sheet(pid):
    pf = {**filters, "Prestataire": [pid]}
    try:
        name = q.provider_label(pid)
        cov = q.provider_coverage(pid, filters)
        status = q.provider_status(pid, filters, start, end)
        d_pec, d_res = q.provider_delays(pid, filters, start, end)
        equip = q.provider_equipments(pid, filters)
        housings = q.housings_by_program(sorted(cov["programme"].dropna().unique())) if len(cov) else None
    except Exception as exc:
        st.button("Retour", icon=":material/arrow_back:", on_click=close_provider, key="pf_back_err")
        st.error(f"Fiche prestataire indisponible : {exc}")
        return

    contracts = cov.drop_duplicates("contrat") if len(cov) else cov
    n_contracts = len(contracts)
    n_active = int((contracts["statut"] == "active").sum()) if n_contracts else 0
    n_inactive = n_contracts - n_active
    metiers = sorted(contracts["metier"].unique()) if n_contracts else []
    esi = int(cov["programme"].nunique()) if len(cov) else 0
    n_housings = int(housings["logements"].sum()) if housings is not None and len(housings) else 0

    n_ops = int(status["n"].sum()) if len(status) else 0
    nav1, nav2 = st.columns([4.6, 1.6], vertical_alignment="center")
    with nav1:
        st.button("Retour à la liste", icon=":material/arrow_back:", on_click=close_provider, key="pf_back", type="tertiary")
    with nav2:
        try:
            everyone = q.providers_list({})
            labels = dict(zip(everyone["provider_id"], everyone["provider_name"]))
        except Exception:
            labels = {}
        labels.setdefault(pid, name)
        ids = list(labels)
        if st.session_state.get("prov_switch") not in ids:
            st.session_state.prov_switch = pid
        st.selectbox("Autre prestataire", ids, key="prov_switch", on_change=switch_provider,
                     format_func=lambda v: labels.get(v, v), label_visibility="collapsed")

    meta = "".join(f'<span class="pf-mchip">{escape(m)}</span>' for m in metiers[:6]) or '<span class="pf-mchip off">Aucun contrat dans le référentiel</span>'
    badge = ('<span class="pf-badge on">Actif</span>' if n_active else '<span class="pf-badge off">Inactif</span>')
    st.markdown(
        f'<div class="pf-id"><span class="pv-hex pf-hex" style="background:#E5114D">{escape(provider_initials(name))}</span>'
        f'<div class="pf-id-txt"><div class="pf-id-top"><div class="pf-title">{escape(name)}</div>{badge}</div>'
        f'<div class="pf-mchips">{meta}</div></div></div>'
        f'<div class="pf-kpis">'
        f'<div class="pf-kpi"><span class="k-ic">{svg("file", 18)}</span><small>Contrats actifs</small><b>{fr_int(n_active)}<em> / {fr_int(n_contracts)}</em></b><i>sur le périmètre filtré</i></div>'
        f'<div class="pf-kpi"><span class="k-ic">{svg("grid", 18)}</span><small>ESI rattachés</small><b>{fr_int(esi)}</b><i>programmes couverts</i></div>'
        f'<div class="pf-kpi"><span class="k-ic">{svg("users", 18)}</span><small>Logements</small><b>{fr_int(n_housings)}</b><i>via les ESI rattachés</i></div>'
        f'<div class="pf-kpi"><span class="k-ic">{svg("wrench", 18)}</span><small>Interventions</small><b>{fr_int(n_ops)}</b><i>sur la période</i></div>'
        f'<div class="pf-kpi"><span class="k-ic">{svg("clock", 18)}</span><small>Délai intervention</small><b>{fmt_duration(d_pec)}</b><i>moyenne</i></div>'
        f'<div class="pf-kpi"><span class="k-ic">{svg("clock", 18)}</span><small>Délai résolution</small><b>{fmt_duration(d_res)}</b><i>moyenne</i></div>'
        f'</div>', unsafe_allow_html=True)

    tab_vue, tab_int, tab_eq = st.tabs(["Vue d’ensemble", "Interventions", "Équipements"])
    with tab_vue:
        left, right = st.columns([1, 1.6])
        with left.container(key="pf_card_contracts"):
            card_title("Contrats actifs et inactifs", "Contrats rattachés au prestataire sur le périmètre filtré")
            if n_contracts:
                fig = go.Figure(go.Pie(labels=["Actifs", "Inactifs"], values=[n_active, n_inactive], hole=.72, sort=False,
                                       marker=dict(colors=["#008080", "#C9CFE0"]), textinfo="none", direction="clockwise"))
                fig.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                                  annotations=[dict(text=f"<b>{n_contracts}</b><br>contrats", showarrow=False,
                                                    font=dict(size=22, family="Nunito, Segoe UI, Arial, sans-serif", color="#1F1A2E"))])
                c1, c2 = st.columns([1.1, 1])
                c1.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="pf_donut")
                c2.markdown(
                    f'<div class="pf-legend"><div><i style="background:#008080"></i>Actifs<b>{n_active}</b>'
                    f'<small>{fr_pct(100 * n_active / n_contracts)}</small></div>'
                    f'<div><i style="background:#C9CFE0"></i>Inactifs<b>{n_inactive}</b>'
                    f'<small>{fr_pct(100 * n_inactive / n_contracts)}</small></div></div>', unsafe_allow_html=True)
            else:
                note("Aucun contrat pour ce prestataire sur ce périmètre.")
        with right.container(key="pf_card_metiers"):
            card_title("Répartition des contrats par métier", "Contrats actifs et inactifs, ESI et logements rattachés")
            if n_contracts:
                by_prog = (housings.set_index("programme")["logements"].to_dict() if housings is not None and len(housings) else {})
                rows = []
                for metier, grp in cov.groupby("metier"):
                    ctr = grp.drop_duplicates("contrat")
                    progs = grp["programme"].dropna().unique()
                    rows.append({"Métier": metier, "Contrats": len(ctr), "Actifs": int((ctr["statut"] == "active").sum()),
                                 "ESI": len(progs), "Logements": int(sum(by_prog.get(p, 0) for p in progs))})
                table = pd.DataFrame(rows).sort_values(["Contrats", "Métier"], ascending=[False, True])
                table["Inactifs"] = table["Contrats"] - table["Actifs"]
                top = int(table["Contrats"].max())
                body = "".join(
                    f'<div class="pf-row"><span>{escape(r.Métier)}</span>'
                    f'<span class="pf-mbar"><i style="width:{100 * r.Actifs / top:.0f}%"></i><u style="width:{100 * r.Inactifs / top:.0f}%"></u>'
                    f'<em>{r.Contrats}</em></span><span>{r.Actifs}</span><span>{r.Inactifs}</span>'
                    f'<span>{fr_int(r.ESI)}</span><span>{fr_int(r.Logements)}</span></div>' for r in table.itertuples())
                st.markdown('<div class="pf-table"><div class="pf-row head"><span>MÉTIER</span><span>CONTRATS</span><span>ACTIFS</span>'
                            '<span>INACTIFS</span><span>ESI</span><span>LOGEMENTS</span></div>' + body +
                            f'<div class="pf-row total"><span>Total</span><span>{n_contracts}</span><span>{n_active}</span>'
                            f'<span>{n_inactive}</span><span>{fr_int(esi)}</span><span>{fr_int(n_housings)}</span></div></div>',
                            unsafe_allow_html=True)
                download_xlsx(table[["Métier", "Contrats", "Actifs", "Inactifs", "ESI", "Logements"]],
                              f"rex_{pid}_metiers.xlsx", "export_pf_metiers", label="")
            else:
                note("Aucun contrat pour ce prestataire sur ce périmètre.")

        with st.container(key="pf_card_ctrlist"):
            card_title("Liste des contrats", "Tous les contrats du prestataire sur le périmètre filtré, avec les ESI et logements rattachés")
            if n_contracts:
                try:
                    det = q.contract_details(list(contracts["contrat"])).set_index("contrat")
                except Exception:
                    det = pd.DataFrame()
                by_prog2 = (housings.set_index("programme")["logements"].to_dict() if housings is not None and len(housings) else {})
                crow = []
                for ref, grp in cov.groupby("contrat"):
                    progs = grp["programme"].dropna().unique()
                    d = det.loc[ref] if len(det) and ref in det.index else None
                    def _d(v):
                        if v is None or (not hasattr(v, "year") and pd.isna(v)):
                            return "–"
                        try:
                            if hasattr(v, "year") and v.year >= 2262:
                                return "Sans fin"  # dates sentinelles (9999-12-31) hors limites pandas
                            return v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else pd.to_datetime(v).strftime("%d/%m/%Y")
                        except Exception:
                            return "–"
                    crow.append({"Contrat": ref, "Libellé": (d["libelle"] if d is not None and pd.notna(d["libelle"]) else "–"),
                                 "Métier": grp["metier"].iloc[0], "Statut": "Actif" if grp["statut"].iloc[0] == "active" else "Inactif",
                                 "Début": _d(d["debut"]) if d is not None else "–", "Fin": _d(d["fin"]) if d is not None else "–",
                                 "ESI": len(progs), "Logements": int(sum(by_prog2.get(p, 0) for p in progs))})
                ctable = pd.DataFrame(crow).sort_values(["Statut", "Métier", "Contrat"])
                st.dataframe(ctable, width="stretch", hide_index=True, height=min(38 + 35 * len(ctable) + 3, 520))
                download_xlsx(ctable, f"rex_{pid}_contrats.xlsx", "export_pf_contrats", label="")
            else:
                note("Aucun contrat pour ce prestataire sur ce périmètre.")
    with tab_int:
        pvm = None
        try:
            pvm = q.provider_prev(pid, filters, start, end)
        except Exception:
            pass
        c_l, c_r = st.columns(2)
        with c_l.container(key="pf_card_cur"):
            card_title("Curatives", "Délais contractuels sur la période",
                       "Délai : prise en charge hors délai pour les interventions en cours, résolution hors délai pour les clôturées. "
                       "Les curatives sans SLA ou sans durée exploitable ne sont jamais comptées dans les comparables.")
            sub = status[status["work_type"] == "corrective"]
            if len(sub):
                total = int(sub["n"].sum())
                active_n = int(sub[~sub["status"].isin(STATUS_INACTIVE)]["n"].sum())
                comp = int(sum(r.comp_res if r.status in STATUS_DONE else r.comp_pec for r in sub.itertuples()))
                late = int(sum(r.late_res if r.status in STATUS_DONE else r.late_pec for r in sub.itertuples()))
                late_active = int(sum(r.late_pec for r in sub.itertuples() if r.status not in STATUS_INACTIVE))
                rate = fr_pct(100 * late / comp) if comp else "n/d"
                st.markdown(status_panel("bad", rate, "hors délai", f"{fr_int(late)} sur {fr_int(comp)} interventions comparables",
                                         [("Interventions", fr_int(total)), ("Actives", fr_int(active_n)),
                                          ("Actives hors délai", fr_int(late_active))], sub, total), unsafe_allow_html=True)
            else:
                note("Aucune intervention curative sur ce périmètre.")
        with c_r.container(key="pf_card_prev"):
            card_title("Préventives", "Passages créés sur la période, réalisation sur la date prévue",
                       "Les passages sont comptés sur leur date de création. Le prévu et le réalisé (date prévue) sont dans les chiffres clés.")
            sub = status[status["work_type"] == "preventive"]
            if len(sub) and pvm is not None:
                total = int(sub["n"].sum())
                prevus, realises = int(pvm["prevus"]), int(pvm["realises"])
                retard = int(pvm["realises_en_retard"]) + int(pvm["en_retard"])
                taux = fr_pct(100 * realises / prevus, 0) if prevus else "n/d"
                st.markdown(status_panel("good", taux, "réalisés", f"{fr_int(realises)} réalisés sur {fr_int(prevus)} prévus",
                                         [("Passages", fr_int(total)), ("Prévus", fr_int(prevus)), ("En retard", fr_int(retard))],
                                         sub, total), unsafe_allow_html=True)
            else:
                note("Aucune intervention préventive sur ce périmètre.")

        render_provider_interventions(pid, status)

    with tab_eq:
        with st.container(key="pf_card_equip"):
            card_title("Équipements concernés", "Équipements sur lesquels le prestataire est intervenu sur la période, les plus sollicités d'abord. "
                       "Les interventions sans équipement sont listées plus bas : menu de la colonne Équipement, « Sans équipement ».",
                       "Équipements distincts de toutes les interventions du prestataire (curatives et préventives), pas seulement les curatives.")
            try:
                eql = q.provider_equipment_list(pid, filters, start, end)
            except Exception as exc:
                eql = None
                st.error(f"Équipements indisponibles : {exc}")
            if eql is not None and len(eql):
                show = eql.rename(columns={"equipement": "Équipement", "libelle": "Libellé", "type": "Type", "curatives": "Curatives",
                                           "preventives": "Préventives", "derniere": "Dernière intervention"})
                show["Dernière intervention"] = pd.to_datetime(show["Dernière intervention"], utc=True).dt.strftime("%d/%m/%Y")
                st.dataframe(fr.traduire(show), width="stretch", hide_index=True, height=300)
                download_xlsx(show, f"rex_{pid}_equipements.xlsx", "export_pf_equip", label="")
            elif eql is not None:
                note("Aucune intervention avec équipement sur cette période.")
            sans = equip["sans_equipement"]
            st.caption(f"{fr_int(sans)} interventions du prestataire n'ont aucun équipement renseigné (tout l'historique, filtres patrimoine).")


LIST_PER_PAGE = 10
PFL = "pf"
PFL_COLS = ["reference", "statut", "creation", "equipement", "delai", "pec", "res", "fin", "cause", "metier", "type", "contrat"]
PFL_CSS = "1.3fr 1fr .7fr 1fr 1fr .85fr .85fr 1.2fr 1fr .85fr .75fr .85fr"
TYPE_FR = {"corrective": "Curative", "preventive": "Préventive"}
DELAI_FR = {"late": "Hors délai", "ok": "Dans les délais", "sans": "Sans conclusion"}


def equip_cell(ref):
    """Équipement concerné, ou mention explicite quand l'intervention n'en a pas."""
    if ref is None or pd.isna(ref) or not str(ref).strip() or str(ref) == "Sans équipement":
        return '<span class="pf-eq none">Sans équipement</span>'
    return f'<span class="pf-eq">{escape(str(ref))}</span>'


def render_provider_interventions(pid, status_df):
    """Liste paginée des interventions du prestataire (période et filtres actifs)."""
    with st.container(key="pf_card_list"):
        if not list_header("pf", "Liste des interventions", "Interventions du prestataire sur la période et les filtres actifs, les plus récentes d'abord",
                           "Une intervention est hors délai quand sa prise en charge ou sa résolution a pris plus de temps que le délai prévu au contrat. "
                           "Sans délai au contrat ou sans durée exploitable, on n'affiche rien (tiret)."):
            return
        c1, c3, c3b, c4 = st.columns([2.2, 3.6, 1.5, 0.6], vertical_alignment="center")
        with c1:
            cat = st.segmented_control("Type", ["Tous", "Curatives", "Préventives"], default="Tous", key="pfl_cat",
                                       label_visibility="collapsed") or "Tous"
        with c3:
            needle = st.text_input("Recherche", key="pfl_search", label_visibility="collapsed", icon=":material/search:",
                                   placeholder="Rechercher une référence, un équipement, un contrat...")
        wt = {"Curatives": "corrective", "Préventives": "preventive"}.get(cat)
        etat_col = colui.etat(PFL, PFL_COLS)
        extra = colf.appliquer(etat_col, PFL_COLS)
        with c3b:
            n_col = len(etat_col["v"]) + len(etat_col["t"]) + len(etat_col["n"])
            if n_col or etat_col["tri"]:
                st.button(f"Effacer les filtres ({n_col})" if n_col else "Effacer le tri", key="pfl_clear", on_click=colui.tout_effacer,
                          args=(PFL, PFL_COLS), icon=":material/filter_alt_off:", width="stretch")
        try:
            total = q.provider_interventions_total(pid, filters, start, end, wt, None, needle, None, extra)
        except Exception as exc:
            st.error(f"Liste des interventions indisponible : {exc}")
            return
        signature = (pid, cat, needle, repr(etat_col))
        if st.session_state.get("pfl_sig") != signature:  # un filtre a changé : retour à la première page
            st.session_state.pfl_sig = signature
            st.session_state.pfl_page = 1
        pages = max(1, -(-total // LIST_PER_PAGE))
        page_no = min(max(int(st.session_state.get("pfl_page", 1)), 1), pages)
        try:
            rows = q.provider_interventions(pid, filters, start, end, wt, None, needle,
                                            LIST_PER_PAGE, (page_no - 1) * LIST_PER_PAGE, None, extra)
        except Exception as exc:
            st.error(f"Liste des interventions indisponible : {exc}")
            return
        with c4:
            if len(rows):
                def _pf_export(d):
                    d = d.assign(status=d["status"].map(lambda s: STATUS_FR.get(s, s)), type_fin=d["type_fin"].map(lambda v: fr.libelle(v) if pd.notna(v) else None),
                                 cause=d["cause"].map(lambda v: fr.libelle(v) if pd.notna(v) else None))
                    return d[["reference", "equipment_reference", "status", "type_fin", "motif", "cause", "work_type", "creation_date", "contract_topic",
                              "contract_reference", "sla_pec", "pec_heures", "sla_res", "res_heures", "late_flag"]]
                download_xlsx(_pf_export(rows), f"rex_{pid}_interventions_p{page_no}.xlsx", "export_pf_list", label="",
                              loader=lambda: _pf_export(q.provider_interventions(pid, filters, start, end, wt, None, needle, 100000, 0, None, extra)),
                              sig=repr(signature), total=total)
        try:
            metiers = q.options("Métier", {**filters, "Prestataire": [str(pid)]}, start, end)
            metiers = dict(zip(metiers["reference"], metiers["libelle"]))
        except Exception:
            metiers = {}
        colui.en_tete(PFL, [("reference", "Référence"), ("statut", "Statut"), ("creation", "Créée"), ("equipement", "Équipement"),
                            ("delai", "Délai"), ("pec", "PEC"), ("res", "Résol."),
                            ("fin", "Clôture · motif"), ("cause", "Cause technique"), ("metier", "Métier"), ("type", "Type"), ("contrat", "Contrat")],
                      PFL_CSS, {"statut": {k: STATUS_FR[k] for k in STATUS_ORDER}, "type": TYPE_FR, "delai": DELAI_FR, "metier": metiers, "fin": fr.TYPE_FIN})
        if not len(rows):
            note("Aucune intervention ne correspond aux filtres.")
            return
        body = []
        for r in rows.itertuples():
            s = str(r.status)
            color = STATUS_TONE.get(s, "#5F566A")
            label = STATUS_FR.get(s, s.replace("_", " ").capitalize())
            causes = []
            if r.late_pec is True:
                causes.append("prise en charge")
            if r.late_res is True:
                causes.append("résolution")
            if r.late_flag == "late":
                delay = f'<span class="pf-tag late">Hors délai</span><br><small>{escape(" et ".join(causes))}</small>'
            elif r.late_flag == "ok":
                delay = '<span class="pf-tag ok">Dans les délais</span>'
            else:
                delay = '<span class="pf-dash">–</span>'
            pec = fr.duree(r.pec_heures)
            res = fr.duree(r.res_heures)
            kind = "Curative" if r.work_type == "corrective" else ("Préventive" if r.work_type == "preventive" else escape(str(r.work_type)))
            fin = f'<b>{escape(fr.libelle(r.type_fin))}</b>' if pd.notna(r.type_fin) else '<span class="pf-dash">–</span>'
            if pd.notna(r.motif):
                fin += f'<br><small title="{escape(str(r.motif))}">{escape(str(r.motif))[:60]}</small>'
            cause = escape(fr.libelle(r.cause)) if pd.notna(r.cause) else '<span class="pf-dash">–</span>'
            body.append(
                f'<div class="pf-lrow"><span class="pf-lref" style="border-left-color:{color}"><b>{escape(str(r.reference))}</b></span>'
                f'<span><span class="pf-spill" style="background:{color}22;color:{color}">● {escape(label)}</span></span>'
                f'<span>{fr_date(r.creation_date, "%d/%m/%y")}</span><span>{equip_cell(r.equipment_reference)}</span><span>{delay}</span>'
                f'<span>{pec}{"<br><small>SLA " + escape(r.sla_pec) + "</small>" if r.sla_pec else ""}</span>'
                f'<span>{res}{"<br><small>SLA " + escape(r.sla_res) + "</small>" if r.sla_res else ""}</span>'
                f'<span>{fin}</span><span>{cause}</span>'
                f'<span><span class="pf-mtag">{escape(str(r.contract_topic)) if pd.notna(r.contract_topic) else "–"}</span></span>'
                f'<span><b>{kind}</b></span><span>{escape(str(r.contract_reference)) if pd.notna(r.contract_reference) else "–"}</span></div>')
        st.markdown(f'<div class="pf-ltable" style="--cols:{PFL_CSS};margin-top:.2rem">' + "".join(body) + "</div>", unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns([5, 0.5, 1.6, 0.5], vertical_alignment="center")
        first = (page_no - 1) * LIST_PER_PAGE + 1
        f1.caption(f"{first} à {first + len(rows) - 1} sur {fr_int(total)} interventions")
        if f2.button("‹", key="pfl_prev", disabled=page_no <= 1):
            st.session_state.pfl_page = page_no - 1
            st.rerun()
        f3.markdown(f'<div class="pf-pageno">Page {page_no} / {fr_int(pages)}</div>', unsafe_allow_html=True)
        if f4.button("›", key="pfl_next", disabled=page_no >= pages):
            st.session_state.pfl_page = page_no + 1
            st.rerun()


# ---------------------------------------------------------------- pages
try:  # l'adresse suit la page (et la fiche prestataire ouverte) pour retrouver sa place après un rafraîchissement
    if st.query_params.get("page") != st.session_state.page:
        st.query_params["page"] = st.session_state.page
    _pid = st.session_state.get("provider_id") if st.session_state.page == "Prestataires" else None
    if _pid:
        st.query_params["prestataire"] = str(_pid)
    elif "prestataire" in st.query_params:
        del st.query_params["prestataire"]
except Exception:
    pass
if st.session_state.page == "Prestataires":
    if st.session_state.provider_id:
        render_provider_sheet(st.session_state.provider_id)
    else:
        render_providers()
    st.stop()
if st.session_state.page in PAGE_TITLES:
    from views import interventions as views_interventions

    def open_provider_page(provider_id):
        st.session_state.page = "Prestataires"
        open_provider(provider_id)

    views_interventions.render(st.session_state.page, filters, start, end, dict(
        fr_int=fr_int, fr_pct=fr_pct, fr_date=fr_date, card_title=card_title, note=note, svg=svg,
        download_xlsx=download_xlsx, list_header=list_header, AVATAR_COLORS=AVATAR_COLORS, provider_initials=provider_initials,
        open_provider_page=open_provider_page))
    st.stop()
if st.session_state.page == "Anomalies":
    render_anomalies()
    st.stop()

# ---------------------------------------------------------------- KPI
try:
    k = q.global_kpis(filters, start, end)
except Exception as exc:
    st.error(f"Calcul des KPI impossible : {exc}")
    st.stop()

# Le KPI est explicite : numérateur et dénominateur issus de la même table agrégée.
num = as_int(k["hors_delai_pec"])
den = as_int(k["comparables_pec"])
pct = as_pct(num, den)


def kpi_markup(icon, tone, label, info, value, sub, accent=False):
    return (f'<div class="kpi-top"><span class="kpi-icon {tone}">{svg(icon, 20)}</span>'
            f'<span class="kpi-label">{escape(label)}</span>{tip(info)}</div>'
            f'<div class="kpi-value{" accent" if accent else ""}">{value}</div><div class="kpi-sub">{sub}</div>')


# Période précédente de même durée : sert aux évolutions des quatre chiffres clés et à la phrase de synthèse.
try:
    from services import interv as _iv
    _ps, _pe = _iv._prev_window(start, end)
    kp = q.global_kpis(filters, _ps, _pe)
except Exception:
    kp = None


def _rates(kk):
    """Les quatre mesures : volume, taux hors délai, taux de réalisation, taux de rapports manquants (None si non calculable)."""
    if kk is None:
        return None, None, None, None
    return (as_int(kk["total_operations"]), as_pct(as_int(kk["hors_delai_pec"]), as_int(kk["comparables_pec"])),
            as_pct(as_int(kk["realises"]), as_int(kk["prevus"])),
            as_pct(as_int(kk["rapport_sans"]), as_int(kk["rapport_avec"]) + as_int(kk["rapport_sans"])))


_cur = _rates(k)
_old = _rates(kp)


def delta_chip(cur, old, bad_up, pct_change=False):
    """Évolution par rapport à la période précédente : pastille verte si c'est bon, rouge si c'est mauvais."""
    if cur is None or old is None or (pct_change and not old):
        return '<span class="kd flat">pas de période précédente comparable</span>'
    d = 100 * (cur - old) / old if pct_change else cur - old
    if abs(d) < (0.5 if pct_change else 0.05):
        return '<span class="kd flat">= stable vs période précédente</span>'
    tone = "flat" if bad_up is None else ("bad" if (d > 0) == bad_up else "good")
    unit = " %" if pct_change else " pt"
    txt = f'{"+" if d > 0 else "−"}{abs(d):.1f}'.replace(".", ",") + unit
    return f'<span class="kd {tone}">{"▲" if d > 0 else "▼"} {txt} vs période précédente</span>'


def _evo(cur, old, unit_pt=True):
    if cur is None or old is None:
        return ""
    d = cur - old
    return f" ({'+' if d >= 0 else '−'}{abs(d):.1f}".replace(".", ",") + (" pt)" if unit_pt else " %)")


_tot, _hd, _re, _rm = _cur
_vol_pct = (100 * (_tot - _old[0]) / _old[0]) if (_old[0] and _tot is not None) else None
_bits = [f"<b>{fr_int(_tot)} interventions</b> sur la période"
         + (f" ({'+' if _vol_pct >= 0 else '−'}{abs(_vol_pct):.0f} % vs période précédente)" if _vol_pct is not None else "")]
st.markdown(f'<div class="an-story"><b>{_bits[0]}.</b></div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
sans_sla = as_int(k["sans_sla"])
horsref = as_int(k["curatives_hors_refus"])
prevus, realises = as_int(k["prevus"]), as_int(k["realises"])
rap_ok, rap_ko, rap_unk = as_int(k["rapport_avec"]), as_int(k["rapport_sans"]), as_int(k["rapport_inconnu"])
with k1.container(key="kpi_1"):
    n_def = as_int(k["prevus_date_defaut"]) if k["prevus_date_defaut"] else 0
    st.markdown(kpi_markup("calendar", "rose", "Interventions sur la période",
                           f"{fr_int(as_int(k['total_operations']))} interventions sur la période : {fr_int(as_int(k['curatives']))} curatives créées "
                           f"et {fr_int(prevus)} préventives prévues.\n\n"
                           "Comment c'est calculé : les curatives sont celles dont la date de création tombe dans la période, refusées et annulées comprises. "
                           "Les préventives sont les passages dont la date prévue tombe dans la période"
                           + (f" ; pour {fr_int(n_def)} d'entre eux la date prévue n'existe pas, la date de création est alors utilisée." if n_def
                              else "."),
                           fr_int(as_int(k["total_operations"])), "curatives et préventives prévues", accent=True),
                unsafe_allow_html=True)
with k2.container(key="kpi_2"):
    st.markdown(kpi_markup("clock", "rose", "Curatif hors délai",
                           (f"{fr_int(num)} prises en charge curatives dépassent le délai du contrat, soit {fr_pct(pct)} des {fr_int(den)} curatives comparables."
                            if pct is not None else "Aucune prise en charge curative comparable sur la période.")
                           + "\n\nComment c'est calculé : une prise en charge est hors délai quand sa durée dépasse le SLA d'intervention. "
                           "Taux = hors délai / comparables. Une curative est comparable quand son SLA est connu et que sa durée est exploitable."
                           + (f"\n\nNon comparables : {fr_int(sans_sla)} curatives sans SLA ({fr_pct(as_pct(sans_sla, horsref))} des curatives hors refus). "
                              "Les durées absentes ou négatives (-1) ne permettent aucune conclusion, et les durées à 0 ms sont exclues du calcul." if horsref else ""),
                           fr_int(num), (f"{fr_pct(pct)} des comparables" if pct is not None else "aucune comparable")),
                unsafe_allow_html=True)
with k3.container(key="kpi_3"):
    taux_real = as_pct(realises, prevus)
    st.markdown(kpi_markup("check", "green", "Taux de réalisation préventive",
                           f"{fr_int(realises)} préventives réalisées sur {fr_int(prevus)} prévues"
                           + (f", soit {fr_pct(taux_real)}." if taux_real is not None else ".")
                           + "\n\nComment c'est calculé : une préventive est réalisée quand elle est clôturée avec un type de fin « réalisée » ou « résolue ». "
                           "Les prévues sont les passages dont la date prévue tombe dans la période"
                           + (f" ({fr_int(as_int(k['prevus_date_defaut']))} sont classés sur leur date de création faute de date prévue)."
                              if k["prevus_date_defaut"] else "."),
                           fr_pct(taux_real) if taux_real is not None else "N/D",
                           f"{fr_int(realises)} sur {fr_int(prevus)} prévues"),
                unsafe_allow_html=True)
with k4.container(key="kpi_4"):
    verifies = rap_ok + rap_ko
    tx_manq = as_pct(rap_ko, verifies)
    st.markdown(kpi_markup("file", "violet", "Rapports manquants",
                           f"{fr_int(rap_ko)} interventions clôturées sans rapport sur {fr_int(verifies)} dont les documents ont été vérifiés"
                           + (f", soit {fr_pct(tx_manq)}." if tx_manq is not None else ".")
                           + "\n\nComment c'est calculé : taux = sans rapport / (avec rapport + sans rapport). "
                           f"Les {fr_int(rap_unk)} interventions non vérifiées (récupération des documents par l'API encore en cours) "
                           "ne sont jamais comptées comme sans rapport.",
                           fr_pct(tx_manq) if tx_manq is not None else "N/D",
                           f"{fr_int(rap_ko)} sur {fr_int(verifies)} vérifiées"),
                unsafe_allow_html=True)


# ---------------------------------------------------------------- évolution
with st.container(key="card_trend"):
    h1, h2, h3 = st.columns([5, 1.6, 0.9], vertical_alignment="top")
    with h1:
        card_title("Évolution de la performance", "Choisis un indicateur : on te dit où il en est, et si c'est mieux ou moins bien qu'au début.",
                   "Chaque point est un taux : le nombre de cas concernés divisé par la base indiquée. "
                   "Prise en charge et résolution hors délai : curatives hors délai / curatives comparables. "
                   "Préventif réalisé : réalisés / prévus. Préventif en retard : en retard / passages dont la ponctualité est jugeable. "
                   "Préventif non réalisé : clôturés non réalisés ou actuellement en retard / prévus. "
                   "Rapports manquants : sans rapport / (avec + sans), curatives et préventives clôturées vérifiées. "
                   "La ligne en pointillés est la moyenne de la période : vert = mieux que la moyenne, rouge = moins bien.")
    with h2:
        grain = st.segmented_control("Granularité", ["Mensuel", "Annuel"], default="Mensuel", key="grain",
                                     label_visibility="collapsed") or "Mensuel"
    chosen = st.pills("Indicateur", list(TREND_IND), selection_mode="single", default=TREND_DEFAULT, key="trend_ind1",
                      format_func=lambda k: TREND_IND[k][0], label_visibility="collapsed") or TREND_DEFAULT
    try:
        trend = q.trend(filters, start, end, grain)
        with h3:
            if len(trend):
                download_xlsx(trend_export(trend), "rex_evolution.xlsx", "export_trend", label="")
        ser = trend_series(trend, grain, chosen) if len(trend) else None
        if ser is None:
            note("Aucune donnée pour cet indicateur sur la période et les filtres actifs.")
        else:
            tone, head, sub, avg = trend_story(ser, chosen)
            hint = "Plus c'est bas, mieux c'est." if TREND_SENS[chosen] == "bad" else "Plus c'est haut, mieux c'est."
            st.markdown(f'<div class="tr-story {tone}"><div>{head}</div><span>{sub}</span></div>'
                        f'<div class="legend wrap"><span><i style="background:#173B69"></i>{escape(TREND_IND[chosen][0])}'
                        f'<small> · base {fr_int(int(ser["d"].sum()))} {TREND_IND[chosen][4]}</small></span>'
                        f'<span class="tr-hint">{hint} Pointillés : moyenne ({avg:.0f} %).</span></div>', unsafe_allow_html=True)
            st.plotly_chart(trend_figure(ser, chosen, avg), width="stretch", config={"displaylogo": False, "displayModeBar": False})
    except Exception as exc:
        st.error(f"Évolution indisponible : {exc}")

# ---------------------------------------------------------------- localisation et récurrence
left, right = st.columns(2)


def card_header(title, description, info, export=None):
    """Titre à gauche, bouton d'export à droite (comme dans la maquette)."""
    head, action = st.columns([8, 1], vertical_alignment="top")
    with head:
        card_title(title, description, info)
    if export is not None:
        with action:
            download_xlsx(*export, label="")


with left.container(key="card_zones"):
    level = st.session_state.get("zone_level", "Agence")
    zone_sort = st.session_state.get("zone_sort") or "Décroissant"
    z, zone_error, zone_exception = None, None, None
    try:
        z, zone_error = q.zones(filters, start, end, level, limit=ZONES_LIMIT, descending=zone_sort == "Décroissant")
    except Exception as exc:
        zone_exception = exc
    has_zones = z is not None and len(z) > 0
    card_header("Localisation des interventions", "Quels périmètres concentrent le plus d'interventions ? Curatives, période filtrée.",
                "Interventions curatives non refusées par périmètre, sur la date de création. Tous les filtres s'appliquent.",
                export=(z.drop(columns=["total_pannes"]).rename(columns={"nb_pannes": "nb_interventions"}), "rex_interventions_zones.xlsx", "export_zones") if has_zones else None)
    c1, c2 = st.columns([1.2, 1.3], vertical_alignment="center")
    with c1:
        st.selectbox("Périmètre", ["Société", "Agence", "Groupe", "Secteur", "Programme"], index=1, key="zone_level",
                     label_visibility="collapsed", format_func=lambda v: f"Périmètre :  {v}")
    with c2:
        st.segmented_control("Tri", ["Décroissant", "Croissant"], default="Décroissant", key="zone_sort",
                             label_visibility="collapsed")
    if zone_exception:
        st.error(f"Classement indisponible : {zone_exception}")
    elif zone_error:
        note(zone_error + " Supprime ce filtre pour afficher ce classement.")
    elif has_zones:
        st.markdown(f'<div class="rk">{rank_zone_rows(z, level)}</div>', unsafe_allow_html=True)
        more = " - faites défiler pour voir la suite" if len(z) > 5 else ""
        st.markdown(f'<div class="rk-foot">{len(z)} {level.lower()}s{more}</div>', unsafe_allow_html=True)
    else:
        note("Aucune donnée sur cette période.")

with right.container(key="card_equipments"):
    eq_sort = st.session_state.get("eq_sort") or "Décroissant"
    eq, eq_error, eq_exception = None, None, None
    try:
        eq, eq_error = q.equipments(filters, start, end, limit=EQUIPMENTS_LIMIT, descending=eq_sort == "Décroissant")
        if eq is not None and len(eq):
            try:
                context = q.equipment_context(eq["equipment_reference"].tolist(), start, end)
            except Exception:  # le classement reste affiché sans prestataire
                context = pd.DataFrame(columns=["equipment_reference", "provider_name", "programme_reference", "agence_label"])
            eq = eq.merge(context, on="equipment_reference", how="left")
    except Exception as exc:
        eq_exception = exc
    has_eq = eq is not None and len(eq) > 0
    card_header("Récurrence par équipement", "Quels équipements concentrent le plus d'interventions curatives ? Classement sur la période filtrée.",
                "Le prestataire et la résidence sont ceux de l'intervention la plus récente de la période "
                "pour l'équipement.",
                export=(eq.rename(columns={"nb_pannes": "nb_interventions", "derniere_panne": "derniere_intervention"}), "rex_interventions_equipements.xlsx", "export_equipments") if has_eq else None)
    _, c2 = st.columns([1.2, 1.3], vertical_alignment="center")
    with c2:
        st.segmented_control("Tri équipements", ["Décroissant", "Croissant"], default="Décroissant", key="eq_sort",
                             label_visibility="collapsed")
    if eq_exception:
        st.error(f"Classement indisponible : {eq_exception}")
    elif eq_error:
        note(eq_error + " Supprime ce filtre pour afficher ce classement.")
    elif has_eq:
        st.markdown(f'<div class="rk">{rank_equipment_rows(eq)}</div>', unsafe_allow_html=True)
        more = " - faites défiler pour voir la suite" if len(eq) > 6 else ""
        st.markdown(f'<div class="rk-foot">{len(eq)} équipements{more}</div>', unsafe_allow_html=True)
    else:
        note("Aucune donnée sur cette période.")

# ---------------------------------------------------------------- liste des interventions
from services.interv import _sla_text as q_sla

with st.container(key="card_vg_list"):
    _vg_open = list_header("vg", "Liste des interventions", "Les références des interventions de la période et des filtres actifs, les plus récentes d'abord. "
                          "Recherche par référence, équipement ou contrat.",
                          "Curatives et préventives, selon la date de création. Pour isoler les interventions sans équipement, ouvre le menu de la colonne Équipement.")
    if _vg_open:
        c2, c3, c4 = st.columns([3.6, 1.2, 0.6], vertical_alignment="center")
        with c2:
            vg_cat = "Toutes"
            vg_needle = st.text_input("Recherche", key="vgl_search", label_visibility="collapsed", icon=":material/search:",
                                      placeholder="Rechercher une référence, un équipement, un contrat...")
        VGL_COLS = ["reference", "type", "statut", "creation", "equipement", "delai", "pec", "res", "fin", "prestataire", "metier", "contrat"]
        VGL_CSS = "1.2fr .8fr 1fr .75fr 1.2fr .9fr .6fr .65fr 1.2fr 1.15fr .95fr .85fr"
        etat_vg = colui.etat("vg", VGL_COLS)
        extra_vg = colf.appliquer(etat_vg, VGL_COLS)
        with c3:
            n_vg = len(etat_vg["v"]) + len(etat_vg["t"]) + len(etat_vg["n"])
            if n_vg or etat_vg["tri"]:
                st.button(f"Effacer ({n_vg})" if n_vg else "Effacer le tri", key="vgl_clear", on_click=colui.tout_effacer,
                          args=("vg", VGL_COLS), icon=":material/filter_alt_off:")
        sig = (vg_cat, vg_needle, repr(filters), str(start), str(end), repr(etat_vg))
        if st.session_state.get("vgl_sig") != sig:
            st.session_state.vgl_sig = sig
            st.session_state.vgl_page = 1
        VG_PER_PAGE = 15
        vg_page = int(st.session_state.get("vgl_page", 1))
        try:
            vg_df, _ = q.details(filters, start, end, vg_cat, VG_PER_PAGE, (vg_page - 1) * VG_PER_PAGE, vg_needle, extra_vg)
            vg_total = q.details_total(filters, start, end, vg_cat, vg_needle, extra_vg)
        except Exception as exc:
            vg_df, vg_total = None, 0
            st.error(f"Liste indisponible : {exc}")
        def _lib(label):
            try:
                o = q.options(label, {**filters, label: []}, start, end)
                return dict(zip(o["reference"].astype(str), o["libelle"]))
            except Exception:
                return {}
        if vg_df is not None:
            colui.en_tete("vg", [("reference", "Référence"), ("type", "Type"), ("statut", "Statut"), ("creation", "Créée"), ("equipement", "Équipement"),
                                 ("delai", "Délai"), ("pec", "PEC"), ("res", "Résol."), ("fin", "Clôture · motif"), ("prestataire", "Prestataire"),
                                 ("metier", "Métier"), ("contrat", "Contrat")], VGL_CSS,
                          {"fin": fr.TYPE_FIN, "type": TYPE_FR, "statut": {k: STATUS_FR[k] for k in STATUS_ORDER}, "delai": DELAI_FR,
                           "prestataire": _lib("Prestataire"), "metier": _lib("Métier")})
        if vg_df is not None and len(vg_df):
            def _vg_export(d):
                shown = d.assign(
                    work_type=d["work_type"].map({"corrective": "Curative", "preventive": "Préventive"}),
                    status=d["status"].map(lambda v: STATUS_FR.get(v, v)),
                    creation_date=pd.to_datetime(d["creation_date"], utc=True).dt.strftime("%d/%m/%Y"),
                    equipment_reference=d["equipment_reference"].fillna("Sans équipement"),
                    sla_pec=[q_sla(a, b) for a, b in zip(d["sla_intervention_value"], d["sla_intervention_unit"])],
                    sla_res=[q_sla(a, b) for a, b in zip(d["sla_recovery_value"], d["sla_recovery_unit"])],
                    pec_heures=pd.to_numeric(d["pec_heures"], errors="coerce").astype(float).round(1),
                    res_heures=pd.to_numeric(d["res_heures"], errors="coerce").astype(float).round(1))
                shown = shown[["reference", "work_type", "status", "creation_date", "equipment_reference", "equipment_label", "delai", "sla_pec", "pec_heures",
                               "sla_res", "res_heures", "provider_name", "contract_reference", "metier", "agence_label", "programme_reference"]]
                shown = shown.rename(columns={"reference": "Référence", "work_type": "Type", "status": "Statut", "creation_date": "Créée le",
                                              "equipment_reference": "Équipement", "equipment_label": "Libellé équipement", "delai": "Délai", "type_fin": "Type de fin", "motif": "Motif de clôture ou d'annulation", "sla_pec": "SLA intervention",
                                              "pec_heures": "Prise en charge (h)", "sla_res": "SLA résolution", "res_heures": "Résolution (h)", "provider_name": "Prestataire",
                                              "contract_reference": "Contrat", "metier": "Métier", "agence_label": "Agence", "programme_reference": "Programme"})
                return shown

            shown = _vg_export(vg_df)
            with c4:
                download_xlsx(shown, f"rex_interventions_p{vg_page}.xlsx", "export_vg_list", label="",
                              loader=lambda: _vg_export(q.details(filters, start, end, vg_cat, 100000, 0, vg_needle, extra_vg)[0]), sig=repr(sig), total=vg_total)
            body = []
            for r in vg_df.itertuples():
                s_ = str(r.status)
                tone = STATUS_TONE.get(s_, "#5F566A")
                if r.delai == "Hors délai":
                    dl = '<span class="pf-tag late">Hors délai</span>'
                elif r.delai == "Dans les délais":
                    dl = '<span class="pf-tag ok">Dans les délais</span>'
                else:
                    dl = '<span class="pf-dash">–</span>'
                pec = fr.duree(r.pec_heures)
                res = fr.duree(r.res_heures)
                kind = "Curative" if r.work_type == "corrective" else "Préventive"
                fin = f'<b>{escape(fr.libelle(r.type_fin))}</b>' if pd.notna(r.type_fin) else '<span class="pf-dash">–</span>'
                if pd.notna(r.motif):
                    fin += f'<br><small title="{escape(str(r.motif))}">{escape(str(r.motif))[:60]}</small>'
                body.append(
                    f'<div class="pf-lrow"><span class="pf-lref" style="border-left-color:{tone}"><b>{escape(str(r.reference))}</b></span>'
                    f'<span><b>{kind}</b></span>'
                    f'<span><span class="pf-spill" style="background:{tone}22;color:{tone}">● {escape(STATUS_FR.get(s_, s_))}</span></span>'
                    f'<span>{fr_date(r.creation_date, "%d/%m/%y")}</span><span>{equip_cell(r.equipment_reference)}</span><span>{dl}</span>'
                    f'<span>{pec}</span><span>{res}</span><span>{fin}</span><span>{escape(str(r.provider_name)) if pd.notna(r.provider_name) else "–"}</span>'
                    f'<span><span class="pf-mtag">{escape(str(r.metier)) if pd.notna(r.metier) else "–"}</span></span>'
                    f'<span>{escape(str(r.contract_reference)) if pd.notna(r.contract_reference) else "–"}</span></div>')
            st.markdown(f'<div class="pf-ltable" style="--cols:{VGL_CSS};margin-top:.2rem">' + "".join(body) + "</div>", unsafe_allow_html=True)
            pages = max(1, -(-vg_total // VG_PER_PAGE))
            f1, f2, f3, f4 = st.columns([5, 0.5, 1.6, 0.5], vertical_alignment="center")
            f1.caption(f"{(vg_page - 1) * VG_PER_PAGE + 1} à {(vg_page - 1) * VG_PER_PAGE + len(vg_df)} sur {fr_int(vg_total)} interventions · export : choisis les colonnes dans le bouton de téléchargement")
            if f2.button("‹", key="vgl_prev", disabled=vg_page <= 1):
                st.session_state.vgl_page = vg_page - 1
                st.rerun()
            f3.markdown(f'<div class="pf-pageno">Page {vg_page} / {fr_int(pages)}</div>', unsafe_allow_html=True)
            if f4.button("›", key="vgl_next", disabled=vg_page >= pages):
                st.session_state.vgl_page = vg_page + 1
                st.rerun()
        elif vg_df is not None:
            note("Aucune intervention ne correspond aux filtres.")

st.markdown('<div class="defs">Définitions : « hors délai » = durée de prise en charge supérieure au SLA d\'intervention, '
            'sur les curatives dont le SLA et la durée sont exploitables. Les curatives sans SLA, ou dont la durée est absente, '
            'négative ou à 0, sont comptées à part et jamais dans le taux. Les classements par périmètre et par équipement excluent les interventions refusées.</div>',
            unsafe_allow_html=True)