import { motion } from 'framer-motion'
import { CircleCheck, CircleHelp, CircleX, LoaderCircle, ZoomIn } from 'lucide-react'
import { Karte } from './ui.jsx'

const URTEIL = {
  laeuft: { text: 'wird geprüft', Symbol: LoaderCircle, farbe: 'text-zinc-400', rahmen: 'ring-zinc-200', drehen: true },
  bestaetigt: { text: 'bestätigt', Symbol: CircleCheck, farbe: 'text-ok', rahmen: 'ring-ok/60' },
  unsicher: { text: 'unsicher', Symbol: CircleHelp, farbe: 'text-warn', rahmen: 'ring-warn/60' },
  verworfen: { text: 'verworfen', Symbol: CircleX, farbe: 'text-brand', rahmen: 'ring-brand' },
}

/**
 * Zweiter Blick live: der vergrösserte Ausschnitt um jedes erkannte Werkzeug und Clefs Urteil dazu.
 * Verworfene Werkzeuge (Fehlalarme) werden durchgestrichen und fallen aus der Werkzeugliste.
 *
 * @param werkzeuge  [{gruppe, label, bild, urteil, wahrscheinlichkeit?}]
 */
export default function WerkzeugPruefung({ werkzeuge }) {
  const fertig = werkzeuge.every((w) => w.urteil !== 'laeuft')
  const verworfen = werkzeuge.filter((w) => w.urteil === 'verworfen').length
  return (
    <Karte className="mt-4 p-4">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
          <ZoomIn className="size-4 text-brand" /> Zweiter Blick auf die Werkzeuge
        </div>
        <span className="text-xs text-zinc-500">
          {fertig
            ? verworfen
              ? `${verworfen} Fehlalarm${verworfen > 1 ? 'e' : ''} verworfen`
              : 'alle bestätigt'
            : `${werkzeuge.length} Ausschnitte vergrössert …`}
        </span>
      </div>
      <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {werkzeuge.map((w, i) => {
          const u = URTEIL[w.urteil] ?? URTEIL.laeuft
          const weg = w.urteil === 'verworfen'
          return (
            <motion.li
              key={w.gruppe}
              title={
                w.wahrscheinlichkeit != null
                  ? `${w.label}: im Ausschnitt zu ${Math.round(w.wahrscheinlichkeit * 100)} % erkannt` +
                    (w.urteil === 'unsicher' ? ' (bleibt in der Liste)' : '')
                  : w.label
              }
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: weg ? 0.6 : 1, scale: 1 }}
              transition={{ delay: i * 0.04 }}
              className="min-w-0"
            >
              <div className={`relative overflow-hidden rounded-xl bg-zinc-100 ring-2 ${u.rahmen}`}>
                {w.bild && (
                  <img src={w.bild} alt={`Ausschnitt ${w.label}`} className={`aspect-square w-full object-cover ${weg ? 'grayscale' : ''}`} />
                )}
                {w.urteil === 'laeuft' && (
                  <motion.div
                    className="absolute inset-x-0 h-1/3 bg-gradient-to-b from-transparent via-brand/25 to-transparent"
                    animate={{ top: ['-33%', '100%'] }}
                    transition={{ duration: 1.3, repeat: Infinity, ease: 'linear', delay: (i % 4) * 0.2 }}
                  />
                )}
              </div>
              <div className={`mt-1 truncate text-xs font-medium ${weg ? 'text-zinc-400 line-through' : 'text-zinc-800'}`}>
                {w.label}
              </div>
              <div className={`flex items-center gap-1 text-[11px] ${u.farbe}`}>
                <u.Symbol className={`size-3 shrink-0 ${u.drehen ? 'animate-spin' : ''}`} />
                <span className="truncate">{u.text}</span>
              </div>
            </motion.li>
          )
        })}
      </ul>
    </Karte>
  )
}
