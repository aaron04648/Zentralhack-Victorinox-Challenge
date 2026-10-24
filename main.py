from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import numpy as np
from embedings import cosine_similarity, CATEGORIES, generate_category_embeddings, setup_embedding_model


app = FastAPI(title="Victorinox-Projekt")

category_emb = generate_category_embeddings()


class CategoryScores(BaseModel):
    query: str
    scores: Dict[str, float]


@app.get("/score_categories", response_model=CategoryScores)
def get_scores(q: str, category_embeddings=category_emb) -> CategoryScores:
    # Falls die Anfrage leer ist, leeres Dict zurückgeben
    if not q.strip():
        return CategoryScores(query=q, scores={cat: 0.0 for cat in CATEGORIES})

    # Suchtext einbetten
    query_embedding = list(setup_embedding_model().embed([q]))[0]
    
    # Dictionary für die Antwort aufbauen
    scores_dict = {}
    for category, cat_emb in zip(CATEGORIES, category_embeddings):
        score = cosine_similarity(query_embedding, cat_emb)
        scores_dict[category] = round(score, 4)
        
    # Das Dictionary nach den höchsten Scores sortieren möchten
    sorted_scores_dict = dict(sorted(scores_dict.items(), key=lambda item: item[1], reverse=True))
    
    # Rückgabe validiert gegen Ihr Pydantic-Modell
    return CategoryScores(query=q, scores=sorted_scores_dict)



