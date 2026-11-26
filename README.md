# Spread by Masdaq : recommandation financière (FAR-Trans, NLGCL + MPT)

Spread propose à un investisseur particulier les actifs qui complètent son portefeuille au lieu de le dupliquer : un GNN (NLGCL) apprend sur de vrais achats quels actifs vont ensemble, un filtre retire tout ce qui dépasse le plafond de risque de l'investisseur, puis un re-ranking selon la théorie moderne du portefeuille (MPT) place en tête les actifs qui réduisent la variance. Un LLM local fixe le profil à partir d'une phrase libre et explique chaque suggestion, chiffres vérifiés. Outil pédagogique, pas un conseil en investissement.

Le **[rapport final](docs/Finance_Recommendation_Final_Report.pdf)** (3 pages) résume la méthode et les résultats. Le plan, l'architecture et les rapports d'étape sont dans [docs/](docs/).

**Équipe** : Ethan Petain (Project Lead), Alfred De Vulpian (Data Engineer), Nicolas Cottez-Abrate (Lead ML Engineer), Thomas Confolent (ML Engineer Ops).

## Lancement rapide

Avec Python 3.11 ou plus récent et Git installés :

```bash
git clone https://github.com/Alfred0404/recsys_project.git
cd recsys_project
run.bat        # Windows (double-clic possible)
./run.sh       # macOS / Linux
```

Le script crée `.venv`, installe les dépendances, télécharge FAR-Trans, prépare les données
et entraîne le modèle servi s'ils manquent, puis lance le serveur et ouvre http://127.0.0.1:8000.
Il entraîne seulement NLGCL (`--skip-ablation`) : la démo n'a pas besoin de l'ablation LightGCN.
Temps mesuré sur un portable sous Windows : 6 min 24 s du clone au serveur lancé avec l'ancienne
procédure complète, dont 1 min 29 s d'entraînement sans l'ablation. Les lancements suivants
démarrent en quelques secondes. `Ctrl+C` arrête le serveur.

## Reproduire l'expérience et lancer la démo

Avec Python 3.11 ou plus récent.

0. Clonez le dépôt : `git clone https://github.com/Alfred0404/recsys_project.git` puis `cd recsys_project`.

1. Créez et activez l'environnement :

   | macOS / Linux | Windows (PowerShell) |
   |---|---|
   | `python3 -m venv .venv` | `python -m venv .venv` |
   | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |

2. Installez, préparez les données et entraînez (environ 5 min sur CPU) :

   ```bash
   python -m pip install -r requirements.txt
   python -m src.data.download
   python -m src.data.load_and_check
   python -m src.train.run
   ```

3. Lancez le serveur (voir plus bas) et ouvrez http://127.0.0.1:8000.

Pour lancer les tests, installez aussi les outils de test. Les tests n'ont besoin ni des
données ni du modèle. Le test des pages web demande Node.js 18 ou plus récent :

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
node --test tests/test_asset_pages.cjs
```

La CI GitHub ([.github/workflows/tests.yml](.github/workflows/tests.yml)) lance ces deux commandes sur chaque PR.

Le téléchargement FAR-Trans vient de l'[Université de Glasgow](https://doi.org/10.5525/gla.researchdata.1658) (CC BY 4.0).
Les données et les artefacts générés restent sous `dataset/`. Le run écrit
`loss.csv`, `metrics.json`, `checkpoint.pt`, `model.npz` et un snapshot financier
dans `dataset/experiment/`. Le graphe utilise uniquement les achats d'entraînement.
Le checkpoint est choisi sur la validation, puis les modèles et références sont
comparés sur les mêmes utilisateurs et le même catalogue de test.

Lancez le serveur avec l'environnement activé :

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Ouvrez http://127.0.0.1:8000. Sélectionnez les actifs détenus par nom ou ISIN et
ajustez leurs montants. Choisissez le questionnaire ou le profil en texte libre.
En mode texte, le premier classement utilise un profil prudent. Le bouton
**Analyser le texte et actualiser** lance l'analyse puis recalcule les suggestions.
Ouvrez une fiche pour consulter les cours disponibles et demander une explication.
Les courbes utilisent `dataset/processed/close_prices.parquet`, produit par
`load_and_check`. Le site (`web/`) est servi par la même API, sans étape de
build ni connexion internet. Pour la montrer depuis un autre appareil du même réseau,
lancez avec `--host 0.0.0.0` et ouvrez `http://<IP de la machine>:8000`.

