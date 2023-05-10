import os
import json
import yaml
import ast
import requests
import shutil
from rasa_sdk import Action
from ruamel.yaml import YAML
from collections import OrderedDict
import re
from typing import List
import rasa
import subprocess


class NluGenerator:

    def __init__(self, skill_id, payload):
        self.skill_id = skill_id
        self.payload = payload

    def create_rasa_folder_structure(self):
        skill_path = f"./{self.skill_id}"
        self.payload_path = f"{skill_path}/data"

        try:
            os.mkdir(skill_path)
        except FileExistsError:
            print(f"Folder {skill_path} already exists")
        else:
            print(f"Folder {skill_path} created")
         
        try:
            os.mkdir(self.payload_path)
        except FileExistsError:
            print(f"Folder {self.payload_path} already exists")
        else:
            print(f"Folder {self.payload_path} created")

         
    def nlu_yml(self):
            nlu_file = os.path.join(self.skill_id, "data", "nlu.yml")
            intents = self.payload["intents"]
            yaml_output = "version: '3.1'\n"
            yaml_output += "nlu:\n"
            for intent in intents:
                    yaml_output += f"  - intent: {intent['name']}\n"
                    yaml_output += "    examples: |\n"
                    for example in intent['utterances']:
                        yaml_output += f"      - {example}\n"

            with open(nlu_file, "w") as yaml_file:
                yaml_file.write(yaml_output)

            return f"Combined YAML file generated and saved in {nlu_file}"

    def upload_config_file(self, config_file_path):
        shutil.copyfile(config_file_path, os.path.join(self.skill_id, 'config.yml'))
        return "Config file uploaded successfully"

    def train_and_save_model(bot_id):
        config = f"{bot_id}/config.yml"
        training_files = f"{bot_id}/data/"
        output = f"{bot_id}/models/"

        command = f"rasa train nlu --nlu delegate/data/nlu.yml"
        subprocess.run(command, shell=True)

        return "Your Rasa model has been trained and saved"



# read the JSON payload
with open("skills.json", "r") as f:
    payload = json.load(f)

skill_id= "delegate"
rasa_project = NluGenerator(skill_id, payload)

rasa_project.create_rasa_folder_structure()
rasa_project.nlu_yml()
rasa_project.upload_config_file("config.yml")
rasa_project.train_and_save_model()