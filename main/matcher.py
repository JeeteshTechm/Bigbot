import json
import spacy
from spacy.matcher import Matcher
from spacy.tokens import Span

################################ chosing model and loading it ###################
#### choose your lanaguage and model
model_type = "small"
lang = "English"
######

# language dictionary
language = {
    "English": 'en',
    "German": "de",
    # remaining lanagauge can be added here
}

# dictionary of available or added model (names, paths or symlinks of models)
models = {
    "small": '{}_core_web_sm'.format(language[lang]),
    "medium": '{}_core_web_md'.format(language[lang]),
    "large": '{}_core_wev_lg'.format(language[lang])
    # more models can be added (iff required)
}

# load the spacy model
nlp = spacy.load(models[model_type])

# load json file which contains the patterns
with open("./pattern.json", "r") as f:
    patterns = json.load(f)
################################################################################



class ProcessText:
    """
    Attributes:
        input_statement (str): input statement
        nlp (object): spaCy's loaded model (nlp = spacy.load('en_core_web_sm'))
        pattern (list): It is list of lists where each list is list of dictionary/dictionaries.
            e.g.
            pattern = [
                [
                    {"LOWER": "hello"},
                    {"IS_PUNCT": True},
                    {"LOWER": "world"}
                ],
                [
                    {"LOWER": "hello"},
                    {"LOWER": "world"}
                ]
            ]

                - each pattern is list of dictionary/dictionaries
                - each dictionary represents the propery of a token. If all properties are matched then it will be considered as Match
                otherwise it will not be considered as Match.
                - `key` of dictionary is attribute of spaCy's Token (e.g. POS, LEMMA, LOWER, TEXT, etc.)
                    refer to this page to know more (https://spacy.io/usage/rule-based-matching#adding-patterns-attributes)
                - `value` of dictionary will depend on Token attribute that you will choose and what you want to match

            for more details, refer to this page: https://spacy.io/usage/rule-based-matching

            >>>matcher=Matcher(nlp.vocab)
            >>>matcher.add('PatternName', pattern)
    """
    def __init__(self, input_statement, nlp):
        self.nlp = nlp
        self.doc = nlp(input_statement)
        self.names = None
        self.ORGs = None
        self.GPEs = None
        self.dates = None
        self.times = None
        self.moneys = None


    @property
    def get_names(self):
        """
        This propert-method will extract all names from the given sentence using spaCy.

        Returns:
            names (list): this list contain all person's name. List can have mutilple names if ther are multiple names in the sentence.
                In case there are no match
        """

        # add more initials as per your requirement
        possible_initials = ['Mr.', 'Mr', 'Mrs.', 'Mrs', 'Dr.', 'Dr', 'Prof.', 'Prof', 'Col.', 'Col']
        self.names = []

        for ent in self.doc.ents:
            if ent.label_ == "PERSON":
                if ent.start != 0:
                    prev_token = self.doc[ent.start-1].text
                    if prev_token in possible_initials:
                        span = Span(self.doc, ent.start-1, ent.end, label=ent.label_)
                    else:
                        span = Span(self.doc, ent.start, ent.end, label=ent.label_)
                else:
                    span = Span(self.doc, ent.start, ent.end, label=ent.label_)
                self.names.append(span.text)
        return self.names


    @property
    def get_orgs(self):
        """
        This propert-method will extract all Organisation from the given sentence using spaCy.

        Returns:
            ORGs (list): Returned list contain organisation name/names. If there are no organisation name in the sentence,
                it will be an empty list
        """
        self.ORGs = []
        for ent in self.doc.ents:
            if ent.label_ == 'ORG':
                self.ORGs.append(ent.text)
        return self.ORGs


    @property
    def get_gpes(self):
        """
        This propert-method will extract all geographical locations in the given sentence using spaCy.
            Geographical locations: Country, Cities, States (not very accurate, for high performance use look-up table.)

        Returns:
            GPEs (list): This list will contain all geographical location in the given sentence.
                If there is no such location, returned list be empty.
        """
        self.GPEs = []
        for ent in self.doc.ents:
            if ent.label_ == 'GPE':
                self.GPEs.append(ent.text)
        return self.GPEs


    @property
    def get_dates(self):
        """
        This propert-method will extract all dates form the given sentence using spaCy.

        NOTE: It will not be converting string into exact date format. If you want to convert te returned data into `datetime` (or some other format),
            change the method accordingly.

        Returns:
            dates (list): Returned list will contain date token/tokens.
                If there is no date (or not found using spaCy), an empty list will be returned.
        """
        self.dates = []
        for ent in self.doc.ents:
            if ent.label_ == 'DATE':
                self.dates.append(ent.text)
        return self.dates


    @property
    def get_times(self):
        """
        This propert-method will extract all times (e.g. 2 hours, 11:00 am, 02:00 pm, last 2 hours, etc.) from the given sentence using spaCy.

        Returns:
            times (list): Returned list will contain all token/tokens which correspond to `TIME` entity label in spaCy (in ner).
                If no such token is found in the sentence, an empty list will be returned.
        """
        self.times = []
        for ent in self.doc.ents:
            if ent.label_ == "TIME":
                self.times.append(ent.text)
        return self.times


    @property
    def get_moneys(self):
        """
        This propert-method will extract all  money based token/tokens from the sentence using spaCy.
            e.g. (e.g. $2 million)

        Retunrs:
            moneys (list): this list will contain money based token or combination of tokens.
                If there no such token, an empty list will be returned.
        """
        self.moneys = []
        for ent in self.doc.ents:
            if ent.label_ == 'MONEY':
                self.moneys.append(ent.text)
        return self.moneys


    @property
    def get_pos(self):
        """
        This method will return `POS` tag of each token

        Returns:
            dictionary (dict): a dictionary
        """
        temp_dict = {
            tok.i: {
                'token': tok.text,
                'pos': tok.pos_
            } for tok in self.doc
        }

        return temp_dict


    @property
    def get_tag(self):
        """
        This method will return `tag_` of each token

        Returns:
            dictionary (dict): a dictionary
        """
        temp_dict = {
            tok.i: {
                'token': tok.text,
                'tag': tok.tag_
            } for tok in self.doc
        }
        return temp_dict


    @property
    def get_dep(self):
        """
        This method will return the `dep_` of each tokens

        Returns:
            dictionary (dict): a dictionary
        """
        temp_dict = {
            tok.i: {
                'token': tok.text,
                'dep': tok.dep_
            } for tok in self.doc
        }
        return temp_dict


    @property
    def get_lemma(self):
        """
        This method will return the lemma form (i.e. root) of each token.

        Return:
            dictionary (dict): a dictionary
        """
        temp_dict = {
            tok.i: {
                'token': tok.text,
                'lemma': tok.lemma_
            } for tok in self.doc
        }
        return temp_dict


    @property
    def get_is_alpha(self):
        """
        This method will return whether tokens of sentence are alpha numeric or not

        Return:
            dictionary (dict):
        """
        temp_dict = {
            tok.i: {
                'token': tok.text,
                'alpha': tok.is_alpha
            } for tok in self.doc
        }
        return temp_dict


    @property
    def get_morph(self):
        """
        This method will return the morpholody of each token

        Retunr:
            dictionary (dict):
        """
        temp_dict = {
            tok.i: {
                'token': tok.text,
                'morph': tok.morph.to_dict()
            } for tok in self.doc
        }
        return temp_dict


    @property
    def get_is_stop(self):
        """
        This method will return whether the token is stop-word or not

        Return:
            dictionary (dict):
        """
        temp_dict = {
            tok.i: {
                'token': tok.text,
                'stop': tok.is_stop
            } for tok in self.doc
        }
        return temp_dict

    @property
    def get_urls(self):
        """
        this method will find all URLs from the sentence.

        Returns:
            urls (list): list of all urls
        """
        urls = []
        for tok in self.doc:
            if tok.like_url:
                urls.append(tok.text)
        return urls


    def get_all_tags(self, tags = ['token', 'pos', 'tag', 'dep', 'lemma', 'morph', 'is_alpha', 'is_stop']):
        """
        This method will return all important tags of token labeled by spaCy's model

        Args:
            tags (list): This list contain important tags labeled by spacy.
                by default, these tags will be returned ('token', 'pos', 'tag', 'dep', 'lemma', 'morph', 'is_alpha', 'is_stop')
                Number of tags can be but it will always have 'token` tag
        Returns:
            dictionary (dict): a dictionary
        """
        mapping_dict = {
            'token': lambda x: x.text,
            'pos': lambda x: x.pos_,
            'tag': lambda x: x.tag_,
            'dep': lambda x: x.dep_,
            'lemma': lambda x: x.lemma_,
            'morph': lambda x: x.morph.to_dict(),
            'is_alpha': lambda x: x.is_alpha,
            'is_stop': lambda x: x.is_stop
        }

        temp_dict = dict()

        for tok in self.doc:
            temp_dict[tok.i] = dict()
            for tag in tags:
                temp_dict[tok.i][tag] = mapping_dict[tag](tok)
        return temp_dict


    def get_matched_string(self, pattern, pattern_name):
        """
        This method matches the given pattern and returns the matched string.

        Args:
            pattern (list): It is list of lists where each list is list of dictionary/dictionaries.
                e.g.
                pattern = [
                    [
                        {"LOWER": "hello"},
                        {"IS_PUNCT": True},
                        {"LOWER": "world"}
                    ],
                    [
                        {"LOWER": "hello"},
                        {"LOWER": "world"}
                    ]
                ]

                    - each pattern is list of dictionary/dictionaries
                    - each dictionary represents the propery of a token. If all properties are matched then it will be considered as Match
                    otherwise it will not be considered as Match.
                    - `key` of dictionary is attribute of spaCy's Token (e.g. POS, LEMMA, LOWER, TEXT, etc.)
                        refer to this page to know more (https://spacy.io/usage/rule-based-matching#adding-patterns-attributes)
                    - `value` of dictionary will depend on Token attribute that you will choose and what you want to match

                for more details, refer to this page: https://spacy.io/usage/rule-based-matching

                >>>matcher=Matcher(nlp.vocab)
                >>>matcher.add('PatternName', pattern)

        pattern_name (str): pattern name that user want to extract.
                NOTE: This `pattern_name` will be updated in `nlp.vocab` and it can be accessed using its hash-key.

        Returns:
            is_matched (boolean): True if there is match else it will be False
            matched_strings_list (list): list will contain all matched string in the sentence. If there is no match it will be an empty list
        """
        is_matched = False
        matched_strings_list = []

        matcher = Matcher(self.nlp.vocab)
        matcher.add(pattern_name, pattern)
        matches = matcher(self.doc)
        if len(matches) > 0:
            is_matched = True
            for match_id, start, end in matches:
                match_type = self.nlp.vocab[match_id]
                matched_strings_list.append(self.doc[start:end])
        return is_matched, matched_strings_list


    def get_all_tokens(self):
        """
        Returns:
            dictionary: function retunrs a dictionary where keys are index of token and values are the token as text
                --- (spaCy tokenizer)
        """
        return {token.i: token.text for token in self.doc}


