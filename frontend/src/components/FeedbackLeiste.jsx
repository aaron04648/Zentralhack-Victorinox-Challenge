import { useState } from 'react'
import { CircleCheck, LoaderCircle, ThumbsDown, ThumbsUp } from 'lucide-react'
import Sheet from './Sheet.jsx'
import { ProduktBild } from './ui.jsx'
import { Suchfeld, useProduktSuche } from './ProduktSuche.jsx'

function ProduktZeile({ produkt, onClick, extra }) {
  return (
    <button onClick={onClick} className="flex w-full items-center gap-3 rounded-xl p-2 text-left transition hover:bg-zinc-50">
      <ProduktBild url={produkt.bild_url} alt="" breite={120} className="size-12 shrink-0 rounded-lg border border-zinc-100" />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{produkt.name}</div>
        <div className="truncate text-xs text-zinc-500">{produkt.artikelnummer}</div>
      </div>
      {extra}
    </button>
  )
}

function BessererTreffer({ kandidaten, onWaehle }) {
  const [q, setQ] = useState('')
  const { laedt, produkte } = useProduktSuche(q, { limit: 20 })
  return (
    <div className="space-y-4">
      {kandidaten.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-zinc-500">Andere Kandidaten</div>
          {kandidaten.map((p) => (
            <ProduktZeile key={p.artikelnummer} produkt={p} onClick={() => onWaehle(p)} />
          ))}
        </div>
      )}
      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Im Katalog suchen</div>
        <Suchfeld wert={q} onAendern={setQ} />
        <div className="mt-2 min-h-24">
          {!q.trim() ? (
            <p className="mt-6 text-center text-sm text-zinc-500">Tippe, um den Katalog zu durchsuchen.</p>
          ) : laedt ? (
            <LoaderCircle className="mx-auto mt-6 size-5 animate-spin text-zinc-400" />
          ) : produkte.length === 0 ? (
            <p className="mt-6 text-center text-sm text-zinc-500">Keine Treffer</p>
          ) : (
            produkte.map((p) => <ProduktZeile key={p.artikelnummer} produkt={p} onClick={() => onWaehle(p)} />)
          )}
        </div>
      </div>
    </div>
  )
}

/** Fixe Leiste unten: "korrekt / nicht korrekt", bei "nicht korrekt" besseren Treffer wählen. */
export default function FeedbackLeiste({ feedback, kandidaten, onSenden }) {
  const [sheet, setSheet] = useState(false)
  const [sendet, setSendet] = useState(false)

  async function sende(daten) {
    setSendet(true)
    try {
      await onSenden(daten)
      setSheet(false)
    } finally {
      setSendet(false)
    }
  }

  return (
    <>
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-zinc-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3">
          {feedback ? (
            <div className="flex items-center gap-2 text-sm font-medium text-ok">
              <CircleCheck className="size-5" />
              {feedback.korrekt
                ? 'Danke! Als korrekt markiert.'
                : `Danke! Korrektur gespeichert${feedback.gewaehlteArtikelnummer ? ` (${feedback.gewaehlteArtikelnummer})` : ''}.`}
            </div>
          ) : (
            <>
              <span className="text-sm font-medium leading-tight text-zinc-700">Passt die Empfehlung?</span>
              <div className="flex shrink-0 gap-2">
                <button
                  disabled={sendet}
                  onClick={() => sende({ korrekt: true })}
                  className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-xl bg-ok-soft px-3.5 py-2 text-sm font-semibold text-ok transition hover:brightness-95 disabled:opacity-50"
                >
                  <ThumbsUp className="size-4" /> Korrekt
                </button>
                <button
                  disabled={sendet}
                  onClick={() => setSheet(true)}
                  className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-xl bg-zinc-100 px-3.5 py-2 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-200 disabled:opacity-50"
                >
                  <ThumbsDown className="size-4" /> Falsch
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <Sheet offen={sheet} onSchliessen={() => setSheet(false)} titel="Welches Produkt wäre richtig?">
        <BessererTreffer kandidaten={kandidaten} onWaehle={(p) => sende({ korrekt: false, gewaehlteArtikelnummer: p.artikelnummer })} />
        <button
          disabled={sendet}
          onClick={() => sende({ korrekt: false })}
          className="mt-4 w-full rounded-xl py-2.5 text-sm font-medium text-zinc-500 hover:bg-zinc-50"
        >
          Weiss ich nicht, nur als falsch markieren
        </button>
      </Sheet>
    </>
  )
}
