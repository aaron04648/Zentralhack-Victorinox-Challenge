import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import * as api from '../api/client.js'

/** Katalogsuche mit kurzer Verzögerung, damit nicht bei jedem Tastendruck angefragt wird. */
export function useProduktSuche(q, { kategorie = '', limit = 50 } = {}) {
  const [stand, setStand] = useState({ laedt: true, produkte: [], anzahl: 0, fehler: null })

  useEffect(() => {
    let aktuell = true
    setStand((s) => ({ ...s, laedt: true }))
    const t = setTimeout(() => {
      api
        .produkte({ q, kategorie, limit })
        .then((r) => aktuell && setStand({ laedt: false, produkte: r.produkte, anzahl: r.anzahl, fehler: null }))
        .catch((e) => aktuell && setStand({ laedt: false, produkte: [], anzahl: 0, fehler: e.message }))
    }, 200)
    return () => {
      aktuell = false
      clearTimeout(t)
    }
  }, [q, kategorie, limit])

  return stand
}

export function Suchfeld({ wert, onAendern, platzhalter = 'Name, Artikelnummer oder Farbe …', autoFocus }) {
  return (
    <label className="relative block">
      <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
      <input
        type="search"
        value={wert}
        autoFocus={autoFocus}
        onChange={(e) => onAendern(e.target.value)}
        placeholder={platzhalter}
        className="w-full rounded-xl border border-zinc-200 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition placeholder:text-zinc-400 focus:border-zinc-400 focus:ring-4 focus:ring-zinc-100"
      />
    </label>
  )
}
