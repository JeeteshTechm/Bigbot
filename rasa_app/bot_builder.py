import json
import os
import yaml
import rasa
from rasa.shared.nlu.training_data.loading import load_data
from rasa.shared.nlu.training_data.message import Message
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


def generate_domain_file(payload,bot_id):
    domain = {}
    domain['version'] = '3.4.4'
    intents = [{'name': intent['name']} for intent in payload['intents']]
    domain['intents'] = intents
    entities = [{'name': entity['name']} for entity in payload['entities']]
    domain['entities'] = entities

    slots = {}
    for slot in payload['slots']:
        slot_name = slot['name']
        slot_type = slot['type']
        slots[slot_name] = {'type': slot_type, 'influence_conversation': False}
        mappings = []
        for value in slot.get('values', []):
            mappings.append({'value': value, 'synonyms': [value]})
        if mappings:
            slots[slot_name]['mappings'] = mappings
    domain['slots'] = slots

    responses = {}
    for intent in payload['intents']:
        for response_idx, response_text in enumerate(intent['responses']):
            response_key = f'utter_{intent["name"]}_{response_idx}'
            responses[response_key] = [{'text': response_text}]
    domain['responses'] = responses

    actions = [{'name': f'action_{intent["name"]}', 'type': 'response'} for intent in payload['intents']]
    domain['actions'] = actions

    session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
    domain['session_config'] = session_config

    domain_file_path = f"{bot_id}/domain.yml"
    with open(domain_file_path, "w") as f:
        yaml.dump(domain_file_path, f, sort_keys=False)

    return ('Domain saved to given path')


def generate_config_file(payload, bot_id):
    config_yaml_data = {
        "recipe": payload.get("recipe", "default.v1"),
        "language": payload.get("language", "en"),
        "pipeline": payload.get("pipeline", []),
        "policies": payload.get("policies", [])
    }

    config_file_path = f"{bot_id}/config.yml"
    with open(config_file_path, "w") as f:
        yaml.dump(config_yaml_data, f, sort_keys=False)

    return ('Domain saved to given path')


def generate_nlu_file(data, bot_id):
    nlu_data = {'version': '3.4.4'}
    nlu_data['nlu'] = []

    # Loop through the intents in the payload data
    for intent in data['intents']:
        # If the intent has utterances, create a NLU example
        if intent['utterances']:
            nlu_example = {
                'intent': intent['name'],
                'examples': []
            }
            # Add the examples for the intent
            for utterance in intent['utterances']:
                example = {'text': utterance}
                if intent.get('slots'):
                    entities = []
                    for slot in intent['slots']:
                        slot_value = f"{{{slot['name']}}}"
                        if slot_value in utterance:
                            entity_start = utterance.index(slot_value)
                            entity_end = entity_start + len(slot_value) - 1
                            entities.append({'start': entity_start, 'end': entity_end, 'value': slot_value, 'entity': slot['name']})
                    if entities:
                        example['entities'] = entities
                nlu_example['examples'].append(example)
            nlu_data['nlu'].append(nlu_example)

    # Save the NLU data to file
    nlu_file_path = os.path.join(bot_id, 'data', 'nlu.yml')
    with open(nlu_file_path, 'w') as f:
        yaml.dump(nlu_data, f)
        
    return nlu_data


def generate_stories_file(payload, bot_id):
    # Create the directory if it doesn't exist
    data_dir = f"{bot_id}/data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Generate stories
    stories = []
    for story in payload['stories']:
        steps = []
        for step in story['steps']:
            if 'intent' in step:
                steps.append({'intent': step['intent']})
            elif 'action' in step:
                steps.append({'action': step['action']})
            elif 'entities' in step:
                entities = {}
                for entity, value in step['entities'].items():
                    entities[entity] = value['value']
                steps.append({'entities': entities})
        stories.append({'story': story['story'], 'steps': steps})

    # Convert stories dictionary to YAML format
    stories_yaml = yaml.dump({'stories': stories}, sort_keys=False)

    # Write the YAML to a file
    with open(f"{data_dir}/stories.yml", 'w') as file:
        file.write(stories_yaml)

    return stories_yaml

def generate_rules_file(payload, bot_id):
    rules = {}

    # Generate rules from the rules block
    for rule in payload['rules']:
        rule_name = rule['rule']
        steps = []

        for step in rule['steps']:
            if 'intent' in step:
                steps.append({'intent': step['intent']})
            elif 'action' in step:
                steps.append({'action': step['action']})
            elif 'entities' in step:
                entities = {}
                for entity, value in step['entities'].items():
                    entities[entity] = {'value': value['value']}
                steps.append({'entities': entities})

        rules[rule_name] = {'steps': steps}

    # Generate rules from intents
    for intent in payload['intents']:
        rule_name = f"{intent['name']}_rule"
        steps = [
            {'intent': intent['name']},
            {'action': f"utter_{intent['name']}"}
        ]
        rules[rule_name] = {'steps': steps}

    # Convert rules dictionary to YAML format
    rules_yaml = yaml.dump({'rules': rules}, sort_keys=False)

    # Save rules.yaml to bot_id/data/rules.yaml
    if not os.path.exists(f"{bot_id}/data"):
        os.makedirs(f"{bot_id}/data")
    with open(f"{bot_id}/data/rules.yml", "w") as f:
        f.write(rules_yaml)

    return rules_yaml


def create_rasa_model(payload_data,config_data,bot_id):
    os.makedirs(bot_id)
    generate_domain_file(payload_data,bot_id)
    generate_config_file(config_data,bot_id)
    generate_nlu_file(payload_data,bot_id)
    generate_stories_file(payload_data,bot_id)
    generate_rules_file(payload_data,bot_id)


    config = f"{bot_id}/config.yml"
    training_files = f"{bot_id}/data/"
    domain = f"{bot_id}/domain.yml"
    output = f"{bot_id}/models/"

    rasa.train(domain, config, [training_files], output, fixed_model_name='rasa_model')  


    return("Your Rasa model has been trained and saved")
