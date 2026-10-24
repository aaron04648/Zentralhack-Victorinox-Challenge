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
REGELN = [
    (r"wellenschliff", "klinge_wellenschliff"),
    (r"hakenklinge|waid|käse|gebogen|kabelklinge|blade, pointed|klinge, spitz|klinge, gerade|blade, straight", "klinge_spezial"),
    (r"^klinge, (gross|10,5)", "klinge_gross"),
    (r"^klinge, klein", "klinge_klein"),
    (r"schere", "schere"),
    (r"holzsäge", "holzsaege"),
    (r"metallsäge|metal saw|scheiben|frontscheiben", "metallsaege"),
    (r"metallfeile|metal file", "metallfeile"),
    (r"nagelfeile|glasnagelfeile", "nagelfeile"),
    (r"korkenzieher", "korkenzieher"),
    (r"dosenöffner|can opener", "dosenoeffner"),
    (r"kapselheber|bottle opener", "kapselheber"),
    (r"mini-schraubendreher", "mini_schraubendreher"),
    (r"^bit|innensechskant", "bits"),
    (r"phillips|torx", "schraubendreher_kreuz"),
    (r"schraubendreher|screwdriver", "schraubendreher_flach"),
    (r"ahle|marlspieker|marlin spike", "ahle"),
    (r"zange", "zange"),
    (r"pinzette", "pinzette"),
    (r"zahnstocher", "zahnstocher"),
    (r"kugelschreiber", "kugelschreiber"),
    (r"stecknadel", "stecknadel"),
    (r"lupe", "lupe"),
    (r"^led$", "led"),
    (r"massstab", "massstab"),
    (r"mehrzweckhaken|zughaken", "mehrzweckhaken"),
    (r"fischentschupper|angellöser", "fischentschupper"),
    (r"holzmeissel", "holzmeissel"),
    (r"kistenöffner|paketöffner", "kistenoeffner"),
    (r"nagelknipser|nagelhaut|nagelreiniger", "nagelpflege"),
    (r"trageclip|^clip$", "trageclip"),
    (r"draht|kabel|hülsenpresser|wire", "drahtwerkzeug"),
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
