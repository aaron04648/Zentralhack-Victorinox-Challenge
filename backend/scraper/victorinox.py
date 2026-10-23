"""Scraper für die Swiss Army Knife & Tools Produkte von victorinox.com (de-CH).

Die Produktlisten der Webseite werden clientseitig über die Frontastic-API
nachgeladen. Dieser Scraper ruft dieselben Endpunkte direkt auf und schreibt
eine CSV mit einer Zeile pro Produkt. Ein Produkt kann in mehreren Kategorien
vorkommen; die Zugehörigkeit steht in der Spalte "kategorien" sowie in je einer
0/1-Spalte pro Kategorie.

Die Werkzeuge eines Messers stehen nur auf der Produktseite (Merkmal
"Hauptfunktion"). Sie landen als Spalte "werkzeuge" in der Haupt-CSV und
zusätzlich als eine Zeile pro Messer und Werkzeug in einer zweiten CSV.

Aufruf:  python -m scraper.victorinox [ausgabe.csv]
"""

import csv
import json
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
TOOLS_FEATURE = "class_sak_functions.sak_main_function"
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


def find_feature(node, code_suffix):
    if isinstance(node, dict):
        if str(node.get("code", "")).endswith(code_suffix) and isinstance(node.get("values"), list):
            return node["values"]
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return None
    for child in children:
        found = find_feature(child, code_suffix)
        if found is not None:
            return found
    return None


def fetch_tools(url):
    """Werkzeugliste von der Produktseite (Next.js-Daten); leer bei Zubehör o. ä."""
    if not url:
        return []
    html = fetch(url, PAGE_HEADERS)
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return []
    values = find_feature(json.loads(match.group(1)), TOOLS_FEATURE) or []
    return [v.replace("\xa0", " ").strip() for v in values if v and v.strip()]


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

    print(f"  Lade Werkzeuge von {len(rows)} Produktseiten ...", file=sys.stderr)
    with ThreadPoolExecutor(PAGE_WORKERS) as pool:
        for row, tools in zip(rows, pool.map(lambda r: fetch_tools(r["url"]), rows)):
            row["werkzeuge"] = TOOLS_SEPARATOR.join(tools)
            row["anzahl_werkzeuge"] = len(tools)

    rows.sort(key=lambda r: (r["kategorien"], r["name"]))
    return rows


PRODUCT_COLUMNS = [
    "artikelnummer", "name", "kategorien", "anzahl_kategorien", *CATEGORIES,
    "unterkategorien", "shop_kategorie", "preis_chf", "lagerstatus",
    "anzahl_varianten", "varianten_artikelnummern", "farben",
    "anzahl_werkzeuge", "werkzeuge", "url", "bild_url",
]
TOOL_COLUMNS = ["artikelnummer", "name", "werkzeug"]


def write_csv(rows, path, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig + Semikolon, damit Excel (CH/DE) die Datei direkt korrekt öffnet
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def tool_rows(rows):
    """Eine Zeile pro Messer und Werkzeug, für einfaches Filtern/Joinen."""
    return [
        {"artikelnummer": r["artikelnummer"], "name": r["name"], "werkzeug": tool}
        for r in rows if r["werkzeuge"]
        for tool in r["werkzeuge"].split(TOOLS_SEPARATOR)
    ]


def main():
    default = Path(__file__).resolve().parent.parent / "data" / "victorinox_sak_produkte.csv"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    tools_out = out.with_name("victorinox_sak_werkzeuge.csv")
    rows = scrape()
    tools = tool_rows(rows)
    write_csv(rows, out, PRODUCT_COLUMNS)
    write_csv(tools, tools_out, TOOL_COLUMNS)
    multi = sum(1 for r in rows if r["anzahl_kategorien"] > 1)
    with_tools = sum(1 for r in rows if r["anzahl_werkzeuge"])
    print(f"{len(rows)} Produkte ({multi} in mehreren Kategorien) -> {out}", file=sys.stderr)
    print(f"{with_tools} Produkte mit Werkzeugen, {len(tools)} Zeilen -> {tools_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
