"""Sélecteur unique (recherche en direct + liste à cocher), identique pour tous les filtres.
Remplace st.multiselect : on voit ce qu'on tape, les libellés longs passent à la ligne,
la sélection reste visible sous forme de pastilles. L'état est écrit dans st.session_state[key] (liste de références)."""
import streamlit as st
import streamlit.components.v2 as v2

_CSS = """
:host { display: block; font-family: "Nunito", "Segoe UI", Arial, sans-serif; }
* { box-sizing: border-box; font-family: "Nunito", "Segoe UI", Arial, sans-serif; }
.pk { color: #2B2433; font-size: 14px; min-width: 0; }
.srch { position: relative; }
.srch svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; color: #8A8294; pointer-events: none; }
.srch input { width: 100%; height: 42px; border: 1.5px solid #EADFE6; border-radius: 12px; padding: 0 38px 0 36px; font-size: 14px;
  color: #2B2433; background: #FBF8FA; outline: none; transition: border-color .15s, box-shadow .15s, background .15s; }
.srch input:focus { border-color: #E5114D; background: #fff; box-shadow: 0 0 0 3px rgba(229,17,77,.12); }
.srch input::placeholder { color: #9A91A4; }
.srch .x { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); width: 24px; height: 24px; border: 0; border-radius: 50%;
  background: #F1E8EE; color: #6B6275; cursor: pointer; font-size: 15px; line-height: 1; display: none; }
.srch .x:hover { background: #E5114D; color: #fff; }
.chips { display: flex; flex-wrap: wrap; gap: 5px; margin: 8px 0 0; max-height: 58px; overflow-y: auto; }
.chip { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; background: #FBF1F5; color: #8E1038; border: 1px solid #F3D3DE; border-radius: 999px;
  padding: 2px 5px 2px 9px; font-size: 11.5px; font-weight: 600; cursor: pointer; border: 0; }
.chip span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.chip i { font-style: normal; width: 15px; height: 15px; border-radius: 50%; background: #F3D3DE; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; flex: none; }
.chip:hover { background: #E5114D; color: #fff; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 10px 2px 4px; font-size: 12.5px; color: #7B7385; }
.bar .act { display: flex; gap: 14px; }
.bar button { border: 0; background: none; padding: 0; color: #E5114D; font-weight: 700; font-size: 12.5px; cursor: pointer; }
.bar button:hover { text-decoration: underline; }
.bar button[disabled] { color: #C9C0CF; cursor: default; text-decoration: none; }
.list { max-height: 260px; overflow-y: auto; border: 1px solid #F1E8EE; border-radius: 12px; padding: 4px; background: #fff; }
.row { display: flex; align-items: flex-start; gap: 10px; padding: 8px 10px; border-radius: 9px; cursor: pointer; line-height: 1.3; }
.row:hover, .row.cur { background: #FBF1F5; }
.box { flex: none; width: 18px; height: 18px; margin-top: 1px; border: 1.8px solid #CFC4D3; border-radius: 5px; display: flex; align-items: center; justify-content: center; background: #fff; transition: all .12s; }
.row.on .box { background: #E5114D; border-color: #E5114D; }
.row.on .box::after { content: ""; width: 5px; height: 9px; border: solid #fff; border-width: 0 2px 2px 0; transform: rotate(45deg) translate(-1px, -1px); }
.txt { min-width: 0; overflow-wrap: anywhere; }
.txt b { color: #173B69; font-weight: 700; }
.txt em { font-style: normal; color: #2B2433; }
.row.on { background: #FFF5F8; } .row.on .txt b { color: #B30E3E; }
mark { background: #FFDC55; color: inherit; border-radius: 3px; padding: 0 1px; }
.empty { padding: 22px 12px; text-align: center; color: #8A8294; }
.more { padding: 8px 10px; color: #8A8294; font-size: 12.5px; text-align: center; }
"""

