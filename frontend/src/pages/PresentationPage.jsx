import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import {
  ArrowDown,
  ArrowRight,
  Camera,
  Check,
  CircleAlert,
  Clock,
  Database,
  Layers,
  MessageSquare,
  Plus,
  ScanSearch,
  Sparkles,
  Target,
  Users,
  Workflow,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import KonfidenzRing from '../components/KonfidenzRing.jsx'
import { ProduktBild } from '../components/ui.jsx'

const chapters = [
  { id: 'ausgangspunkt', nummer: '01', label: 'Ausgangspunkt' },
  { id: 'loesung', nummer: '02', label: 'Die Lösung' },
  { id: 'beweis', nummer: '03', label: 'Der Beweis' },
  { id: 'ergebnisse', nummer: '04', label: 'Ergebnisse' },
  { id: 'architektur', nummer: '05', label: 'Architektur' },
  { id: 'clef', nummer: '06', label: 'Clef im Detail' },
  { id: 'clef-vorschlag', nummer: '07', label: 'Entscheidungslogik' },
  { id: 'naechster-schritt', nummer: '08', label: 'Roadmap' },
  { id: 'team', nummer: '09', label: 'Das Team' },
]

const TEAM = ['Admir', 'Simon', 'Philipp', 'Aaron']

const reveal = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1] } },
}

const SPARTAN_BILD = 'https://imageengine.victorinox.com/transform/3e41526b-7ced-4cc1-8fee-c8447ed9d818/SAK_1_3603_S1'
const CLIMBER_BILD = 'https://imageengine.victorinox.com/transform/b930a3ee-e28e-40e8-bb94-6f4dbc02bddf/SAK_1_3703__S1'

// Werkzeuge laut Foto (SWIZA D03) und laut Victorinox-Katalog (Spartan 1.3603)
const D03_WERKZEUGE = ['Klinge, gross', 'Korkenzieher', 'Dosenöffner', 'Kapselheber', 'Schraubendreher 6 mm', 'Stech-Bohr-Nähahle', 'Pinzette']
const SPARTAN_EXTRA = ['Klinge, klein', 'Ring', 'Zahnstocher', 'Schraubendreher 3 mm', 'Drahtabisolierer']

// Erfolgskriterien aus dem Victorinox-Fragebogen, Messwerte aus der README
const KRITERIEN = [
  {
    kriterium: 'Victorinox vs. Konkurrenz unterscheiden',
    wert: '11/12',
    detail: 'Marke unter den Top-3 auf 12 echten Handyfotos (Top-1: 9/12)',
    status: 'erfuellt',
  },
  {
    kriterium: 'Transparente Konfidenz',
    wert: '100 %',
    detail: 'Trefferquote ab Konfidenz 0,3: 9/12 beantwortet, beim Rest fragt die App nach statt zu raten',
    status: 'erfuellt',
  },
  {
    kriterium: 'Fachlich plausible Alternative',
    wert: '88 %',
    detail: 'Top-1 beim Werkzeug-Abgleich über 32 Testmesser (Top-3: 100 %), sobald die Werkzeuge erkannt sind',
    status: 'erfuellt',
  },
  {
    kriterium: 'Keine erfundenen Spezifikationen',
    wert: '0',
    detail: 'erfundene Werte: Jede Angabe stammt aus victorinox.com oder dem Katalog 2026 und zeigt ihre Quelle',
    status: 'erfuellt',
  },
  {
    kriterium: 'Richtiges Produkt in den Top-3',
    wert: '3/5',
    detail: 'Victorinox-Kundenfotos, Bildsuche im Katalog. Hier ist noch am meisten Luft',
    status: 'teilweise',
  },
  {
    kriterium: 'Betriebskosten',
    wert: '$0.00003',
    detail: 'pro Entscheidung des Vision-Modells (Clef über OpenRouter)',
    status: 'erfuellt',
  },
]

// Bausteine aus der Challenge-Beschreibung und wo sie bei uns liegen
const BAUSTEINE = [
  { icon: ScanSearch, rolle: 'Vision Agent', modul: 'vision.py · clef.py', text: 'Clef (Apache-2.0) über OpenRouter, alternativ Azure OpenAI – per VISION_ANBIETER umschaltbar.' },
  { icon: Database, rolle: 'Product Data Agent', modul: 'Produktdaten · Kataloge', text: '153 Victorinox-Taschenmesser von victorinox.com, ergänzt um Katalog 2026 sowie SWIZA, Leatherman und Gerber.' },
  { icon: Layers, rolle: 'Vektorindex', modul: 'embeddings.py', text: 'Semantische Suche über Verwendungszwecke („Wandern“, „Picknick und Wein“).' },
  { icon: Target, rolle: 'Recommendation Agent', modul: 'matching.py · konkurrenz.py', text: 'Werkzeug-Abgleich über 32 Werkzeuggruppen plus Konkurrenz-Zuordnung.' },
  { icon: MessageSquare, rolle: 'Feedback', modul: '/api/feedback', text: 'Richtig/falsch aus dem Alltag fliesst zurück in die Bewertung.' },
]

