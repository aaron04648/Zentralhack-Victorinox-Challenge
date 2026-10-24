import { chf } from '../lib/format.js'

const zahl = (wert, einheit) => (wert == null ? null : `${new Intl.NumberFormat('de-CH').format(wert)} ${einheit}`)
const janein = (wert) => (wert == null ? null : wert ? 'Ja' : 'Nein')

function masse(p) {
  const teile = [p.laenge_mm, p.breite_mm, p.hoehe_mm]
  if (teile.every((t) => t != null)) return `${teile.join(' × ')} mm`
  return zahl(p.laenge_mm, 'mm lang')
}

/** Alle Katalogdaten eines Produkts als Liste; leere Felder werden ausgelassen. */
export default function ProduktDaten({ produkt }) {
  const zeilen = [
    ['Preis', chf(produkt.preis_chf)],
    ['Masse', masse(produkt)],
    ['Gewicht', zahl(produkt.gewicht_g, 'g')],
    ['Schale', produkt.material],
    ['Feststellbare Klinge', janein(produkt.feststellbar)],
    ['Einhandklinge', janein(produkt.einhandklinge)],
    ['Funktionen', produkt.anzahl_funktionen ?? produkt.anzahl_werkzeuge],
    ['Kategorien', produkt.kategorien?.join(', ')],
    ['Shop-Kategorie', produkt.shop_kategorie],
    ['Farben', produkt.farben?.join(', ')],
    ['Varianten', produkt.varianten_artikelnummern?.join(', ')],
  ].filter(([, wert]) => wert != null && wert !== '' && wert !== '—')

  return (
    <div>
      <dl className="grid gap-x-6 sm:grid-cols-2">
        {zeilen.map(([label, wert]) => (
          <div key={label} className="flex justify-between gap-3 border-b border-zinc-100 py-2 text-sm">
            <dt className="shrink-0 text-zinc-500">{label}</dt>
            <dd className="min-w-0 text-right font-medium">{wert}</dd>
          </div>
        ))}
      </dl>
      {produkt.werkzeuge?.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-sm text-zinc-500">Werkzeuge ({produkt.werkzeuge.length})</div>
          <ul className="flex flex-wrap gap-1.5">
            {produkt.werkzeuge.map((w, i) => (
              <li key={`${w}-${i}`} className="rounded-lg bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-700">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
