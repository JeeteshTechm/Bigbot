import json
import yaml
import rasa
import os
from transformers import *

class DataPreprocessor:
    def __init__(self):
        self.model = PegasusForConditionalGeneration.from_pretrained("tuner007/pegasus_paraphrase")
        self.tokenizer = PegasusTokenizerFast.from_pretrained("tuner007/pegasus_paraphrase")

    # Generate similar sentences for user prompt text
    def get_paraphrased_sentences(self, sentence, num_return_sequences=5, num_beams=5):
        inputs = self.tokenizer([sentence], truncation=True, padding="longest", return_tensors="pt")
        outputs = self.model.generate(
            **inputs,
            num_beams=num_beams,
            num_return_sequences=num_return_sequences,
        )

        return self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

    #Generate training data from blocks
    def get_rasa_training_data(self, file_path):
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

    #Update training data with more examples
    def update_training_data_with_utterances(self, rasa_training_data):
        for intent in rasa_training_data["intents"]:
            tag = intent["tag"]
            utterances = intent["utterances"]
            new_utterances = self.get_paraphrased_sentences(utterances)
            intent["utterances"] = utterances + new_utterances

        return rasa_training_data


class RasaFileGenerator:

    def __init__(self, bot_id):
        self.bot_id = bot_id
    
    def generate_domain_file(self, training_data, bot_id):
        domain = {}
        domain['version'] = '3.4.4'

        intents = [{'name': intent['name']} for intent in training_data['intents']]
        domain['intents'] = intents

        entities = [{'name': entity['name']} for entity in training_data['entities']]
        domain['entities'] = entities

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
            yaml.dump(domain, f, sort_keys=False)

        return ('Domain saved to given path')

    def generate_nlu_file(self, data, bot_id):
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

    def generate_stories_file(self, payload, bot_id):
        data_dir = f"{bot_id}/data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        stories = []

        #### Needs implementation ####

        stories_yaml = yaml.dump({'stories': stories}, sort_keys=False)
        with open(f"{data_dir}/stories.yml", 'w') as file:
            file.write(stories_yaml)

        return stories_yaml

class RasaModelTrainer:
    def __init__(self, skill_builder_file_path, config_file_path, bot_id):
        self.skill_builder_file_path = skill_builder_file_path
        self.config_file_path = config_file_path
        self.bot_id = bot_id
        self.data_preprocessor = DataPreprocessor() 
        self.rasa_file_generator = RasaFileGenerator()

    def train_and_save_model(self):
        rasa_training_data = self.data_preprocessor.get_rasa_training_data(self.skill_builder_file_path)

        updated_training_data = self.data_preprocessor.update_training_data_with_utterances(self.rasa_training_data)

        os.makedirs(self.bot_id)

        self.rasa_file_generator.generate_domain_file(self.updated_training_data, self.bot_id)
        self.rasa_file_generator.generate_nlu_file(self.updated_training_data, self.bot_id)
        self.rasa_file_generator.generate_stories_file(self.updated_training_data, self.bot_id)
        shutil.copy(self.config_file_path, f"{self.bot_id}/config.yml")

        config = f"{self.bot_id}/config.yml"
        training_files = f"{self.bot_id}/data/"
        domain = f"{self.bot_id}/domain.yml"
        output = f"{self.bot_id}/models/"

        rasa.train(domain, config, [training_files], output, fixed_model_name='rasa_model')

        return("Your Rasa model has been trained and saved")
