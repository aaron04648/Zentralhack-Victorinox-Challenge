import numpy as np
from fastembed import TextEmbedding

# 1. Modell initialisieren (lädt standardmäßig ein leichtgewichtiges BGE-Modell)
embedding_model = TextEmbedding()

# 2. Vor-eingebettete Texte (Ihre Datenbank/Referenzen)
existing_texts = [
    "Outdoor, Fischen, Jagen,",
    "Everyday, ",
    ""
]

# Texte in Vektoren umwandeln (gibt einen Generator zurück)
embeddings_generator = embedding_model.embed(existing_texts)
existing_embeddings = list(embeddings_generator)  # Als Liste von Arrays speichern

# 3. Neuen Suchtext einbetten
query_text = ""
query_embedding = list(embedding_model.embed([query_text]))[0]

# 4. Abgleich via Kosinus-Ähnlichkeit (Manuelle Berechnung per NumPy)
def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# Ähnlichkeit zu allen existierenden Texten berechnen
scores = [cosine_similarity(query_embedding, ext_emb) for ext_emb in existing_embeddings]

# 5. Bestes Ergebnis finden
best_match_idx = np.argmax(scores)

print(f"Suchanfrage: '{query_text}'\n")
print("Testergebnisse:")
for text, score in zip(existing_texts, scores):
    print(f"- Ähnlichkeit: {score:.4f} | Text: '{text}'")

print(f"\nBester Treffer: '{existing_texts[best_match_idx]}' (Score: {scores[best_match_idx]:.4f})")
