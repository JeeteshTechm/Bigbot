import json
import os
import yaml
import rasa
from transformers import *

model = PegasusForConditionalGeneration.from_pretrained("tuner007/pegasus_paraphrase")
tokenizer = PegasusTokenizerFast.from_pretrained("tuner007/pegasus_paraphrase")

#Generate training data from blocks
def get_rasa_training_data(file_path):
    with open(file_path, 'r') as f:
        skill_builder_json = json.load(f)

    rasa_training_data = {"intents": []}
    current_intent = None

    for i, block in enumerate(skill_builder_json['blocks']):
        if block['component'] == 'main.Block.InputText':
            tags = block.get('tags', [])
            current_intent = {
                'tag': '_'.join(tags),
                'utterances': [],
                'responses': []
            }

            for prop in block['properties']:
                if prop['name'] == 'value':
                    current_intent['utterances'].append(prop['value'])

            # Check if the next block is a PromptText block
            if i + 1 < len(skill_builder_json['blocks']):
                next_block = skill_builder_json['blocks'][i + 1]
                if next_block['component'] == 'main.Block.PromptText':
                    for prop in next_block['properties']:
                        if prop['name'] == 'value':
                            current_intent['responses'].append(prop['value'])
                            break

            rasa_training_data['intents'].append(current_intent)
            current_intent = None

    return rasa_training_data


# Generate similar sentences for text
def get_paraphrased_sentences(model, tokenizer, sentence, num_return_sequences=5, num_beams=5):

    inputs = tokenizer([sentence], truncation=True, padding="longest", return_tensors="pt")
    outputs = model.generate(
        **inputs,
        num_beams=num_beams,
        num_return_sequences=num_return_sequences,
    )

    return tokenizer.batch_decode(outputs, skip_special_tokens=True)


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
