# Recommandation financière (FAR-Trans, NLGCL + MPT)

Projet d'équipe : recommandation d'actifs par GNN (NLGCL), re-ranking selon la théorie moderne du portefeuille (MPT) et filtre de risque, avec profil et explications par LLM. Les documents de cadrage sont dans [docs/](docs/).

## Reproduire l'expérience et lancer la démo

Depuis le dossier du dépôt, avec Python 3.11 ou plus récent :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.data.download
python -m src.data.load_and_check
python -m src.train.run
python -m pytest
```

Sous macOS ou Linux, activez l'environnement avec `source .venv/bin/activate`.
Le téléchargement FAR-Trans vient de l'[Université de Glasgow](https://doi.org/10.5525/gla.researchdata.1658) (CC BY 4.0).
Les données et les artefacts générés restent sous `dataset/`. Le run écrit
`loss.csv`, `metrics.json`, `checkpoint.pt`, `model.npz` et un snapshot financier
dans `dataset/experiment/`. Le graphe utilise uniquement les achats d'entraînement.
Le checkpoint est choisi sur la validation, puis les modèles et références sont
comparés sur les mêmes utilisateurs et le même catalogue de test.

Ouvrez deux terminaux avec l'environnement activé, puis lancez l'API et l'interface :

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

```bash
python -m streamlit run app/streamlit_app.py
```

Ouvrez l'adresse affichée par Streamlit (port 8501 par défaut). Le serveur charge
les embeddings du run et les tables financières datées au démarrage. Le catalogue
d'expérimentation est historique. La démo sert à observer les compromis du classement.

Sélectionnez un actif du catalogue et un montant, puis cliquez sur **Afficher les
suggestions**. Avec un portefeuille connu, l'API moyenne les embeddings des actifs
détenus en les pondérant par montant. Le questionnaire fixe le plafond de risque.
Quand les prix nécessaires sont disponibles, les candidats sont reclassés en
simulant une allocation de 10 % au nouvel actif. L'ordre de la réponse correspond
au classement final. Le champ `score` mesure la pertinence issue du modèle.
Les actions de la démo sont journalisées dans `dataset/interactions.sqlite3`.

### Vérification facultative du profil

Avec un modèle Ollama déjà lancé, définissez `RECSYS_OLLAMA_MODEL` avant de
démarrer l'API. Pour un serveur local compatible avec l'API Chat Completions,
définissez `RECSYS_OPENAI_COMPAT_URL` (URL complète du point d'accès) et
`RECSYS_PROFILE_MODEL`. L'écran propose alors la vérification du profil.
Les valeurs affichées restent validées par les règles du questionnaire. La
vérification LLM s'exécute à la demande, séparément de `/recommend`.

```bash
python -m src.eval.profile_benchmark
```

Ce test compare la première réponse du modèle et le profil vérifié sur neuf cas
synthétiques. Le [rapport Week 3](docs/Finance_Recommendation_Week3_Status_Report.pdf)
contient les mesures de l'expérience et de la démo.

## Données

[FAR-Trans](https://doi.org/10.5525/gla.researchdata.1658) (CC BY 4.0) : transactions réelles de clients particuliers d'une banque grecque, du 2 janvier 2018 au 30 novembre 2022. `python -m src.data.load_and_check` régénère ces chiffres dans `dataset/processed/stats.md`.

| Mesure | Valeur |
|---|---|
| Transactions (achats / ventes) | 388 048 (228 913 / 159 135) |
| Clients / actifs achetés / actifs cotés | 29 090 / 320 / 807 |
| Couples client-actif distincts (achats) | 89 884 |
| Densité de la matrice d'achats | 0,97 % |
| Actifs distincts achetés par client (médiane / moyenne) | 1 / 3,09 |
| Part des achats sur les 10 actifs les plus achetés | 48,2 % |

Une interaction est un **achat**. Les ventes servent seulement à reconstruire les portefeuilles.

**Seuils retenus**

| Étape | Règle |
|---|---|
| Filtrage clients / actifs | Aucun : tous les acheteurs sont gardés. Un filtre « 3 actifs par client » n'en laisserait que 8 842 sur 29 090 ; les clients avec peu d'actifs sont le cas démarrage à froid |
| Split temporel (`src/eval/split.py`) | 70 / 15 / 15 % des dates d'achat : train avant le 16/07/2021, validation jusqu'au 23/02/2022, test ensuite. Validation et test ne gardent que les nouveaux couples client-actif |
| Taille du split | Train 158 053 achats, 25 355 clients, 288 actifs. Test 6 134 achats, 3 455 clients, dont 1 035 absents du train |
| Portefeuilles (`src/data/holdings.py`) | Vente supérieure à la position connue : position ramenée à 0 (556 couples, parts achetées avant 2018). Le même jour, achats avant ventes. Transactions partagées (comptes joints probables) : gardées pour chaque co-titulaire |
| Prix (`src/data/asset_returns.py`) | Saut de plus de 50 % qui revient à ±20 % en 5 cotations : erreur de prix effacée (6 cas). Trous de 5 jours au plus comblés par le dernier prix |
| μ et Σ | μ : moyenne exponentielle des rendements (`span=60`), annualisée. Σ : 252 derniers jours, Ledoit-Wolf. Actifs avec au moins 60 rendements dans la fenêtre |
| Classes de risque 1 à 7 | Volatilité annualisée découpée selon l'échelle SRRI (0,5 / 2 / 5 / 10 / 15 / 25 %). Moins de 60 rendements : classe médiane de la sous-catégorie (28 actifs) |
| ETF PEA (`src/data/pea/`) | 19 ETF lus sur justETF (éligibilité PEA et cotation à Paris vérifiées), pays tels que publiés, classe de risque calculée sur la volatilité justETF |

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
