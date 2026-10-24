// Mock für Endpoints, die das Backend noch nicht hat (v. a. /api/match).
// Produkte inkl. Werkzeuglisten sind echte Zeilen aus backend/data/victorinox_sak_produkte.csv
// (so wie GET /api/products sie liefert). Was angeblich auf dem Foto erkannt wurde,
// ist dagegen fest vorgegeben und als "Bilderkennung (Demo)" markiert. Vertrag: docs/api.md

const KATALOG = 'Produktdaten victorinox.com'
const BILD = 'Bilderkennung (Demo)'

const PRODUKTE = {
  '1.3603': {"artikelnummer": "1.3603", "name": "Spartan", "kategorien": ["Everyday", "Personalisieren"], "shop_kategorie": "Essentials", "preis_chf": 25.0, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3603", "1.3603.3", "1.3603.7", "1.3603.T", "1.3603.94", "1.3603.T2", "1.3603.T7"], "farben": ["rot", "schwarz", "weiss", "rot transparent", "camouflage", "blau transparent", "silvertech"], "anzahl_werkzeuge": 12, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Ring", "Pinzette", "Zahnstocher", "Kapselheber", "Schraubendreher 3 mm", "Schraubendreher 6 mm", "Dosenöffner", "Drahtabisolierer"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Spartan/p/1.3603/", "bild_url": "https://imageengine.victorinox.com/transform/3e41526b-7ced-4cc1-8fee-c8447ed9d818/SAK_1_3603_S1"},
  '1.3703': {"artikelnummer": "1.3703", "name": "Climber", "kategorien": ["Everyday", "Personalisieren"], "shop_kategorie": "Essentials", "preis_chf": 37.0, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3703", "1.3703.3", "1.3703.7", "1.3703.T", "1.3703.94", "1.3703.T2", "1.3703.T7"], "farben": ["rot", "schwarz", "weiss", "rot transparent", "camouflage", "blau transparent", "silvertech"], "anzahl_werkzeuge": 14, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Schere", "Mehrzweckhaken", "Ring", "Pinzette", "Zahnstocher", "Dosenöffner", "Kapselheber", "Schraubendreher 3 mm", "Schraubendreher 6 mm", "Drahtabisolierer"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Climber/p/1.3703/", "bild_url": "https://imageengine.victorinox.com/transform/b930a3ee-e28e-40e8-bb94-6f4dbc02bddf/SAK_1_3703__S1"},
  '1.4603': {"artikelnummer": "1.4603", "name": "Tinker", "kategorien": ["Everyday"], "shop_kategorie": "Essentials", "preis_chf": 25.0, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.4603"], "farben": ["rot"], "anzahl_werkzeuge": 12, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Dosenöffner", "Schraubendreher 3 mm", "Kapselheber", "Schraubendreher 6 mm", "Drahtabisolierer", "Stech-Bohr-Nähahle", "Phillips-Schraubendreher 1/2", "Ring", "Pinzette", "Zahnstocher"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Tinker/p/1.4603/", "bild_url": "https://imageengine.victorinox.com/transform/f0cc93cf-2dd3-4fa9-b5e9-01c14762e8a4/SAK_1_4603__S1"},
  '1.3713': {"artikelnummer": "1.3713", "name": "Huntsman", "kategorien": ["Outdoor & Sports", "Personalisieren"], "shop_kategorie": "Outdoor", "preis_chf": 43.0, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3713", "1.3713.3", "1.3713.7", "1.3713.T", "1.3713.94", "1.3713.T2", "1.3713.T7", "1.3713.941", "1.3713.942"], "farben": ["rot", "schwarz", "weiss", "rot transparent", "camouflage", "blau transparent", "silvertech", "desert camouflage", "navy camouflage"], "anzahl_werkzeuge": 15, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Schere", "Holzsäge", "Mehrzweckhaken", "Ring", "Pinzette", "Zahnstocher", "Dosenöffner", "Kapselheber", "Schraubendreher 6 mm", "Schraubendreher 3 mm", "Drahtabisolierer"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Outdoor/Huntsman/p/1.3713/", "bild_url": "https://imageengine.victorinox.com/transform/be27477a-5deb-4412-87dd-ba03f429520c/SAK_1-3713_S1"},
  '1.6703': {"artikelnummer": "1.6703", "name": "Explorer", "kategorien": ["Everyday", "Personalisieren"], "shop_kategorie": "Essentials", "preis_chf": 55.0, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.6703"], "farben": ["rot"], "anzahl_werkzeuge": 16, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Schere", "Phillips-Schraubendreher 1/2", "Mehrzweckhaken", "Lupe", "Ring", "Pinzette", "Zahnstocher", "Kapselheber", "Dosenöffner", "Schraubendreher 3 mm", "Schraubendreher 6 mm", "Drahtabisolierer"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Explorer/p/1.6703/", "bild_url": "https://imageengine.victorinox.com/transform/9ec884fd-9e54-4576-b381-0e1c686031c1/SAK_1_6703__S1"},
  '1.3701.63E1': {"artikelnummer": "1.3701.63E1", "name": "Climber Wood Winter Magic Limited Edition 2025", "kategorien": ["Everyday"], "shop_kategorie": "Essentials", "preis_chf": 79.0, "lagerstatus": "outOfStock", "varianten_artikelnummern": ["1.3701.63E1"], "farben": ["pear wood"], "anzahl_werkzeuge": 13, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Kapselheber", "Schraubendreher 6 mm", "Drahtabisolierer", "Dosenöffner", "Schraubendreher 3 mm", "Stech-Bohr-Nähahle", "Schere", "Mehrzweckhaken", "Ring", "Paketöffner"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Climber-Wood-Winter-Magic-Limited-Edition-2025/p/1.3701.63E1/", "bild_url": "https://imageengine.victorinox.com/transform/40585665-81ae-4814-8a55-070017e9c74e/SAK_1-3701-63E1_S1"},
  '1.3703.E95': {"artikelnummer": "1.3703.E95", "name": "Climber „Place to Be”", "kategorien": ["Everyday"], "shop_kategorie": "Essentials", "preis_chf": 45.0, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3703.E95"], "farben": ["switzerland"], "anzahl_werkzeuge": 11, "werkzeuge": ["Schere", "Mehrzweckhaken", "Zahnstocher", "Korkenzieher", "Stech-Bohr-Nähahle", "Pinzette", "Kapselheber", "Ring", "Dosenöffner", "Klinge, klein", "Klinge, gross"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Climber-%E2%80%9EPlace-to-Be%E2%80%9D/p/1.3703.E95/", "bild_url": "https://imageengine.victorinox.com/transform/f166dd1d-d2a2-48a8-a160-2f5b0845298c/SAK_1_3703_E95__S1"},
  '1.3601.63': {"artikelnummer": "1.3601.63", "name": "Spartan Wood", "kategorien": ["Everyday", "Personalisieren"], "shop_kategorie": "Essentials", "preis_chf": 37.0, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3601.63"], "farben": ["nussbaumholz"], "anzahl_werkzeuge": 10, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Ring", "Kapselheber", "Dosenöffner", "Schraubendreher 3 mm", "Schraubendreher 6 mm", "Drahtabisolierer"], "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Spartan-Wood/p/1.3601.63/", "bild_url": "https://imageengine.victorinox.com/transform/95e082ba-6faf-4f0a-bc9f-6a19426ab29d/SAK_1_3601_63__S1"},
}

// Merkmale für die Vergleichstabelle, nur aus Katalogfeldern; leere Felder fallen weg.
function merkmale(produkt) {
  return [
    { key: 'funktionen', label: 'Funktionen', wert: produkt.anzahl_werkzeuge || null, quelle: KATALOG },
    { key: 'werkzeuge', label: 'Werkzeuge', wert: produkt.werkzeuge?.length ? produkt.werkzeuge : null, quelle: KATALOG },
    { key: 'farben', label: 'Farben', wert: produkt.farben?.length ? produkt.farben : null, quelle: KATALOG },
  ].filter((m) => m.wert != null)
}

function empfehlung(artikelnummer, score, begruendung, gruende) {
  const produkt = PRODUKTE[artikelnummer]
  return { produkt, score, begruendung, gruende, merkmale: merkmale(produkt) }
}

function schritte(details) {
  const labels = {
    vision: 'Bild analysiert',
    marke: 'Marke & Modell erkannt',
    ocr: 'Gravur / Artikelnummer gelesen',
    suche: 'Katalog durchsucht (Top-k)',
    empfehlung: 'Empfehlung bewertet',
  }
  return Object.entries(labels).map(([id, label]) => ({
    id,
    label,
    status: details[id]?.status ?? 'ok',
    detail: details[id]?.detail ?? '',
  }))
}

const SZENARIEN = {
  // Konkurrenzprodukt → bester Victorinox-Ersatz (Beispiel aus dem Einführungs-Deck)
  konkurrenz: () => ({
    pfad: 'ersatz',
    erkannt: {
      marke: 'SWIZA',
      ist_victorinox: false,
      modell: 'D03 AM (Black)',
      artikelnummer: 'KNI.0036.1010',
      kategorie: 'Taschenmesser',
      konfidenz: 0.91,
      merkmale: [
        // Werkzeugnamen im Vokabular des Victorinox-Katalogs, damit sie vergleichbar sind
        { key: 'werkzeuge', label: 'Werkzeuge', wert: ['Klinge, gross', 'Korkenzieher', 'Dosenöffner', 'Kapselheber', 'Schraubendreher 6 mm', 'Stech-Bohr-Nähahle', 'Pinzette'], quelle: BILD },
        { key: 'farben', label: 'Farben', wert: ['schwarz'], quelle: BILD },
      ],
    },
    empfehlungen: [
      empfehlung('1.3603', 0.87,
        'Der Spartan hat alle Werkzeuge, die auf dem Foto erkannt wurden, und ist ebenfalls in Schwarz erhältlich. Er ist der klassische Allrounder im gleichen Preissegment.',
        ['Alle 7 erkannten Werkzeuge vorhanden', 'In Schwarz verfügbar (1.3603.3)', 'An Lager']),
      empfehlung('1.3703', 0.81,
        'Gleiche Grundausstattung wie der Spartan, zusätzlich mit Schere und Mehrzweckhaken. Passt, wenn der Kunde etwas mehr Funktionen möchte.',
        ['Alle 7 erkannten Werkzeuge vorhanden', '+ Schere, + Mehrzweckhaken', 'In Schwarz verfügbar']),
      empfehlung('1.3713', 0.72,
        'Deutlich mehr Funktionen (u. a. Holzsäge). Nur sinnvoll, wenn der Kunde ein Upgrade sucht.',
        ['Alle 7 erkannten Werkzeuge vorhanden', '+ Schere, Holzsäge, Haken', 'Höherer Preis']),
    ],
    rueckfrage: null,
    schritte: schritte({
      vision: { detail: 'Taschenmesser erkannt, aufgeklappt, 7 Werkzeuge sichtbar' },
      marke: { detail: 'SWIZA-Logo auf der Klinge, Modell D03' },
      ocr: { detail: '„SWIZA“ auf der Klinge gelesen' },
      suche: { detail: '153 Victorinox-Taschenmesser verglichen, Top 3 ausgewählt' },
      empfehlung: { detail: 'Gewichtet nach Werkzeugen, Farbe, Verfügbarkeit' },
    }),
  }),

  // Ausgelaufenes Victorinox-Produkt → aktueller Nachfolger
  victorinox: () => ({
    pfad: 'nachfolger',
    erkannt: {
      marke: 'Victorinox',
      ist_victorinox: true,
      modell: 'Climber Wood Winter Magic Limited Edition 2025',
      artikelnummer: '1.3701.63E1',
      kategorie: 'Taschenmesser',
      konfidenz: 0.92,
      produkt: PRODUKTE['1.3701.63E1'],
      merkmale: merkmale(PRODUKTE['1.3701.63E1']),
    },
    empfehlungen: [
      empfehlung('1.3703', 0.94,
        'Die Limited Edition 2025 ist nicht mehr verfügbar. Der Climber ist dasselbe Modell aus der regulären Serie: gleiche Werkzeuge, statt Paketöffner mit Pinzette und Zahnstocher, an Lager.',
        ['Gleiches Basismodell', 'Gleiche Werkzeuge (+ Pinzette, Zahnstocher)', 'An Lager', 'Günstiger (CHF 37 statt 79)']),
      empfehlung('1.3703.E95', 0.8,
        'Climber mit Sonderdesign „Place to Be“, ebenfalls an Lager.',
        ['Climber-Basis', 'Sonderdesign', 'An Lager']),
      empfehlung('1.3601.63', 0.72,
        'Wer die Holzschalen möchte: Spartan Wood, allerdings ohne Schere und Mehrzweckhaken.',
        ['Holzschalen wie das Original', 'Ohne Schere und Mehrzweckhaken', 'An Lager']),
    ],
    rueckfrage: null,
    schritte: schritte({
      vision: { detail: 'Taschenmesser erkannt, aufgeklappt, Holzschalen mit Schneeflocken-Motiv' },
      marke: { detail: 'Victorinox-Kreuz erkannt' },
      ocr: { detail: 'Motiv „Winter Magic“ erkannt' },
      suche: { detail: 'Treffer: 1.3701.63E1, Status „nicht verfügbar“' },
      empfehlung: { detail: 'Nachfolger über Basismodell Climber ermittelt' },
    }),
  }),

  // Unsichere Erkennung → mehrere Kandidaten + gezielte Rückfrage
  unsicher: () => ({
    pfad: 'aktuell',
    erkannt: {
      marke: 'Victorinox',
      ist_victorinox: true,
      modell: null,
      artikelnummer: null,
      kategorie: 'Taschenmesser',
      konfidenz: 0.48,
      merkmale: [{ key: 'farben', label: 'Farben', wert: ['rot'], quelle: BILD }],
    },
    empfehlungen: [
      empfehlung('1.3703', 0.58, 'Form und Farbe passen. Die Werkzeuge sind auf dem Foto nicht eindeutig erkennbar.', ['Form & Farbe passen', 'Werkzeuge unklar']),
      empfehlung('1.3603', 0.56, 'Sieht geschlossen fast identisch aus wie der Climber.', ['Form & Farbe passen', 'Werkzeuge unklar']),
      empfehlung('1.4603', 0.55, 'Ebenfalls rote Schale in gleicher Grösse; unterscheidet sich nur in den Werkzeugen.', ['Form & Farbe passen', 'Werkzeuge unklar']),
    ],
    rueckfrage: {
      frage: 'Ich bin mir nicht sicher. Kannst du das Messer aufgeklappt fotografieren?',
      hinweis: 'Spartan, Climber und Tinker sehen geschlossen fast gleich aus. Erst die Werkzeuge unterscheiden sie: Der Climber hat eine Schere, der Tinker einen Phillips-Schraubendreher statt Korkenzieher.',
    },
    schritte: schritte({
      vision: { status: 'warnung', detail: 'Foto unscharf, Werkzeuge nicht sichtbar' },
      marke: { detail: 'Victorinox-Kreuz erkannt, Modell unklar' },
      ocr: { status: 'warnung', detail: 'Keine Artikelnummer lesbar' },
      suche: { detail: '3 Kandidaten mit fast gleichem Score' },
      empfehlung: { status: 'warnung', detail: 'Abstand zu klein, Rückfrage nötig' },
    }),
  }),

  // Zweites Foto nach der Rückfrage → jetzt eindeutig
  nachfoto: () => ({
    pfad: 'aktuell',
    erkannt: {
      marke: 'Victorinox',
      ist_victorinox: true,
      modell: 'Climber',
      artikelnummer: '1.3703',
      kategorie: 'Taschenmesser',
      konfidenz: 0.93,
      produkt: PRODUKTE['1.3703'],
      merkmale: merkmale(PRODUKTE['1.3703']),
    },
    empfehlungen: [
      empfehlung('1.3703', 0.93, 'Mit dem zweiten Foto sind Schere und Korkenzieher sichtbar. Das passt nur zum Climber. Er ist aktuell erhältlich.', ['Schere sichtbar → kein Spartan', 'Korkenzieher sichtbar → kein Tinker', 'An Lager']),
      empfehlung('1.3713', 0.66, 'Ähnlich, hat aber zusätzlich eine Holzsäge, die auf dem Foto fehlt.', ['+ Holzsäge (nicht sichtbar)']),
      empfehlung('1.3603', 0.52, 'Ohne Schere, passt daher nicht zum zweiten Foto.', ['Keine Schere']),
    ],
    rueckfrage: null,
    schritte: schritte({
      vision: { detail: 'Zweites Foto kombiniert, Schere und Korkenzieher sichtbar' },
      marke: { detail: 'Victorinox Climber' },
      ocr: { detail: 'Keine Artikelnummer nötig' },
      suche: { detail: 'Climber klar vor Huntsman' },
      empfehlung: { detail: 'Produkt aktuell erhältlich' },
    }),
  }),
}

const warte = (ms) => new Promise((r) => setTimeout(r, ms))

export async function match({ kategorie, vorherigeMatchId, demo } = {}) {
  await warte(1800)
  const szenario = vorherigeMatchId ? 'nachfoto' : SZENARIEN[demo] ? demo : 'konkurrenz'
  const ergebnis = SZENARIEN[szenario]()
  if (kategorie) {
    ergebnis.schritte = ergebnis.schritte.map((s) =>
      s.id === 'suche' ? { ...s, detail: `Suche auf „${kategorie}“ eingegrenzt · ${s.detail}` } : s,
    )
  }
  return { match_id: `mock-${Date.now().toString(36)}`, modus: 'mock', ...ergebnis }
}

export async function feedback(body) {
  await warte(300)
  try {
    const alt = JSON.parse(localStorage.getItem('feedback') ?? '[]')
    localStorage.setItem('feedback', JSON.stringify([...alt, { ...body, zeit: new Date().toISOString() }]))
  } catch {
    // Feedback ist im Mock nur lokal; ohne Storage geht es eben verloren.
  }
  return { gespeichert: 'lokal' }
}

export async function produkte({ q = '', kategorie = '', limit = 50, offset = 0 }) {
  const n = q.trim().toLowerCase()
  const alle = Object.values(PRODUKTE).filter(
    (p) =>
      (!kategorie || p.kategorien.includes(kategorie)) &&
      (!n || `${p.name} ${p.artikelnummer} ${p.farben.join(' ')}`.toLowerCase().includes(n)),
  )
  return { anzahl: alle.length, produkte: alle.slice(offset, offset + limit) }
}

export async function produkt(artikelnummer) {
  const p = PRODUKTE[artikelnummer]
  if (!p) throw new Error(`Kein Produkt mit Artikelnummer ${artikelnummer}`)
  return p
}
