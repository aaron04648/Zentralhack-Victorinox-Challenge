import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Camera, ImagePlus, Timer, TimerOff, X } from 'lucide-react'
import * as api from '../api/client.js'

// Auto-Auslöser in zwei Stufen:
// 1. Im Browser, ohne KI (klein, MESS_BREITE px): Bewegung = mittlere Helligkeitsdifferenz zum
//    vorherigen Frame, Schärfe = mittlere Kantenstärke (Laplace) relativ zur bisher besten.
// 2. Ist das Bild ruhig und scharf, geht ein kleines Standbild an Clef: Ist ein Messer zu sehen?
//    Nur bei Ja füllt sich der Ring und nach HALTEN_MS wird ausgelöst. Das Ergebnis gilt, bis sich
//    das Bild deutlich verändert; ein Nein wird frühestens nach NEU_PRUEFEN_MS wiederholt.
const MESS_BREITE = 160
const TAKT_MS = 120
const HALTEN_MS = 900
const PRUEF_BREITE = 384
const MESSER_SICHER = 0.5
const MAX_ABWEICHUNG = 12 // Helligkeitsstufen pro Pixel gegenüber dem geprüften Bild: darüber neue Szene
const NEU_PRUEFEN_MS = 2500
const MAX_BEWEGUNG = 5 // Helligkeitsstufen (0..255) pro Pixel
const MIN_SCHAERFE_ANTEIL = 0.75 // im Verhältnis zur besten bisher gemessenen Schärfe
const MIN_KONTRAST = 18 // Standardabweichung der Helligkeit: darunter ist nichts im Bild

function messen(ctx, b, h, vorher) {
  const daten = ctx.getImageData(0, 0, b, h).data
  const grau = new Float32Array(b * h)
  let summe = 0
  for (let i = 0; i < grau.length; i++) {
    grau[i] = 0.299 * daten[i * 4] + 0.587 * daten[i * 4 + 1] + 0.114 * daten[i * 4 + 2]
    summe += grau[i]
  }
  const mittel = summe / grau.length
  let varianz = 0
  let kanten = 0
  let bewegung = 0
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < b - 1; x++) {
      const i = y * b + x
      kanten += Math.abs(4 * grau[i] - grau[i - 1] - grau[i + 1] - grau[i - b] - grau[i + b])
    }
  }
  for (let i = 0; i < grau.length; i++) {
    varianz += (grau[i] - mittel) ** 2
    if (vorher) bewegung += Math.abs(grau[i] - vorher[i])
  }
  return {
    grau,
    schaerfe: kanten / ((b - 2) * (h - 2)),
    kontrast: Math.sqrt(varianz / grau.length),
    bewegung: vorher ? bewegung / grau.length : Infinity,
  }
}

/**
 * Vollbild-Kamera im Browser (fragt nach der Kamera-Erlaubnis). Löst automatisch aus, sobald das
 * Bild ruhig und scharf ist, oder per Knopf. Ohne Kamera/Erlaubnis: Hinweis + Weg zur Foto-App.
 */
const abweichung = (a, b) => {
  let summe = 0
  for (let i = 0; i < a.length; i++) summe += Math.abs(a[i] - b[i])
  return summe / a.length
}

