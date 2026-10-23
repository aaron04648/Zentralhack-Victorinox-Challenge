// Victorinox-Bilder kommen über ImageEngine; dort lassen sie sich per URL skalieren
// (das Original ist ein ~500 KB PNG).
export function bild(url, breite = 400) {
  if (!url) return ''
  if (!url.includes('imageengine.victorinox.com')) return url
  return `${url}?imgeng=/w_${breite}/f_webp`
}

export function chf(preis) {
  if (preis == null) return '—'
  return new Intl.NumberFormat('de-CH', { style: 'currency', currency: 'CHF' }).format(preis)
}

export function prozent(wert) {
  if (wert == null) return '—'
  return `${Math.round(wert * 100)}%`
}

const LAGERSTATUS = {
  inStock: { label: 'An Lager', ton: 'ok' },
  outOfStock: { label: 'Nicht verfügbar', ton: 'warn' },
}

export function lagerstatus(status) {
  return LAGERSTATUS[status] ?? { label: 'Status unbekannt', ton: 'neutral' }
}

// Ab hier gilt eine Erkennung als unsicher: Kandidaten zeigen und nachfragen.
export const KONFIDENZ_SCHWELLE = 0.6

export function konfidenzTon(wert) {
  if (wert >= 0.8) return 'ok'
  if (wert >= KONFIDENZ_SCHWELLE) return 'neutral'
  return 'warn'
}
