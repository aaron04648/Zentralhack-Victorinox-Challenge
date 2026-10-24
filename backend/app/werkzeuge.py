"""Grobe, auf Fotos erkennbare Werkzeuggruppen.

Die Victorinox-Daten nennen Werkzeuge sehr fein ("Schraubendreher 3 mm",
"Phillips-Schraubendreher 0/1, magnetisch"). Auf einem Foto ist das nicht
unterscheidbar, und andere Marken benennen dieselben Werkzeuge anders. Für die
Bilderkennung und das Matching wird deshalb jedes Werkzeug auf eine Gruppe
abgebildet. Werkzeuge ohne passende Gruppe (z. B. "Ring", "Kartenschutzhülle")
werden beim Matching ignoriert.
"""

import re

# key -> (Anzeigename, Beschreibung für das Vision-Modell)
GRUPPEN = {
    "klinge_gross": ("Klinge, gross", "Hauptklinge, längste Klinge des Messers, glatter Schliff"),
    "klinge_klein": ("Klinge, klein", "zweite, deutlich kürzere Klinge"),
    "klinge_wellenschliff": ("Klinge mit Wellenschliff", "Klinge mit gezahnter/gewellter Schneide"),
    "klinge_spezial": ("Spezialklinge", "Haken-, Waid-, Käse-, gebogene oder Kabelklinge"),
    "schere": ("Schere", "kleine Schere mit Feder"),
    "holzsaege": ("Holzsäge", "Säge mit grossen, groben Zähnen"),
    "metallsaege": ("Metallsäge", "Säge mit sehr feinen Zähnen, oft kombiniert mit Metallfeile"),
    "metallfeile": ("Metallfeile", "geriffelte Feile, oft Rückseite der Metallsäge"),
    "nagelfeile": ("Nagelfeile", "schmale Feile mit Nagelreiniger an der Spitze"),
    "korkenzieher": ("Korkenzieher", "spiralförmiger Korkenzieher"),
    "dosenoeffner": ("Dosenöffner", "hakenförmiger Dosenöffner, meist mit kleinem Schraubendreher an der Spitze"),
    "kapselheber": ("Kapselheber", "Flaschenöffner, meist mit Schraubendreher und Drahtabisolierer"),
    "schraubendreher_flach": ("Schraubendreher (flach)", "Schlitzschraubendreher, eigenständig oder an einem anderen Werkzeug"),
    "schraubendreher_kreuz": ("Kreuzschraubendreher", "Phillips-/Kreuzschlitz-Schraubendreher"),
    "mini_schraubendreher": ("Mini-Schraubendreher", "winziger Schraubendreher, meist im Korkenzieher eingesteckt"),
    "ahle": ("Ahle", "spitze Stech-/Reib-Ahle, evtl. mit Nähöhr"),
    "zange": ("Zange", "Kombi- oder Spitzzange, meist mit Drahtschneider"),
    "pinzette": ("Pinzette", "kleine Pinzette, steckt in der Schale"),
    "zahnstocher": ("Zahnstocher", "Zahnstocher aus Kunststoff, steckt in der Schale"),
    "kugelschreiber": ("Kugelschreiber", "ausziehbarer/Druck-Kugelschreiber"),
    "stecknadel": ("Stecknadel", "Stecknadel in der Schale"),
    "lupe": ("Lupe", "kleine Vergrösserungslinse"),
    "led": ("LED-Lampe", "eingebaute LED-Taschenlampe"),
    "massstab": ("Massstab", "Skala in cm oder Zoll auf Klinge oder Schale"),
    "mehrzweckhaken": ("Mehrzweckhaken", "Haken zum Tragen von Paketen"),
    "fischentschupper": ("Fischentschupper", "gezahnter Entschupper mit Hakenlöser und Massstab"),
    "holzmeissel": ("Holzmeissel", "Meissel/Schaber für Holz"),
    "kistenoeffner": ("Kistenöffner", "Hebel zum Öffnen von Kisten, Paketöffner"),
    "bits": ("Bit-Halter", "Halter oder Satz austauschbarer Bits"),
    "nagelpflege": ("Nagelknipser/-pflege", "Nagelknipser, Nagelhautschieber, Nagelreiniger als eigenes Teil"),
    "trageclip": ("Trageclip", "Clip zum Befestigen an Tasche oder Gürtel"),
    "drahtwerkzeug": ("Draht-/Kabelwerkzeug", "Drahtabisolierer, -schaber, -bieger, Kabelschneider, Hülsenpresser"),
}

