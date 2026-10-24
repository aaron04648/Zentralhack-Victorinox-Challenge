import { PencilLine } from 'lucide-react'

export const MAX_BESCHREIBUNG = 300

/**
 * Freitext zum Foto (optional). Wird als `beschreibung` an /api/match geschickt;
 * das Backend wertet ihn noch nicht aus (siehe docs/api.md).
 */
export default function BeschreibungFeld({ wert, onAendern, deaktiviert }) {
  return (
    <div>
      <label htmlFor="beschreibung" className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-zinc-700">
        <PencilLine className="size-4 text-zinc-400" />
        Zusätzliche Angaben <span className="font-normal text-zinc-400">(optional)</span>
      </label>
      <textarea
        id="beschreibung"
        rows={3}
        value={wert}
        maxLength={MAX_BESCHREIBUNG}
        disabled={deaktiviert}
        onChange={(e) => onAendern(e.target.value)}
        placeholder="z. B. Marke, Artikelnummer, Farbe oder besondere Werkzeuge"
        className="w-full resize-none rounded-xl border border-zinc-200 bg-white px-3.5 py-3 text-[15px] outline-none transition placeholder:text-zinc-400 focus:border-zinc-400 focus:ring-4 focus:ring-zinc-100 disabled:opacity-60"
      />
      <p className="mt-1 px-0.5 text-right text-xs text-zinc-400">
        {wert.length}/{MAX_BESCHREIBUNG}
      </p>
    </div>
  )
}
