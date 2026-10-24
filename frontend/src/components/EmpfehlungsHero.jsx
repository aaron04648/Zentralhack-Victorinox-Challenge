import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check, ChevronRight, ExternalLink } from 'lucide-react'
import ProduktDaten from './ProduktDaten.jsx'
import { Karte, ProduktBild, StatusBadge } from './ui.jsx'
import { chf } from '../lib/format.js'

const TITEL = {
  ersatz: 'Bester Victorinox-Ersatz',
  nachfolger: 'Empfohlener Nachfolger',
  aktuell: 'Victorinox-Produkt',
}

export default function EmpfehlungsHero({ empfehlung, pfad, rang, unsicher = false }) {
  const { produkt, begruendung, gruende } = empfehlung
  return (
    <motion.div key={produkt.artikelnummer} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Karte className="overflow-hidden">
        <div className="flex items-center justify-between gap-2 bg-zinc-900 px-4 py-2.5 text-white">
          <span className="text-xs font-semibold uppercase tracking-wider">
            {unsicher ? `Kandidat #${rang + 1}` : rang === 0 ? TITEL[pfad] ?? 'Empfehlung' : `Alternative #${rang + 1}`}
          </span>
        </div>

        <div className="grid gap-4 p-4 sm:grid-cols-[220px_1fr]">
          <div className="relative">
            <ProduktBild url={produkt.bild_url} alt={produkt.name} breite={500} className="aspect-square rounded-xl border border-zinc-100 p-3" />
          </div>

          <div className="min-w-0">
            <h2 className="text-2xl font-bold tracking-tight">{produkt.name}</h2>
            <div className="mt-0.5 text-sm text-zinc-500">Art.-Nr. {produkt.artikelnummer}</div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StatusBadge status={produkt.lagerstatus} />
              <span className="text-sm font-semibold">{chf(produkt.preis_chf)}</span>
            </div>

            <p className="mt-4 text-[15px] leading-relaxed text-zinc-700">{begruendung}</p>

            {gruende?.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {gruende.map((g) => (
                  <li key={g} className="inline-flex items-center gap-1 rounded-lg bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-700">
                    <Check className="size-3.5 text-ok" />
                    {g}
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-sm font-medium">
              <Link to={`/produkt/${encodeURIComponent(produkt.artikelnummer)}`} className="inline-flex items-center gap-0.5 text-brand hover:underline">
                Alle Produktdaten <ChevronRight className="size-4" />
              </Link>
              {produkt.url && (
                <a href={produkt.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-zinc-600 hover:underline">
                  victorinox.com <ExternalLink className="size-3.5" />
                </a>
              )}
            </div>
          </div>
        </div>

        <div className="border-t border-zinc-100 p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Produktdaten</div>
          <ProduktDaten produkt={produkt} />
        </div>
      </Karte>
    </motion.div>
  )
}
