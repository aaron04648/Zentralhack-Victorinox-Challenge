# Zentralhack-Victorinox-Challenge
Hackathon 23.10.2026

## Project Management
- Team members: Philipp, Aaron, Admir, Simon
- work items:
    - Aaron: data processing
    - classification
        - Philipp: embeddings
        - Simon: jev
    - Claude: app

# API Endpoints 
POST /api/products/image

{ "Everyday": true, "Personalisieren": true }
{
  "anzahl": 28,
  "bild_url": "https://...",
  "treffer": [
    { "artikelnummer": "0.6223.G", "name": "Classic SD", "bild_url": "https://..." },
    ...
  ]
}
