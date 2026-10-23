import { useRef } from 'react'
import { Camera, ImagePlus } from 'lucide-react'
import { Button } from './ui.jsx'

/**
 * Zwei Wege zum Foto: Kamera (öffnet am Handy direkt die Rückkamera) und Galerie/Datei.
 * `kompakt` = zwei Buttons nebeneinander, sonst die grosse Variante für die Startseite.
 */
export default function FotoAufnahme({ onDatei, kompakt = false, deaktiviert = false }) {
  const kamera = useRef(null)
  const galerie = useRef(null)

  function gewaehlt(event) {
    const datei = event.target.files?.[0]
    event.target.value = ''
    if (datei) onDatei(datei)
  }

  const inputs = (
    <>
      <input ref={kamera} type="file" accept="image/*" capture="environment" hidden onChange={gewaehlt} />
      <input ref={galerie} type="file" accept="image/*" hidden onChange={gewaehlt} />
    </>
  )

  if (kompakt) {
    return (
      <div className="flex gap-2">
        {inputs}
        <Button icon={Camera} disabled={deaktiviert} onClick={() => kamera.current.click()}>
          Neues Foto
        </Button>
        <Button variante="sekundaer" icon={ImagePlus} disabled={deaktiviert} onClick={() => galerie.current.click()}>
          Hochladen
        </Button>
      </div>
    )
  }

  return (
    <div
      className="grid gap-3"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault()
        const datei = e.dataTransfer.files?.[0]
        if (datei?.type.startsWith('image/')) onDatei(datei)
      }}
    >
      {inputs}
      <button
        disabled={deaktiviert}
        onClick={() => kamera.current.click()}
        className="group relative flex flex-col items-center justify-center gap-3 overflow-hidden rounded-3xl bg-brand px-6 py-10 text-white shadow-lg shadow-brand/25 transition active:scale-[0.99] disabled:opacity-60"
      >
        <span className="pointer-events-none absolute inset-4 rounded-2xl border border-white/25" />
        {/* Sucher-Ecken wie in der Kamera-Ansicht aus dem Einführungs-Deck */}
        {['left-6 top-6 border-l-2 border-t-2', 'right-6 top-6 border-r-2 border-t-2', 'left-6 bottom-6 border-l-2 border-b-2', 'right-6 bottom-6 border-r-2 border-b-2'].map((pos) => (
          <span key={pos} className={`pointer-events-none absolute size-6 rounded-[3px] border-white ${pos}`} />
        ))}
        <span className="flex size-16 items-center justify-center rounded-full bg-white/15 ring-8 ring-white/10 transition group-hover:scale-105">
          <Camera className="size-8" />
        </span>
        <span className="text-lg font-semibold">Foto aufnehmen</span>
        <span className="text-sm text-white/80">Messer möglichst aufgeklappt, auf ruhigem Hintergrund</span>
      </button>
      <button
        disabled={deaktiviert}
        onClick={() => galerie.current.click()}
        className="flex items-center justify-center gap-2 rounded-2xl border border-dashed border-zinc-300 bg-white px-4 py-4 text-sm font-medium text-zinc-700 transition hover:border-zinc-400 hover:bg-zinc-50 disabled:opacity-60"
      >
        <ImagePlus className="size-5 text-zinc-500" />
        Bild hochladen <span className="hidden text-zinc-400 sm:inline">oder hierher ziehen</span>
      </button>
    </div>
  )
}
