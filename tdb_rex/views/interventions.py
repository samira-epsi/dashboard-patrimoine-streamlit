"""Pages Interventions : Curatives, Préventives (avec leur onglet Comparatif) et Qualité des rapports."""
from html import escape
from types import SimpleNamespace

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services import colf, colui, fr, vg, picker
from services import interv as iv

STATUS = {  # clé : (pluriel, singulier, couleur). Statuts réels de la source : open, pending, hold, closed, denied.
    "open": ("Ouvertes", "Ouverte", "#F78BC7"),
    "pending": ("En cours", "En cours", "#432ABD"),
    "hold": ("En attente", "En attente", "#F5A524"),
    "closed": ("Clôturées", "Clôturée", "#008080"),
    "canceled": ("Annulées", "Annulée", "#C9CFE0"),
    "denied": ("Refusées", "Refusée", "#8A91A6"),
}
ACTIVE_ORDER = {"corrective": ["open", "pending", "hold"], "preventive": ["open", "pending", "hold"]}
DONUT_ORDER = {"corrective": ["open", "pending", "hold", "closed", "canceled", "denied"],
               "preventive": ["open", "pending", "hold", "closed", "canceled", "denied"]}
INDICATORS = {"corrective": ["Volume par statut", "Taux hors délai"],
              "preventive": ["Volume par résultat", "Prévus vs réalisés", "Taux de retard"]}
CHIP_COLORS = ["#E5114D", "#173B69", "#0074FF", "#432ABD", "#008080", "#FFB7E3"]
PAGE_SIZE = 7
END_FR = fr.TYPE_FIN
LIST_COLS = {"corrective": ["reference", "statut", "creation", "equipement", "delai", "pec", "res", "fin", "cause", "metier", "prestataire", "contrat"],
             "preventive": ["reference", "statut", "prevue", "realisation", "equipement", "delai_prev", "retard", "fin", "metier", "prestataire", "contrat"]}
ENTETES = {
    "corrective": ([("reference", "Référence"), ("statut", "Statut"), ("creation", "Créée"), ("equipement", "Équipement"), ("delai", "Délai"),
                    ("pec", "Prise en charge"), ("res", "Résol."), ("fin", "Clôture · motif"), ("cause", "Cause technique"),
                    ("metier", "Métier"), ("prestataire", "Prestataire"), ("contrat", "Contrat")],
                   "1.3fr 1fr .7fr 1fr 1fr .85fr .85fr 1.25fr 1fr .85fr 1.15fr .85fr"),
    "preventive": ([("reference", "Référence"), ("statut", "Statut"), ("prevue", "Prévue le"), ("realisation", "Réalisée le"), ("equipement", "Équipement"),
                    ("delai_prev", "Ponctualité"), ("retard", "Retard"), ("fin", "Clôture · motif"), ("metier", "Métier"),
                    ("prestataire", "Prestataire"), ("contrat", "Contrat")],
                   "1.25fr 1fr .8fr .8fr 1fr 1.4fr .7fr 1.2fr .9fr 1.1fr .85fr"),
}
QUAL_COLS = ["reference", "equipement", "programme", "type", "metier", "prestataire", "cloturee", "rapport"]
QUAL_CSS = "1.4fr 1.1fr 1.8fr .9fr 1.1fr 1.4fr .8fr 1.4fr"
DELAI_LIB = {"corrective": {"late": "Hors délai", "ok": "Dans les délais", "sans": "Sans conclusion"},
             "preventive": colf.PONCT_LIB}
C = SimpleNamespace()  # outils fournis par app.py (fr_int, card_title, svg, ...)
_SCOPE = {}


def base_line(n, what):
    """Ligne « Base » sous le titre d'une carte : ce qui est compté et combien."""
    st.markdown(f'<div class="iv-base"><b>Base</b><span><em>{n_fmt(n)}</em> {escape(what)}</span></div>', unsafe_allow_html=True)


def _libelles(label, filters, start, end, **plus):
    """Correspondance code -> libellé d'un filtre (prestataire, métier) pour le menu de colonne ; vide si indisponible."""
    try:
        df = vg.options(label, {**filters, label: []}, start, end)
        return dict(zip(df["reference"].astype(str), df["libelle"]))
    except Exception:
        return {}


def n_fmt(value):
    return C.fr_int(value)


def pct_fmt(value, decimals=1):
    return C.fr_pct(value, decimals)


def avatar(name):
    color = C.AVATAR_COLORS[sum(ord(ch) for ch in str(name)) % len(C.AVATAR_COLORS)]
    return (f'<span class="iv-av" style="background:{color}">{escape(C.provider_initials(name)[:2])}</span>')


def pager(key, total, per_page=PAGE_SIZE):
    """Pagination simple ‹ Page x / y ›. Retourne la page courante (1 à n)."""
    pages = max(1, -(-total // per_page))
    page_no = min(max(int(st.session_state.get(key, 1)), 1), pages)
    return page_no, pages


def pager_controls(key, page_no, pages, total, shown, per_page=PAGE_SIZE):
    f1, f2, f3, f4 = st.columns([5, 0.5, 1.6, 0.5], vertical_alignment="center")
    first = (page_no - 1) * per_page + 1
    f1.caption(f"{first} à {first + shown - 1} sur {n_fmt(total)} lignes · export : choisis les colonnes dans le bouton de téléchargement")
    if f2.button("‹", key=f"{key}_prev", disabled=page_no <= 1):
        st.session_state[key] = page_no - 1
        st.rerun()
    f3.markdown(f'<div class="pf-pageno">Page {page_no} / {n_fmt(pages)}</div>', unsafe_allow_html=True)
    if f4.button("›", key=f"{key}_next", disabled=page_no >= pages):
        st.session_state[key] = page_no + 1
        st.rerun()


def guard(fn, label):
    """Exécute un bloc ; une donnée manquante ou une erreur s'affiche à la place du bloc, sans casser la page."""
    try:
        return fn()
    except NotImplementedError as exc:
        C.note(str(exc))
    except Exception as exc:
        st.error(f"{label} indisponible : {exc}")
    return None


# ---------------------------------------------------------------- blocs communs
def donut_card(df, wt, key):
    with st.container(key=f"iv_donut_{key}"):
        C.card_title("Répartition par statut", f"Interventions {'curatives' if wt == 'corrective' else 'préventives'} de la période")
        total = int(df["n"].sum())
        base_line(total, "interventions créées")
        order = [s for s in DONUT_ORDER[wt] if s in set(df["status"])]
        sub = df.set_index("status").loc[order]
        fig = go.Figure(go.Pie(labels=[STATUS[s][0] for s in order], values=sub["n"].tolist(), hole=.72, sort=False,
                               marker=dict(colors=[STATUS[s][2] for s in order]), textinfo="none", direction="clockwise"))
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                          annotations=[dict(text=f"<b>{n_fmt(total)}</b><br>interventions", showarrow=False,
                                            font=dict(size=20, family="Nunito, Segoe UI, Arial, sans-serif", color="#1F1A2E"))])
        c1, c2 = st.columns([1, 1.15], vertical_alignment="center")
        c1.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"donut_{key}")
        rows = "".join(
            f'<div class="iv-leg"><i style="background:{STATUS[s][2]}"></i><span>{STATUS[s][0]}</span>'
            f'<b>{n_fmt(r.n)}</b><small>{pct_fmt(100 * r.n / total)}</small></div>'
            for s, r in zip(order, sub.itertuples())) if total else ""
        c2.markdown(f'<div class="iv-legend">{rows}</div>', unsafe_allow_html=True)


