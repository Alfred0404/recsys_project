# Spread by Masdaq: financial recommendation (FAR-Trans, NLGCL + MPT)

Spread suggests to a retail investor the assets that complement their portfolio instead of duplicating it. A GNN (NLGCL) learns from real purchases which assets go together, a filter removes everything above the investor's risk ceiling, then a modern portfolio theory (MPT) re-ranking puts the assets that reduce variance first. A local LLM sets the profile from a free-text sentence and explains each suggestion, with verified figures. Educational tool, not investment advice.

The **[final report](docs/Finance_Recommendation_Final_Report.pdf)** (3 pages) summarizes the method and the results. The plan, the architecture and the progress reports are in [docs/](docs/).

**Team**: Ethan Petain (Project Lead), Alfred De Vulpian (Data Engineer), Nicolas Cottez-Abrate (Lead ML Engineer), Thomas Confolent (ML Engineer Ops).

## Quick start

Requirements: **Python 3.11 or newer** (python.org; tick "Add Python to PATH" on Windows) and an
internet connection for the first run (downloading the dependencies and the FAR-Trans dataset).
Git is not needed.

1. Unzip the `.zip` and open a terminal in the resulting folder (the one containing `run.sh`).
2. Install everything (environment, dependencies, data, model), about 5 to 6 min:

   | Windows | macOS / Linux |
   |---|---|
   | `install.bat` (double-click works) | `bash install.sh` |

3. Start the site:

   | Windows | macOS / Linux |
   |---|---|
   | `run.bat` (double-click works) | `bash run.sh` |

   The browser opens on http://127.0.0.1:8000. `Ctrl+C` stops the server.

If the `.zip` already contains `dataset/experiment/` (trained weights) and `dataset/processed/`
(prepared prices), as in the delivered archive, the install only creates the environment and
installs the dependencies: nothing is downloaded and the model is **not retrained**, so it takes
about 1 to 2 min. Delete `dataset/experiment/` to force a retraining.

