"""Alle Katalog-Importe nacheinander: python -m scraper.kataloge"""

from scraper.kataloge import gerber, leatherman, swiza, victorinox_2026

for modul in (victorinox_2026, swiza, leatherman, gerber):
    print(f"== {modul.__name__}")
    modul.main()
