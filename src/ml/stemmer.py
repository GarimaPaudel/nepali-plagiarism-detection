from typing import List
import snowballstemmer


class NepaliStemmer:
    def __init__(self):
        self.stemmer = snowballstemmer.stemmer("nepali")

    def stem_text(self, text: str) -> List[str]:
        return self.stemmer.stemWords(text.split())
