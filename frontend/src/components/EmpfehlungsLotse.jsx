import { useEffect, useMemo, useState } from 'react'
import { Check, Compass, RotateCcw, Sparkles } from 'lucide-react'

const PRIORITAETEN = [
  { id: 'nah', label: 'Möglichst ähnlich', hint: 'Werkzeuge beibehalten' },
  { id: 'preis', label: 'Günstiger', hint: 'Preis stärker gewichten' },
  { id: 'umfang', label: 'Mehr Funktionen', hint: 'Ausstattung erweitern' },
  { id: 'lager', label: 'Sofort verfügbar', hint: 'Lagerstatus priorisieren' },
]

const EINSATZE = [
  { id: 'Everyday', label: 'Alltag' },
  { id: 'Outdoor & Sports', label: 'Draussen' },
  { id: 'Trades & Crafts', label: 'Arbeit & Reparatur' },
]

function werkzeugeVon(empfehlung) {
  return empfehlung.produkt.werkzeuge ?? []
}

function score(empfehlung, start, prioritaet, einsatz, erkannt) {
  const p = empfehlung.produkt
  let wert = empfehlung.score ?? 0
  if (einsatz) wert += p.kategorien?.includes(einsatz) ? 0.16 : -0.08
  if (prioritaet === 'preis') {
    const preise = start.map((e) => e.produkt.preis_chf).filter(Number.isFinite)
    if (Number.isFinite(p.preis_chf) && preise.length) {
      wert += (Math.max(...preise) - p.preis_chf) / (Math.max(...preise) - Math.min(...preise) || 1) * 0.24
    }
  }
  if (prioritaet === 'umfang') {
    const max = Math.max(...start.map((e) => e.produkt.anzahl_werkzeuge ?? 0), 1)
    wert += ((p.anzahl_werkzeuge ?? 0) / max) * 0.18
  }
  if (prioritaet === 'lager') wert += p.lagerstatus === 'inStock' ? 0.2 : -0.2
  if (prioritaet === 'nah' && erkannt.length) {
    const vorhanden = new Set(werkzeugeVon(empfehlung))
    wert += erkannt.filter((w) => vorhanden.has(w.label)).length / erkannt.length * 0.16
  }
  return wert
}

export default function EmpfehlungsLotse({ empfehlungen, erkannt, onEmpfehlung }) {
  const [prioritaet, setPrioritaet] = useState(null)
  const [einsatz, setEinsatz] = useState(null)

  const rangliste = useMemo(() => {
    if (!prioritaet && !einsatz) return empfehlungen
    const start = empfehlungen
    const erkannteWerkzeuge = erkannt?.merkmale?.find((m) => m.key === 'werkzeuge')?.wert ?? []
    return [...empfehlungen].sort((a, b) =>
      score(b, start, prioritaet, einsatz, erkannteWerkzeuge) - score(a, start, prioritaet, einsatz, erkannteWerkzeuge),
    )
  }, [empfehlungen, erkannt, prioritaet, einsatz])

  const aktiv = Boolean(prioritaet || einsatz)
  const top = rangliste[0]
  const original = empfehlungen[0]
  const aktualisiert = aktiv && top?.produkt.artikelnummer !== original?.produkt.artikelnummer

  useEffect(() => {
    if (aktiv && top) onEmpfehlung?.(top)
  }, [aktiv, top, onEmpfehlung])

  function zuruecksetzen() {
    setPrioritaet(null)
    setEinsatz(null)
  }

  return (
    <section aria-labelledby="lotse-titel" className="mt-6 overflow-hidden rounded-2xl border border-zinc-200 bg-white">
      <div className="border-b border-zinc-100 bg-zinc-900 px-4 py-4 text-white sm:px-5">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-white/10 p-2"><Compass className="size-5" /></div>
          <div>
            <h2 id="lotse-titel" className="font-semibold">Gemeinsam die passende Wahl finden</h2>
            <p className="mt-1 text-sm text-zinc-300">Tippe an, was dir wichtig ist. Du kannst beides auswählen.</p>
          </div>
        </div>
      </div>

      <div className="space-y-5 p-4 sm:p-5">
        <fieldset>
          <legend className="mb-2 text-sm font-semibold">Was zählt am meisten?</legend>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {PRIORITAETEN.map((option) => {
              const selected = prioritaet === option.id
              return (
                <button key={option.id} type="button" aria-pressed={selected}
                  onClick={() => setPrioritaet(selected ? null : option.id)}
                  className={`min-h-16 rounded-xl border px-3 py-2 text-left transition-colors active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${selected ? 'border-brand bg-brand-soft text-brand-dark' : 'border-zinc-200 hover:border-zinc-400'}`}>
                  <span className="flex items-center justify-between gap-1 text-sm font-semibold">{option.label}{selected && <Check className="size-4" />}</span>
                  <span className="mt-0.5 block text-xs opacity-70">{option.hint}</span>
                </button>
              )
            })}
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-2 text-sm font-semibold">Wofür soll es passen?</legend>
          <div className="flex flex-wrap gap-2">
            {EINSATZE.map((option) => {
              const selected = einsatz === option.id
              return (
                <button key={option.id} type="button" aria-pressed={selected}
                  onClick={() => setEinsatz(selected ? null : option.id)}
                  className={`rounded-full border px-3.5 py-2 text-sm font-medium transition-colors active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${selected ? 'border-brand bg-brand text-white' : 'border-zinc-200 bg-white hover:border-zinc-400'}`}>
                  {option.label}
                </button>
              )
            })}
          </div>
        </fieldset>

        {aktiv && top && (
          <div aria-live="polite" className="rounded-xl border border-brand/20 bg-brand-soft/50 p-3.5">
            <div className="flex items-start gap-2">
              <Sparkles className="mt-0.5 size-4 shrink-0 text-brand" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-zinc-900">
                  {aktualisiert ? `Mit deinen Wünschen passt ${top.produkt.name} am besten.` : `${top.produkt.name} bleibt die beste Wahl.`}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-zinc-700">
                  {prioritaet === 'preis' && Number.isFinite(top.produkt.preis_chf) && `Preis: CHF ${new Intl.NumberFormat('de-CH').format(top.produkt.preis_chf)}. `}
                  {prioritaet === 'lager' && (top.produkt.lagerstatus === 'inStock' ? 'Laut Katalog an Lager. ' : 'Aktuell laut Katalog nicht verfügbar. ')}
                  {prioritaet === 'umfang' && top.produkt.anzahl_werkzeuge != null && `${top.produkt.anzahl_werkzeuge} Funktionen laut Katalog. `}
                  {einsatz && `Kategorie: ${EINSATZE.find((e) => e.id === einsatz)?.label}. `}
                  Die Auswahl basiert auf den {empfehlungen.length} erkannten Kandidaten und den hinterlegten Produktdaten.
                </p>
              </div>
              <button type="button" onClick={zuruecksetzen} className="shrink-0 rounded-lg p-2 text-zinc-600 hover:bg-white focus-visible:outline-2 focus-visible:outline-brand" aria-label="Auswahl zurücksetzen" title="Zurücksetzen">
                <RotateCcw className="size-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
