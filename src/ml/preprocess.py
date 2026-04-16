import re
import string

from src.ml.stemmer import NepaliStemmer


class TextPreprocessor:
    def __init__(self, stopwords: list[str]):
        self.stopwords = stopwords
        self.stemmer = NepaliStemmer()

    def preprocess(self, text: str) -> list[list[str]]:
        sentences = re.split(r"(?<=[।?!]) +", text)
        processed_sentences = []
        for sentence in sentences:
            words = re.findall(r"[\u0900-\u097F]+|[\d]+|[\w]+", sentence)
            joined_text = " ".join(words)
            translator = str.maketrans("", "", string.punctuation + "।")
            cleaned_text = joined_text.translate(translator)
            translation_table = str.maketrans("", "", "0123456789०१२३४५६७८९")
            cleaned_text = cleaned_text.translate(translation_table)
            cleaned_text = "".join(c for c in cleaned_text if c != "।")
            words = re.findall(r"[\u0900-\u097F]+", cleaned_text)
            filtered_words = [w for w in words if w not in self.stopwords]
            stemmed = self.stemmer.stem_text(" ".join(filtered_words))
            processed_sentences.append(stemmed)
        return processed_sentences
