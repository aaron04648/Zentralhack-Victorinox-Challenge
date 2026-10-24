import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { RotateCcw, TriangleAlert } from 'lucide-react'
import AgentSchritte, { STANDARD_SCHRITTE } from '../components/AgentSchritte.jsx'
import RoentgenBild from '../components/RoentgenBild.jsx'
import WerkzeugPruefung from '../components/WerkzeugPruefung.jsx'
import { Button, Karte } from '../components/ui.jsx'
import { useScans } from '../state/ScanContext.jsx'

const TAKT_MS = 450 // Tempo, in dem die Schritte während des Wartens "abgehakt" werden

export default function AnalyzePage() {
  const { scanId } = useParams()
  const { scans, warteAuf } = useScans()
  const navigate = useNavigate()
  const scan = scans[scanId]
  const [aktiv, setAktiv] = useState(0)
  const [ergebnis, setErgebnis] = useState(null)
  const [fehler, setFehler] = useState(null)
  // Backend streamt echte Schritte (Live-Ablauf); sonst (Mock, altes Backend) wird simuliert
  const live = scan?.live?.schritte?.length > 0

  // Fortschritt simulieren, bis die Antwort da ist; der letzte Schritt dreht weiter.
  useEffect(() => {
    if (ergebnis || fehler || live) return
    const t = setInterval(() => setAktiv((a) => Math.min(a + 1, STANDARD_SCHRITTE.length - 1)), TAKT_MS)
    return () => clearInterval(t)
  }, [ergebnis, fehler, live])

  useEffect(() => {
    if (scan?.status === 'fertig') {
      setErgebnis(scan.ergebnis)
      return
    }
    const anfrage = warteAuf(scanId)
    if (!anfrage) {
      setFehler('Die Analyse wurde unterbrochen (Seite neu geladen?).')
      return
    }
    let aktuell = true
    anfrage.then((e) => aktuell && setErgebnis(e)).catch((e) => aktuell && setFehler(e.message))
    return () => {
      aktuell = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanId])

  // Antwort da: restliche Schritte zügig abhaken, dann zum Ergebnis.
  useEffect(() => {
    if (!ergebnis) return
    if (live) {
      // Schritte waren schon live zu sehen: kurz das Endergebnis zeigen, dann weiter
      const t = setTimeout(() => navigate(`/ergebnis/${scanId}`, { replace: true }), 1200)
      return () => clearTimeout(t)
    }
    if (aktiv < (ergebnis.schritte?.length || STANDARD_SCHRITTE.length)) {
      const t = setTimeout(() => setAktiv((a) => a + 1), 220)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => navigate(`/ergebnis/${scanId}`, { replace: true }), 500)
    return () => clearTimeout(t)
  }, [ergebnis, aktiv, navigate, scanId, live])

  return (
    <div className="mx-auto max-w-md pt-2">
      <div className="relative mx-auto aspect-[4/5] w-full overflow-hidden rounded-3xl bg-zinc-900 shadow-xl">
        {scan?.vorschau && (
          <RoentgenBild src={scan.vorschau} werkzeuge={scan.live?.werkzeuge} className="size-full bg-white" />
        )}
        {!fehler && !ergebnis && (
          <>
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-brand/5 to-transparent" />
            <div className="scan-line absolute inset-x-0 h-0.5 bg-brand shadow-[0_0_16px_4px_rgba(227,6,19,0.55)]" />
          </>
        )}
        {['left-4 top-4 border-l-2 border-t-2', 'right-4 top-4 border-r-2 border-t-2', 'left-4 bottom-4 border-l-2 border-b-2', 'right-4 bottom-4 border-r-2 border-b-2'].map((pos) => (
          <span key={pos} className={`absolute size-7 border-brand ${pos}`} />
        ))}
      </div>

      {!fehler && scan?.live?.pruefung?.length > 0 && <WerkzeugPruefung werkzeuge={scan.live.pruefung} />}

      <Karte className="mt-4 p-3">
        {fehler ? (
          <div className="flex flex-col items-center gap-3 p-4 text-center">
            <TriangleAlert className="size-8 text-warn" />
            <div>
              <div className="font-semibold">Analyse fehlgeschlagen</div>
              <div className="mt-1 text-sm text-zinc-500">{fehler}</div>
            </div>
            <Button icon={RotateCcw} onClick={() => navigate('/')}>Neues Foto</Button>
          </div>
        ) : (
          <>
            <div className="px-2 pb-1 pt-1 text-xs font-semibold uppercase tracking-wider text-zinc-500">
              {ergebnis ? 'Fertig' : 'Agent arbeitet …'}
            </div>
            {live ? (
              <AgentSchritte live schritte={ergebnis?.schritte ?? scan.live.schritte} />
            ) : (
              <AgentSchritte aktiv={aktiv} schritte={ergebnis?.schritte} />
            )}
          </>
        )}
      </Karte>
    </div>
  )
}
