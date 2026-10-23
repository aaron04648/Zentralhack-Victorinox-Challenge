import { Equal, Plus, X } from 'lucide-react'
import { Karte, StatusBadge } from './ui.jsx'
import { chf } from '../lib/format.js'

// Vergleich erkanntes Produkt ↔ Empfehlung. Fehlende Werte bleiben "—":
// Es wird nichts ergänzt, was nicht aus einer Quelle kommt.

function zeilenAus(erkannt, empfehlung) {
  const links = Object.fromEntries((erkannt.merkmale ?? []).map((m) => [m.key, m]))
  const rechts = Object.fromEntries((empfehlung.merkmale ?? []).map((m) => [m.key, m]))
  const keys = [...new Set([...Object.keys(links), ...Object.keys(rechts)])]
  return keys.map((key) => ({ key, label: (links[key] ?? rechts[key]).label, links: links[key], rechts: rechts[key] }))
}

function Quelle({ merkmal }) {
  if (!merkmal?.quelle) return null
  return <div className="mt-1 text-[10px] leading-tight text-zinc-400">Quelle: {merkmal.quelle}</div>
}

function Leer() {
  return <span className="text-zinc-300" title="Keine Daten vorhanden">—</span>
}

function Werkzeuge({ links, rechts }) {
  const basis = new Set(links ?? [])
  const ziel = new Set(rechts ?? [])
  const fehlt = [...basis].filter((w) => !ziel.has(w))
  return (
    <div className="flex flex-wrap gap-1">
      {[...ziel].map((w) => {
        const gemeinsam = basis.has(w)
        return (
          <span
            key={w}
            className={`inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[11px] font-medium ${
              gemeinsam ? 'bg-ok-soft text-ok' : 'bg-zinc-100 text-zinc-600'
            }`}
          >
            {!gemeinsam && links && <Plus className="size-3" />}
            {w}
          </span>
        )
      })}
      {fehlt.map((w) => (
        <span key={w} className="inline-flex items-center gap-0.5 rounded-md bg-brand-soft px-1.5 py-0.5 text-[11px] font-medium text-brand-dark line-through decoration-1">
          <X className="size-3" />
          {w}
        </span>
      ))}
    </div>
  )
}

function Wert({ merkmal }) {
  if (merkmal?.wert == null || merkmal.wert === '') return <Leer />
  if (Array.isArray(merkmal.wert)) {
    return (
      <div className="flex flex-wrap gap-1">
        {merkmal.wert.map((w) => (
          <span key={w} className="rounded-md bg-zinc-100 px-1.5 py-0.5 text-[11px] font-medium text-zinc-600">{w}</span>
        ))}
      </div>
    )
  }
  return <span className="font-medium">{String(merkmal.wert)}</span>
}

function Vergleichszeichen({ links, rechts }) {
  if (links?.wert == null || rechts?.wert == null || Array.isArray(links.wert)) return null
  return String(links.wert) === String(rechts.wert) ? (
    <Equal className="size-4 text-ok" aria-label="gleich" />
  ) : (
    <span className="size-2 rounded-full bg-warn" aria-label="abweichend" />
  )
}

export default function VergleichsTabelle({ erkannt, empfehlung }) {
  const zeilen = zeilenAus(erkannt, empfehlung)
  const quellProdukt = erkannt.produkt
  const name = erkannt.modell ? `${erkannt.marke} ${erkannt.modell}` : erkannt.marke

  return (
    <Karte className="overflow-hidden">
      <div className="grid grid-cols-[88px_1fr_1fr] border-b border-zinc-200 bg-zinc-50 text-xs font-semibold sm:grid-cols-[140px_1fr_1fr]">
        <div className="p-3 text-zinc-500">Merkmal</div>
        <div className="truncate border-l border-zinc-200 p-3">{name}</div>
        <div className="truncate border-l border-zinc-200 p-3 text-brand">{empfehlung.produkt.name}</div>
      </div>

      <div className="divide-y divide-zinc-100 text-sm">
        {zeilen.map(({ key, label, links, rechts }) => (
          <div key={key} className="grid grid-cols-[88px_1fr_1fr] sm:grid-cols-[140px_1fr_1fr]">
            <div className="flex items-start justify-between gap-1 hyphens-auto p-3 text-xs font-medium text-zinc-500 [overflow-wrap:anywhere]">
              {label}
              <Vergleichszeichen links={links} rechts={rechts} />
            </div>
            <div className="min-w-0 border-l border-zinc-100 p-3">
              <Wert merkmal={links} />
              <Quelle merkmal={links} />
            </div>
            <div className="min-w-0 border-l border-zinc-100 p-3">
              {key === 'werkzeuge' && Array.isArray(rechts?.wert) ? (
                <Werkzeuge links={links?.wert} rechts={rechts.wert} />
              ) : (
                <Wert merkmal={rechts} />
              )}
              <Quelle merkmal={rechts} />
            </div>
          </div>
        ))}

        <div className="grid grid-cols-[88px_1fr_1fr] sm:grid-cols-[140px_1fr_1fr]">
          <div className="p-3 text-xs font-medium text-zinc-500">Preis</div>
          <div className="border-l border-zinc-100 p-3">{quellProdukt ? chf(quellProdukt.preis_chf) : <Leer />}</div>
          <div className="border-l border-zinc-100 p-3 font-medium">{chf(empfehlung.produkt.preis_chf)}</div>
        </div>
        <div className="grid grid-cols-[88px_1fr_1fr] sm:grid-cols-[140px_1fr_1fr]">
          <div className="p-3 text-xs font-medium text-zinc-500">Status</div>
          <div className="border-l border-zinc-100 p-3">{quellProdukt ? <StatusBadge status={quellProdukt.lagerstatus} /> : <Leer />}</div>
          <div className="border-l border-zinc-100 p-3"><StatusBadge status={empfehlung.produkt.lagerstatus} /></div>
        </div>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-zinc-100 bg-zinc-50 px-3 py-2 text-[11px] text-zinc-500">
        <span className="inline-flex items-center gap-1"><Equal className="size-3 text-ok" /> gleich</span>
        <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-warn" /> abweichend</span>
        <span className="inline-flex items-center gap-1"><X className="size-3 text-brand" /> fehlt in Empfehlung</span>
        <span>— keine Daten</span>
      </div>
    </Karte>
  )
}
