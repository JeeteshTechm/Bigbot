import json

class JsonUpdater:
    def __init__(self, json_data):
        self.json_data = json_data

    def convert_to_string(self, value):
        return str(value)

    def add_empty_keys(self, slot):
        slot.setdefault("name", "")
        slot.setdefault("type", "")
        slot.setdefault("examples", [])
        slot.setdefault("bot_ask", "")
        return slot

    def validate_and_update_slot(self, slot):
        slot = self.add_empty_keys(slot)
        slot["name"] = self.convert_to_string(slot["name"])
        slot["type"] = self.convert_to_string(slot["type"])
        slot["bot_ask"] = self.convert_to_string(slot["bot_ask"])
        slot["examples"] = [self.convert_to_string(e) for e in slot["examples"]]
        return slot

    def append_intent_name_to_form(self, intent):
        if "form" in intent and intent["form"]:
            intent_name = intent.get("intent")
            if intent_name:
                intent["form"] = f"{intent_name}_{intent['form']}"
        return intent

    def validate_and_update_intent(self, intent):
        intent = self.append_intent_name_to_form(intent)
        if "response" not in intent:
            intent["response"] = ""
        if "utterances" not in intent:
            intent["utterances"] = []

        if "form" in intent and intent["form"]:
            if "slots" in intent:
                intent["slots"] = [self.validate_and_update_slot(slot) for slot in intent["slots"]]
        return intent

    def update_intents(self):
        updated_intents = [self.validate_and_update_intent(intent) for intent in self.json_data["intents"]]
        updated_data = {
            "bot_id": self.json_data.get("bot_id"),
            "intents": updated_intents
        }
        return updated_data


# Example usage
with open("input/flight_booking.json", 'r') as file:
        json_data = json.load(file)


updater = JsonUpdater(json_data)
updated_data = updater.update_intents()

# Print the updated JSON object
print(json.dumps(updated_data, indent=4))
