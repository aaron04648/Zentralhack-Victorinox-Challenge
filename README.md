# Zentralhack-Victorinox-Challenge

**Victorinox Product Match Agent** — a multimodal agent that identifies a photographed
product and recommends the best matching Victorinox alternative, with technical specs,
a rationale and a confidence score.

Hackathon 23.10.2026 — 24h sprint, live demo deadline end of the following day (late afternoon).

## Problem

The Victorinox assortment and the portfolios of direct competitors contain many visually
similar articles. Sales, customer service, product management and trading staff currently
have to identify a photographed product manually and then hunt down matching Victorinox
alternatives and technical specifications across different sources. This is especially
costly when a Victorinox product is discontinued, or when a competitor product should be
replaced by the closest possible Victorinox equivalent.

Existing cross-reference tables between competitor and Victorinox products already exist
in part — in Commercial Cutlery alone the range covers several hundred SKUs — but there is
no integrated solution that connects photo recognition, technical product data and
rule-based alternative lookup.

## Goal / End Product

A mobile-capable web app for the hackathon prototype:

1. Capture or upload a product photo.
2. Automatically recognise the product (category, brand, and where possible the concrete
   model / SKU).
3. Show a prioritised Victorinox recommendation within a few seconds.

The result view contains: product image, article number, product name, availability /
status, key technical features, a comparison against the detected source product, the
rationale for the recommendation, and a confidence value. A simple feedback function
("correct / not correct" plus picking a better hit) supports continuous improvement.

The prototype must work end-to-end for **one clearly delimited product category**.

### Scope of this prototype

- **In scope:** **pocket knives** from the SAK (Swiss Army Knife) category only.
  The catalogue CSV also contains accessories, nail care, Swiss Cards, fixed-blade knives
  (Venture) and Swiss Tools (pliers); these are filtered out by `is_pocket_knife()` in
  `backend/app/main.py`, leaving **153 of 247** products. New backend code should read the
  catalogue via `load_pocket_knives()`.
- **Competitor brands considered:** Swiss Army Knife (own), Swiza, Roxon, The Helton,
  Leatherman, Gerber Gear, Benchmade Knives.
- **Reference example:** SWIZA D03 AM (Black), SKU `KNI.0036.1010` — used as the
  worked example from the client's introduction deck.

### Out of scope for the prototype

- Product categories other than SAK, and SAK products that are not pocket knives
  (accessories, nail care, Swiss Cards, Swiss Tools, fixed-blade knives).
- Training or fine-tuning of models.
- Production integration with Victorinox PIM / ERP / DAM / Microsoft Fabric Lakehouse.
- Any live write-back into customer systems; feedback is captured locally for the
  prototype only.

## Architecture

Modular, API-based and model-independent, as requested by the challenge. The pipeline is
split into stages that are independently testable:

| Stage | Responsibility |
| --- | --- |
| **Vision** | Object/product detection, brand and model recognition, OCR (e.g. visible article number) |
| **Product Data Agent** | Controlled access to released product master data (article no., name, category, technical features, availability / lifecycle status, images) |
| **Embedding / Vector Index** | Image and text embeddings with top-k similarity search over the SAK catalogue |
| **Recommendation Agent** | Weighted matching over technical features, availability, successor relations and cross-reference rules |
| **Orchestrator** | Routing, result assembly and clarification questions |

### Technology

- **Backend:** Python. **Frontend:** React.
- **Vision / LLM:** provider-agnostic, called through an OpenAI-compatible API
  (Azure OpenAI, OpenAI, Ollama, …). Model choice is configuration, not code.
- **Embeddings + vector search:** local embeddings (`fastembed`, CLIP/SigLIP image
  embeddings) with a local vector store. Kept swappable for Azure AI Search.
- **API:** REST/HTTP service between frontend and the agent workflow.

### Matching and confidence

A recommendation is produced by weighted scoring over these dimensions:

- image similarity (embedding cosine distance)
- physical dimensions
- functions / tool set
- blade and lock type
- availability / lifecycle status
- explicit cross-reference and successor rules

The result carries a similarity / confidence value. Low separation between the top
candidates must not be hidden — in that case the app shows several candidates and asks
for a further photo, a visible article number, or a distinguishing feature rather than
guessing. No specification may ever be invented; all technical data is sourced from the
catalogue.

## Data

Required for the SAK category: article numbers, names, categories, technical features,
availability / lifecycle status, product images, and — where available — the existing
cross-reference tables for competitor products.

**Status: in progress.** A quality-checked export or read-only interface for the SAK
category is being prepared by Aaron (data processing).

The scraped catalogue now lives in `backend/data/`:
`victorinox_sak_produkte.csv` (247 SAK products: article number, name, categories,
price, stock status, colours, tool list, product URL, image URL) and
`victorinox_sak_werkzeuge.csv` (1,936 rows mapping each article number to its
individual tools).

Additionally, the hackathon input PDF (`infos_zentral_hack_regional_impact/Input
Hackathon_Victorinox.pdf`) contains 12 product photos with sticky-note ground-truth
labels by the client. These have been extracted to `data/sak_ground_truth/` and are
used as the evaluation set for the classification workstream — see
[docs/classification_recommendation.md](docs/classification_recommendation.md).

## Success criteria

For the defined test catalogue:

- a high share of correct products in the **top-3** hits
- a technically plausible best alternative product
- complete, source-based technical data
- transparent confidence, no invented specifications

The expected result is a convincing live demo with real smartphone photos and traceable
recommendations — not a plain chatbot.

## Project Management

