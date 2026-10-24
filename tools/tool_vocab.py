"""Tool vocabulary: map the catalogue's German tool names to English.

`backend/data/victorinox_sak_werkzeuge.csv` stores tool names in German
(`Klinge, gross`, `Korkenzieher`, `Schere`, ...). The decision model is
English-centric, so we need a mapping to build English criteria and to compare
detected features against catalogue tool sets.

The mapping below is derived from the 147 distinct values in the scrape. A few
catalogue entries are already English (`Blade, straight`, `Bottle opener`,
`Metal saw`); those pass through unchanged.

Usage:
    from tools.tool_vocab import TOOL_EN, canonical_tool, tool_set_for, EN_OPTIONS

    canonical_tool("Klinge, gross")   # -> "large_blade"
    tool_set_for("1.3603")           # -> {"large_blade", "small_blade", ...}
"""

from __future__ import annotations

import csv
import functools
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WERKZEUGE_CSV = REPO / "backend" / "data" / "victorinox_sak_werkzeuge.csv"
PRODUKTE_CSV = REPO / "backend" / "data" / "victorinox_sak_produkte.csv"

# Canonical tool id -> English description, used as the `criteria` for a
# `choice` question. Keep this list to tools that are actually recognisable in
# a photograph - a criterion for an invisible tool only adds noise.
TOOL_EN: dict[str, str] = {
    "large_blade": "a large folding blade",
    "small_blade": "a small folding blade",
    "scissors": "scissors",
    "corkscrew": "a corkscrew (spiral screw)",
    "saw": "a saw with teeth",
    "screwdriver": "a flat screwdriver",
    "bottle_opener": "a bottle opener",
    "can_opener": "a can opener",
    "tweezers": "tweezers",
    "toothpick": "a toothpick",
    "pen": "a ballpoint pen",
    "nail_file": "a nail file",
    "wire_cutter": "a wire cutter or wire stripper",
    "awl": "an awl (a pointed piercing tool)",
    "cap_lifter": "a bottle cap lifter",
    "ring": "a key ring",
    "pliers": "pliers",
    "magnifier": "a magnifying glass",
    "hooked_blade": "a hooked cutting blade",
    "strap_cutter": "a strap cutter",
    "wire_bender": "a wire bending tool",
    "chisel": "a wood chisel",
    "fish_scaler": "a fish scaler",
    "scraper": "a scraper",
    "firesteel": "a fire steel striker",
    "bottle_cork": "a corkscrew for wine corks",
    "letter_opener": "a letter opener",
    "attachment_eye": "an attachment eye",
    "thumb_stud": "a removable thumb stud",
    "multi_hook": "a multi-purpose hook",
    "ruler": "a ruler (cm or inch)",
    "money_clip": "a money clip",
    "fork": "a fork",
    "cheese_knife": "a cheese knife",
    "cable_knife": "a cable knife",
    "nail_cleaner": "a nail cleaner",
    "nail_clipper": "a nail clipper",
    "crimp_tool": "a crimping tool",
    "punch": "a hole punch",
    "ballpoint_pen": "a ballpoint pen",
    "cord": "a cord",
    "led": "an LED light",
    "peeler": "a citrus peeler",
    "spanner": "a spanner",
    "hex_key": "a hex key",
    "bit_holder": "a bit holder",
    "bit_key": "a bit key",
    "hex_bit": "a hex bit",
    "phillips_bit": "a Phillips bit",
    "torx_bit": "a Torx bit",
    "pouch": "a protective pouch",
    "paracord": "a paracord strap",
    "spatula": "a spatula",
    "repair_tool": "a repair tool",
    "support": "a support stand",
    "clip": "a pocket clip",
    "extended_blade": "an extended blade",
    "bark_lifter": "a bark lifter",
    "banknote": "a banknote gripper",
    "hook_remover": "a fish hook remover",
    "sim_pin": "a SIM card ejector pin",
    "glass_breaker": "a glass breaker",
    "watch_opener": "a watch case opener",
    "hoof_pick": "a hoof pick",
}

