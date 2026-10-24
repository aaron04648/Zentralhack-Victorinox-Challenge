import { useState } from 'react'

const SICHER = 0.5 // gleiche Grenze wie die Werkzeug-Chips
const SCHRIFT = 1.7 // Schriftgrösse relativ zum Markerradius

const istSicher = (w) => w.wahrscheinlichkeit == null || w.wahrscheinlichkeit >= SICHER
const ueberlappt = (a, b) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1

/**
 * Wo die Beschriftungen hinkommen: sicherste zuerst, bevorzugt rechts vom Marker (links am rechten Rand).
 * Überlappt der Text ein schon platziertes Label oder einen sicheren Marker, wird die andere Seite versucht,
 * sonst bleibt der Marker unbeschriftet (Label erscheint beim Hover).
 * @returns Map gruppe -> "rechts" | "links"
 */
function platziereLabels(werkzeuge, b, h, r) {
  const schrift = r * SCHRIFT
  // Nur sichere Marker freihalten; unsichere (gestrichelt) dürfen von einem Label verdeckt werden
  const marker = werkzeuge.filter(istSicher).map((w) => {
    const x = w.position.x * b
    const y = w.position.y * h
    return { x0: x - r, x1: x + r, y0: y - r, y1: y + r, gruppe: w.gruppe }
  })
  const belegt = []
  const seiten = new Map()
  for (const w of [...werkzeuge].sort((a, c) => (c.wahrscheinlichkeit ?? 1) - (a.wahrscheinlichkeit ?? 1))) {
    const x = w.position.x * b
    const y = w.position.y * h
    const breite = (w.label.length + 1) * schrift * 0.56
    const box = (seite) => {
      const start = seite === 'rechts' ? x + r * 1.8 : x - r * 1.8 - breite
      return { x0: start, x1: start + breite, y0: y - schrift * 0.6, y1: y + schrift * 0.6 }
    }
    const reihenfolge = w.position.x < 0.6 ? ['rechts', 'links'] : ['links', 'rechts']
    const seite = reihenfolge.find((s) => {
      const k = box(s)
      return (
        k.x0 >= 0 && k.x1 <= b &&
        !belegt.some((a) => ueberlappt(a, k)) &&
        !marker.some((m) => m.gruppe !== w.gruppe && ueberlappt(m, k))
      )
    })
    if (seite) {
      seiten.set(w.gruppe, seite)
      belegt.push(box(seite))
    }
  }
  return seiten
}

/**
 * Röntgenblick: Foto mit Markern, wo das Modell die Werkzeuge sieht.
 * Das SVG liegt über dem Bild und skaliert mit preserveAspectRatio="meet" exakt wie object-contain,
 * darum passen die relativen Positionen (0..1) aus dem Backend bei jeder Bildgrösse.
 *
 * @param werkzeuge  [{ gruppe, label, wahrscheinlichkeit, position: { x, y } | null }]
 * @param hervorgehoben  gruppe, die gerade hervorgehoben ist (Hover auf Chip oder Marker)
 */
export default function RoentgenBild({ src, werkzeuge = [], hervorgehoben, onHervorheben, className = '' }) {
  const [groesse, setGroesse] = useState(null)
  const mitOrt = (werkzeuge ?? []).filter((w) => w.position)
  // Markerradius relativ zur Bildgrösse
  const r = groesse ? Math.max(groesse.b, groesse.h) * 0.018 : 0
  const seiten = groesse ? platziereLabels(mitOrt, groesse.b, groesse.h, r) : new Map()

  return (
    <div className={`relative ${className}`}>
      <img
        src={src}
        alt="Dein Foto"
        onLoad={(e) => setGroesse({ b: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
        className="size-full object-contain"
      />
      {groesse && mitOrt.length > 0 && (
        <svg
          viewBox={`0 0 ${groesse.b} ${groesse.h}`}
          preserveAspectRatio="xMidYMid meet"
          className="pointer-events-none absolute inset-0 size-full"
        >
          {mitOrt.map((w, i) => {
            const x = w.position.x * groesse.b
            const y = w.position.y * groesse.h
            const sicher = istSicher(w)
            const aktiv = hervorgehoben === w.gruppe
            return (
              <g
                key={w.gruppe}
                className="roentgen-marker pointer-events-auto cursor-pointer"
                style={{ animationDelay: `${i * 90}ms` }}
                onMouseEnter={() => onHervorheben?.(w.gruppe)}
                onMouseLeave={() => onHervorheben?.(null)}
              >
                <circle cx={x} cy={y} r={r * 2.2} className="roentgen-puls" fill={sicher ? '#e30613' : '#71717a'} opacity="0.25" />
                <circle
                  cx={x}
                  cy={y}
                  r={aktiv ? r * 1.25 : r}
                  fill={sicher ? '#e30613' : 'white'}
                  stroke={sicher ? 'white' : '#71717a'}
                  strokeWidth={r * 0.35}
                  strokeDasharray={sicher ? undefined : `${r * 0.5} ${r * 0.35}`}
                />
              </g>
            )
          })}
          {/* Beschriftungen als eigene Ebene über allen Markern */}
          {mitOrt.map((w, i) => {
            const aktiv = hervorgehoben === w.gruppe
            if (!aktiv && !seiten.has(w.gruppe)) return null
            const x = w.position.x * groesse.b
            const y = w.position.y * groesse.h
            const sicher = istSicher(w)
            const rechts = (seiten.get(w.gruppe) ?? (w.position.x < 0.6 ? 'rechts' : 'links')) === 'rechts'
            return (
              <text
                key={w.gruppe}
                className="roentgen-marker"
                style={{ animationDelay: `${i * 90}ms` }}
                x={x + (rechts ? r * 1.8 : -r * 1.8)}
                y={y + r * 0.6}
                textAnchor={rechts ? 'start' : 'end'}
                fontSize={r * (aktiv ? 2.1 : SCHRIFT)}
                fontWeight={aktiv ? 700 : 600}
                fill={sicher ? '#18181b' : '#52525b'}
                stroke="white"
                strokeWidth={r * 0.55}
                paintOrder="stroke"
              >
                {w.label}
                {sicher ? '' : '?'}
              </text>
            )
          })}
        </svg>
      )}
    </div>
  )
}
