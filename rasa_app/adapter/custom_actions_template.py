from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction

class ActionDataExchange(Action):

    def name(self) -> Text:
        """Return the name of the action."""
        return "action_data_exchange"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """Execute the action and return the response."""

        # Retrieving input data from a slot (similar to the input data of DataExchange)
        input_data = tracker.get_slot("input_data")

        # Process this data (similar to the on_process method in DataExchange)
        processed_data = self.data_exchange_function(input_data)

        # Respond with a message after processing
        dispatcher.utter_message(f"Processed the data: {processed_data}")

        # Setting the processed data in an output slot
        return [SlotSet("output_data", processed_data)]

    def data_exchange_function(self, data):
        # Replace this with your actual processing logic
        return data + "_processed"

class ExampleForm(FormAction):

    def name(self) -> Text:
        """Return the name of the form."""
        return "example_form"

    @staticmethod
    def required_slots(tracker: Tracker) -> List[Text]:
        """List the required slots that the form has to fill."""
        return ["slot1", "slot2"]

    def slot_mappings(self) -> Dict[Text, Any]:
        """Define how to extract slot values from user inputs."""
        return {
            "slot1": self.from_text(),
            "slot2": self.from_text()
        }

    def submit(self, dispatcher: CollectingDispatcher,
               tracker: Tracker,
               domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """Define what the form has to do after all required slots are filled."""

        slot1_value = tracker.get_slot("slot1")
        slot2_value = tracker.get_slot("slot2")

        dispatcher.utter_message(f"Received the values: {slot1_value} and {slot2_value}")
        return []
