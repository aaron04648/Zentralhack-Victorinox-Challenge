import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import * as api from '../api/client.js'
import { bereiteFotoVor } from '../lib/image.js'

// Hält alle Scans der Sitzung: Vorschau, laufende Anfrage, Ergebnis, Feedback.
// Fertige Scans landen (ohne Foto-Blob) im localStorage für "Zuletzt gescannt".

const SPEICHER_KEY = 'scans'
const MAX_GESPEICHERT = 8

const ScanContext = createContext(null)

function ladeGespeichert() {
  try {
    return JSON.parse(localStorage.getItem(SPEICHER_KEY) ?? '{}')
  } catch {
    return {}
  }
}

function speichere(scans) {
  const fertig = Object.values(scans)
    .filter((s) => s.status === 'fertig')
    .sort((a, b) => b.zeit - a.zeit)
    .slice(0, MAX_GESPEICHERT)
  try {
    localStorage.setItem(SPEICHER_KEY, JSON.stringify(Object.fromEntries(fertig.map((s) => [s.id, s]))))
  } catch {
    // Speicher voll oder gesperrt: dann eben nur für diese Sitzung.
  }
}

export function ScanProvider({ children }) {
  const [scans, setScans] = useState(ladeGespeichert)
  const anfragen = useRef({})

  useEffect(() => speichere(scans), [scans])

  const aktualisiere = useCallback((id, aenderung) => {
    setScans((alt) => ({ ...alt, [id]: { ...alt[id], ...aenderung } }))
  }, [])

  const starteScan = useCallback(
    async (datei, { demo, kategorie, beschreibung, vorherigerScanId } = {}) => {
      const id = Date.now().toString(36)
      const { upload, vorschau } = await bereiteFotoVor(datei)
      const vorheriger = vorherigerScanId ? scans[vorherigerScanId] : null
      const vorherigeMatchId = vorheriger?.ergebnis?.match_id
      kategorie = kategorie ?? vorheriger?.kategorie ?? ''
      beschreibung = beschreibung ?? vorheriger?.beschreibung ?? ''

      setScans((alt) => ({
        ...alt,
        [id]: { id, zeit: Date.now(), vorschau, kategorie, beschreibung, status: 'laeuft', vorherigerScanId: vorherigerScanId ?? null },
      }))

      anfragen.current[id] = api
        .match(upload, { demo, kategorie, beschreibung, vorherigeMatchId })
        .then((ergebnis) => {
          aktualisiere(id, { status: 'fertig', ergebnis })
          return ergebnis
        })
        .catch((fehler) => {
          aktualisiere(id, { status: 'fehler', fehler: fehler.message })
          throw fehler
        })

      return id
    },
    [scans, aktualisiere],
  )

  const warteAuf = useCallback((id) => anfragen.current[id] ?? null, [])

  const sendeFeedback = useCallback(
    async (id, { korrekt, gewaehlteArtikelnummer }) => {
      const scan = scans[id]
      await api.feedback({ matchId: scan?.ergebnis?.match_id, korrekt, gewaehlteArtikelnummer })
      aktualisiere(id, { feedback: { korrekt, gewaehlteArtikelnummer: gewaehlteArtikelnummer ?? null } })
    },
    [scans, aktualisiere],
  )

  const verlauf = Object.values(scans)
    .filter((s) => s.status === 'fertig')
    .sort((a, b) => b.zeit - a.zeit)

  return (
    <ScanContext.Provider value={{ scans, verlauf, starteScan, warteAuf, sendeFeedback }}>
      {children}
    </ScanContext.Provider>
  )
}

export function useScans() {
  return useContext(ScanContext)
}
