import { useCallback, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, FlaskConical, RotateCcw } from 'lucide-react'
import ErkennungsKarte from '../components/ErkennungsKarte.jsx'
import EmpfehlungsHero from '../components/EmpfehlungsHero.jsx'
import KandidatenListe from '../components/KandidatenListe.jsx'
import FeedbackLeiste from '../components/FeedbackLeiste.jsx'
import EmpfehlungsLotse from '../components/EmpfehlungsLotse.jsx'
import { Abschnitt, Badge, Button } from '../components/ui.jsx'
import { useScans } from '../state/ScanContext.jsx'
import { KONFIDENZ_SCHWELLE } from '../lib/format.js'
import { kategorieLabel } from '../lib/kategorien.js'

const PFAD_TEXT = {
  ersatz: 'Konkurrenzprodukt erkannt: Das ist der funktional beste Victorinox-Ersatz.',
  nachfolger: 'Dieses Victorinox-Produkt ist nicht mehr erhältlich. Das sind die aktuellen Alternativen.',
  aktuell: 'Victorinox-Produkt erkannt.',
}

export default function ResultPage() {
  const { scanId } = useParams()
  // key: Auswahl & Ladezustand gehören zum Scan, nicht zur Seite
  return <Ergebnis key={scanId} scanId={scanId} />
}

function Ergebnis({ scanId }) {
  const { scans, sendeFeedback, korrigiereWerkzeuge } = useScans()
  const navigate = useNavigate()
  const [auswahl, setAuswahl] = useState(0)
  const scan = scans[scanId]

  if (!scan) return <Navigate to="/" replace />
  if (scan.status !== 'fertig') return <Navigate to={`/analyse/${scanId}`} replace />

  const { erkannt, empfehlungen, rueckfrage, pfad, modus } = scan.ergebnis
  const unsicher = Boolean(rueckfrage) || erkannt.konfidenz < KONFIDENZ_SCHWELLE
  const empfehlung = empfehlungen[auswahl]
  const waehleEmpfehlung = useCallback((kandidat) => {
    const index = empfehlungen.findIndex((e) => e.produkt.artikelnummer === kandidat.produkt.artikelnummer)
    if (index >= 0) setAuswahl(index)
  }, [empfehlungen])

  return (
    <div>
      {modus === 'mock' && (
        <div className="mb-3 flex justify-end">
          <Badge ton="dunkel" icon={FlaskConical}>Demo-Modus · Mock-Daten</Badge>
        </div>
      )}

      <ErkennungsKarte
        vorschau={scan.vorschau}
        erkannt={erkannt}
        sucheLaeuft={scan.sucheLaeuft}
        fehler={scan.korrekturFehler}
        onWerkzeugeAendern={(werkzeuge) => {
          setAuswahl(0)
          korrigiereWerkzeuge(scanId, werkzeuge)
        }}
      />

      {(scan.vorherigerScanId || scan.kategorie) && (
        <p className="mt-2 px-1 text-xs text-zinc-500">
          {[scan.kategorie && `Kategorie-Hinweis: ${kategorieLabel(scan.kategorie)}`, scan.vorherigerScanId && 'Mit zweitem Foto präzisiert']
            .filter(Boolean)
            .join(' · ')}
        </p>
      )}

      <div className="mt-4">
        <p className="flex items-center gap-2 px-1 text-sm text-zinc-600">
          <ArrowRight className="size-4 shrink-0 text-brand" />
          {PFAD_TEXT[pfad] ?? 'Empfehlung'}
        </p>
      </div>

      {empfehlungen.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-dashed border-zinc-300 p-8 text-center text-sm text-zinc-500">
          Kein passendes Victorinox-Produkt gefunden.
          <div className="mt-4">
            <Button variante="sekundaer" icon={RotateCcw} onClick={() => navigate('/')}>Neues Foto</Button>
          </div>
        </div>
      ) : (
        <>
          {unsicher && (
            <Abschnitt titel="Mögliche Treffer">
              <KandidatenListe empfehlungen={empfehlungen} auswahl={auswahl} onWaehle={setAuswahl} />
            </Abschnitt>
          )}

          {empfehlungen.length > 1 && (
            <EmpfehlungsLotse empfehlungen={empfehlungen} erkannt={erkannt} onEmpfehlung={waehleEmpfehlung} />
          )}

          <div className="mt-6">
            <EmpfehlungsHero empfehlung={empfehlung} pfad={pfad} rang={auswahl} unsicher={unsicher} />
          </div>

          {!unsicher && empfehlungen.length > 1 && (
            <Abschnitt titel="Weitere Kandidaten">
              <KandidatenListe empfehlungen={empfehlungen} auswahl={auswahl} onWaehle={setAuswahl} />
            </Abschnitt>
          )}
        </>
      )}

      <FeedbackLeiste
        feedback={scan.feedback}
        kandidaten={empfehlungen.filter((_, i) => i !== auswahl).map((e) => e.produkt)}
        onSenden={(daten) =>
          sendeFeedback(scanId, {
            ...daten,
            // "Korrekt" bezieht sich auf die gerade angezeigte Empfehlung
            gewaehlteArtikelnummer: daten.korrekt ? empfehlung?.produkt.artikelnummer : daten.gewaehlteArtikelnummer,
          })
        }
      />
    </div>
  )
}
