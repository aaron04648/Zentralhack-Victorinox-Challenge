import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ChevronLeft, ExternalLink, LoaderCircle } from 'lucide-react'
import * as api from '../api/client.js'
import { Badge, Karte, ProduktBild, StatusBadge } from '../components/ui.jsx'
import { chf } from '../lib/format.js'

function Zeile({ label, children }) {
  return (
    <div className="grid grid-cols-[130px_1fr] gap-3 px-4 py-3 text-sm">
      <div className="text-zinc-500">{label}</div>
      <div className="min-w-0 font-medium">{children || <span className="text-zinc-300">—</span>}</div>
    </div>
  )
}

export default function ProductPage() {
  const { artikelnummer } = useParams()
  const navigate = useNavigate()
  const [produkt, setProdukt] = useState(null)
  const [fehler, setFehler] = useState(null)

  useEffect(() => {
    let aktuell = true
    setProdukt(null)
    setFehler(null)
    api
      .produkt(artikelnummer)
      .then((p) => aktuell && setProdukt(p))
      .catch((e) => aktuell && setFehler(e.message))
    return () => {
      aktuell = false
    }
  }, [artikelnummer])

  return (
    <div>
      <button onClick={() => navigate(-1)} className="mb-3 inline-flex items-center gap-1 text-sm font-medium text-zinc-600 hover:text-zinc-900">
        <ChevronLeft className="size-4" /> Zurück
      </button>

      {fehler && <Karte className="p-8 text-center text-sm text-zinc-500">{fehler}</Karte>}
      {!produkt && !fehler && <LoaderCircle className="mx-auto mt-16 size-6 animate-spin text-zinc-400" />}

      {produkt && (
        <div className="grid gap-4 sm:grid-cols-[1fr_1.2fr]">
          <Karte className="p-4">
            <ProduktBild url={produkt.bild_url} alt={produkt.name} breite={800} className="aspect-square" />
          </Karte>

          <div>
            <div className="flex flex-wrap gap-1.5">
              {produkt.kategorien?.map((k) => <Badge key={k}>{k}</Badge>)}
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight">{produkt.name}</h1>
            <div className="mt-1 text-sm text-zinc-500">Art.-Nr. {produkt.artikelnummer}</div>
            <div className="mt-3 flex items-center gap-3">
              <span className="text-xl font-semibold">{chf(produkt.preis_chf)}</span>
              <StatusBadge status={produkt.lagerstatus} />
            </div>

            <Karte className="mt-4 divide-y divide-zinc-100">
              <Zeile label="Shop-Kategorie">{produkt.shop_kategorie}</Zeile>
              <Zeile label="Unterkategorien">{produkt.unterkategorien?.join(', ')}</Zeile>
              <Zeile label="Farben">
                {produkt.farben?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {produkt.farben.map((f) => <Badge key={f}>{f}</Badge>)}
                  </div>
                )}
              </Zeile>
              <Zeile label={`Varianten (${produkt.varianten_artikelnummern?.length ?? 0})`}>
                <span className="font-mono text-xs leading-relaxed text-zinc-600">{produkt.varianten_artikelnummern?.join(' · ')}</span>
              </Zeile>
            </Karte>
            <p className="mt-2 px-1 text-[11px] text-zinc-400">Quelle: Victorinox-Produktdaten (victorinox.com, de-CH)</p>

            {produkt.url && (
              <a
                href={produkt.url}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand hover:underline"
              >
                Auf victorinox.com ansehen <ExternalLink className="size-4" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