def monthly_card(wt, key, filters, start, end):
    with st.container(key=f"iv_month_{key}"):
        C.card_title("Évolution annuelle" if st.session_state.get(f"grain_{key}") == "Annuel" else "Évolution mensuelle", "Par statut, sur la période filtrée" if wt == "corrective" else "Par résultat, prévus contre réalisés ou taux de retard, selon la date prévue")
        h2, h3 = st.columns([2.4, 1.6], vertical_alignment="center")
        with h2:
            indicator = st.selectbox("Indicateur", INDICATORS[wt], key=f"ind_{key}", label_visibility="collapsed",
                                     format_func=lambda v: f"Indicateur : {v}")
        with h3:
            grain = st.segmented_control("Granularité", ["Mensuel", "Annuel"], default="Mensuel", key=f"grain_{key}",
                                         label_visibility="collapsed") or "Mensuel"
        layout = dict(height=300, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Nunito, Segoe UI, Arial, sans-serif"), xaxis=dict(type="category", showgrid=False, tickfont=dict(family="Nunito, Segoe UI, Arial, sans-serif", size=12, color="#5F566A")))

        def draw_status():
            df = iv.monthly_status(filters, start, end, grain)
            if not len(df):
                C.note("Aucune donnée sur la période et les filtres actifs.")
                return
            fig = go.Figure()
            periods = list(dict.fromkeys(df["periode"]))
            base_line(int(df["n"].sum()), "interventions créées")
            for s in DONUT_ORDER[wt]:
                part = df[df["status"] == s].set_index("periode")["n"]
                if not len(part):
                    continue
                fig.add_bar(x=periods, y=[int(part.get(p_, 0)) for p_ in periods], name=STATUS[s][0], marker_color=STATUS[s][2],
                            hovertemplate="%{x} · " + STATUS[s][0] + " : %{y}<extra></extra>")
            totals = [int(df[df["periode"] == p_]["n"].sum()) for p_ in periods]
            fig.add_scatter(x=periods, y=totals, mode="text", text=[n_fmt(t) for t in totals], textposition="top center",
                            textfont=dict(size=11, color="#173B69"), showlegend=False, hoverinfo="skip")
            fig.update_layout(**layout, barmode="stack", bargap=.4, yaxis=dict(visible=False, range=[0, max(totals) * 1.15]),
                              legend=dict(orientation="h", y=1.14, x=0, font=dict(size=12, color="#2B3350"), traceorder="normal"))
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"month_{key}_{grain}_status")

        def draw_rate():
            df = iv.monthly(filters, start, end, wt, indicator, grain)
            is_rate = "retard" in indicator or "délai" in indicator or "Taux" in indicator
            df = df.dropna(subset=["valeur"])
            if not len(df) or float(df["valeur"].max()) == 0:
                C.note("Aucune donnée sur la période et les filtres actifs.")
                return
            what = ("interventions dont le délai est comparable" if (wt == "corrective" and is_rate) else
                    "interventions créées" if wt == "corrective" else
                    "passages dont la ponctualité est jugeable" if is_rate else "passages prévus")
            base_line(int(df["base"].sum()), what)
            if wt == "preventive" and is_rate:
                st.caption("Taux de retard = passages en retard (réalisés après la date prévue, ou pas faits alors que la date est dépassée) "
                           "divisés par les passages dont on peut juger la ponctualité. Même calcul que la carte « Ponctualité ».")
            fig = go.Figure(go.Bar(x=df["periode"], y=df["valeur"], marker_color="#E5114D",
                                   text=[f"{v:.1f} %".replace(".", ",") if is_rate else n_fmt(v) for v in df["valeur"]],
                                   textposition="outside", cliponaxis=False, hovertemplate="%{x} : %{text}<extra></extra>"))
            fig.update_layout(**layout, bargap=.45, yaxis=dict(visible=False, range=[0, float(df["valeur"].max()) * 1.25]))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"month_{key}_{grain}_{indicator}")

        def draw_prev():
            df = iv.prev_monthly_result(filters, start, end, grain)
            if not len(df):
                C.note("Aucune donnée sur la période et les filtres actifs.")
                return
            periods = list(df["periode"])
            series = [("realises", "Réalisés", "#008080"), ("non_realises", "Clôturés non réalisés", "#F5A524"),
                      ("restants", "Restants", "#F78BC7"), ("annules", "Annulés", "#C9CFE0")]
            fig = go.Figure()
            for col, lbl, color in series:
                fig.add_bar(x=periods, y=df[col].tolist(), name=lbl, marker_color=color,
                            hovertemplate="%{x} · " + lbl + " : %{y}<extra></extra>")
            totals = [int(sum(df[c].iloc[i] for c, _, _ in series)) for i in range(len(df))]
            base_line(sum(totals), "passages prévus")
            fig.add_scatter(x=periods, y=totals, mode="text", text=[n_fmt(t) for t in totals], textposition="top center",
                            textfont=dict(size=11, color="#173B69"), showlegend=False, hoverinfo="skip")
            fig.update_layout(**layout, barmode="stack", bargap=.4, yaxis=dict(visible=False, range=[0, max(totals + [1]) * 1.15]),
                              legend=dict(orientation="h", y=1.14, x=0, font=dict(size=12, color="#2B3350"), traceorder="normal"))
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"month_{key}_{grain}_result")

        def draw_pvr():
            df = iv.prev_monthly_result(filters, start, end, grain)
            if not len(df):
                C.note("Aucune donnée sur la période et les filtres actifs.")
                return
            periods = list(df["periode"])
            prevus = [int(df["realises"].iloc[i] + df["non_realises"].iloc[i] + df["restants"].iloc[i] + df["annules"].iloc[i]) for i in range(len(df))]
            reals = [int(v) for v in df["realises"]]
            base_line(sum(prevus), "passages prévus")
            fig = go.Figure()
            fig.add_bar(x=periods, y=prevus, name="Prévus", marker_color="#173B69", text=[n_fmt(v) for v in prevus],
                        textposition="outside", cliponaxis=False, textfont=dict(size=11, color="#173B69"),
                        hovertemplate="%{x} · Prévus : %{y}<extra></extra>")
            fig.add_bar(x=periods, y=reals, name="Réalisés", marker_color="#008080", text=[n_fmt(v) for v in reals],
                        textposition="outside", cliponaxis=False, textfont=dict(size=11, color="#008080"),
                        hovertemplate="%{x} · Réalisés : %{y}<extra></extra>")
            fig.update_layout(**layout, barmode="group", bargap=.3, bargroupgap=.08,
                              yaxis=dict(visible=False, range=[0, max(prevus + [1]) * 1.18]),
                              legend=dict(orientation="h", y=1.14, x=0, font=dict(size=12, color="#2B3350"), traceorder="normal"))
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"month_{key}_{grain}_pvr")

        if wt == "corrective" and indicator == "Volume par statut":
            guard(draw_status, "Évolution")
        elif wt == "preventive" and indicator == "Volume par résultat":
            guard(draw_prev, "Évolution")
        elif wt == "preventive" and indicator == "Prévus vs réalisés":
            guard(draw_pvr, "Évolution")
        else:
            guard(draw_rate, "Évolution")


def active_card(df, wt):
    with st.container(key=f"iv_active_{wt}"):
        C.card_title("Interventions actives", "Statuts en cours de traitement, avec le respect des délais"
                     if wt == "corrective" else "Passages programmés ou en cours, avec le respect de la date prévue")
        sub = df.set_index("status")
        if not any(s in sub.index and int(sub.loc[s].n) for s in ACTIVE_ORDER[wt]):
            C.note("Aucune intervention active sur la période et les filtres actifs." if wt == "corrective"
                   else "Aucun passage actif sur la période et les filtres actifs.")
            return
        tot_act = sum(int(sub.loc[s].n) for s in ACTIVE_ORDER[wt] if s in sub.index)
        base_line(tot_act, "interventions actives (ouvertes, en cours ou en attente)" if wt == "corrective" else "passages actifs")
        cols = st.columns(3)
        for col, s in zip(cols, ACTIVE_ORDER[wt]):
            if s not in sub.index:
                continue
            r = sub.loc[s]
            comp, late = int(r.comp_pec), int(r.late_pec)
            color = STATUS[s][2]
            split = ""
            if comp:
                ontime = comp - late
                share = 100 * late / comp
                split = (f'<div class="iv-split" style="--c:{color}"><i style="width:{share:.0f}%"></i></div>'
                         f'<div class="iv-splitleg"><span>{n_fmt(ontime)} dans les délais <em>{pct_fmt(100 - share)}</em></span>'
                         f'<b style="color:{color}">{n_fmt(late)} {"hors délai" if wt == "corrective" else "dépassés"} <em>{pct_fmt(share)}</em></b></div>'
                         f'<div class="iv-splitbase">sur {n_fmt(comp)} {"comparables" if wt == "corrective" else "jugeables"}</div>')
            else:
                split = f'<div class="iv-split" style="--c:{color}"><i style="width:0"></i></div>'
            col.markdown(f'<div class="iv-act"><div class="iv-actlbl"><i style="background:{color}"></i>{STATUS[s][0]}</div>'
                         f'<div class="iv-actn"><b>{n_fmt(r.n)}</b><small>actives · {pct_fmt(100 * r.n / tot_act) if tot_act else "0 %"}</small></div>{split}</div>', unsafe_allow_html=True)


def _ranked(rows, color, limit=5):
    """Lignes classées (libellé, effectif) : les `limit` premières, le reste regroupé en « Autres »."""
    rows = sorted(rows, key=lambda r: -r[1])
    if len(rows) > limit + 1:
        rows = rows[:limit] + [("Autres", sum(n for _, n in rows[limit:]))]
    top = max((n for _, n in rows), default=1) or 1
    tot = sum(n for _, n in rows) or 1
    return "".join(f'<div class="iv-rk"><span>{escape(lbl)}</span><span class="iv-rkbar"><i style="width:{100 * n / top:.0f}%;background:{color}"></i></span>'
                   f'<b>{n_fmt(n)}</b><small>{100 * n / tot:.0f} %</small></div>' for lbl, n in rows)


def _stack(parts, total):
    """Barre unique découpée en parts (couleur, effectif)."""
    return '<div class="iv-stack">' + "".join(f'<i style="width:{100 * n / total:.2f}%;background:{c}"></i>' for c, n in parts if n and total) + '</div>'


def end_card(df_status, filters, start, end):
    """Comment les interventions se terminent : une barre d'ensemble, puis les types de fin de chaque groupe côte à côte."""
    with st.container(key="iv_end_types"):
        C.card_title("Comment elles se terminent", "Clôturées, refusées ou annulées, avec le type de fin de chacune.")
        def draw():
            data = iv.end_types(filters, start, end)
            total_all = int(df_status["n"].sum()) or 1
            base_line(total_all, "interventions créées")
            groups = []
            for status, title, color in (("closed", "Clôturées", "#008080"), ("denied", "Refusées et annulées", "#8A91A6")):
                part = data[data["status"] == status]
                groups.append((title, color, int(part["n"].sum()), [(fr.libelle(r.type_fin), int(r.n)) for r in part.itertuples()]))
            reste = max(total_all - sum(g[2] for g in groups), 0)
            hero = "".join(f'<div style="--g:{c}"><b>{n_fmt(n)}</b><span><u></u>{t}</span><small>{pct_fmt(100 * n / total_all)}</small></div>'
                           for t, c, n, _ in groups)
            cols = "".join(f'<div class="iv-col" style="--g:{c}"><div class="iv-colh">{t}</div>{_ranked(rows, c, 4) if rows else ""}</div>'
                           for t, c, _, rows in groups)
            st.markdown(f'<div class="iv-hero">{hero}</div>'
                        + _stack([(c, n) for _, c, n, _ in groups] + [("#EEF0F6", reste)], total_all)
                        + f'<div class="iv-two">{cols}</div>', unsafe_allow_html=True)
        guard(draw, "Types de fin")


def causes_card(filters, start, end):
    with st.container(key="iv_causes"):
        C.card_title("Causes techniques", "Cause renseignée sur les curatives clôturées. Ce n'est pas un motif de clôture.")
        def draw():
            data = iv.technical_causes(filters, start, end)
            rows = sorted([(fr.libelle(r.cause), int(r.n)) for r in data.itertuples()], key=lambda r: -r[1])
            if len(rows) > 7:
                rows = rows[:6] + [("Autres", sum(n for _, n in rows[6:]))]
            total = sum(n for _, n in rows) or 1
            base_line(total, "curatives clôturées")
            palette = ["#173B69", "#0074FF", "#80CDFF", "#432ABD", "#008080", "#F5A524", "#8A91A6"]
            colored, k = [], 0
            for lbl, n in rows:
                if lbl.lower().startswith(("non renseign", "autres")):
                    colored.append((lbl, n, "#C9CFE0"))
                else:
                    colored.append((lbl, n, palette[k % len(palette)])); k += 1
            hero = f'<div class="iv-hero"><div style="--g:#173B69"><b>{n_fmt(total)}</b><span><u></u>curatives clôturées avec une cause</span></div></div>'
            lst = "".join(f'<div class="iv-dl"><u style="background:{c}"></u><span>{escape(l)}</span><b>{n_fmt(n)}</b><small>{100 * n / total:.0f} %</small></div>'
                          for l, n, c in colored)
            st.markdown(hero + _stack([(c, n) for _, n, c in colored], total) + f'<div class="iv-dlist">{lst}</div>', unsafe_allow_html=True)
        guard(draw, "Causes techniques")


