// Mock für Endpoints, die das Backend noch nicht hat (v. a. /api/match).
// Die Produkte sind echte Zeilen aus backend/data/victorinox_sak_produkte.csv;
// die technischen Merkmale stehen (noch) nicht in der CSV und sind deshalb
// ausdrücklich als Demo-Daten markiert. Vertrag: docs/api.md

const DEMO = 'Demo-Daten (nicht verifiziert)'
const BILD = 'Bilderkennung'

const PRODUKTE = {
  '1.3603': {
    artikelnummer: '1.3603', name: 'Spartan', preis_chf: 25, lagerstatus: 'inStock',
    kategorien: ['Everyday', 'Personalisieren'], shop_kategorie: 'Essentials',
    farben: ['rot', 'schwarz', 'weiss', 'rot transparent', 'camouflage', 'blau transparent', 'silvertech'],
    varianten_artikelnummern: ['1.3603', '1.3603.3', '1.3603.7', '1.3603.T', '1.3603.94', '1.3603.T2', '1.3603.T7'],
    url: 'https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Spartan/p/1.3603/',
    bild_url: 'https://imageengine.victorinox.com/transform/3e41526b-7ced-4cc1-8fee-c8447ed9d818/SAK_1_3603_S1',
  },
  '1.3703': {
    artikelnummer: '1.3703', name: 'Climber', preis_chf: 37, lagerstatus: 'inStock',
    kategorien: ['Everyday', 'Personalisieren'], shop_kategorie: 'Essentials',
    farben: ['rot', 'schwarz', 'weiss', 'rot transparent', 'camouflage', 'blau transparent', 'silvertech'],
    varianten_artikelnummern: ['1.3703', '1.3703.3', '1.3703.7', '1.3703.T', '1.3703.94', '1.3703.T2', '1.3703.T7'],
    url: 'https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Climber/p/1.3703/',
    bild_url: 'https://imageengine.victorinox.com/transform/b930a3ee-e28e-40e8-bb94-6f4dbc02bddf/SAK_1_3703__S1',
  },
  '1.4603': {
    artikelnummer: '1.4603', name: 'Tinker', preis_chf: 25, lagerstatus: 'inStock',
    kategorien: ['Everyday'], shop_kategorie: 'Essentials', farben: ['rot'],
    varianten_artikelnummern: ['1.4603'],
    url: 'https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Tinker/p/1.4603/',
    bild_url: 'https://imageengine.victorinox.com/transform/f0cc93cf-2dd3-4fa9-b5e9-01c14762e8a4/SAK_1_4603__S1',
  },
  '1.3713': {
    artikelnummer: '1.3713', name: 'Huntsman', preis_chf: 43, lagerstatus: 'inStock',
    kategorien: ['Outdoor & Sports', 'Personalisieren'], shop_kategorie: 'Outdoor',
    farben: ['rot', 'schwarz', 'weiss', 'rot transparent', 'camouflage', 'blau transparent', 'silvertech', 'desert camouflage', 'navy camouflage'],
    varianten_artikelnummern: ['1.3713', '1.3713.3', '1.3713.7', '1.3713.T', '1.3713.94', '1.3713.T2', '1.3713.T7', '1.3713.941', '1.3713.942'],
    url: 'https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Outdoor/Huntsman/p/1.3713/',
    bild_url: 'https://imageengine.victorinox.com/transform/be27477a-5deb-4412-87dd-ba03f429520c/SAK_1-3713_S1',
  },
  '1.6703': {
    artikelnummer: '1.6703', name: 'Explorer', preis_chf: 55, lagerstatus: 'inStock',
    kategorien: ['Everyday', 'Personalisieren'], shop_kategorie: 'Essentials', farben: ['rot'],
    varianten_artikelnummern: ['1.6703'],
    url: 'https://www.victorinox.com/de-CH/Produkte/Swiss-Army-Knife%E2%84%A2%C2%A0%C2%A0Tools/Essentials/Explorer/p/1.6703/',
    bild_url: 'https://imageengine.victorinox.com/transform/9ec884fd-9e54-4576-b381-0e1c686031c1/SAK_1_6703__S1',
  },
  '4.3803.1': {
    artikelnummer: '4.3803.1', name: 'Swiss Post Limited Edition Huntsman Lite', preis_chf: 179, lagerstatus: 'outOfStock',
    kategorien: ['Everyday'], shop_kategorie: 'Essentials', farben: ['schwarz'],
    varianten_artikelnummern: ['4.3803.1'],
    url: '',
    bild_url: 'https://imageengine.victorinox.com/transform/93fab081-f580-4497-8be7-5b56fabed311/SAK_4-3803-1-S1',
  },
  '1.7915.T': {
    artikelnummer: '1.7915.T', name: 'Huntsman Lite', preis_chf: 79, lagerstatus: 'inStock',
    kategorien: ['Outdoor & Sports'], shop_kategorie: 'Outdoor', farben: ['rot transparent'],
    varianten_artikelnummern: ['1.7915.T'],
    url: '',
    bild_url: 'https://imageengine.victorinox.com/transform/391f6487-ddf7-41b2-bf37-88c32569aa45/SAK_1_7915_T__S1',
  },
  '1.3613': {
    artikelnummer: '1.3613', name: 'Camper', preis_chf: 33, lagerstatus: 'inStock',
    kategorien: ['Outdoor & Sports', 'Personalisieren'], shop_kategorie: 'Outdoor', farben: ['rot'],
    varianten_artikelnummern: ['1.3613'],
    url: '',
    bild_url: 'https://imageengine.victorinox.com/transform/2674500b-7fdc-42ff-8c2d-c747969c7b64/SAK_1_3613__S1',
  },
}

