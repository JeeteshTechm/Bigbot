import json

class AvailiableSkills:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path

    def get_skill_names(self):
        with open(self.json_file_path, 'r') as file:
            data = json.load(file)
            intents = data["intents"]
            intent_names = [intent["name"] for intent in intents]
            return intent_names

json_file_path = "input/skills.json"
reader = AvailiableSkills(json_file_path)
intent_names = reader.get_skill_names()
print(intent_names)
