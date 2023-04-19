class EmailMatcher:
    def __init__(self, input_text):
        self.doc = input_text
        self.emails = []

    @property
    def email(self):
        is_email = False

        for token in self.doc:
            if token.like_email:
                is_email = True
                self.emails.append(token)
        return is_email, self.emails


class EmailMatcherUsingPattern:
    def __init__(self, input_text):
        self.doc = input_text
        self.emails = None

    def get_email(self, pattern, nlp):
        is_email, self.emails = self.get_matched_string(pattern=pattern, pattern_name="EMAIL", nlp=nlp)
        return is_email, self.emails


class PhoneNumberMatcher:
    def __init__(self, input_text):
        self.doc = input_text
        self.phone_numbers = []

    def get_phone_number(self, pattern, nlp):
        is_phone, self.phone_numbers = self.get_matched_string(pattern=pattern, pattern_name="PHONE", nlp=nlp)
        return is_phone, self.phone_numbers


class IntentMatcher:
    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, processed_text, pattern_name):
        is_match, matched_string = processed_text.get_matched_string(pattern=self.pattern, pattern_name=pattern_name)
        if is_match:
            return {'data': [i.text for i in matched_string]}
        return {}


class BookIntentMatcher(IntentMatcher):
    pass


class CheckIntentMatcher(IntentMatcher):
    pass


class ContactIntentMatcher(IntentMatcher):
    pass


class CreateIntentMatcher(IntentMatcher):
    pass


class DeleteIntentMatcher(IntentMatcher):
    pass


class DeliveryIntentMatcher(IntentMatcher):
    pass


class DesireIntentMatcher(IntentMatcher):
    pass


class GreetIntentMatcher(IntentMatcher):
    pass


class OrderIntentMatcher(IntentMatcher):
    pass


class PurchaseIntentMatcher(IntentMatcher):
    pass


class NewsIntentMatcher(IntentMatcher):
    pass


class RateIntentMatcher(IntentMatcher):
    pass


class RemindIntentMatcher(IntentMatcher):
    pass


class RentIntentMatcher(IntentMatcher):
    pass


class SearchIntentMatcher(IntentMatcher):
    pass


class SetIntentMatcher(IntentMatcher):
    pass


class UpdateIntentMatcher(IntentMatcher):
    pass


class AddTaskIntentMatcher(IntentMatcher):
    pass


class LinkTaskIntentMatcher(IntentMatcher):
    pass


class SetDeadlineIntentMatcher(IntentMatcher):
    pass


class TokenSimilarity:
    def __init__(self, nlp):
        self.nlp = nlp

    def get_similarity(self, token1, token2):
        token1 = self.nlp(token1)
        token2 = self.nlp(token2)
        return token1.similarity(token2)


class SentenceSimilarity:
    def __init__(self, nlp):
        self.nlp = nlp

    def get_similarity(self, sentence1, sentence2):
        doc1 = self.nlp(sentence1)
        doc2 = self.nlp(sentence2)
        similarity = doc1.similarity(doc2)
        return similarity
