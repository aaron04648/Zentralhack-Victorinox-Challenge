// Werkzeuggruppen des Backends (backend/app/werkzeuge.py, GET /api/werkzeuge), für Vorschläge beim
// Hinzufügen. Generiert aus GRUPPEN; die Keys (gruppe) müssen mit dem Backend übereinstimmen.
export const WERKZEUGE = [
  { gruppe: "klinge_gross", label: "Klinge, gross", beschreibung: "Hauptklinge, längste Klinge des Messers, glatter Schliff" },
  { gruppe: "klinge_klein", label: "Klinge, klein", beschreibung: "zweite, deutlich kürzere Klinge" },
  { gruppe: "klinge_wellenschliff", label: "Klinge mit Wellenschliff", beschreibung: "Klinge mit gezahnter/gewellter Schneide" },
  { gruppe: "klinge_spezial", label: "Spezialklinge", beschreibung: "Haken-, Waid-, Käse-, gebogene oder Kabelklinge" },
  { gruppe: "schere", label: "Schere", beschreibung: "kleine Schere mit Feder" },
  { gruppe: "holzsaege", label: "Holzsäge", beschreibung: "Säge mit grossen, groben Zähnen" },
  { gruppe: "metallsaege", label: "Metallsäge", beschreibung: "Säge mit sehr feinen Zähnen, oft kombiniert mit Metallfeile" },
  { gruppe: "metallfeile", label: "Metallfeile", beschreibung: "geriffelte Feile, oft Rückseite der Metallsäge" },
  { gruppe: "nagelfeile", label: "Nagelfeile", beschreibung: "schmale Feile mit Nagelreiniger an der Spitze" },
  { gruppe: "korkenzieher", label: "Korkenzieher", beschreibung: "spiralförmiger Korkenzieher" },
  { gruppe: "dosenoeffner", label: "Dosenöffner", beschreibung: "hakenförmiger Dosenöffner, meist mit kleinem Schraubendreher an der Spitze" },
  { gruppe: "kapselheber", label: "Kapselheber", beschreibung: "Flaschenöffner, meist mit Schraubendreher und Drahtabisolierer" },
  { gruppe: "schraubendreher_flach", label: "Schraubendreher (flach)", beschreibung: "Schlitzschraubendreher, eigenständig oder an einem anderen Werkzeug" },
  { gruppe: "schraubendreher_kreuz", label: "Kreuzschraubendreher", beschreibung: "Phillips-/Kreuzschlitz-Schraubendreher" },
  { gruppe: "mini_schraubendreher", label: "Mini-Schraubendreher", beschreibung: "winziger Schraubendreher, meist im Korkenzieher eingesteckt" },
  { gruppe: "ahle", label: "Ahle", beschreibung: "spitze Stech-/Reib-Ahle, evtl. mit Nähöhr" },
  { gruppe: "zange", label: "Zange", beschreibung: "Kombi- oder Spitzzange, meist mit Drahtschneider" },
  { gruppe: "pinzette", label: "Pinzette", beschreibung: "kleine Pinzette, steckt in der Schale" },
  { gruppe: "zahnstocher", label: "Zahnstocher", beschreibung: "Zahnstocher aus Kunststoff, steckt in der Schale" },
  { gruppe: "kugelschreiber", label: "Kugelschreiber", beschreibung: "ausziehbarer/Druck-Kugelschreiber" },
  { gruppe: "stecknadel", label: "Stecknadel", beschreibung: "Stecknadel in der Schale" },
  { gruppe: "lupe", label: "Lupe", beschreibung: "kleine Vergrösserungslinse" },
  { gruppe: "led", label: "LED-Lampe", beschreibung: "eingebaute LED-Taschenlampe" },
  { gruppe: "massstab", label: "Massstab", beschreibung: "Skala in cm oder Zoll auf Klinge oder Schale" },
  { gruppe: "mehrzweckhaken", label: "Mehrzweckhaken", beschreibung: "Haken zum Tragen von Paketen" },
  { gruppe: "fischentschupper", label: "Fischentschupper", beschreibung: "gezahnter Entschupper mit Hakenlöser und Massstab" },
  { gruppe: "holzmeissel", label: "Holzmeissel", beschreibung: "Meissel/Schaber für Holz" },
  { gruppe: "kistenoeffner", label: "Kistenöffner", beschreibung: "Hebel zum Öffnen von Kisten, Paketöffner" },
  { gruppe: "bits", label: "Bit-Halter", beschreibung: "Halter oder Satz austauschbarer Bits" },
  { gruppe: "nagelpflege", label: "Nagelknipser/-pflege", beschreibung: "Nagelknipser, Nagelhautschieber, Nagelreiniger als eigenes Teil" },
  { gruppe: "trageclip", label: "Trageclip", beschreibung: "Clip zum Befestigen an Tasche oder Gürtel" },
  { gruppe: "drahtwerkzeug", label: "Draht-/Kabelwerkzeug", beschreibung: "Drahtabisolierer, -schaber, -bieger, Kabelschneider, Hülsenpresser" },
]

// Werden beim Hinzufügen zuerst vorgeschlagen (häufig gesuchte, gut sichtbare Werkzeuge)
export const BELIEBT = ['schere', 'korkenzieher', 'holzsaege', 'zange', 'schraubendreher_kreuz', 'lupe', 'led', 'klinge_wellenschliff']

export const WERKZEUG_LABEL = Object.fromEntries(WERKZEUGE.map((w) => [w.gruppe, w.label]))
