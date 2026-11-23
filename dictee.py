"""Dictée vocale : la reconnaissance de la parole du navigateur (Web Speech API), sans bibliothèque à installer.

Chrome et Edge transmettent l’audio à leur service de reconnaissance ; Safari traite selon les réglages de l’appareil.
Sur téléphone, le micro du clavier reste une alternative qui fonctionne partout.
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_composant = components.declare_component('dictee', path=str(Path(__file__).resolve().parent / 'composants' / 'dictee'))


def dictee(key, label='Dicter'):
    """Affiche le bouton de dictée ; renvoie le texte dicté une seule fois, juste après l’arrêt, sinon ''."""
    valeur = _composant(label=label, key=key, default=None)
    if valeur and valeur.get('id') != st.session_state.get(key + '-lu'):
        st.session_state[key + '-lu'] = valeur.get('id')
        return (valeur.get('text') or '').strip()
    return ''


def ajouter(cle_texte, texte):
    """Ajoute le texte dicté à la suite d’un champ (à appeler avant que le champ ne soit affiché)."""
    actuel = (st.session_state.get(cle_texte) or '').rstrip()
    st.session_state[cle_texte] = (actuel + ('\n\n' if actuel else '') + texte[:1].upper() + texte[1:]).strip()
