import { Link, useLocation } from 'react-router-dom'
import { ScanLine } from 'lucide-react'

export function Logo({ className = 'size-8' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="var(--color-brand)" />
      <path d="M13 7h6v6h6v6h-6v6h-6v-6H7v-6h6z" fill="#fff" />
    </svg>
  )
}

export default function Header() {
  const { pathname } = useLocation()
  return (
    <header className="sticky top-0 z-30 border-b border-zinc-200/80 bg-white/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2.5">
          <Logo />
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-tight">Product Match Agent</div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">Victorinox · SAK</div>
          </div>
        </Link>
        <div className="flex items-center gap-2">
          {pathname !== '/praesentation' && <Link to="/praesentation" className="rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50">Story ansehen</Link>}
          {pathname !== '/' && <Link to="/" className="flex items-center gap-1.5 rounded-full bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-zinc-800"><ScanLine className="size-4" />Neuer Scan</Link>}
        </div>
      </div>
    </header>
  )
}
