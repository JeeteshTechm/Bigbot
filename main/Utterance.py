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
        self.similarity = []
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


    def show_confidence_graph(self):
        intents = [result['name'] for result in self.results]
        confidences = [result['confidence'] for result in self.results]

        # Create a subplot with a single trace
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Bar(x=intents, y=confidences), row=1, col=1)

        fig.update_layout(title='Confidence graph for query: ' + self.query,
                          xaxis_title='Intents',
                          yaxis_title='Confidence')

        fig.show()

    def show_confidence_heatmap(self):
        intents = [result['name'] for result in self.results]
        confidences = [result['confidence'] for result in self.results]

        # Define the trace for the heatmap
        trace = go.Heatmap(z=[confidences],
                           x=intents,
                           y=[self.query],
                           colorscale='YlGnBu')

        # Set the layout for the heatmap
        layout = go.Layout(title='Confidence heatmap for query: ' + self.query,
                           xaxis=dict(title='Intents'),
                           yaxis=dict(title='Query'))

        # Create the figure and add the trace
        fig = go.Figure(data=[trace], layout=layout)

        # Show the figure
        fig.show()
