import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronRight, Loader2, RotateCcw, ScanEye, ScanLine, Sparkles } from 'lucide-react'
import FotoAufnahme from '../components/FotoAufnahme.jsx'
import RoentgenBild from '../components/RoentgenBild.jsx'
import VerwendungEingabe from '../components/VerwendungEingabe.jsx'
import { Abschnitt, Badge, Button, Karte } from '../components/ui.jsx'
import { useScans } from '../state/ScanContext.jsx'
import * as api from '../api/client.js'
import { bereiteFotoVor, ladeDemoDatei } from '../lib/image.js'

// Feste Beispiele, damit die Live-Demo auch ohne Kamera/Licht funktioniert.
// `demo` wählt im Mock das passende Szenario; das echte Backend bekommt nur das Bild.
const BEISPIELE = [
  { demo: 'konkurrenz', bild: '/demo/swiza-d03.jpg', titel: 'SWIZA D03', text: 'Konkurrenzprodukt → Victorinox-Ersatz' },
  { demo: 'victorinox', bild: '/demo/huntsman-lite-swiss-post.webp', titel: 'Huntsman Lite Swiss Post', text: 'Ausgelaufen → Nachfolger' },
  { demo: 'unsicher', bild: '/demo/climber-unscharf.webp', titel: 'Unscharfes Foto', text: 'Unsicher → Rückfrage' },
]

