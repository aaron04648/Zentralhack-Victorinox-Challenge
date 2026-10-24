"""Importe aus PDF-Katalogen (catalogues/*.pdf) nach data/kataloge/*.json.

Ein Modul pro Katalog, weil jedes PDF ein eigenes Layout hat. Gemeinsame Helfer in pdf.py.
Die Ausgaben sind erzeugt: nie von Hand bearbeiten, sondern das Modul erneut ausführen.

Abhängigkeiten (nicht im Backend-Container nötig): scraper/requirements.txt
"""
