"""Client for the Cloudflare Clef decision model via OpenRouter.

Clef is a decision model: it takes a `state` plus a schema of typed questions and
returns a probability for every allowed option of every question in one forward pass.
It never generates free-form text, so there is no output parsing.

OpenRouter exposes it on a dedicated endpoint, not on /chat/completions:

    POST https://openrouter.ai/api/alpha/decisions

Calling /chat/completions with a decisions model returns HTTP 400:
    "cloudflare/clef is a decisions model and cannot be used with the
     chat/completions endpoint. Use the /api/alpha/decisions endpoint instead."

Images are NOT passed in a top-level `images` field (also HTTP 400). They go into
the `state` array as OpenAI-style content parts:

    "state": [
        {"type": "text", "text": "..."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]
"""

from __future__ import annotations

import base64
import mimetypes
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


@dataclass
class Answer:
    """One answer. `probabilities` maps option id -> probability."""

    type: str
    choice: str | None = None
    confidence: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    noul: float | None = None
    score: float | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Answer":
        return cls(
            type=payload.get("type", ""),
            choice=payload.get("choice"),
            confidence=payload.get("confidence"),
            probabilities=payload.get("probabilities") or {},
            noul=payload.get("noul"),
            score=payload.get("score"),
        )


@dataclass
class DecisionResult:
    model: str
    answers: dict[str, Answer]
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def probability(self, question_id: str, option_id: str) -> float:
        answer = self.answers.get(question_id)
        if answer is None:
            return 0.0
        return answer.probabilities.get(option_id, 0.0)

    def margin(self, question_id: str) -> float:
        """Gap between the top two options. Use this for abstention."""
        answer = self.answers.get(question_id)
        if answer is None or len(answer.probabilities) < 2:
            return 0.0
        values = sorted(answer.probabilities.values(), reverse=True)
        return values[0] - values[1]


def _data_url(path: str | Path) -> str:
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"


def _load_dotenv() -> None:
    """Load OPENROUTER_API_KEY from a .env file at the repo root, if present.

    Keeps the key out of the shell environment so the scripts work from a clean
    checkout. An already-set environment variable always wins.
    """
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class ClefClient:
    """Thin wrapper over the OpenRouter decisions endpoint.

    Usage:
        client = ClefClient(api_key=os.environ["OPENROUTER_API_KEY"])
        result = client.decide(
            state=["Photo:", {"type": "image_url", "image_url": {"url": _data_url(p)}}],
            questions={
                "brand": {
                    "type": "choice",
                    "instructions": "Which brand is this?",
                    "criteria": {"swiza": "shield logo", "victorinox": "Swiss cross"},
                }
            },
        )
        print(result.answers["brand"].probabilities)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "cloudflare/clef-flash",
        timeout: float = 180.0,
        max_retries: int = 3,
        app_url: str = "https://localhost",
        app_title: str = "victorinox-product-match",
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            _load_dotenv()
            self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "No OpenRouter API key. Set OPENROUTER_API_KEY, add it to .env "
                "at the repo root (see .env.example), or pass api_key=."
            )
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": app_url,
            "X-Title": app_title,
        }

    def decide(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: dict[str, Any],
        images: list[str | Path] | None = None,
    ) -> DecisionResult:
        """Run one decision request.

        `state` may be a string, a dict, or a list of content parts. If `images` is
        given, they are appended to the state as image content parts.
        """
        if images:
            parts: list[Any] = state if isinstance(state, list) else [{"type": "text", "text": str(state)}]
            for image in images:
                parts.append({"type": "image_url", "image_url": {"url": _data_url(image)}})
            state = parts

        payload = {"model": self.model, "state": state, "questions": questions}
        last_error: Exception | None = None
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = client.post(
                        OPENROUTER_DECISIONS_URL, json=payload, headers=self.headers
                    )
                    break
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    # Transient: connection reset / timeout. Back off and retry.
                    last_error = exc
                    if attempt == self.max_retries:
                        raise
                    time.sleep(2 ** attempt)
        if response.status_code != 200:
            raise RuntimeError(
                f"Clef decision failed ({response.status_code}): {response.text[:500]}"
            )
        data = response.json()
        answers = {
            qid: Answer.from_payload(payload_)
            for qid, payload_ in (data.get("answers") or {}).items()
        }
        return DecisionResult(
            model=data.get("model", self.model),
            answers=answers,
            usage=data.get("usage") or {},
            raw=data,
        )
