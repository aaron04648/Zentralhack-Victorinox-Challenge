"""Fine-Tuning eines Vision-Modells auf die Werkzeugerkennung (Azure OpenAI oder OpenAI).

Die Trainingsbeispiele haben genau das Format, das app/vision.py zur Laufzeit schickt
(System-Prompt + Bild -> JSON-Antwort), nur ohne Few-Shot-Beispiele.

Schritte:
  python -m training.finetune vorbereiten   # schreibt train/valid JSONL, kostet nichts
  python -m training.finetune starten       # lädt hoch und startet den Job (kostet!)
  python -m training.finetune status <job>  # Fortschritt; am Ende steht das fertige Modell

Danach (Azure): das fertige Modell im Portal als Deployment bereitstellen und dessen Namen
als VISION_FT_DEPLOYMENT in .env eintragen. Bei OpenAI direkt: Modellname eintragen.

Konfiguration: dieselben Variablen wie app/vision.py, zusätzlich
  FT_BASISMODELL  (Standard gpt-4o-2024-08-06, muss Vision-Fine-Tuning unterstützen)
  FT_EPOCHEN      (Standard 3)
"""

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

from app import vision

OUT = Path(__file__).resolve().parent.parent / "data" / "training"
VALID_ANTEIL = 0.15


def bild_als_data_url(url):
    """Bilder eingebettet statt als URL: der Trainingsdienst muss nichts nachladen."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ZentralHack training)"})
    with urllib.request.urlopen(req, timeout=30) as res:
        mime = res.headers.get_content_type() or "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(res.read()).decode()}"


def beispiel(sample):
    msgs = vision.nachrichten(bild_als_data_url(sample["bild_url"]))
    msgs.append({"role": "assistant", "content": vision.antwort_fuer(
        sample["werkzeug_gruppen"], sample["marke"],
        sample["name"] if sample["marke"] == "Victorinox" else sample.get("name"))})
    return {"messages": msgs}


def vorbereiten():
    samples = [json.loads(z) for z in (OUT / "datensatz.jsonl").read_text(encoding="utf-8").splitlines()]
    train = [s for s in samples if s["split"] == "train"]
    if len(train) < 10:
        sys.exit("Zu wenig Trainingsbilder (mind. 10). Zuerst: python -m training.datensatz")
    # Validierung: jedes k-te Bild, deterministisch
    k = max(2, round(1 / VALID_ANTEIL))
    valid, train = train[::k], [s for i, s in enumerate(train) if i % k]
    for name, teil in (("ft_train.jsonl", train), ("ft_valid.jsonl", valid)):
        with (OUT / name).open("w", encoding="utf-8") as f:
            for i, s in enumerate(teil, 1):
                try:
                    f.write(json.dumps(beispiel(s), ensure_ascii=False) + "\n")
                except OSError as fehler:
                    print(f"  übersprungen {s['id']}: {fehler}", file=sys.stderr)
                print(f"\r  {name}: {i}/{len(teil)}", end="", file=sys.stderr)
        print(file=sys.stderr)
    print(f"Fertig: {len(train)} Training, {len(valid)} Validierung in {OUT}", file=sys.stderr)


def starten():
    client = vision.client()
    dateien = {}
    for name in ("ft_train.jsonl", "ft_valid.jsonl"):
        with (OUT / name).open("rb") as f:
            dateien[name] = client.files.create(file=f, purpose="fine-tune").id
        print(f"  hochgeladen {name}: {dateien[name]}", file=sys.stderr)
    job = client.fine_tuning.jobs.create(
        model=os.getenv("FT_BASISMODELL", "gpt-4o-2024-08-06"),
        training_file=dateien["ft_train.jsonl"],
        validation_file=dateien["ft_valid.jsonl"],
        hyperparameters={"n_epochs": int(os.getenv("FT_EPOCHEN", "3"))},
        suffix="sak-werkzeuge",
    )
    print(f"Job gestartet: {job.id} (Status: {job.status})")
    print(f"Fortschritt:   python -m training.finetune status {job.id}")


def status(job_id):
    client = vision.client()
    job = client.fine_tuning.jobs.retrieve(job_id)
    print(f"Status: {job.status}")
    if job.fine_tuned_model:
        print(f"Fertiges Modell: {job.fine_tuned_model}")
        print("Azure: im Portal deployen, dann VISION_FT_DEPLOYMENT=<deployment-name> in .env setzen.")
    for event in reversed(client.fine_tuning.jobs.list_events(job_id, limit=10).data):
        print(f"  {event.created_at}  {event.message}")


if __name__ == "__main__":
    befehl = sys.argv[1] if len(sys.argv) > 1 else ""
    if befehl == "vorbereiten":
        vorbereiten()
    elif befehl == "starten":
        starten()
    elif befehl == "status" and len(sys.argv) > 2:
        status(sys.argv[2])
    else:
        sys.exit(__doc__)
