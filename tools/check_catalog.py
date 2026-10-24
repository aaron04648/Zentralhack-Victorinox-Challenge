"""Prüft die Produktdaten in backend/data/ (victorinox_produkte.json + cross_references.json).

- Struktur (Pydantic-Modelle in backend/app/katalog.py)
- doppelte IDs, Verweise auf unbekannte Produkte, Ziele, die kein Taschenmesser sind
- Werkzeugnamen der Konkurrenzprodukte gegen das Vokabular in tools/tool_vocab.py

Usage:
    uv run python tools/check_catalog.py   # Exit-Code 1 bei Fehlern
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / "backend")]

from pydantic import ValidationError  # noqa: E402

from app.katalog import load_cross_references, load_konkurrenz, load_pocket_knives, load_products, pruefe  # noqa: E402
from tools.tool_vocab import canonical_tool  # noqa: E402


def main() -> int:
    try:
        fehler = pruefe(ist_werkzeug=lambda name: canonical_tool(name) is not None)
    except ValidationError as e:
        print(f"Strukturfehler:\n{e}")
        return 1

    if fehler:
        print(f"{len(fehler)} Fehler:")
        for f in fehler:
            print(f"  - {f}")
        return 1

    refs = load_cross_references()
    verifiziert = sum(1 for r in refs if r.status.value == "verifiziert")
    print(
        f"OK: {len(load_products())} Victorinox-Produkte ({len(load_pocket_knives())} Taschenmesser), "
        f"{len(load_konkurrenz())} Konkurrenzprodukte, {len(refs)} Cross-References ({verifiziert} verifiziert)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