class MatchEmail(ProcessText):
    def __init__(self, input_statement, nlp):
        super().__init__(input_statement, nlp)
        self.emails = []

    @property
    def email(self):
        """
        This function returns all email/emails in the sentence.

        Returns:
            is_email (boolian): True if there is atleast one match else it will be False
            emails (list): this list will contains all email in the string
                if there is no match it will be an empty list
        """
        is_email = False

        for token in self.doc:
            if token.like_enail:
                is_email = True
                self.emails.append(token)
        return is_email, self.emails


class MatchEmailUsingPattern(ProcessText):
    def __init__(self, input_statement, nlp):
        super().__init__(input_statement=input_statement, nlp=nlp)
        self.emails = None

    def email(self, pattern):
        """
        This function returns all email/emails in the sentence.

        Args:
            pattern (list): list of lists/list where each list is list of dictionaries/dictionary.
                (see method of parent class to know in detail)

        Returns:
            is_email (boolian): True if there is atleast one match else it will be False
            emails (list): this list will contains all email in the string
                if there is no match it will be an empty list
        """
        is_eamil, self.emails = self.get_matched_string(pattern=pattern, pattern_name="EMAIL")
        return is_eamil, self.emails


class MatchPhoneNumber(ProcessText):
    def __init__(self, input_statement, nlp):
        super().__init__(input_statement=input_statement, nlp=nlp)
        self.phone_numbers = []

    def phone_number(self, pattern):
        """
        This function checks whether pattern matches or not.

        Args:
            pattern (list): list of lists where each list is list of dictionaries/dictionary.
                (see the method of parent class to know in detail.)

        Retunrs:
            is_phone (boolean): True if there is atleast one match else it will be False
            phone_numbers (list): this list contains the matched phone number in the given text.
                If there is no match, retunred list will be empty (i.e. [])
        """
        is_phone, self.phone_numbers = self.get_matched_string(pattern=pattern, pattern_name="PHONE")
        return is_phone, self.phone_numbers


