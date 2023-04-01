import json
import yaml

def generate_domain_file(training_data, bot_id):
    domain = {}
    domain['version'] = '3.4.4'

    intents = [{'name': intent['name']} for intent in training_data['intents']]
    domain['intents'] = intents

    entities = [{'name': entity['name'], 'values': entity.get('values', [])} for entity in training_data['entities']]
    domain['entities'] = entities

    session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
    domain['session_config'] = session_config

    responses = {}
    for intent in training_data['intents']:
        for response_idx, response_text in enumerate(intent['responses']):
            response_key = f'utter_{intent["name"]}_{response_idx}'
            responses[response_key] = [{'text': response_text}]
    domain['responses'] = responses

    actions = [{'name': f'action_{intent["name"]}', 'type': 'response'} for intent in training_data['intents']]
    domain['actions'] = actions

    session_config = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
    domain['session_config'] = session_config

    domain_file_path = f"{bot_id}/domain.yml"

    with open(domain_file_path, "w") as f:
        yaml.dump(domain, f)

    return ('Domain saved to given path')


with open("payload3.json", 'r') as f:
    skill_builder_json = json.load(f)
print(generate_domain_file(skill_builder_json, "123"))


