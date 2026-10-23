import { konfidenzTon } from '../lib/format.js'

const FARBEN = { ok: 'var(--color-ok)', neutral: '#52525b', warn: 'var(--color-warn)' }

/** Ring mit Prozentwert; Farbe kippt unterhalb der Konfidenz-Schwelle auf Orange. */
export default function KonfidenzRing({ wert, groesse = 64, label }) {
  const r = 26
  const umfang = 2 * Math.PI * r
  const farbe = FARBEN[konfidenzTon(wert)]
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: groesse, height: groesse }}>
        <svg viewBox="0 0 64 64" className="size-full -rotate-90">
          <circle cx="32" cy="32" r={r} fill="none" stroke="#e4e4e7" strokeWidth="6" />
          <circle
            cx="32"
            cy="32"
            r={r}
            fill="none"
            stroke={farbe}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={umfang}
            strokeDashoffset={umfang * (1 - wert)}
            style={{ transition: 'stroke-dashoffset 900ms ease-out' }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold tabular-nums" style={{ color: farbe }}>
          {Math.round(wert * 100)}%
        </span>
      </div>
      {label && <span className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">{label}</span>}
    </div>
  )
}
