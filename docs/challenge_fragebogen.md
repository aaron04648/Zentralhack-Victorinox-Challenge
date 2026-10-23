Challenge Geber:
Name: Goldinger
Vorname: Sven
Firma: Victorinox AG
Tel: +41 79 808 74 84
E-Mail: sven.goldinger@victorinox.com

Zentral Hack Challenge 1 – Victorinox Product Match Agent
Ausgangslage
Das Victorinox-Produktsortiment sowie die Produktportfolios direkter Wettbewerber umfassen zahlreiche, teilweise optisch ähnliche Artikel. Mitarbeitende in Verkauf, Customer Service, Produktmanagement und Handel müssen ein fotografiertes Produkt heute manuell identifizieren und anschliessend passende Victorinox-Alternativen sowie technische Spezifikationen in unterschiedlichen Quellen suchen. Dies ist besonders aufwendig, wenn ein Victorinox-Produkt nicht mehr erhältlich ist oder ein Konkurrenzprodukt möglichst genau durch ein Victorinox-Produkt ersetzt werden soll. Bereits vorhandene Zuordnungen zwischen Konkurrenz- und Victorinox-Produkten liegen teilweise in umfangreichen Tabellen vor; allein im Bereich Commercial Cutlery umfasst das Sortiment mehrere hundert SKUs.


Idee
Ein multimodaler AI-Agent analysiert ein mit Smartphone oder Kamera aufgenommenes Produktfoto, erkennt Produktkategorie, Marke und – soweit möglich – das konkrete Modell bzw. die SKU. Anschliessend orchestriert er zwei Pfade: (1) Bei einem Victorinox-Produkt ermittelt er geeignete aktuelle Alternativ- oder Nachfolgeprodukte, insbesondere bei ausgelaufenen Artikeln. (2) Bei einem Konkurrenzprodukt bestimmt er anhand von Bildähnlichkeit, Produktmerkmalen und vorhandenen Cross-Reference-Regeln das funktional beste Victorinox-Ersatzprodukt. Der Agent liefert die Empfehlung mit vollständigen technischen Angaben, einer verständlichen Begründung, einem Ähnlichkeits- bzw. Konfidenzwert und bei Unsicherheit mehreren Kandidaten zur Auswahl.


Ziel oder Endprodukt Bspw. App, Webseite, Dashboard etc.
Hackathon-Prototyp als mobilfähige Web-App: Foto aufnehmen oder hochladen, Produkt automatisch erkennen und innerhalb weniger Sekunden eine priorisierte Victorinox-Empfehlung anzeigen. Die Resultatansicht enthält Produktbild, Artikelnummer, Produktname, Verfügbarkeit bzw. Status, zentrale technische Merkmale, Vergleich zum erkannten Ausgangsprodukt, Begründung der Empfehlung und Konfidenz. Eine einfache Feedback-Funktion („korrekt / nicht korrekt“ und Auswahl eines besseren Treffers) dient zur laufenden Verbesserung. Der Prototyp soll mindestens für eine klar abgegrenzte Produktkategorie end-to-end funktionieren.


Bestehende ähnliche Lösungen
Ähnliche Lösungsprinzipien existieren als visuelle Produktsuche und „Similar Items“-Funktion in E-Commerce-Plattformen: Bildmerkmale werden als Embeddings abgelegt und über eine Vektorsuche mit Katalogbildern verglichen. Generische Bilderkennungs- oder Auto-Tagging-Lösungen reichen für diesen Use Case jedoch nicht aus, da eine Identifikation auf SKU-Ebene sowie eine fachlich begründete Victorinox-Substitution erforderlich ist. Intern bestehen teilweise bereits Cross-Reference-Tabellen zwischen Konkurrenz- und Victorinox-Produkten; eine integrierte Lösung, welche Fotoerkennung, technische Produktdaten und regelbasierte Alternativsuche verbindet, ist jedoch nicht bekannt.


Anforderungen an Lösung (Technisch, mit welcher Technologie muss es umgesetzt werden)
Die Lösung soll als modularer Agenten-Workflow auf dem bevorzugten Microsoft-Stack umgesetzt werden. Benötigt werden: eine responsive Web-Oberfläche mit Kamera-/Upload-Funktion; ein Vision-Modell für Objekterkennung, Marken-/Modellerkennung und OCR; Bild- und Text-Embeddings mit Vektorindex für Top-k-Ähnlichkeitssuche; ein Product-Data-Agent für den kontrollierten Zugriff auf freigegebene Produktstammdaten; ein Recommendation-Agent, der technische Merkmale, Verfügbarkeit, Nachfolgebeziehungen und Cross-Reference-Regeln gewichtet; sowie ein Orchestrator für Routing, Ergebnisaufbereitung und Rückfragen. Die Architektur soll API-basiert, erweiterbar und modellunabhängig sein.


Datenverfügbarkeit (vorhanden und zugänglich -Schnittstellen API, Datenbank, Memory Stick).
Voraussichtlich vorhanden: offizielle Produktstammdaten mit Artikelnummern, Bezeichnungen, Kategorien, technischen Merkmalen, Verfügbarkeits-/Lifecycle-Status und Produktbildern; Produktkataloge und technische Dokumentationen; Teilweise Cross-Reference-Tabellen für Konkurrenzprodukte; gegebenenfalls Daten aus PIM/PLM, ERP, DAM/Bynder, Webshop sowie der Microsoft-Fabric-Lakehouse-Plattform. Für den Hackathon sollte ein qualitätsgeprüfter Export oder eine Read-only-Schnittstelle für eine ausgewählte Produktkategorie bereitgestellt werden.


Spezielle Erwartungen an Resultat
Erwartet wird eine überzeugende Live-Demo mit realen Smartphone-Fotos und nachvollziehbaren Empfehlungen statt eines reinen Chatbots. Der Prototyp soll den gesamten Ablauf vom Foto bis zur technischen Vergleichsansicht zeigen und klar zwischen Victorinox- und Konkurrenzprodukt unterscheiden. Erfolgskriterien für den definierten Testkatalog: hoher Anteil korrekter Produkte in den Top-3-Treffern; fachlich plausibles bestes Alternativprodukt; vollständige und quellenbasierte technische Angaben; transparente Konfidenz und keine erfundenen Spezifikationen. Bei unzureichender Sicherheit soll der Agent gezielt nach einem weiteren Foto, einer sichtbaren Artikelnummer oder einem Merkmal fragen.