class Intent:
    """
    This class will find the pattern based intents that can be found.
    """
    def __init__(self):
        pass

    def match(self, processed_text, pattern_name):
        """
        This method finds the matched string for a given pattern.

        Args:
            processed_text (object): user-defined object (`ProcessText`)
            pattern_name (str): name of the pattern (i.e. Intent name)

        Returns:
            dictionary (dict): A dictionary
        """
        is_match, matched_string = processed_text.get_matched_string(pattern=self.pattern, pattern_name=pattern_name)
        if is_match:
            return {'data': [i.text for i in matched_string]}
        return dict()


class BookIntent(Intent):
    """
    Class to find the the `Book` intent. (e.g. Book my ticket)

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class CheckIntent(Intent):
    """
    This class will help in finding the `Check` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class ContactIntent(Intent):
    """
    This class will help in finidng the `Contact` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class CreateIntent(Intent):
    """
    This class will help in fimding the `Create` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class DeleteIntent(Intent):
    """
    This class will help in finding the `Delete` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class DeliveryIntent(Intent):
    """
    This class will help in finding the `Delivery` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class DesireIntent(Intent):
    """
    This class will help in finding the `Desire` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class GreetIntent(Intent):
    """
    This class will help in finding the `Greet` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class OrderIntent(Intent):
    """
    This class will in finding the `Order` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class PurchaseIntent(Intent):
    """
    This class help in finding the `Purchase` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class NewsIntent(Intent):
    """
    This class will help in finding the `News` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class RateIntent(Intent):
    """
    This class will help in finding hte `Rate` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class RemindIntent(Intent):
    """
    This class will help in finding the `Remind` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class RentIntent(Intent):
    """
    This class wil help in finding the `Rent` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class SearchIntent(Intent):
    """
    This class will help in finidng the `Search` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class SetIntent(Intent):
    """
    This class will help in finding the `Set` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class UpdateIntent(Intent):
    """
    This class will help in finding the `Update` intent.

    Args:
        pattern (list): This list contain lists/list which have/has the pattern/patterns for matching in sentence
    """
    def __init__(self, pattern):
        self.pattern = pattern


