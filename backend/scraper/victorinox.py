"""Scraper für die Swiss Army Knife & Tools Produkte von victorinox.com (de-CH).

Die Produktlisten der Webseite werden clientseitig über die Frontastic-API
nachgeladen. Dieser Scraper ruft dieselben Endpunkte direkt auf und schreibt
data/victorinox_produkte.json mit einem Eintrag pro Produkt (Format: app/katalog.py,
Modell `Produkt`). Ein Produkt kann in mehreren Kategorien vorkommen ("kategorien").

Die Werkzeuge eines Messers stehen nur auf der Produktseite (Merkmal
"Hauptfunktion") und landen als Liste "werkzeuge" im Produkt. Von dort kommen
auch Masse, Material und alle Galeriebilder (Trainingsdaten).

Die Datei wird komplett neu geschrieben: nie von Hand bearbeiten. Konkurrenzprodukte
und Zuordnungen gehören in data/cross_references.json.

Aufruf:  python -m scraper.victorinox [ausgabe.json]
"""

import json
from datetime import date
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://b2cstore-victorinox.frontastic.live/frontastic/data-source"
SITE = "https://www.victorinox.com/de-CH"
PAGE_SIZE = 30
CAROUSEL_LIMIT = 200  # Maximum der API
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Frontastic-Locale": "de_CH",
    "User-Agent": "Mozilla/5.0 (ZentralHack scraper)",
}
PAGE_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/130.0 (ZentralHack scraper)"}
PAGE_WORKERS = 4
# Merkmale der Produktseite: Spalte -> Code-Endung des Merkmals
FEATURES = {
    "werkzeuge": "class_sak_functions.sak_main_function",
    "anzahl_funktionen": "base_sales_info.base_no_features",
    "laenge_mm": "base_size.base_length",
    "breite_mm": "base_size.base_width",
    "hoehe_mm": "base_size.base_height",
    "gewicht_g": "base_size.base_weight_net",
    "material": "sak_material.sak_scale_material",
    "feststellbar": "sak_functions.sak_lockable",
    "einhandklinge": "sak_functions.sak_onehand",
}
TOOLS_SEPARATOR = " / "  # wie auf der Webseite

# Jede Kategorie besteht aus Quellen: (Typ, ID, Unterkategorie).
# "grid" = vollständige Produktliste einer CMS-Seite, "list" = Shop-Kategorie,
# "carousel" = Produktgruppe auf der Kategorieseite (liefert die Unterkategorie).
CATEGORIES = {
    "Everyday": {
        "page": "/de-CH/Pocket-Knives-for-Everyday-Use/cms/sak-everyday-all-products/",
        "sources": [
            ("grid", "SAK_Everyday_all_knives", None),
            ("carousel", "SAK_Everyday Essentials", "Essentials"),
            ("carousel", "SAK_Everyday Personal Care", "Personal Care"),
            ("carousel", "SAK_Everyday Food and Drink", "Food and Drink"),
        ],
    },
    "Outdoor & Sports": {
        "page": "/de-CH/Pocket-Knives-for-Outdoor-and-Sports/cms/sak-outdoor-and-sports-all-products/",
        "sources": [
            ("grid", "SAK_OutdoorSports_all_knives", None),
            ("carousel", "SAK_OutdoorSports Outdoor", "Outdoor"),
            ("carousel", "SAK_OutdoorSports Sports", "Sports"),
        ],
    },
    "Trades & Crafts": {
        "page": "/de-CH/Pocket-Knives-for-Trades-and-Crafts/cms/sak-trades-and-crafts-all-products/",
        "sources": [
            ("grid", "SAK_TradesCrafts_all_knives", None),
            ("carousel", "sak-trades-and-crafts TradesCrafts", "Trades & Crafts"),
            ("carousel", "sak-trades-and-crafts Gardening", "Gardening"),
        ],
    },
    "Accessoires": {
        "page": "/de-CH/Pocket-Knife-Accessories/cms/sak-accessories/",
        "sources": [
            ("carousel", "SAK_Accessories Pouches", "Etuis"),
            ("carousel", "SAK_Accessories ChainsParacords", "Ketten & Paracords"),
            ("carousel", "SAK_Accessories Knife Care", "Messerpflege"),
            ("carousel", "SAK_Accessories Books", "Bücher"),
        ],
    },
    "Swiss Tools": {
        "page": "/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Swiss-Tools/c/SAK_SwissTool/",
        "sources": [("list", "SAK_SwissTool", None)],
    },
    "Personalisieren": {
        "page": "/de-CH/Personalizable-Swiss-Army-Knives/cms/personalizable-swiss-army-knives/",
        "sources": [("grid", "personalizable-swiss-army-knives", None)],
    },
}