# Reihenfolge ist wichtig: der erste passende Ausdruck gewinnt.
# Deutsch (Webseite, Leatherman) und Englisch (Victorinox-Katalog 2026, SWIZA, Gerber) nebeneinander;
# geprüft an den Messern, die im Katalog und auf der Webseite stehen (gleiche Gruppen in beiden Sprachen).
REGELN = [
    (r"wellenschliff|wavy edge|^blade.*serrat", "klinge_wellenschliff"),
    (r"hakenklinge|waid|käse|gebogen|kabelklinge|blade, pointed|klinge, spitz|klinge, gerade|blade, straight"
     r"|pruning blade|gutting blade|electrician|cheese blade", "klinge_spezial"),
    (r"^klinge, (gross|10,5)|^blade[.,] (large|10\.5)", "klinge_gross"),
    (r"^klinge, klein|^blade, small", "klinge_klein"),
    (r"^blade\b", "klinge_gross"),                      # SWIZA: "Blade, 75mm", "Blade for one hand"
    (r"schere|scissors", "schere"),
    (r"holzsäge|wood saw", "holzsaege"),
    (r"metallsäge|metal saw|scheiben|frontscheiben|glass saw", "metallsaege"),
    (r"metallfeile|metal file", "metallfeile"),
    (r"nagelfeile|glasnagelfeile|nail file", "nagelfeile"),
    (r"korkenzieher|corkscrew", "korkenzieher"),
    (r"dosenöffner|can opener", "dosenoeffner"),
    (r"kapselheber|bottle opener", "kapselheber"),
    (r"mini-schraubendreher|mini screwdriver", "mini_schraubendreher"),
    (r"^bit|innensechskant|hex drive", "bits"),
    (r"phillips|torx", "schraubendreher_kreuz"),
    (r"schraubendreher|screwdriver", "schraubendreher_flach"),
    (r"ahle|marlspieker|marlin spike|reamer|\bawl\b", "ahle"),
    (r"zange|pliers", "zange"),
    (r"pinzette|tweezers", "pinzette"),
    (r"zahnstocher|toothpick", "zahnstocher"),
    (r"kugelschreiber|ballpoint pen", "kugelschreiber"),
    (r"stecknadel|^pin$", "stecknadel"),
    (r"lupe|magnifying glass", "lupe"),
    (r"^led$", "led"),
    (r"massstab|ruler", "massstab"),
    (r"mehrzweckhaken|zughaken|multipurpose hook|pulling hook", "mehrzweckhaken"),
    (r"fischentschupper|angellöser|fish scaler|hook disgorger", "fischentschupper"),
    (r"holzmeissel|chisel", "holzmeissel"),
    (r"kistenöffner|paketöffner|crate opener|box opener", "kistenoeffner"),
    (r"nagelknipser|nagelhaut|nagelreiniger|nail clipper|cuticle|nail cleaner", "nagelpflege"),
    (r"trageclip|^clip$|carry clip", "trageclip"),
    (r"draht|kabel|hülsenpresser|wire|cable|cap crimper", "drahtwerkzeug"),
]
_REGELN = [(re.compile(muster, re.I), key) for muster, key in REGELN]


def gruppe(werkzeug):
    """Gruppe eines einzelnen Werkzeugs oder None."""
    name = werkzeug.replace("\xa0", " ").strip()
    for muster, key in _REGELN:
        if muster.search(name):
            return key
    return None


def gruppen(werkzeuge):
    """Gruppen-Set aus einer Liste von Werkzeugen. Kombi-Einträge "A | B" werden aufgetrennt."""
    result = set()
    for eintrag in werkzeuge:
        for teil in eintrag.split("|"):
            key = gruppe(teil)
            if key:
                result.add(key)
    return result


def label(key):
    return GRUPPEN[key][0]
