import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle2, Loader2, Monitor, Smartphone } from 'lucide-react'
import FotoAufnahme from '../components/FotoAufnahme.jsx'
import { Karte } from '../components/ui.jsx'
import * as api from '../api/client.js'
import { bereiteFotoVor } from '../lib/image.js'

/**
 * Handy-Seite der Kopplung (/handy/:sitzungId, geöffnet über den QR-Code am Computer):
 * Foto aufnehmen, verkleinern, an den Computer schicken. Analysiert wird auf dem Computer.
 */
export default function HandyPage() {
  const { sitzungId } = useParams()
  const [status, setStatus] = useState('verbinden') // verbinden | bereit | sendet | gesendet | fehler
  const [fehler, setFehler] = useState(null)
  const [vorschau, setVorschau] = useState(null)
  const [anzahl, setAnzahl] = useState(0)

  useEffect(() => {
    api
      .handyVerbunden(sitzungId)
      .then(() => setStatus('bereit'))
      .catch((e) => {
        setFehler(e.message)
        setStatus('fehler')
      })
  }, [sitzungId])

  async function senden(datei) {
    setStatus('sendet')
    setFehler(null)
    try {
      const { upload, vorschau } = await bereiteFotoVor(datei)
      setVorschau(vorschau)
      await api.handyFotoSenden(sitzungId, upload)
      setAnzahl((n) => n + 1)
      setStatus('gesendet')
    } catch (e) {
      setFehler(`Senden fehlgeschlagen (${e.message})`)
      setStatus('bereit')
    }
  }

  return (
    <div className="mx-auto max-w-md pt-2">
      <div className="mb-5 text-center">
        <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-brand/10 text-brand">
          <Smartphone className="size-6" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Handy als Kamera</h1>
        <p className="mt-1 text-sm text-zinc-600">Das Foto wird an den Computer geschickt und dort analysiert.</p>
      </div>

      {status === 'verbinden' && (
        <div className="flex justify-center py-10">
          <Loader2 className="size-8 animate-spin text-zinc-300" />
        </div>
      )}

      {status === 'fehler' && (
        <Karte className="p-5 text-center text-sm">
          <p className="font-medium text-brand">{fehler}</p>
          <p className="mt-1 text-zinc-500">Bitte am Computer erneut „Mit Handy scannen“ wählen und den neuen QR-Code scannen.</p>
        </Karte>
      )}

      {status === 'sendet' && (
        <Karte className="overflow-hidden">
          {vorschau && <img src={vorschau} alt="Dein Foto" className="aspect-[4/3] w-full bg-zinc-100 object-contain" />}
          <div className="flex items-center justify-center gap-2 p-4 text-sm text-zinc-600">
            <Loader2 className="size-4 animate-spin" /> Wird an den Computer geschickt …
          </div>
        </Karte>
      )}

      {status === 'gesendet' && (
        <Karte className="overflow-hidden">
          {vorschau && <img src={vorschau} alt="Dein Foto" className="aspect-[4/3] w-full bg-zinc-100 object-contain" />}
          <div className="space-y-4 p-4">
            <div className="flex items-start gap-2.5">
              <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-600" />
              <div>
                <div className="font-semibold">Foto gesendet{anzahl > 1 ? ` (${anzahl})` : ''}</div>
                <div className="flex items-center gap-1 text-sm text-zinc-500">
                  <Monitor className="size-3.5" /> Das Ergebnis erscheint auf dem Computer.
                </div>
              </div>
            </div>
            <FotoAufnahme kompakt ohneHandy onDatei={senden} />
          </div>
        </Karte>
      )}

      {status === 'bereit' && (
        <>
          <FotoAufnahme ohneHandy onDatei={senden} />
          {fehler && <p className="mt-3 text-center text-sm text-brand">{fehler}</p>}
        </>
      )}
    </div>
  )
}
