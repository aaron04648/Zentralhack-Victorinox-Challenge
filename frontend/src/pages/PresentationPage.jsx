import { motion, useScroll, useSpring } from 'framer-motion'
import {
  ArrowDown,
  ArrowRight,
  Camera,
  Check,
  CircleAlert,
  Database,
  GitBranch,
  ScanSearch,
  Sparkles,
  Target,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'

const chapters = [
  { id: 'ausgangspunkt', nummer: '01', label: 'Ausgangspunkt' },
  { id: 'idee', nummer: '02', label: 'Die Idee' },
  { id: 'ablauf', nummer: '03', label: 'Der Ablauf' },
  { id: 'beispiel', nummer: '05', label: 'Der Beweis' },
  { id: 'naechster-schritt', nummer: '06', label: 'Der nächste Schritt' },
]

const reveal = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1] } },
}

function Kapitel({ id, nummer, label, children, className = '' }) {
  return (
    <motion.section
      id={id}
      className={`relative scroll-mt-20 py-20 sm:py-28 ${className}`}
      variants={reveal}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.2 }}
    >
      <div className="mb-6 flex items-center gap-3 text-xs font-bold uppercase tracking-[0.18em] text-brand">
        <span>{nummer}</span><span className="h-px w-8 bg-brand/40" /><span>{label}</span>
      </div>
      {children}
    </motion.section>
  )
}

function Signal({ icon: Icon, title, text }) {
  return (
    <div className="group rounded-[24px] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition duration-300 hover:-translate-y-1 hover:border-red-300 hover:shadow-[0_18px_50px_rgba(227,6,19,0.08)]">
      <div className="flex size-10 items-center justify-center rounded-xl bg-red-50 ring-1 ring-red-100">
        <Icon className="size-5 text-brand" />
      </div>
      <div className="mt-4 text-sm font-semibold text-slate-900">{title}</div>
      <p className="mt-1 text-xs leading-relaxed text-slate-600">{text}</p>
    </div>
  )
}