const BASIS = ['Klinge', 'Kleine Klinge', 'Korkenzieher', 'Dosenöffner', 'Kapselheber', 'Schraubendreher', 'Stechahle', 'Pinzette', 'Zahnstocher']

function merkmale({ laenge, funktionen, werkzeuge, schale = 'Cellidor' }, quelle = DEMO) {
  return [
    { key: 'laenge', label: 'Länge', wert: laenge, quelle },
    { key: 'funktionen', label: 'Funktionen', wert: funktionen, quelle },
    { key: 'werkzeuge', label: 'Werkzeuge', wert: werkzeuge, quelle },
    { key: 'schale', label: 'Schalenmaterial', wert: schale, quelle },
  ]
}

const MERKMALE = {
  '1.3603': merkmale({ laenge: '91 mm', funktionen: 12, werkzeuge: BASIS }),
  '1.3703': merkmale({ laenge: '91 mm', funktionen: 14, werkzeuge: [...BASIS, 'Schere', 'Mehrzweckhaken'] }),
  '1.4603': merkmale({ laenge: '91 mm', funktionen: 12, werkzeuge: BASIS.filter((w) => w !== 'Korkenzieher').concat('Kreuzschlitz-Schraubendreher') }),
  '1.3713': merkmale({ laenge: '91 mm', funktionen: 15, werkzeuge: [...BASIS, 'Schere', 'Säge', 'Mehrzweckhaken'] }),
  '1.6703': merkmale({ laenge: '91 mm', funktionen: 16, werkzeuge: [...BASIS, 'Schere', 'Lupe', 'Kreuzschlitz-Schraubendreher'] }),
  '4.3803.1': merkmale({ laenge: '91 mm', funktionen: 21, werkzeuge: [...BASIS, 'Schere', 'Säge', 'LED-Lampe', 'Kugelschreiber'] }),
  '1.7915.T': merkmale({ laenge: '91 mm', funktionen: 21, werkzeuge: [...BASIS, 'Schere', 'Säge', 'LED-Lampe', 'Kugelschreiber'] }),
}

