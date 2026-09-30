"""Pick top-k voice examples by TF-IDF similarity. Reads ONLY
voice_examples.jsonl — never holdout.jsonl (enforced by test)."""
import os

from app.models import VoiceExample

K = 5


def retrieve(examples: list[VoiceExample], post_text: str, k: int | None = None) -> list[VoiceExample]:
    if not examples:
        return []
    k = k or int(os.getenv("RETRIEVE_K", str(K)))
    k = min(k, len(examples))
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = [f"{e.topic} {e.post_text} {e.founder_comment}" for e in examples]
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        matrix = vectorizer.fit_transform(corpus + [post_text])
        scores = cosine_similarity(matrix[-1:], matrix[:-1])[0]
        ranked = sorted(range(len(examples)), key=lambda i: -scores[i])
        return [examples[i] for i in ranked[:k]]
    except Exception:
        # tiny corpora / empty vocab: deterministic fallback, no crash
        return examples[:k]