export default function LiveKamera({ onFoto, onSchliessen, onFotoApp }) {
  const video = useRef(null)
  const messCanvas = useRef(null)
  const stream = useRef(null)
  const vorher = useRef(null)
  const besteSchaerfe = useRef(0)
  const ruhigSeit = useRef(null)
  const [fehler, setFehler] = useState(null)
  const [bereit, setBereit] = useState(false)
  const [auto, setAuto] = useState(true)
  const [fortschritt, setFortschritt] = useState(0)
  const [hinweis, setHinweis] = useState('Kamera wird gestartet …')
  const [blitz, setBlitz] = useState(false)
  const ausgeloest = useRef(false)
  // Messer-Prüfung: offen | laeuft | ja | nein | aus (nicht verfügbar -> nur manuell auslösen)
  const pruefung = useRef({ status: 'offen' })

  // Kamera starten (Rückkamera bevorzugt) und beim Schliessen wieder freigeben
  useEffect(() => {
    let abgebrochen = false
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      .then((s) => {
        if (abgebrochen) return s.getTracks().forEach((t) => t.stop())
        stream.current = s
        video.current.srcObject = s
        return video.current.play().then(() => setBereit(true))
      })
      .catch((e) => {
        setFehler(
          e?.name === 'NotAllowedError'
            ? 'Der Kamera-Zugriff wurde nicht erlaubt. Du kannst ihn in den Browser-Einstellungen freigeben oder die Foto-App verwenden.'
            : `Die Kamera konnte nicht gestartet werden (${e?.message ?? 'unbekannter Fehler'}).`,
        )
      })
    return () => {
      abgebrochen = true
      stream.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  const ausloesen = useCallback(() => {
    const v = video.current
    if (!v?.videoWidth || ausgeloest.current) return
    ausgeloest.current = true
    const canvas = document.createElement('canvas')
    canvas.width = v.videoWidth
    canvas.height = v.videoHeight
    canvas.getContext('2d').drawImage(v, 0, 0)
    setBlitz(true)
    canvas.toBlob(
      (blob) => {
        stream.current?.getTracks().forEach((t) => t.stop())
        onFoto(new File([blob], `kamera-${Date.now()}.jpg`, { type: 'image/jpeg' }))
      },
      'image/jpeg',
      0.9,
    )
  }, [onFoto])

  // Kleines Standbild an Clef: Ist ein Messer zu sehen? (läuft parallel zur Messschleife)
  const messerPruefen = useCallback((v, grau) => {
    pruefung.current = { status: 'laeuft' }
    const canvas = document.createElement('canvas')
    canvas.width = PRUEF_BREITE
    canvas.height = Math.round((v.videoHeight / v.videoWidth) * PRUEF_BREITE)
    canvas.getContext('2d').drawImage(v, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) =>
        api
          .messerSichtbar(blob)
          .then((p) => {
            pruefung.current =
              p == null ? { status: 'aus' } : { status: p >= MESSER_SICHER ? 'ja' : 'nein', grau, zeit: performance.now() }
          })
          .catch(() => {
            pruefung.current = { status: 'nein', grau, zeit: performance.now() }
          }),
      'image/jpeg',
      0.7,
    )
  }, [])

  // Messschleife für den Auto-Auslöser
  useEffect(() => {
    if (!bereit) return
    const t = setInterval(() => {
      const v = video.current
      if (!v?.videoWidth || ausgeloest.current) return
      const b = MESS_BREITE
      const h = Math.round((v.videoHeight / v.videoWidth) * b)
      const canvas = messCanvas.current
      canvas.width = b
      canvas.height = h
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      ctx.drawImage(v, 0, 0, b, h)
      const m = messen(ctx, b, h, vorher.current)
      vorher.current = m.grau
      // Beste Schärfe langsam vergessen, damit ein früher Glückstreffer nicht ewig die Latte setzt
      besteSchaerfe.current = Math.max(m.schaerfe, besteSchaerfe.current * 0.995)

      // Ein Prüfergebnis gilt nur für die Szene, in der es entstanden ist
      const vorherig = pruefung.current
      if (vorherig.grau && ['ja', 'nein'].includes(vorherig.status) && abweichung(m.grau, vorherig.grau) > MAX_ABWEICHUNG) {
        pruefung.current = { status: 'offen' }
      }

      let text
      let ok = false
      if (m.kontrast < MIN_KONTRAST) text = 'Messer ins Bild halten'
      else if (m.bewegung > MAX_BEWEGUNG) text = 'Ruhig halten …'
      else if (m.schaerfe < besteSchaerfe.current * MIN_SCHAERFE_ANTEIL) text = 'Scharf stellen …'
      else {
        const p = pruefung.current
        if (p.status === 'offen' || (p.status === 'nein' && performance.now() - p.zeit > NEU_PRUEFEN_MS)) {
          messerPruefen(v, m.grau)
        }
        const status = pruefung.current.status
        if (status === 'ja') {
          text = auto ? 'Messer erkannt, nicht bewegen' : 'Messer erkannt, Auslöser drücken'
          ok = true
        } else if (status === 'nein') text = 'Kein Messer erkannt, Messer ins Bild halten'
        else if (status === 'aus') text = 'Bereit, Auslöser drücken'
        else text = 'Suche Messer …'
      }
      setHinweis(text)

      if (!auto || !ok) {
        ruhigSeit.current = null
        setFortschritt(0)
        return
      }
      ruhigSeit.current ??= performance.now()
      const anteil = Math.min((performance.now() - ruhigSeit.current) / HALTEN_MS, 1)
      setFortschritt(anteil)
      if (anteil >= 1) ausloesen()
    }, TAKT_MS)
    return () => clearInterval(t)
  }, [bereit, auto, ausloesen, messerPruefen])

  // Escape schliesst
  useEffect(() => {
    const taste = (e) => e.key === 'Escape' && onSchliessen()
    window.addEventListener('keydown', taste)
    return () => window.removeEventListener('keydown', taste)
  }, [onSchliessen])

  const umfang = 2 * Math.PI * 38

  return createPortal(
    <div className="fixed inset-0 z-50 flex flex-col bg-black text-white">
      <video ref={video} playsInline muted className="absolute inset-0 size-full object-cover" />
      <canvas ref={messCanvas} hidden />
      {blitz && <div className="kamera-blitz pointer-events-none absolute inset-0 bg-white" />}

      {/* Sucherrahmen: färbt sich grün, sobald der Auto-Auslöser zählt */}
      {bereit && !fehler && (
        <div className="pointer-events-none absolute inset-x-[8%] inset-y-[18%]">
          {['left-0 top-0 border-l-4 border-t-4', 'right-0 top-0 border-r-4 border-t-4', 'left-0 bottom-0 border-l-4 border-b-4', 'right-0 bottom-0 border-r-4 border-b-4'].map((pos) => (
            <span
              key={pos}
              className={`absolute size-10 rounded-[4px] transition-colors ${pos} ${fortschritt > 0 ? 'border-emerald-400' : 'border-white/80'}`}
            />
          ))}
        </div>
      )}

      <div className="relative flex items-center justify-between p-4">
        <button onClick={onSchliessen} aria-label="Kamera schliessen" className="rounded-full bg-black/40 p-2.5 backdrop-blur">
          <X className="size-6" />
        </button>
        {bereit && !fehler && (
          <button
            onClick={() => setAuto((a) => !a)}
            className="flex items-center gap-1.5 rounded-full bg-black/40 px-3 py-2 text-sm font-medium backdrop-blur"
          >
            {auto ? <Timer className="size-4" /> : <TimerOff className="size-4" />}
            Auto-Auslöser {auto ? 'an' : 'aus'}
          </button>
        )}
      </div>

      <div className="relative mt-auto flex flex-col items-center gap-4 bg-gradient-to-t from-black/80 to-transparent p-6 pb-10">
        {fehler ? (
          <div className="max-w-sm rounded-2xl bg-zinc-900/90 p-5 text-center">
            <Camera className="mx-auto mb-2 size-8 text-zinc-400" />
            <p className="text-sm">{fehler}</p>
            <button
              onClick={onFotoApp}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-zinc-900"
            >
              <ImagePlus className="size-4" /> Foto-App oder Datei verwenden
            </button>
          </div>
        ) : (
          <>
            <div className="rounded-full bg-black/50 px-4 py-1.5 text-sm font-medium backdrop-blur">{hinweis}</div>
            <button onClick={ausloesen} disabled={!bereit} aria-label="Foto aufnehmen" className="relative size-20 disabled:opacity-50">
              <svg viewBox="0 0 84 84" className="absolute inset-0 size-full -rotate-90">
                <circle cx="42" cy="42" r="38" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="5" />
                <circle
                  cx="42"
                  cy="42"
                  r="38"
                  fill="none"
                  stroke="#34d399"
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray={umfang}
                  strokeDashoffset={umfang * (1 - fortschritt)}
                  className="transition-[stroke-dashoffset] duration-100"
                />
              </svg>
              <span className="absolute inset-[10px] rounded-full bg-white transition active:scale-95" />
            </button>
          </>
        )}
      </div>
    </div>,
    document.body,
  )
}