Le serveur charge les embeddings du run et les tables financières datées au démarrage.
Le catalogue d'expérimentation est historique. La démo sert à observer les compromis du classement.

Avec un portefeuille connu, l'API moyenne les embeddings des actifs
détenus en les pondérant par montant. Le questionnaire fixe le plafond de risque.
Quand les prix nécessaires sont disponibles, les candidats sont reclassés en
simulant une allocation de 10 % au nouvel actif. L'ordre de la réponse correspond
au classement final. Le champ `score` mesure la pertinence issue du modèle.
Les actions de la démo sont journalisées dans `dataset/interactions.sqlite3`
(`python -m src.storage.export` les exporte en CSV).

La section **Et si vous ajoutiez un ETF PEA ?** de la page d'accueil compare l'exposition
par pays d'un portefeuille d'ETF PEA avant et après l'ajout d'un ETF (19 ETF éligibles, données
justETF). Elle ne dépend pas du modèle.

### Vérification facultative du profil

Avec un modèle Ollama déjà lancé, définissez `RECSYS_OLLAMA_MODEL` avant de
démarrer l'API. Pour un serveur local compatible avec l'API Chat Completions,
définissez `RECSYS_OPENAI_COMPAT_URL` (URL complète du point d'accès) et
`RECSYS_PROFILE_MODEL`. L'écran propose alors la vérification du profil.
Les valeurs affichées restent validées par les règles du questionnaire. La
vérification LLM s'exécute à la demande, séparément de `/recommend`.

```bash
python -m src.llm.profile_benchmark
```

Ce test compare la première réponse du modèle et le profil vérifié sur neuf cas
synthétiques. Le [rapport final](docs/Finance_Recommendation_Final_Report.pdf)
contient les mesures de l'expérience et de la démo.

## Architecture

```
FAR-Trans (CSV) ─► src/data : parquet typés, portefeuilles, μ, Σ, classes de risque 1 à 7
                        │
                        ▼
      src/eval/split : split temporel 70/15/15 (achats seulement)
                        │ train
                        ▼
      src/graph : graphe biparti client-actif ─► src/models : NLGCL (LightGCN + contraste entre couches)
                                                        │ embeddings (model.npz)
                                                        ▼
questionnaire / texte ─► src/llm : profil (plafond, γ) ─► src/serve : score des embeddings
                                                        ─► src/rerank : filtre de risque puis MPT (λ)
                                                        │
                                                        ▼
                         src/api (FastAPI) ◄──► web/ (site statique)  ─► dataset/interactions.sqlite3
```

**Endpoints** (`src/api/main.py`)

| Route | Rôle |
|---|---|
| `GET /health` | État du serveur et taille du catalogue |
| `GET /assets` | Catalogue servi : ISIN, nom, catégorie, classe de risque, rang de popularité |
| `POST /recommend` | `{holdings, answers, free_text, session_id}` → classement final, profil, `recommendation_id`. N'appelle jamais le LLM |
| `POST /profile` | Vérification du profil par le LLM local, ou par les règles s'il n'y en a pas ; résultat mis en cache pour la session |
| `POST /explain` | Explication d'un actif d'une recommandation déjà servie, vérifiée contre les chiffres du classement |
| `POST /log_interaction` | Journalise un événement anonyme de la démo dans SQLite |
| `GET /prices?isins=…&years=3` | Cours hebdomadaires et variation sur la période |
| `GET /asset/{isin}` | Historique quotidien et description d'un actif |
| `GET /pea/etfs` | Les 19 ETF éligibles au PEA de la vue d'exposition |
| `POST /pea/exposure` | `{holdings, candidate, share}` → exposition par pays avant et après l'ajout |

**Variables d'environnement** (toutes facultatives)

| Variable | Défaut | Rôle |
|---|---|---|
| `RECSYS_MODEL_PATH` | `dataset/experiment/model.npz` | Modèle servi |
| `RECSYS_FINANCE_DIR` | `dataset/experiment/finance` | Snapshot μ, Σ, risque |
| `RECSYS_DATA_DIR` | `dataset/processed` | Cours affichés sur les fiches |
| `RECSYS_DB_PATH` | `dataset/interactions.sqlite3` | Journal des interactions |
| `RECSYS_OLLAMA_MODEL` | aucun | Active le LLM via Ollama |
| `RECSYS_OLLAMA_URL` | `http://127.0.0.1:11434` | Adresse d'Ollama |
| `RECSYS_OPENAI_COMPAT_URL` | aucun | Active le LLM via un serveur compatible Chat Completions (URL complète) |
| `RECSYS_PROFILE_MODEL` | `local` | Nom du modèle envoyé à ce serveur |

## Résultats

Moyenne ± écart-type sur cinq graines (`python -m src.train.run --seeds 42 1 2 3 4`), sur le test
temporel : 3 455 clients, dont 1 035 absents du train. La colonne « cibles sous le plafond » ne garde
que les 564 clients qui ont acheté au moins un actif compatible avec leur plafond. Le détail par
cohorte est dans `dataset/experiment-multi/metrics.json` (`dataset/experiment/metrics.json` pour le
run servi, graine 42).

| Classement | NDCG@10 | Recall@20 | NDCG@10, cibles sous le plafond | Top 10 au-dessus du plafond |
|---|---|---|---|---|
| Aléatoire | 0,014 ± 0,001 | 0,048 ± 0,002 | 0,019 ± 0,004 | – |
| Les plus populaires | 0,167 | 0,346 | 0,165 | – |
| LightGCN (ablation, sans contraste) | 0,194 ± 0,002 | 0,395 ± 0,003 | 0,224 ± 0,004 | – |
| NLGCL | 0,192 ± 0,003 | 0,389 ± 0,002 | 0,220 ± 0,003 | 76,4 % |
| NLGCL + filtre de risque | 0,053 ± 0,001 | 0,100 ± 0,001 | 0,366 ± 0,005 | 0 % |
| NLGCL + filtre + MPT (λ = 0,25), servi | 0,051 ± 0,001 | 0,099 ± 0,001 | 0,356 ± 0,007 | 0 % |

- Les deux modèles appris battent nettement les références, avec un écart entre graines bien plus petit que l'écart avec la popularité.
- Le filtre de risque fait chuter le NDCG brut, parce que 80,8 % des achats réels du test dépassent le plafond de l'acheteur. Sur les cibles compatibles avec ce plafond, ce qu'un conseil adapté peut retrouver, il est le meilleur. Le MPT réduit en plus la variance simulée du portefeuille (−2,8·10⁻⁴ sur 1 969 clients) pour 4 % de NDCG.
- Sur l'ensemble du test, le terme contrastif de NLGCL ne gagne pas sur l'ablation LightGCN (écart dans le bruit). Le réglage du poids et de la température sur la validation (`python -m src.train.tune_nlgcl`) choisit un poids de 0,01, mais le gain ne se retrouve pas sur le test (0,192 ± 0,005). Le contraste aide en revanche les 112 clients absents du graphe mais avec des actifs connus : 0,206 ± 0,010 contre 0,192 ± 0,007 pour LightGCN, sur chaque graine.
- Profil en texte libre sur les 40 profils écrits par l'équipe (qwen2.5:7b) : macro-F1 de 0,34 (règles), 0,56 (actor) et 0,74 (actor + réflexion) en français ; 0,11, 0,67 et 0,81 en anglais.

## Réentraîner le modèle et reproduire les résultats

`python -m src.train.run` réentraîne NLGCL et l'ablation LightGCN (environ 5 min sur CPU), puis écrit le modèle servi par l'API. `--skip-ablation` n'entraîne que NLGCL (environ 1 min 30 s), ce qui suffit pour la démo mais retire la ligne LightGCN des résultats. Les commandes suivantes relisent `dataset/experiment/model.npz` ou relancent l'expérience :

| Commande | Résultat |
|---|---|
| `python -m src.train.run --seeds 42 1 2 3 4` | Même expérience sur cinq graines, moyenne et écart-type dans `dataset/experiment-multi/metrics.json`. Ne remplace pas le modèle servi |
| `python -m src.train.tune_nlgcl --contrastive-weights 0.01 0.05 0.2 --temperatures 0.1 0.2 0.5` | Choisit le poids et la température du contraste sur la **validation** seulement (`nlgcl_tuning/validation_grid.csv`, `selected.json`) |
| `python -m src.train.run --risk-tolerance 1` | Run complet, avec en plus l'ablation du filtre tolérant (une classe au-dessus du plafond, pénalisée) |
| `python -m src.eval.tune` | Choisit λ et le rétrécissement de μ sur la **validation** (`tuning/validation_grid.csv`, `tuning/selected.json`). Les valeurs retenues sont les défauts de `src.train.run` |
| `python -m src.eval.lambda_sweep` | Courbe pertinence / diversification sur le test pour chaque λ (`lambda_sweep/`) |
| `python -m src.rerank.calibrate` | γ implicite des portefeuilles réels par niveau de risque (`gamma_calibration.json`) |
| `python -m src.llm.evaluate_profiles` | Profil contre les vrais `riskLevel` (modèle local requis) |
| `python -m src.llm.text_benchmark --draft-suite` | Essai du texte libre sur 40 cas (10 Thomas et 30 brouillons synthétiques, modèle local requis) |
| `python -m src.llm.explanation_benchmark` | Fidélité des explications, LLM contre gabarit (modèle local requis) |

Pour mesurer les contributions de l'équipe, passez les quatre fichiers JSON à
`python -m src.llm.text_benchmark --require-team`. La commande attend dix profils
étiquetés par membre et exclut les brouillons synthétiques.

Les profils sont disponibles en deux versions, avec les mêmes `id` et les mêmes
niveaux : le français d'origine (`src/llm/fixtures/<prénom>_profiles.json`) et une
traduction anglaise (`src/llm/fixtures/en/<prénom>_profiles.json`). **Pour une
démo ou un rapport en anglais, utilisez les fichiers de `en/`** :

```bash
python -m src.llm.text_benchmark --require-team src/llm/fixtures/en/alfred_profiles.json src/llm/fixtures/en/ethan_profiles.json src/llm/fixtures/en/nicolas_profiles.json src/llm/fixtures/en/thomas_profiles.json
```

Comparez les deux runs pour voir l'effet de la langue. Le garde-fou pour un
refus explicite de perdre du capital existe dans les deux langues, et les
autres règles par mots-clés privilégient le français.
Si vous modifiez un profil, mettez à jour les deux versions : un test vérifie
qu'elles gardent les mêmes `id` et niveaux.

**Choix documentés**

- **μ rétréci vers la moyenne (δ = 1)**. Le rendement attendu sur 60 jours est trop bruité : avec μ brut, augmenter λ dégradait à la fois le NDCG, la diversité et la variance. Avec δ = 1, le score MPT ne classe plus que par la variance ajoutée au portefeuille. λ = 0,25 et δ = 1 sont choisis sur la validation (NDCG au moins égal à 95 % du filtre seul, puis plus forte baisse de variance).
- **γ reste une grille fixe** (4 / 3 / 2 / 1). Le γ implicite des portefeuilles réels est négatif en médiane à tous les niveaux et ne décroît pas avec le niveau déclaré : la volatilité médiane des portefeuilles est de 0,28 à 0,29 quel que soit le niveau. Il n'y a donc rien à calibrer de façon fiable.
- **Pas de filtre de bande de volatilité du portefeuille**. 0 % des portefeuilles « conservative » et 0,5 % des « income » sont déjà dans leur bande : un tel filtre ne laisserait que des actifs qui réduisent le risque, ce que le re-ranker MPT favorise déjà.
- **Démarrage à froid** : moyenne des embeddings des actifs détenus (pondérée par montant à la démo), sinon popularité filtrée par le plafond de risque. Un mélange avec la popularité pour les clients à 2 actifs ou moins n'améliore pas la validation : il n'est pas retenu.

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
| μ et Σ | μ : moyenne exponentielle des rendements (`span=60`), annualisée, puis rétrécie vers la moyenne des actifs dans le re-ranker (δ = 1, voir plus haut). Σ : 252 derniers jours, Ledoit-Wolf. Actifs avec au moins 60 rendements dans la fenêtre |
| Classes de risque 1 à 7 | Volatilité annualisée découpée selon l'échelle SRRI (0,5 / 2 / 5 / 10 / 15 / 25 %). Moins de 60 rendements : classe médiane de la sous-catégorie (28 actifs) |
| ETF PEA (`src/data/pea/`) | 19 ETF lus sur justETF (éligibilité PEA et cotation à Paris vérifiées), pays tels que publiés, classe de risque calculée sur la volatilité justETF |

## Propriétaires des dossiers

| Qui | Dossiers |
|---|---|
| Ethan (Project Lead) | `src/eval/`, `src/graph/`, `README.md`, `.github/` |
| Alfred (Data Engineer) | `src/data/`, `src/storage/`, route `/log_interaction` de `src/api/main.py` |
| Nicolas (Lead ML, Core) | `src/models/`, `src/rerank/` |
| Thomas (ML Ops) | `src/train/`, `src/serve/`, `src/llm/`, `src/api/main.py` |
| Toute l'équipe | `web/` |

## Interfaces entre modules

| Module | Interface |
|---|---|
| Split (`src/eval/split.py`) | `temporal_split(buys, t1, t2) -> (train, validation, test)`, chacun au format `[customerID, ISIN, timestamp]`, un achat par ligne ; `check_no_leak` vérifie l'absence de fuite |
| Graphe (`src/graph/build.py`) | `build_graph(train) -> (edge_index, user2idx, item2idx)`, voir précision ci-dessous |
| Évaluation (`src/eval/metrics.py`) | `evaluate(ranked: dict[customerID, list[ISIN]], test) -> {"ndcg@10", "recall@20", ...}` |
| Modèle (`src/models/nlgcl.py`) | `NLGCL(n_users, n_items, dim, n_layers, contrastive_weight)` avec `forward(edge_index) -> (user_emb, item_emb)` et `loss_parts(users, pos, neg, edge_index) -> (loss, bpr, contrastive)` ; `contrastive_weight=0` donne l'ablation LightGCN |
| Portefeuilles (`src/data/holdings.py`) | `holdings_at(tx, prices, before) -> DataFrame[customerID, ISIN, units, value]` |
| Prix et risque (`src/data/asset_returns.py`) | `expected_returns`, `covariance` (Ledoit-Wolf), `asset_risk -> DataFrame[ISIN, volatility, max_drawdown, risk_class, ...]` (classes 1 à 7) |
| Snapshot servi (`dataset/experiment/finance/`) | `mu.parquet`, `sigma.parquet`, `asset_risk.parquet`, `assets.parquet`, écrits par `src.train.run` à la date de coupure du test |
| Re-ranking (`src/rerank/mpt.py`) | `risk_filter(isins, asset_risk, ceiling) -> isins` et `mpt_rerank(isins, relevance, weights, mu, sigma, gamma, lam) -> isins` |
| Prédiction (`src/serve/predict.py`) | `Recommender(model_path, finance_dir).predict(holdings: dict[ISIN, montant], profile, k=10) -> {items, ranking_source, unrecognized_isins}` |
| Profil et LLM (`src/llm/`) | `build_profile(holdings, answers) -> Profile(risk_level, ceiling, gamma, gaps, source)`, `review_profile(holdings, answers, free_text, generate)` et `explain_suggestion(facts, generate)` |

### Précision sur `edge_index`

Tenseur `torch.long` de forme `[2, E]` : ligne 0 = indice utilisateur (`user2idx`), ligne 1 = indice actif (`item2idx`). Les indices actifs ne sont **pas** décalés de `n_users`, et le graphe n'est **pas** symétrisé (une arête par couple utilisateur-actif distinct). Au modèle de construire la version symétrique ou décalée dont il a besoin.

## Règles de travail

- Une branche par PR (`alfred/holdings`), personne ne pousse sur `main`.
- PR petites, chacune avec au moins un test dans `tests/`. La CI doit être verte avant de merger.
- `requirements.txt` : une ligne à la fois, rebase sur `main` juste avant de merger.
- Le README appartient à Ethan : les autres écrivent leur section dans la description de leur PR.
- Ne jamais commiter les données (`dataset/` est dans le `.gitignore`).