export default function ScanPage() {
  const { starteScan, verlauf } = useScans()
  const navigate = useNavigate()
  const [laedt, setLaedt] = useState(false)
  const [fehler, setFehler] = useState(null)
  // Gewähltes, noch nicht analysiertes Foto: Vorschau + optionaler Verwendungszweck, dann "Analysieren"
  const [entwurf, setEntwurf] = useState(null)
  const [verwendung, setVerwendung] = useState('')
  const [hervorgehoben, setHervorgehoben] = useState(null)

  const entwurfUrl = entwurf?.url
  useEffect(() => () => entwurfUrl && URL.revokeObjectURL(entwurfUrl), [entwurfUrl])

  // Röntgenblick startet sofort nach der Aufnahme, noch während der Einsatzzweck eingetippt wird.
  // "Analysieren" schickt danach dieselben Bytes, damit das Backend das Ergebnis übernimmt.
  function waehle(datei, demo) {
    setFehler(null)
    const id = Date.now()
    const vorbereitung = bereiteFotoVor(datei)
    setEntwurf({ id, datei, demo, url: URL.createObjectURL(datei), vorbereitung, roentgen: null, roentgenStatus: 'laeuft' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
    const setzen = (aenderung) => setEntwurf((e) => (e?.id === id ? { ...e, ...aenderung } : e))
    vorbereitung
      .then(({ upload }) => api.roentgen(upload))
      .then((roentgen) => setzen({ roentgen, roentgenStatus: roentgen ? 'ok' : 'aus' }))
      .catch(() => setzen({ roentgenStatus: 'fehler' }))
  }

  async function scanne() {
    setLaedt(true)
    setFehler(null)
    try {
      const vorbereitet = await entwurf.vorbereitung
      const id = await starteScan(entwurf.datei, { demo: entwurf.demo, verwendung: verwendung.trim(), vorbereitet })
      navigate(`/analyse/${id}`)
    } catch (e) {
      setFehler(`Das Bild konnte nicht gelesen werden (${e.message ?? 'unbekannter Fehler'}).`)
      setLaedt(false)
    }
  }

  return (
    <div>
      <div className="pb-6 pt-4 text-center sm:pt-8">
        <Badge ton="brand" icon={Sparkles}>Multimodaler AI-Agent</Badge>
        <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
          Foto rein, <span className="text-brand">Victorinox</span> raus.
        </h1>
        <p className="mx-auto mt-2 max-w-md text-[15px] text-zinc-600">
          Fotografiere ein Taschenmesser. Der Agent erkennt Marke und Modell und schlägt das passende Victorinox-Produkt vor,
          mit technischem Vergleich und Begründung.
        </p>
      </div>

      <div className="mx-auto max-w-md">
        {entwurf ? (
          <Karte className="overflow-hidden">
            <div className="relative aspect-[4/3] overflow-hidden bg-zinc-100">
              <RoentgenBild
                src={entwurf.url}
                werkzeuge={entwurf.roentgen?.werkzeuge}
                hervorgehoben={hervorgehoben}
                onHervorheben={setHervorgehoben}
                className="size-full"
              />
              {entwurf.roentgenStatus === 'laeuft' && (
                <div className="scan-line pointer-events-none absolute inset-x-0 h-0.5 bg-brand shadow-[0_0_14px_3px_rgba(227,6,19,0.55)]" />
              )}
              <RoentgenStatus entwurf={entwurf} />
            </div>
            <div className="space-y-4 p-4">
              <VerwendungEingabe wert={verwendung} onAendern={setVerwendung} deaktiviert={laedt} />
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <Button icon={ScanLine} onClick={scanne} disabled={laedt} className="py-3 text-base">
                  Analysieren
                </Button>
                <Button variante="sekundaer" icon={RotateCcw} onClick={() => setEntwurf(null)} disabled={laedt}>
                  Anderes Foto
                </Button>
              </div>
            </div>
          </Karte>
        ) : (
          <FotoAufnahme onDatei={(datei) => waehle(datei)} deaktiviert={laedt} />
        )}
        {fehler && <p className="mt-3 text-center text-sm text-brand">{fehler}</p>}
      </div>

      <Abschnitt titel="Demo-Beispiele">
        <div className="grid grid-cols-3 gap-3">
          {BEISPIELE.map((b) => (
            <button
              key={b.demo}
              disabled={laedt}
              onClick={async () => waehle(await ladeDemoDatei(b.bild), b.demo)}
              className="group overflow-hidden rounded-2xl border border-zinc-200 bg-white text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md disabled:opacity-60"
            >
              <div className="aspect-square bg-white p-2">
                <img src={b.bild} alt={b.titel} className="size-full object-contain transition group-hover:scale-105" />
              </div>
              <div className="border-t border-zinc-100 p-2.5">
                <div className="truncate text-[13px] font-semibold">{b.titel}</div>
                <div className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-zinc-500">{b.text}</div>
              </div>
            </button>
          ))}
        </div>
      </Abschnitt>

      {verlauf.length > 0 && (
        <Abschnitt titel="Zuletzt gescannt">
          <Karte className="divide-y divide-zinc-100">
            {verlauf.slice(0, 5).map((scan) => {
              const { erkannt, empfehlungen } = scan.ergebnis
              const top = empfehlungen[0]
              return (
                <Link key={scan.id} to={`/ergebnis/${scan.id}`} className="flex items-center gap-3 p-3 transition hover:bg-zinc-50">
                  <img src={scan.vorschau} alt="" className="size-12 rounded-lg border border-zinc-100 object-cover" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {erkannt.modell ? `${erkannt.marke} ${erkannt.modell}` : `${erkannt.marke}, Modell unklar`}
                    </div>
                    <div className="truncate text-xs text-zinc-500">
                      → {top?.produkt.name}
                    </div>
                  </div>
                  <ChevronRight className="size-4 text-zinc-400" />
                </Link>
              )
            })}
          </Karte>
        </Abschnitt>
      )}
    </div>
  )
}

/** Kleiner Hinweis unten links in der Vorschau: läuft / Ergebnis des Röntgenblicks. */
function RoentgenStatus({ entwurf }) {
  const { roentgenStatus: status, roentgen } = entwurf
  if (status !== 'laeuft' && status !== 'ok') return null
  const anzahl = roentgen?.werkzeuge?.filter((w) => w.position).length ?? 0
  return (
    <div className="pointer-events-none absolute bottom-2 left-2 flex items-center gap-1.5 rounded-full bg-zinc-900/80 px-2.5 py-1 text-xs font-medium text-white backdrop-blur">
      {status === 'laeuft' ? (
        <>
          <Loader2 className="size-3.5 animate-spin" /> Röntgenblick läuft …
        </>
      ) : (
        <>
          <ScanEye className="size-3.5" />
          {anzahl} Werkzeuge erkannt{roentgen.marke ? ` · ${roentgen.marke}` : ''}
        </>
      )}
    </div>
  )
}
