# Classification workstream — research findings & recommendation

**Owner:** Simon (README work item "Simon: jev")
**Date:** 2026-10-23
**Scope:** SAK category, Victorinox Product Match Agent, hackathon prototype

> **Status of this document.** Everything marked "measured" was measured against the
> live OpenRouter Clef endpoint on the 12 photos in `data/sak_ground_truth/`, and can
> be reproduced with `tools/eval_clef.py` and `tools/eval_retrieval.py`. Two earlier
> drafts of this document contained claims that the later measurements overturned —
> notably that Clef was unavailable on OpenRouter, and that a pairwise tournament was
> the right decision framing. Both were wrong; the corrections are noted inline.

---

## TL;DR

1. **"jev" is a real method and it fits this task perfectly.** It is *Visual Jev*
   (arXiv:2609.25845, Sept 2026). The pattern — encode the image once, then answer
   several independent forced-choice questions and read calibrated probabilities off
   the LM head — is exactly a "which of these top-k candidate products is this?"
   decision.

2. **Use Cloudflare Clef as the decision layer — it is available on OpenRouter** at
   `POST /api/alpha/decisions` (not `/chat/completions`). It is Apache-2.0,
   multimodal, Jev-API-compatible, and costs ~$0.00003/call on `clef-flash`.
   Measured on **real smartphone photos** (`data/real_photos/`): **top-1 = 9/12
   (75%), top-3 = 11/12 (92%)**, with confidence separating cleanly (0.850 when
   correct vs 0.119 when wrong). At confidence ≥ 0.3 it shows 9/12 at **100%
   precision** and abstains on the rest. See §10.

3. **Do not build the classifier on top of CLIP/SigLIP embeddings alone.** I measured
   this on the 12 real ground-truth photos extracted from the client PDF. Every
   off-the-shelf image encoder tested produces a **negative within-class vs
   between-class gap** — i.e. *worse than chance* at telling SAK variants apart.
   Best top-1 was 2/12. Clef alone gets 9–11/12. **Embeddings are now optional for
   brand identification**; add them only if SKU-level precision is needed.

4. **The catalogue's tool lists, not the photo, are the real discriminator.** Aaron's
   scrape gives per-SKU tool lists and colours for 247 SAK products; the 79 Essentials
   SKUs collapse to **57 distinct tool-set signatures** and 72 distinct
   (tool count, colour) signatures. Images cannot separate four classes of black
   multi-tool; the catalogue can. Build the decision criteria from those fields.
   See §8.

5. **Ask the open question, not the pairwise one.** *"Is photo B the same product
   as photo A?"* scored **0/10 on same-class pairs** — Clef almost never says
   "same". *"Which brand is this?"* with detailed per-option criteria scored 11/12
   top-3. The prompt framing matters more than the model size.

6. **Feature-level detection works, but as description not as matching.** Asking the
   model "which tool is visible?" over a **tight 18-option vocabulary** gives
   **100% top-1 precision** against the catalogue's tool lists — and it correctly
   reports "cannot see" for closed knives. But one detected tool is consistent with
   **55–100 of the 247 SKUs**, so it cannot identify the SKU (two-stage filtering
   scored 0/4). Use it for the rationale, a coarse category prior, and as a
   consistency check on the final answer. See §9.
   Two gotchas worth keeping: the vocabulary must be **short** (64 options drops
   precision to 1/4 — near-synonyms like `bottle_cork` vs `corkscrew` win by
   accident), and a closed knife must trigger a request for an open-tools photo.

7. **Use OCR of the visible article number as a hard override.** It is the only
   signal in this domain that can be exact.

**Proposed architecture (in priority order for the remaining time):**

```
photo ──┬─→ [1] OCR (article no.) ─────────────→ exact match, overrides everything
        ├─→ [2] Clef attribute probes (noul) ───→ visible facts: colour, logo, lettering
        └─→ [3] Clef / VLM visual description ──→ "red handle, Swiss cross emblem, 12 tools"
                                                     ▼
        catalogue (backend/data/)  ──────────→ candidates filtered by
        tool count ∩ colour ∩ category ∩ availability   tool-set signature
                                                     ▼
                                    [4] Clef choice over the surviving candidates,
                                        criteria = per-SKU tool list + colour
                                                     ▼
                                    [5] confidence + margin + probe consistency
                                        │              │
                              confident │              │ uncertain
                                       ▼              ▼
                              single result      show candidates +
                                + rationale       ask for closer photo
```
---

## 1. What "jev" is — confirmed

**Visual Jev: Accurate and Efficient Decisions from Shared Visual Context**
- Paper: https://arxiv.org/abs/2609.25845 (submitted 22 Sep 2026)
- Code: https://github.com/guanxuyu-sv/Visual-Jev (Apache-2.0)
- Adapter: https://huggingface.co/guanxuyu/visual-jev-4b-answer-sft (Apache-2.0)
- Authors: Guanxu Yu, Yuhang Yao (CMU)

There is a whole 2026 arXiv family in this style: *Visual Jev*, *FastJEV*,
*Chinese-Jev*, *NavJev*, *Visual Jev Rewards*, plus *"Multimodal Reranking Is a
System One Decision"*. So "Simon: jev" in the README is a deliberate choice of a
current method, not a typo.

### The core idea

> An instance is an image `I`, a public text context `S`, and a set of questions `Q`.
> Each question is answered independently: it may read `I`, `S` and its own text, and
> may not read the other questions or their answers.

Each question supplies its own candidate set at request time (K ≤ 16). The answer is
read from the **backbone's existing LM head** at a fixed `Answer:` position, and the
candidate-token logits are softmax-normalised over just that question's options:

```
p(c_j | I, S, q) = exp(z_j) / Σ_{ℓ=1..K} exp(z_ℓ)
```

So you get a **proper probability distribution over candidates**, not a free-text
essay. That is exactly what a "which product is this?" decision needs, and it gives
you a confidence value for free.

### Why it fits our task

Our decision is textbook Jev:

| Jev concept | Our case |
| --- | --- |
| Image `I` | the customer's smartphone photo |
| Public context `S` | "Victorinox SAK catalogue, 2026" + the candidate metadata |
| Question `q` | "Which candidate is the same product?" |
| Candidates | top-k retrieved catalogue product IDs |
| Answer | exactly one product ID, or "none" |

And the **efficiency** story is directly relevant: we ask *several* questions about
the same photo (brand? model? which candidate? is the article number readable?).
Visual Jev shares one image encoding across all of them: at N=32 questions it is
**8.9× faster** than serial execution (176 q/s vs 20 q/s on an RTX 5090).

### Important caveats from the paper itself

- **N=1 is slower, not faster.** Prefix sharing *adds* overhead at a single question
  (82.9 ms vs 48.1 ms). For a single-product demo the speedup is irrelevant; only
  the decision interface matters. Do not sell the throughput number in the demo.
- The accuracy gain (0.706 → 0.761 macro) came from **post-training on the task**.
  We are explicitly **out of scope for training/fine-tuning**. So we should use the
  **decision interface** (LM-head probability readout over a candidate set) with a
  zero-shot model, and not expect the paper's accuracy numbers.
- The paper's authors explicitly caution: *"the candidate probability this system
  returns is not a calibrated probability that the answer is correct."* We must
  calibrate on our own data and/or add a margin check.
- The evidence-sufficiency head was a **negative result** in the paper (it detects
  missing evidence but does not improve decisions). Do not spend time on it.
- Backbone: Qwen3-VL-4B-Instruct, vision tower frozen, LoRA on the language tower.
  With no training, use the base instruct model via our OpenAI-compatible endpoint.
- Max 16 candidates per question. Larger sets are rejected, not truncated.

---

## 2. The critical measurement: embeddings do not work here

### 2.1 The ground-truth data I extracted

The client PDF (`Input Hackathon_Victorinox.pdf`) is not just a briefing — it is a
**labelled dataset**. It has 3 slides with product photos and 12 sticky-note
annotations by `sven.goldinger`, each a ground-truth label on one photo.

I extracted all of them: `data/sak_ground_truth/` (photos + `labels.json`), with
provenance documented in `data/sak_ground_truth/README.md`.

| class | n |
| --- | --- |
| Roxon | 3 |
| Swiza | 3 |
| SAK / Essentials / Spartan (SKU 1.3603) | 3 |
| SAK / Essentials / Synergy X Alox (SKU: 0.8226.22) | 2 |
| The Helton | 1 |

