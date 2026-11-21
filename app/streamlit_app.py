"""Streamlit interface for the FAR-Trans recommendation demo."""

import sys
from pathlib import Path
from uuid import uuid4

import pandas as pd
import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.client import catalog, log_interaction, recommend, review_profile  # noqa: E402
from src.llm.profile import QUESTIONNAIRE  # noqa: E402


st.set_page_config(page_title="Recommandation d’actifs", layout="wide")
st.title("Recommandation d’actifs")
st.caption("Explorez comment des actifs issus de FAR-Trans compléteraient votre portefeuille. Démonstration pédagogique.")


@st.cache_data(ttl=60, show_spinner=False)
def load_catalog() -> dict[str, str]:
    return {asset["isin"]: asset["name"] for asset in catalog()}


try:
    names = load_catalog()
except requests.RequestException:
    st.error("Impossible de charger le catalogue. Démarrez l’API et rechargez cette page.")
    st.stop()

if "session_uuid" not in st.session_state:
    st.session_state.session_uuid = str(uuid4())

inputs, output = st.columns([1, 2], gap="large")
levels = {1: "Prudent", 2: "Modéré", 3: "Équilibré", 4: "Dynamique"}

with inputs:
    st.subheader("Portefeuille")
    symbols = st.multiselect("Actifs détenus", list(names), max_selections=100,
                             format_func=lambda isin: f"{names[isin]} · {isin}")
    with st.form("recommendation_form"):
        holdings = {
            isin: st.number_input(f"Montant pour {names[isin]} (€)", min_value=0.01, value=1000.0,
                                  key=f"amount_{isin}")
            for isin in symbols
        }
        st.subheader("Tolérance au risque")
        answers = {
            key: st.selectbox(label, range(len(options)), index=1, format_func=options.__getitem__)
            for key, (label, options) in QUESTIONNAIRE.items()
        }
        submitted = st.form_submit_button("Afficher les suggestions", type="primary")

    st.caption("Le journal de la démo enregistre le type d’action et un identifiant aléatoire de session.")

if submitted:
    st.session_state.pop("recommendation_result", None)
    st.session_state.pop("recommendation_error", None)
    st.session_state.pop("feedback_ack", None)
    st.session_state.pop("profile_review", None)
    payload = {"holdings": holdings, "answers": answers}
    try:
        with output, st.spinner("Calcul des suggestions…"):
            st.session_state.recommendation_result = recommend(payload)
            st.session_state.recommendation_payload = payload
    except requests.RequestException:
        st.session_state.recommendation_error = "Le serveur n’a pas pu calculer les suggestions. Réessayez."
    else:
        try:
            log_interaction(st.session_state.session_uuid, "portfolio_entered")
            log_interaction(st.session_state.session_uuid, "recommendation_viewed")
        except requests.RequestException:
            output.warning("Les suggestions sont disponibles. Le journal de la démo n’a pas été mis à jour.")

with output:
    st.subheader("Suggestions")
    if error := st.session_state.get("recommendation_error"):
        st.error(error)
    if result := st.session_state.get("recommendation_result"):
        profile = result["profile"]
        level_label = levels[profile["risk_level"]]
        st.caption(f"Profil {level_label} · plafond de risque {profile['ceiling']}/7")
        for gap in profile["gaps"]:
            st.write(gap)
        if result["ranking_source"] == "popularity":
            st.info("Le classement part des actifs les plus détenus lorsque le portefeuille est vide ou inconnu.")
        if result["items"]:
            rows = pd.DataFrame(result["items"])[["name", "isin", "risk_class", "variance_change"]]
            st.dataframe(rows, hide_index=True, width="stretch", column_config={
                "name": "Actif", "isin": "ISIN", "risk_class": "Risque / 7",
                "variance_change": st.column_config.NumberColumn("Écart de variance", format="%.4f"),
            })
            st.caption("Écart de variance annualisée pour une allocation hypothétique de 10 %.")
            useful, not_useful = st.columns(2)
            feedback = None
            if useful.button("Suggestions utiles"):
                feedback = "feedback_positive"
            if not_useful.button("Suggestions à améliorer"):
                feedback = "feedback_negative"
            if feedback:
                try:
                    log_interaction(st.session_state.session_uuid, feedback)
                    st.session_state.feedback_ack = True
                except requests.RequestException:
                    st.warning("Votre retour n’a pas pu être enregistré. Réessayez.")
            if st.session_state.get("feedback_ack"):
                st.caption("Merci pour votre retour.")
        else:
            st.info("Aucun candidat ne respecte le plafond de risque de ce profil.")
        st.caption(f"Temps de calcul API : {result['server_ms']:.0f} ms")
        if result["profile_review_available"]:
            if st.button("Vérifier le profil avec le modèle local"):
                try:
                    with st.spinner("Vérification du profil…"):
                        st.session_state.profile_review = review_profile(st.session_state.recommendation_payload)
                except requests.RequestException:
                    st.warning("Le serveur n’a pas terminé la vérification du profil.")
            if review := st.session_state.get("profile_review"):
                review_status = {
                    "verified": "Le modèle local a confirmé le profil.",
                    "refined": "La proposition du modèle local a été corrigée et vérifiée.",
                    "rules_fallback": "Le questionnaire a servi à établir le profil après vérification.",
                }
                st.caption(review_status.get(review["status"], "Le profil provient du questionnaire."))
    elif not st.session_state.get("recommendation_error"):
        st.info("Renseignez votre profil pour obtenir des suggestions. Le portefeuille peut être vide.")
