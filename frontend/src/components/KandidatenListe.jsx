import { ProduktBild, StatusBadge } from './ui.jsx'
import { prozent } from '../lib/format.js'

/** Top-k-Kandidaten; Antippen macht einen Kandidaten zur angezeigten Empfehlung. */
export default function KandidatenListe({ empfehlungen, auswahl, onWaehle }) {
  return (
    <div className="no-scrollbar -mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-3 sm:px-0">
      {empfehlungen.map((e, i) => {
        const aktiv = i === auswahl
        return (
          <button
            key={e.produkt.artikelnummer}
            onClick={() => onWaehle(i)}
            className={`w-40 shrink-0 snap-start rounded-2xl border bg-white p-3 text-left transition sm:w-auto ${
              aktiv ? 'border-brand ring-2 ring-brand/20' : 'border-zinc-200 hover:border-zinc-300'
            }`}
          >
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-zinc-400">#{i + 1}</span>
              <span className={aktiv ? 'text-brand' : 'text-zinc-700'}>{prozent(e.score)}</span>
            </div>
            <ProduktBild url={e.produkt.bild_url} alt={e.produkt.name} breite={240} className="my-2 aspect-square rounded-lg" />
            <div className="truncate text-sm font-semibold">{e.produkt.name}</div>
            <div className="mb-1.5 truncate text-xs text-zinc-500">{e.produkt.artikelnummer}</div>
            <StatusBadge status={e.produkt.lagerstatus} />
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-zinc-100">
              <div className={`h-full rounded-full ${aktiv ? 'bg-brand' : 'bg-zinc-400'}`} style={{ width: `${e.score * 100}%` }} />
            </div>
          </button>
        )
      })}
    </div>
  )
}
