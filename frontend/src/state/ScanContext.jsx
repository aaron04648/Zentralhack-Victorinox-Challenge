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
    async (datei, { demo, kategorie, verwendung, vorherigerScanId, vorbereitet } = {}) => {
      const id = Date.now().toString(36)
      // vorbereitet: schon verkleinertes Foto aus der Vorschau, damit das Backend den Röntgenblick wiederverwendet
      const { upload, vorschau } = vorbereitet ?? (await bereiteFotoVor(datei))
      const vorheriger = vorherigerScanId ? scans[vorherigerScanId] : null
      const vorherigeMatchId = vorheriger?.ergebnis?.match_id
      kategorie = kategorie ?? vorheriger?.kategorie ?? ''
      verwendung = verwendung ?? vorheriger?.verwendung ?? ''

      setScans((alt) => ({
        ...alt,
        [id]: { id, zeit: Date.now(), vorschau, kategorie, verwendung, status: 'laeuft', vorherigerScanId: vorherigerScanId ?? null },
      }))

      // Live-Ablauf: Schritte (gleiche id = Update) und erkannte Werkzeuge mit Position
      const live = (ereignis) =>
        setScans((alt) => {
          const bisher = alt[id]?.live ?? { schritte: [], werkzeuge: null }
          const neu =
            ereignis.typ === 'schritt'
              ? {
                  ...bisher,
                  schritte: bisher.schritte.some((s) => s.id === ereignis.schritt.id)
                    ? bisher.schritte.map((s) => (s.id === ereignis.schritt.id ? ereignis.schritt : s))
                    : [...bisher.schritte, ereignis.schritt],
                }
              : ereignis.typ === 'werkzeuge'
                ? { ...bisher, werkzeuge: ereignis.werkzeuge }
                : bisher
          return { ...alt, [id]: { ...alt[id], live: neu } }
        })

      anfragen.current[id] = api
        .match(upload, { demo, kategorie, verwendung, vorherigeMatchId, onEreignis: live })
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

  // Werkzeuge bestätigen/hinzufügen/entfernen -> Backend sucht ohne neues Foto erneut
  const korrigiereWerkzeuge = useCallback(
    async (id, werkzeuge) => {
      const scan = scans[id]
      const alt = scan.ergebnis
      aktualisiere(id, {
        sucheLaeuft: true,
        ergebnis: { ...alt, erkannt: { ...alt.erkannt, werkzeuge } },
      })
      try {
        const neu = await api.werkzeugeKorrigieren(alt.match_id, werkzeuge.filter((w) => w.gruppe))
        aktualisiere(id, {
          sucheLaeuft: false,
          korrekturFehler: null,
          ergebnis: neu ?? { ...alt, erkannt: { ...alt.erkannt, werkzeuge } },
        })
      } catch (fehler) {
        aktualisiere(id, { sucheLaeuft: false, ergebnis: alt, korrekturFehler: fehler.message })
      }
    },
    [scans, aktualisiere],
  )

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
    <ScanContext.Provider value={{ scans, verlauf, starteScan, warteAuf, sendeFeedback, korrigiereWerkzeuge }}>
      {children}
    </ScanContext.Provider>
  )
}

export function useScans() {
  return useContext(ScanContext)
}