def transparency_card(filters, start, end):
    """Sur quoi repose le taux hors délai : repli en bas de page, présenté comme un entonnoir en trois étapes."""
    with st.expander("Sur quelles interventions repose le taux hors délai ?", expanded=False, key="iv_transparency"):
        def draw():
            t = iv.transparency(filters, start, end)
            total = int(t["curatives"])
            if not total:
                C.note("Aucune curative sur la période et les filtres actifs.")
                return
            comp = int(t["comparables_pec"])
            sans_sla = min(int(t["sans_sla_pec"]), total)
            avec_sla = total - sans_sla
            comp = min(comp, avec_sla)
            perdu_duree = avec_sla - comp
            mois = int(t["pec_mois"])
            share = 100 * comp / total
            steps = [("Curatives de la période", "hors refusées", total, "#173B69"),
                     ("Avec un délai fixé par le contrat", "il y a quelque chose à comparer", avec_sla, "#0074FF"),
                     ("Avec une durée de prise en charge exploitable", "elles entrent dans le taux", comp, "#008080")]
            drops = [(sans_sla, "écartées : le contrat ne fixe aucun délai"),
                     (perdu_duree, "écartées : durée vide, négative ou nulle")]
            html = ""
            for k, (lbl, sub, n, color) in enumerate(steps):
                html += (f'<div class="iv-fs"><div class="iv-fst"><b>{escape(lbl)}</b><small>{escape(sub)}</small></div>'
                         f'<div class="iv-fsb"><i style="width:{max(100 * n / total, 0.6):.2f}%;background:{color}"></i></div>'
                         f'<div class="iv-fsn"><b>{n_fmt(n)}</b><small>{100 * n / total:.0f} %</small></div></div>')
                if k < len(drops):
                    dn, dl = drops[k]
                    html += f'<div class="iv-fd"><span>− {n_fmt(dn)}</span>{escape(dl)}</div>'
            note_mois = (f'<div class="iv-fnote">{n_fmt(mois)} interventions ont un délai exprimé en mois : elles sont comptées à part.</div>'
                         if mois else "")
            st.markdown(
                f'<div class="iv-fun"><div class="iv-ring" style="--p:{share:.1f}"><div><b>{share:.0f} %</b><small>entrent dans le taux</small></div></div>'
                f'<div class="iv-fsteps">{html}{note_mois}</div></div>', unsafe_allow_html=True)
        guard(draw, "Fiabilité")


PONCT_TONE = {"real_ok": "ok", "real_retard": "late", "real_inconnue": "unk", "non_real_retard": "late", "a_venir": "wait",
              "clot_non_real": "unk", "annule": "unk", "autre": "unk"}


def ponct_tag(code):
    lib = colf.PONCT_LIB.get(code, "–")
    return f'<span class="pf-tag {PONCT_TONE.get(code, "unk")}">{escape(lib)}</span>'


def status_pill(s):
    plural, singular, color = STATUS.get(s, (s, str(s).replace("_", " ").capitalize(), "#5F566A"))
    return f'<span class="pf-spill" style="background:{color}22;color:{color}">● {escape(singular)}</span>'


PONCT_QUICK = {"Toutes": [], "En retard (réalisés ou non)": ["real_retard", "non_real_retard"],
               "Non réalisés en retard": ["non_real_retard"], "Réalisés en retard": ["real_retard"],
               "Réalisés dans le délai": ["real_ok"], "Pas encore en retard": ["a_venir"], "Ponctualité inconnue": ["real_inconnue"]}


def export_frame(df, wt):
    """Colonnes lisibles pour l'export d'une liste d'interventions (le choix des colonnes se fait dans le bouton d'export)."""
    out = pd.DataFrame({"Référence": df["reference"], "Équipement": df["esi"],
                        "Statut": [STATUS.get(x, (x, x, ""))[1] for x in df["status"]],
                        "Type de fin": [fr.libelle(x) if pd.notna(x) else None for x in df["type_fin"]],
                        "Motif de clôture ou d'annulation": df["motif"], "Cause technique": [fr.libelle(x) if pd.notna(x) else None for x in df["cause"]],
                        "Créée le": df["ouverture"]})
    if wt == "corrective":
        out["Délai"] = [{True: "Hors délai", False: "Dans les délais"}.get(x, "Sans conclusion") for x in df["late"]]
        out["SLA prise en charge"], out["Prise en charge (h)"] = df["sla"], df["pec_heures"].astype(float).round(2)
        out["SLA résolution"], out["Résolution (h)"] = df["sla_res"], df["res_heures"].astype(float).round(2)
    else:
        out["Date prévue"] = df["date_prevue"]
        out["Origine de la date prévue"] = [fr.libelle(x) if pd.notna(x) else None for x in df["date_prevue_source"]]
        out["Réalisée le"] = df["date_realisation"]
        out["Ponctualité"] = [colf.PONCT_LIB.get(x) for x in df["ponct"]]
        out["Jours de retard"] = df["overrun_days"]
    out["Métier"], out["Prestataire"], out["Contrat"] = df["metier"], df["provider_name"], df["contract_reference"]
    return out