const LEISTE = 48 // Höhe der Kapitel-Leiste
const RAND = 32 // Abstand oben und unten pro Folie (md:py-8)

/**
 * Eine Folie füllt am Desktop genau eine Bildschirmhöhe unter der Kapitel-Leiste.
 * Ist der Inhalt höher (kleiner Beamer), wird er per CSS-zoom verkleinert, damit jede Pfeiltaste genau eine Folie weiterspringt.
 */
function Kapitel({ id, nummer, label, children, className = '' }) {
  const innen = useRef(null)
  const [zoom, setZoom] = useState(1)

  useLayoutEffect(() => {
    const el = innen.current
    function messen() {
      if (window.innerWidth < 768) return setZoom(1)
      const vorher = el.style.zoom
      el.style.zoom = '1'
      const hoehe = el.offsetHeight
      el.style.zoom = vorher
      setZoom(Math.min(1, (window.innerHeight - LEISTE - 2 * RAND) / hoehe))
    }
    messen()
    document.fonts?.ready.then(messen)
    window.addEventListener('resize', messen)
    return () => window.removeEventListener('resize', messen)
  }, [])

  return (
    <motion.section
      id={id}
      data-folie
      className={`relative flex scroll-mt-12 flex-col justify-center py-14 md:h-[calc(100dvh-3rem)] md:py-8 ${className}`}
      variants={reveal}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.15 }}
    >
      <div ref={innen} style={{ zoom }}>
        <div className="mb-5 flex items-center gap-3 text-xs font-bold uppercase tracking-[0.18em] text-brand">
          <span>{nummer}</span><span className="h-px w-8 bg-brand/40" /><span>{label}</span>
        </div>
        {children}
      </div>
    </motion.section>
  )
}

function Titel({ children, akzent }) {
  return (
    <h2 className="max-w-3xl text-4xl font-bold leading-[1.05] tracking-tight text-slate-900 sm:text-5xl">
      {children}
      {akzent && <><br /><span className="bg-gradient-to-r from-red-600 to-amber-500 bg-clip-text text-transparent">{akzent}</span></>}
    </h2>
  )
}

function Karte({ className = '', children }) {
  return <div className={`rounded-[28px] border border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.06)] ${className}`}>{children}</div>
}

function MarkenBadge({ victorinox }) {
  return victorinox ? (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-brand px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-white">Victorinox</span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-800 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-white">Konkurrenz</span>
  )
}

/** Handy-Attrappe mit dem Ergebnis eines Scans – für den Startbildschirm. */
function HandyErgebnis() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30, rotate: 2 }}
      animate={{ opacity: 1, y: 0, rotate: 2 }}
      transition={{ duration: 0.8, delay: 0.2 }}
      className="relative mx-auto w-[270px] rounded-[44px] border-[10px] border-slate-900 bg-white shadow-[0_40px_90px_rgba(15,23,42,0.25)]"
    >
      <div className="absolute left-1/2 top-2 z-10 h-5 w-20 -translate-x-1/2 rounded-full bg-slate-900" />
      <div className="overflow-hidden rounded-[34px]">
        <div className="relative bg-slate-100">
          <img src="/demo/swiza-d03.jpg" alt="Foto eines SWIZA D03" className="aspect-[4/3] w-full object-contain" />
          <div className="absolute left-3 top-8"><MarkenBadge /></div>
        </div>
        <div className="space-y-3 p-4">
          <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Erkannt · SWIZA D03</div>
          <div className="flex items-center gap-3">
            <ProduktBild url={SPARTAN_BILD} alt="Victorinox Spartan" breite={200} className="size-14 rounded-xl ring-1 ring-slate-200" />
            <div className="min-w-0 flex-1">
              <MarkenBadge victorinox />
              <div className="mt-1 text-base font-bold leading-tight">Spartan</div>
              <div className="text-[11px] text-slate-500">Art.-Nr. 1.3603</div>
            </div>
            <KonfidenzRing wert={0.87} groesse={52} />
          </div>
          <div className="flex flex-wrap gap-1.5 text-[11px] font-medium">
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700 ring-1 ring-emerald-100">7/7 Werkzeuge</span>
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700 ring-1 ring-emerald-100">An Lager</span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">Quelle: victorinox.com</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}


/** Seitenoberkante ohne Transformationen (die Einblend-Animation verschiebt die Folien kurzzeitig). */
function oberkante(el) {
  let y = 0
  for (let e = el; e; e = e.offsetParent) y += e.offsetTop
  return y
}

/** Kapitel-Links: sanft zur Folie scrollen (gleiche Zielposition wie die Pfeiltasten) statt hart zu springen. */
function zuFolie(e, id) {
  const ziel = document.getElementById(id)
  if (!ziel) return
  e.preventDefault()
  window.scrollTo({ top: oberkante(ziel) - LEISTE, behavior: 'smooth' })
  history.replaceState(null, '', `#${id}`)
}

/**
 * Fortschritt 0–1 für den Balken oben: Auf der Startseite ist er leer, bei Folie k reicht er genau bis
 * zum Ende von Kapitel k in der Kapitel-Leiste. Beim Scrollen zwischen zwei Folien wandert er linear weiter.
 */
