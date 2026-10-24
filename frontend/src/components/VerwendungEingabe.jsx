import { Target } from 'lucide-react'

const BEISPIELE = ['Wandern & Picknick', 'Fischen', 'Handwerk', 'Garten']

/** Freitext: wofür das Messer gebraucht wird. Das Backend gleicht ihn per Embedding mit den Produkten ab. */
export default function VerwendungEingabe({ wert, onAendern, deaktiviert }) {
  return (
    <div>
      <label htmlFor="verwendung" className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-zinc-700">
        <Target className="size-4 text-zinc-400" />
        Wofür brauchst du das Messer? <span className="font-normal text-zinc-400">(optional)</span>
      </label>
      <input
        id="verwendung"
        type="text"
        value={wert}
        maxLength={300}
        disabled={deaktiviert}
        onChange={(e) => onAendern(e.target.value)}
        placeholder="z. B. Wandern mit Picknick und Wein"
        className={`w-full rounded-xl border bg-white px-3.5 py-3 text-[15px] outline-none transition placeholder:text-zinc-400 focus:ring-4 focus:ring-zinc-100 disabled:opacity-60 ${
          wert ? 'border-zinc-900' : 'border-zinc-200'
        }`}
      />
      <div className="mt-2 flex flex-wrap gap-1.5">
        {BEISPIELE.map((b) => (
          <button
            key={b}
            type="button"
            disabled={deaktiviert}
            onClick={() => onAendern(b)}
            className="rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-xs text-zinc-600 transition hover:border-zinc-400 disabled:opacity-60"
          >
            {b}
          </button>
        ))}
      </div>
      <p className="mt-1.5 px-0.5 text-xs text-zinc-500">
        Hilft bei der Auswahl, wenn mehrere Messer auf dem Foto ähnlich aussehen.
      </p>
    </div>
  )
}
