// Mock für Endpoints, die das Backend noch nicht hat (v. a. /api/match).
// Produkte inkl. Werkzeuglisten sind echte Einträge aus backend/data/victorinox_produkte.json
// (so wie GET /api/products sie liefert). Was angeblich auf dem Foto erkannt wurde,
// ist dagegen fest vorgegeben und als "Bilderkennung (Demo)" markiert. Vertrag: docs/api.md

const KATALOG = 'Produktdaten victorinox.com'
const BILD = 'Bilderkennung (Demo)'

const PRODUKTE = {
  '1.3603': {"id": "victorinox:1.3603", "marke": "Victorinox", "artikelnummer": "1.3603", "name": "Spartan", "kategorien": ["Everyday", "Personalisieren"], "shop_kategorie": "Essentials", "preis_chf": 25, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3603", "1.3603.3", "1.3603.7", "1.3603.T", "1.3603.94", "1.3603.T2", "1.3603.T7"], "farben": ["rot", "schwarz", "weiss", "rot transparent", "camouflage", "blau transparent", "silvertech"], "anzahl_werkzeuge": 12, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Ring", "Pinzette", "Zahnstocher", "Kapselheber", "Schraubendreher 3 mm", "Schraubendreher 6 mm", "Dosenöffner", "Drahtabisolierer"], "anzahl_funktionen": 12, "laenge_mm": 91, "material": "ABS/Cellidor", "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Spartan/p/1.3603/", "bild_url": "https://imageengine.victorinox.com/transform/3e41526b-7ced-4cc1-8fee-c8447ed9d818/SAK_1_3603_S1"},
  '1.3703': {"id": "victorinox:1.3703", "marke": "Victorinox", "artikelnummer": "1.3703", "name": "Climber", "kategorien": ["Everyday", "Personalisieren"], "shop_kategorie": "Essentials", "preis_chf": 37, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3703", "1.3703.3", "1.3703.7", "1.3703.T", "1.3703.94", "1.3703.T2", "1.3703.T7"], "farben": ["rot", "schwarz", "weiss", "rot transparent", "camouflage", "blau transparent", "silvertech"], "anzahl_werkzeuge": 14, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Schere", "Mehrzweckhaken", "Ring", "Pinzette", "Zahnstocher", "Dosenöffner", "Kapselheber", "Schraubendreher 3 mm", "Schraubendreher 6 mm", "Drahtabisolierer"], "anzahl_funktionen": 14, "laenge_mm": 91, "material": "ABS/Cellidor", "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Climber/p/1.3703/", "bild_url": "https://imageengine.victorinox.com/transform/b930a3ee-e28e-40e8-bb94-6f4dbc02bddf/SAK_1_3703__S1"},
  '1.4603': {"id": "victorinox:1.4603", "marke": "Victorinox", "artikelnummer": "1.4603", "name": "Tinker", "kategorien": ["Everyday"], "shop_kategorie": "Essentials", "preis_chf": 25, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.4603"], "farben": ["rot"], "anzahl_werkzeuge": 12, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Dosenöffner", "Schraubendreher 3 mm", "Kapselheber", "Schraubendreher 6 mm", "Drahtabisolierer", "Stech-Bohr-Nähahle", "Phillips-Schraubendreher 1/2", "Ring", "Pinzette", "Zahnstocher"], "anzahl_funktionen": 12, "laenge_mm": 91, "material": "ABS/Cellidor", "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Tinker/p/1.4603/", "bild_url": "https://imageengine.victorinox.com/transform/f0cc93cf-2dd3-4fa9-b5e9-01c14762e8a4/SAK_1_4603__S1"},
  '1.3713': {"id": "victorinox:1.3713", "marke": "Victorinox", "artikelnummer": "1.3713", "name": "Huntsman", "kategorien": ["Outdoor & Sports", "Personalisieren"], "shop_kategorie": "Outdoor", "preis_chf": 43, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3713", "1.3713.3", "1.3713.7", "1.3713.T", "1.3713.94", "1.3713.T2", "1.3713.T7", "1.3713.941", "1.3713.942"], "farben": ["rot", "schwarz", "weiss", "rot transparent", "camouflage", "blau transparent", "silvertech", "desert camouflage", "navy camouflage"], "anzahl_werkzeuge": 15, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Stech-Bohr-Nähahle", "Schere", "Holzsäge", "Mehrzweckhaken", "Ring", "Pinzette", "Zahnstocher", "Dosenöffner", "Kapselheber", "Schraubendreher 6 mm", "Schraubendreher 3 mm", "Drahtabisolierer"], "anzahl_funktionen": 15, "laenge_mm": 91, "material": "ABS/Cellidor", "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Outdoor/Huntsman/p/1.3713/", "bild_url": "https://imageengine.victorinox.com/transform/be27477a-5deb-4412-87dd-ba03f429520c/SAK_1-3713_S1"},
  '1.3714.E15': {"id": "victorinox:1.3714.E15", "marke": "Victorinox", "artikelnummer": "1.3714.E15", "name": "Huntsman Year of the Horse 2026", "kategorien": ["Outdoor & Sports"], "shop_kategorie": "Outdoor", "preis_chf": 88, "lagerstatus": "outOfStock", "varianten_artikelnummern": ["1.3714.E15"], "farben": ["rot"], "anzahl_werkzeuge": 16, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Dosenöffner", "Schraubendreher 3 mm", "Kapselheber", "Schraubendreher 6 mm", "Drahtabisolierer", "Stech-Bohr-Nähahle", "Schere", "Holzsäge", "Mehrzweckhaken", "Ring", "Pinzette", "Zahnstocher", "SIM Karten Pin"], "anzahl_funktionen": 16, "laenge_mm": 91, "material": null, "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Outdoor/Huntsman-Year-of-the-Horse%C2%A02026/p/1.3714.E15/", "bild_url": "https://imageengine.victorinox.com/transform/ed7ff060-2838-4a0e-9f59-067c5a7523a8/SAK_1-3714-E15_S1"},
  '1.3714.E16': {"id": "victorinox:1.3714.E16", "marke": "Victorinox", "artikelnummer": "1.3714.E16", "name": "Huntsman Year of the Goat 2027", "kategorien": ["Outdoor & Sports"], "shop_kategorie": "Outdoor", "preis_chf": 88, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3714.E16"], "farben": ["rot"], "anzahl_werkzeuge": 16, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Dosenöffner", "Schraubendreher 3 mm", "Kapselheber", "Schraubendreher 6 mm", "Drahtabisolierer", "Stech-Bohr-Nähahle", "Schere", "Holzsäge", "Mehrzweckhaken", "Ring", "Pinzette", "Zahnstocher", "SIM Karten Pin"], "anzahl_funktionen": 16, "laenge_mm": 91, "material": null, "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Outdoor/Huntsman-Year-of-the-Goat%C2%A02027/p/1.3714.E16/", "bild_url": "https://imageengine.victorinox.com/transform/ea11def6-3a11-4bf5-8a1b-d282635612b2/SAK_1-3714-E16_S1"},
  '1.3711.63': {"id": "victorinox:1.3711.63", "marke": "Victorinox", "artikelnummer": "1.3711.63", "name": "Huntsman Wood", "kategorien": ["Outdoor & Sports"], "shop_kategorie": "Outdoor", "preis_chf": 55, "lagerstatus": "inStock", "varianten_artikelnummern": ["1.3711.63"], "farben": ["nussbaumholz"], "anzahl_werkzeuge": 13, "werkzeuge": ["Klinge, gross", "Klinge, klein", "Korkenzieher", "Dosenöffner", "Schraubendreher 3 mm", "Kapselheber", "Schraubendreher 6 mm", "Drahtabisolierer", "Stech-Bohr-Nähahle", "Schere", "Holzsäge", "Mehrzweckhaken", "Ring"], "anzahl_funktionen": 13, "laenge_mm": 91, "material": "Nussbaumholz", "url": "https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Outdoor/Huntsman-Wood/p/1.3711.63/", "bild_url": "https://imageengine.victorinox.com/transform/047f68fe-2b25-44a1-8344-3c713f48e28e/SAK_1_3711_63"},
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

