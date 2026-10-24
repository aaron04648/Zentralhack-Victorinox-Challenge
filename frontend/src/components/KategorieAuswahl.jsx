import { ChevronDown, Tag } from 'lucide-react'
import { KATEGORIEN } from '../lib/kategorien.js'

/** Natives Select (am Handy das System-Auswahlrad), darunter die Erklärung zur Auswahl. */
export default function KategorieAuswahl({ wert, onAendern, deaktiviert }) {
  const aktuell = KATEGORIEN.find((k) => k.wert === wert) ?? KATEGORIEN[0]
  return (
    <div>
      <label htmlFor="kategorie" className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-zinc-700">
        <Tag className="size-4 text-zinc-400" />
        Kategorie <span className="font-normal text-zinc-400">(optional, hilft der Erkennung)</span>
      </label>
      <div className="relative">
        <select
          id="kategorie"
          value={wert}
          disabled={deaktiviert}
          onChange={(e) => onAendern(e.target.value)}
          className={`w-full appearance-none rounded-xl border bg-white py-3 pl-3.5 pr-10 text-[15px] font-medium outline-none transition focus:ring-4 focus:ring-zinc-100 disabled:opacity-60 ${
            wert ? 'border-zinc-900' : 'border-zinc-200 text-zinc-600'
          }`}
        >
          {KATEGORIEN.map((k) => (
            <option key={k.wert || 'auto'} value={k.wert}>{k.label}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-zinc-400" />
      </div>
      <p className="mt-1.5 px-0.5 text-xs text-zinc-500">{aktuell.beschreibung}</p>
    </div>
  )
}
