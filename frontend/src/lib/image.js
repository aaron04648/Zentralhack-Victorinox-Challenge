// Fotos vom Smartphone sind schnell 5–10 MB. Vor dem Upload verkleinern wir sie,
// damit die Analyse auch im Messe-WLAN in wenigen Sekunden durch ist.

function ladeBild(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function zeichne(img, maxSeite) {
  const faktor = Math.min(1, maxSeite / Math.max(img.naturalWidth, img.naturalHeight))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(img.naturalWidth * faktor)
  canvas.height = Math.round(img.naturalHeight * faktor)
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  return canvas
}

/** Liefert { upload: Blob (max. 1600 px), vorschau: dataURL (max. 640 px, für den Röntgenblick) }. */
export async function bereiteFotoVor(datei) {
  const url = URL.createObjectURL(datei)
  try {
    const img = await ladeBild(url)
    const upload = await new Promise((resolve) =>
      zeichne(img, 1600).toBlob(resolve, 'image/jpeg', 0.85),
    )
    const vorschau = zeichne(img, 640).toDataURL('image/jpeg', 0.72)
    return { upload: upload ?? datei, vorschau }
  } finally {
    URL.revokeObjectURL(url)
  }
}

/** Demo-Bild aus /public als File laden, damit es denselben Weg wie ein echtes Foto geht. */
export async function ladeDemoDatei(pfad) {
  const res = await fetch(pfad)
  const blob = await res.blob()
  return new File([blob], pfad.split('/').pop(), { type: blob.type })
}