# German catalogue name -> canonical tool id. Catalogue entries that bundle
# several tools ("Dosenöffner | Schraubendreher 3 mm") are split on " | ".
TOOL_DE: dict[str, str] = {
    "Klinge, gross": "large_blade",
    "Klinge, klein": "small_blade",
    "Klinge, gebogen": "large_blade",
    "Klinge, gerade": "large_blade",
    "Klinge, spitz": "large_blade",
    "Klinge, gross ohne Spitz": "large_blade",
    "Klinge, gross mit Wellenschliff": "large_blade",
    "Schere": "scissors",
    "Schere mit Mikrozahnung": "scissors",
    "Korkenzieher": "corkscrew",
    "Kupplung für Korkenzieher": "bottle_cork",
    "Holzsäge": "saw",
    "Metallsäge": "saw",
    "Frontscheibensäge für Verbundglas": "saw",
    "Metallfeile": "nail_file",
    "Glasnagelfeile": "nail_file",
    "Schraubendreher 2 mm": "screwdriver",
    "Schraubendreher 2,5 mm": "screwdriver",
    "Schraubendreher 3 mm": "screwdriver",
    "Schraubendreher 5 mm": "screwdriver",
    "Schraubendreher 5 mm, feststellbar": "screwdriver",
    "Schraubendreher 6 mm": "screwdriver",
    "Schraubendreher 7 mm": "screwdriver",
    "Schraubendreher 7.5 mm": "screwdriver",
    "Mini-Schraubendreher 1,5 mm": "screwdriver",
    "Phillips-Schraubendreher 1/2": "screwdriver",
    "Phillips-Schraubendreher 0/1, magnetisch": "screwdriver",
    "Dosenöffner": "can_opener",
    "Flaschenöffner": "bottle_opener",
    "Kistenöffner": "bottle_opener",
    "Kistenöffner, robust": "bottle_opener",
    "Paketöffner": "bottle_opener",
    "Pinzette": "tweezers",
    "Zahnstocher": "toothpick",
    "Druckkugelschreiber": "pen",
    "Nagelfeile": "nail_file",
    "Drahtabisolierer": "wire_cutter",
    "Drahtabisolierer und -schaber": "wire_cutter",
    "Drahtschneider": "wire_cutter",
    "Drahtschneider für dünne und weiche Drähte bis 40 HRC": "wire_cutter",
    "Hartdraht-Schneider": "wire_cutter",
    "Stech-Bohr-Nähahle": "awl",
    "Stech-Reib-Ahle": "awl",
    "Stecknadel": "awl",
    "Ring": "ring",
    "Kapselheber": "cap_lifter",
    "Kapselheber, feststellbar": "cap_lifter",
    "Kombi-Zange": "pliers",
    "Kombi-Spitzzange": "pliers",
    "Lupe": "magnifier",
    "Hakenklinge": "hooked_blade",
    "Gurtenschneider": "strap_cutter",
    "Drahtbieger": "wire_bender",
    "Holzmeissel 4 mm": "chisel",
    "Holzmeissel 7 mm und -schaber": "chisel",
    "Fischentschupper": "fish_scaler",
    "Schaber": "scraper",
    "Feuerstahl": "firesteel",
    # --- second pass: photo-visible tools found in the remaining names ---
    "Brieföffner": "letter_opener",
    "Befestigungsöse": "attachment_eye",
    "Daumenpin, abnehmbar": "thumb_stud",
    "Drahtschaber": "wire_cutter",
    "Mehrzweckhaken": "multi_hook",
    "Massstab (cm)": "ruler",
    "Massstab (Zoll)": "ruler",
    "Geldband": "money_clip",
    "Gabel": "fork",
    "Fonduegabel": "fork",
    "Käseklinge": "cheese_knife",
    "Kabelklinge": "cable_knife",
    "Kabelmantel-Längsschneider": "wire_cutter",
    "Kabelmantel-Querschneider": "wire_cutter",
    "Nagelreiniger": "nail_cleaner",
    "Nagelknipser": "nail_clipper",
    "Nagelhautschieber": "nail_cleaner",
    "Hülsenpresser": "crimp_tool",
    "Kapselschneider": "cap_lifter",
    "Kapselpresser": "cap_lifter",
    "Locher": "punch",
    "Ballmarkierer": "ballpoint_pen",
    "Kordel": "cord",
    "LED": "led",
    "Fischentschupper": "fish_scaler",
    "Marlspieker": "hooked_blade",
    "Helix Zunder": "firesteel",
    "Blasrohr zum Feuerstarten": "firesteel",
    "Hufreiniger": "hoof_pick",
    "Orangenschäler": "peeler",
    "Geldband": "money_clip",
    "Gabelschlüssel M3, M4, M5": "spanner",
    "Schraubendreher 000": "screwdriver",
    "Phillips Schraubendreher 000": "screwdriver",
    "Bit Schlitz": "screwdriver",
    "Bit Schlitz 4 mm": "screwdriver",
    "Bit Schlitz 4,5 mm": "screwdriver",
    "Bit-Halter": "bit_holder",
    "Bit-Schlüssel": "bit_key",
    "Innensechskant für Bits 4 mm": "hex_key",
    "Innensechskant für Bits 5 mm für D-SUB-Stecker": "hex_key",
    "Bit Hex 3": "hex_bit",
    "Bit Hex 4": "hex_bit",
    "Bit Phillips 0": "phillips_bit",
    "Bit Phillips 1": "phillips_bit",
    "Bit Phillips 2": "phillips_bit",
    "Bit Phillips 3": "phillips_bit",
    "Bit Torx 8": "torx_bit",
    "Bit Torx 10": "torx_bit",
    "Bit Torx 15": "torx_bit",
    "Klinge, 10,5 cm": "large_blade",
    "Drahtschaber": "wire_cutter",
    "Kartenschutzhülle": "pouch",
    "Paracord-Anhänger": "paracord",
    "Pharmaspachtel": "spatula",
    "Reparatur-Werkzeug": "repair_tool",
    "Zweistufige Stütze": "support",
    "Trageclip": "clip",
    "Clip": "clip",
    "Verlängerter Erl": "extended_blade",
    "Waidklinge": "hooked_blade",
    "Waidklinge, klein": "hooked_blade",
    "Messing-Rindenlöser": "bark_lifter",
    "Thüringer": "banknote",
    # --- final pass ---
    "Angellöser": "hook_remover",
    "Coupling for corkscrew and carry clip": "bottle_cork",
    "Phillips-Schraubendreher 0/1, lang": "screwdriver",
    "Phillips-Schraubendreher 00/0": "screwdriver",
    "Platz für zusätzliche Bits": "bit_holder",
    "SIM Karten Pin": "sim_pin",
    "Scheibenzertrümmerer": "glass_breaker",
    "Schäkelöffner": "bottle_opener",
    "Sechskantloch": "hex_key",
    "Torx Schraubendreher T4": "screwdriver",
    "Uhrengehäuseöffner": "watch_opener",
    "Zughaken": "multi_hook",
}