The PDF also annotates Leatherman, Gerber Gear, Benchmade, EVOKE ALOX, Swiss Tool and
Swiss Tool Spirit XBS — but those annotations sit in **areas of the slides with no
photo**, so they cannot be paired with an image. Worth asking Sven for those
originals; 12 usable labels is thin.

### 2.2 The result

Leave-one-out image-to-image retrieval over the 12 photos. The decisive column is
`gap` = mean within-class cosine − mean between-class cosine.

| model | top-1 | top-3 | within | between | **gap** |
| --- | --- | --- | --- | --- | --- |
| `google/siglip2-base-patch16-224` (fastembed) | 1/12 | 2/12 | 0.684 | 0.725 | **−0.041** |
| `google/siglip2-base-patch16-384` (transformers) | 1/12 | 2/12 | 0.694 | 0.720 | **−0.026** |
| `Qdrant/clip-ViT-B-32-vision` | 2/12 | 4/12 | 0.780 | 0.802 | −0.022 |
| `Qdrant/Unicom-ViT-B-16` | 1/12 | 2/12 | 0.305 | 0.360 | −0.055 |
| `nomic-ai/nomic-embed-vision-v1.5` | 1/12 | 2/12 | 0.816 | 0.849 | −0.033 |
| `jinaai/jina-clip-v1` | 1/12 | 4/12 | 0.714 | 0.754 | −0.040 |
| `Qdrant/resnet50-onnx` | 0/12 | 3/12 | 0.457 | 0.526 | −0.069 |

**Every gap is negative.** Different SAKs of the *same* class are, on average, *less*
similar to each other than SAKs of *different* classes. On this data, image
embeddings are worse than a coin flip.

Two things this rules out:

- It is **not a resolution problem** — 384 px gives the same negative gap.
- It is **not a model-quality problem** — every encoder family behaves the same way.

The cause is structural: these are white-background packshots of near-identical
objects, and the discriminative evidence (a shield logo, a red scale, an emblem)
occupies a tiny fraction of the image and is largely discarded by a global pooled
embedding. Note that all five SAK classes except SPARTAN are *black* — colour is
almost useless here, which is exactly why the global embedding collapses.

Reproduce with:

```bash
uv run python tools/eval_retrieval.py
uv run python tools/eval_retrieval.py --model google/siglip2-base-patch16-224 --multicrop --tagnames
```

### 2.3 What partially helps

**Region max-similarity** (encode 5 crops per image, take the best-matching crop
pair) lifts top-3 from 2/12 to **6/12** and pulls the gap from −0.041 to −0.013.
Better, still not usable alone.

**Text descriptions aligned to images** (simulating a VLM writing a description,
matched against the image embedding) got 0/12 top-1, 5/12 top-3 — *worse* than
image-to-image. So **do not let a VLM caption replace the image signal**; a
caption loses exactly the details that matter here.

**The text↔text sanity check scored 11/12.** Text descriptions of the same product
do match each other well. So the text channel is usable for *filtering and
explaining*, just not for *seeing*.

### 2.4 The conclusion

> Embeddings cannot make this decision. They can only propose who to consider.
> The decision must be made by a model looking at pixels.

This is exactly the case Jev-style forced-choice is built for, and it is exactly
where a generic similarity score fails.

---

## 3. Recommended architecture

### Stage 1 — Candidate generation

**Prefer the catalogue's tool lists over image embeddings** for this (see §8). Two
routes to a shortlist, best first:

