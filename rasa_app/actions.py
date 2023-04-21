from typing import Dict, Text, Any, List, Union

from rasa_sdk import Tracker,Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
import requests
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet
import json


class ValidaterestaurantForm(Action):

    def name(self) -> Text:
        return "validate_restaurant_form"

    
    def validate_cuisine(self, value: Text, dispatcher: CollectingDispatcher,
                            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        """Validate cuisine value."""

        if value:
            return { "cuisine": value }
        else:
            dispatcher.utter_message(response="utter_ask_cuisine")
            # validation failed, set this slot to None, meaning the
            # user will be asked for the slot again
            return { "cuisine": None }
            

    def validate_num_people(self, value: Text, dispatcher: CollectingDispatcher,
                            tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        """Validate num_people value."""

        if value:
            return { "num_people": value }
        else:
            dispatcher.utter_message(response="utter_ask_num_people")
            # validation failed, set this slot to None, meaning the
            # user will be asked for the slot again
            return { "num_people": None }
            

    
        

class SubmitrestaurantForm(Action):

    def name(self) -> Text:
        return "submit_restaurant_form"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:

        cuisine = tracker.get_slot("cuisine")
        num_people = tracker.get_slot("num_people")

        slots=['cuisine', 'num_people']
        url = "https://postman-echo.com/get?foo1=bar1&foo2=bar2"

        payload={}
        headers = {
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        res=json.loads(response.text)
        dispatcher.utter_message(res)
    
        return [SlotSet("cuisine", None),SlotSet("num_people", None),]
    

    