# Catalogue entries that are already English -> canonical id.
TOOL_EN_NATIVE: dict[str, str] = {
    "Blade, straight": "large_blade",
    "Blade, pointed tip": "hooked_blade",
    "Bottle opener": "bottle_opener",
    "Metal saw": "saw",
    "Metal file": "nail_file",
    "Shackle opener": "bottle_opener",
    "Marlin spike": "hooked_blade",
    "Can opener": "can_opener",
    "Screwdriver 5 mm": "screwdriver",
    "Screwdriver 7 mm": "screwdriver",
    "Wire stripper": "wire_cutter",
    "Fondue fork": "bottle_opener",
    "Thumb stud, removable": "ring",
}


# The tools that are realistically distinguishable in a photograph of an open
# pocket knife. Measured on the 12 ground-truth photos: using this 18-tool
# vocabulary as the `choice` options scored 4/4 on the catalogue-known cases,
# while the full 64-tool vocabulary scored 1/4. Keep the option list short -
# every extra plausible option dilutes the probability mass and lets
# near-synonyms (bottle_cork vs corkscrew, paracord vs cord) win by accident.
PHOTO_VISIBLE_TOOLS: list[str] = [
    "large_blade",
    "small_blade",
    "scissors",
    "corkscrew",
    "saw",
    "screwdriver",
    "bottle_opener",
    "can_opener",
    "tweezers",
    "toothpick",
    "pen",
    "nail_file",
    "wire_cutter",
    "awl",
    "cap_lifter",
    "ring",
    "pliers",
    "magnifier",
]


