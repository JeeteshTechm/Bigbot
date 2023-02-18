import json
import textdistance
import spacy
import rasa.nlu.training_data as training_data
import rasa.nlu.config as config
import rasa.nlu.model as model
import rasa.utils.io as io_utils
import plotly.express as px

class UtteranceDistance:
    # Initializing the class with given parameters
    def __init__(self, utterances: list, query: str, algorithm: str = 'levenshtein'):
        self.algorithm = algorithm
        self.utterances = utterances
        self.query = query
        self.distance = 0.0
        self.index = None
        self.text = None

        # If query is given, compute the results
        if self.query:
            self._compute()

    # Private method to compute the results
    def _compute(self):

        # Loading spacy model
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(self.query)

        # Getting lemmatized verbs, nouns and adjectives from the query
        verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
        nouns = [token.lemma_ for token in doc if token.pos_ == "NOUN"]
        adjectives = [token.lemma_ for token in doc if token.pos_ == "ADJ"]

        # Loading training data and creating an interpreter
        nlu_data = training_data.load_data('data/nlu.md')
        trainer = model.Trainer(config.load('config.yml'))
        interpreter = trainer.train(nlu_data)
        model_directory = trainer.persist('models/')

        # Parsing the query and getting intent ranking
        results = interpreter.parse(self.query)['intent_ranking']

        # Comparing each utterance with query and calculating distance
        for i, utterance in enumerate(self.utterances):
            match_distance = textdistance.levenshtein.normalized_similarity(self.query, utterance)
            intent = results[i]['name']
            confidence = results[i]['confidence']
            distance = match_distance * (1 - confidence)

            # Updating the distance, text and index if current utterance has less distance
            if distance < self.distance or not self.distance:
                self.distance = distance
                self.text = utterance
                self.index = i

    # String representation of the class
    def __str__(self):
        return f"'{self.text}', index:{self.index}, confidence: {self.get_confidence()}%"

    # Method to get the text with least distance
    def get_text(self):
        return self.text

    # Method to get the distance
    def get_distance(self):
        return self.distance

    # Method to get the confidence
    def get_confidence(self):
        return int((1 - self.distance) * 100)

    # Method to get the index
    def get_index(self):
        return self.index