function useFolienFortschritt() {
  const fortschritt = useMotionValue(0)
  useEffect(() => {
    let stopps = []
    let kanten = []
    const leiste = document.querySelector('[data-kapitel-leiste]')
    function messen() {
      stopps = [0, ...[...document.querySelectorAll('section[data-folie]')].map((f) => oberkante(f) - LEISTE)]
      // rechte Kante jedes Kapitel-Links plus halber Abstand zum nächsten (gap-3 = 12px)
      kanten = [0, ...[...document.querySelectorAll('[data-kapitel-link]')].map((a) => Math.min(1, (a.getBoundingClientRect().right + 6) / window.innerWidth))]
      aktualisieren()
    }
    function aktualisieren() {
      const y = window.scrollY
      const n = stopps.length - 1
      if (n < 1 || kanten.length !== stopps.length) return
      const i = stopps.findLastIndex((s) => s <= y)
      if (i >= n) return fortschritt.set(kanten[n])
      const anteil = (y - stopps[i]) / (stopps[i + 1] - stopps[i])
      fortschritt.set(kanten[i] + (kanten[i + 1] - kanten[i]) * anteil)
    }
    messen()
    document.fonts?.ready.then(messen)
    window.addEventListener('scroll', aktualisieren, { passive: true })
    window.addEventListener('resize', messen)
    leiste?.addEventListener('scroll', messen, { passive: true })
    return () => {
      window.removeEventListener('scroll', aktualisieren)
      window.removeEventListener('resize', messen)
      leiste?.removeEventListener('scroll', messen)
    }
  }, [fortschritt])
  return fortschritt
}

