from main.Component import OAuthProvider,SkillProvider
from main.Statement import OutputStatement
from requests_oauthlib import OAuth2Session
from django.template import Context, Template
from requests_oauthlib import OAuth2Session
import requests
from jose import jws as jose_jws
import json
import math
from django.conf import settings as django_settings
import datetime
from urllib import parse as urlparse
from core.models import OAuthTokenModel

from .node import Expandable
from .utils import number_to_ordinal
from typing import List, Text

import spacy

from algoliasearch.search_client import SearchClient

en_spacy = spacy.load("en_core_web_md")
STOPWORDS = spacy.lang.en.stop_words.STOP_WORDS.union({"need", "want", "help", "able", "unable", "know", "use"})

def preprocess_search_text(search_text: Text) -> Text:
    tokens = en_spacy(search_text.lower())
    return " ".join([w.text for w in tokens if w.text not in STOPWORDS and not w.is_punct])

class AlgoliaAPI:
    def __init__(self, app_id: Text, search_key: Text, index: Text):
        self.client = SearchClient.create(app_id, search_key)
        self.index = self.client.init_index(index)

    def get_algolia_link(self, hits: List, index: int) -> Text:
        hierarchy = hits[index].get("hierarchy")
        lvl0 = hierarchy.get("lvl0")
        lvl1 = hierarchy.get("lvl1", "").strip()
        lvl2 = hierarchy.get("lvl2", "").strip()
        doc_link = f"- [{lvl0}/{lvl1}/{lvl2}]({hits[index].get('url')})"
        return doc_link

    def search(self, search_string: Text):
        search_text = preprocess_search_text(search_string)
        res = self.index.search(search_text)
        return res
