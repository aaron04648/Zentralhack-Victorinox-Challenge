"""Leave-one-out evaluation harness for SAK image retrieval.

Measures how well an image embedding separates the 12 ground-truth SAK photos by
class. Run it whenever you change the embedding model or the retrieval strategy.

Usage:
    uv run python -m tools.eval_retrieval                    # all fastembed image models
    uv run python -m tools.eval_retrieval --model Qdrant/clip-ViT-B-32-vision
    uv run python -m tools.eval_retrieval --multicrop        # region max-similarity
    uv run python -m tools.eval_retrieval --tagnames

The key metric is `gap` = mean within-class cosine - mean between-class cosine.
A negative gap means the encoder is worse than chance at separating classes.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sak_ground_truth"

# Short class keys for readable output.
CLASS_KEYS = {
    "Roxon": "ROXON",
    "The Helton": "HELTON",
    "Swiza": "SWIZA",
    "Spartan": "SPARTAN",
    "Synergy": "SYNERGY",
}


def load_dataset() -> tuple[list[Path], list[str]]:
    """Return (image_paths, class_keys) for the ground-truth set."""
    labels = json.loads((DATA_DIR / "labels.json").read_text())
    paths: list[Path] = []
    keys: list[str] = []
    for row in labels:
        name = f"p{row['page']}_{row['xobj']}_obj{row['obj']}.png"
        path = DATA_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"missing ground-truth image: {path}")
        label = row["label"]
        key = next((v for k, v in CLASS_KEYS.items() if k in label), label[:12])
        paths.append(path)
        keys.append(key)
    return paths, keys


def class_separation(embeddings: np.ndarray, keys: list[str]) -> dict:
    """Compute top-1/top-3 accuracy and the within-vs-between similarity gap."""
    sim = embeddings @ embeddings.T
    np.fill_diagonal(sim, -9.0)

    n = len(keys)
    top1 = sum(keys[j] == keys[i] for i, j in enumerate(sim.argmax(1)))
    top3 = sum(
        keys[i] in [keys[j] for j in np.argsort(-sim[i])[:3]] for i in range(n)
    )

    groups: dict[str, list[int]] = defaultdict(list)
    for i, key in enumerate(keys):
        groups[key].append(i)

    within: list[float] = []
    between: list[float] = []
    for key, idx in groups.items():
        if len(idx) > 1:
            block = sim[np.ix_(idx, idx)]
            within.extend(block[np.triu_indices(len(idx), 1)].tolist())
        others = [j for other_key, jj in groups.items() if other_key != key for j in jj]
        for i in idx:
            between.extend(sim[i, j] for j in others)

    return {
        "top1": top1,
        "top3": top3,
        "n": n,
        "within": float(np.mean(within)),
        "between": float(np.mean(between)),
        "gap": float(np.mean(within) - np.mean(between)),
    }


def embed_with_fastembed(model_name: str, paths: list[Path], multicrop: bool) -> np.ndarray:
    from fastembed import ImageEmbedding
    from PIL import Image

    model = ImageEmbedding(model_name=model_name)

    def crops(path: Path) -> list[Image.Image]:
        image = Image.open(path).convert("RGB")
        width, height = image.size
        return [
            image,
            image.crop((0, 0, width // 2, height)),
            image.crop((width // 2, 0, width, height)),
            image.crop((0, 0, width, height // 2)),
            image.crop((0, height // 2, width, height)),
        ]

    if not multicrop:
        return np.array(list(model.embed([str(p) for p in paths])))

    # Region max-similarity: compare every crop pair, keep the best match.
    per_image = []
    for path in paths:
        vectors = list(model.embed([crop for crop in crops(path)]))
        per_image.append(np.array(vectors))
    stack = np.array(per_image)
    n = len(paths)
    sim = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            sim[i, j] = (stack[i] @ stack[j].T).max()
    np.fill_diagonal(sim, -9.0)
    return sim


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="fastembed image model name")
    parser.add_argument("--multicrop", action="store_true", help="region max-similarity")
    parser.add_argument("--tagnames", action="store_true", help="print per-image predictions")
    args = parser.parse_args()

    paths, keys = load_dataset()
    models = (
        [args.model]
        if args.model
        else [
            "google/siglip2-base-patch16-224",
            "Qdrant/clip-ViT-B-32-vision",
            "Qdrant/Unicom-ViT-B-16",
            "nomic-ai/nomic-embed-vision-v1.5",
            "jinaai/jina-clip-v1",
            "Qdrant/resnet50-onnx",
        ]
    )

    print(f"{'model':<44} {'top1':>7} {'top3':>7} {'within':>8} {'between':>8} {'gap':>8}")
    print("-" * 88)
    for model_name in models:
        embeddings = embed_with_fastembed(model_name, paths, args.multicrop)
        if args.multicrop:
            # `embed_with_fastembed` already returns a similarity matrix for multicrop.
            sim = embeddings
            np.fill_diagonal(sim, -9.0)
            keys_idx = list(range(len(keys)))
            top1 = sum(keys[sim[i].argmax()] == keys[i] for i in keys_idx)
            top3 = sum(
                keys[i] in [keys[j] for j in np.argsort(-sim[i])[:3]] for i in keys_idx
            )
            groups: dict[str, list[int]] = defaultdict(list)
            for i, key in enumerate(keys):
                groups[key].append(i)
            within, between = [], []
            for key, idx in groups.items():
                if len(idx) > 1:
                    block = sim[np.ix_(idx, idx)]
                    within.extend(block[np.triu_indices(len(idx), 1)].tolist())
                others = [j for k2, jj in groups.items() if k2 != key for j in jj]
                for i in idx:
                    between.extend(sim[i, j] for j in others)
            result = {
                "top1": top1,
                "top3": top3,
                "n": len(keys),
                "within": float(np.mean(within)),
                "between": float(np.mean(between)),
                "gap": float(np.mean(within) - np.mean(between)),
            }
        else:
            result = class_separation(embeddings, keys)

        print(
            f"{model_name:<44} {result['top1']:>3}/{result['n']:<3} "
            f"{result['top3']:>3}/{result['n']:<3} {result['within']:>8.3f} "
            f"{result['between']:>8.3f} {result['gap']:>+8.3f}"
        )

        if args.tagnames:
            sim = embeddings if args.multicrop else embeddings @ embeddings.T
            for i, path in enumerate(paths):
                order = np.argsort(-sim[i])[:3]
                print(
                    f"    {path.stem:<22} truth={keys[i]:<9} "
                    f"top3={[keys[j] for j in order]}"
                )


if __name__ == "__main__":
    main()
