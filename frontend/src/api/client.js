import * as mock from './mock.js'

// VITE_USE_MOCK: "true" = immer Mock, "false" = nie Mock,
// sonst ("auto") echtes Backend und Mock nur, wenn ein Endpoint (noch) fehlt.
const MOCK_MODUS = import.meta.env.VITE_USE_MOCK ?? 'auto'

class ApiFehler extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`)
    this.status = status
  }
}

async function request(pfad, optionen) {
  const res = await fetch(pfad, optionen)
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      detail = res.statusText
    }
    throw new ApiFehler(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json()
}

// Fehlt der Endpoint (404/405/501) oder ist das Backend weg, springt der Mock ein.
function endpointFehlt(fehler) {
  return !(fehler instanceof ApiFehler) || [404, 405, 501, 502, 503].includes(fehler.status)
}

async function mitFallback(echt, ersatz) {
  if (MOCK_MODUS === 'true') return ersatz()
  try {
    return await echt()
  } catch (fehler) {
    if (MOCK_MODUS === 'false' || !endpointFehlt(fehler)) throw fehler
    console.info('[api] Mock statt Backend:', fehler.message)
    return ersatz()
  }
}

/**
 * Live-Ablauf: /api/match/stream liefert eine JSON-Zeile pro Ereignis (Schritt, Werkzeuge, Ergebnis).
 * Gibt das Ergebnis zurück; Zwischenstände gehen an onEreignis.
 */
async function matchStream(form, onEreignis) {
  const res = await fetch('/api/match/stream', { method: 'POST', body: form })
  if (!res.ok || !res.body) throw new ApiFehler(res.status, res.statusText)
  const leser = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let puffer = ''
  for (;;) {
    const { value, done } = await leser.read()
    if (done) break
    puffer += value
    const zeilen = puffer.split('\n')
    puffer = zeilen.pop()
    for (const zeile of zeilen) {
      if (!zeile.trim()) continue
      const ereignis = JSON.parse(zeile)
      if (ereignis.typ === 'fehler') throw new ApiFehler(ereignis.status, ereignis.detail)
      if (ereignis.typ === 'ergebnis') return ereignis.ergebnis
      onEreignis?.(ereignis)
    }
  }
  throw new ApiFehler(502, 'Verbindung zur Analyse abgebrochen')
}

/**
 * Foto analysieren und Victorinox-Empfehlung holen.
 * @param {Blob} bild
 * @param {{ kategorie?: string, verwendung?: string, vorherigeMatchId?: string, demo?: string, onEreignis?: Function }} optionen
 *   kategorie = optionaler Hinweis aus dem Dropdown, verwendung = Freitext "wofür", demo steuert nur den Mock
 */
export function match(bild, { kategorie, verwendung, vorherigeMatchId, demo, onEreignis } = {}) {
  return mitFallback(
    async () => {
      const form = new FormData()
      form.append('bild', bild, 'foto.jpg')
      if (kategorie) form.append('kategorie', kategorie)
      if (verwendung) form.append('verwendung', verwendung)
      if (vorherigeMatchId) form.append('vorherige_match_id', vorherigeMatchId)
      try {
        return { modus: 'live', ...(await matchStream(form, onEreignis)) }
      } catch (fehler) {
        // Älteres Backend ohne Stream-Endpoint: normale Anfrage
        if (!(fehler instanceof ApiFehler) || ![404, 405].includes(fehler.status)) throw fehler
        return { modus: 'live', ...(await request('/api/match', { method: 'POST', body: form })) }
      }
    },
    () => mock.match({ kategorie, vorherigeMatchId, demo }),
  )
}

/**
 * Röntgenblick direkt nach der Aufnahme: Marke + Werkzeuge mit Position (ohne Katalogsuche, ca. 3 s).
 * Das Backend merkt sich das Ergebnis; match() mit demselben Blob übernimmt es.
 * @returns {{ marke, konfidenz, werkzeuge }} oder null (Mock / Clef nicht aktiv)
 */
export function roentgen(bild) {
  return mitFallback(
    async () => {
      const form = new FormData()
      form.append('bild', bild, 'foto.jpg')
      return request('/api/roentgen', { method: 'POST', body: form })
    },
    async () => null,
  )
}

/**
 * Vom Nutzer korrigierte Werkzeugliste schicken und ohne neues Foto erneut suchen.
 * @param {{ gruppe: string, wahrscheinlichkeit?: number | null }[]} werkzeuge  komplette Liste, 1.0 = sicher
 * @returns neues Match-Ergebnis, im Mock null (dann ändert sich nur die Anzeige)
 */
export function werkzeugeKorrigieren(matchId, werkzeuge) {
  return mitFallback(
    async () => ({
      modus: 'live',
      ...(await request(`/api/match/${encodeURIComponent(matchId)}/werkzeuge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ werkzeuge }),
      })),
    }),
    async () => null,
  )
}

export function feedback({ matchId, korrekt, gewaehlteArtikelnummer }) {
  const body = {
    match_id: matchId,
    korrekt,
    gewaehlte_artikelnummer: gewaehlteArtikelnummer ?? null,
  }
  return mitFallback(
    () =>
      request('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    () => mock.feedback(body),
  )
}

export function produkte({ q = '', kategorie = '', limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({ q, kategorie, limit, offset })
  return mitFallback(
    () => request(`/api/products?${params}`),
    () => mock.produkte({ q, kategorie, limit, offset }),
  )
}

export function produkt(artikelnummer) {
  return mitFallback(
    () => request(`/api/products/${encodeURIComponent(artikelnummer)}`),
    () => mock.produkt(artikelnummer),
  )
}
