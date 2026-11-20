# Recommandation financière (FAR-Trans, NLGCL + MPT)

Projet d'équipe : recommandation d'actifs par GNN (NLGCL), re-ranking selon la théorie moderne du portefeuille (MPT) et filtre de risque, avec profil et explications par LLM. Les documents de cadrage sont dans [docs/](docs/).

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.data.load_and_check   # nécessite dataset/FAR-Trans/*.csv (jamais commité)
pytest
```

## Propriétaires des dossiers

| Qui | Dossiers |
|---|---|
| Ethan (Project Lead) | `src/eval/`, `src/graph/`, `app/`, `README.md` |
| Alfred (Data Engineer) | `src/data/`, `src/storage/`, `src/api/routes_log.py` |
| Nicolas (Lead ML, Core) | `src/models/`, `src/rerank/` |
| Thomas (ML Ops) | `src/train/`, `src/serve/`, `src/llm/`, `src/api/main.py` |

## Contrats (formats échangés)

Tant qu'un module dont vous dépendez n'existe pas, codez contre une version factice qui respecte le même format.

| Qui produit | Quoi | Format |
|---|---|---|
| Alfred | Prix et risque | `dataset/processed/returns.parquet` : dates en lignes, ISIN en colonnes, rendements quotidiens. `asset_risk.parquet` : `ISIN, volatility, max_drawdown, risk_class` (1 à 7) |
| Alfred | Portefeuilles | `holdings(date) -> DataFrame[customerID, ISIN, units, value]` |
| Ethan | Split | `train / val / test` au format `[customerID, ISIN, timestamp]`, un achat par ligne (`src/eval/split.py`) |
| Ethan | Graphe | `edge_index`, `user2idx`, `item2idx` (`src/graph/build.py`), voir précision ci-dessous |
| Ethan | Évaluation | `evaluate(ranked: dict[customerID, list[ISIN]], test) -> {"ndcg@10", "recall@20", ...}` (`src/eval/metrics.py`) |
| Nicolas | Modèle | `NLGCL(n_users, n_items, dim)` avec `forward(edge_index) -> (user_emb, item_emb)` et `loss(users, pos, neg, edge_index)` |
| Nicolas | Re-ranking | `risk_filter(isins, asset_risk, ceiling) -> isins` et `mpt_rerank(isins, relevance, weights, mu, sigma, gamma, lam) -> isins` |
| Thomas | Prédiction | `predict(holdings: dict[ISIN, montant], profile, k=10) -> list[(ISIN, score)]` |
| Thomas | LLM | `build_profile(facts, free_text) -> Profile(risk_level, ceiling, gamma, gaps)` et `explain(facts) -> str` |
| Thomas / Ethan | API | `POST /recommend` avec `{holdings, answers, free_text}`, renvoie `{items: [{isin, name, score}], profile}` |

### Précision sur `edge_index`

Tenseur `torch.long` de forme `[2, E]` : ligne 0 = indice utilisateur (`user2idx`), ligne 1 = indice actif (`item2idx`). Les indices actifs ne sont **pas** décalés de `n_users`, et le graphe n'est **pas** symétrisé (une arête par couple utilisateur-actif distinct). Au modèle de construire la version symétrique ou décalée dont il a besoin.

## Règles de travail

- Une branche par PR (`alfred/holdings`), personne ne pousse sur `main`.
- PR petites, chacune avec au moins un test dans `tests/`.
- `requirements.txt` : une ligne à la fois, rebase sur `main` juste avant de merger.
- Le README appartient à Ethan : les autres écrivent leur section dans la description de leur PR.
- Ne jamais commiter les données (`dataset/` est dans le `.gitignore`).
