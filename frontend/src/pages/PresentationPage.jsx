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
import { Logo } from '../components/Header.jsx'

const chapters = [
  { id: 'ausgangspunkt', nummer: '01', label: 'Ausgangspunkt' },
  { id: 'idee', nummer: '02', label: 'Die Idee' },
  { id: 'ablauf', nummer: '03', label: 'Der Ablauf' },
  { id: 'beispiel', nummer: '04', label: 'Der Beweis' },
  { id: 'naechster-schritt', nummer: '05', label: 'Der nächste Schritt' },
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
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <Icon className="size-5 text-brand" />
      <div className="mt-3 text-sm font-semibold">{title}</div>
      <p className="mt-1 text-xs leading-relaxed text-zinc-500">{text}</p>
    </div>
  )
}

export default function PresentationPage() {
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 })

  return (
    <div className="overflow-hidden bg-zinc-950 text-white">
      <motion.div className="fixed inset-x-0 top-0 z-50 h-1 origin-left bg-brand" style={{ scaleX }} />
      <div className="mx-auto max-w-4xl px-5 sm:px-10">
        <nav className="flex items-center justify-between py-5 text-sm">
          <Link to="/" className="flex items-center gap-2.5"><Logo className="size-8" /><span className="font-semibold tracking-tight">Product Match Agent</span></Link>
          <Link to="/" className="rounded-full border border-white/20 px-3 py-1.5 text-xs font-medium text-white/80 transition hover:border-white/50 hover:text-white">App öffnen</Link>
        </nav>

        <header className="relative flex min-h-[78dvh] flex-col justify-center py-20">
          <div className="pointer-events-none absolute -right-32 top-16 size-80 rounded-full bg-brand/20 blur-3xl" />
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-brand/40 bg-brand/10 px-3 py-1.5 text-xs font-semibold text-red-200"><Sparkles className="size-3.5" /> Zentralhack · Victorinox</div>
            <h1 className="max-w-3xl text-5xl font-bold leading-[0.98] tracking-[-0.04em] sm:text-7xl">Vom Foto zur<br /><span className="text-brand">passenden Klinge.</span></h1>
            <p className="mt-7 max-w-xl text-lg leading-relaxed text-zinc-300">Die Geschichte hinter unserem Product Match Agent – und warum aus einer Produktfrage ein klarer, nachvollziehbarer Vorschlag wird.</p>
          </motion.div>
          <a href="#ausgangspunkt" className="mt-14 flex w-fit items-center gap-2 text-sm font-medium text-zinc-400 transition hover:text-white"><ArrowDown className="size-4 animate-bounce" /> Story starten</a>
        </header>

        <div className="sticky top-0 z-40 -mx-5 overflow-x-auto border-y border-white/10 bg-zinc-950/90 px-5 py-3 backdrop-blur sm:-mx-10 sm:px-10">
          <div className="flex min-w-max gap-5 text-xs font-medium text-zinc-500">{chapters.map((chapter) => <a key={chapter.id} href={`#${chapter.id}`} className="transition hover:text-white"><span className="mr-1.5 text-brand">{chapter.nummer}</span>{chapter.label}</a>)}</div>
        </div>

        <Kapitel {...chapters[0]} className="border-b border-white/10">
          <div className="grid gap-10 md:grid-cols-[1.1fr_0.9fr] md:items-end">
            <div><h2 className="max-w-xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl">Ein Foto. Viele ähnliche Antworten.</h2><p className="mt-5 max-w-lg text-base leading-relaxed text-zinc-400">Heute wird ein fotografiertes Produkt manuell identifiziert. Danach beginnt die Suche in Katalogen, Produktdaten und Cross-Reference-Tabellen – besonders aufwendig, wenn ein Artikel ausgelaufen ist oder ein Konkurrenzprodukt ersetzt werden soll.</p></div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-5"><div className="mb-4 flex items-center gap-3 text-sm text-zinc-400"><Camera className="size-5 text-brand" /> Ausgangslage</div><div className="flex items-center gap-3 text-sm"><div className="rounded-xl bg-zinc-800 px-3 py-2 text-zinc-300">Foto</div><ArrowRight className="size-4 text-brand" /><div className="rounded-xl bg-zinc-800 px-3 py-2 text-zinc-300">Suche</div><ArrowRight className="size-4 text-brand" /><div className="rounded-xl bg-zinc-800 px-3 py-2 text-zinc-300">?</div></div><p className="mt-5 text-xs leading-relaxed text-zinc-500">Wissen ist da – aber noch nicht in einem Weg verbunden.</p></div>
          </div>
        </Kapitel>

        <Kapitel {...chapters[1]} className="border-b border-white/10">
          <div className="grid gap-10 md:grid-cols-[0.9fr_1.1fr] md:items-center"><div><h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">Wir verbinden,<br /><span className="text-brand">was zusammengehört.</span></h2><p className="mt-5 text-base leading-relaxed text-zinc-400">Ein multimodaler Agent liest das Bild, gleicht Merkmale mit dem Katalog ab und macht daraus eine fachlich begründete Victorinox-Empfehlung.</p></div><div className="grid grid-cols-2 gap-3"><Signal icon={ScanSearch} title="Sehen" text="Marke, Modell, Form und sichtbare Werkzeuge erkennen." /><Signal icon={Database} title="Verstehen" text="Freigegebene Produktdaten und Cross-References nutzen." /><Signal icon={GitBranch} title="Vergleichen" text="Funktionen, Masse und Verfügbarkeit gewichten." /><Signal icon={Target} title="Empfehlen" text="Top-Treffer mit Konfidenz und Begründung zeigen." /></div></div>
        </Kapitel>

        <Kapitel {...chapters[2]} className="border-b border-white/10">
          <h2 className="max-w-2xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl">Der rote Faden<br />in drei Schritten.</h2>
          <div className="mt-12 grid gap-4 md:grid-cols-3">{[
            ['01', Camera, 'Foto aufnehmen', 'Mit dem Smartphone – auch ein Demo-Bild reicht für den ersten Durchlauf.'],
            ['02', ScanSearch, 'Erkennen & abgleichen', 'Vision, Produktdaten und Merkmale werden in einem Workflow zusammengeführt.'],
            ['03', Sparkles, 'Victorinox vorschlagen', 'Ein oder mehrere Treffer – priorisiert, technisch belegt und transparent.'],
          ].map(([nr, Icon, title, text], index) => <motion.div key={nr} className="relative rounded-3xl bg-white p-6 text-zinc-900" initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.12 }} viewport={{ once: true }}><div className="flex items-center justify-between"><span className="text-4xl font-bold text-brand/25">{nr}</span><Icon className="size-6 text-brand" /></div><h3 className="mt-8 text-lg font-bold">{title}</h3><p className="mt-2 text-sm leading-relaxed text-zinc-500">{text}</p></motion.div>)}</div>
        </Kapitel>

        <Kapitel {...chapters[3]} className="border-b border-white/10">
          <div className="grid gap-8 md:grid-cols-[0.85fr_1.15fr] md:items-center"><div className="overflow-hidden rounded-3xl bg-white p-4"><img src="/demo/swiza-d03.jpg" alt="SWIZA D03 Beispiel" className="aspect-[4/3] w-full object-contain" /><div className="mt-3 border-t border-zinc-100 pt-3 text-xs text-zinc-500">Eingabe · SWIZA D03 AM</div></div><div><div className="mb-4 inline-flex items-center gap-2 rounded-full bg-brand/10 px-3 py-1.5 text-xs font-semibold text-red-200"><Check className="size-3.5" /> Beispiel aus dem Case</div><h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">Nicht nur ähnlich.<br /><span className="text-brand">Begründet passend.</span></h2><p className="mt-5 text-base leading-relaxed text-zinc-400">Aus dem Konkurrenzprodukt SWIZA D03 wird ein passender Victorinox-Vorschlag: <strong className="text-white">Spartan</strong>. Die Empfehlung basiert auf sichtbaren Funktionen, Produktmerkmalen und dem verfügbaren Katalog – nicht auf einer erfundenen Spezifikation.</p><div className="mt-6 flex items-center gap-3"><div className="rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-sm">SWIZA D03</div><ArrowRight className="size-4 text-brand" /><div className="rounded-xl bg-brand px-3 py-2 text-sm font-semibold">Victorinox Spartan</div></div></div></div>
        </Kapitel>

        <Kapitel {...chapters[4]}>
          <div className="grid gap-10 md:grid-cols-[1.1fr_0.9fr]"><div><h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">Vertrauen entsteht,<br /><span className="text-brand">wenn Unsicherheit sichtbar bleibt.</span></h2><p className="mt-5 max-w-xl text-base leading-relaxed text-zinc-400">Der Prototyp ist bewusst auf die SAK-Taschenmesser fokussiert. Bei knappen Treffern zeigt er mehrere Kandidaten und fragt nach einem weiteren Foto oder Merkmal – statt zu raten.</p><div className="mt-7 flex flex-wrap gap-2 text-xs text-zinc-300"><span className="rounded-full border border-white/15 px-3 py-1.5">153 Pocket Knives im Scope</span><span className="rounded-full border border-white/15 px-3 py-1.5">Top-3 statt Black Box</span><span className="rounded-full border border-white/15 px-3 py-1.5">Quellenbasierte Daten</span></div></div><div className="rounded-3xl border border-amber-300/20 bg-amber-300/10 p-6"><CircleAlert className="size-6 text-amber-300" /><div className="mt-4 text-lg font-semibold">Noch nicht sicher genug?</div><p className="mt-2 text-sm leading-relaxed text-amber-100/70">„Bitte fotografiere das Messer geöffnet oder zeige die Artikelnummer.“</p><div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full w-2/3 rounded-full bg-amber-300" /></div><div className="mt-2 text-xs text-amber-200/60">Konfidenz wird erklärt, nicht versteckt.</div></div></div>
          <div className="mt-16 border-t border-white/10 pt-10"><div className="flex items-start gap-4"><Users className="mt-1 size-6 shrink-0 text-brand" /><div><h3 className="text-xl font-semibold">Von der Demo zum regionalen Nutzen</h3><p className="mt-2 max-w-2xl text-sm leading-relaxed text-zinc-400">Was im Hackathon mit SAK startet, kann Verkauf, Customer Service, Produktmanagement und Handel im Alltag verbinden: Schweizer Produktwissen wird schneller auffindbar, Ersatzempfehlungen werden nachvollziehbar und Feedback fliesst zurück in die Verbesserung.</p></div></div></div>
        </Kapitel>

        <footer className="border-t border-white/10 py-14 text-center"><p className="text-sm text-zinc-400">Bereit für den ersten Scan?</p><Link to="/" className="mt-4 inline-flex items-center gap-2 rounded-full bg-brand px-5 py-3 text-sm font-semibold transition hover:bg-brand-dark">App ausprobieren <ArrowRight className="size-4" /></Link><p className="mt-8 text-xs text-zinc-600">Victorinox Product Match Agent · Zentralhack Challenge</p></footer>
      </div>
    </div>
  )
}
