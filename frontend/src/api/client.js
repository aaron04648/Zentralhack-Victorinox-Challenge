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
 * Foto analysieren und Victorinox-Empfehlung holen.
 * @param {Blob} bild
 * @param {{ kategorie?: string, beschreibung?: string, vorherigeMatchId?: string, demo?: string }} optionen
 *   kategorie = optionaler Hinweis aus dem Dropdown, beschreibung = Freitext (noch nicht ausgewertet),
 *   demo steuert nur den Mock
 */
export function match(bild, { kategorie, beschreibung, vorherigeMatchId, demo } = {}) {
  return mitFallback(
    async () => {
      const form = new FormData()
      form.append('bild', bild, 'foto.jpg')
      if (kategorie) form.append('kategorie', kategorie)
      if (beschreibung) form.append('beschreibung', beschreibung)
      if (vorherigeMatchId) form.append('vorherige_match_id', vorherigeMatchId)
      return { modus: 'live', ...(await request('/api/match', { method: 'POST', body: form })) }
    },
    () => mock.match({ kategorie, vorherigeMatchId, demo }),
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