function empfehlung(artikelnummer, score, begruendung, gruende) {
  return {
    produkt: PRODUKTE[artikelnummer],
    score,
    begruendung,
    gruende,
    merkmale: MERKMALE[artikelnummer] ?? [],
  }
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
      kategorie: 'Taschenmesser (SAK)',
      konfidenz: 0.91,
      merkmale: [
        { key: 'laenge', label: 'Länge', wert: '95 mm', quelle: DEMO },
        { key: 'funktionen', label: 'Funktionen', wert: 11, quelle: DEMO },
        { key: 'werkzeuge', label: 'Werkzeuge', wert: ['Klinge', 'Korkenzieher', 'Dosenöffner', 'Kapselheber', 'Schraubendreher', 'Stechahle', 'Pinzette'], quelle: BILD },
        { key: 'schale', label: 'Schalenmaterial', wert: 'Kunststoff, schwarz', quelle: BILD },
      ],
    },
    empfehlungen: [
      empfehlung('1.3603', 0.87,
        'Der Spartan deckt alle auf dem Foto erkannten Werkzeuge ab, ist fast gleich gross und ebenfalls in Schwarz erhältlich. Er ist der klassische Allrounder im gleichen Preissegment.',
        ['Alle 7 erkannten Werkzeuge vorhanden', 'Ähnliche Grösse (91 mm statt 95 mm)', 'In Schwarz verfügbar (1.3603.3)', 'An Lager']),
      empfehlung('1.3703', 0.81,
        'Gleiche Grundausstattung wie der Spartan, zusätzlich mit Schere und Mehrzweckhaken. Passt, wenn der Kunde etwas mehr Funktionen möchte.',
        ['Alle erkannten Werkzeuge vorhanden', '+ Schere, + Mehrzweckhaken', 'In Schwarz verfügbar']),
      empfehlung('1.3713', 0.72,
        'Deutlich mehr Funktionen (u. a. Säge). Nur sinnvoll, wenn der Kunde ein Upgrade sucht.',
        ['Alle erkannten Werkzeuge vorhanden', '+ Schere, Säge, Haken', 'Höherer Preis']),
    ],
    rueckfrage: null,
    schritte: schritte({
      vision: { detail: 'Taschenmesser erkannt, aufgeklappt, 7 Werkzeuge sichtbar' },
      marke: { detail: 'SWIZA-Logo auf der Klinge, Modell D03' },
      ocr: { detail: '„SWIZA“ auf der Klinge gelesen' },
      suche: { detail: '247 Victorinox-Produkte verglichen, Top 3 ausgewählt' },
      empfehlung: { detail: 'Gewichtet nach Werkzeugen, Grösse, Verfügbarkeit' },
    }),
  }),

  // Ausgelaufenes Victorinox-Produkt → aktueller Nachfolger
  victorinox: () => ({
    pfad: 'nachfolger',
    erkannt: {
      marke: 'Victorinox',
      ist_victorinox: true,
      modell: 'Swiss Post Limited Edition Huntsman Lite',
      artikelnummer: '4.3803.1',
      kategorie: 'Taschenmesser (SAK)',
      konfidenz: 0.94,
      produkt: PRODUKTE['4.3803.1'],
      merkmale: MERKMALE['4.3803.1'],
    },
    empfehlungen: [
      empfehlung('1.7915.T', 0.95,
        'Die Limited Edition ist nicht mehr verfügbar. Der Huntsman Lite ist das gleiche Basismodell in der regulären Serie, mit identischer Werkzeugausstattung und an Lager.',
        ['Gleiches Basismodell', 'Identische Werkzeuge inkl. LED & Kugelschreiber', 'An Lager', 'Günstiger (CHF 79 statt 179)']),
      empfehlung('1.3713', 0.78,
        'Der Huntsman bietet die gleiche Grundausstattung ohne LED-Lampe und Kugelschreiber.',
        ['Gleiche Grösse', 'Ohne LED & Kugelschreiber', 'An Lager']),
      empfehlung('1.6703', 0.7,
        'Alternative mit Lupe und Kreuzschlitz-Schraubendreher statt Säge.',
        ['Gleiche Grösse', 'Andere Zusatzwerkzeuge']),
    ],
    rueckfrage: null,
    schritte: schritte({
      vision: { detail: 'Taschenmesser erkannt, schwarze Schale mit Aufdruck' },
      marke: { detail: 'Victorinox-Kreuz erkannt' },
      ocr: { detail: 'Aufdruck „Swiss Post“ gelesen' },
      suche: { detail: 'Treffer: 4.3803.1, Status „nicht verfügbar“' },
      empfehlung: { detail: 'Nachfolger über Basismodell Huntsman Lite ermittelt' },
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
      kategorie: 'Taschenmesser (SAK)',
      konfidenz: 0.48,
      merkmale: [
        { key: 'laenge', label: 'Länge', wert: 'ca. 91 mm', quelle: BILD },
        { key: 'schale', label: 'Schalenmaterial', wert: 'Cellidor, rot', quelle: BILD },
      ],
    },
    empfehlungen: [
      empfehlung('1.3703', 0.58, 'Form und Farbe passen. Die Werkzeuge sind auf dem Foto nicht eindeutig erkennbar.', ['Form & Farbe passen', 'Werkzeuge unklar']),
      empfehlung('1.3603', 0.56, 'Sieht geschlossen fast identisch aus wie der Climber.', ['Form & Farbe passen', 'Werkzeuge unklar']),
      empfehlung('1.4603', 0.55, 'Ebenfalls 91 mm mit roter Schale; unterscheidet sich nur in den Werkzeugen.', ['Form & Farbe passen', 'Werkzeuge unklar']),
    ],
    rueckfrage: {
      frage: 'Ich bin mir nicht sicher. Kannst du das Messer aufgeklappt fotografieren?',
      hinweis: 'Spartan, Climber und Tinker sehen geschlossen fast gleich aus. Erst die Werkzeuge unterscheiden sie: Der Climber hat eine Schere, der Tinker einen Kreuzschlitz-Schraubendreher statt Korkenzieher.',
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
      kategorie: 'Taschenmesser (SAK)',
      konfidenz: 0.93,
      produkt: PRODUKTE['1.3703'],
      merkmale: MERKMALE['1.3703'],
    },
    empfehlungen: [
      empfehlung('1.3703', 0.93, 'Mit dem zweiten Foto sind Schere und Korkenzieher sichtbar. Das passt nur zum Climber. Er ist aktuell erhältlich.', ['Schere sichtbar → Climber', 'Korkenzieher sichtbar → kein Tinker', 'An Lager']),
      empfehlung('1.3713', 0.66, 'Ähnlich, hat aber zusätzlich eine Säge, die auf dem Foto fehlt.', ['+ Säge (nicht sichtbar)']),
      empfehlung('1.3603', 0.52, 'Ohne Schere, passt daher nicht zum zweiten Foto.', ['Keine Schere']),
    ],
    rueckfrage: null,
    schritte: schritte({
      vision: { detail: 'Zweites Foto kombiniert, 11 Werkzeuge sichtbar' },
      marke: { detail: 'Victorinox Climber' },
      ocr: { detail: 'Keine Artikelnummer nötig' },
      suche: { detail: 'Climber klar vor Huntsman' },
      empfehlung: { detail: 'Produkt aktuell erhältlich' },
    }),
  }),
}

const warte = (ms) => new Promise((r) => setTimeout(r, ms))

export async function match({ vorherigeMatchId, demo } = {}) {
  await warte(1800)
  const szenario = vorherigeMatchId ? 'nachfoto' : SZENARIEN[demo] ? demo : 'konkurrenz'
  return {
    match_id: `mock-${Date.now().toString(36)}`,
    modus: 'mock',
    ...SZENARIEN[szenario](),
  }
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

export function merkmaleFuer(artikelnummer) {
  return MERKMALE[artikelnummer] ?? []
}