/** Pfeiltasten, Leertaste und Bild auf/ab springen von Kapitel zu Kapitel – präsentieren ohne Scrollen. */
function useFolienSteuerung() {
  useEffect(() => {
    function onKey(e) {
      if (e.target.closest?.('input, textarea, select, [contenteditable]') || e.metaKey || e.ctrlKey || e.altKey) return
      const vor = ['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(e.key)
      const zurueck = ['ArrowLeft', 'ArrowUp', 'PageUp'].includes(e.key)
      if (!vor && !zurueck) return
      e.preventDefault()
      const folien = [...document.querySelectorAll('[data-folie]')]
      const y = window.scrollY
      const stopps = folien.map((f) => Math.max(0, oberkante(f) - LEISTE))
      // Ist das aktuelle Kapitel höher als der Bildschirm, zuerst darin weiterblättern
      const i = stopps.findLastIndex((t) => t <= y + 8)
      const rest = i >= 0 ? oberkante(folien[i]) + folien[i].offsetHeight - (y + window.innerHeight) : 0
      if (vor && rest > 8) {
        window.scrollBy({ top: Math.min(rest, window.innerHeight * 0.8), behavior: 'smooth' })
        return
      }
      const ziel = vor ? stopps.find((t) => t > y + 8) : stopps.findLast((t) => t < y - 8)
      if (ziel !== undefined) window.scrollTo({ top: ziel, behavior: 'smooth' })
      else if (zurueck) window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
}

/** Folie 6: Clefs Bildklassifikation, ohne den anschliessenden Produktabgleich. */
function ClefErkennung() {
  return (
    <div className="mx-auto max-w-5xl">
      <Titel akzent="Architektur & Ablauf.">So arbeitet Clef</Titel>
      <div className="mt-8 grid items-center gap-3 lg:grid-cols-[1fr_auto_1.25fr_auto_1fr]">
        <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400"><Camera className="size-4" /> Eingabe</div>
          <div className="mt-4 text-lg font-semibold">Foto</div>
          <div className="mt-1 text-sm leading-relaxed text-slate-500">Backend lädt, normalisiert und verkleinert auf max. 768 px.</div>
          <div className="mt-3 font-mono text-[11px] text-slate-400">JPEG → data URL</div>
        </div>
        <ArrowRight className="mx-auto hidden size-5 text-slate-300 lg:block" />
        <div className="rounded-[28px] border-2 border-red-200 bg-white p-5 shadow-[0_20px_60px_rgba(15,23,42,0.06)]">
          <div className="flex items-center justify-between"><div className="flex items-center gap-2 font-semibold"><ScanSearch className="size-5 text-brand" /> Clef · multimodales Entscheidungsmodell</div><span className="rounded-full bg-red-50 px-2.5 py-1 font-mono text-[10px] text-red-700">OpenRouter API</span></div>
          <div className="mt-4 rounded-xl bg-slate-950 px-4 py-3 font-mono text-xs text-slate-200"><span className="text-emerald-300">state</span> = Bild + Kontext <span className="px-2 text-slate-500">·</span> <span className="text-amber-200">questions</span> = typisierte Optionen</div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2"><div className="rounded-xl bg-slate-50 p-3"><div className="text-xs font-semibold">NOUL</div><div className="mt-1 text-xs text-slate-500">Ja / Nein pro Werkzeuggruppe; in Paketen mit 12 Fragen</div></div><div className="rounded-xl bg-slate-50 p-3"><div className="text-xs font-semibold">Choice</div><div className="mt-1 text-xs text-slate-500">Markenwahl mit „unklar“ und „andere“</div></div></div>
        </div>
        <ArrowRight className="mx-auto hidden size-5 text-slate-300 lg:block" />
        <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400"><Target className="size-4" /> Ausgabe</div>
          <div className="mt-4 space-y-2"><div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"><span>Marke</span><span className="font-mono text-xs text-brand">p(Option)</span></div><div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"><span>Werkzeuge</span><span className="font-mono text-xs text-brand">p(Ja)</span></div><div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"><span>Taschenmesser?</span><span className="font-mono text-xs text-brand">p(Ja)</span></div></div>
        </div>
      </div>
      <div className="mt-5 flex flex-col gap-3 border-l-2 border-red-200 pl-4 sm:flex-row sm:items-center sm:justify-between sm:pl-5"><div><div className="font-semibold">Backend kalibriert die Ausgaben</div><div className="text-sm text-slate-500">Gelernte Schwellen filtern Werkzeug-Antworten; Marken-Konfidenz berücksichtigt den Abstand zur zweitbesten Option.</div></div><div className="shrink-0 rounded-xl bg-red-50 px-4 py-2 font-mono text-xs text-red-800">JSON → Erkennung</div></div>
    </div>
  )
}

/** Folie 7: Entscheidungsbaum für den Produktabgleich nach der Erkennung. */
function ClefVorschlag() {
  return (
    <div className="mx-auto max-w-5xl">
      <Titel akzent="zum passenden Victorinox.">Vom erkannten Produkt</Titel>
      <div className="mt-5 overflow-x-auto pb-2">
        <div className="mx-auto min-w-[720px] max-w-4xl">
          <div className="flex justify-center"><div className="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white">Marke erkannt</div></div>
          <svg className="h-12 w-full" viewBox="0 0 800 48" preserveAspectRatio="none" aria-hidden="true"><path d="M400 0 V18 H200 V48 M400 18 H600 V48" fill="none" stroke="#cbd5e1" strokeWidth="2" /></svg>
          <div className="grid grid-cols-2 gap-16">
            <div className="text-center"><span className="inline-block rounded-full bg-red-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-red-700">Konkurrenz</span><div className="mt-3 text-sm font-semibold text-slate-800">Querverweis / Werkzeugliste</div><div className="mt-1 text-xs text-slate-500">Modell bestimmen, falls bekannt</div><div className="mx-auto h-7 w-px bg-slate-300" /><div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm"><span className="text-brand">●</span> Victorinox nach Werkzeugen ordnen</div><div className="mt-1 text-[11px] text-slate-400">Bildähnlichkeit = kleiner Gleichstandsbonus</div></div>
            <div className="text-center"><span className="inline-block rounded-full bg-slate-100 px-3 py-1 text-xs font-bold uppercase tracking-wide text-slate-600">Victorinox / unklar</span><div className="mt-3 text-sm font-semibold text-slate-800">Katalogbild-Vergleich</div><div className="mt-1 text-xs text-slate-500">Foto gegen Victorinox-Katalog</div><div className="mx-auto h-7 w-px bg-slate-300" /><div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm"><span className="text-brand">●</span> Nach Bildtreffer ordnen</div><div className="mt-1 text-[11px] text-slate-400">Ohne Bildtreffer: Werkzeug-Abgleich</div></div>
          </div>
          <svg className="h-12 w-full" viewBox="0 0 800 48" preserveAspectRatio="none" aria-hidden="true"><path d="M200 0 V18 H400 V48 M600 0 V18 H400" fill="none" stroke="#cbd5e1" strokeWidth="2" /></svg>
          <div className="mx-auto max-w-xl rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm text-slate-700">Kategorie-Hinweis passt? <span className="text-slate-400">Ja: normal gewichtet · Nein: Score halbiert</span></div>
          <div className="mx-auto h-8 w-px bg-slate-300" />
          <div className="flex justify-center"><div className="rounded-full bg-red-600 px-7 py-3 text-sm font-bold text-white shadow-md">Top 3 Victorinox-Empfehlungen</div></div>
          <div className="mx-auto h-7 w-px bg-slate-300" />
          <div className="text-center text-sm"><span className="font-semibold text-slate-800">Genug Abstand zwischen Treffern?</span><span className="px-2 text-slate-400">Nein → Rückfrage</span><span className="text-slate-400"> · Ja → Ergebnis zeigen</span></div>
        </div>
      </div>
    </div>
  )
}

export default function PresentationPage() {
  const scaleX = useSpring(useFolienFortschritt(), { stiffness: 100, damping: 30, restDelta: 0.001 })
  useFolienSteuerung()

  // Direktlink auf ein Kapitel (/praesentation#beweis): ohne Animation dorthin
  useLayoutEffect(() => {
    const ziel = window.location.hash && document.getElementById(window.location.hash.slice(1))
    if (ziel) window.scrollTo(0, oberkante(ziel) - LEISTE)
  }, [])

  return (
    <div className="relative overflow-x-clip bg-[#f7f3ef] text-slate-900">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(227,6,19,0.12),transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(251,191,36,0.08),transparent_26%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(15,23,42,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.04)_1px,transparent_1px)] [background-size:64px_64px]" />

      <motion.div className="fixed inset-x-0 top-0 z-50 h-1 origin-left bg-gradient-to-r from-[#ff8e7a] via-brand to-[#f59e0b]" style={{ scaleX }} />
      <div className="relative mx-auto max-w-6xl px-5 sm:px-8 lg:px-12">
        <header data-folie className="relative grid min-h-dvh items-center gap-12 py-16 md:grid-cols-[1.25fr_0.75fr]">
          <div className="pointer-events-none absolute -right-20 top-12 size-72 rounded-full bg-red-200/60 blur-3xl" />
          <div className="pointer-events-none absolute left-0 top-1/3 size-64 rounded-full bg-amber-100/80 blur-3xl" />
          <motion.div className="relative" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-red-700"><Sparkles className="size-3.5" /> Zentralhack · Victorinox</div>
            <h1 className="max-w-3xl text-5xl font-bold leading-[0.96] tracking-[-0.05em] text-slate-900 sm:text-7xl">Vom Foto zur<br /><span className="bg-gradient-to-r from-red-600 via-red-500 to-amber-500 bg-clip-text text-transparent">passenden Klinge.</span></h1>
            <p className="mt-7 max-w-xl text-xl leading-relaxed text-slate-700">Ein Foto eines beliebigen Taschenmessers – und in Sekunden steht da, welches Victorinox-Produkt passt, warum, und wie sicher wir uns sind.</p>
            <div className="mt-10 flex flex-wrap items-center gap-5">
              <Link to="/" className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-red-500 to-red-600 px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(227,6,19,0.25)] transition hover:brightness-110"><Camera className="size-4" /> Live-Demo</Link>
              <a href="#ausgangspunkt" onClick={(e) => zuFolie(e, 'ausgangspunkt')} className="flex items-center gap-2 text-sm font-medium text-slate-700 transition hover:text-slate-900"><ArrowDown className="size-4 animate-bounce" /> Story starten <span className="hidden text-slate-400 sm:inline">· oder Pfeiltasten</span></a>
            </div>
          </motion.div>
          <HandyErgebnis />
        </header>

        <nav data-kapitel-leiste className="sticky top-0 z-40 -mx-5 overflow-x-auto border-y border-slate-200 bg-[#f9f6f2]/85 px-5 py-3 backdrop-blur-xl sm:-mx-8 sm:px-8 lg:-mx-12 lg:px-12">
          <div className="flex min-w-max items-center gap-3 text-[13px] font-medium text-slate-700">
            {chapters.map((c) => (
              <a key={c.id} data-kapitel-link href={`#${c.id}`} onClick={(e) => zuFolie(e, c.id)} className="transition hover:text-slate-900"><span className="mr-1.5 text-brand">{c.nummer}</span>{c.label}</a>
            ))}
            <Link to="/" className="ml-auto inline-flex items-center gap-1 rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white transition hover:bg-slate-700">Zur App <ArrowRight className="size-3.5" /></Link>
          </div>
        </nav>

        {/* 01 · Problem mit Vorher/Nachher */}
        <Kapitel {...chapters[0]} className="border-b border-slate-200">
          <div className="grid gap-10 md:grid-cols-[1fr_1fr] md:items-center">
            <div>
              <Titel akzent="Viele ähnliche Antworten.">Ein Foto.</Titel>
              <p className="mt-6 max-w-lg text-lg leading-relaxed text-slate-700">Kunden schicken ein Foto oder halten ein Messer über den Ladentisch. Heute heisst das: Modell von Hand bestimmen, dann in Katalogen, Produktdaten und Cross-Reference-Tabellen suchen – besonders mühsam bei ausgelaufenen Artikeln und Konkurrenzprodukten.</p>
              <div className="mt-6 flex flex-wrap gap-2 text-sm text-slate-700">
                {['Verkauf', 'Customer Service', 'Produktmanagement', 'Handel'].map((n) => <span key={n} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5"><Users className="size-3.5 text-brand" />{n}</span>)}
              </div>
            </div>
            <div className="grid gap-4">
              <Karte className="p-6">
                <div className="flex items-center justify-between text-sm font-semibold text-slate-500"><span>Heute</span><span className="inline-flex items-center gap-1.5"><Clock className="size-4" /> Minuten</span></div>
                <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
                  {['Foto ansehen', 'Modell raten', 'Katalog', 'Excel-Tabelle', 'Rückfrage'].map((s, i) => (
                    <span key={s} className="flex items-center gap-2">{i > 0 && <ArrowRight className="size-3.5 text-slate-300" />}<span className="rounded-xl bg-slate-100 px-3 py-2 text-slate-700 ring-1 ring-slate-200">{s}</span></span>
                  ))}
                </div>
                <p className="mt-4 text-sm text-slate-500">Das Wissen ist da – aber verteilt, und das Ergebnis hängt davon ab, wer gerade fragt.</p>
              </Karte>
              <Karte className="border-red-200 p-6 ring-1 ring-red-100">
                <div className="flex items-center justify-between text-sm font-semibold text-brand"><span>Mit dem Product Match Agent</span><span className="inline-flex items-center gap-1.5"><Zap className="size-4" /> Sekunden</span></div>
                <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
                  {['Foto', 'Top-3 mit Begründung'].map((s, i) => (
                    <span key={s} className="flex items-center gap-2">{i > 0 && <ArrowRight className="size-3.5 text-brand" />}<span className={`rounded-xl px-3 py-2 ${i ? 'bg-brand font-semibold text-white' : 'bg-red-50 text-red-800 ring-1 ring-red-100'}`}>{s}</span></span>
                  ))}
                </div>
                <p className="mt-4 text-sm text-slate-600">Einheitlich, mit Quellen und Konfidenz – im Laden, am Telefon oder im Büro.</p>
              </Karte>
            </div>
          </div>
        </Kapitel>

        {/* 02 · Lösung in drei Schritten */}
        <Kapitel {...chapters[1]} className="border-b border-slate-200">
          <Titel akzent="in drei Schritten.">Kein Chatbot. Ein Agent</Titel>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {[
              ['01', Camera, 'Foto aufnehmen', 'Mit der Handykamera, live am Laptop oder per QR-Code vom Handy an den Rechner.'],
              ['02', ScanSearch, 'Erkennen & abgleichen', 'Marke, Modell und sichtbare Werkzeuge erkennen, dann mit freigegebenen Produktdaten und Konkurrenz-Zuordnungen abgleichen.'],
              ['03', Target, 'Victorinox vorschlagen', 'Top-3 mit Konfidenz, technischem Vergleich und Begründung. Ist es unsicher, fragt der Agent nach.'],
            ].map(([nr, Icon, title, text], index) => (
              <motion.div key={nr} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.12 }} viewport={{ once: true }}>
                <Karte className="h-full p-7">
                  <div className="flex items-center justify-between"><span className="text-5xl font-bold text-red-100">{nr}</span><Icon className="size-7 text-brand" /></div>
                  <h3 className="mt-8 text-xl font-bold text-slate-900">{title}</h3>
                  <p className="mt-2 text-base leading-relaxed text-slate-700">{text}</p>
                </Karte>
              </motion.div>
            ))}
          </div>
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-base text-slate-800">
            <CircleAlert className="mt-0.5 size-5 shrink-0 text-amber-500" />
            <p><strong>Lieber nachfragen als raten:</strong> Liegt die Konfidenz unter der Schwelle, bittet die App um ein Foto des geöffneten Messers oder die Artikelnummer.</p>
          </div>
        </Kapitel>

        {/* 03 · Echte Vergleichsansicht */}
        <Kapitel {...chapters[2]} className="border-b border-slate-200">
          <Titel akzent="Begründet passend.">Nicht nur ähnlich.</Titel>
          <Karte className="mt-8 overflow-hidden">
            <div className="grid md:grid-cols-[1fr_auto_1fr]">
              <div className="p-6">
                <div className="flex items-center justify-between"><MarkenBadge /><span className="text-xs text-slate-500">Eingabe: Handyfoto</span></div>
                <img src="/demo/swiza-d03.jpg" alt="SWIZA D03" className="mt-4 h-36 w-full rounded-2xl bg-slate-50 object-contain" />
                <div className="mt-3 text-xl font-bold">SWIZA D03</div>
                <div className="text-sm text-slate-500">Marke erkannt mit 91 % Konfidenz</div>
              </div>
              <div className="flex items-center justify-center border-y border-slate-100 bg-slate-50/60 px-6 py-4 md:border-x md:border-y-0">
                <div className="flex flex-col items-center gap-2">
                  <KonfidenzRing wert={0.87} groesse={84} label="Match" />
                  <ArrowRight className="hidden size-6 text-brand md:block" />
                </div>
              </div>
              <div className="p-6">
                <div className="flex items-center justify-between"><MarkenBadge victorinox /><span className="text-xs text-slate-500">Empfehlung #1</span></div>
                <ProduktBild url={SPARTAN_BILD} alt="Victorinox Spartan" breite={600} className="mt-4 h-36 w-full rounded-2xl" />
                <div className="mt-3 text-xl font-bold">Spartan <span className="text-sm font-medium text-slate-500">1.3603</span></div>
                <div className="text-sm text-slate-500">An Lager · auch in Schwarz (1.3603.3)</div>
              </div>
            </div>
            <div className="border-t border-slate-100 p-6">
              <div className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Technischer Abgleich</div>
              <div className="mt-4 flex flex-wrap gap-2 text-sm">
                {D03_WERKZEUGE.map((w) => <span key={w} className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-emerald-800 ring-1 ring-emerald-100"><Check className="size-3.5" />{w}</span>)}
                {SPARTAN_EXTRA.map((w) => <span key={w} className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-3 py-1 text-sky-800 ring-1 ring-sky-100"><Plus className="size-3.5" />{w}</span>)}
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                <span><span className="text-emerald-700">●</span> auf dem Foto erkannt und vorhanden (7/7)</span>
                <span><span className="text-sky-700">●</span> beim Spartan zusätzlich</span>
                <span>Quelle: victorinox.com, Produktdaten de-CH</span>
              </div>
            </div>
          </Karte>
          <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
            <Karte className="flex flex-wrap items-center gap-4 p-5 sm:flex-nowrap">
              <img src="/demo/climber-wood-winter-magic.webp" alt="Climber Wood Winter Magic" className="size-16 rounded-xl bg-slate-50 object-contain" />
              <ArrowRight className="size-5 shrink-0 text-brand" />
              <ProduktBild url={CLIMBER_BILD} alt="Climber" breite={200} className="size-16 rounded-xl" />
              <div className="order-last min-w-0 basis-full sm:order-none sm:flex-1 sm:basis-auto">
                <div className="text-sm font-semibold">Zweites Beispiel: ausgelaufen → Nachfolger</div>
                <div className="text-sm text-slate-600">Climber Wood Winter Magic (Limited Edition 2025) → aktueller Climber 1.3703</div>
              </div>
              <KonfidenzRing wert={0.94} groesse={52} />
            </Karte>
            <Link to="/" className="inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-red-500 to-red-600 px-6 py-4 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(227,6,19,0.25)] transition hover:brightness-110"><Camera className="size-4" /> Live-Demo starten</Link>
          </div>
        </Kapitel>

        {/* 04 · Erfolgskriterien mit Messwerten */}
        <Kapitel {...chapters[3]} className="border-b border-slate-200">
          <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
            <Titel akzent="gemessen, nicht behauptet.">Eure Erfolgskriterien –</Titel>
            <p className="max-w-xs text-sm text-slate-600">Gemessen auf echten Smartphone-Fotos, nicht auf Produktbildern aus dem Shop.</p>
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {KRITERIEN.map((k, index) => (
              <motion.div key={k.kriterium} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.06 }} viewport={{ once: true }}>
                <Karte className="h-full px-5 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="text-sm font-semibold text-slate-700">{k.kriterium}</div>
                    {k.status === 'erfuellt'
                      ? <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"><Check className="size-4" /></span>
                      : <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">in Arbeit</span>}
                  </div>
                  <div className="mt-2 text-3xl font-bold tabular-nums tracking-tight text-slate-900">{k.wert}</div>
                  <p className="mt-1 text-sm leading-snug text-slate-600">{k.detail}</p>
                </Karte>
              </motion.div>
            ))}
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-[1.2fr_1fr]">
            <Karte className="px-5 py-4">
              <div className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Warum die Konfidenz trägt</div>
              <div className="mt-3 space-y-2.5">
                {[['Antwort richtig', 0.85, 'from-emerald-400 to-emerald-500'], ['Antwort falsch', 0.12, 'from-amber-400 to-amber-500']].map(([label, wert, farbe]) => (
                  <div key={label}>
                    <div className="flex justify-between text-sm"><span className="text-slate-700">{label}</span><span className="font-semibold tabular-nums">Ø {wert.toFixed(2).replace('.', ',')}</span></div>
                    <div className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-slate-100">
                      <motion.div className={`h-full rounded-full bg-gradient-to-r ${farbe}`} initial={{ width: 0 }} whileInView={{ width: `${wert * 100}%` }} transition={{ duration: 1 }} viewport={{ once: true }} />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-sm leading-snug text-slate-600">Liegt das Modell falsch, weiss es das meistens auch. Deshalb kann die App bei tiefer Konfidenz nachfragen.</p>
            </Karte>
            <Karte className="border-amber-200 bg-gradient-to-br from-amber-50 to-white px-5 py-4">
              <div className="text-xs font-bold uppercase tracking-[0.16em] text-amber-700">Ehrliche Grenzen</div>
              <ul className="mt-3 space-y-1.5 text-sm leading-snug text-slate-700">
                <li>· Geschlossene Messer verbergen ihre Werkzeuge: Spartan, Climber und Tinker sehen dann fast gleich aus.</li>
                <li>· Werkzeugerkennung auf Fotos: F1 0,69 – der grösste Hebel für bessere Top-3.</li>
                <li>· Unbekannte Blickwinkel: Top-3 33 %, Top-5 52 % auf 21 zurückgehaltenen Messern.</li>
              </ul>
            </Karte>
          </div>
        </Kapitel>

        {/* 05 · Architektur und Entwicklung */}
        <Kapitel {...chapters[4]} className="border-b border-slate-200">
          <Titel akzent="über APIs austauschbar.">Modular gebaut,</Titel>
          <p className="mt-4 max-w-2xl text-lg leading-relaxed text-slate-700">Jeder Baustein aus eurer Challenge-Beschreibung hat bei uns ein eigenes Modul. Ein FastAPI-Orchestrator ruft sie nacheinander auf und streamt jeden Schritt live ins Frontend.</p>
          <div className="mt-8 grid items-stretch gap-3 lg:grid-cols-[auto_1fr_auto]">
            <div className="flex items-center justify-center gap-3 rounded-[24px] border border-slate-200 bg-white p-5 lg:flex-col">
              <Camera className="size-7 text-brand" /><span className="text-sm font-semibold">Foto</span>
            </div>
            <div className="rounded-[28px] border-2 border-dashed border-red-200 bg-white/60 p-4">
              <div className="mb-3 flex items-center gap-2 px-1 text-sm font-semibold text-slate-700"><Workflow className="size-4 text-brand" /> Orchestrator · FastAPI <span className="font-mono text-xs font-normal text-slate-500">/api/match/stream</span></div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                {BAUSTEINE.map(({ icon: Icon, rolle, modul, text }) => (
                  <div key={rolle} className="rounded-2xl border border-slate-200 bg-white p-4">
                    <Icon className="size-5 text-brand" />
                    <div className="mt-3 text-sm font-bold">{rolle}</div>
                    <div className="font-mono text-[11px] text-slate-500">{modul}</div>
                    <p className="mt-2 text-xs leading-relaxed text-slate-600">{text}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-center gap-3 rounded-[24px] border border-red-200 bg-red-50 p-5 lg:flex-col">
              <Target className="size-7 text-brand" /><span className="text-sm font-semibold">Top-3</span>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <span className="mr-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Stack</span>
            {['Python · FastAPI', 'React · Vite', 'Clef · OpenRouter', 'Azure OpenAI (optional)', 'fastembed', 'Docker'].map((t) => (
              <span key={t} className="rounded-full bg-white px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-200">{t}</span>
            ))}
            <span className="ml-2 text-sm text-slate-600">· Vision-Modell per Umgebungsvariable wechselbar, ohne Code zu ändern.</span>
          </div>
        </Kapitel>

        {/* 06 · Wie Clef arbeitet */}
        <Kapitel {...chapters[5]} className="border-b border-slate-200">
          <ClefErkennung />
        </Kapitel>

        {/* 07 · Vom Clef-Ergebnis zum Vorschlag */}
        <Kapitel {...chapters[6]} className="border-b border-slate-200">
          <ClefVorschlag />
        </Kapitel>

        {/* 08 · Roadmap */}
        <Kapitel {...chapters[7]}>
          <Titel akzent="zum Werkzeug im Alltag.">Vom Hackathon-Prototyp</Titel>
          <div className="mt-10 grid gap-4 md:grid-cols-4">
            {[
              ['Heute', 'Taschenmesser end-to-end', 'Foto → Erkennung → Top-3 → technischer Vergleich, live auf dem Handy.', true],
              ['Als Nächstes', 'Victorinox-Daten anbinden', 'Cross-Reference-Tabellen, PIM/ERP und Bynder-Bilder statt gescrapter Daten.'],
              ['Dann', 'Auf Azure betreiben', 'Container Apps, Azure OpenAI und Daten aus dem Fabric Lakehouse.'],
              ['Später', 'Mehr Kategorien', 'Haushalts- und Berufsmesser; Feedback aus dem Alltag verbessert die Treffer.'],
            ].map(([wann, titel, text, aktiv], index) => (
              <motion.div key={wann} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }} viewport={{ once: true }}>
                <Karte className={`h-full p-6 ${aktiv ? 'border-red-200 ring-1 ring-red-100' : ''}`}>
                  <div className={`text-xs font-bold uppercase tracking-[0.16em] ${aktiv ? 'text-brand' : 'text-slate-500'}`}>{wann}</div>
                  <div className="mt-3 text-lg font-bold">{titel}</div>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p>
                </Karte>
              </motion.div>
            ))}
          </div>
        </Kapitel>

        {/* 09 · Team und Abschluss */}
        <Kapitel {...chapters[8]} className="border-t border-slate-200">
          <div className="grid gap-10 md:grid-cols-[1.3fr_1fr] md:items-center">
            <figure className="overflow-hidden rounded-[28px] border border-slate-200 bg-white p-2 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
              <img src="/team.webp" alt="Das Team vor dem Product Match Agent am Zentralhack" className="aspect-[4/3] w-full rounded-[22px] object-cover" />
              <figcaption className="px-3 py-2.5 text-xs text-slate-500">Am Zentralhack, mit dem Prototyp auf dem Bildschirm</figcaption>
            </figure>
            <div>
              <Titel akzent="Ein Agent.">Vier Köpfe.</Titel>
              <p className="mt-6 text-lg leading-relaxed text-slate-700">Wir haben den Product Match Agent für die Victorinox-Challenge gemeinsam entwickelt – von den Produktdaten über das Backend bis zur mobilen App.</p>
              <div className="mt-6 grid grid-cols-2 gap-3">
                {TEAM.map((name) => (
                  <div key={name} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
                    <span className="flex size-10 items-center justify-center rounded-full bg-red-50 text-sm font-bold text-brand ring-1 ring-red-100">{name[0]}</span>
                    <span className="text-base font-semibold">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-10 flex flex-col items-center gap-3 border-t border-slate-200 pt-8 text-center">
            <p className="text-lg text-slate-700">Bereit für den ersten Scan?</p>
            <Link to="/" className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-red-500 to-red-600 px-7 py-4 text-base font-semibold text-white shadow-[0_12px_30px_rgba(227,6,19,0.25)] transition hover:brightness-110"><Camera className="size-5" /> Zur Live-Demo <ArrowRight className="size-4" /></Link>
          </div>
        </Kapitel>

        <footer className="border-t border-slate-200 py-10 text-center text-sm text-slate-500">
          Victorinox Product Match Agent · Zentralhack Challenge · Admir, Simon, Philipp, Aaron
        </footer>
      </div>
    </div>
  )
}
