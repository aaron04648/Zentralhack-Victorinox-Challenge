import numpy as np
from fastembed import TextEmbedding


CATEGORIES = [
    "Outdoor, Fischen, Jagen,",
    "Everyday, Freizeit, Wandern, Küche, ",
    "Sport, Fitness, Saling",
    "Crafts, Werkzeug, Baustelle",
]

def setup_embedding_model():
    embedding_model = TextEmbedding()
    return embedding_model


def cosine_similarity(v1, v2):
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


def generate_category_embeddings():
    embedding_model = setup_embedding_model()
    category_embeddings = list(embedding_model.embed(CATEGORIES))
    return category_embeddings