def fetch(url, headers):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.read().decode("utf-8")
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def get_json(endpoint, params):
    payload = json.loads(fetch(f"{API}/{endpoint}?{urllib.parse.urlencode(params)}", HEADERS))
    payload = payload["dataSourcePayload"]
    if not payload.get("ok"):
        raise RuntimeError(f"{endpoint} {params}: {payload.get('errors')}")
    return payload["data"]


def fetch_paged(endpoint, params):
    docs, start = [], 0
    while True:
        data = get_json(endpoint, {**params, "maxResults": PAGE_SIZE, "startFrom": start})
        response = data["response"]
        docs += response["docs"]
        start += PAGE_SIZE
        if start >= response["numFound"] or not response["docs"]:
            return docs


def fetch_source(kind, component_id, page):
    common = {"isPreviewMode": "false", "pagePath": page}
    if kind == "grid":
        return fetch_paged("products/grid/dynamic", {**common, "componentId": component_id})
    if kind == "list":
        return fetch_paged("products/list", {**common, "q": component_id, "searchType": "category"})
    data = get_json(
        "products/carousel",
        {**common, "componentId": component_id, "limit": CAROUSEL_LIMIT,
         "isConnectedToCart": "false", "isConnectedToPageId": "false"},
    )
    # Karussell-Einträge sind {"type": "PRODUCT"|"BANNER", "element": {...}}
    docs = [d["element"] for d in data["response"]["docs"] if d.get("type") == "PRODUCT"]
    if len(data["response"]["docs"]) >= CAROUSEL_LIMIT:
        print(f"  WARNUNG: {component_id} hat das Limit von {CAROUSEL_LIMIT} erreicht", file=sys.stderr)
    return docs


def collect_features(node, found):
    """Alle Klassifikationsmerkmale {code: values}; das erste Vorkommen gewinnt."""
    if isinstance(node, dict):
        code = node.get("code")
        if isinstance(code, str) and isinstance(node.get("values"), list):
            found.setdefault(code, node["values"])
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return found
    for child in children:
        collect_features(child, found)
    return found


def find_gallery(node):
    if isinstance(node, dict):
        if isinstance(node.get("galleryImages"), list):
            return [image_url(img) for img in node["galleryImages"] if image_url(img)]
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return None
    for child in children:
        found = find_gallery(child)
        if found is not None:
            return found
    return None


def fetch_details(url):
    """Werkzeuge, Masse und Galeriebilder von der Produktseite (Next.js-Daten)."""
    details = {"werkzeuge": [], "galerie": []}
    if not url:
        return details
    html = fetch(url, PAGE_HEADERS)
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return details
    data = json.loads(match.group(1))
    features = collect_features(data, {})
    for column, suffix in FEATURES.items():
        values = next((v for code, v in features.items() if code.endswith(suffix)), [])
        values = [v.replace("\xa0", " ").strip() for v in values if v and v.strip()]
        details[column] = values if column == "werkzeuge" else ", ".join(values)
    details["galerie"] = find_gallery(data) or []
    return details


def image_url(image):
    sources = ((image or {}).get("default") or {}).get("sources") or []
    return sources[0] if sources else ""


def to_row(product):
    variants = product.get("variants") or []
    price = product.get("price") or {}
    sub = product.get("subCategory") or {}
    colors = [
        q["value"] for v in variants for q in (v.get("qualifiers") or [])
        if q.get("type") == "color" and q.get("value")
    ]
    return {
        "artikelnummer": product["id"],
        "name": product["name"].replace("\xa0", " ").strip(),
        "shop_kategorie": sub.get("name") or "",
        "preis_chf": price.get("value") or "",
        "lagerstatus": (product.get("stock") or {}).get("stockLevelStatus", ""),
        "anzahl_varianten": len(variants),
        "varianten_artikelnummern": ", ".join(v["productCode"] for v in variants if v.get("productCode")),
        "farben": ", ".join(dict.fromkeys(colors)),
        "url": f"{SITE}{product['seoPath']}/p/{product['id']}/" if product.get("seoPath") else "",
        "bild_url": image_url(product.get("primaryImage")),
    }


