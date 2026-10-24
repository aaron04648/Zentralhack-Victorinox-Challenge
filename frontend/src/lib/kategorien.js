// Optionaler Hinweis für die Bilderkennung. Die Werte entsprechen exakt der Spalte
// `kategorien` der Produkt-CSV, damit das Backend die Kandidaten darauf eingrenzen kann.
export const KATEGORIEN = [
  {
    wert: '',
    label: 'Automatisch erkennen',
    beschreibung: 'Der Agent bestimmt die Kategorie selbst.',
  },
  {
    wert: 'Everyday',
    label: 'Alltag (Everyday)',
    beschreibung: 'Kompakte Messer für die Hosentasche, z. B. Classic SD, Spartan, Climber.',
  },
  {
    wert: 'Outdoor & Sports',
    label: 'Outdoor & Sport',
    beschreibung: 'Grössere Messer, oft mit Säge oder Feststellklinge, z. B. Huntsman, Ranger Grip, Hunter Pro.',
  },
  {
    wert: 'Trades & Crafts',
    label: 'Handwerk & Garten',
    beschreibung: 'Werkzeugreiche Modelle und Gartenmesser, z. B. Swiss Champ, Handyman, Okuliermesser.',
  },
]

export function kategorieLabel(wert) {
  return KATEGORIEN.find((k) => k.wert === wert)?.label ?? wert
}