export default function PresentationPage() {
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 })

  return (
    <div className="relative overflow-hidden bg-[#f7f3ef] text-slate-900">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(227,6,19,0.12),transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(251,191,36,0.08),transparent_26%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(15,23,42,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.04)_1px,transparent_1px)] [background-size:64px_64px]" />

      <motion.div className="fixed inset-x-0 top-0 z-50 h-1 origin-left bg-gradient-to-r from-[#ff8e7a] via-brand to-[#f59e0b]" style={{ scaleX }} />
      <div className="relative mx-auto max-w-5xl px-5 sm:px-8 lg:px-12">
        <header className="relative flex min-h-[78dvh] flex-col justify-center py-20">
          <div className="pointer-events-none absolute -right-20 top-12 size-72 rounded-full bg-red-200/60 blur-3xl" />
          <div className="pointer-events-none absolute left-0 top-1/3 size-64 rounded-full bg-amber-100/80 blur-3xl" />
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold tracking-[0.14em] text-red-700 uppercase"><Sparkles className="size-3.5" /> Zentralhack · Victorinox</div>
            <h1 className="max-w-3xl text-5xl font-bold leading-[0.96] tracking-[-0.05em] text-slate-900 sm:text-7xl">Vom Foto zur<br /><span className="bg-gradient-to-r from-red-600 via-red-500 to-amber-500 bg-clip-text text-transparent">passenden Klinge.</span></h1>
            <p className="mt-7 max-w-xl text-lg leading-relaxed text-slate-600">Die Geschichte hinter unserem Product Match Agent – und warum aus einer Produktfrage ein klarer, nachvollziehbarer Vorschlag wird.</p>
          </motion.div>
          <a href="#ausgangspunkt" className="mt-14 flex w-fit items-center gap-2 text-sm font-medium text-slate-600 transition hover:text-slate-900"><ArrowDown className="size-4 animate-bounce" /> Story starten</a>
        </header>

        <div className="sticky top-0 z-40 -mx-5 overflow-x-auto border-y border-slate-200 bg-[#f9f6f2]/85 px-5 py-3 backdrop-blur-xl sm:-mx-8 sm:px-8 lg:-mx-12 lg:px-12">
          <div className="flex min-w-max gap-5 text-xs font-medium text-slate-600">{chapters.slice(0, 3).map((chapter) => <a key={chapter.id} href={`#${chapter.id}`} className="transition hover:text-slate-900"><span className="mr-1.5 text-brand">{chapter.nummer}</span>{chapter.label}</a>)}<a href="#entwicklung" className="transition hover:text-slate-900"><span className="mr-1.5 text-brand">04</span>Entwicklung</a>{chapters.slice(3).map((chapter) => <a key={chapter.id} href={`#${chapter.id}`} className="transition hover:text-slate-900"><span className="mr-1.5 text-brand">{chapter.nummer}</span>{chapter.label}</a>)}</div>
        </div>

        <Kapitel {...chapters[0]} className="border-b border-slate-200">
          <div className="grid gap-10 md:grid-cols-[1.1fr_0.9fr] md:items-end">
            <div><h2 className="max-w-xl text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">Ein Foto. Viele ähnliche Antworten.</h2><p className="mt-5 max-w-lg text-base leading-relaxed text-slate-600">Heute wird ein fotografiertes Produkt manuell identifiziert. Danach beginnt die Suche in Katalogen, Produktdaten und Cross-Reference-Tabellen – besonders aufwendig, wenn ein Artikel ausgelaufen ist oder ein Konkurrenzprodukt ersetzt werden soll.</p></div>
            <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_20px_60px_rgba(15,23,42,0.06)]"><div className="mb-4 flex items-center gap-3 text-sm text-slate-700"><Camera className="size-5 text-brand" /> Ausgangslage</div><div className="flex items-center gap-3 text-sm"><div className="rounded-xl bg-slate-100 px-3 py-2 text-slate-700 ring-1 ring-slate-200">Foto</div><ArrowRight className="size-4 text-brand" /><div className="rounded-xl bg-slate-100 px-3 py-2 text-slate-700 ring-1 ring-slate-200">Suche</div><ArrowRight className="size-4 text-brand" /><div className="rounded-xl bg-slate-100 px-3 py-2 text-slate-700 ring-1 ring-slate-200">?</div></div><p className="mt-5 text-xs leading-relaxed text-slate-500">Wissen ist da – aber noch nicht in einem Weg verbunden.</p></div>
          </div>
        </Kapitel>

        <Kapitel {...chapters[1]} className="border-b border-slate-200">
          <div className="grid gap-10 md:grid-cols-[0.9fr_1.1fr] md:items-center"><div><h2 className="text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">Wir verbinden,<br /><span className="bg-gradient-to-r from-red-600 to-amber-500 bg-clip-text text-transparent">was zusammengehört.</span></h2><p className="mt-5 text-base leading-relaxed text-slate-600">Ein multimodaler Agent liest das Bild, gleicht Merkmale mit dem Katalog ab und macht daraus eine fachlich begründete Victorinox-Empfehlung.</p></div><div className="grid grid-cols-2 gap-3"><Signal icon={ScanSearch} title="Sehen" text="Marke, Modell, Form und sichtbare Werkzeuge erkennen." /><Signal icon={Database} title="Verstehen" text="Freigegebene Produktdaten und Cross-References nutzen." /><Signal icon={GitBranch} title="Vergleichen" text="Funktionen, Masse und Verfügbarkeit gewichten." /><Signal icon={Target} title="Empfehlen" text="Top-Treffer mit Konfidenz und Begründung zeigen." /></div></div>
        </Kapitel>

        <Kapitel {...chapters[2]} className="border-b border-slate-200">
          <h2 className="max-w-2xl text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">Der rote Faden<br />in drei Schritten.</h2>
          <div className="mt-12 grid gap-4 md:grid-cols-3">{[
            ['01', Camera, 'Foto aufnehmen', 'Mit dem Smartphone – auch ein Demo-Bild reicht für den ersten Durchlauf.'],
            ['02', ScanSearch, 'Erkennen & abgleichen', 'Vision, Produktdaten und Merkmale werden in einem Workflow zusammengeführt.'],
            ['03', Sparkles, 'Victorinox vorschlagen', 'Ein oder mehrere Treffer – priorisiert, technisch belegt und transparent.'],
          ].map(([nr, Icon, title, text], index) => <motion.div key={nr} className="relative rounded-[28px] border border-slate-200 bg-white p-6 text-slate-900 shadow-[0_18px_50px_rgba(15,23,42,0.06)]" initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.12 }} viewport={{ once: true }}><div className="flex items-center justify-between"><span className="text-4xl font-bold text-red-100">{nr}</span><Icon className="size-6 text-brand" /></div><h3 className="mt-8 text-lg font-bold text-slate-900">{title}</h3><p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p></motion.div>)}</div>
        </Kapitel>

        <motion.section
          id="entwicklung"
          className="relative border-b border-slate-200 py-20 sm:py-28"
          variants={reveal}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
        >
          <div className="mb-6 flex items-center gap-3 text-xs font-bold uppercase tracking-[0.18em] text-brand"><span>04</span><span className="h-px w-8 bg-brand/40" /><span>Entwicklung</span></div>
          <div className="grid gap-10 md:grid-cols-[0.8fr_1.2fr] md:items-end"><div><h2 className="text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">Vom Rohmaterial<br /><span className="bg-gradient-to-r from-red-600 to-amber-500 bg-clip-text text-transparent">zum Live-Prototyp.</span></h2><p className="mt-5 text-base leading-relaxed text-slate-600">Wir haben die Lösung in nachvollziehbaren Schichten gebaut. Jede Schicht löst ein konkretes Problem – und bleibt über eine API austauschbar.</p></div><div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_20px_60px_rgba(15,23,42,0.05)]"><div className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Technologie-Stack</div><div className="mt-4 flex flex-wrap gap-2"><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-700 ring-1 ring-slate-200">Python · FastAPI</span><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-700 ring-1 ring-slate-200">React · Vite</span><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-700 ring-1 ring-slate-200">Jev · Clef</span><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-700 ring-1 ring-slate-200">Docker</span></div></div></div>
          <div className="relative mt-12 ml-2 border-l border-slate-200 pl-7 sm:ml-5 sm:pl-10">
            {[
              ['01', 'Daten erschliessen', 'Wir scrapen den Victorinox-Produktkatalog aus dem Produkt-PDF und bereiten Artikelnummern, Namen, Bilder, Werkzeuge und Verfügbarkeiten strukturiert auf. Zusätzlich erfassen wir Konkurrenzprodukte und Cross-References – zum Beispiel SWIZA, Roxon, Leatherman oder Gerber.', Database],
              ['02', 'Backend als Agent bauen', 'FastAPI orchestriert Vision, Katalogsuche, Matching und Feedback. Das Backend entscheidet nicht nur „was sieht es?“, sondern auch „welcher Victorinox-Ersatz passt funktional und ist verfügbar?“.', GitBranch],
              ['03', 'Open-Source-Vision integrieren', 'Für die Bilderkennung nutzen wir Clef von Cloudflare – ein Open-Source-Jev-Modell. Über die OpenAI-kompatible Schnittstelle bleibt der Vision-Baustein austauschbar, während unsere Regeln und Produktdaten die Empfehlung erklären.', Sparkles],
              ['04', 'React-Frontend darauf setzen', 'Die mobile React-App führt durch Scan, Vorschau, Analyse und Ergebnis. Konfidenz, Quellen, technische Unterschiede und Rückfragen werden als verständliche Oberfläche sichtbar.', Target],
              ['05', 'Alles in Docker verpacken', 'Backend, Frontend und Laufzeit werden reproduzierbar als Container betrieben. Genau das vereinfacht den nächsten Schritt: auf Azure deployen, skalieren und später an produktive Datenquellen anschliessen.', Check],
            ].map(([nr, title, text, Icon], index) => <motion.div key={nr} className="relative mb-9 last:mb-0" initial={{ opacity: 0, x: -14 }} whileInView={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.08 }} viewport={{ once: true }}><div className="absolute -left-[2.15rem] top-0 flex size-7 items-center justify-center rounded-full border border-red-200 bg-white text-[11px] font-bold text-brand sm:-left-[2.65rem]">{nr}</div><div className="flex gap-3"><Icon className="mt-0.5 size-5 shrink-0 text-brand" /><div><h3 className="text-lg font-semibold text-slate-900">{title}</h3><p className="mt-1 max-w-2xl text-sm leading-relaxed text-slate-600">{text}</p></div></div></motion.div>)}
          </div>
        </motion.section>

        <Kapitel {...chapters[3]} className="border-b border-slate-200">
          <div className="grid gap-8 md:grid-cols-[0.85fr_1.15fr] md:items-center"><div className="overflow-hidden rounded-[28px] bg-white p-4 shadow-[0_20px_60px_rgba(15,23,42,0.08)]"><img src="/demo/swiza-d03.jpg" alt="SWIZA D03 Beispiel" className="aspect-[4/3] w-full object-contain" /><div className="mt-3 border-t border-slate-200 pt-3 text-xs text-slate-500">Eingabe · SWIZA D03 AM</div></div><div><div className="mb-4 inline-flex items-center gap-2 rounded-full bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 ring-1 ring-red-100"><Check className="size-3.5" /> Beispiel aus dem Case</div><h2 className="text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">Nicht nur ähnlich.<br /><span className="bg-gradient-to-r from-red-600 to-amber-500 bg-clip-text text-transparent">Begründet passend.</span></h2><p className="mt-5 text-base leading-relaxed text-slate-600">Aus dem Konkurrenzprodukt SWIZA D03 wird ein passender Victorinox-Vorschlag: <strong className="text-slate-900">Spartan</strong>. Die Empfehlung basiert auf sichtbaren Funktionen, Produktmerkmalen und dem verfügbaren Katalog – nicht auf einer erfundenen Spezifikation.</p><div className="mt-6 flex items-center gap-3"><div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">SWIZA D03</div><ArrowRight className="size-4 text-brand" /><div className="rounded-xl bg-gradient-to-r from-red-500 to-red-600 px-3 py-2 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(227,6,19,0.25)]">Victorinox Spartan</div></div></div></div>
        </Kapitel>

        <Kapitel {...chapters[4]}>
          <div className="grid gap-10 md:grid-cols-[1.1fr_0.9fr]"><div><h2 className="text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">Vertrauen entsteht,<br /><span className="bg-gradient-to-r from-red-600 to-amber-500 bg-clip-text text-transparent">wenn Unsicherheit sichtbar bleibt.</span></h2><p className="mt-5 max-w-xl text-base leading-relaxed text-slate-600">Der Prototyp ist bewusst auf die SAK-Taschenmesser fokussiert. Bei knappen Treffern zeigt er mehrere Kandidaten und fragt nach einem weiteren Foto oder Merkmal – statt zu raten.</p><div className="mt-7 flex flex-wrap gap-2 text-xs text-slate-700"><span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">153 Pocket Knives im Scope</span><span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">Top-3 statt Black Box</span><span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">Quellenbasierte Daten</span></div></div><div className="rounded-[28px] border border-amber-200 bg-gradient-to-br from-amber-50 to-red-50 p-6 shadow-[0_20px_60px_rgba(251,191,36,0.08)]"><CircleAlert className="size-6 text-amber-500" /><div className="mt-4 text-lg font-semibold text-slate-900">Noch nicht sicher genug?</div><p className="mt-2 text-sm leading-relaxed text-slate-700">„Bitte fotografiere das Messer geöffnet oder zeige die Artikelnummer.“</p><div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white"><div className="h-full w-2/3 rounded-full bg-gradient-to-r from-amber-400 to-yellow-400" /></div><div className="mt-2 text-xs text-slate-600">Konfidenz wird erklärt, nicht versteckt.</div></div></div>
          <div className="mt-16 border-t border-slate-200 pt-10"><div className="flex items-start gap-4"><Users className="mt-1 size-6 shrink-0 text-brand" /><div><h3 className="text-xl font-semibold text-slate-900">Von der Demo zum regionalen Nutzen</h3><p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">Was im Hackathon mit SAK startet, kann Verkauf, Customer Service, Produktmanagement und Handel im Alltag verbinden: Schweizer Produktwissen wird schneller auffindbar, Ersatzempfehlungen werden nachvollziehbar und Feedback fliesst zurück in die Verbesserung.</p></div></div></div>
        </Kapitel>

        <footer className="border-t border-slate-200 py-14 text-center"><p className="text-sm text-slate-600">Bereit für den ersten Scan?</p><Link to="/" className="mt-4 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-red-500 to-red-600 px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(227,6,19,0.25)] transition hover:brightness-110">App ausprobieren <ArrowRight className="size-4" /></Link><p className="mt-8 text-xs text-slate-500">Victorinox Product Match Agent · Zentralhack Challenge</p></footer>
      </div>
    </div>
  )
}
