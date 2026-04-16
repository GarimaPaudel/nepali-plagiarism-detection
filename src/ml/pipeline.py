"""
Core plagiarism detection pipeline.

- TF-IDF cosine similarity
- Rabin-Karp exact sentence matching
- XLM-RoBERTa semantic similarity (lazy-loaded, gracefully skipped if unavailable)
"""
import os
import re
import unicodedata

import PyPDF2
import torch
import torch.nn.functional as F
from loguru import logger

from src.ml.embed import TFIDFEmbedder
from src.ml.model_loader import get_model, is_model_available
from src.ml.preprocess import TextPreprocessor


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def split_into_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[।?!])\s+", text)


def read_file_with_encoding(file_path: str) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode file: {file_path}")


def extract_text_from_pdf(uploaded_pdf) -> str:
    text = ""
    pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    text = text.replace("\n", "")
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------------------
# Rabin-Karp exact sentence matching
# ---------------------------------------------------------------------------

def rabin_karp_single_sentence(text: str, pattern: str) -> tuple[bool, int]:
    d, q = 256, 101
    n, m = len(text), len(pattern)
    if m > n:
        return False, -1

    h = pow(d, m - 1, q)
    p = t = 0
    for i in range(m):
        p = (d * p + ord(pattern[i])) % q
        t = (d * t + ord(text[i])) % q

    for i in range(n - m + 1):
        if p == t and text[i:i + m] == pattern:
            return True, i
        if i < n - m:
            t = (d * (t - ord(text[i]) * h) + ord(text[i + m])) % q
            if t < 0:
                t += q

    return False, -1


def find_copied_sentences(text: str, pattern: str) -> list[tuple[str, int, int]]:
    """Return list of (matched_sentence, sentence_index, char_index)."""
    text_sentences = split_into_sentences(text)
    pattern_sentences = split_into_sentences(pattern)
    matches = []
    for pat_sentence in pattern_sentences:
        for j, txt_sentence in enumerate(text_sentences):
            if pat_sentence and txt_sentence:
                found, index = rabin_karp_single_sentence(txt_sentence, pat_sentence)
                if found:
                    matches.append((pat_sentence, j, index))
    return matches


# ---------------------------------------------------------------------------
# XLM-RoBERTa semantic similarity
# ---------------------------------------------------------------------------

def _get_embedding(text: str, tokenizer, model) -> torch.Tensor:
    inputs = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        output = model(**inputs)
    return output.last_hidden_state.mean(dim=1)


def xlm_similarity(text1: str, text2: str) -> float | None:
    """Returns cosine similarity [0,1], or None if model is unavailable."""
    if not text1 or not text2:
        return None
    if not is_model_available():
        logger.warning("XLM-RoBERTa model not loaded — skipping semantic similarity.")
        return None
    tokenizer, model = get_model()
    emb1 = _get_embedding(text1, tokenizer, model)
    emb2 = _get_embedding(text2, tokenizer, model)
    return F.cosine_similarity(emb1, emb2).item()


# ---------------------------------------------------------------------------
# Main comparison pipeline
# ---------------------------------------------------------------------------

def compare_against_corpus(uploaded_text: str) -> list[dict] | None:
    """
    Compare uploaded_text against every .txt/.pdf in the corpus directory.
    Returns list of result dicts, or None if corpus directory is missing.

    Each dict has:
        filename, is_plagiarized, similarity_score, xlm_similarity, matches
    """
    from src.config import settings

    corpus_path = settings.CORPUS_PATH
    if not os.path.exists(corpus_path):
        logger.error("Corpus directory not found: %s", corpus_path)
        return None

    with open(settings.STOPWORDS_PATH, "r", encoding="utf-8") as f:
        stopwords = f.read().splitlines()

    preprocessor = TextPreprocessor(stopwords)
    embedder = TFIDFEmbedder()

    results = []
    for filename in os.listdir(corpus_path):
        file_path = os.path.join(corpus_path, filename)
        if filename.endswith(".txt"):
            file_text = read_file_with_encoding(file_path)
        elif filename.endswith(".pdf"):
            with open(file_path, "rb") as pdf_file:
                file_text = extract_text_from_pdf(pdf_file)
        else:
            continue

        preprocessed_ref = preprocessor.preprocess(file_text)
        preprocessed_sub = preprocessor.preprocess(uploaded_text)
        ref_str = " ".join(w for sentence in preprocessed_ref for w in sentence)
        sub_str = " ".join(w for sentence in preprocessed_sub for w in sentence)

        tfidf_score = embedder.calculate_features(ref_str, sub_str) if ref_str and sub_str else 0.0
        is_plagiarized = tfidf_score >= settings.PLAGIARISM_THRESHOLD
        matches = find_copied_sentences(file_text, uploaded_text)
        xlm_score = xlm_similarity(file_text, uploaded_text)

        results.append({
            "filename": filename,
            "is_plagiarized": is_plagiarized,
            "similarity_score": float(tfidf_score),
            "xlm_similarity": float(xlm_score) if xlm_score is not None else None,
            "matches": [list(m) for m in matches],
        })

    return results
