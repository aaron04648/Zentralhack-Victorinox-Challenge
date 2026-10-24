import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import qrcode from 'qrcode-generator'
import { CheckCircle2, Loader2, Smartphone, X } from 'lucide-react'
import * as api from '../api/client.js'

const ADRESSE_KEY = 'handy-adresse'
const POLL_MS = 1000
const istLokal = (host) => ['localhost', '127.0.0.1', '[::1]'].includes(host)

function gespeicherteAdresse() {
  try {
    return localStorage.getItem(ADRESSE_KEY) ?? ''
  } catch {
    return ''
  }
}

function qrSvg(text) {
  const qr = qrcode(0, 'M')
  qr.addData(text)
  qr.make()
  return qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true })
}

/**
 * Handy als Kamera: zeigt einen QR-Code, das Handy macht damit das Foto und schickt es zurück.
 * Der Computer fragt jede Sekunde nach und übergibt neue Fotos an onFoto.
 *
 * Die Adresse fürs Handy:
 * - App unter localhost: Das Backend öffnet für diese Kopplung einen https-Tunnel (cloudflared) und
 *   schliesst ihn wieder, sobald das Foto da ist oder der Dialog zu ist. Geht auch in WLANs, in denen
 *   sich die Geräte nicht sehen. Schlägt das fehl: WLAN-Adresse (HANDY_BASIS_URL oder von Hand).
 * - Sonst (z. B. über einen Tunnel geöffnet): die eigene Adresse.
 */
