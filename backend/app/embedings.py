"""Text-Embeddings (fastembed): Verwendungszweck des Kunden <-> Kategorien und Produkte.

Das Modell ist mehrsprachig, weil Eingaben und Katalog deutsch sind (das fastembed-Standardmodell
bge-small-en versteht nur Englisch). Es wird beim ersten Aufruf einmal geladen (~220 MB, Cache in
data/.fastembed) und bleibt dann im Speicher.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

MODELL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE = Path(__file__).resolve().parent.parent / "data" / ".fastembed"

CATEGORIES = [
    "Outdoor, Fischen, Jagen,",
    "Everyday, Freizeit, Wandern, Küche, ",
    "Sport, Fitness, Saling",
    "Crafts, Werkzeug, Baustelle",
]


@lru_cache
def setup_embedding_model():
    return TextEmbedding(MODELL, cache_dir=str(CACHE))


def cosine_similarity(v1, v2):
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


@lru_cache
def generate_category_embeddings():
    return list(setup_embedding_model().embed(CATEGORIES))


def produkt_text(row):
    """Was ein Produkt kann, als Satz für das Embedding (Felder als Listen, siehe app/katalog.py)."""
    teile = [row["name"], ", ".join(row.get("kategorien") or ()), ", ".join(row.get("unterkategorien") or ())]
    if row.get("werkzeuge"):
        teile.append("Werkzeuge: " + ", ".join(row["werkzeuge"]).replace(" | ", ", "))
    return ". ".join(t for t in teile if t)


@lru_cache
def _produkt_matrix(texte):
    vektoren = np.array(list(setup_embedding_model().embed(list(texte))))
    return vektoren / np.linalg.norm(vektoren, axis=1, keepdims=True)


def verwendung_passung(verwendung, rows):
    """Wie gut passt jedes Produkt zum Verwendungszweck? -> {artikelnummer: z-Wert}

    z-Wert = Kosinus-Ähnlichkeit, standardisiert über alle Produkte (0 = durchschnittlich,
    +1 = eine Standardabweichung besser), damit die Stärke unabhängig vom Modell ist.
    """
    matrix = _produkt_matrix(tuple(produkt_text(r) for r in rows))
    frage = np.array(list(setup_embedding_model().embed([verwendung]))[0])
    aehnlich = matrix @ (frage / np.linalg.norm(frage))
    z = (aehnlich - aehnlich.mean()) / (aehnlich.std() or 1.0)
    return {r["artikelnummer"]: float(w) for r, w in zip(rows, z)}