def scrape():
    products = {}     # artikelnummer -> Zeile
    membership = {}   # artikelnummer -> {Kategorie: set(Unterkategorien)}

    for category, cfg in CATEGORIES.items():
        before = sum(1 for m in membership.values() if category in m)
        for kind, component_id, subcategory in cfg["sources"]:
            docs = fetch_source(kind, component_id, cfg["page"])
            print(f"  {category:17} {kind:8} {component_id:40} {len(docs):4} Produkte", file=sys.stderr)
            for doc in docs:
                product = doc["commerce"]
                pid = product["id"]
                products.setdefault(pid, to_row(product))
                subs = membership.setdefault(pid, {}).setdefault(category, set())
                if subcategory:
                    subs.add(subcategory)
        count = sum(1 for m in membership.values() if category in m)
        print(f"  -> {category}: {count - before} Produkte", file=sys.stderr)

    rows = []
    for pid, row in products.items():
        cats = membership[pid]
        row["kategorien"] = "; ".join(c for c in CATEGORIES if c in cats)
        row["anzahl_kategorien"] = len(cats)
        row["unterkategorien"] = "; ".join(
            f"{c}: {s}" for c in CATEGORIES if c in cats for s in sorted(cats[c])
        )
        for c in CATEGORIES:
            row[c] = int(c in cats)
        rows.append(row)

    print(f"  Lade Details von {len(rows)} Produktseiten ...", file=sys.stderr)
    with ThreadPoolExecutor(PAGE_WORKERS) as pool:
        for row, details in zip(rows, pool.map(lambda r: fetch_details(r["url"]), rows)):
            tools = details.pop("werkzeuge")
            galerie = details.pop("galerie")
            row.update(details)
            row["werkzeuge"] = TOOLS_SEPARATOR.join(tools)
            row["anzahl_werkzeuge"] = len(tools)
            row["galerie_bilder"] = " ".join(galerie)

    rows.sort(key=lambda r: (r["kategorien"], r["name"]))
    return rows


def split(value, sep):
    return [part.strip() for part in str(value or "").split(sep) if part.strip()]


def number(value):
    value = str(value or "").strip()
    if not value:
        return None
    f = float(value)
    return int(f) if f.is_integer() else f


def yes_no(value):
    return {"Ja": True, "Nein": False}.get(str(value or "").strip())


def to_product(row):
    """Interne Scraper-Zeile → Produkt im JSON-Format (Listen statt Trennzeichen, null statt "").
    Abgeleitete Werte (Anzahlen, Werkzeuggruppen) werden nicht gespeichert, sondern beim Laden berechnet."""
    return {
        "id": f"victorinox:{row['artikelnummer']}",
        "marke": "Victorinox",
        "artikelnummer": row["artikelnummer"],
        "name": row["name"],
        "kategorien": split(row["kategorien"], ";"),
        "unterkategorien": split(row["unterkategorien"], ";"),
        "shop_kategorie": str(row.get("shop_kategorie") or "").replace("\xa0", " ") or None,
        "preis_chf": number(row.get("preis_chf")),
        "lagerstatus": row.get("lagerstatus") or None,
        "varianten": split(row["varianten_artikelnummern"], ","),
        "farben": split(row["farben"], ","),
        "werkzeuge": split(row.get("werkzeuge"), TOOLS_SEPARATOR),
        "anzahl_funktionen": number(row.get("anzahl_funktionen")),
        "laenge_mm": number(row.get("laenge_mm")),
        "breite_mm": number(row.get("breite_mm")),
        "hoehe_mm": number(row.get("hoehe_mm")),
        "gewicht_g": number(row.get("gewicht_g")),
        "material": row.get("material") or None,
        "feststellbar": yes_no(row.get("feststellbar")),
        "einhandklinge": yes_no(row.get("einhandklinge")),
        "url": row.get("url") or None,
        "bild_url": row.get("bild_url") or None,
        "galerie_bilder": split(row.get("galerie_bilder"), " "),
    }


def write_json(products, path, scraped=None):
    """Ein Produkt pro Zeile: kompakt und in Git-Diffs pro Produkt lesbar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ",\n".join("    " + json.dumps(p, ensure_ascii=False) for p in products)
    header = {
        "quelle": f"{SITE} (backend/scraper/victorinox.py)",
        "gescrapt_am": (scraped or date.today()).isoformat(),
        "anzahl": len(products),
    }
    head = json.dumps(header, ensure_ascii=False, indent=2)[:-2]  # ohne schliessende Klammer
    path.write_text(f'{head},\n  "produkte": [\n{lines}\n  ]\n}}\n', encoding="utf-8")


def main():
    default = Path(__file__).resolve().parent.parent / "data" / "victorinox_produkte.json"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    products = [to_product(row) for row in scrape()]
    write_json(products, out)
    multi = sum(1 for p in products if len(p["kategorien"]) > 1)
    with_tools = sum(1 for p in products if p["werkzeuge"])
    print(f"{len(products)} Produkte ({multi} in mehreren Kategorien, {with_tools} mit Werkzeugen) -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
