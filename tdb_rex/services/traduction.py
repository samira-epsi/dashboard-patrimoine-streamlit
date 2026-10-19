"""Traduit en français les textes que Streamlit affiche lui-même (barre des tableaux, filtres, aide à la saisie).
Streamlit n'a pas de réglage de langue : un petit script observe la page et remplace les textes connus.
Pour traduire un nouveau texte, ajouter une ligne dans TEXTES."""
import json
import streamlit.components.v1 as components

TEXTES = {
    "No results": "Aucun résultat",
    "No options to select.": "Aucune option disponible.",
    "Press Enter to apply": "Appuyez sur Entrée pour valider",
    "Press Enter to submit form": "Appuyez sur Entrée pour valider",
    "Choose an option": "Choisir une option",
    "Choose options": "Choisir des options",
    "Select...": "Sélectionner...",
    "Select all": "Tout sélectionner",
    "Clear all": "Tout effacer",
    "Clear": "Effacer",
    "Download as CSV": "Télécharger en CSV",
    "Search": "Rechercher",
    "Fullscreen": "Plein écran",
    "Exit fullscreen": "Quitter le plein écran",
    "Show/hide columns": "Afficher ou masquer les colonnes",
    "Sort ascending": "Tri croissant",
    "Sort descending": "Tri décroissant",
    "Hide column": "Masquer la colonne",
    "Pin column": "Épingler la colonne",
    "Unpin column": "Désépingler la colonne",
    "Autosize": "Ajuster la largeur",
    "Autosize column": "Ajuster la largeur",
    "Deploy": "Déployer",
    "Main menu": "Menu principal",
    "Running...": "Chargement...",
    "Rerun": "Relancer",
    "Settings": "Paramètres",
    "Print": "Imprimer",
    "Record a screencast": "Enregistrer l'écran",
    "About": "À propos",
    "Clear cache": "Vider le cache",
    "Close": "Fermer",
    "Open": "Ouvrir",
    "Show password text": "Afficher le mot de passe",
    "Hide password text": "Masquer le mot de passe",
    # calendrier de la période
    "January": "Janvier", "February": "Février", "March": "Mars", "April": "Avril", "May": "Mai", "June": "Juin", "July": "Juillet",
    "August": "Août", "September": "Septembre", "October": "Octobre", "November": "Novembre", "December": "Décembre",
    "Mo": "Lu", "Tu": "Ma", "We": "Me", "Th": "Je", "Fr": "Ve", "Su": "Di",
    "Past Week": "7 derniers jours", "Past Month": "Dernier mois", "Past 3 Months": "3 derniers mois", "Past 6 Months": "6 derniers mois",
    "Past Year": "Dernière année", "Past 2 Years": "2 dernières années", "Past 7 days": "7 derniers jours",
    "None": "Aucun", "Today": "Aujourd'hui", "Yesterday": "Hier", "Select a date": "Choisir une date",
    "Select a date range": "Choisir une période", "Select a range": "Choisir une période", "Quick select": "Sélection rapide",
    "Previous month.": "Mois précédent", "Next month.": "Mois suivant", "Previous month": "Mois précédent", "Next month": "Mois suivant",
}

_JS = """
<script>
(function(){
 const T=__T__;
 let P;try{P=parent;P.document.body}catch(e){return}
 if(P.__rexTrad)return;P.__rexTrad=true;
 try{P.document.documentElement.lang="fr"}catch(e){}
 const attrs=["placeholder","aria-label","title"];
 function fixAttrs(n){for(const a of attrs){const v=n.getAttribute&&n.getAttribute(a);if(v){const t=T[v.trim()];if(t!==undefined&&t!==v)n.setAttribute(a,t)}}}
 function walk(n){
  if(n.nodeType===3){const k=n.nodeValue.trim();if(k&&T[k]!==undefined&&T[k]!==k)n.nodeValue=n.nodeValue.replace(k,T[k]);return}
  if(n.nodeType!==1||n.tagName==="SCRIPT"||n.tagName==="STYLE")return;
  fixAttrs(n);for(const c of n.childNodes)walk(c)}
 const obs=new P.MutationObserver(ms=>{for(const m of ms){
   if(m.type==="attributes")fixAttrs(m.target);
   else if(m.type==="characterData")walk(m.target);
   else m.addedNodes.forEach(walk)}});
 obs.observe(P.document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:attrs});
 walk(P.document.body);
})();
</script>
"""


def render_traduction():
    """À appeler une fois, tout en haut de app.py : traduit les textes natifs de Streamlit."""
    components.html(_JS.replace("__T__", json.dumps(TEXTES, ensure_ascii=False)), height=0)