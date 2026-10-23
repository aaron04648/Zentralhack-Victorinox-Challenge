import { Link, NavLink } from 'react-router-dom'
import { LayoutGrid, ScanLine } from 'lucide-react'

export function Logo({ className = 'size-8' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="var(--color-brand)" />
      <path d="M13 7h6v6h6v6h-6v6h-6v-6H7v-6h6z" fill="#fff" />
    </svg>
  )
}

function NavEintrag({ to, icon: Icon, children }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition ${
          isActive ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100'
        }`
      }
    >
      <Icon className="size-4" />
      <span className="hidden sm:inline">{children}</span>
    </NavLink>
  )
}

export default function Header() {
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
        <nav className="flex items-center gap-1">
          <NavEintrag to="/" icon={ScanLine}>Scannen</NavEintrag>
          <NavEintrag to="/katalog" icon={LayoutGrid}>Katalog</NavEintrag>
        </nav>
      </div>
    </header>
  )
}
