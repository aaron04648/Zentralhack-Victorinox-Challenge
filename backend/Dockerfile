FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
# Kein --reload im Container: der Reload-Prozess startet die App in einem zweiten
# Interpreter, in dem der Modul-Import anders gebunden wird. Fuer die Entwicklung
# laeuft der Backend lokal mit `uvicorn app.main:app --reload`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