// Wie /api/match: Stufe 1 Bildsuche, Stufe 2 Werkzeugerkennung nur, wenn die Bildsuche nicht eindeutig ist
function schritte(details) {
  const labels = {
    bildsuche: 'Bildsuche im Katalog',
    vision: details.vision?.uebersprungen ? 'Werkzeugerkennung' : 'Werkzeuge erkannt',
    marke: 'Marke bestimmt',
    suche: details.suche?.label ?? 'Kandidaten verglichen',
    empfehlung: 'Empfehlung erstellt',
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
      stufe: 'werkzeuge',
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
      bildsuche: { status: 'warnung', detail: 'Marke SWIZA: kein Victorinox-Katalogbild kann dasselbe Modell zeigen' },
      vision: { detail: 'Taschenmesser aufgeklappt, 7 Werkzeuge erkannt' },
      marke: { detail: 'SWIZA (Logo auf der Klinge)' },
      suche: { label: 'Ausstattung verglichen', detail: '7 Werkzeuge mit 159 Victorinox-Taschenmessern verglichen' },
      empfehlung: { detail: 'Gewichtet nach Werkzeugen, Farbe, Verfügbarkeit' },
    }),
  }),

  // Ausgelaufenes Victorinox-Produkt → aktueller Nachfolger
  victorinox: () => ({
    pfad: 'nachfolger',
    erkannt: {
      marke: 'Victorinox',
      ist_victorinox: true,
      modell: 'Huntsman Year of the Horse 2026',
      artikelnummer: '1.3714.E15',
      kategorie: 'Taschenmesser',
      stufe: 'bildsuche',
      konfidenz: 0.94,
      produkt: PRODUKTE['1.3714.E15'],
      // Stufe 1: keine Werkzeugerkennung, wie im echten Backend
      werkzeuge: [],
      merkmale: [],
    },
    empfehlungen: [
      empfehlung('1.3714.E16', 0.96,
        'Die Jahresedition 2026 ist nicht mehr verfügbar. Die Nachfolge-Edition Year of the Goat 2027 hat dieselben 16 Werkzeuge, kostet gleich viel und ist an Lager.',
        ['Identische 16 Werkzeuge', 'Nachfolge-Edition 2027', 'An Lager', 'Gleicher Preis (CHF 88)']),
      empfehlung('1.3713', 0.88,
        'Das Basismodell Huntsman hat dieselben Werkzeuge ohne SIM-Karten-Pin und ist deutlich günstiger, aber ohne Sonderdesign.',
        ['15 von 16 Werkzeugen (ohne SIM-Karten-Pin)', 'An Lager', 'Günstiger (CHF 43)']),
      empfehlung('1.3711.63', 0.74,
        'Huntsman mit Holzschalen; ohne Pinzette, Zahnstocher und SIM-Karten-Pin.',
        ['13 von 16 Werkzeugen', 'Holzschalen', 'An Lager']),
    ],
    rueckfrage: null,
    schritte: schritte({
      bildsuche: { detail: 'Foto mit 157 Katalogbildern verglichen: Huntsman Year of the Horse 2026 mit 78 %' },
      vision: { uebersprungen: true, detail: 'übersprungen: die Bildsuche hat das Modell eindeutig gefunden' },
      marke: { detail: 'Victorinox (Kreuz im Wappen)' },
      suche: { label: 'Nachfolger gesucht', detail: '1.3714.E15 ist nicht lieferbar; Nachfolger laut Cross-Reference: Year of the Goat 2027' },
      empfehlung: { detail: 'Nachfolger mit gleichem Werkzeugset zuerst' },
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
      stufe: 'werkzeuge',
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
      bildsuche: { status: 'warnung', detail: 'Platz 1 nur 24 % (nötig: 30 %), weiter mit der Werkzeugerkennung' },
      vision: { status: 'warnung', detail: 'Foto unscharf, Werkzeuge nicht sichtbar' },
      marke: { detail: 'Victorinox (Kreuz erkannt), Modell unklar' },
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
      stufe: 'bildsuche',
      konfidenz: 0.93,
      produkt: PRODUKTE['1.3703'],
      // Stufe 1: keine Werkzeugerkennung, wie im echten Backend
      werkzeuge: [],
      merkmale: [],
    },
    empfehlungen: [
      empfehlung('1.3703', 0.93, 'Mit dem zweiten Foto sind Schere und Korkenzieher sichtbar. Das passt nur zum Climber. Er ist aktuell erhältlich.', ['Schere sichtbar → kein Spartan', 'Korkenzieher sichtbar → kein Tinker', 'An Lager']),
      empfehlung('1.3713', 0.66, 'Ähnlich, hat aber zusätzlich eine Holzsäge, die auf dem Foto fehlt.', ['+ Holzsäge (nicht sichtbar)']),
      empfehlung('1.3603', 0.52, 'Ohne Schere, passt daher nicht zum zweiten Foto.', ['Keine Schere']),
    ],
    rueckfrage: null,
    schritte: schritte({
      bildsuche: { detail: 'Zwei Fotos kombiniert: Climber mit 81 %, klar vor Huntsman' },
      vision: { uebersprungen: true, detail: 'übersprungen: die Bildsuche hat das Modell eindeutig gefunden' },
      marke: { detail: 'Victorinox' },
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