def canonical_tool(name: str) -> str | None:
    """Canonical tool id for a catalogue tool name, or None if unknown.

    Handles bundled entries like "Dosenöffner | Schraubendreher 3 mm" by
    returning the first recognised component.
    """
    name = name.strip()
    if not name:
        return None
    if name in TOOL_DE:
        return TOOL_DE[name]
    if name in TOOL_EN_NATIVE:
        return TOOL_EN_NATIVE[name]
    for part in name.split("|"):
        part = part.strip()
        if part in TOOL_DE:
            return TOOL_DE[part]
        if part in TOOL_EN_NATIVE:
            return TOOL_EN_NATIVE[part]
    return None


@functools.lru_cache(maxsize=1)
def _catalogue() -> tuple[dict[str, frozenset[str]], list[dict[str, str]]]:
    if not WERKZEUGE_CSV.exists():
        return {}, []
    tools_by_article: dict[str, set[str]] = {}
    with WERKZEUGE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            article = row["artikelnummer"].strip()
            canonical = canonical_tool(row["werkzeug"])
            if canonical:
                tools_by_article.setdefault(article, set()).add(canonical)
    products: list[dict[str, str]] = []
    if PRODUKTE_CSV.exists():
        with PRODUKTE_CSV.open(encoding="utf-8-sig", newline="") as handle:
            products = list(csv.DictReader(handle, delimiter=";"))
    return {k: frozenset(v) for k, v in tools_by_article.items()}, products


def tool_set_for(article_number: str) -> frozenset[str]:
    """Canonical tool ids for a catalogue article number."""
    tools, _ = _catalogue()
    return tools.get(article_number.strip(), frozenset())


def products() -> list[dict[str, str]]:
    """Catalogue rows from victorinox_sak_produkte.csv."""
    _, rows = _catalogue()
    return rows


def EN_OPTIONS(tools: list[str] | None = None) -> dict[str, str]:
    """`criteria` dict for a Clef `choice` question over the tool vocabulary.

    Defaults to PHOTO_VISIBLE_TOOLS. The vocabulary size matters a lot: measured
    on the 12 ground-truth photos, an 18-option vocabulary scored 4/4 on the
    catalogue-known cases while a 64-option vocabulary scored 1/4. Every extra
    plausible option competes for probability mass and introduces
    near-synonyms that the model cannot separate (bottle_cork vs corkscrew,
    paracord vs cord, ruler vs ...). Keep it tight.
    """
    if tools is None:
        tools = PHOTO_VISIBLE_TOOLS
    return {tool: TOOL_EN[tool] for tool in tools if tool in TOOL_EN}


if __name__ == "__main__":
    tools, prods = _catalogue()
    mapped = sum(1 for row in prods for tool in tools.get(row["artikelnummer"], ()))
    print(f"articles with tools: {len(tools)} / {len(prods)}")
    print(f"canonical tool ids available: {len(TOOL_EN)}")
    # Report catalogue tool names we could not map, so the table can be completed.
    unmapped: set[str] = set()
    with WERKZEUGE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if canonical_tool(row["werkzeug"]) is None:
                unmapped.add(row["werkzeug"])
    print(f"\n{len(unmapped)} catalogue tool names not yet mapped:")
    for name in sorted(unmapped):
        print(f"  {name}")