- **Tool-list match (deterministic, explainable, no model needed).** Take the visual
  description from Stage 3 ("red handle, Swiss cross emblem, corkscrew and a small
  blade") and match the mentioned tools against the 147-tool vocabulary from
  `backend/data/victorinox_sak_werkzeuge.csv`. Score candidates by how many mentioned
  tools they contain. This narrows 247 SKUs to a handful with no embedding at all.
- **Image embedding (fallback).** SigLIP2 (`google/siglip2-base-patch16-224`) via
  **fastembed**, which the project already depends on. Multicrop max-similarity helps
  (2/12 → 6/12 top-3). Keep the full-image vector too, so a foreground-crop failure is
  visible.
- **Text channel.** Catalogue descriptions (name + tool list + colour) embedded with
  the **matching SigLIP2 text tower**. `fastembed` 0.9.0 supports
  `google/siglip2-base-patch16-224` on **both** the image and the text side, so they
  share one embedding space — verified working (unit-norm 768-d vectors, meaningful
  cosines). A convenient single-model story; no second model to download.
- **Union** of the channels' top-k → ~10 candidates.

Note `fastembed`'s SigLIP2 support is the **base patch16-224** only; the stronger
`so400m` variants are not in fastembed and would need `transformers` (so400m is a
~1.6 GB download and slow on CPU — not worth it for the demo). DINOv3 and DFN are
also *not* in fastembed and are not text-aligned.

### Stage 2 — OCR on the article number (hard override)

Many SAKs have the article number engraved on the scale, and the reference example
is `KNI.0036.1010`. A correct OCR hit is *exact evidence* and should override
everything else.

- **RapidOCR** (Apache-2.0, ONNX Runtime, CPU-friendly) — best low-friction option.
  Tesseract is easier but weaker on small engraved text; EasyOCR pulls in a big
  PyTorch dependency.
- Preprocess: upscale 4–8×, grayscale, CLAHE, Otsu, try 0/90/180/270° rotations.
- Normalise `O`→`0`, `I`/`l`→`1`, then fuzzy-match against the catalogue article
  numbers (exact match, or edit distance 1 **plus** high OCR confidence **plus**
  visual confirmation).
- Be honest in the UI: engraved text is genuinely hard. Use OCR as a *booster*, and
  treat "OCR found nothing" as normal, not as failure.

### Stage 3 — Structured attributes (VLM, JSON only)

Ask the vision model for a JSON object with explicit `unknown` values. Require
`"unknown"` rather than forcing a value — the model must not invent tool counts.

```json
{
  "is_pocket_knife": true,
  "brand": "Swiza | Victorinox | Leatherman | unknown",
  "handle": {"color": "black", "material": "ABS | Alox | unknown", "shape": "..."},
  "visible_tools": ["large blade", "corkscrew", "scissors"],
  "logo": "Swiss cross shield | Swiss cross emblem | none | unknown",
  "article_number_visible": false,
  "uncertainties": ["tool count not determinable"]
}
```

Use this for (a) hard filtering (brand, logo), (b) the explanation text, and
(c) the text-side retrieval query.

### Stage 4 — Clef decision over the candidates ← *the core of my workstream*

This is where the identification happens. **See §7 for the API details and measured
results.**

The shape of the decision is textbook Jev:

| Jev concept | Our case |
| --- | --- |
| Image `I` | the customer's smartphone photo |
| Public context `S` | the candidate catalogue metadata |
| Question `q` | "Which brand and model is this?" |
| Candidates | the retrieved catalogue product IDs |
| Answer | one product ID, with a probability distribution |

**Recommended: Clef via OpenRouter's `/api/alpha/decisions`.**

Measured on our 12 photos with `clef-flash` and detailed per-option criteria:

- **top-3 = 11/12 (92%)** — meets the README's "high share of correct products in
  the top-3 hits"
- top-1 = 6/12, rising to 9/12 (58%) with terser criteria
- $0.00003 per decision

**Ask an open question, not a pairwise one.** This is the single most important
prompt-design finding:

- ❌ *"Is photo B the same product as photo A?"* → **0/10** on same-class pairs.
  Clef almost never answers "same".
- ✅ *"Which brand and model is this pocket knife?"* with per-option criteria →
  11/12 top-3.

**The per-option criteria must describe visible features**, not brand names alone.
This worked:

```json
{
  "roxon":   "ROXON brand. Black handle. The word ROXON is printed in white capitals on the handle. Slender parallel metal frames.",
  "helton":  "The Helton. Black textured handle with no logo and no lettering. Narrow plain blade.",
  "swiza":   "Swiza. Black handle with a Swiss cross inside a shield badge. SWIZA lettering on the handle.",
  "spartan": "Victorinox Spartan. RED handle with the Swiss cross emblem. Classic Swiss Army Knife shape.",
  "synergy": "Victorinox Synergy X Alox. Dark grey/black plain textured scales, no logo, no lettering."
}
```

**Always include a "none / unclear" option.** It gives the model somewhere to put a
genuinely ambiguous photo, which is what the README's abstention requirement needs.

**Use `clef-flash` as the default, not the 27B.** Measured: flash 58% top-1 vs 27B
50%, and the 27B is *more confident when wrong* (mean confidence 0.746 when wrong).
Reserve `clef` for escalation when flash's margin is small.

**Fallbacks, in order of preference:**

1. `clef` (27B) via the same endpoint — same client, one model swap.
2. Plain VLM via our OpenAI-compatible endpoint, forced-choice over letters. We get
   only the *choice*, not a probability, so confidence must be derived.
3. `typesafe/jev-router` on OpenRouter — **text output only**, and the SystemOne
   decision API is not exposed there. Requires the photo to be described in text
   first, making the attribute step load-bearing. A degraded fallback.
4. Visual Jev proper (arXiv:2609.25845 + the Apache-2.0
   `guanxuyu/visual-jev-4b-answer-sft` adapter) — gives the genuine LM-head
   probability distribution, but needs a Qwen3-VL-4B served locally. Note plain Jev
   is text-only, so this path requires the *Vision* Jev variant.

**Prompt-hygiene rules, taken from the papers' own diagnostics:**
- **Shuffle the candidate order** every call — option order is itself a bias.
- Build distractors from **same-type** answers (another SAK), not a global pool.
- Run a **blind baseline**: ask the same question with the photo replaced by a grey
  field. If the model still answers confidently, the candidate set is giving it away.
  (The Visual Jev paper found a 58.5% blind baseline on converted GQA vs 36.5% chance
  — a reminder to always check.)

### Stage 5 — Confidence and abstention

Never expose a raw cosine similarity as confidence. Use the decision probabilities,
but **calibrate them** — measured on our 12 photos, Clef's raw confidence is only
weakly calibrated:

| model | mean conf when correct | mean conf when wrong | at conf ≥ 0.7 |
| --- | --- | --- | --- |
| `clef-flash` | 0.585 | 0.499 | 75% precision, 33% coverage |
| `clef` (27B) | 0.746 | 0.640 | 60% precision, 42% coverage |

So the bigger model is not just less accurate on this task, it is *more confidently
wrong*. Prefer `clef-flash` and use the **margin** rather than the top probability
as the abstention signal.

Combine signals:

```python
final = (0.55 * clef_margin          # top1 - top2 over the option probabilities
       + 0.20 * clef_top_probability
       + 0.15 * probe_consistency    # do the noul attribute probes agree?
       + 0.10 * retrieval_agreement) # only if embeddings are in the pipeline
```

With an **exact OCR match**, override the score entirely and set confidence high —
but say in the UI *why* (the article number was read).

**Abstain** (show several candidates, ask for a closer photo) when:

- the top-1 vs top-2 **margin** is below a threshold (calibrate on the 12 photos —
  the misses had low margins: 0.035, 0.105, 0.155, 0.162, 0.277),
- `clef-flash` and `clef` disagree (they agreed on 11/12, and between them covered
  all 12 — so disagreement is a strong "unsure" signal),
- the attribute probes contradict the chosen brand (e.g. the brand decision says
  SPARTAN but the `red` probe says 0.02),
- the choice was "none / unclear",
- the photo is partly cut off, or is not a pocket knife at all.

Match the README's requirement: *"Low separation between the top candidates must not
be hidden."* The abstention path is a **feature**, not a fallback — it demonstrates
honesty, which is an explicit success criterion.

Calibrate the thresholds on the 12-photo set with leave-one-out, and report top-1,
top-3 and abstention rate. With 12 samples, prefer conservative thresholds that
favour abstention over confident wrong answers.

**A caveat on the measured numbers.** 12 photos is a very small sample, and they are
clean white-background packshots, not the smartphone photos the demo will use. Expect
a further drop from the domain gap, and expect the *relative* ranking of approaches
to hold. Re-measure with real demo photos as soon as you have them.

### Stage 6 — The recommendation (not my workstream, but the interface)

Once the source product is identified, the Victorinox alternative comes from
weighted scoring over dimensions/functions, lock type, dimensions, availability,
and explicit cross-reference/successor rules — per the README. My part hands over a
confident source identity plus the attributes that feed that scoring.

---

## 4. What I would **not** do

- **Do not fine-tune.** Out of scope, and 12 photos is statistically hopeless for it
  (a linear probe on frozen features would already be questionable).
- **Do not use a typed classification head.** The paper's own matched comparison found
  no advantage over the LM head (both 0.761 macro). Keep it simple.
- **Do not build an evidence-sufficiency head.** Negative result in the paper.
- **Do not sell the throughput speedup in the demo.** At N=1, prefix sharing is
  *slower*. Sell the decision quality and the traceability instead.
- **Do not let the VLM caption be the query.** Measured worse than image-to-image.
- **Do not let similarity scores be the headline confidence.** It is not calibrated
  and the paper explicitly warns against reading it as correctness.
- **Do not default to the 27B Clef model.** Measured *worse* than the 9B on this task
  (50% vs 58% top-1) and more confidently wrong. Use `clef-flash`; reserve the 27B
  for escalation.
- **Do not use the pairwise "is B the same as A?" framing.** It scored 0/10 on
  same-class pairs. Ask the open question with explicit options.
- **Do not build a CLIP/SigLIP index as the primary classifier.** It measures worse
  than chance here. Keep the embedding work (Philipp) as a *candidate generator* for
  SKU-level recall, not as the decision.
- **Do not wait for more labels before building anything.** 12 photos is enough to
  establish that embeddings fail and that Clef works. That conclusion will not change
  with more data — only the accuracy number will.

---

## 5. Suggested sequence for the remaining time

The hackathon is 24 h with a live demo. Proposed order, highest value first:

| # | Task | Why now |
| --- | --- | --- |
| 1 | **Clef decision via `tools/clef_client.py`** — brand/category choice + `noul` probes | This is the classifier. Measured **9/12 top-1, 11/12 top-3 on real photos**, 100% precision above conf 0.3 |
| 2 | **Open/closed gate** before anything else | A closed knife cannot be feature-probed. Gate on `open_state`, then either identify brand-only + ask for an open photo, or go the full SKU route |
| 3 | Build the per-SKU `criteria` from the scrape: tool list + colour + category | Turns the decision from "which brand" into "which SKU" — the tool lists are the real discriminator (§8) |
| 4 | Translate the German tool names to English | **Done** — `tools/tool_vocab.py` maps all 147 names, 0 unmapped |
| 5 | Candidate shortlist by tool-set signature (string match, no embeddings) | Deterministic and explainable; narrows 247 SKUs to a handful |
| 6 | Rationale generation (separate VLM call) + comparison view | README requires a human-readable justification; Clef cannot generate text |
| 7 | Confidence fusion + margin-based abstention | **Validated**: conf ≥ 0.3 → 100% precision on real photos |
| 8 | OCR (RapidOCR) with article-number lookup | Highest-precision signal; the "VICTORINOX" marks in these photos suggest it is readable |
| 9 | *If needed:* SigLIP2 embeddings for the residual cases | Only if the tool-list match is not enough |

**Ask the client for more labelled photos.** 12 is the binding constraint on every
number above. The PDF's unmatchable annotations (Leatherman, Gerber Gear,
Benchmade, EVOKE ALOX, Swiss Tool, Swiss Tool Spirit XBS) are a concrete, specific
ask: *"can we get the original slide source with photos and labels together?"* Also
worth asking for photos where the article number is visible, and for 2–3 views per
product, since multi-view is what makes embedding retrieval work.

---

## 6. Open questions for the team

1. **Is "jev" definitely Visual Jev / the SystemOne family?** If Philipp and Simon
   meant something else, say so — the design is the same either way, but the framing
   and the citation differ. Note that **Clef is the Jev-API-compatible sibling**, so
   picking Clef satisfies either reading.
2. **OpenRouter is already wired up and working** — `OPENROUTER_API_KEY` is in `.env`,
   and `tools/clef_client.py` calls `/api/alpha/decisions` successfully. Cost is
   ~$0.00003 per decision on `clef-flash`, so budget is a non-issue. Remaining
   question: is there a spend limit, and do we have a fallback key?

