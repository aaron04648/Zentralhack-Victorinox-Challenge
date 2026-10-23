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

- **In scope:** the **SAK (Swiss Army Knife)** category only.
- **Competitor brands considered:** Swiss Army Knife (own), Swiza, Roxon, The Helton,
  Leatherman, Gerber Gear, Benchmade Knives.
- **Reference example:** SWIZA D03 AM (Black), SKU `KNI.0036.1010` — used as the
  worked example from the client's introduction deck.

### Out of scope for the prototype

- Product categories other than SAK.
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

## Repository Layout

```
docs/                              Challenge briefing and client documents
infos_zentral_hack_regional_impact/  Original client files (Fragebogen, intro deck, input PDF)
main.py                            Entry point
embeddings.py                      Embedding pipeline (in progress)
pyproject.toml                     Python project definition
```

## Getting Started

```bash
uv sync        # install dependencies
uv run main.py # run the project
```

## References

- `docs/challenge_fragebogen.md` — challenge briefing (client questionnaire, plain-text extract)
- `infos_zentral_hack_regional_impact/` — original client documents: challenge questionnaire
  (docx), introduction deck for the SAK use case (pptx), hackathon input (pdf)
