import { ShieldCheck, Store } from 'lucide-react'
import KonfidenzRing from './KonfidenzRing.jsx'
import { Badge, Karte, StatusBadge } from './ui.jsx'

/** Was der Agent auf dem Foto erkannt hat, klar getrennt nach Victorinox und Konkurrenz. */
export default function ErkennungsKarte({ vorschau, erkannt }) {
  return (
    <Karte className="flex items-center gap-4 p-4">
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
    </Karte>
  )
}
