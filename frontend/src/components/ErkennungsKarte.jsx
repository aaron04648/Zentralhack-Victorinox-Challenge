import { ShieldCheck, Store, Wrench } from 'lucide-react'
import KonfidenzRing from './KonfidenzRing.jsx'
import { Badge, Karte, StatusBadge } from './ui.jsx'

const SICHER = 0.5 // ab dieser Wahrscheinlichkeit gilt ein Werkzeug als sicher erkannt

/** Erkannte Werkzeuge: aus der Bilderkennung (mit Wahrscheinlichkeit) oder, im Mock, aus den Merkmalen. */
function erkannteWerkzeuge(erkannt) {
  if (erkannt.werkzeuge?.length) return erkannt.werkzeuge
  const merkmal = erkannt.merkmale?.find((m) => m.key === 'werkzeuge')
  return (merkmal?.wert ?? []).map((label) => ({ label, wahrscheinlichkeit: null }))
}

/** Was der Agent auf dem Foto erkannt hat, klar getrennt nach Victorinox und Konkurrenz. */
export default function ErkennungsKarte({ vorschau, erkannt }) {
  const werkzeuge = erkannt.ist_victorinox ? [] : erkannteWerkzeuge(erkannt)
  const sicher = werkzeuge.filter((w) => w.wahrscheinlichkeit == null || w.wahrscheinlichkeit >= SICHER)
  const unsicher = werkzeuge.filter((w) => w.wahrscheinlichkeit != null && w.wahrscheinlichkeit < SICHER)
  return (
    <Karte className="p-4">
    <div className="flex items-center gap-4">
      <img src={vorschau} alt="Dein Foto" className="size-20 shrink-0 rounded-xl border border-zinc-100 bg-white object-contain sm:size-24" />
      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
          {erkannt.ist_victorinox ? (
            <Badge ton="ok" icon={ShieldCheck}>Victorinox</Badge>
          ) : (
            <Badge ton="warn" icon={Store}>Konkurrenz · {erkannt.marke}</Badge>
          )}
          {erkannt.produkt && <StatusBadge status={erkannt.produkt.lagerstatus} />}
        </div>
        <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">Erkannt</div>
        <div className="line-clamp-2 text-lg font-semibold leading-tight">
          {erkannt.modell ? `${erkannt.marke} ${erkannt.modell}` : `${erkannt.marke}, Modell unklar`}
        </div>
        <div className="truncate text-sm text-zinc-500">
          {erkannt.artikelnummer ? `Art.-Nr. ${erkannt.artikelnummer}` : 'Keine Artikelnummer erkannt'}
          {erkannt.kategorie && ` · ${erkannt.kategorie}`}
        </div>
      </div>
      <KonfidenzRing wert={erkannt.konfidenz} groesse={60} label="Sicherheit" />
    </div>
    {werkzeuge.length > 0 && (
      <div className="mt-4 border-t border-zinc-100 pt-3">
        <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-zinc-500">
          <Wrench className="size-3.5" />
          Erkannte Werkzeuge ({werkzeuge.length})
        </div>
        <div className="flex flex-wrap gap-1.5">
          {sicher.map((w) => (
            <span key={w.label} className="rounded-full bg-zinc-900 px-2.5 py-1 text-xs font-medium text-white">
              {w.label}
            </span>
          ))}
          {unsicher.map((w) => (
            <span
              key={w.label}
              title={`Wahrscheinlichkeit ${Math.round(w.wahrscheinlichkeit * 100)} %`}
              className="rounded-full border border-dashed border-zinc-300 px-2.5 py-1 text-xs text-zinc-500"
            >
              {w.label}?
            </span>
          ))}
        </div>
        {unsicher.length > 0 && (
          <p className="mt-2 text-[11px] text-zinc-400">Gestrichelt = unsicher erkannt, zählt beim Vergleich weniger.</p>
        )}
      </div>
    )}
    </Karte>
  )
}
