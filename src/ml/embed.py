from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TFIDFEmbedder:
    def calculate_features(self, original: str, suspicious: str) -> float:
        vectorizer = TfidfVectorizer().fit([original, suspicious])
        original_vec = vectorizer.transform([original])
        suspicious_vec = vectorizer.transform([suspicious])
        return cosine_similarity(original_vec, suspicious_vec)[0][0]
