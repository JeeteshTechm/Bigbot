from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction

class ActionExample(Action):
    def name(self) -> Text:
        return "action_example"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
      
        # Your custom action logic here
      
        response = "This is an example response from the custom action."
        dispatcher.utter_message(response)
        return []
