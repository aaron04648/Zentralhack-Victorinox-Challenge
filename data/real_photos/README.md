# Real smartphone photos (12)

The actual demo domain, as opposed to the clean packshots in
[`../sak_ground_truth/`](../sak_ground_truth/).

12 photos taken with a Pixel phone (3000×4000) of products lying on a white desk.
The scene includes real distractions — a drinks can, a power cable, a yellow
plastic strip — and the products are mostly **closed**, which is exactly the case
the app has to handle.

## Ground truth

Established by **reading the markings directly off the photos**, not from a model
prediction. Three of the products carry legible brand marks:

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
| `07_..._070713477.jpg` | `sak_black` | Victorinox SAK, black, closed, side view |
| `08_..._070734192.jpg` | `ruler` | Victorinox metal ruler / cm scale |
| `09_..._070739736.jpg` | `ruler` | Victorinox metal ruler / cm scale (marked VICTORINOX) |
| `10_..._070745178.jpg` | `sak_black` | Victorinox SAK, black, closed |
| `11_..._070749922.jpg` | `sak_red` | Victorinox SAK, red, closed |
| `12_..._070755770.jpg` | `sak_black` | Victorinox SAK, black textured, closed |

Distribution: 4× `sak_red`, 4× `sak_black`, 2× `ruler`, 1× `leatherman`, 1× `gerber`.

Note this set contains **competitor brands** (Leatherman, Gerber) — the case the
project actually cares about — whereas `data/sak_ground_truth/` is mostly
competitors too but with clean backgrounds.

## Results

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

## Reproducing

```bash
uv run python tools/eval_real.py              # brand decision + open/closed gate
uv run python tools/eval_real.py --experiment brand
```

Raw output: `../real_brand_results.json`.