def list_card(wt, filters, start, end):
    key = "cur" if wt == "corrective" else "prev"
    with st.container(key=f"iv_list_{key}"):
        if not C.list_header(f"iv_{key}", "Liste des interventions",
                     "Les plus récentes d'abord · filtrée par statut" if wt == "corrective"
                     else "Passages prévus sur la période, triés par date prévue. Filtre « Ponctualité » pour isoler les retards.",
                     "Une intervention est hors délai quand sa prise en charge ou sa résolution a pris plus de temps que le délai prévu au contrat. "
                     "Quand le contrat n'a pas de délai, ou que la durée n'est pas exploitable, on n'affiche rien (tiret)."
                     if wt == "corrective" else "Date prévue : quand la donnée n'en contient pas, on prend la date de création du passage et on l'indique « (création) »."):
            return
        if wt == "preventive":
            c1, c1b, c2, c3, c4 = st.columns([1.5, 2.1, 2.6, 1.2, 0.6], vertical_alignment="center")
        else:
            c1, c2, c3, c4 = st.columns([1.6, 3, 1.3, 0.6], vertical_alignment="center")
            c1b = None
        with c1:
            group = st.selectbox("Statut", ["Actives", "Inactives", "Toutes"], key=f"ivl_group_{key}", label_visibility="collapsed",
                                 index=0 if wt == "corrective" else 2, format_func=lambda v: f"Statut : {v}")
        quick = "Toutes"
        if c1b is not None:
            with c1b:
                quick = st.selectbox("Ponctualité", list(PONCT_QUICK), key="ivl_quick_prev", label_visibility="collapsed",
                                     format_func=lambda v: f"Ponctualité : {v}")
        with c2:
            needle = st.text_input("Recherche", key=f"ivl_search_{key}", label_visibility="collapsed", icon=":material/search:",
                                   placeholder="Rechercher une référence, un ESI, un contrat...")
        liste = f"iv_{key}"
        cles = LIST_COLS[wt]
        etat_col = colui.etat(liste, cles)
        extra = colf.appliquer(etat_col, cles)
        if quick != "Toutes":
            extra["clauses"] = extra["clauses"] + [f"({colf.COLS['delai_prev']['expr']}) = ANY(:quick_p)"]
            extra["params"] = {**extra["params"], "quick_p": PONCT_QUICK[quick]}
        with c3:
            n_col = len(etat_col["v"]) + len(etat_col["t"]) + len(etat_col["n"])
            if n_col or etat_col["tri"]:
                st.button(f"Effacer ({n_col})" if n_col else "Effacer le tri", key=f"ivl_clear_{key}", on_click=colui.tout_effacer,
                          args=(liste, cles), icon=":material/filter_alt_off:", width="stretch")
        sig = (group, needle, quick, repr(filters), str(start), str(end), repr(etat_col))
        if st.session_state.get(f"ivl_sig_{key}") != sig:
            st.session_state[f"ivl_sig_{key}"] = sig
            st.session_state[f"ivl_page_{key}"] = 1
        total_guess = 10 ** 9
        page_no = int(st.session_state.get(f"ivl_page_{key}", 1))
        def draw():
            nonlocal page_no
            df, total = iv.interventions_page(filters, start, end, wt, group, needle, PAGE_SIZE, (page_no - 1) * PAGE_SIZE, extra)
            pages = max(1, -(-total // PAGE_SIZE))
            if page_no > pages:
                page_no = pages
                st.session_state[f"ivl_page_{key}"] = pages
            with c4:
                if len(df):
                    C.download_xlsx(export_frame(df, wt), f"rex_interventions_{key}_p{page_no}.xlsx", f"export_ivl_{key}", label="",
                                    loader=lambda: export_frame(iv.interventions_page(filters, start, end, wt, group, needle, 100000, 0, extra)[0], wt),
                                    sig=repr(sig), total=total)
            colui.en_tete(liste, ENTETES[wt][0], ENTETES[wt][1], {
                "statut": {k: v[0] for k, v in STATUS.items()}, "delai": DELAI_LIB[wt], "delai_prev": colf.PONCT_LIB, "fin": END_FR,
                "metier": _libelles("Métier", filters, start, end), "prestataire": _libelles("Prestataire", filters, start, end)})
            if not len(df):
                C.note("Aucune intervention ne correspond aux filtres.")
                return
            body = []
            for r in df.itertuples():
                color = STATUS.get(r.status, ("", "", "#5F566A"))[2]
                ref = f'<span class="pf-lref" style="border-left-color:{color}"><b>{escape(str(r.reference))}</b></span>'
                eq = (f'<span class="pf-eq">{escape(str(r.esi))}</span>' if pd.notna(r.esi) and str(r.esi).strip() else '<span class="pf-eq none">Sans équipement</span>')
                if r.late is True:
                    why = [w for w, f in (("prise en charge", r.late_pec), ("résolution", r.late_res)) if f is True] if wt == "corrective" else []
                    delay = (f'<span class="pf-tag late">{"Hors délai" if wt == "corrective" else "En retard"}</span>'
                             + (f'<br><small>{escape(" et ".join(why))}</small>' if why else ""))
                elif r.late is False:
                    delay = '<span class="pf-tag ok">Dans les délais</span>'
                else:
                    delay = '<span class="pf-dash">–</span>'
                metier = f'<span class="pf-mtag">{escape(str(r.metier))}</span>' if pd.notna(r.metier) else "–"
                prov = f'<span class="iv-prov">{avatar(r.provider_name)}<b>{escape(str(r.provider_name))}</b></span>' if pd.notna(r.provider_name) else "–"
                contract = escape(str(r.contract_reference)) if pd.notna(r.contract_reference) else "–"
                pill = status_pill(r.status)
                fin = (f'<b>{escape(fr.libelle(r.type_fin))}</b>' if pd.notna(r.type_fin) else '<span class="pf-dash">–</span>')
                if pd.notna(r.motif):
                    fin += f'<br><small title="{escape(str(r.motif))}">{escape(str(r.motif))[:60]}</small>'
                cause = escape(fr.libelle(r.cause)) if pd.notna(r.cause) else '<span class="pf-dash">–</span>'
                if wt == "corrective":
                    pec = fr.duree(r.pec_heures) + (f'<br><small>SLA {escape(str(r.sla))}</small>' if r.sla else "")
                    resol = fr.duree(r.res_heures) + (f'<br><small>SLA {escape(str(r.sla_res))}</small>' if r.sla_res else "")
                    cells = [ref, pill, C.fr_date(r.ouverture, "%d/%m/%y"), eq, delay, pec, resol, fin, cause, metier, prov, contract]
                else:
                    known = pd.notna(r.date_prevue)
                    due = r.date_prevue if known else r.ouverture
                    mark = "" if known else ' <small title="Date prévue absente : date de création utilisée">(création)</small>'
                    over = (f'<b class="iv-over">+{int(r.overrun_days)} j</b>' if pd.notna(r.overrun_days) and r.overrun_days else '<span class="pf-dash">–</span>')
                    done = C.fr_date(r.date_realisation, "%d/%m/%y") if pd.notna(r.date_realisation) else '<span class="pf-dash">–</span>'
                    delay = ponct_tag(r.ponct)
                    cells = [ref, pill, C.fr_date(due, "%d/%m/%y") + mark, done, eq, delay, over, fin, metier, prov, contract]
                body.append('<div class="pf-lrow">' + "".join(f"<span>{c}</span>" for c in cells) + "</div>")
            st.markdown(f'<div class="pf-ltable" style="--cols:{ENTETES[wt][1]};margin-top:.2rem">' + "".join(body) + "</div>", unsafe_allow_html=True)
            pager_controls(f"ivl_page_{key}", page_no, pages, total, len(df))
        guard(draw, "Liste des interventions")


# ---------------------------------------------------------------- performance prestataires
def compare_card(wt, filters, start, end):
    selected = filters.get("Prestataire") or []
    df = iv.compare_providers(filters, start, end, wt, selected or None)
    with st.container(key=f"iv_compare_{wt}"):
        C.card_title("Tableau comparatif", "Périmètre contractuel et curatif de chaque prestataire : contrats actifs, ESI et logements rattachés, métiers et volume d'interventions."
                     if wt == "corrective" else "Périmètre contractuel et préventif de chaque prestataire : contrats, ESI, logements, métiers et passages.")
        if selected:
            st.markdown(f'<div class="iv-filterpill">{C.svg("users", 14)} {len(selected)} prestataire{"s" if len(selected) > 1 else ""} sélectionné{"s" if len(selected) > 1 else ""} dans le filtre</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="iv-filterpill soft">Aucun prestataire dans le filtre : les 5 plus actifs sont affichés. Choisis des prestataires dans le filtre pour comparer.</div>',
                        unsafe_allow_html=True)
        if not len(df):
            C.note("Aucun prestataire sur ce périmètre.")
            return df
        head = ('<div class="iv-crow head"><span>PRESTATAIRE</span><span>CONTRATS ACTIFS</span><span>ESI RATTACHÉS</span>'
                '<span>LOGEMENTS COUVERTS</span><span>MÉTIERS</span><span>INTERVENTIONS ' + ("CURATIVES" if wt == "corrective" else "PRÉVENTIVES")
                + '</span><span></span></div>')
        st.markdown(head, unsafe_allow_html=True)
        max_esi, max_int = max(int(df["esi"].max()), 1), max(int(df["interventions"].max()), 1)
        for i, r in enumerate(df.itertuples()):
            color = CHIP_COLORS[i % len(CHIP_COLORS)]
            pct = 100 * r.actifs / r.total if r.total else 0
            tags = "".join(f'<span class="pf-mtag">{escape(m)}</span>' for m in (r.metiers or [])[:2])
            if len(r.metiers or []) > 2:
                tags += f'<span class="pv-tag more">+{len(r.metiers) - 2}</span>'
            logements = n_fmt(r.logements) if pd.notna(r.logements) and r.logements is not None else "n/d"
            with st.container(key=f"rowc_{wt}_{r.provider_id}"):
                st.markdown(
                    f'<div class="iv-crow" style="--bar:{color}"><span class="iv-cprov">{avatar(r.provider_name)}<b>{escape(r.provider_name)}</b></span>'
                    f'<span><span class="iv-n"><b>{r.actifs}</b><em>/ {r.total}</em></span><span class="iv-mini teal"><i style="width:{pct:.0f}%"></i></span>'
                    f'<small>{pct:.0f} % actifs</small></span>'
                    f'<span><b>{n_fmt(r.esi)}</b><span class="iv-mini blue"><i style="width:{100 * r.esi / max_esi:.0f}%"></i></span>'
                    f'<small>{n_fmt(r.esi)} résidences</small></span>'
                    f'<span><b>{logements}</b><span class="iv-mini navy"><i style="width:{min(100, 100 * (r.logements or 0) / max(1, df["logements"].fillna(0).max())):.0f}%"></i></span>'
                    f'<small>{r.agences} agences</small></span>'
                    f'<span class="iv-ctags">{tags}</span>'
                    f'<span><b>{n_fmt(r.interventions)}</b><span class="iv-mini red"><i style="width:{100 * r.interventions / max_int:.0f}%"></i></span>'
                    f'<small>sur la période filtrée</small></span><span class="iv-arrow">›</span></div>', unsafe_allow_html=True)
                st.button("Ouvrir la fiche", key=f"rowb_{wt}_{r.provider_id}", on_click=C.open_provider_page, args=(r.provider_id,))
        return df


PALETTE = ["#E5114D", "#173B69", "#0074FF", "#432ABD", "#008080", "#E0A02E", "#FFB7E3", "#80CDFF", "#7B7385", "#B5164F", "#2F6FE4", "#0A9A83"]
MAX_LIGNES = 8


def analysis_card(wt, filters, start, end, df):
    with st.container(key=f"iv_analysis_{wt}"):
        C.card_title("Analyse prestataires", "Qui fait mieux, qui fait moins bien, d'où vient l'écart et où ça va. Un taux sur moins de "
                     f"{iv.MIN_BASE} cas n'est ni classé ni tracé.")
        if df is None or not len(df):
            C.note("Sélectionne au moins un prestataire.")
            return
        c1, c2, c3, c4 = st.columns([2.2, 1.6, 1.6, 2.2], vertical_alignment="center")
        options = list(iv.INDICATEURS[wt])
        indicator = c1.selectbox("Indicateur", options, key=f"an_ind3_{wt}", format_func=lambda v: f"Indicateur : {v}",
                                 label_visibility="collapsed")
        view = c2.segmented_control("Vue", ["Classement", "Évolution"], default="Classement", key=f"an_view_{wt}",
                                    label_visibility="collapsed") or "Classement"
        all_ids = list(df.sort_values("interventions", ascending=False)["provider_id"])
        names = dict(zip(df["provider_id"], df["provider_name"]))
        key = f"an_show_{wt}"
        sig = tuple(all_ids)
        if st.session_state.get(key + "_sig") != sig or not [x for x in st.session_state.get(key, []) if x in all_ids]:
            st.session_state[key + "_sig"] = sig
            st.session_state[key] = all_ids[:MAX_LIGNES]
        if len(all_ids) > 1:
            with c3.popover(f"Prestataires : {len([x for x in st.session_state[key] if x in all_ids])} / {len(all_ids)}", width="stretch"):
                picker.select(key, {i: names.get(i, i) for i in all_ids}, placeholder="Rechercher un prestataire...")
                st.caption("Les 12 premiers prestataires cochés sont affichés, pour garder le graphique lisible.")
        compare = False
        if view == "Évolution":
            compare = c4.selectbox("Comparer à", ["Aucune comparaison", "Période précédente"], key=f"an_cmp3_{wt}",
                                   format_func=lambda v: f"Comparer à : {v}", label_visibility="collapsed") == "Période précédente"
        ids = ([x for x in st.session_state.get(key, all_ids[:MAX_LIGNES]) if x in all_ids] or all_ids[:MAX_LIGNES])[:12]
        st.markdown(f'<div class="iv-fnote" style="margin:.2rem 0 .4rem">{escape(iv.INDIC_HELP[indicator])}</div>', unsafe_allow_html=True)
        if len(all_ids) > len(ids):
            st.caption(f"{len(all_ids)} prestataires dans le périmètre : {len(ids)} affichés (les plus actifs par défaut).")
        if view == "Classement":
            guard(lambda: _ranking(wt, filters, start, end, ids, names, indicator), "Classement")
        else:
            guard(lambda: _trend(wt, filters, start, end, ids, names, indicator, compare), "Évolution")


def _fmt(v, is_rate):
    return (f"{v:.0f} %" if abs(v - round(v)) < .05 else f"{v:.1f} %".replace(".", ",")) if is_rate else n_fmt(v)


def _tone(delta, sens, tol=1.0):
    """good, bad ou flat selon le sens de l'indicateur et l'écart."""
    if sens == "vol" or delta is None or pd.isna(delta) or abs(delta) < tol:
        return "flat"
    return "good" if (delta > 0) == (sens == "good") else "bad"


def _ranked_frame(wt, filters, start, end, ids, names, indicator):
    data, is_rate, sens = iv.providers_ranking(filters, start, end, wt, ids, indicator)
    present = set(data.loc[data["base"] > 0, "provider_id"])
    empty = pd.DataFrame({"provider_id": [i for i in ids if i not in present]})
    empty["name"] = empty["provider_id"].map(names).fillna(empty["provider_id"])
    data = data[data["base"] > 0].copy()
    data["name"] = data["provider_id"].map(names).fillna(data["provider_id"])
    solid = data[data["base"] >= iv.MIN_BASE] if is_rate else data
    weak = data[~data.index.isin(solid.index)]
    solid = solid.sort_values("valeur", ascending=(sens == "bad"))  # le mieux placé en premier
    avg = float(solid["num"].sum() / solid["base"].sum() * 100) if is_rate and len(solid) and solid["base"].sum() else None
    return solid, weak, avg, is_rate, sens, empty


def _ranking(wt, filters, start, end, ids, names, indicator):
    solid, weak, avg, is_rate, sens, empty = _ranked_frame(wt, filters, start, end, ids, names, indicator)
    if not len(solid) and not len(weak) and not len(empty):
        C.note(f"Aucune donnée pour « {indicator} » sur ces prestataires et cette période.")
        return
    if not len(solid):
        st.markdown('<div class="an-story"><b>Aucun prestataire n\'a assez de cas pour être comparé.</b></div>', unsafe_allow_html=True)
    allb = pd.concat([solid, weak]) if len(weak) else solid
    base_line(int(allb["base"].sum()) if is_rate else int(allb["valeur"].sum()),
              (("passages prévus" if indicator != "Taux de retard" else iv.INDIC_BASE["Taux de retard"]) if wt == "preventive" else iv.INDIC_BASE.get(indicator, "interventions")) + " (prestataires affichés)")
    best, worst = (solid.iloc[0], solid.iloc[-1]) if len(solid) else (None, None)
    headline = sub = ""
    if not len(solid):
        pass
    elif is_rate and avg is not None and len(solid) > 1:
        gap = abs(float(worst["valeur"]) - avg)
        side = "au-dessus" if (worst["valeur"] > avg) else "en dessous"
        headline = (f"{escape(best['name'])} est le mieux placé ({_fmt(best['valeur'], True)}), {escape(worst['name'])} le moins bien ({_fmt(worst['valeur'], True)}) : "
                    f"{gap:.0f} points {side} de la moyenne du groupe ({_fmt(avg, True)}).")
        pnum, pbase = float(solid["prev_num"].sum()), float(solid["prev_base"].sum())
        sub = f"Moyenne du groupe sur la période : {_fmt(avg, True)}"
        if pbase >= iv.MIN_BASE:
            pavg = 100 * pnum / pbase
            sub += f", contre {_fmt(pavg, True)} sur la période précédente ({'+' if avg - pavg >= 0 else '−'}{abs(avg - pavg):.0f} pt)."
        else:
            sub += "."
    elif is_rate:
        headline = f"{escape(best['name'])} : {_fmt(best['valeur'], True)} sur {n_fmt(best['base'])} cas."
        sub = "Un seul prestataire avec assez de cas : pas de comparaison possible."
    else:
        total = float(solid["valeur"].sum())
        top = solid.sort_values("valeur", ascending=False).iloc[0]
        headline = f"{escape(top['name'])} concentre {100 * top['valeur'] / total:.0f} % du total ({n_fmt(top['valeur'])} sur {n_fmt(total)})." if total else "Aucun volume."
        sub = f"Volume cumulé des prestataires affichés : {n_fmt(total)}."
    maxv = 100.0 if is_rate else max(float(pd.concat([solid, weak])["valeur"].max()) if (len(solid) or len(weak)) else 1, 1)
    rows = ['<div class="an-row head"><span>PRESTATAIRE</span><span>' + escape(indicator.upper()) + '</span><span></span>'
            + ('<span>ÉCART À LA MOYENNE</span>' if is_rate else '<span>PART DU TOTAL</span>') + '<span>VS PÉRIODE PRÉCÉDENTE</span></div>']
    total_vol = float(solid["valeur"].sum()) if not is_rate else 0
    for r in solid.itertuples():
        w = max(min(100 * r.valeur / maxv, 100), 0.8)
        delta = (r.valeur - avg) if (is_rate and avg is not None) else None
        tone_bar = _tone(delta, sens)
        color = {"good": "#008080" if sens == "good" else "#F78BC7", "bad": "#E5114D", "flat": "#F78BC7"}[tone_bar] if is_rate else "#F78BC7"
        mark = f'<i class="an-avg" style="left:{min(avg / maxv * 100, 100):.1f}%" title="Moyenne du groupe"></i>' if (is_rate and avg is not None) else ""
        detail = f"{n_fmt(r.num)} sur {n_fmt(r.base)}" if is_rate else ""
        if is_rate:
            ecart = (f'<span class="an-chip {tone_bar}">{"+" if delta >= 0 else "−"}{abs(delta):.0f} pt</span>' if delta is not None else "–")
        else:
            ecart = f'<span class="an-chip flat">{100 * r.valeur / total_vol:.0f} %</span>' if total_vol else "–"
        if is_rate:
            ok_prev = pd.notna(r.prev_valeur) and r.prev_base >= iv.MIN_BASE
            d2 = (r.valeur - r.prev_valeur) if ok_prev else None
        else:
            ok_prev = pd.notna(r.prev_valeur) and r.prev_valeur > 0
            d2 = (100 * (r.valeur - r.prev_valeur) / r.prev_valeur) if ok_prev else None
        if d2 is None:
            tend = '<span class="pf-dash">–</span><small>pas de période précédente comparable</small>'
        else:
            t2 = _tone(d2, sens, 1.0 if is_rate else 3.0)
            arrow = "▲" if d2 > 0 else "▼" if d2 < 0 else "="
            unit = " pt" if is_rate else " %"
            tend = f'<span class="an-chip {t2}">{arrow} {"+" if d2 >= 0 else "−"}{abs(d2):.0f}{unit}</span><small>avant : {_fmt(r.prev_valeur, is_rate)}</small>'
        rows.append(f'<div class="an-row"><span class="iv-prov">{avatar(r.name)}<b>{escape(r.name)}</b></span>'
                    f'<span class="an-bar"><i style="width:{w:.1f}%;background:{color}"></i>{mark}</span>'
                    f'<span class="an-val"><b>{_fmt(r.valeur, is_rate)}</b><small>{detail}</small></span><span>{ecart}</span><span class="an-tend">{tend}</span></div>')
    for r in weak.itertuples():  # trop peu de cas pour un taux solide : visibles, mais hors classement
        w = max(min(100 * r.valeur / maxv, 100), 0.8)
        detail = f"{n_fmt(r.num)} sur {n_fmt(r.base)}" if is_rate else ""
        rows.append(f'<div class="an-row dim"><span class="iv-prov">{avatar(r.name)}<b>{escape(r.name)}</b></span>'
                    f'<span class="an-bar"><i style="width:{w:.1f}%;background:#C9CFE0"></i></span>'
                    f'<span class="an-val"><b>{_fmt(r.valeur, is_rate)}</b><small>{detail}</small></span>'
                    f'<span class="an-note" style="grid-column: span 2">Trop peu de cas (moins de {iv.MIN_BASE}) pour être comparé</span></div>')
    for r in empty.itertuples():  # aucune activité : on affiche quand même la ligne, à 0
        rows.append(f'<div class="an-row dim"><span class="iv-prov">{avatar(r.name)}<b>{escape(r.name)}</b></span>'
                    f'<span class="an-bar"></span><span class="an-val"><b>0</b><small>{"0 sur 0" if is_rate else ""}</small></span>'
                    f'<span class="an-note" style="grid-column: span 2">Aucune activité sur la période et les filtres actifs</span></div>')
    st.markdown((f'<div class="an-story"><b>{headline}</b><span>{sub}</span></div>' if headline else "") + '<div class="an-table">' + "".join(rows) + "</div>"
                + ('<div class="an-legend"><i class="an-avg"></i>Moyenne du groupe · vert : mieux que la moyenne · rouge : moins bien · tendance : écart avec la période précédente de même durée</div>'
                   if is_rate else ""), unsafe_allow_html=True)


def _trend(wt, filters, start, end, ids, names, indicator, compare):
    solid, _, avg, _, sens, empty = _ranked_frame(wt, filters, start, end, ids, names, indicator)
    data, n, is_rate, labels = iv.providers_trend(filters, start, end, wt, ids, indicator, compare)
    cur = data[data["serie"] == "Période filtrée"]
    ok = cur.dropna(subset=["valeur"])
    if not len(ok):
        C.note(f"Aucune donnée solide pour « {indicator} » sur ces prestataires et cette période.")
        return
    unit = " %" if is_rate else ""
    # courbe du groupe : somme des numérateurs sur somme des bases, mois par mois
    g = cur.groupby("idx").agg(num=("num", "sum"), base=("base", "sum")).reset_index().sort_values("idx")
    g["valeur"] = (100 * g["num"] / g["base"]) if is_rate else g["num"]
    if is_rate:
        g = g[g["base"] >= iv.MIN_BASE]
    story = []
    gs = g[g["idx"] < n - 1] if (n > 2 and is_rate and pd.Timestamp(end).to_period("M") >= pd.Timestamp.today().to_period("M")) else g
    if len(gs) >= 2:  # le mois en cours est incomplet : il fausserait le récit
        f, l = gs.iloc[0], gs.iloc[-1]
        word = "monte" if l["valeur"] > f["valeur"] else "baisse" if l["valeur"] < f["valeur"] else "reste stable"
        story.append(f"Pour l'ensemble du groupe, « {indicator.lower()} » {word} : {_fmt(f['valeur'], is_rate)} en {labels[int(f['idx'])]}, {_fmt(l['valeur'], is_rate)} en {labels[int(l['idx'])]}" + (" (mois en cours exclu)." if len(gs) < len(g) else "."))
    best_n = worst_n = None
    if len(solid) > 1:
        best_n, worst_n = solid.iloc[0], solid.iloc[-1]
        if sens != "vol":
            story.append(f"En couleur : {escape(best_n['name'])} (le mieux placé sur la période) et {escape(worst_n['name'])} (le moins bien). Les autres sont en gris.")
    st.markdown('<div class="an-story">' + (f"<b>{story[0]}</b>" if story else "") + (f"<span>{story[1]}</span>" if len(story) > 1 else "") + "</div>",
                unsafe_allow_html=True)
    few = len(ids) <= 3
    focus = {best_n["provider_id"]: "#008080" if sens == "good" else "#173B69", worst_n["provider_id"]: "#E5114D"} if (best_n is not None and sens != "vol") else {}
    colors = {pid: PALETTE[i % len(PALETTE)] for i, pid in enumerate(ids)} if (few or not focus) else focus
    fig = go.Figure()
    for pid in ids:
        sub = ok[ok["provider_id"] == pid].sort_values("idx")
        if not len(sub):
            continue
        hi = pid in colors
        if hi:
            fig.add_trace(go.Scatter(x=sub["idx"], y=sub["valeur"], mode="lines+markers", name=names[pid], connectgaps=False,
                                     line=dict(color=colors[pid], width=3), marker=dict(size=6, color=colors[pid]), customdata=sub["label"],
                                     hovertemplate=f"{names[pid]} · %{{customdata}} : %{{y:,.1f}}{unit}<extra></extra>".replace(",", " ")))
            last = sub.iloc[-1]
            fig.add_annotation(x=last["idx"], y=last["valeur"], text=f"<b>{names[pid]}</b> {_fmt(last['valeur'], is_rate)}", showarrow=False, xanchor="left",
                               xshift=8, font=dict(size=11, color=colors[pid]))
        else:
            fig.add_trace(go.Scatter(x=sub["idx"], y=sub["valeur"], mode="lines", name=names[pid], connectgaps=False,
                                     line=dict(color="#D5D9E6", width=1.5), customdata=sub["label"],
                                     hovertemplate=f"{names[pid]} · %{{customdata}} : %{{y:,.1f}}{unit}<extra></extra>".replace(",", " ")))
    if compare:
        for pid in colors:
            prev = data[(data["serie"] == "Période précédente") & (data["provider_id"] == pid)].dropna(subset=["valeur"]).sort_values("idx")
            if len(prev):
                fig.add_trace(go.Scatter(x=prev["idx"], y=prev["valeur"], mode="lines", name=names[pid] + " (précédente)", opacity=.5,
                                         line=dict(color=colors[pid], width=1.8, dash="dot"), customdata=prev["label"],
                                         hovertemplate=f"{names[pid]} · précédente · %{{customdata}} : %{{y:,.1f}}{unit}<extra></extra>".replace(",", " ")))
    if len(g) >= 2:
        fig.add_trace(go.Scatter(x=g["idx"], y=g["valeur"], mode="lines", name="Moyenne du groupe", line=dict(color="#173B69", width=2, dash="dash"),
                                 customdata=[labels[int(i)] for i in g["idx"]], hovertemplate=f"Moyenne du groupe · %{{customdata}} : %{{y:,.1f}}{unit}<extra></extra>".replace(",", " ")))
    step = max(1, -(-n // 12))
    fig.update_layout(height=360, margin=dict(l=0, r=90, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False, font=dict(family="Nunito, Segoe UI, Arial, sans-serif", color="#5F566A"), hovermode="closest",
                      xaxis=dict(tickmode="array", tickvals=list(range(0, n, step)), ticktext=[labels[i] for i in range(0, n, step)],
                                 showgrid=False, range=[-.3, n - .5]),
                      yaxis=dict(gridcolor="#EEF0F6", ticksuffix=unit, rangemode="tozero"))
    chips = "".join(f'<span class="iv-chip"><i style="background:{c}"></i>{escape(names[p])}</span>' for p, c in colors.items())
    chips += '<span class="iv-chip"><i style="background:#173B69"></i>Moyenne du groupe (pointillés)</span>'
    if len(colors) < len(ids):
        chips += f'<span class="iv-chip"><i style="background:#D5D9E6"></i>{len(ids) - len(colors)} autre{"s" if len(ids) - len(colors) > 1 else ""} prestataire{"s" if len(ids) - len(colors) > 1 else ""}</span>'
    st.markdown('<div class="iv-chips">' + chips + "</div>", unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"an_{wt}_{indicator}_{compare}_{'-'.join(map(str, ids))}")
    if compare:
        st.caption("Pointillés fins : période précédente de même durée, alignée mois par mois, pour les prestataires en couleur.")
    if len(empty):
        st.caption("Sans activité sur la période (0) : " + ", ".join(empty["name"]) + ".")


def planned_card(filters, start, end):
    with st.container(key="iv_planned"):
        def draw():
            df = iv.planned_vs_done(filters, start, end)
            real, plan = int(df["realises"].sum()), int(df["prevus"].sum())
            C.card_title("Réalisation par prestataire",
                         "Pour chaque prestataire : combien de passages étaient prévus, combien ont été réalisés, et ce que sont devenus les autres.",
                         "Taux = réalisés ÷ prévus. Les passages non réalisés sont de trois sortes : clôturés sans être faits (occupant absent, réparation partielle...), "
                         "restants (pas encore faits, pas clôturés) et annulés. Les prestataires affichés sont les 12 qui ont le plus de passages prévus sur la période.")
            base_line(plan, f"passages prévus pour les {len(df)} prestataires ayant le plus de passages")
            cols = [("realises", "#008080"), ("non_realises", "#F5A524"), ("restants", "#F78BC7"), ("annules", "#C9CFE0")]

            def tone(rate):
                return "ok" if rate >= 85 else "mid" if rate >= 70 else "low"

            svg_sum = C.svg("grid", 20)

            def row(name, r, total=False):
                rate = 100 * r["realises"] / r["prevus"] if r["prevus"] else 0
                bar = _stack([(c, int(r[k])) for k, c in cols], int(r["prevus"]) or 1)
                miss = int(r["prevus"]) - int(r["realises"])
                who = (f'<span class="iv-prov"><span class="iv-sigma">{svg_sum}</span><span class="iv-totl"><small>ENSEMBLE</small><b>{len(df)} prestataires</b></span></span>' if total else
                       f'<span class="iv-prov">{avatar(name)}<b>{escape(name)}</b></span>')
                late = f'<small>dont {n_fmt(r["en_retard"])} en retard</small>' if int(r["restants"]) and int(r["en_retard"]) else ""
                return (f'<div class="iv-prow v2{" tot" if total else ""}">{who}{bar}<span class="iv-pn">{n_fmt(r["prevus"])}</span>'
                        f'<span class="iv-pn real">{n_fmt(r["realises"])}</span><span class="iv-pn miss">{n_fmt(miss)}{late}</span>'
                        f'<span class="iv-rate {tone(rate)}">{rate:.0f} %</span></div>')
            rows = [row(r.provider_name, r._asdict()) for r in df.itertuples()]
            tot = {k: int(df[k].sum()) for k in ("realises", "prevus", "non_realises", "restants", "annules", "en_retard")}
            legend = ('<div class="iv-plegend"><span><i style="background:#008080"></i>Réalisés</span><span><i style="background:#F5A524"></i>Clôturés non réalisés</span>'
                      '<span><i style="background:#F78BC7"></i>Restants</span><span><i style="background:#C9CFE0"></i>Annulés</span>'
                      '<em>Taux : vert à partir de 85 %, jaune de 70 à 85 %, rouge en dessous de 70 %. Classés du plus grand au plus petit nombre de passages prévus.</em></div>')
            st.markdown('<div class="iv-prow v2 head"><span>PRESTATAIRE</span><span>CE QUE SONT DEVENUS LES PASSAGES PRÉVUS</span><span>PRÉVUS</span>'
                        '<span>RÉALISÉS</span><span>NON RÉALISÉS</span><span>TAUX</span></div>' + row("", tot, True) + "".join(rows) + legend,
                        unsafe_allow_html=True)
        guard(draw, "Réalisation par prestataire")


# ---------------------------------------------------------------- pages
def tabs_row(wt, key):
    spacer, tabs = st.columns([4, 2.2])
    with tabs:
        return st.segmented_control("Vue", ["Interventions", "Comparatif"], default="Interventions", key=f"tab_{key}",
                                    label_visibility="collapsed") or "Interventions"


def prev_page(filters, start, end):
    sm = guard(lambda: iv.prev_summary(filters, start, end), "Prévu et réalisé")
    if sm is None:
        return
    prevus = int(sm["prevus"])
    if not prevus:
        C.note("Aucun passage prévu sur ce périmètre.")
        return
    real = int(sm["realises"])
    non_real, restants, annules = int(sm["cloturees_non_realisees"]), int(sm["restants"]), int(sm["annules"])
    en_retard_now = int(sm["actuellement_en_retard"])
    taux = 100 * real / prevus
    left, right = st.columns([1.25, 1])
    with left, st.container(key="iv_prev_tiles"):
        C.card_title("Où en sont les passages prévus", "Passages prévus sur la période (date prévue) et ce qu'ils sont devenus. Chaque passage est dans un seul groupe.",
                     "On prend tous les passages dont la date prévue tombe dans la période. Chacun est classé dans un seul groupe : "
                     "réalisé (le prestataire est passé et a terminé), clôturé non réalisé (dossier fermé sans que le travail soit fait, "
                     "par exemple occupant absent), restant (pas encore fait ni fermé) ou annulé. "
                     "Le taux de réalisation = réalisés divisé par tous les passages prévus. Les passages refusés ne sont pas comptés.")
        base_line(prevus, "passages prévus (date prévue dans la période)")
        parts = [("Réalisés", real, "#008080", "passages faits"), ("Clôturés non réalisés", non_real, "#F5A524", "occupant absent, réparation partielle"),
                 ("Restants", restants, "#F78BC7", f"dont {n_fmt(en_retard_now)} en retard aujourd'hui"), ("Annulés", annules, "#C9CFE0", "")]
        rows = "".join(f'<div class="iv-dl"><u style="background:{c}"></u><span>{lbl}<small class="iv-sub">{escape(sub)}</small></span>'
                       f'<b>{n_fmt(n)}</b><small>{100 * n / prevus:.0f} %</small></div>' for lbl, n, c, sub in parts)
        st.markdown(f'<div class="iv-pg"><div class="iv-ring" style="--p:{taux:.1f}"><div><b>{taux:.0f} %</b><small>réalisés sur {n_fmt(prevus)} prévus</small></div></div>'
                    f'<div class="iv-pgr">{_stack([(c, n) for _, n, c, _ in parts], prevus)}<div class="iv-dlist">{rows}</div></div></div>',
                    unsafe_allow_html=True)
    with right, st.container(key="iv_prev_punct"):
        C.card_title("Ponctualité des passages prévus", "À l'heure ou en retard, y compris les passages pas encore faits dont la date est dépassée.",
                     "On regarde les passages réalisés et les passages restants. Dans le délai : fait le jour prévu ou avant. Réalisé en retard : fait après la date prévue. "
                     "Non réalisé en retard : pas encore fait alors que la date prévue est dépassée. Pas encore échu : pas encore fait, mais la date prévue n'est pas dépassée. "
                     "Inconnue : réalisé mais sans date prévue dans la donnée. Le pourcentage compare les passages à l'heure à tous les passages en retard, sans les inconnus.")
        ok, late_r, unk = int(sm["dans_delai"]), int(sm["en_retard_realise"]), int(sm["ponctualite_inconnue"])
        late_o = int(sm["actuellement_en_retard"])
        wait = max(restants - late_o, 0)
        late = late_r + late_o
        known = ok + late
        pct_ok = 100 * ok / known if known else 0
        pct_late = 100 - pct_ok if known else 0
        base_line(ok + late + unk + wait, "passages réalisés ou restants (hors annulés et clôturés non réalisés)")
        rows = [("Dans le délai", "fait le jour prévu ou avant", ok, "#008080"),
                ("Réalisés en retard", "faits après la date prévue", late_r, "#E5114D"),
                ("Non réalisés, en retard", "pas faits, date prévue dépassée", late_o, "#9B0B3A")]
        st.markdown(
            f'<div class="iv-hero two"><div style="--g:#008080"><b>{pct_ok:.0f} %</b><span><u></u>à l\'heure</span></div>'
            f'<div style="--g:#E5114D"><b>{pct_late:.0f} %</b><span><u></u>en retard</span></div></div>'
            f'<div class="iv-herosub">sur {n_fmt(known)} passages dont on peut juger la ponctualité</div>'
            + _stack([(c, n) for _, _, n, c in rows], known or 1)
            + '<div class="iv-dlist">'
            + "".join(f'<div class="iv-dl"><u style="background:{c}"></u><span>{lbl}<small class="iv-sub">{sub}</small></span><b>{n_fmt(n)}</b>'
                      f'<small>{100 * n / (known or 1):.0f} %</small></div>' for lbl, sub, n, c in rows)
            + '</div>'
            + '<div class="iv-unj"><div class="iv-unjt">Non jugés</div>'
            + (f'<div class="iv-unjr warn"><b>{n_fmt(unk)}</b><span>passages réalisés sans date prévue dans la donnée : impossible de dire s\'ils étaient en retard</span></div>' if unk else "")
            + (f'<div class="iv-unjr"><b>{n_fmt(wait)}</b><span>passages pas encore faits, mais la date prévue n\'est pas dépassée</span></div>' if wait else "")
            + '</div>', unsafe_allow_html=True)
    monthly_card("preventive", "prev", filters, start, end)
    planned_card(filters, start, end)
    list_card("preventive", filters, start, end)
    date_source_card(sm, prevus)


def date_source_card(sm, prevus):
    """Repli en bas de page : d'où vient la date prévue, donc la fiabilité de la période."""
    with st.expander("D'où vient la date prévue ?", expanded=False, key="iv_transparency_prev"):
        src = [("Date prévue de l'événement en cours", int(sm["date_courante"]), "#008080", "la plus fiable"),
               ("Date retrouvée dans l'historique", int(sm["date_historique"]), "#0074FF", "fiable"),
               ("Date de création, par défaut", int(sm["date_defaut"]), "#C9CFE0", "aucune date prévue dans la donnée : la création sert de repère")]
        share = 100 * (src[0][1] + src[1][1]) / prevus
        rows = "".join(f'<div class="iv-fs"><div class="iv-fst"><b>{escape(l)}</b><small>{escape(s)}</small></div>'
                       f'<div class="iv-fsb"><i style="width:{max(100 * n / prevus, 0.6):.2f}%;background:{c}"></i></div>'
                       f'<div class="iv-fsn"><b>{n_fmt(n)}</b><small>{100 * n / prevus:.0f} %</small></div></div>' for l, n, c, s in src)
        st.markdown(f'<div class="iv-fun"><div class="iv-ring" style="--p:{share:.1f}"><div><b>{share:.0f} %</b><small>ont une vraie date prévue</small></div></div>'
                    f'<div class="iv-fsteps">{rows}<div class="iv-fnote">Pour les passages sans date prévue, la période est calculée à partir de la date de création.</div></div></div>',
                    unsafe_allow_html=True)


def render_work_page(wt, filters, start, end):
    key = "cur" if wt == "corrective" else "prev"
    tab = tabs_row(wt, key)
    if tab == "Comparatif":
        df = guard(lambda: compare_card(wt, filters, start, end), "Tableau comparatif")
        analysis_card(wt, filters, start, end, df)
        return
    if wt == "preventive":
        prev_page(filters, start, end)
        return
    status_df = guard(lambda: iv.status_breakdown(filters, start, end, wt), "Répartition par statut")
    if status_df is None or not len(status_df):
        C.note("Aucune intervention sur ce périmètre.")
        return
    left, right = st.columns([1, 1.15])
    with left:
        donut_card(status_df, wt, key)
    with right:
        monthly_card(wt, key, filters, start, end)
    active_card(status_df, wt)
    a, b = st.columns(2)
    with a:
        end_card(status_df, filters, start, end)
    with b:
        causes_card(filters, start, end)
    list_card(wt, filters, start, end)
    transparency_card(filters, start, end)


def _rep_ranking(df, avg, what_sing):
    """Classement simple : une barre de taux par ligne, le trait vertical est la moyenne. Les lignes à trop peu de cas sont repliées en bas."""
    solid = df[df["verifiees"] >= iv.MIN_BASE].sort_values(["taux", "verifiees"], ascending=[True, False]).head(10)
    weak = df[df["verifiees"] < iv.MIN_BASE].sort_values(["verifiees", "name"], ascending=[False, True])
    top = ""
    if len(solid) > 1 and avg is not None:
        w_, b_ = solid.iloc[0], solid.iloc[-1]
        gap = round(abs(avg - w_["taux"]))
        top = (f'<div class="an-story"><b>{escape(str(w_["name"]))} est le moins conforme : {w_["taux"]:.0f} % de rapports'
               + (f', {gap} points sous la moyenne ({avg:.0f} %).' if gap >= 3 else f' (moyenne {avg:.0f} %), les écarts sont faibles.') + '</b></div>')
    elif not len(solid):
        top = f'<div class="an-story"><b>Aucun {what_sing} n\'a encore {iv.MIN_BASE} clôturées vérifiées : pas de classement possible.</b></div>'
    avatar_on = what_sing == "prestataire"
    rows = []
    if len(solid):
        rows.append(f'<div class="sm-row head"><span>{what_sing.upper()}</span><span>AVEC RAPPORT <i class="sm-key"></i> moyenne {avg:.0f} %</span><span></span></div>')
    for n, r in enumerate(solid.itertuples(), 1):
        d = r.taux - avg
        color = "#E5114D" if d <= -3 else "#008080" if d >= 3 else "#173B69"
        lead = avatar(r.name) if avatar_on else ""
        rows.append(f'<div class="sm-row"><span class="iv-prov">{lead}<b>{escape(str(r.name))}</b></span>'
                    f'<span class="an-bar"><i style="width:{max(r.taux, .8):.1f}%;background:{color}"></i><i class="an-avg" style="left:{avg:.1f}%"></i></span>'
                    f'<span class="an-val"><b>{r.taux:.0f} %</b><small>{n_fmt(r.avec)} sur {n_fmt(r.verifiees)}</small></span></div>')
    more = ""
    if len(weak):
        items = "".join(f'<div class="sm-mrow"><span>{escape(str(r.name))}</span><small>{n_fmt(r.avec)} sur {n_fmt(r.verifiees)}</small></div>' for r in weak.itertuples())
        plural = "s" if len(weak) > 1 else ""
        more = (f'<details class="sm-more"><summary>{len(weak)} {what_sing}{plural} avec moins de {iv.MIN_BASE} clôturées vérifiées, non classé{plural}</summary>{items}</details>')
    return top, '<div class="sm-table">' + "".join(rows) + "</div>" + more


def render_quality(filters, start, end):
    sm = iv.reports_summary(filters, start, end)
    verif = sm["avec"] + sm["sans"]
    clot = verif + sm["inconnu"]
    avg = 100 * sm["avec"] / verif if verif else None

    left, right = st.columns(2)
    with left, st.container(key="iv_qual_sum"):
        def draw_sum():
            C.card_title("Où en est la conformité", "Part des interventions clôturées qui ont un rapport dans Intent.",
                         "On ne juge que les clôturées dont on a pu vérifier les documents (avec ou sans rapport). "
                         "Celles qu'on n'a pas encore pu vérifier sont affichées à part et ne comptent jamais comme « sans rapport ». "
                         "Taux = avec rapport divisé par (avec + sans).")
            if not clot:
                C.note("Aucune intervention clôturée sur la période et les filtres actifs.")
                return
            base_line(clot, "interventions clôturées")
            share_v = 100 * verif / clot
            st.markdown(
                f'<div class="qr-hero"><div class="iv-ring" style="--p:{avg or 0:.1f}"><div><b>{(f"{avg:.0f} %" if avg is not None else "n/d")}</b><small>ont un rapport</small></div></div>'
                f'<div class="qr-herotxt"><b>{n_fmt(sm["avec"])} sur {n_fmt(verif)}</b><span>clôturées vérifiées ont un rapport.</span>'
                f'<span class="qr-cov">{share_v:.0f} % des clôturées sont vérifiées, {n_fmt(sm["inconnu"])} restent à vérifier.</span></div></div>',
                unsafe_allow_html=True)
            parts = [("#008080", sm["avec"]), ("#E5114D", sm["sans"]), ("#C9CFE0", sm["inconnu"])]
            st.markdown(_stack(parts, clot), unsafe_allow_html=True)
            leg = "".join(f'<div class="qr-leg"><i style="background:{c}"></i><span>{lbl}</span><b>{n_fmt(n)}</b><small>{pct_fmt(100 * n / clot)}</small></div>'
                          for c, lbl, n in [("#008080", "Avec rapport", sm["avec"]), ("#E5114D", "Sans rapport", sm["sans"]), ("#C9CFE0", "Non vérifiées", sm["inconnu"])])
            st.markdown(f'<div class="qr-legs">{leg}</div>', unsafe_allow_html=True)
        guard(draw_sum, "Conformité")
    with right, st.container(key="iv_qual_month"):
        def draw_month():
            C.card_title("Évolution mensuelle", "Taux de rapports présents, mois par mois.",
                         "Chaque point est le taux du mois : avec rapport divisé par (avec + sans). "
                         "Le dernier mois est souvent incomplet, car les documents ne sont pas encore tous vérifiés.")
            df = iv.reports_monthly(filters, start, end)
            df = df[df["verifiees"] > 0]
            if not len(df):
                C.note("Aucune donnée vérifiée sur la période et les filtres actifs.")
                return
            base_line(int(df["verifiees"].sum()), "clôturées vérifiées")
            ok = df[df["verifiees"] >= iv.MIN_BASE]
            if len(ok) > 1:
                hi, lo = ok.loc[ok["taux"].idxmax()], ok.loc[ok["taux"].idxmin()]
                st.markdown(f'<div class="an-story"><b>Meilleur mois : {escape(hi["periode"])} ({hi["taux"]:.0f} %). Plus bas : {escape(lo["periode"])} ({lo["taux"]:.0f} %).</b>'
                            f'<span>Moyenne de la période : {avg:.0f} %.</span></div>', unsafe_allow_html=True)
            x, y = df["periode"].tolist(), df["taux"].round(1).tolist()
            up, lo_ = [max(v, avg) for v in y], [min(v, avg) for v in y]
            base_ = [avg] * len(y)
            tone = ["#008080" if v > avg + .5 else "#E5114D" if v < avg - .5 else "#173B69" for v in y]
            size = [9] * len(y)
            fig = go.Figure()
            fig.add_scatter(x=x, y=base_, mode="lines", line=dict(color="#9AA0B3", width=1, dash="dash"), hoverinfo="skip", showlegend=False)
            fig.add_scatter(x=x, y=up, mode="lines", line=dict(width=0, shape="spline"), fill="tonexty", fillcolor="rgba(0,128,128,.16)", hoverinfo="skip", showlegend=False)
            fig.add_scatter(x=x, y=base_, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
            fig.add_scatter(x=x, y=lo_, mode="lines", line=dict(width=0, shape="spline"), fill="tonexty", fillcolor="rgba(229,17,77,.14)", hoverinfo="skip", showlegend=False)
            fig.add_scatter(x=x, y=y, mode="lines+markers+text", line=dict(color="#173B69", width=3, shape="spline", smoothing=.6),
                            marker=dict(size=size, color="#fff", line=dict(color=tone, width=3)),
                            text=[f"{v:.0f} %" for v in y], textposition="top center", textfont=dict(size=11, color="#173B69"),
                            customdata=list(zip(df["avec"], df["verifiees"])),
                            hovertemplate="%{x} : %{y:.1f} %<br>%{customdata[0]:,.0f} sur %{customdata[1]:,.0f} vérifiées<extra></extra>", showlegend=False)
            fig.update_layout(height=300, margin=dict(l=0, r=10, t=14, b=0), plot_bgcolor="#fff", paper_bgcolor="#fff", font=dict(family="Nunito, Segoe UI, Arial, sans-serif"),
                              xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=12, color="#5F566A")),
                              yaxis=dict(visible=False, range=[max(0, min(y) - 8), min(100, max(y) + 8)]))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="qual_month_chart")
        guard(draw_month, "Évolution mensuelle")

    left2, right2 = st.columns(2)
    with left2, st.container(key="iv_qual_prov"):
        def draw():
            C.card_title("Conformité par prestataire", "Du moins conforme au mieux placé, comparé à la moyenne.",
                         f"Taux = clôturées avec rapport divisé par clôturées vérifiées. Un prestataire est classé à partir de {iv.MIN_BASE} clôturées vérifiées. "
                         "Le trait vertical est la moyenne de l'ensemble.")
            df = iv.reports_by(filters, start, end, "prestataire")
            if not len(df):
                C.note("Aucune clôturée sur la période et les filtres actifs.")
                return
            base_line(int(df["verifiees"].sum()), "clôturées vérifiées (tous prestataires)")
            story, html = _rep_ranking(df, avg, "prestataire")
            st.markdown(story + html, unsafe_allow_html=True)
        guard(draw, "Conformité")
    with right2, st.container(key="iv_qual_metier"):
        def draw2():
            C.card_title("Conformité par métier", "Où les rapports manquent le plus.",
                         f"Même calcul que pour les prestataires, par métier. Un métier est classé à partir de {iv.MIN_BASE} clôturées vérifiées.")
            df = iv.reports_by(filters, start, end, "metier")
            if not len(df):
                C.note("Aucune clôturée sur la période et les filtres actifs.")
                return
            base_line(int(df["verifiees"].sum()), "clôturées vérifiées (tous métiers)")
            story, html = _rep_ranking(df, avg, "métier")
            st.markdown(story + html, unsafe_allow_html=True)
        guard(draw2, "Conformité par métier")
    with st.container(key="iv_qual_list"):
        _qopen = C.list_header("qual", "Liste des interventions clôturées", "Contrôle de présence du rapport dans Intent")
        h1, h2, h3 = st.columns([0.01, 4.4, 0.6], vertical_alignment="center") if _qopen else (None, None, None)
        mode = st.session_state.get("qual_mode", "Tous")
        def draw3():
            nonlocal mode
            with h2:
                needle = st.text_input("Recherche", key="qual_search", label_visibility="collapsed", icon=":material/search:",
                                       placeholder="Rechercher une référence, un équipement, un programme...")
            QL = "qual"
            etat_col = colui.etat(QL, QUAL_COLS)
            extra = colf.appliquer(etat_col, QUAL_COLS)
            _, _, counts = iv.reports_list(filters, start, end, "Tous", "", 1, 0, extra)
            mode = st.segmented_control("Rapport", ["Tous", "Avec rapport", "Sans rapport", "Non vérifié"], default="Tous", key="qual_mode",
                                        label_visibility="collapsed",
                                        format_func=lambda v: f"{v} ({counts[v]})") or "Tous"
            sig = (mode, needle, repr(filters), repr(etat_col))
            if st.session_state.get("qual_sig") != sig:
                st.session_state["qual_sig"] = sig
                st.session_state["qual_page"] = 1
            page_no = int(st.session_state.get("qual_page", 1))
            df, total, _ = iv.reports_list(filters, start, end, mode, needle, PAGE_SIZE, (page_no - 1) * PAGE_SIZE, extra)
            with h3:
                C.download_xlsx(df.drop(columns=["work_type", "rapport_statut"], errors="ignore"), f"rex_rapports_p{page_no}.xlsx", "export_qual", label="")
            body = []
            for r in df.itertuples():
                kind = "Curatif" if r.type == "Curatif" else "Préventif"
                rap = (f'<b>Oui · {escape(r.rapport)}</b>' if r.rapport_statut == "avec"
                       else '<b class="iv-over">Non</b>' if r.rapport_statut == "sans" else '<span class="pf-dash">Non vérifié</span>')
                body.append('<div class="pf-lrow">' + "".join(f"<span>{c}</span>" for c in [
                    f'<span class="pf-lref plain"><b>{escape(str(r.reference))}</b></span>',
                    (f'<span class="pf-eq">{escape(str(r.esi))}</span>' if pd.notna(r.esi) and str(r.esi).strip() else '<span class="pf-eq none">Sans équipement</span>'),
                    f'<span class="pf-lref plain"><b>{escape(str(r.residence))}</b><small>{escape(str(r.objet))}</small></span>',
                    f'<span class="pf-tag {"late" if kind == "Curatif" else "ok"}">{kind}</span>', escape(str(r.metier)),
                    f'<span class="iv-prov">{avatar(r.provider_name)}<b>{escape(r.provider_name)}</b></span>',
                    C.fr_date(r.cloturee, "%d/%m"), rap]) + "</div>")
            n_col = len(etat_col["v"]) + len(etat_col["t"]) + len(etat_col["n"])
            if n_col or etat_col["tri"]:
                st.button(f"Effacer les filtres ({n_col})" if n_col else "Effacer le tri", key="qual_clear", on_click=colui.tout_effacer,
                          args=(QL, QUAL_COLS), icon=":material/filter_alt_off:")
            colui.en_tete(QL, [("reference", "Référence"), ("equipement", "Équipement"), ("programme", "Programme · service"), ("type", "Type"),
                               ("metier", "Métier"), ("prestataire", "Prestataire"), ("cloturee", "Clôturée"), ("rapport", "Rapport")],
                          QUAL_CSS, {"type": {"corrective": "Curatif", "preventive": "Préventif"}, "metier": _libelles("Métier", filters, start, end),
                                     "prestataire": _libelles("Prestataire", filters, start, end),
                                     "rapport": {"avec": "Avec rapport", "sans": "Sans rapport", "non_verifie": "Non vérifié", "erreur_api": "Erreur de vérification"}})
            if not len(df):
                C.note("Aucune intervention ne correspond aux filtres.")
                return
            st.markdown(f'<div class="pf-ltable" style="--cols:{QUAL_CSS};margin-top:.2rem">' + "".join(body) + "</div>", unsafe_allow_html=True)
            page_no, pages = pager("qual_page", total)
            pager_controls("qual_page", page_no, pages, total, len(df))
        if _qopen:
            guard(draw3, "Liste des interventions clôturées")


def render(page, filters, start, end, ctx):
    """Point d'entrée : page = 'Curatives', 'Préventives' ou 'Qualité des rapports'."""
    C.__dict__.update(ctx)
    _SCOPE.update(filters=filters, start=start, end=end)
    if page == "Qualité des rapports":
        render_quality(filters, start, end)
    else:
        render_work_page(iv.WORK[page], filters, start, end)