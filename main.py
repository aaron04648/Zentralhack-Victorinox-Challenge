from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

# 1. FastAPI-Instanz erstellen
app = FastAPI(title="Mein erstes FastAPI-Projekt")

# Beispiel-Datenbank im Speicher (In-Memory)
fake_db = [
    {"id": 1, "titel": "Einkaufen", "erledigt": False},
    {"id": 2, "titel": "Python lernen", "erledigt": True}
]

# 2. Pydantic-Modell für die POST-Datenvalidierung definieren
class TodoItem(BaseModel):
    titel: str
    erledigt: bool = False


# --- ENDPOINTS ---

# GET: Startseite / Willkommen
@app.get("/")
def read_root():
    return {"status": "aktiv", "nachricht": "Willkommen bei meiner FastAPI!"}

# GET: Alle Einträge abrufen
@app.get("/items")
def get_all_items():
    return fake_db

# GET: Einen spezifischen Eintrag via ID abrufen (Pfad-Parameter)
@app.get("/items/{item_id}")
def get_item(item_id: int):
    # Sucht das Item mit der passenden ID
    for item in fake_db:
        if item["id"] == item_id:
            return item
    return {"fehler": "Eintrag nicht gefunden"}, 404

# POST: Einen neuen Eintrag hinzufügen
@app.post("/items")
def create_item(item: TodoItem):
    # Neue ID generieren
    neue_id = max([i["id"] for i in fake_db]) + 1 if fake_db else 1
    
    # Daten aus dem Pydantic-Modell in ein Dictionary umwandeln
    neuer_eintrag = {"id": neue_id, "titel": item.titel, "erledigt": item.erledigt}
    
    # In der "Datenbank" speichern
    fake_db.append(neuer_eintrag)
    
    return {"nachricht": "Erfolgreich erstellt", "daten": neuer_eintrag}

