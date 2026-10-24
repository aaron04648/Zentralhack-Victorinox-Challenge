import { motion } from 'framer-motion'
import { CircleCheck, Circle, LoaderCircle, TriangleAlert } from 'lucide-react'

// Die Agenten-Pipeline aus dem README, sichtbar gemacht. Das Backend liefert
// dieselben ids in `schritte`; bis dahin zeigen wir die Standard-Labels.
export const STANDARD_SCHRITTE = [
  { id: 'vision', label: 'Bild analysiert' },
  { id: 'marke', label: 'Marke & Modell erkannt' },
  { id: 'ocr', label: 'Gravur / Artikelnummer gelesen' },
  { id: 'suche', label: 'Katalog durchsucht (Top-k)' },
  { id: 'empfehlung', label: 'Empfehlung bewertet' },
]

function Symbol({ zustand }) {
  if (zustand === 'laeuft') return <LoaderCircle className="size-5 animate-spin text-brand" />
  if (zustand === 'warnung') return <TriangleAlert className="size-5 text-warn" />
  if (zustand === 'fertig') return <CircleCheck className="size-5 text-ok" />
  return <Circle className="size-5 text-zinc-300" />
}

const LIVE_ZUSTAND = { laeuft: 'laeuft', ok: 'fertig', warnung: 'warnung' }

/**
 * @param aktiv  Index des gerade laufenden Schritts (davor = fertig); ohne `live`
 * @param schritte  optional Backend-Schritte mit status/detail
 * @param live  true = Zustand direkt aus schritt.status (Live-Ablauf vom Backend)
 */
export default function AgentSchritte({ aktiv, schritte, live = false }) {
  const liste = schritte?.length ? schritte : STANDARD_SCHRITTE
  return (
    <ol className="space-y-1">
      {liste.map((schritt, i) => {
        let zustand = i < aktiv ? 'fertig' : i === aktiv ? 'laeuft' : 'offen'
        if (zustand === 'fertig' && schritt.status === 'warnung') zustand = 'warnung'
        if (live) zustand = LIVE_ZUSTAND[schritt.status] ?? 'fertig'
        return (
          <motion.li
            key={`${schritt.id}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: zustand === 'offen' ? 0.45 : 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-start gap-3 rounded-xl px-2 py-2"
          >
            <span className="mt-px"><Symbol zustand={zustand} /></span>
            <div className="min-w-0">
              <div className="text-sm font-medium">{schritt.label}</div>
              {zustand !== 'offen' && schritt.detail && (
                <motion.div key={schritt.detail} initial={{ opacity: 0.3 }} animate={{ opacity: 1 }} className="text-xs text-zinc-500">
                  {schritt.detail}
                </motion.div>
              )}
            </div>
          </motion.li>
        )
      })}
    </ol>
  )
}
