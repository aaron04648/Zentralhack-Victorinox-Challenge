import { useState } from 'react'
import { Link } from 'react-router-dom'
import { LoaderCircle } from 'lucide-react'
import { Suchfeld, useProduktSuche } from '../components/ProduktSuche.jsx'
import { ProduktBild, StatusBadge } from '../components/ui.jsx'
import { chf } from '../lib/format.js'

const KATEGORIEN = ['', 'Everyday', 'Outdoor & Sports', 'Trades & Crafts', 'Swiss Tools', 'Accessoires']

export default function CatalogPage() {
  const [q, setQ] = useState('')
  const [kategorie, setKategorie] = useState('')
  const [limit, setLimit] = useState(48)
  const { laedt, produkte, anzahl, fehler } = useProduktSuche(q, { kategorie, limit })

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Katalog</h1>
      <p className="mt-1 text-sm text-zinc-500">Victorinox Swiss Army Knives &amp; Tools · manuelle Suche</p>

      <div className="sticky top-14 z-20 -mx-4 mt-4 space-y-3 bg-zinc-50/95 px-4 pb-3 pt-1 backdrop-blur">
        <Suchfeld wert={q} onAendern={setQ} />
        <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4">
          {KATEGORIEN.map((k) => (
            <button
              key={k || 'alle'}
              onClick={() => setKategorie(k)}
              className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                kategorie === k ? 'bg-zinc-900 text-white' : 'border border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-100'
              }`}
            >
              {k || 'Alle'}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3 text-xs text-zinc-500">{laedt ? 'Suche …' : `${anzahl} Produkte`}</div>

      {fehler && <p className="text-sm text-brand">{fehler}</p>}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {produkte.map((p) => (
          <Link
            key={p.artikelnummer}
            to={`/produkt/${encodeURIComponent(p.artikelnummer)}`}
            className="group flex flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <ProduktBild url={p.bild_url} alt={p.name} breite={320} className="aspect-square p-3 transition group-hover:scale-[1.03]" />
            <div className="flex flex-1 flex-col border-t border-zinc-100 p-3">
              <div className="line-clamp-2 text-sm font-semibold leading-snug">{p.name}</div>
              <div className="mt-0.5 text-xs text-zinc-500">{p.artikelnummer}</div>
              <div className="mt-auto flex items-center justify-between gap-2 pt-2">
                <span className="text-sm font-semibold">{chf(p.preis_chf)}</span>
                {p.lagerstatus && <StatusBadge status={p.lagerstatus} />}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {laedt && produkte.length === 0 && <LoaderCircle className="mx-auto mt-10 size-6 animate-spin text-zinc-400" />}
      {!laedt && produkte.length === 0 && !fehler && <p className="mt-10 text-center text-sm text-zinc-500">Keine Produkte gefunden.</p>}

      {produkte.length < anzahl && (
        <button
          onClick={() => setLimit((l) => l + 48)}
          className="mx-auto mt-6 block rounded-xl border border-zinc-200 bg-white px-5 py-2.5 text-sm font-medium hover:bg-zinc-50"
        >
          Mehr laden ({anzahl - produkte.length} weitere)
        </button>
      )}
    </div>
  )
}