- Team members: Philipp, Aaron, Admir, Simon
- work items:
    - Aaron: data processing
    - classification
        - Philipp: embeddings
        - Simon: jev
    - Claude: app

# API Endpoints 
POST /api/products/image

{ "Everyday": true, "Personalisieren": true }
{
  "anzahl": 28,
  "bild_url": "https://...",
  "treffer": [
    { "artikelnummer": "0.6223.G", "name": "Classic SD", "bild_url": "https://..." },
    ...
  ]
}

GET  /api/products?q=&kategorie=&limit=&offset=   pocket-knife search (used by the feedback dialog)
GET  /api/products/{artikelnummer}                 single pocket knife incl. tool list (variant numbers resolve too)
POST /api/match                                    photo → recognition + recommendations (open, mocked in frontend)
POST /api/feedback                                 correct / not correct + better hit (open, mocked in frontend)

Full request/response contract: [docs/api.md](docs/api.md).

## Frontend

Mobile-first React app in `frontend/` (Vite, JSX, Tailwind CSS v4, lucide-react, framer-motion, react-router).

Flow: **Scan** (camera / upload / demo examples) → **Preview** (check the photo, optional category)
→ **Analyse** (agent steps live) → **Result** (recognised product with Victorinox/competitor badge and
confidence, top recommendation with rationale, technical comparison with sources, top-3 candidates,
clarification prompt when unsure, feedback bar) → **Product detail**.

### Category hint

After choosing a photo the user can optionally pick a category. It is sent to `POST /api/match` as the
form field `kategorie` and is meant to narrow the candidate set (the "category" filter in the
classification pipeline, see `docs/classification_recommendation.md` §8). The values are exactly the
pocket-knife values of the CSV column `kategorien`:

| Value (`kategorie`) | Label in the app | Typical models | Knives |
| --- | --- | --- | --- |
| *(empty)* | Automatisch erkennen | — | 153 |
| `Everyday` | Alltag (Everyday) | Classic SD, Spartan, Climber | 79 |
| `Outdoor & Sports` | Outdoor & Sport | Huntsman, Ranger Grip, Hunter Pro | 51 |
| `Trades & Crafts` | Handwerk & Garten | Swiss Champ, Handyman, Okuliermesser | 30 |

Products can be in several categories. The hint is a soft filter: if the recognition is very
confident about a product outside the chosen category, it should still win. The options live in
`frontend/src/lib/kategorien.js`. On a follow-up photo after a clarification prompt, the category of the
first photo is reused.

### Mock

As long as `/api/match` and `/api/feedback` do not exist, the frontend falls back to a mock
(`frontend/src/api/mock.js`). Its products and tool lists are real catalogue rows; what was supposedly
recognised on the photo is fixed per demo example and labelled "Bilderkennung (Demo)".
Mock results show a "Demo-Modus" badge. `VITE_USE_MOCK=true|false|auto` (default `auto`) controls this.

```bash
docker compose up --build -V   # -V renews the node_modules volume after dependency changes
# or locally:
cd frontend && npm install && npm run dev   # http://localhost:3000, proxies /api to :8000
```

## Repository Layout

```
docs/                                Challenge briefing and client documents
  classification_recommendation.md   Classification workstream: research + recommendation
  api.md                             Backend API contract
infos_zentral_hack_regional_impact/  Original client files (Fragebogen, intro deck, input PDF)
backend/                             FastAPI service + catalogue scraper
  app/main.py                        API endpoints
  scraper/victorinox.py              Catalogue scraper
  data/                              Scraped SAK catalogue (products + per-SKU tools)
frontend/                            React app (Vite, Tailwind)
data/sak_ground_truth/               12 labelled product photos extracted from the input PDF
tools/                               Classification workstream: Clef client + evaluation harnesses
  clef_client.py                     Clef decision client (OpenRouter /api/alpha/decisions)
  eval_clef.py                       Clef decision experiments
  eval_retrieval.py                  Embedding retrieval baselines
main.py                              Entry point
embeddings.py                        Embedding pipeline (in progress)
pyproject.toml                       Python project definition
```

## Classification (Simon: jev)

The classification approach is documented in
[docs/classification_recommendation.md](docs/classification_recommendation.md).

Summary of what was measured on the 12 labelled photos in `data/sak_ground_truth/`:

- **Off-the-shelf image embeddings do not work here.** CLIP, SigLIP2, UniCom, nomic and
  resnet50 all produce a *negative* within-class vs between-class similarity gap —
  worse than chance at telling SAK variants apart. Best top-1 was **2/12**.
- **[Cloudflare Clef](https://huggingface.co/Cloudflare/clef)** (Apache-2.0,
  multimodal, Jev/SystemOne-compatible) does work: **top-3 = 11/12 (92%)**, which
  meets the success criterion above, at ~$0.00003 per decision.
- It is reachable on OpenRouter at `POST /api/alpha/decisions` — **not**
  `/chat/completions`, and it is **not** listed in the model catalogue.

```bash
uv run python tools/eval_retrieval.py     # embedding baselines
uv run python tools/eval_clef.py          # Clef decision experiments
```

`tools/clef_client.py` is the decision client. `OPENROUTER_API_KEY` goes in `.env`
(see `.env.example`).

## Getting Started

```bash
uv sync        # install dependencies
uv run main.py # run the project
```

The backend and frontend run via Docker:

```bash
docker compose up --build -V
```

## References

- `docs/challenge_fragebogen.md` — challenge briefing (client questionnaire, plain-text extract)
- `infos_zentral_hack_regional_impact/` — original client documents: challenge questionnaire
  (docx), introduction deck for the SAK use case (pptx), hackathon input (pdf)
