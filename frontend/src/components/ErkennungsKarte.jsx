import { useMemo, useState } from 'react'
import { Loader2, Plus, ShieldCheck, Store, Wrench, X } from 'lucide-react'
import KonfidenzRing from './KonfidenzRing.jsx'
import { Badge, Karte, StatusBadge } from './ui.jsx'
import { BELIEBT, WERKZEUGE } from '../lib/werkzeuge.js'

const SICHER = 0.5 // ab dieser Wahrscheinlichkeit gilt ein Werkzeug als sicher erkannt

/** Erkannte Werkzeuge: aus der Bilderkennung (mit Wahrscheinlichkeit) oder, im Mock, aus den Merkmalen. */
function erkannteWerkzeuge(erkannt) {
  if (erkannt.werkzeuge?.length) return erkannt.werkzeuge
  const merkmal = erkannt.merkmale?.find((m) => m.key === 'werkzeuge')
  return (merkmal?.wert ?? []).map((label) => ({
    gruppe: WERKZEUGE.find((w) => w.label === label)?.gruppe,
    label,
    wahrscheinlichkeit: null,
  }))
}

const istSicher = (w) => w.wahrscheinlichkeit == null || w.wahrscheinlichkeit >= SICHER

/** Was der Agent auf dem Foto erkannt hat, klar getrennt nach Victorinox und Konkurrenz. */
export default function ErkennungsKarte({ vorschau, erkannt, sucheLaeuft, fehler, onWerkzeugeAendern }) {
  const werkzeuge = erkannteWerkzeuge(erkannt)
  return (
    <Karte className="p-4">
      <div className="flex items-center gap-4">
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
      </div>
      {(werkzeuge.length > 0 || onWerkzeugeAendern) && (
        <WerkzeugListe werkzeuge={werkzeuge} sucheLaeuft={sucheLaeuft} fehler={fehler} onAendern={onWerkzeugeAendern} />
      )}
    </Karte>
  )
}

/**
 * Erkannte Werkzeuge zum Korrigieren: sicher = dunkel, unsicher = gestrichelt mit "?".
 * Doppelklick auf ein unsicheres Werkzeug bestätigt es, × entfernt ein Werkzeug, "+" fügt eines hinzu.
 * Jede Änderung startet im Backend eine neue Suche (ohne neues Foto).
 */