class AddTaskIntent(Intent):
    """
    This class will find whether a `AddTask` intent exist or not.
    """
    def __init__(self, pattern):
        self.pattern = pattern


class LinkTaskIntent(Intent):
    """
    This class will find whether the sentence has `LinkTaskIntent` or not.
    """
    def __init__(self, pattern):
        self.pattern = pattern


class SetDeadlineIntent(Intent):
    """
    This class will help to find out the `SetDeadline` intent in the given sentence.
    """
    def __init__(self, pattern):
        self.pattern = pattern


class TokenSimilairt:
    """
    This class will find the similarity between two token using spaCy's model.

    Attributes:
        nlp (object): spaCy's loaded model (NOTE: use medium or large model, i.e model that has the vectors of token)
    """
    def __init__(self, nlp):
        self.nlp = nlp

    def get_(self, token1, token2):
        """
        This method will find the token similarity.

        Args:
            token1 (str): token or word
            token2 (str): token or word

        Returns:
            similarity (int): cosine similarity between given two tokens
        """
        token1 = self.nlp(token1)
        token2 = self.nlp(token2)
        return token1.similarity(token2)


class SentenceSimilarity:
    """
    This class will find the similarity between two sentences using spaCy's trained model. But it will required either medium or large model.

    Attributes:
        nlp (object): spaCy's model (medium or large model)
            >>>nlp = spacy.load('en_core_web_md') # medium model
            >>>nlp = spacy.load('en_core_web_lg') # large model
    """
    def __init__(self, nlp):
        self.nlp = nlp

    def get(self, sentence1, sentence2):
        """
        This methos will find the similarity between given two sentences.

        Args:
            sentence1 (str): first sentence
            sentence2 (str): second sentence
        """
        doc1 = self.nlp(sentence1)
        doc2 = self.nlp(sentence2)
        similarity = doc1.similarity(doc2)
        return similarity
