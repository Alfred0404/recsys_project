"""Streamlit front end. Run: streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from client import recommend  # noqa: E402

st.set_page_config(page_title="Recommandation financière", layout="wide")
st.title("Recommandation d'actifs")

use_mock = st.sidebar.toggle("Réponse factice (API non branchée)", value=True)

st.subheader("Votre portefeuille")
holdings_df = st.data_editor(
    pd.DataFrame({"ISIN": ["FR0000000001"], "montant": [1000.0]}),
    num_rows="dynamic", width="stretch",
)
free_text = st.text_area("Décrivez votre objectif en quelques mots (optionnel)")

if st.button("Recommander", type="primary"):
    holdings = {r.ISIN: float(r.montant) for r in holdings_df.itertuples() if r.ISIN and r.montant == r.montant}
    payload = {"holdings": holdings, "answers": {}, "free_text": free_text}
    try:
        result = recommend(payload, use_mock=use_mock)
    except Exception as exc:  # network error, API down, bad status
        st.error(f"Appel à /recommend impossible : {exc}")
    else:
        left, right = st.columns([2, 1])
        with left:
            st.subheader("Suggestions")
            st.dataframe(pd.DataFrame(result["items"]), width="stretch", hide_index=True)
        with right:
            st.subheader("Profil")
            st.json(result["profile"])
