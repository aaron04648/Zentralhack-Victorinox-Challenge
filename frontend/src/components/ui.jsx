import { useState } from 'react'
import { Package } from 'lucide-react'
import { bild, lagerstatus } from '../lib/format.js'

// Kleine, gemeinsam genutzte UI-Bausteine.

const TOENE = {
  ok: 'bg-ok-soft text-ok',
  warn: 'bg-warn-soft text-warn',
  brand: 'bg-brand-soft text-brand-dark',
  dunkel: 'bg-zinc-900 text-white',
  neutral: 'bg-zinc-100 text-zinc-700',
}

export function Badge({ ton = 'neutral', icon: Icon, children, className = '' }) {
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${TOENE[ton]} ${className}`}>
      {Icon && <Icon className="size-3.5" />}
      {children}
    </span>
  )
}

export function StatusBadge({ status }) {
  const { label, ton } = lagerstatus(status)
  return (
    <Badge ton={ton}>
      <span className={`size-1.5 rounded-full ${ton === 'ok' ? 'bg-ok' : ton === 'warn' ? 'bg-warn' : 'bg-zinc-400'}`} />
      {label}
    </Badge>
  )
}

export function Karte({ className = '', children, ...rest }) {
  return (
    <section className={`rounded-2xl border border-zinc-200 bg-white shadow-sm ${className}`} {...rest}>
      {children}
    </section>
  )
}

export function Abschnitt({ titel, aktion, children }) {
  return (
    <div className="mt-8">
      <div className="mb-3 flex items-end justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">{titel}</h2>
        {aktion}
      </div>
      {children}
    </div>
  )
}

export function ProduktBild({ url, alt, breite = 400, className = '' }) {
  const [kaputt, setKaputt] = useState(false)
  return (
    <div className={`flex items-center justify-center overflow-hidden bg-white ${className}`}>
      {url && !kaputt ? (
        <img
          src={url.startsWith('data:') ? url : bild(url, breite)}
          alt={alt}
          loading="lazy"
          onError={() => setKaputt(true)}
          className="size-full object-contain"
        />
      ) : (
        <Package className="size-8 text-zinc-300" />
      )}
    </div>
  )
}

export function Button({ variante = 'primaer', className = '', icon: Icon, children, ...rest }) {
  const stile = {
    primaer: 'bg-brand text-white hover:bg-brand-dark shadow-sm shadow-brand/20',
    dunkel: 'bg-zinc-900 text-white hover:bg-zinc-800',
    sekundaer: 'bg-white text-zinc-900 border border-zinc-200 hover:bg-zinc-50',
    geist: 'text-zinc-600 hover:bg-zinc-100',
  }
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-semibold transition active:scale-[0.98] disabled:opacity-50 ${stile[variante]} ${className}`}
      {...rest}
    >
      {Icon && <Icon className="size-4" />}
      {children}
    </button>
  )
}
