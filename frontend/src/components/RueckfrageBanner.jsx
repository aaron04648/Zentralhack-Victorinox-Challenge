import { TriangleAlert } from 'lucide-react'
import FotoAufnahme from './FotoAufnahme.jsx'

/** Bei unsicherer Erkennung: nicht raten, sondern gezielt nach einem weiteren Foto fragen. */
export default function RueckfrageBanner({ rueckfrage, onDatei, deaktiviert }) {
  return (
    <div className="rounded-2xl border border-warn/30 bg-warn-soft p-4">
      <div className="flex gap-3">
        <TriangleAlert className="mt-0.5 size-5 shrink-0 text-warn" />
        <div className="min-w-0">
          <div className="font-semibold text-zinc-900">
            {rueckfrage?.frage ?? 'Die Erkennung ist unsicher. Ein weiteres Foto hilft.'}
          </div>
          {rueckfrage?.hinweis && <p className="mt-1 text-sm text-zinc-700">{rueckfrage.hinweis}</p>}
          <div className="mt-3">
            <FotoAufnahme kompakt onDatei={onDatei} deaktiviert={deaktiviert} />
          </div>
        </div>
      </div>
    </div>
  )
}
