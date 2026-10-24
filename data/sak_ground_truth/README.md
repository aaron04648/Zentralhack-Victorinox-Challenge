# SAK ground-truth set (12 photos)

Extracted from `infos_zentral_hack_regional_impact/Input Hackathon_Victorinox.pdf`.

The client PDF contains 3 slides with product photos and 12 sticky-note annotations
authored by `sven.goldinger`. Each annotation is a ground-truth label placed on one
photo. This directory contains the photos plus the photo -> label mapping.

## Provenance

Photos were extracted from the PDF's image XObjects (pages 1, 13, 22). Annotations are
`/Subtype /Text` objects; each was matched to the image whose bounding box contains the
annotation's `/Rect`. All 12 matches resolved with distance 0.

| file | page | PDF image obj | label |
| --- | --- | --- | --- |
| `p1_Im1_obj3.png` | 1 | 3 | Roxon |
| `p1_Im2_obj5.png` | 1 | 5 | The Helton |
| `p1_Im3_obj7.png` | 1 | 7 | Swiza |
| `p1_Im4_obj9.png` | 1 | 9 | SAK / Essentials / Spartan (SKU 1.3603) |
| `p1_Im5_obj11.png` | 1 | 11 | SAK / Essentials / Synergy X Alox (SKU: 0.8226.22) |
| `p13_Im1_obj16.png` | 13 | 16 | Roxon |
| `p13_Im2_obj18.png` | 13 | 18 | SAK / Essentials / Spartan (SKU 1.3603) |
| `p13_Im3_obj19.png` | 13 | 19 | Swiza |
| `p13_Im4_obj21.png` | 13 | 21 | SAK / Essentials / Synergy X Alox (SKU: 0.8226.22) |
| `p22_Im1_obj24.png` | 22 | 24 | Swiza |
| `p22_Im2_obj26.png` | 22 | 26 | SAK / Essentials / Spartan (SKU 1.3603) |
| `p22_Im3_obj27.png` | 22 | 27 | Roxon |

`labels.json` holds the same mapping in machine-readable form.

## Class distribution

| class | n |
| --- | --- |
| Roxon | 3 |
| Swiza | 3 |
| SAK / Essentials / Spartan (SKU 1.3603) | 3 |
| SAK / Essentials / Synergy X Alox (SKU: 0.8226.22) | 2 |
| The Helton | 1 |

## Caveats

- These are **clean catalogue / packshot photos on white**, not the smartphone photos the
  app will receive in the demo. Expect a further domain gap.
- The Helton has a single example, so per-class retrieval numbers for it are not
  meaningful on their own.
- 12 images is far too small for training. It is enough for a **leave-one-out sanity
  check** of a retrieval approach and for **measuring the size of the domain gap**.
- The PDF also annotates Leatherman, Gerber Gear, Benchmade, EVOKE ALOX, Swiss Tool and
  Swiss Tool Spirit XBS, but those annotations sit in areas of the slides without a
  photo, so no image could be matched to them. Those labels are currently unusable.

## Measured baseline (leave-one-out, image-to-image retrieval)

See `docs/classification_recommendation.md`. Summary of the gap between
within-class and between-class cosine similarity:

| model | top-1 | top-3 | within | between | gap |
| --- | --- | --- | --- | --- | --- |
| `google/siglip2-base-patch16-224` (fastembed) | 1/12 | 2/12 | 0.684 | 0.725 | **−0.041** |
| `google/siglip2-base-patch16-384` (transformers) | 1/12 | 2/12 | 0.694 | 0.720 | **−0.026** |
| `Qdrant/clip-ViT-B-32-vision` | 2/12 | 4/12 | 0.780 | 0.802 | −0.022 |
| `Qdrant/Unicom-ViT-B-16` | 1/12 | 2/12 | 0.305 | 0.360 | −0.055 |
| `nomic-ai/nomic-embed-vision-v1.5` | 1/12 | 2/12 | 0.816 | 0.849 | −0.033 |
| `jinaai/jina-clip-v1` | 1/12 | 4/12 | 0.714 | 0.754 | −0.040 |
| `Qdrant/resnet50-onnx` | 0/12 | 3/12 | 0.457 | 0.526 | −0.069 |

A **negative gap means the encoder places different products of the same class closer
together than products of different classes** — i.e. worse than chance. This is the
single most important finding for the classification workstream: off-the-shelf global
image embeddings do not separate SAK variants.

## Measured baseline (Clef decision model)

For comparison, the same 12 photos with the Clef decision model
(`cloudflare/clef-flash` via OpenRouter `/api/alpha/decisions`):