Step 2 is optional: `run.bat` / `run.sh` perform the same installation if anything is missing,
then start the server. If [uv](https://docs.astral.sh/uv/) is installed, the scripts use it and
the dependencies install much faster.

The scripts create `.venv`, install the dependencies, download FAR-Trans, prepare the data
and train the served model if they are missing, then start the server.
They only train NLGCL (`--skip-ablation`): the demo does not need the LightGCN ablation.
Time measured on a Windows laptop: 6 min 24 s from clone to running server with the old full
procedure, including 1 min 29 s of training without the ablation. Later launches
start in a few seconds.

If something goes wrong: "Python not found" means Python 3.11+ is not installed or not on the
PATH; on Linux, `python3 -m venv` may require `sudo apt install python3-venv`.

## Reproduce the experiment and run the demo

Requires Python 3.11 or newer.

0. Go to the project folder (unzipped from the `.zip`, or cloned with
   `git clone https://github.com/Alfred0404/recsys_project.git`).

1. Create and activate the environment:

   | macOS / Linux | Windows (PowerShell) |
   |---|---|
   | `python3 -m venv .venv` | `python -m venv .venv` |
   | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |

2. Install, prepare the data and train (about 5 min on CPU):

   ```bash
   python -m pip install -r requirements.txt
   python -m src.data.download
   python -m src.data.load_and_check
   python -m src.train.run
   ```

   On Linux, first install the CPU build of torch, otherwise pip downloads the CUDA build
   (about 2.5 GB): `python -m pip install "torch>=2.2,<3" --index-url https://download.pytorch.org/whl/cpu`.
   `run.sh` does this automatically.

3. Start the server (see below) and open http://127.0.0.1:8000.

To run the tests, also install the test tools. The tests need neither the data nor the model.
The web pages test requires Node.js 18 or newer:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
node --test tests/test_asset_pages.cjs
```

The GitHub CI ([.github/workflows/tests.yml](.github/workflows/tests.yml)) runs these two commands on every PR.

The FAR-Trans download comes from the [University of Glasgow](https://doi.org/10.5525/gla.researchdata.1658) (CC BY 4.0).
Data and generated artifacts stay under `dataset/`. The run writes
`loss.csv`, `metrics.json`, `checkpoint.pt`, `model.npz` and a financial snapshot
in `dataset/experiment/`. The graph only uses training purchases.
The checkpoint is chosen on validation, then the models and baselines are
compared on the same users and the same test catalog.

Start the server with the environment activated:

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Select the held assets by name or ISIN and
adjust their amounts. Choose the questionnaire or the free-text profile.
In text mode, the first ranking uses a cautious profile. The
**Review text and refresh** button runs the analysis then recomputes the suggestions.
Open an asset page to see the available prices and request an explanation.
The charts use `dataset/processed/close_prices.parquet`, produced by
`load_and_check`. The site (`web/`) is served by the same API, with no build step
and no internet connection. To show it from another device on the same network,
start with `--host 0.0.0.0` and open `http://<machine IP>:8000`.

The server loads the run's embeddings and the dated financial tables at startup.
The experiment catalog is historical. The demo is for observing the trade-offs of the ranking.

With a known portfolio, the API averages the embeddings of the held assets,
weighted by amount. The questionnaire sets the risk ceiling.
When the required prices are available, the candidates are re-ranked by
simulating a 10 % allocation to the new asset. The order of the response
matches the final ranking. The `score` field measures the relevance coming from the model.
Demo actions are logged in `dataset/interactions.sqlite3`
(`python -m src.storage.export` exports them to CSV).

The **What if you added a PEA ETF?** section of the home page compares the country
exposure of a PEA ETF portfolio before and after adding an ETF (19 eligible ETFs, justETF
data). It does not depend on the model.

### Optional profile verification

With an Ollama model already running, set `RECSYS_OLLAMA_MODEL` before
starting the API. For a local server compatible with the Chat Completions API,
set `RECSYS_OPENAI_COMPAT_URL` (full endpoint URL) and
`RECSYS_PROFILE_MODEL`. The screen then offers the profile verification.
The displayed values remain validated by the questionnaire rules. The LLM
verification runs on demand, separately from `/recommend`.

```bash
python -m src.llm.profile_benchmark
```

This test compares the model's first answer and the verified profile on nine
synthetic cases. The [final report](docs/Finance_Recommendation_Final_Report.pdf)
contains the measurements of the experiment and of the demo.

## Architecture

```
FAR-Trans (CSV) ─► src/data : typed parquet, portfolios, μ, Σ, risk classes 1 to 7
                        │
                        ▼
      src/eval/split : 70/15/15 temporal split (purchases only)
                        │ train
                        ▼
      src/graph : bipartite client-asset graph ─► src/models : NLGCL (LightGCN + inter-layer contrast)
                                                        │ embeddings (model.npz)
                                                        ▼
questionnaire / text ─► src/llm : profile (ceiling, γ) ─► src/serve : embedding scores
                                                        ─► src/rerank : risk filter then MPT (λ)
                                                        │
                                                        ▼
                         src/api (FastAPI) ◄──► web/ (static site)  ─► dataset/interactions.sqlite3
```

**Endpoints** (`src/api/main.py`)

| Route | Role |
|---|---|
| `GET /health` | Server state and catalog size |
| `GET /assets` | Served catalog: ISIN, name, category, risk class, popularity rank |
| `POST /recommend` | `{holdings, answers, free_text, session_id}` → final ranking, profile, `recommendation_id`. Never calls the LLM |
| `POST /profile` | Profile verification by the local LLM, or by the rules if there is none; result cached for the session |
| `POST /explain` | Explanation of one asset of an already served recommendation, checked against the ranking's figures |
| `POST /log_interaction` | Logs an anonymous demo event in SQLite |
| `GET /prices?isins=…&years=3` | Weekly prices and change over the period |
| `GET /asset/{isin}` | Daily history and description of an asset |
| `GET /pea/etfs` | The 19 PEA-eligible ETFs of the exposure view |
| `POST /pea/exposure` | `{holdings, candidate, share}` → country exposure before and after the addition |

**Environment variables** (all optional)

| Variable | Default | Role |
|---|---|---|
| `RECSYS_MODEL_PATH` | `dataset/experiment/model.npz` | Served model |
| `RECSYS_FINANCE_DIR` | `dataset/experiment/finance` | μ, Σ, risk snapshot |
| `RECSYS_DATA_DIR` | `dataset/processed` | Prices shown on the asset pages |
| `RECSYS_DB_PATH` | `dataset/interactions.sqlite3` | Interaction log |
| `RECSYS_OLLAMA_MODEL` | none | Enables the LLM through Ollama |
| `RECSYS_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama address |
| `RECSYS_OPENAI_COMPAT_URL` | none | Enables the LLM through a Chat Completions compatible server (full URL) |
| `RECSYS_PROFILE_MODEL` | `local` | Model name sent to that server |

## Results

Mean ± standard deviation over five seeds (`python -m src.train.run --seeds 42 1 2 3 4`), on the
temporal test: 3,455 clients, 1,035 of them absent from train. The "targets under the ceiling" column keeps
only the 564 clients who bought at least one asset compatible with their ceiling. The per-cohort
detail is in `dataset/experiment-multi/metrics.json` (`dataset/experiment/metrics.json` for the
served run, seed 42).

| Ranking | NDCG@10 | Recall@20 | NDCG@10, targets under the ceiling | Top 10 above the ceiling |
|---|---|---|---|---|
| Random | 0.014 ± 0.001 | 0.048 ± 0.002 | 0.019 ± 0.004 | – |
| Most popular | 0.167 | 0.346 | 0.165 | – |
| LightGCN (ablation, no contrast) | 0.194 ± 0.002 | 0.395 ± 0.003 | 0.224 ± 0.004 | – |
| NLGCL | 0.192 ± 0.003 | 0.389 ± 0.002 | 0.220 ± 0.003 | 76.4 % |
| NLGCL + risk filter | 0.053 ± 0.001 | 0.100 ± 0.001 | 0.366 ± 0.005 | 0 % |
| NLGCL + filter + MPT (λ = 0.25), served | 0.051 ± 0.001 | 0.099 ± 0.001 | 0.356 ± 0.007 | 0 % |

- Both learned models clearly beat the baselines, with a gap between seeds much smaller than the gap with popularity.
- The risk filter makes the raw NDCG drop, because 80.8 % of the real test purchases exceed the buyer's ceiling. On the targets compatible with that ceiling, which is what suitable advice can recover, it is the best. MPT additionally reduces the simulated portfolio variance (−2.8·10⁻⁴ over 1,969 clients) for 4 % of NDCG.
- On the whole test set, the contrastive term of NLGCL does not beat the LightGCN ablation (difference within the noise). Tuning the weight and the temperature on validation (`python -m src.train.tune_nlgcl`) selects a weight of 0.01, but the gain is not found on test (0.192 ± 0.005). The contrast does help the 112 clients absent from the graph but with known assets: 0.206 ± 0.010 against 0.192 ± 0.007 for LightGCN, on every seed.
- Free-text profile on the 40 profiles written by the team (qwen2.5:7b): macro-F1 of 0.34 (rules), 0.56 (actor) and 0.74 (actor + reflection) in French; 0.11, 0.67 and 0.81 in English.

## Retrain the model and reproduce the results

`python -m src.train.run` retrains NLGCL and the LightGCN ablation (about 5 min on CPU), then writes the model served by the API. `--skip-ablation` only trains NLGCL (about 1 min 30 s), which is enough for the demo but removes the LightGCN row from the results. The following commands reread `dataset/experiment/model.npz` or rerun the experiment:

| Command | Result |
|---|---|
| `python -m src.train.run --seeds 42 1 2 3 4` | Same experiment on five seeds, mean and standard deviation in `dataset/experiment-multi/metrics.json`. Does not replace the served model |
| `python -m src.train.tune_nlgcl --contrastive-weights 0.01 0.05 0.2 --temperatures 0.1 0.2 0.5` | Chooses the contrast weight and temperature on **validation** only (`nlgcl_tuning/validation_grid.csv`, `selected.json`) |
| `python -m src.train.run --risk-tolerance 1` | Full run, plus the ablation of the tolerant filter (one class above the ceiling, penalized) |
| `python -m src.eval.tune` | Chooses λ and the μ shrinkage on **validation** (`tuning/validation_grid.csv`, `tuning/selected.json`). The selected values are the defaults of `src.train.run` |
| `python -m src.train.run --seeds 42 1 2` | Same run on 3 seeds, mean and standard deviation of each metric (`dataset/experiment-multi/metrics.json`): these are the figures of the Results section |
| `python -m src.train.tune_nlgcl --contrastive-weights 0.05 --temperatures 0.2` | Compares NLGCL and LightGCN on **validation** for a grid of contrast weights and temperatures (`nlgcl_tuning/`). Add `--epochs 30` to see again why the limit was raised to 80 |
| `python -m src.serve.benchmark_api` | Real latency of `/recommend` on the running server (2 s budget; `--check-deferred` also measures `/explain`) |
| `python -m src.eval.lambda_sweep` | Relevance / diversification curve on test for each λ (`lambda_sweep/`) |
| `python -m src.rerank.calibrate` | Implied γ of the real portfolios by risk level (`gamma_calibration.json`) |
| `python -m src.llm.evaluate_profiles` | Profile against the real `riskLevel` (local model required) |
| `python -m src.llm.text_benchmark --draft-suite` | Free-text trial on 40 cases (10 from Thomas and 30 synthetic drafts, local model required) |
| `python -m src.llm.explanation_benchmark` | Faithfulness of the explanations, LLM against template (local model required) |

To measure the team's contributions, pass the four JSON files to
`python -m src.llm.text_benchmark --require-team`. The command expects ten labeled
profiles per member and excludes the synthetic drafts.

The profiles are available in two versions, with the same `id`s and the same
levels: the original French (`src/llm/fixtures/<first name>_profiles.json`) and an
English translation (`src/llm/fixtures/en/<first name>_profiles.json`). **For an
English demo or report, use the files in `en/`**:

```bash
python -m src.llm.text_benchmark --require-team src/llm/fixtures/en/alfred_profiles.json src/llm/fixtures/en/ethan_profiles.json src/llm/fixtures/en/nicolas_profiles.json src/llm/fixtures/en/thomas_profiles.json
```

Compare the two runs to see the effect of the language. The safeguard for an
explicit refusal to lose capital exists in both languages, and the
other keyword rules favor French.
If you change a profile, update both versions: a test checks
that they keep the same `id`s and levels.

**Documented choices**

- **μ shrunk toward the mean (δ = 1)**. The 60-day expected return is too noisy: with raw μ, increasing λ degraded NDCG, diversity and variance all at once. With δ = 1, the MPT score only ranks by the variance added to the portfolio. λ = 0.25 and δ = 1 are chosen on validation (NDCG at least 95 % of the filter alone, then the largest variance drop).
- **γ stays a fixed grid** (4 / 3 / 2 / 1). The implied γ of real portfolios is negative at the median at every level and does not decrease with the declared level: the median portfolio volatility is 0.28 to 0.29 whatever the level. There is therefore nothing to calibrate reliably.
- **No portfolio volatility band filter**. 0 % of the "conservative" portfolios and 0.5 % of the "income" ones are already inside their band: such a filter would only keep assets that reduce risk, which the MPT re-ranker already favors.
- **Cold start**: mean of the embeddings of the held assets (weighted by amount in the demo), otherwise popularity filtered by the risk ceiling. Blending with popularity for clients with 2 assets or fewer does not improve validation: it is not kept.

## Data

[FAR-Trans](https://doi.org/10.5525/gla.researchdata.1658) (CC BY 4.0): real transactions of retail clients of a Greek bank, from 2 January 2018 to 30 November 2022. `python -m src.data.load_and_check` regenerates these figures in `dataset/processed/stats.md`.

| Measure | Value |
|---|---|
| Transactions (buys / sells) | 388,048 (228,913 / 159,135) |
| Clients / assets bought / assets listed | 29,090 / 320 / 807 |
| Distinct client-asset pairs (buys) | 89,884 |
| Density of the purchase matrix | 0.97 % |
| Distinct assets bought per client (median / mean) | 1 / 3.09 |
| Share of purchases on the 10 most bought assets | 48.2 % |

An interaction is a **purchase**. Sells are only used to rebuild the portfolios.

**Chosen thresholds**

| Step | Rule |
|---|---|
| Client / asset filtering | None: all buyers are kept. A "3 assets per client" filter would keep only 8,842 of 29,090; clients with few assets are the cold-start case |
| Temporal split (`src/eval/split.py`) | 70 / 15 / 15 % of purchase dates: train before 16/07/2021, validation until 23/02/2022, test after. Validation and test only keep new client-asset pairs |
| Split size | Train 158,053 purchases, 25,355 clients, 288 assets. Test 6,134 purchases, 3,455 clients, 1,035 of them absent from train |
| Portfolios (`src/data/holdings.py`) | Sell larger than the known position: position set to 0 (556 pairs, shares bought before 2018). Same day, buys before sells. Shared transactions (probable joint accounts): kept for each co-holder |
| Prices (`src/data/asset_returns.py`) | Jump of more than 50 % that returns to ±20 % within 5 quotes: price error erased (6 cases). Gaps of at most 5 days filled with the last price |
| μ and Σ | μ: exponential mean of returns (`span=60`), annualized, then shrunk toward the asset mean in the re-ranker (δ = 1, see above). Σ: last 252 days, Ledoit-Wolf. Assets with at least 60 returns in the window |
| Risk classes 1 to 7 | Annualized volatility cut according to the SRRI scale (0.5 / 2 / 5 / 10 / 15 / 25 %). Fewer than 60 returns: median class of the subcategory (28 assets) |
| PEA ETFs (`src/data/pea/`) | 19 ETFs read from justETF (PEA eligibility and Paris listing checked), countries as published, risk class computed on the justETF volatility |

## Folder owners

| Who | Folders |
|---|---|
| Ethan (Project Lead) | `src/eval/`, `src/graph/`, `README.md`, `.github/` |
| Alfred (Data Engineer) | `src/data/`, `src/storage/`, `/log_interaction` route of `src/api/main.py` |
| Nicolas (Lead ML, Core) | `src/models/`, `src/rerank/` |
| Thomas (ML Ops) | `src/train/`, `src/serve/`, `src/llm/`, `src/api/main.py` |
| The whole team | `web/` |

## Interfaces between modules

| Module | Interface |
|---|---|
| Split (`src/eval/split.py`) | `temporal_split(buys, t1, t2) -> (train, validation, test)`, each in the format `[customerID, ISIN, timestamp]`, one purchase per row; `check_no_leak` checks there is no leak |
| Graph (`src/graph/build.py`) | `build_graph(train) -> (edge_index, user2idx, item2idx)`, see the note below |
| Evaluation (`src/eval/metrics.py`) | `evaluate(ranked: dict[customerID, list[ISIN]], test) -> {"ndcg@10", "recall@20", ...}` |
| Model (`src/models/nlgcl.py`) | `NLGCL(n_users, n_items, dim, n_layers, contrastive_weight)` with `forward(edge_index) -> (user_emb, item_emb)` and `loss_parts(users, pos, neg, edge_index) -> (loss, bpr, contrastive)`; `contrastive_weight=0` gives the LightGCN ablation |
| Portfolios (`src/data/holdings.py`) | `holdings_at(tx, prices, before) -> DataFrame[customerID, ISIN, units, value]` |
| Prices and risk (`src/data/asset_returns.py`) | `expected_returns`, `covariance` (Ledoit-Wolf), `asset_risk -> DataFrame[ISIN, volatility, max_drawdown, risk_class, ...]` (classes 1 to 7) |
| Served snapshot (`dataset/experiment/finance/`) | `mu.parquet`, `sigma.parquet`, `asset_risk.parquet`, `assets.parquet`, written by `src.train.run` at the test cutoff date |
| Re-ranking (`src/rerank/mpt.py`) | `risk_filter(isins, asset_risk, ceiling) -> isins` and `mpt_rerank(isins, relevance, weights, mu, sigma, gamma, lam) -> isins` |
| Prediction (`src/serve/predict.py`) | `Recommender(model_path, finance_dir).predict(holdings: dict[ISIN, amount], profile, k=10) -> {items, ranking_source, unrecognized_isins}` |
| Profile and LLM (`src/llm/`) | `build_profile(holdings, answers) -> Profile(risk_level, ceiling, gamma, gaps, source)`, `review_profile(holdings, answers, free_text, generate)` and `explain_suggestion(facts, generate)` |

### Note on `edge_index`

`torch.long` tensor of shape `[2, E]`: row 0 = user index (`user2idx`), row 1 = asset index (`item2idx`). Asset indices are **not** shifted by `n_users`, and the graph is **not** symmetrized (one edge per distinct user-asset pair). It is up to the model to build the symmetric or shifted version it needs.

## Working rules

- One branch per PR (`alfred/holdings`), nobody pushes to `main`.
- Small PRs, each with at least one test in `tests/`. CI must be green before merging.
- `requirements.txt`: one line at a time, rebase on `main` right before merging.
- The README belongs to Ethan: the others write their section in their PR description.
- Never commit the data (`dataset/` is in the `.gitignore`).
