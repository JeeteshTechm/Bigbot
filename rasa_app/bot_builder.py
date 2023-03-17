import json
import os
import yaml
import rasa

#Generate training data from blocks
def convert_flow_to_training_data(flow):

    ### This function should generate a specific format of training_data,then only remaining functions work ###

    training_data = {"common_examples": []}
    for block in flow.blocks:

        tags = block.tags
        properties = block.properties
        intent_label = "_".join(tags)
        entity_label = " ".join([f"{key}:{value}" for key, value in properties.items()])

        input_example = block.input_property
        output_example = block.output_property

        training_data["common_examples"].append({"text": input_example, "intent": intent_label, "entities": [{"start": 0, "end": len(entity_label), "value": entity_label, "entity": "property"}]})
        training_data["common_examples"].append({"text": output_example, "intent": intent_label, "entities": [{"start": 0, "end": len(entity_label), "value": entity_label, "entity": "property"}]})

    return training_data

def utterance_generator(training_data):

    #### Needs implementation ###

    return updated_training_data

#Creates domain.yml file for the given training data
def generate_domain_file(training_data,bot_id):
    domain = {}
    domain['version'] = '3.4.4'

    intents = [{'name': intent['name']} for intent in training_data['intents']]
    domain['intents'] = intents

    entities = [{'name': entity['name']} for entity in training_data['entities']]
    domain['entities'] = entities

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

#Creates nlu.yml file for the given training data
def generate_nlu_file(data, bot_id):
    nlu_data = {'version': '3.4.4'}
    nlu_data['nlu'] = []

    for intent in data['intents']:
        if intent['utterances']:
            nlu_example = {
                'intent': intent['name'],
                'examples': []
            }
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

    nlu_file_path = os.path.join(bot_id, 'data', 'nlu.yml')
    with open(nlu_file_path, 'w') as f:
        yaml.dump(nlu_data, f)
        
    return nlu_data

#Creates stories.yml file for the given training data
def generate_stories_file(payload, bot_id):
    data_dir = f"{bot_id}/data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    stories = []
    
    #### Needs implementation ####

    stories_yaml = yaml.dump({'stories': stories}, sort_keys=False)
    with open(f"{data_dir}/stories.yml", 'w') as file:
        file.write(stories_yaml)

    return stories_yaml


# Train and save the rasa model for the training data
def train_save_rasa_model(training_data,config_file_path,bot_id):
    os.makedirs(bot_id)
    generate_domain_file(training_data,bot_id)
    generate_nlu_file(training_data,bot_id)
    generate_stories_file(training_data,bot_id)
    shutil.copy(config_file_path, f"{bot_id}/config.yml")

    config = f"{bot_id}/config.yml"
    training_files = f"{bot_id}/data/"
    domain = f"{bot_id}/domain.yml"
    output = f"{bot_id}/models/"

    rasa.train(domain, config, [training_files], output, fixed_model_name='rasa_model')  

    return("Your Rasa model has been trained and saved")


##Load the training model as interpreter to get the response for the user query
def get_response(text,bot_id):

  ### Needs Implementation ###

    return reponse

