import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronRight, Sparkles } from 'lucide-react'
import FotoAufnahme from '../components/FotoAufnahme.jsx'
import { Abschnitt, Badge, Karte } from '../components/ui.jsx'
import { useScans } from '../state/ScanContext.jsx'
import { ladeDemoDatei } from '../lib/image.js'
import { prozent } from '../lib/format.js'

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

  async function scanne(datei, optionen) {
    setLaedt(true)
    setFehler(null)
    try {
      const id = await starteScan(datei, optionen)
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
        <FotoAufnahme onDatei={(datei) => scanne(datei)} deaktiviert={laedt} />
        {fehler && <p className="mt-3 text-center text-sm text-brand">{fehler}</p>}
      </div>

      <Abschnitt titel="Demo-Beispiele">
        <div className="grid grid-cols-3 gap-3">
          {BEISPIELE.map((b) => (
            <button
              key={b.demo}
              disabled={laedt}
              onClick={async () => scanne(await ladeDemoDatei(b.bild), { demo: b.demo })}
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
                      → {top?.produkt.name} · {prozent(top?.score)}
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