export default function HandyKoppeln({ onFoto, onSchliessen }) {
  const [sitzung, setSitzung] = useState(null)
  const [verbunden, setVerbunden] = useState(false)
  const [laedtFoto, setLaedtFoto] = useState(false)
  const [fehler, setFehler] = useState(null)
  const [adresse, setAdresse] = useState(() => (istLokal(location.hostname) ? gespeicherteAdresse() : location.origin))
  const [adresseBearbeiten, setAdresseBearbeiten] = useState(false)
  const [tunnel, setTunnel] = useState(() => istLokal(location.hostname))
  const gesehen = useRef(0)
  const fotoMelden = useRef(onFoto)
  fotoMelden.current = onFoto

  // Sitzung starten (und neu starten, wenn sie abgelaufen ist)
  function starten(mitTunnel = tunnel) {
    setFehler(null)
    setVerbunden(false)
    setSitzung(null)
    gesehen.current = 0
    api
      .handyStarten({ tunnel: mitTunnel })
      .then((s) => {
        setSitzung(s)
        if (!s.tunnel && istLokal(location.hostname) && !gespeicherteAdresse() && s.url) setAdresse(new URL(s.url).origin)
      })
      .catch((e) => {
        if (!mitTunnel) return setFehler(`Kopplung nicht möglich (${e.message})`)
        // Kein Tunnel möglich: direkt über die WLAN-Adresse versuchen
        setTunnel(false)
        setFehler(null)
        starten(false)
      })
  }
  useEffect(() => starten(), [])

  // Dialog zu: Kopplung beenden, damit der Tunnel sofort schliesst
  useEffect(() => () => sitzung && api.handyBeenden(sitzung.id), [sitzung])

  // Warten aufs Handy: verbunden? neues Foto?
  useEffect(() => {
    if (!sitzung) return
    let aktiv = true
    const t = setInterval(async () => {
      try {
        const status = await api.handyStatus(sitzung.id)
        if (!aktiv) return
        setVerbunden(status.verbunden)
        if (status.nummer > gesehen.current) {
          gesehen.current = status.nummer
          setLaedtFoto(true)
          const datei = await api.handyFotoHolen(sitzung.id)
          if (aktiv) fotoMelden.current(datei)
        }
      } catch (e) {
        if (aktiv && e.status === 404) starten()
      }
    }, POLL_MS)
    return () => {
      aktiv = false
      clearInterval(t)
    }
  }, [sitzung])

  useEffect(() => {
    const taste = (e) => e.key === 'Escape' && onSchliessen()
    window.addEventListener('keydown', taste)
    return () => window.removeEventListener('keydown', taste)
  }, [onSchliessen])

  const link = sitzung?.tunnel ? sitzung.url : sitzung && adresse ? `${adresse.replace(/\/$/, '')}/handy/${sitzung.id}` : null
  const svg = useMemo(() => (link ? qrSvg(link) : null), [link])

  function adresseSpeichern(wert) {
    setAdresse(wert)
    try {
      localStorage.setItem(ADRESSE_KEY, wert)
    } catch {
      // nur für diese Sitzung
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/60 p-4 backdrop-blur-sm" onClick={onSchliessen}>
      <div className="relative w-full max-w-sm rounded-3xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <button onClick={onSchliessen} aria-label="Schliessen" className="absolute right-3 top-3 rounded-full p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700">
          <X className="size-5" />
        </button>
        <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
          <Smartphone className="size-5 text-brand" /> Mit dem Handy scannen
        </div>

        <div className="mx-auto flex aspect-square w-56 items-center justify-center rounded-2xl border border-zinc-100 bg-white p-2">
          {fehler ? (
            <p className="text-center text-sm text-brand">{fehler}</p>
          ) : laedtFoto ? (
            <div className="flex flex-col items-center gap-2 text-sm text-zinc-500">
              <Loader2 className="size-8 animate-spin text-brand" /> Foto wird übernommen …
            </div>
          ) : svg ? (
            <div className="size-full [&>svg]:size-full" dangerouslySetInnerHTML={{ __html: svg }} />
          ) : sitzung ? (
            <p className="px-2 text-center text-sm text-zinc-500">Trage unten die WLAN-Adresse dieses Computers ein.</p>
          ) : (
            <div className="flex flex-col items-center gap-2 px-2 text-center text-sm text-zinc-500">
              <Loader2 className="size-8 animate-spin text-zinc-300" />
              {tunnel && 'Sichere Verbindung fürs Handy wird aufgebaut …'}
            </div>
          )}
        </div>

        <div className="mt-4 flex items-center justify-center gap-2 text-sm">
          {verbunden ? (
            <>
              <CheckCircle2 className="size-4 text-emerald-600" />
              <span className="font-medium text-emerald-700">Handy verbunden, jetzt Foto aufnehmen</span>
            </>
          ) : (
            <>
              <span className="size-2 animate-pulse rounded-full bg-zinc-300" />
              <span className="text-zinc-500">Warte auf das Handy …</span>
            </>
          )}
        </div>

        <ol className="mt-4 space-y-1 text-sm text-zinc-600">
          <li>1. QR-Code mit der Handy-Kamera scannen</li>
          <li>2. Auf dem Handy das Messer fotografieren</li>
          <li>3. Das Foto erscheint hier automatisch</li>
        </ol>

        <div className="mt-4 border-t border-zinc-100 pt-3 text-xs text-zinc-500">
          {sitzung?.tunnel ? (
            <p>
              Sichere Verbindung über das Internet, nur für diese Kopplung. Sie schliesst automatisch, sobald das Foto da
              ist. Das Handy braucht nur Internet, nicht dasselbe WLAN.
            </p>
          ) : tunnel ? null : adresseBearbeiten || !adresse ? (
            <label className="block">
              Adresse dieses Computers im WLAN
              <input
                autoFocus={adresseBearbeiten}
                value={adresse}
                onChange={(e) => adresseSpeichern(e.target.value.trim())}
                onKeyDown={(e) => e.key === 'Enter' && setAdresseBearbeiten(false)}
                placeholder="http://192.168.1.20:3000"
                className="mt-1 w-full rounded-lg border border-zinc-200 px-2.5 py-1.5 text-sm text-zinc-800 outline-none focus:ring-4 focus:ring-zinc-100"
              />
            </label>
          ) : (
            <div className="flex items-center justify-between gap-2">
              <span className="truncate">{link}</span>
              <button onClick={() => setAdresseBearbeiten(true)} className="shrink-0 font-medium text-zinc-700 underline">
                ändern
              </button>
            </div>
          )}
          {!tunnel && <p className="mt-1.5">Handy und Computer müssen im selben WLAN sein.</p>}
        </div>
      </div>
    </div>,
    document.body,
  )
}
