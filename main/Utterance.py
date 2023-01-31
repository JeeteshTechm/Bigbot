import json
import textdistance
from . import Log

class UtteranceDistance:
    def __init__(self, utterances: list, query: str, algorithm: str = 'levenshtein'):
        self.algorithm = algorithm
        self.utterances = utterances
        self.query = query
        self.distance = 0.0
        self.index = None
        self.text = None
        if self.query:
            self._compute()

    def _compute(self):
        for i, utterance in enumerate(self.utterances):
            match_distance = textdistance.levenshtein.normalized_similarity(self.query, utterance)
            if match_distance > self.distance:
                self.distance = match_distance
                self.text = utterance
                self.index = i

    def __str__(self):
        return f"'{self.text}', index:{self.index}, confidence: {self.get_confidence()}%"

    def get_text(self):
        return self.text

    def get_distance(self):
        return self.distance

    def get_confidence(self):
        return int(self.distance * 100)

    def get_index(self):
        return self.index