function WerkzeugListe({ werkzeuge, sucheLaeuft, fehler, onAendern }) {
  const [hinzufuegen, setHinzufuegen] = useState(false)
  const sicher = werkzeuge.filter(istSicher)
  const unsicher = werkzeuge.filter((w) => !istSicher(w))
  const aenderbar = Boolean(onAendern) && !sucheLaeuft

  function aendere(neu) {
    if (aenderbar) onAendern(neu)
  }
  const bestaetige = (gruppe) => aendere(werkzeuge.map((w) => (w.gruppe === gruppe ? { ...w, wahrscheinlichkeit: 1 } : w)))
  const entferne = (gruppe) => aendere(werkzeuge.filter((w) => w.gruppe !== gruppe))
  const fuegeHinzu = (w) => {
    setHinzufuegen(false)
    aendere([...werkzeuge, { gruppe: w.gruppe, label: w.label, wahrscheinlichkeit: 1 }])
  }

  return (
    <div className="mt-4 border-t border-zinc-100 pt-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-zinc-500">
        <Wrench className="size-3.5" />
        Erkannte Werkzeuge ({werkzeuge.length})
        {sucheLaeuft && (
          <span className="ml-auto flex items-center gap-1 normal-case tracking-normal text-zinc-400">
            <Loader2 className="size-3.5 animate-spin" /> Suche wird aktualisiert …
          </span>
        )}
      </div>
      <div className={`flex flex-wrap gap-1.5 transition ${sucheLaeuft ? 'opacity-60' : ''}`}>
        {sicher.map((w) => (
          <span key={w.gruppe ?? w.label} className="inline-flex items-center gap-1 rounded-full bg-zinc-900 py-1 pl-2.5 pr-1.5 text-xs font-medium text-white">
            {w.label}
            {w.gruppe && onAendern && (
              <button
                type="button"
                disabled={!aenderbar}
                onClick={() => entferne(w.gruppe)}
                aria-label={`${w.label} entfernen`}
                className="rounded-full p-0.5 text-zinc-400 transition hover:bg-zinc-700 hover:text-white"
              >
                <X className="size-3" />
              </button>
            )}
          </span>
        ))}
        {unsicher.map((w) => (
          <button
            key={w.gruppe ?? w.label}
            type="button"
            disabled={!aenderbar}
            onDoubleClick={() => bestaetige(w.gruppe)}
            title={`Unsicher erkannt (${Math.round(w.wahrscheinlichkeit * 100)} %). Doppelklick: Werkzeug ist vorhanden`}
            className="select-none rounded-full border border-dashed border-zinc-300 px-2.5 py-1 text-xs text-zinc-500 transition hover:border-zinc-500 hover:text-zinc-700"
          >
            {w.label}?
          </button>
        ))}
        {onAendern && !hinzufuegen && (
          <button
            type="button"
            disabled={!aenderbar}
            onClick={() => setHinzufuegen(true)}
            className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs font-medium text-zinc-700 transition hover:border-zinc-400"
          >
            <Plus className="size-3" /> Werkzeug
          </button>
        )}
      </div>
      {hinzufuegen && (
        <WerkzeugHinzufuegen
          vorhanden={new Set(werkzeuge.map((w) => w.gruppe))}
          onWaehle={fuegeHinzu}
          onAbbrechen={() => setHinzufuegen(false)}
        />
      )}
      <p className="mt-2 text-[11px] text-zinc-400">
        {unsicher.length > 0 && 'Gestrichelt = Modell ist unsicher, ob das Werkzeug vorhanden ist. Doppelklick bestätigt es. '}
        Fehlt etwas, das dein Messer hat oder das du willst? Mit „+ Werkzeug“ ergänzen.
      </p>
      {fehler && <p className="mt-1 text-xs text-brand">Neue Suche fehlgeschlagen: {fehler}</p>}
    </div>
  )
}

/** Suchfeld mit vorgeschlagenen Werkzeugen (beliebte zuerst, ohne bereits vorhandene). */
function WerkzeugHinzufuegen({ vorhanden, onWaehle, onAbbrechen }) {
  const [suche, setSuche] = useState('')
  const vorschlaege = useMemo(() => {
    const frei = WERKZEUGE.filter((w) => !vorhanden.has(w.gruppe))
    const q = suche.trim().toLowerCase()
    if (q) return frei.filter((w) => `${w.label} ${w.beschreibung}`.toLowerCase().includes(q))
    const rang = (w) => (BELIEBT.includes(w.gruppe) ? BELIEBT.indexOf(w.gruppe) : BELIEBT.length)
    return [...frei].sort((a, b) => rang(a) - rang(b))
  }, [suche, vorhanden])

  return (
    <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50 p-2.5">
      <div className="flex gap-2">
        <input
          autoFocus
          type="text"
          value={suche}
          onChange={(e) => setSuche(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && vorschlaege[0]) onWaehle(vorschlaege[0])
            if (e.key === 'Escape') onAbbrechen()
          }}
          placeholder="Werkzeug suchen, z. B. Schere"
          className="min-w-0 flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:ring-4 focus:ring-zinc-100"
        />
        <button type="button" onClick={onAbbrechen} aria-label="Abbrechen" className="rounded-lg px-2 text-zinc-400 hover:text-zinc-700">
          <X className="size-4" />
        </button>
      </div>
      <div className="mt-2 flex max-h-36 flex-wrap gap-1.5 overflow-y-auto">
        {vorschlaege.map((w) => (
          <button
            key={w.gruppe}
            type="button"
            onClick={() => onWaehle(w)}
            title={w.beschreibung}
            className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-xs text-zinc-700 transition hover:border-zinc-900"
          >
            <Plus className="size-3 text-zinc-400" />
            {w.label}
          </button>
        ))}
        {vorschlaege.length === 0 && <span className="px-1 text-xs text-zinc-400">Kein passendes Werkzeug</span>}
      </div>
    </div>
  )
}