| approach | top-1 | top-3 |
| --- | --- | --- |
| Clef, brand question, terse criteria | 7/12 (58%) | — |
| Clef, brand question, rich per-option criteria | 6/12 (50%) | **11/12 (92%)** |
| Clef, pairwise "is B the same as A?" | — | 6/12 (50%) tournament top-3 |
| Clef 27B, rich criteria | 6/12 (50%) | 10/12 (83%) |

Notes:

- The **pairwise framing fails**: it scored **0/10** on same-class pairs (and 54/56
  on different-class pairs). Clef almost never answers "same". Ask the open
  question instead.
- The **9B model beats the 27B** here, and the 27B is more confident when wrong.
  Use `clef-flash` as the default.
- The per-option criteria must describe **visible** features (handle colour, logo
  shape, lettering), not brand names alone.
- The 12 photos are clean packshots on white. The demo will use smartphone photos, so
  expect a further drop.

Raw results: `../clef_noul_results.json`, `../clef_pairwise_results.json`.

## Updated brand ranking run (corrected labels)

The earlier direct-brand figures above used the five label keys from `labels.json`
and did not apply the page 13/22 photo-to-sticky-note corrections used by
`backend/training/evaluieren.py`. For a fair brand-level run, the corrected labels
are grouped into seven brands (Roxon, The Helton, SWIZA, Victorinox, Leatherman,
Gerber, Benchmade), and Clef is asked to rank those seven options from visible
evidence. The best of three prompt variants reached **11/12 top-1 and 12/12 top-3**
with `cloudflare/clef-flash`. The 27B model also reached 11/12 and 12/12, but was
more confident on the single miss. Trimming white margins did not change the score.

The sole top-1 error is `p22_Im1_obj24`: Sven's corrected label is Gerber, but Clef
ranks Benchmade first and Gerber second. This result is prompt-tuned on the same 12
examples, so it is a diagnostic upper result for this set, not an independent
generalisation estimate. The production brand prompt now includes the missing
Benchmade option and identifies Gerber by its shield mark as well as lettering; that
exact prompt also scores **11/12 top-1 and 12/12 top-3**. The full production option
list includes unknown/other fallbacks. Reproduce it with:

```bash
python3 tools/eval_clef_pdf.py --candidate-set production
```

Raw probabilities: `../clef_pdf_rich.json`, `../clef_pdf_compact.json`,
`../clef_pdf_evidence.json`, `../clef_pdf_rich_27b.json`, and
`../clef_pdf_rich_trim.json`, `../clef_pdf_production.json`.

## Full local API evaluation

All 12 PDF images were also sent through the local `/api/match` endpoint after the
brand-prompt update. Brand was correct on **11/12**. For the five photos with
Victorinox product labels, the exact labelled article appeared in recommendations
top 3 on **2/5**; matching canonical product families and catalogue variants raises
that to **3/5**. The `0.8226.22` Synergy X Alox photo matched canonical catalogue
article `0.8226.20` at rank 2; the exact colour variant is not selected by the API.

This is a small end-to-end set. Competitor replacement products are not labelled in
the PDF, so their recommendation quality cannot be measured from these annotations.
Full per-photo API responses are in `../api_match_both_sets.json`.

## Reproducing

```bash
uv run python tools/eval_retrieval.py    # embedding baselines
uv run python tools/eval_clef.py         # Clef experiments (needs OPENROUTER_API_KEY)
```

`tools/eval_retrieval.py` needs the `fastembed` extra; `tools/eval_clef.py` needs
`httpx` and an OpenRouter key in `.env` (see `.env.example`).

## Relationship to the catalogue

The scraped catalogue in `backend/data/` contains **Victorinox** SKUs only. Of the
five classes labelled here, four are in the scrape:

| class | article no. | in `victorinox_sak_produkte.csv`? |
| --- | --- | --- |
| SAK / Essentials / Spartan | `1.3603` | yes |
| SAK / Essentials / EVOKE ALOX | `0.9411.D20` | yes |
| SAK / Trades&Crafts / Swiss Tool | `3.0323.L` | yes |
| SAK / Trades&Crafts / Swiss Tool Spirit XBS | `3.0224.3CN` | yes |
| SAK / Essentials / Synergy X Alox | `0.8226.22` | yes, as a colour variant of canonical article `0.8226.20` |

The three competitor brands (Roxon, Swiza, The Helton) are **not** in the catalogue
at all — the cross-reference tables the client mentioned are still needed.
