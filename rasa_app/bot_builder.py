import json
import os
import yaml
import rasa
from rasa.shared.nlu.training_data.training_data import TrainingData
from rasa.shared.core.domain import Domain
from rasa.shared.nlu.training_data.loading import load_data
from rasa.core.utils import  EndpointConfig
from rasa.shared.core.training_data.structures import StoryGraph
from rasa.shared.core.generator import TrainingDataGenerator
from rasa.shared.core.events import ActionExecuted, UserUttered
from rasa.core.agent import Agent
from rasa.shared.nlu.interpreter import RegexInterpreter
from rasa.core.policies.memoization import MemoizationPolicy
from rasa.core.policies.rule_policy import RulePolicy
from rasa.core.policies.ted_policy import TEDPolicy


def create_bot(bot_id, payload):
    if not os.path.exists(bot_id):
        os.makedirs(bot_id)

    # Define the YAML structure for domain.yml
    domain_yaml_data = {
        "intents": [],
        "entities": {},
        "slots": {},
        "responses": {},
        "actions": {},
        "forms": {}
    }

    # Define the YAML structure for config.yml
    config_yaml_data = {
        "language": "en",
        "pipeline": [
            {
                "name": "WhitespaceTokenizer"
            },
            {
                "name": "RegexFeaturizer"
            },
            {
                "name": "CRFEntityExtractor"
            },
            {
                "name": "EntitySynonymMapper"
            },
            {
                "name": "CountVectorsFeaturizer"
            },
            {
                "name": "EmbeddingIntentClassifier",
                "epochs": 100
            }
        ]
    }

    # Define the YAML structure for data.yml
    data_yaml_data = {
        "version": "3.4.4",
        "nlu": [],
        "stories": [],
        "rules": []
    }

    # Generate the NLU section of the YAML
    for intent, data in payload["intents"].items():
        examples = "\n    - ".join(data["examples"])
        nlu_section = {
            "intent": intent,
            "examples": f"|\n    - {examples}"
        }
        data_yaml_data["nlu"].append(nlu_section)
        domain_yaml_data["intents"].append(intent)

    # Generate the entity section of the YAML
    for entity in payload["entities"]:
        domain_yaml_data["entities"][entity] = {}

    # Generate the slot section of the YAML
    for slot, data in payload["slots"].items():
        slot_section = {
            slot: {
                "type": data["type"]
            }
        }
        if "initial_value" in data:
            slot_section[slot]["initial_value"] = data["initial_value"]
        domain_yaml_data["slots"].update(slot_section)

    # Generate the rules section of the YAML
    for entity in payload["entities"]:
        rule_section = {
            "rule": f"Extract {entity} entity",
            "steps": [
                {
                    "intent": "",
                    "action": f"utter_ask_{entity}"
                },
                {
                    "intent": f"{entity}",
                    "action": f"utter_thanks_{entity}"
                }
            ]
        }
        data_yaml_data["rules"].append(rule_section)

    # Generate the YAML file for domain.yml
    domain_file_path = f"{bot_id}/domain.yml"
    with open(domain_file_path, "w") as f:
        yaml.dump(domain_yaml_data, f, sort_keys=False)

    # Generate the YAML file for config.yml
    config_file_path = f"{bot_id}/config.yml"
    with open(config_file_path, "w") as f:
        yaml.dump(config_yaml_data, f, sort_keys=False)

    # Generate the YAML file for data.yml
    data_file_path = f"{bot_id}/data.yml"
    with open(data_file_path, "w") as f:
        yaml.dump(data_yaml_data, f, sort_keys=False)
    

   # Train your Rasa model
    model_directory = rasa.train(domain=domain_file,
                             config=config,
                             training_data=training_data,
                             output=os.path.join(project_directory, f"{bot_id}/models"),
                             fixed_model_name=bot_id)

    return (f"Your Rasa model has been trained and saved ")



