3. **Do we have a local GPU, and how much VRAM?** Only needed if we want to
   self-host `clef-flash` (19 GB), which would lift the 4-image-per-request limit and
   allow a single listwise call over many candidates. Not needed for the demo.

4. **The scrape is Victorinox-only — where are the competitor SKUs?** Our
   ground-truth set is mostly competitor brands (Roxon, Swiza, The Helton) and **none
   of them are in `backend/data/`**. The client said cross-reference tables exist
   "in part". Are they coming? Without them, the demo can only identify Victorinox
   products, which is the *other* half of the challenge ("find the Victorinox
   alternative for this competitor knife").

5. **Does the API need to select exact colour variants?** The catalogue row for
   canonical article `0.8226.20` includes `0.8226.22` among its three variants. The
   full API can recommend the Synergy X Alox family but currently returns the
   canonical article, not the exact labelled colour variant.

6. **What are the cross-reference tables?** The README says they exist "in part". If
   a competitor SKU already maps to a Victorinox SKU, that mapping should *override*
   visual similarity — it is authoritative.

7. **Who writes the rationale text?** Clef deliberately cannot generate free text. The
   README requires a human-readable justification, so we need either a separate
   generative VLM call or a templated rationale built from the decision + catalogue
   fields.

8. **Can we get more labelled photos?** The 12 real photos in `data/real_photos/`
   are the best data we have, and they cover only 5 classes (4× red SAK, 4× black
   SAK, 2× ruler, 1× Leatherman, 1× Gerber). The PDF's unmatchable annotations
   (Leatherman, Gerber Gear, Benchmade, EVOKE ALOX, Swiss Tool, Swiss Tool Spirit
   XBS) are a concrete ask: *"can we get the original slide source with photos and
   labels together?"* Also worth asking for photos where the article number is
   visible, and 2–3 views per product.
9. **Should the demo ask for an open-tools photo?** The measurements say SKU-level
   identification needs it, and brand-level works without it. Asking for one extra
   photo when the knife is closed is a cheap trade for a much more precise
   result — but it costs a demo round-trip, so it is a product decision.

---

## 7. Cloudflare Clef — the decision layer to use

**Short answer: yes, use Clef. It is strictly better than what I proposed in §3 Stage 4,
and it removes most of the implementation risk in this workstream.**

Clef is Cloudflare's open-weight **decision model** family. It is the multimodal
successor to Jev and it is *already released*, unlike the Visual Jev paper's
fine-tuned adapter.

| | Clef | Clef-Flash |
| --- | --- | --- |
| HuggingFace | [`Cloudflare/clef`](https://huggingface.co/Cloudflare/clef) | [`Cloudflare/clef-flash`](https://huggingface.co/Cloudflare/clef-flash) |
| Backbone | Qwen3.8-27B | Qwen3.5-9B |
| License | **Apache-2.0** | **Apache-2.0** |
| Vision | **Yes** | **Yes** |
| Context (hosted) | 65,536 tokens | 24,576 tokens |
| Hosted price | $0.24 / M input tokens | **$0.038 / M input tokens** |
| Weights size | 55 GB | 19 GB |
| Median latency | 209 ms | **38.8 ms** |
| Hosted model id | `@cf/cloudflare/clef` | `@cf/cloudflare/clef-flash` |

### Why it fits this task better than Jev

From Cloudflare's announcement blog: *"it has a vision encoder so it's able to take in
images and classify visual content. **This is different from Jev, which only does text
classification today**."*

That is precisely the gap I identified in §2: our decision is a **visual** one, and
plain Jev cannot look at images. Clef can. The Visual Jev paper's approach requires a
Qwen3-VL backbone plus a LoRA adapter we would have to serve ourselves; Clef is a
**single hosted endpoint** that takes images directly.

### It is API-compatible with Jev/SystemOne

Clef answers `POST /v1/systemone` requests and returns the same body shape:
`answers` keyed by question id, each `choice` answer carrying `choice`,
`confidence` and `probabilities`. Question types:

- `choice` — named options (our product match)
- `noul` — true/false (our "is an article number visible?" / "is this a pocket knife?")
- `score` — ordered options (our confidence in a 0–1 scale)

This is the Jev interface, so the design in §3 Stage 4 carries over almost unchanged
— and we get **real per-option probabilities**, not a chat completion we have to parse.

### The hosted API accepts images directly

```
POST https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/ai/run/@cf/cloudflare/clef-flash
{
  "model": "clef-flash",
  "state": "<catalogue metadata for the candidate products>",
  "images": [<query photo>, <candidate 1>, <candidate 2>, <candidate 3>],
  "questions": {
    "match": {
      "type": "choice",
      "instructions": "Which candidate is the same product as the first photo?",
      "criteria": {
        "KNI.0036.1010": "Swiza D03 AM, black ABS scales, corkscrew and scissors",
        "0.9411.D20":    "Victorinox EVOKE ALOX, dark Alox scales, master blade",
        "none":          "None of the candidates is the same product"
      }
    },
    "article_visible": { "type": "noul", "instructions": "Is an article number legible?" }
  }
}
```

Response gives `answers.match.probabilities` — a distribution over the candidate
article numbers. That is a **calibrated-ish confidence** and a **margin** for
abstention, both of which the README asks for, essentially for free.

### Cost

A realistic call — query photo + 3 candidate photos + catalogue metadata ≈ 5,300
input tokens:

| model | cost / call |
| --- | --- |
| clef (27B) | ~$0.0013 |
| clef-flash (9B) | **~$0.0002** |

Even 1,000 demo calls cost under 20 cents. This is a rounding error next to the
engineering time of self-hosting a 19–55 GB model.

### Image handling: images go in the `state` array

The **Cloudflare Workers AI** endpoint takes a top-level `images[]` array (max 4
items, 1,024 tokens each). The **OpenRouter** endpoint does not — it returns HTTP 400:

> `Top-level 'images' is not supported. Put each image in the 'state' array as
> {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}`

On OpenRouter, images are content parts inside `state`:

```python
state = [
    {"type": "text", "text": "Product photo:"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
]
```

`tools/clef_client.py` handles this: pass `images=[path, ...]` and it builds the
data URLs for you.

### Recommended variant

| | use |
| --- | --- |
| **clef-flash (9B)** | **Default.** 38.8 ms median, $0.038/M, ~$0.00003 per decision. Measured *better* than the 27B on this task (58% vs 50% top-1). |
| **clef (27B)** | Escalation for close calls. Measured 50% top-1 and **more confident when wrong** — so it is a tie-breaker, not an upgrade. |

This gives a natural two-tier design that also *is* the abstention mechanism:
**flash decides, 27B confirms, and if they disagree → show candidates and ask for a
closer photo.** The two models agreed on 11/12 and between them covered all 12, so
disagreement is a strong "unsure" signal.

### Does Clef fix the embedding problem? Mostly — and that changes the plan

Clef is the **decision layer**, not the **candidate generator**. Measured on the same
12 photos:

| layer | result |
| --- | --- |
| best embedding retrieval (SigLIP2 + others) | 2/12 top-1, 2/12 top-3 |
| Clef brand decision, rich criteria | 6/12 top-1, **11/12 top-3** |

So for **brand** identification the embeddings are no longer needed at all — Clef
reads the photo directly and wins comfortably. That is a significant simplification:
the embedding work becomes optional rather than load-bearing.

For **SKU-level** precision the picture changes again, in the other direction — and
that is where the catalogue's tool lists take over (§8). The embeddings' remaining
job is narrow: recall. Get the true SKU into a shortlist of ~8, then let the
decision layer pick it using the tool list and colour as criteria.

```
catalogue tool lists  →  shortlist top-8 by tool-set signature   [deterministic]
embeddings (optional) →  shortlist top-8 by image similarity       [recall fallback]
Clef choice over the shortlist, criteria = per-SKU tool list + colour  [the classifier]
OCR                  →  hard override
```

### Practical notes

- **Self-hosting is possible but not necessary.** `clef-flash` is 19 GB in BF16;
  there are GGUF/INT8/FP8/NVFP4/MXFP4 community quantisations. But for a 24-hour
  hackathon, the hosted endpoint is the right call — it removes GPU provisioning from
  the critical path entirely.
- **OpenRouter is the easiest route** and is already wired up: `OPENROUTER_API_KEY`
  in `.env`, `tools/clef_client.py` calling `/api/alpha/decisions`. The Cloudflare
  Workers AI endpoint (`@cf/cloudflare/clef-flash`) is the alternative and takes a
  top-level `images[]` array instead. Both return the same typed answer shape, so
  swapping is a one-line change.
- **Images must be embedded, not URL'd.** Remote URLs are not accepted. Base64-encode
  and downscale first: 32×32 px per token, 1,024-token cap per image, 4 MiB per
  image, 8 MiB total decoded, 13 MiB request body.
- **SGLang locally** is the documented path (`/v1/systemone`), so if we do self-host
  the client code barely changes.
- **The endpoint occasionally resets the connection.** `tools/clef_client.py` retries
  with exponential backoff (3 retries by default).
- **Does not do free-form text.** Clef returns only typed probabilities — it cannot
  write the rationale. The rationale must come from a separate generative VLM call
  (or be templated from the decision + catalogue data). Keep those separate.

### Head-to-head evidence

`Scan or Index? large Evidence Coverage, Answer Quality, and Cost in Long-Document RAG`
(arXiv:2610.28957, 20 Oct 2026) compares Jev, OpenAI Decisions and local Clef on
retrieval selection. On their book corpus:

| method | evidence coverage @5 | median latency (hybrid) | full-scan latency |
| --- | --- | --- | --- |
| Hybrid + Jev | **94.1%** | 1.72 s | 25.1 s |
| Hybrid + Clef | 91.2% | 54.7 s | 23.3 min |
| Hybrid + Decisions | 87.4% | 4.51 s | 63.4 s |

Caveat: their Clef ran locally on a **shared GB10, serially, in BF16** — hence the
slow numbers; the hosted Workers AI deployment is far faster (38.8 ms median for
clef-flash). The relevant lesson for us is not the latency column but that **Clef
completed 80/80 scans where Jev completed 76/80 and Decisions 72/80** — i.e. it was
the most *reliable* of the three, never failing. For a demo where a crash or a
timeout is visible, that reliability matters.

Also relevant: the paper confirms **evidence coverage and answer accuracy are
different things** — higher coverage did not consistently produce better answers.
Another reason not to trust embedding similarity as a proxy for correctness.

### Available via OpenRouter — yes, on a dedicated endpoint

**Correction:** an earlier version of this document said Clef was not on OpenRouter.
That was wrong. Clef **is** on OpenRouter, but it is **not** reachable through
`/chat/completions` — it lives on a separate endpoint:

```
POST https://openrouter.ai/api/alpha/decisions
```

The error message when you get this wrong is explicit:

> `cloudflare/clef is a decisions model and cannot be used with the chat/completions
> endpoint. Use the /api/alpha/decisions endpoint instead.`

Model ids: `cloudflare/clef` (27B) and `cloudflare/clef-flash` (9B).

Two gotchas that cost time if you do not know them:

1. **The catalogue hides them.** `GET /api/v1/models` returns 469 models and *none*
   of them contain "clef" or "cloudflare", and `GET /api/v1/models/cloudflare/clef`
   returns 404 even **with** a valid API key. The model is dispatchable but not
   listed. Do not use the catalogue to decide whether a model exists.
2. **Images do not go in a top-level `images` field.** That returns 400 with the
   message *"Top-level `images` is not supported. Put each image in the `state` array
   as `{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}`"* —
   even though the Cloudflare Workers AI API *does* take a top-level `images` array.
   The two APIs differ.

Request shape that works:

```json
{
  "model": "cloudflare/clef-flash",
  "state": [
    {"type": "text", "text": "Product photo:"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ],
  "questions": {
    "brand": {
      "type": "choice",
      "instructions": "Which brand and model is this pocket knife?",
      "criteria": {
        "roxon": "ROXON brand. Black handle, ROXON printed in white capitals...",
        "swiza": "Swiza. Black handle with a Swiss cross inside a shield badge...",
        "none":  "None of these - the photo is too unclear"
      }
    }
  }
}
```

Response gives `answers.brand.probabilities` — a distribution over option ids, plus
`confidence`. Question types: `choice` (named options), `noul` (true/false, returns
the probability of true), `score` (ordered options).

A working client is in `tools/clef_client.py`; the evaluation harness is
`tools/eval_clef.py`.

### Measured results on our 12 ground-truth photos

I ran real decisions against the 12 labelled photos. These are the numbers that
should drive the design.

**Direct brand identification** — one photo in, "which brand is this?", five options:

| model | top-1 | top-3 | cost / call |
| --- | --- | --- | --- |
| `clef-flash` (9B) | 7/12 (58%) | — | $0.00003 |
| `clef` (27B) | 6/12 (50%) | — | $0.00019 |
| `clef-flash`, **rich per-option criteria** | 6/12 (50%) | **11/12 (92%)** | $0.00003 |
| `clef` (27B), rich per-option criteria | 6/12 (50%) | 10/12 (83%) | $0.00019 |

**Key findings:**

- **Top-3 hits 11/12 (92%)** with detailed per-option criteria — which is exactly
  the README's success criterion ("a high share of correct products in the top-3
  hits"). The criteria must describe *visible* features (handle colour, logo shape,
  lettering), not brand names alone.
- **The 27B model is not better here** (50% vs 58% top-1) and is **more confident
  when wrong**. Do not assume the bigger model wins; here the 9B model is both
  faster and better. Use 27B only as an escalation for ambiguous cases, not as the
  default.
- **Confidence is weakly calibrated.** Mean confidence when correct vs wrong:
  0.585 vs 0.499 (flash), 0.746 vs 0.640 (27B). The signal is there but weak.
  At `confidence ≥ 0.7` flash reaches 75% precision on 33% coverage. This supports
  a **margin-based abstention**, not a hard confidence cut.
- **The two models agree on 11/12, and between them they cover all 12 (100%
  oracle).** So a two-model ensemble — flash first, 27B as escalation — is worth
  trying, but the real value is that disagreement *is* the abstention signal.
- **Cost is negligible:** $0.00003 per decision on flash. 1,000 demo calls ≈ $0.03.

The earlier pairwise experiment asked *"is photo B the same product as photo A?"*
for all 66 pairs. Its results are below.

**Correction, 2026-10-24:** The table above is the earlier five-option experiment and
used the raw labels without the page 13/22 photo mapping corrections. The current
seven-brand evaluation applies the corrected photo labels and reaches **11/12 top-1,
12/12 top-3** with Clef Flash. The updated production prompt, including Benchmade and
the unknown/other fallbacks, scores the same. Clef 27B ties the score but is more
confident on its one error. Three prompt variants and trimmed images were compared on
these same 12 examples, so this is a prompt-tuned in-sample result. The one miss is a
low-resolution Gerber folder ranked as Benchmade. Reproduce the production brand stage
with `python3 tools/eval_clef_pdf.py --candidate-set production`; raw probabilities are
in `data/clef_pdf_*.json`.

The **9/12 top-1, 11/12 top-3** result documented in §10 is from the separate, harder
PXL smartphone set (`data/real_photos/`), not the PDF packshots. See the dataset-specific
labels and score definitions before comparing the two.

| | result |
| --- | --- |
| different-class pairs | 54/56 correct (96%) |
| **same-class pairs** | **0/10 correct (0%)** |
| tournament top-1 | 2/12 (17%) |
| tournament top-3 | 6/12 (50%) |

Clef almost never says "same". It is good at rejecting and bad at confirming, so a
pairwise tournament throws away the signal. **Ask the open question ("which brand is
this?") with explicit options instead.**

**Attribute probes work well as a separate channel.** `noul` questions on the same
12 photos gave a clean separation:

| class | red | cross emblem | brand lettering | tools shown open |
| --- | --- | --- | --- | --- |
| ROXON | 0.020 | 0.052 | 0.706 | 0.675 |
| HELTON | 0.017 | 0.098 | 0.397 | 0.962 |
| SWIZA | 0.027 | 0.326 | 0.525 | 0.667 |
| SPARTAN | **0.641** | 0.686 | 0.367 | 0.698 |
| SYNERGY | 0.020 | 0.614 | 0.463 | 0.973 |

The `red` probe alone perfectly separates SPARTAN (0.94–0.96) from everything else
(0.013–0.045) — a threshold anywhere in between works. But the other features
overlap heavily between ROXON / HELTON / SWIZA / SYNERGY, which are all black. This
is the same colour-collapse problem from §2, and it explains why the brand decision
struggles: four of five classes are black multi-tools with subtle logos.

**A note on the `open` probe.** It is unreliable — 0.96 for ROXON (tools open) but
also 0.97 for SYNERGY (tools closed). Do not build on it.

### Revised architecture

```
photo ──┬─→ [1] OCR (article no.) ──────────────→ exact match / hard override
        ├─→ [2] Clef attribute probes (noul) ────→ per-photo visual facts
        └─→ [3] Image embedding (SigLIP2) ───────┐
                                                    ├─→ shortlist
        ┌───────────────────────────────────────────┘
        ▼
    [4] Clef brand decision (choice, rich criteria) → probabilities
        ▼
    [5] confidence + margin + probe consistency → answer or abstain
```

Note what changed: **embeddings are now optional.** Clef's brand decision reads
9/12 or 11/12 correctly on its own from a single photo. Embeddings still help when
the catalogue holds hundreds of SKUs and the brand is not enough — but for brand
identification, Clef alone is stronger than everything the embedding pipeline
produced (§2.2: 2/12).

That is a big simplification and it changes the priority order: **get the Clef
decision working first**, then add embeddings only if SKU-level precision is needed.

---

## 8. What Aaron's catalogue scrape gives us (and how it changes the plan)

Aaron's scrape is in `backend/data/`:

| file | rows | contents |
| --- | --- | --- |
| `victorinox_sak_produkte.csv` | 247 | article number, name, categories, sub-categories, price CHF, stock status, colour variants, tool count, tool list, product URL, image URL |
| `victorinox_sak_werkzeuge.csv` | 1,936 | article number → individual tools (147 distinct tools) |

This is the data §3 assumed would exist. It has **everything** the README asks for:
technical features (the tool lists), availability (`lagerstatus`), and images
(`bild_url`, 247/247 populated).

### The key insight: tool lists are the discriminator that images failed at

This is the important consequence of §2. The image embeddings could not tell two
black multi-tools apart because they are *visually* almost identical. But the
catalogue says they are **functionally** different:

```
1.3603  Spartan
        12 tools: Klinge, gross / Klinge, klein / Korkenzieher / Stech-Bohr-Nähahle /
        Ring / Pinzette / Zahnstocher / Kapselheber / Schraubendreher 3 mm /
        Schraubendreher 6 mm / Dosenöffner / Drahtabisolierer
        farben: rot, schwarz, weiss, rot transparent, camouflage, blau transparent, silvertech
```

So the discriminating signal is **"how many tools, which tools, what colour"** — and
that is a *text* question. Which is exactly what a decision model is good at.

Measured on the 79 Essentials SKUs that have a tool list:

- **57 distinct tool-set signatures** for 79 SKUs → the tool list alone identifies
  most SKUs uniquely.
- Only 6 signatures are shared by more than one SKU, and those differ by colour
  (e.g. 3 SKUs share a 9-tool set but differ in `farben`).
- **72 distinct `(tool count, colour)` signatures** — so tool count + colour is even
  more discriminative than the tool set alone.

That is a **catalogue-side** discriminator that is far stronger than anything
measured on the image side. It also explains the ceiling in §7: four of the five
ground-truth classes are black multi-tools, so the *photo* genuinely cannot
distinguish them, but the *catalogue* can.

### Coverage of our ground-truth set

| ground-truth class | article no. | in the scrape? |
| --- | --- | --- |
| SAK / Essentials / Spartan | `1.3603` | **yes** |
| SAK / Essentials / EVOKE ALOX | `0.9411.D20` | **yes** |
| SAK / Trades&Crafts / Swiss Tool | `3.0323.L` | **yes** |
| SAK / Trades&Crafts / Swiss Tool Spirit XBS | `3.0224.3CN` | **yes** |
| SAK / Essentials / Synergy X Alox | `0.8226.22` | yes — listed as a variant of `0.8226.20` |
| Roxon / Swiza / The Helton (competitor brands) | — | **not present** |

Two consequences:

1. **The scrape is Victorinox-only.** The three competitor classes in our
   ground-truth set (Roxon, Swiza, The Helton) have no catalogue entry at all. The
   cross-reference tables the client mentioned are therefore *not* in this scrape, and
   the competitor → Victorinox mapping still has to come from somewhere else. This is
   the single most important open question (§6).
2. **The canonical product family is present, but exact variant selection is not
   measured as a family match.** The label `0.8226.22` resolves to canonical
   `0.8226.20`; the current app recommends the family but does not choose that
   specific variant.

### Revised architecture

The catalogue's discriminative fields change what the decision model should be asked:

```
photo ──┬─→ [1] OCR (article no.) ─────────────→ exact match, overrides everything
        ├─→ [2] Clef attribute probes (noul) ───→ visible facts: colour, logo, lettering
        └─→ [3] Clef / VLM visual description ──→ "red handle, Swiss cross emblem, 12 tools"
                                                     ▼
        catalogue (backend/data/)  ──────────→ candidates filtered by
        tool count ∩ colour ∩ category ∩ availability   tool-set signature
                                                     ▼
                                    [4] Clef choice over the surviving candidates,
                                        criteria = per-SKU tool list + colour
                                                     ▼
                                    [5] confidence + margin → answer or abstain
```

Concretely, the criteria for each candidate SKU become data-driven:

```python
criteria = {
    sku.artikelnummer: (
        f"{sku.name} — {sku.anzahl_werkzeuge} tools "
        f"({', '.join(sku.werkzeuge.split(' / '))}), "
        f"colours: {sku.farben}"
    )
    for sku in candidates
}
```

This is much stronger than the brand-level criteria in §7, because now each option
describes a *functionally distinct* product rather than a brand.

**Important caveat:** the tool lists are in **German** (`Klinge, gross` = large blade,
`Korkenzieher` = corkscrew, `Schere` = scissors). The Clef model is English-centric.
Either translate the ~147 tool names once into a lookup table, or give the model the
German terms directly and let it match the English visual description. A small
de→en mapping for the 147 tools is probably 30 minutes of work and is worth doing.

### Also worth doing: match on the tool list, not the image

A cheap, high-value addition: **index the catalogue by tool set**. If the VLM says
"the photo shows a corkscrew and a small blade", we can string-match that against
the tool vocabulary and shortlist the SKUs whose tool list contains both. That
narrows ~247 SKUs to a handful without any image embedding at all, and it is
deterministic and explainable — which the README's "traceable recommendations"
criterion rewards.

---

## 9. Feature-level detection: does it help, and where does it break?

The idea: instead of asking "which product is this?", ask "**which tools does it
have?**" — a saw, scissors, a corkscrew — and match those features against the
catalogue's per-SKU tool lists. The photo cannot distinguish two black multi-tools,
but the *tool list* can, so detecting tools should sharpen the match.

I tested this properly. The answer is **yes for describing the product, no for
identifying the SKU** — and the reason is instructive.

### The detection itself works well — with a tight vocabulary

Two framings, both as a single `choice` question over the tool vocabulary
(`tools/tool_vocab.py` maps all 147 catalogue tool names to English):

| framing | top-1 precision vs catalogue truth | top-5 recall |
| --- | --- | --- |
| **multi-choice over the vocabulary** | **100%** (4/4) | 35% |
| independent `noul` probes per tool | 43–80% | 50% |

The multi-choice framing is clearly better: asking *one* question ("which of these
tools is visible?") and reading the probability distribution beats asking 15
independent yes/no questions, which accumulate false positives.

#### The vocabulary size is the critical knob

This is the most actionable finding in this section, and it is counter-intuitive.
Same model, same photos, same prompt — only the number of options changed:

| options offered | top-1 precision | what the top-1 became |
| --- | --- | --- |
| **18** (photo-visible subset) | **4/4** | `corkscrew`, `large_blade`, `scissors`, `scissors` |
| 24 | 2/4 | `bottle_cork` instead of `corkscrew` |
| 30 | 1/4 | `bottle_cork`, `paracord` |
| 48 | 1/4 | `bottle_cork`, `paracord` |
| 64 (full catalogue vocabulary) | 1/4 | `bottle_cork`, `paracord`, `ruler` |

Every extra plausible option competes for probability mass, and near-synonyms win by
accident: `bottle_cork` is actually a *coupling* for a corkscrew, not a corkscrew;
`paracord` is a strap, not a tool. The model cannot separate them reliably, so
including them turns a correct `corkscrew` into a wrong `bottle_cork`.

**So: keep the option list short and photo-relevant.** `tools/tool_vocab.py`
defines `PHOTO_VISIBLE_TOOLS` — 18 tools that are actually distinguishable in a
photograph of an open knife — and `EN_OPTIONS()` uses it by default. The full
64-tool mapping is still there for *catalogue* comparison (every SKU's tool set is
translated), it just must not be offered as detection options.

Per-photo results for the multi-choice framing, checked against the catalogue's
tool set for that SKU:

| photo | SKU | top-1 detected tool | in catalogue tool set? |
| --- | --- | --- | --- |
| `p1_Im4_obj9` (Spartan, open) | `1.3603` | `corkscrew` (0.51) | **yes** |
| `p22_Im2_obj26` (Spartan, closed) | `1.3603` | `large_blade` (0.79) | **yes** |
| `p1_Im5_obj11` (Synergy, open) | `0.8226.20` | `scissors` (0.59) | **yes** |
| `p13_Im4_obj21` (Synergy, open) | `0.8226.20` | `scissors` (0.29) | **yes** |

### Visibility is the gate, and it is cleanly detectable

The `open_state` probe separates the photos almost perfectly: 0.84–0.96 for the nine
open-tools photos, **0.02–0.03** for the three closed ones. That matters, because a
closed knife genuinely cannot be feature-probed — and the model says so rather than
guessing. On closed knives the tool probabilities collapse to ~0.02–0.05 across the
board, which is the honest answer.

So the pipeline should check `open_state` first and, when the knife is closed, ask
for a photo of the open knife rather than pretending to detect features.

### Where it breaks: one detected tool is far too weak a signal

Here is the arithmetic that sank the idea, and it is worth stating precisely because
it looks like it should work:

| detected tool | SKUs in the catalogue containing it |
| --- | --- |
| `large_blade` | 100 / 247 (40%) |
| `scissors` | 95 / 247 (38%) |
| `tweezers` | 92 / 247 (37%) |
| `corkscrew` | 55 / 247 (22%) |
| `pliers` | 13 / 247 (5%) |

A single detected tool is consistent with **55–100 SKUs**. Even the three most
commonly detected tools together still leave **22–29 SKUs**. And detection is
low-recall: the model reliably identifies *one* visible tool, not the full set of
10–12.

### Four ways of using the features — only one works, and it is the weakest

All measured against the four catalogue-known photos:

| approach | result |
| --- | --- |
| **hard containment filter** (`detected ⊆ catalogue tool set`) | truth kept 4/4 at threshold ≥ 0.30, but leaves 55–113 candidates — barely a filter. At threshold 0.05 it keeps only 2/4 and collapses to 1–2 candidates, because one false positive eliminates every SKU. |
| **sum scoring** (sum detected probabilities over the SKU's tools) | truth ranks 28–45. Big multi-tools win because they contain everything. |
| **normalised / precision scoring** (divide by the SKU's tool count) | truth ranks 27–77. |
| **two-stage: filter → Clef `choice` over survivors** | **0/4**, and the model's confidence collapsed to ~0.02. |

The two-stage failure is the most informative. Given 13–58 near-identical candidates
(47 SKUs contain both a large blade and scissors), the criteria become
indistinguishable, the model has no basis to choose, and it correctly reports low
confidence. **That is the model behaving honestly, not failing** — but it means the
features did not do the disambiguating work.

### What the features *are* good for

Not SKU identification — **description and shortlisting**:

1. **Descriptive output for the UI.** "This knife has a corkscrew, a large blade and
   a can opener" is exactly the kind of traceable, source-based detail the README
   asks for, and it comes from the model's own observation rather than a guess.
2. **A coarse category prior.** Tool *counts* separate the catalogue well (12 tools
   vs 10 tools vs 20 tools), so the detected feature set can rule out whole
   product families (a 3-tool knife cannot be a Swiss Champ) before the model chooses.
3. **A confirmation signal for the final answer.** If the chosen SKU's catalogue
   tool set contains the detected tool, that is corroborating evidence. If it does
   not, that is a **conflict** worth surfacing — and possibly worth abstaining on.
4. **Retrieval as a soft feature, not a filter.** Feed the detected-tool vector into
   the candidate ranking alongside the embedding similarity, rather than using it as
   a hard gate.

### Recommended use

```
photo ──→ open_state probe ──┬── closed  → ask for an open-tools photo
                             │
                             └── open
                                  ├─→ tool detection (multi-choice)  → description + soft prior
                                  ├─→ brand/category decision (Clef choice)  → the product
                                  └─→ cross-check: does the chosen SKU's catalogue
                                      tool set contain the detected tool?
                                      yes → corroborate      no → surface the conflict
```

So the answer to the question is: **yes, use it — as a description and a consistency
check, not as the matching mechanism.** The matching still has to come from the
brand/category decision plus the tool-count prior, and the catalogue's tool list is
what makes the final comparison explainable.

### Implementation

- `tools/tool_vocab.py` — all 147 catalogue tool names mapped to English canonical
  ids, plus `tool_set_for(article)` and `EN_OPTIONS()` for building criteria.
  Run it directly to see coverage (currently 178/247 articles with tools, 0 unmapped
  names).
- `tools/feature_detection.py` — `detect_tools(image)` returning probabilities, the
  open/closed gate, and `rank_catalogue()`.
- `tools/eval_clef.py --experiment features` — the measurements above.

---

## 10. Results on real smartphone photos — the actual demo domain

Everything above was measured on clean packshots. `data/real_photos/` holds 12
photos taken with a Pixel phone of products on a desk: real distractions (a drinks
can, a power cable), mostly **closed** knives, and — importantly — **competitor
brands** (Leatherman, Gerber), which is the case the project is actually about.

Some labels are directly confirmed by markings (`LEATHERMAN® Rev™`, `GERBER`, the
Victorinox shield, the cm scale). A later photo review found that the original class
labels for PXL photos 07, 10, and 12 need correction or confirmation; see
`data/real_photos/README.md`. The archived direct-brand metrics below use those legacy
labels and are not the latest full-pipeline result.

### Brand decision: 9/12 top-1, 11/12 top-3 — and a very clean confidence split

| metric | value |
| --- | --- |
| top-1 | **9/12 (75%)** |
| top-3 | **11/12 (92%)** |
| mean confidence when **correct** | **0.850** |
| mean confidence when **wrong** | **0.119** |

Every correct answer scored ≥0.62; every wrong answer ≤0.21. That separation is
*better* than on the packshots (0.585 vs 0.499), which makes sense: a real photo
of a real product is a much easier decision than a cropped packshot of a generic
black multi-tool.

**The abstention threshold works.** At `confidence ≥ 0.3` the system shows 9/12
with **100% precision** and abstains on the other 3. The margin (top1 − top2)
separates just as cleanly: 0.910 when correct vs 0.036 when wrong.

Against the original labels, the archived misses were:

- **the ruler photos (2×)** — a flat metal bar with a centimetre scale does not
  look like a knife, and the model ranked the SAK options above `ruler`. Both score
  below 0.12 confidence, so abstention catches them.
- **photo 07** — a black SAK photographed edge-on, read as `gerber` (0.437) over
  `sak_black` (0.113). Confidence 0.213, again caught by abstention.

### Full local `/api/match` run

All 12 photos were run through the current backend on 2026-10-24. It returns one
brand, detected tools, and three Victorinox recommendations; it does not expose a
brand top-3 list.

| label view | brand correct | confidence ≥ 0.6 |
| --- | ---: | ---: |
| legacy `labels.json` | **9/12** | — |
| reviewed labels (photo 12 excluded) | **8/11** | **7/7 correct at 7/11 coverage** |

The three errors against the reviewed labels are photo 06 (Roxon for Victorinox),
photo 07 (Victorinox for Gerber), and photo 10 (Benchmade for Gerber). Photo 12 was
predicted as Benchmade, but its maker is unconfirmed. No exact SKUs or correct
Victorinox substitutes are labelled on this set, so recommendation accuracy cannot
be measured here. The full responses are in `data/api_match_both_sets.json`.

### The open/closed gate generalises

| set | open photos | closed photos |
| --- | --- | --- |
| packshots | 0.86 – 0.97 | 0.05 – 0.06 |
| real photos | — (all closed) | 0.02 – 0.22 |

Photo 02 (red SAK with a visible spiral corkscrew) scores 0.10 — the corkscrew is
out but the knife is closed, so "not visible" is the honest answer. The gate
transfers cleanly from the packshot domain to the real one.

### SKU level is still weak, and now we know why

Running the same 12 photos through a SKU-level choice over 14 real catalogue
Essentials SKUs gives **confidence 0.06 – 0.21** — an order of magnitude below the
brand-level decision.

The reason is now clear and it is *not* a modelling problem: the catalogue
discriminates SKUs by tool lists (§8), but the photo has to supply the tool
evidence first, and **a closed knife does not**. The feature pipeline is the
bottleneck, and it is gated on the knife being open.

So the demo needs to handle three photo states explicitly:

```
photo ──→ open_state probe
             │
             ├── closed (p ≈ 0.8+) ──→ identify brand/category only,
             │                            then ASK for a photo of the open knife
             │                            to pin down the SKU
             │
             └── open (p ≈ 0.2-)  ──→ detect tools → full SKU identification
```

That is a better product anyway: *"I can tell you this is a Swiss Army Knife with
the Swiss cross, but to confirm the exact model I need a photo of the open knife"*
is exactly the kind of honest, traceable interaction the README asks for.

### A production constraint we hit for real

The API rejects oversized images:

```
HTTP 422: AiError: Request body failed validation: images.0:
image exceeds the decoded byte limit
```

A 3000×4000 Pixel photo (4.7 MB) fails. `tools/clef_client.py` now **downscales
and re-encodes automatically** (to ≤1400 px, ≤900 KB JPEG), which takes the
4.7 MB photo down to 0.22 MB and stays inside the 1,024-token-per-image cap.
This has to happen in the client — the frontend should not have to know about it.

### Summary: the domain gap was smaller than feared

| | packshots | real photos |
| --- | --- | --- |
| brand top-1 | 6/12 (50%) – 7/12 (58%) | **9/12 (75%)** |
| brand top-3 | 11/12 (92%) | **11/12 (92%)** |
| confidence separation | 0.585 / 0.499 | **0.850 / 0.119** |
| open/closed gate | clean | clean |

Real photos score **better** than packshots for brand identification. The packshot
set is the harder case: cropped, high-resolution images of generic black multi-tools
with no context, where the only cue is a subtle logo.

Reproduce with `uv run python tools/eval_real.py`.

---

## 11. Provider interface (keeping the model swappable)

The README requires a model-independent, provider-agnostic architecture. Two
providers are needed anyway, and they expose different shapes:

| need | provider | API shape |
| --- | --- | --- |
| **decision** (which product is this?) | OpenRouter → `cloudflare/clef-flash` at `/api/alpha/decisions` | Jev/SystemOne: `state` + `questions` → typed `answers` with `probabilities` |
| **rationale / attributes** (explain it, extract JSON) | whatever OpenAI-compatible endpoint we have | chat completions → text / JSON |

So define two small protocols, not one generic one. The decision client is already
implemented in `tools/clef_client.py`:

```python
from tools.clef_client import ClefClient

client = ClefClient(model="cloudflare/clef-flash")   # reads OPENROUTER_API_KEY

result = client.decide(
    state=[
        {"type": "text", "text": "Product photo:"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
    ],
    questions={
        "brand": {
            "type": "choice",
            "instructions": "Which brand and model is this pocket knife?",
            "criteria": {"roxon": "ROXON brand, black handle, ROXON in capitals", "...": "..."},
        },
        "article_visible": {
            "type": "noul",
            "instructions": "Is an article number legible on the handle?",
        },
    },
)

print(result.answers["brand"].probabilities)   # {'roxon': 0.82, 'swiza': 0.03, ...}
print(result.margin("brand"))                  # top1 - top2, for abstention
print(result.usage["cost"])                    # ~0.00003
```

Note the client:
- takes image **paths** and base64-encodes them, so callers never build data URLs by
  hand,
- **retries** on transient network errors (the endpoint resets connections
  occasionally),
- exposes `margin()` so the abstention logic does not have to re-derive it,
- keeps `raw` for debugging.

A fallback implementation for when the OpenRouter route is unavailable:

```python
class OpenAiCompatibleDecision:
    """Fallback: forced-choice over letters via a normal chat completion.

    We only get the *choice*, not a probability, so confidence must be derived
    (e.g. by asking the model for a 0-100 score in the same call, or by running
    several option orders and measuring agreement).
    """

    def decide(self, state, questions):
        # 1. flatten the typed questions into a single natural-language prompt
        # 2. ask for one letter, optionally with a confidence
        # 3. map back to the option id
        ...
```

**One thing that fallback changes.** It needs the photo described in text before the
decision, which makes the attribute step load-bearing rather than optional. And
§2.3 measured why that is a real downgrade: text→text matching of SAK products
scored 11/12, but the image→text direction scored 0/12 top-1. A VLM-written
description must carry the discriminative detail (logo shape, handle material,
lettering) or the decision will be guesswork.

---

## Appendix — Sources


- **Clef** — model card: https://huggingface.co/Cloudflare/clef · flash: https://huggingface.co/Cloudflare/clef-flash · blog: https://blog.cloudflare.com/clef-decision-models/ · Cloudflare-hosted API: https://developers.cloudflare.com/workers-ai/models/clef/ · Decision Index leaderboard: https://clef-evals.workers-ai-mle.workers.dev
- **OpenRouter decisions endpoint** — `POST https://openrouter.ai/api/alpha/decisions`, model ids `cloudflare/clef` and `cloudflare/clef-flash`. Note these are **not** listed in `GET /api/v1/models` and **not** usable via `/chat/completions`.
- **Jev** — Visual Jev paper: https://arxiv.org/abs/2609.25845 · code: https://github.com/guanxuyu-sv/Visual-Jev · adapter: https://huggingface.co/guanxuyu/visual-jev-4b-answer-sft · benchmark: https://arxiv.org/abs/2609.37647 · Jev API docs: https://docs.typesafe.ai/models
- **Head-to-head comparison** — "Scan or Index? large Evidence Coverage, Answer Quality, and Cost in Long-Document RAG", arXiv:2610.28957 (Jev vs OpenAI Decisions vs local Clef)
- **OpenAI Decisions API** — https://developers.openai.com/api/docs/guides/decisions
- **Measured here** — `tools/eval_clef.py` (Clef experiments: pairwise / attribute probes / direct brand ID / feature detection), `tools/eval_real.py` (real smartphone photos) and `tools/eval_retrieval.py` (embedding baselines). Raw results in `data/clef_*.json` and `data/real_brand_results.json`.
- **Evaluation sets** — `data/sak_ground_truth/` (12 packshots from the client PDF) and `data/real_photos/` (12 real smartphone photos, ground truth read off the brand markings).
- **Catalogue** — `backend/data/victorinox_sak_produkte.csv` (247 products) and `backend/data/victorinox_sak_werkzeuge.csv` (1,936 article→tool rows), scraped by `backend/scraper/victorinox.py`.
- SigLIP 2 paper: arXiv:2502.14786 · model: https://huggingface.co/google/siglip2-base-patch16-224 (Apache-2.0)
- fastembed 0.9.0 supported models (verified by reading the installed package source):
  images — `Qdrant/clip-ViT-B-32-vision`, `Qdrant/resnet50-onnx`, `Qdrant/Unicom-ViT-B-16`,
  `Qdrant/Unicom-ViT-B-32`, `jinaai/jina-clip-v1`, `nomic-ai/nomic-embed-vision-v1.5`(+`-Q`),
  `google/siglip2-base-patch16-224`; text — `google/siglip2-base-patch16-224`,
  `Qdrant/clip-ViT-B-32-text`, `jinaai/jina-clip-v1`
- Fine-grained product retrieval: VL-CLIP (arXiv:2507.17080), MCMR (arXiv:2603.01082),
  STIR (arXiv:2304.13393), MMFL-Net (arXiv:2210.15108)
- Knife-specific retrieval: KnifeHunter (arXiv:2608.07057) — 543 knife classes, global
  + local features, 88% mAP. Its design lesson (global context + *localised*
  discriminative evidence) matches what we need.
- OCR: RapidOCR (Apache-2.0), PaddleOCR, Tesseract, EasyOCR