_JS = r"""
export default function({ parentElement, data, setStateValue }) {
  const root = parentElement;
  const MAX = 150;
  const st = root.__st || (root.__st = { q: "", sel: null, cur: 0, sig: null });
  const norm = s => (s || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const opts = data.options || [];
  const sig = JSON.stringify([data.selected || [], opts.length, data.key]);
  if (st.sig !== sig) { st.sel = new Set(data.selected || []); st.sig = sig; }
  const byV = new Map(opts.map(o => [o.v, o]));
  const emit = () => { st.sig = JSON.stringify([[...st.sel], opts.length, data.key]); setStateValue("selected", [...st.sel]); };

  if (!root.querySelector(".pk")) {
    root.innerHTML = "<style>" + __CSS__ + "</style>" + `<div class="pk">
      <div class="srch"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input type="text" autocomplete="off" spellcheck="false"><button class="x" type="button" title="Effacer la recherche">×</button></div>
      <div class="chips"></div><div class="bar"></div><div class="list"></div></div>`;
    ["mousedown", "mouseup", "click", "pointerdown", "pointerup", "touchstart"].forEach(ev => root.querySelector(".pk").addEventListener(ev, e => e.stopPropagation()));
    const inp = root.querySelector("input");
    inp.addEventListener("input", () => { st.q = inp.value; st.cur = 0; draw(); });
    inp.addEventListener("keydown", e => {
      const rows = matches();
      if (e.key === "ArrowDown") { st.cur = Math.min(st.cur + 1, Math.min(rows.length, MAX) - 1); draw(true); e.preventDefault(); }
      else if (e.key === "ArrowUp") { st.cur = Math.max(st.cur - 1, 0); draw(true); e.preventDefault(); }
      else if (e.key === "Enter") { const o = rows[st.cur]; if (o) { toggle(o.v); } e.preventDefault(); }
    });
    root.querySelector(".x").addEventListener("click", () => { st.q = ""; inp.value = ""; draw(); inp.focus(); });
  }
  const inp = root.querySelector("input");
  inp.placeholder = data.placeholder || "Rechercher...";
  if (inp.value !== st.q) inp.value = st.q;

  function matches() {
    const t = norm(st.q).split(/\s+/).filter(Boolean);
    return opts.filter(o => { const h = norm(o.l) + " " + norm(o.v); return t.every(x => h.includes(x)); });
  }
  function toggle(v) { st.sel.has(v) ? st.sel.delete(v) : st.sel.add(v); emit(); draw(true); }
  function hl(text) {
    const t = norm(st.q).split(/\s+/).filter(Boolean)[0];
    if (!t) return esc(text);
    const n = norm(text), i = n.indexOf(t);
    if (i < 0 || n.length !== text.length) return esc(text);
    return esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + t.length)) + "</mark>" + esc(text.slice(i + t.length));
  }
  function label(o) {
    const k = o.l.indexOf(" / ");
    if (data.split && k > 0) return `<b>${hl(o.l.slice(0, k))}</b> <em>${hl(o.l.slice(k + 3))}</em>`;
    return `<em>${hl(o.l)}</em>`;
  }
  function draw(keep) {
    root.querySelector(".x").style.display = st.q ? "block" : "none";
    const m = matches(), shown = m.slice(0, MAX), n = st.sel.size;
    const chips = root.querySelector(".chips");
    chips.style.display = n ? "flex" : "none";
    chips.innerHTML = [...st.sel].map(v => `<button class="chip" type="button" data-v="${esc(v)}" title="Retirer"><span>${esc((byV.get(v) || { l: v }).l)}</span><i>×</i></button>`).join("");
    chips.querySelectorAll(".chip").forEach(c => c.onclick = () => toggle(c.dataset.v));
    const allOn = m.length > 0 && m.every(o => st.sel.has(o.v));
    root.querySelector(".bar").innerHTML = `<span>${st.q ? m.length + " résultat" + (m.length > 1 ? "s" : "") + " sur " + opts.length : opts.length + " valeur" + (opts.length > 1 ? "s" : "")}${n ? " · <b style='color:#B30E3E'>" + n + " sélectionnée" + (n > 1 ? "s" : "") + "</b>" : ""}</span>
      <span class="act"><button type="button" class="all" ${m.length ? "" : "disabled"}>${allOn ? "Tout désélectionner" : (st.q ? "Sélectionner les résultats" : "Tout sélectionner")}</button><button type="button" class="clr" ${n ? "" : "disabled"}>Effacer</button></span>`;
    root.querySelector(".all").onclick = () => { if (allOn) m.forEach(o => st.sel.delete(o.v)); else m.forEach(o => st.sel.add(o.v)); emit(); draw(true); };
    root.querySelector(".clr").onclick = () => { st.sel.clear(); emit(); draw(true); };
    const list = root.querySelector(".list"), top = list.scrollTop;
    list.innerHTML = shown.length ? shown.map((o, i) => `<div class="row${st.sel.has(o.v) ? " on" : ""}${i === st.cur ? " cur" : ""}" data-v="${esc(o.v)}"><span class="box"></span><span class="txt">${label(o)}</span></div>`).join("")
        + (m.length > MAX ? `<div class="more">${m.length - MAX} autres valeurs : affinez la recherche</div>` : "")
      : `<div class="empty">Aucun résultat pour « ${esc(st.q)} »</div>`;
    list.querySelectorAll(".row").forEach(r => r.onclick = () => toggle(r.dataset.v));
    if (keep) list.scrollTop = top;
    const cur = list.querySelector(".row.cur"); if (cur && keep === true && st.q) cur.scrollIntoView({ block: "nearest" });
  }
  draw();
}
"""

import json
_comp = v2.component("pf_picker", js=_JS.replace("__CSS__", json.dumps(_CSS)), html="")


def select(key, names, placeholder="Rechercher...", split=False):
    """names : {référence: libellé}. Écrit la sélection dans st.session_state[key] (liste de références)."""
    st.session_state.setdefault(key, [])

    def _sync():
        val = st.session_state["pk_" + key.replace("__", "_")]
        sel = val.get("selected") if isinstance(val, dict) else getattr(val, "selected", None)
        if sel is not None:
            st.session_state[key] = [v for v in sel if v in names]

    _comp(key="pk_" + key.replace("__", "_"), data={"options": [{"v": str(k), "l": str(v)} for k, v in names.items()],
                                  "selected": [v for v in st.session_state[key] if v in names],
                                  "placeholder": placeholder, "split": split, "key": key},
          on_selected_change=_sync)