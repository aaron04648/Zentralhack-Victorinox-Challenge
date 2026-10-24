"""Detect which tools are visible in a pocket-knife photo, using the Clef decision model.

This turns a photo into a set of *functional attributes* ("has a saw", "has
scissors"), which is the kind of signal the image embeddings could not extract
(see docs/classification_recommendation.md) but which the catalogue records
exactly.

Measured on the 12 ground-truth photos (docs/classification_recommendation.md §10):

- The **multi-choice** framing (one `choice` question over the tool vocabulary)
  gives **top-1 precision 100%** on the catalogue cases we could score.
- The **independent `noul` probes** are noisier: precision 43-80%, with several
  spurious detections.
- Detection only works when the tools are **open/fanned out**. On a closed knife
  the model correctly reports it cannot see them - which is honest and useful.

Usage:
    from tools.feature_detection import detect_tools
    result = detect_tools("photo.jpg")
    print(result.top_tools, result.detected, result.open_state)

    # score catalogue SKUs against the detected features
    print(result.rank_catalogue())
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.clef_client import ClefClient
from tools.tool_vocab import EN_OPTIONS, TOOL_EN, products, tool_set_for

# Probability above which a tool is considered "detected". Measured on the
# ground-truth set: below ~0.15 the false positives dominate and any
# set-containment filter collapses to zero candidates (see §10 of the
# recommendation doc).
DEFAULT_THRESHOLD = 0.15


@dataclass
class FeatureResult:
    """Outcome of one feature-detection pass."""

    probabilities: dict[str, float] = field(default_factory=dict)
    open_state: float = 0.0
    threshold: float = DEFAULT_THRESHOLD
    model: str = ""

    @property
    def detected(self) -> set[str]:
        """Tools above the detection threshold."""
        return {tool for tool, prob in self.probabilities.items() if prob >= self.threshold}

    @property
    def top_tools(self) -> list[tuple[str, float]]:
        """All tools ordered by probability, best first."""
        return sorted(self.probabilities.items(), key=lambda kv: -kv[1])

    @property
    def tools_are_visible(self) -> bool:
        """False when the knife is closed - detection would be guesswork."""
        return self.open_state >= 0.5

    def rank_catalogue(self) -> list[tuple[str, float, str]]:
        """Catalogue SKUs scored against the detected tools.

        Score is the sum of the detected probability for each tool the SKU
        contains, normalised by the SKU's tool count, so that large multi-tools
        do not automatically win. Returns [(article_number, score, name), ...]
        best first.
        """
        if not self.detected:
            return []
        ranked = []
        for product in products():
            article = product["artikelnummer"]
            features = tool_set_for(article)
            if not features:
                continue
            matched = sum(self.probabilities.get(tool, 0.0) for tool in features)
            score = matched / len(features)
            ranked.append((article, score, product["name"]))
        ranked.sort(key=lambda item: -item[1])
        return ranked


def detect_tools(
    image: str | Path,
    client: ClefClient | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    tools: list[str] | None = None,
) -> FeatureResult:
    """Detect the visible tools on a pocket knife.

    `tools` restricts the vocabulary (defaults to the photo-recognisable subset
    in tools.tool_vocab.TOOL_EN).
    """
    client = client or ClefClient(model="cloudflare/clef-flash")
    options = EN_OPTIONS(tools)

    questions = {
        "tools": {
            "type": "choice",
            "instructions": (
                "Which of these tools are visible among the implements of this "
                "pocket knife? Choose the single best match. If the knife is "
                "closed and no implements are visible, choose the large blade."
            ),
            "criteria": options,
        },
        "open_state": {
            "type": "noul",
            "instructions": (
                "Are the implements of this pocket knife shown OPEN (fanned out, "
                "so several different tools are visible at once)?"
            ),
            "criteria": {
                "true": "the knife is shown open with several tools visible",
                "false": "the knife is closed or only one tool is visible",
            },
        },
    }

    result = client.decide(state=["Product photo:"], questions=questions, images=[image])
    tool_answer = result.answers["tools"]
    open_answer = result.answers["open_state"]
    return FeatureResult(
        probabilities=dict(tool_answer.probabilities),
        open_state=open_answer.noul or 0.0,
        threshold=threshold,
        model=result.model,
    )


def feature_criteria(article_number: str) -> str:
    """English description of a catalogue SKU's tool set, for a `choice` question."""
    product = next(
        (p for p in products() if p["artikelnummer"] == article_number), None
    )
    if product is None:
        return article_number
    features = sorted(tool_set_for(article_number))
    described = ", ".join(TOOL_EN.get(tool, tool) for tool in features)
    return (
        f"{product['name']} — {product['anzahl_werkzeuge']} tools: {described}; "
        f"colours: {product['farben']}"
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    result = detect_tools(sys.argv[1])
    print(f"model      : {result.model}")
    print(f"open state : {result.open_state:.3f}  (tools visible: {result.tools_are_visible})")
    print(f"detected   : {sorted(result.detected)}")
    print("\ntop tools:")
    for tool, prob in result.top_tools[:8]:
        print(f"  {tool:<16} {prob:.3f}")
    print("\ntop catalogue SKUs:")
    for article, score, name in result.rank_catalogue()[:10]:
        print(f"  {article:<14} {score:.3f}  {name[:40]}")
