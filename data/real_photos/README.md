# Real smartphone photos (12)

The actual demo domain, as opposed to the clean packshots in
[`../sak_ground_truth/`](../sak_ground_truth/).

12 photos taken with a Pixel phone (3000×4000) of products lying on a white desk.
The scene includes real distractions — a drinks can, a power cable, a yellow
plastic strip — and the products are mostly **closed**, which is exactly the case
the app has to handle.

## Ground truth

The original labels were assembled by inspecting the photos. A review for the latest
full-pipeline run found three conflicts: photos 07 and 10 show Gerber marks, while
photo 12 is a one-hand locking folder rather than a Victorinox SAK; its maker is not
confirmed. The table distinguishes these reviewed labels from the legacy classes in
`labels.json`.

- photo 01 — engraved `LEATHERMAN® Rev™`
- photo 03 — engraved `GERBER`
- photos 04/05 — the Victorinox Swiss cross shield

| file | class | what it is |
| --- | --- | --- |
| `01_..._070613768.jpg` | `leatherman` | Leatherman Rev, stainless |
| `02_..._070633052.jpg` | `sak_red` | Victorinox SAK, red, spiral corkscrew visible |
| `03_..._070643393.jpg` | `gerber` | Gerber multi-tool |
| `04_..._070652715.MP.jpg` | `sak_red` | Victorinox SAK, red + Swiss cross shield |
| `05_..._070657633.jpg` | `sak_red` | Victorinox SAK, red + Swiss cross shield |
| `06_..._070707946.jpg` | `sak_black` | Victorinox SAK, black carbon scales, closed |
| `07_..._070713477.jpg` | `gerber` (reviewed) | Black folding knife with Gerber shield mark; legacy label was `sak_black` |
| `08_..._070734192.jpg` | `ruler` | Victorinox metal ruler / cm scale |
| `09_..._070739736.jpg` | `ruler` | Victorinox metal ruler / cm scale (marked VICTORINOX) |
| `10_..._070745178.jpg` | `gerber` (reviewed) | Gerber FAST DRAW folding knife; legacy label was `sak_black` |
| `11_..._070749922.jpg` | `sak_red` | Victorinox SAK, red, closed |
| `12_..._070755770.jpg` | `other / unconfirmed` | Black locking folder; visible mark is too small to confirm the maker; legacy label was `sak_black` |

The legacy labels contain 4× `sak_red`, 4× `sak_black`, 2× `ruler`, 1× `leatherman`,
and 1× `gerber`. The reviewed labels move photos 07/10 to Gerber and photo 12 to an
unconfirmed other brand.

Note this set contains **competitor brands** (Leatherman, Gerber) — the case the
project actually cares about — whereas `data/sak_ground_truth/` is mostly
competitors too but with clean backgrounds.

## Archived direct Clef result (legacy labels)

Brand decision with `cloudflare/clef-flash`, five options covering all classes:

| metric | value |
| --- | --- |
| top-1 | **9/12 (75%)** |
| top-3 | **11/12 (92%)** |
| mean confidence when correct | 0.850 |
| mean confidence when wrong | **0.119** |

The confidence separation is very clean: every correct answer scored ≥0.62, every
wrong answer scored ≤0.21. At `confidence ≥ 0.3` the system shows 9/12 with
**100% precision** and abstains on the other 3.

The two misses are informative:

- **the ruler photos (2×)** — a flat metal bar with a cm scale does not look like a
  knife, and the model ranked the SAK options above `ruler` (0.017–0.238). Both
  score below 0.12 confidence, so the abstention threshold catches them.
- **photo 07** — a black SAK seen edge-on, read as `gerber` (0.437) over
  `sak_black` (0.113). Confidence 0.213, so again caught by abstention.

This is the archived standalone experiment against the original `labels.json`
classes. It is not the full app pipeline, and photos 07, 10, and 12 now have label
caveats above; use the latest full API figures below for the current labels.

## The open/closed gate generalises

`open_state` separates cleanly on both sets:

| set | open photos | closed photos |
| --- | --- | --- |
| packshots | 0.86 – 0.97 | 0.05 – 0.06 |
| real photos | — (all closed) | 0.02 – 0.22 |

Photo 02 (red SAK with a visible spiral corkscrew) scores 0.10 — the corkscrew is
out but the knife is closed, so "not visible" is the honest answer.

## SKU level is still weak

Running the same 12 photos through a SKU-level choice over 14 real catalogue
Essentials SKUs gives **confidence 0.06 – 0.21** — an order of magnitude below the
brand-level decision. The model cannot tell SKUs apart from a closed knife in a
desk photo. This matches the packshot finding: the catalogue's tool lists
discriminate, but the *photo* has to supply the tool evidence first, and a closed
knife does not.

## Full local API run (2026-10-24)

All 12 photos were sent through the complete local `/api/match` flow after the
production brand-prompt update:

| scoring view | brand accuracy |
| --- | --- |
| original labels in `labels.json` | **9/12** |
| reviewed labels, excluding photo 12 (maker unconfirmed) | **8/11** |
| reviewed known labels at confidence ≥ 0.6 | **7/7 correct, 7/11 coverage** |

Errors on the reviewed known labels are photos 06 (Roxon for Victorinox), 07
(Victorinox for Gerber), and 10 (Benchmade for Gerber). Photo 12 was predicted as
Benchmade, but the maker has not been verified. No exact product SKUs or ground-truth
Victorinox replacements are labelled for this photo set, so recommendation accuracy
cannot be scored. Full outputs, including ranked Victorinox recommendations, are in
[`../api_match_both_sets.json`](../api_match_both_sets.json).

The pipeline asked for clarification on 10/12 photos. Two low-confidence brand results
(photos 02 and 12, both below 0.6) did not trigger a clarification, so the tested
confidence cutoff is not yet consistently enforced in the response flow.

## Reproducing

```bash
uv run python tools/eval_real.py              # brand decision + open/closed gate
uv run python tools/eval_real.py --experiment brand
```

Raw output: `../real_brand_results.json`.
