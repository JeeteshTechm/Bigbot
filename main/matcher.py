import json
import spacy
from spacy.tokens import Span
from intents import (
    AddTaskIntent, BookIntent, CheckIntent, ContactIntent, CreateIntent,
    DeleteIntent, DeliveryIntent, DesireIntent, GreetIntent, Intent,
    LinkTaskIntent, MatchEmail, MatchEmailUsingPattern, MatchPhoneNumber,
    NewsIntent, OrderIntent, PurchaseIntent, RateIntent, RemindIntent,
    RentIntent, SearchIntent, SentenceSimilarity, SetDeadlineIntent, SetIntent,
    TokenSimilarity, UpdateIntent
)

class ProcessText:
    def __init__(self, input_statement, nlp):
        self.nlp = nlp
        self.doc = nlp(input_statement)
        self.ents = self.doc.ents
        self.labels = ['PERSON', 'ORG', 'GPE', 'DATE', 'TIME', 'MONEY']
        self.properties = ['pos', 'tag', 'dep', 'lemma', 'is_alpha', 'morph', 'is_stop']

    def get_entities(self, label):
        return [ent.text for ent in self.ents if ent.label_ == label]

    def get_properties(self, prop):
        return {token.i: {prop: getattr(token, prop)} for token in self.doc}

    @property
    def get_names(self):
        possible_initials = ['Mr.', 'Mr', 'Mrs.', 'Mrs', 'Dr.', 'Dr', 'Prof.', 'Prof', 'Col.', 'Col']
        names = []
        for ent in self.ents:
            if ent.label_ == "PERSON":
                if ent.start != 0 and self.doc[ent.start-1].text in possible_initials:
                    span = Span(self.doc, ent.start-1, ent.end, label=ent.label_)
                else:
                    span = Span(self.doc, ent.start, ent.end, label=ent.label_)
                names.append(span.text)
        return names

    def get_urls(self):
        urls = []
        for token in self.doc:
            if token.like_url:
                urls.append(token.text)
        return urls

    def get_intent(self):
        intent_matchers = [
            Matcher(self.doc.vocab).add(name, 'INTENT', patterns) for name, patterns in INTENT_PATTERNS.items()
        ]
        for matcher in intent_matchers:
            matches = matcher(self.doc)
            if matches:
                return INTENT_MAPPING[matches[0][0]]
        return None
