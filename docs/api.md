# API-Vertrag Frontend ↔ Backend

Alle Endpoints liegen unter `/api` (Vite-Proxy → FastAPI, `backend/app/main.py`).
Feldnamen sind deutsch und entsprechen den CSV-Spalten in `backend/data/victorinox_sak_produkte.csv`.

| Endpoint | Status |
| --- | --- |
| `GET /api/health` | vorhanden |
| `POST /api/products/image` | vorhanden (Filter auf CSV-Spalten) |
| `GET /api/products` | vorhanden |
| `GET /api/products/{artikelnummer}` | vorhanden |
| `POST /api/match` | vorhanden (braucht Vision-Key in `.env`, sonst 503 → Frontend nutzt den Mock) |
| `POST /api/feedback` | **offen**, Mock speichert lokal im Browser |

Fehlt ein Endpoint (404/405/501) oder ist das Backend nicht erreichbar, springt im Frontend automatisch
der Mock ein (`VITE_USE_MOCK=auto`, Standard). Mit `VITE_USE_MOCK=false` werden Fehler stattdessen angezeigt,
mit `true` wird immer der Mock benutzt. Ergebnisse aus dem Mock sind in der UI als „Demo-Modus“ markiert.

## Product

So liefern es `GET /api/products` und `GET /api/products/{artikelnummer}`, und so erwartet das Frontend
`produkt` auch in `/api/match`.

```json
{
  "artikelnummer": "1.3603",
  "name": "Spartan",
  "kategorien": ["Everyday", "Personalisieren"],
  "unterkategorien": ["Everyday: Essentials"],
  "shop_kategorie": "Essentials",
  "preis_chf": 25.0,
  "lagerstatus": "inStock",            // "inStock" | "outOfStock" | null
  "varianten_artikelnummern": ["1.3603", "1.3603.3"],
  "farben": ["rot", "schwarz"],
  "anzahl_werkzeuge": 12,              // null, wenn die CSV keine Angabe hat
  "werkzeuge": ["Klinge, gross", "Korkenzieher", "Dosenöffner | Schraubendreher 3 mm"],  // " | " = Kombi-Werkzeug
  "url": "https://www.victorinox.com/...",
  "bild_url": "https://imageengine.victorinox.com/transform/..."
}
```

### `GET /api/products?q=&kategorie=&limit=50&offset=0`

`q` sucht in Name, Artikelnummer, Varianten-Artikelnummern und Farben (ohne Gross-/Kleinschreibung).
`kategorie` ist eine der Messer-Kategorien (`Everyday`, `Outdoor & Sports`, `Trades & Crafts`).
Antwort: `{ "anzahl": 41, "produkte": [Product, …] }`.

Beide Produkt-Endpoints liefern **nur Taschenmesser** (153 von 247 CSV-Zeilen, siehe `is_pocket_knife()` in
`backend/app/main.py`). Zubehör, Nagelpflege, Swiss Cards und Venture ergeben 404 bzw. keinen Treffer. Swiss Tools sind nicht in der
Suche, aber per Artikelnummer abrufbar, weil `/api/match` sie als Ersatz für fremde Zangen-Multitools empfiehlt.

### `GET /api/products/{artikelnummer}`

Löst auch Varianten-Artikelnummern auf (z. B. `1.3603.3` → Spartan). 404, wenn unbekannt.

## `POST /api/match`

`multipart/form-data`:

| Feld | Typ | |
| --- | --- | --- |
| `bild` | Datei (JPEG, max. 1600 px, vom Frontend verkleinert) | Pflicht |
| `kategorie` | string | optional: Hinweis aus dem Dropdown, `Everyday` \| `Outdoor & Sports` \| `Trades & Crafts` (= Werte der CSV-Spalte `kategorien`). Weicher Filter für die Kandidaten. Fehlt das Feld, ist „automatisch“ gewählt. |
| `verwendung` | string | optional: Freitext „Wofür brauchst du das Messer?“ (max. 300 Zeichen). Per Embedding mit den Produkten abgeglichen: gewichtet Clefs Bildsuche, filtert bei fremden Marken die Kandidaten. |
| `vorherige_match_id` | string | optional: zweites Foto nach einer Rückfrage, mit dem vorherigen Ergebnis kombinieren |

Antwort:

```json
{
  "match_id": "m_123",
  "pfad": "ersatz",                     // "ersatz" (Konkurrenz) | "nachfolger" (Victorinox, ausgelaufen) | "aktuell" (Victorinox, erhältlich)
  "erkannt": {
    "marke": "SWIZA",
    "ist_victorinox": false,
    "modell": "D03 AM (Black)",         // null, wenn unklar
    "artikelnummer": "KNI.0036.1010",   // null, wenn nicht erkannt
    "kategorie": "Taschenmesser",
    "konfidenz": 0.91,                  // 0..1, Sicherheit der Erkennung
    "werkzeuge": [                      // erkannte Werkzeuggruppen, sicherste zuerst
      { "gruppe": "zange", "label": "Zange", "wahrscheinlichkeit": 0.93 }   // null = aus erstem Foto übernommen
    ],
    "produkt": null,                    // Product, falls es ein Victorinox-Katalogprodukt ist
    "merkmale": [Merkmal, …]
  },
  "empfehlungen": [                     // sortiert, bestes zuerst, typischerweise Top 3
    {
      "produkt": Product,
      "score": 0.87,                    // 0..1, Match-Score
      "begruendung": "Kurzer, verständlicher Text …",
      "gruende": ["Alle 7 erkannten Werkzeuge vorhanden", "An Lager"],
      "merkmale": [Merkmal, …]
    }
  ],
  "rueckfrage": null,                   // oder { "frage": "…", "hinweis": "…" }
  "schritte": [Schritt, …]
}
```

**Merkmal**: Grundlage für die Vergleichstabelle. Gleiche `key`s auf beiden Seiten werden nebeneinander
gestellt. `wert` darf string, number oder string[] sein (Listen werden als Chips verglichen, z. B. `werkzeuge`).
`quelle` wird in der UI angezeigt: **keine Werte ohne Quelle**, lieber weglassen.

```json
{ "key": "funktionen", "label": "Funktionen", "wert": 12, "quelle": "Produktdaten victorinox.com" }
```

Bekannte Keys: `funktionen` (= `anzahl_werkzeuge`), `werkzeuge` (= `werkzeuge`, im Vokabular des Katalogs, damit sie vergleichbar sind), `farben`. Weitere Keys werden automatisch als Zeile angezeigt.

**Schritt**: für die Agenten-Ansicht während der Analyse.

```json
{ "id": "vision", "label": "Bild analysiert", "status": "ok", "detail": "Taschenmesser erkannt, 7 Werkzeuge sichtbar" }
```

`id` ∈ `vision`, `marke`, `ocr`, `suche`, `empfehlung`; `status` ∈ `ok`, `warnung`, `fehler`.

**Rückfrage**: Das Frontend zeigt Rückfrage-Banner und Kandidatenauswahl, wenn `rueckfrage` gesetzt ist
oder `erkannt.konfidenz < 0.6` (`KONFIDENZ_SCHWELLE` in `frontend/src/lib/format.js`).

## `POST /api/feedback`

```json
{ "match_id": "m_123", "korrekt": false, "gewaehlte_artikelnummer": "1.3703" }
```

Bei `korrekt: true` enthält `gewaehlte_artikelnummer` die angezeigte Empfehlung, bei `false` den vom
Nutzer gewählten besseren Treffer (oder `null`). Antwort beliebig, z. B. `{ "gespeichert": true }`.
