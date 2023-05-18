import os
import json
import uuid
import shutil
import subprocess
from typing import List


class NluGenerator:
    def __init__(self, skill_id: str, payload: List[dict]):
        self.skill_id = skill_id
        self.payload = payload

    def create_rasa_folder_structure(self) -> None:
        skill_path = f"./{self.skill_id}"
        self.payload_path = f"{skill_path}/data"
        self._create_folder(skill_path)
        self._create_folder(self.payload_path)

    def _create_folder(self, folder_path: str) -> None:
        try:
            os.mkdir(folder_path)
        except FileExistsError:
            print(f"Folder {folder_path} already exists")
        else:
            print(f"Folder {folder_path} created")

    def nlu_yml(self) -> str:
        nlu_file = os.path.join(self.skill_id, "data", "nlu.yml")
        yaml_output = "version: '3.1'\n"
        yaml_output += "nlu:\n"
        for item in self.payload:
            intent = item["name"]
            utterances = item["utterances"]
            yaml_output += f"  - intent: {intent}\n"
            yaml_output += "    examples: |\n"
            for example in utterances:
                yaml_output += f"      {example}\n"

        with open(nlu_file, "w") as yaml_file:
            yaml_file.write(yaml_output)

        return f"Combined YAML file generated and saved in {nlu_file}"

    def upload_config_file(self, config_file_path: str) -> str:
        shutil.copyfile(config_file_path, os.path.join(self.skill_id, 'config.yml'))
        return "Config file uploaded successfully"

    def train_and_save_model(self) -> str:
        config = f"{self.skill_id}/config.yml"
        training_files = f"{self.skill_id}/data/"
        output = f"{self.skill_id}/models/"

        command = f"rasa train nlu --nlu {training_files}nlu.yml --out {output}"
        subprocess.run(command, shell=True)

        return "Your Rasa model has been trained and saved"


def main():
    input_dir = 'output'
    input_files = os.listdir(input_dir)
    json_files = [f for f in input_files if f.endswith('.json')]

    skill_id_mapping = {}

    for file in json_files:
        with open(os.path.join(input_dir, file), "r") as f:
            payload = json.load(f)["intents"]

        skill_id = str(uuid.uuid4())
        skill_id_mapping[skill_id] = [intent['name'] for intent in payload]

        rasa_project = NluGenerator(skill_id, payload)

        rasa_project.create_rasa_folder_structure()
        rasa_project.nlu_yml()
        rasa_project.upload_config_file("path_to_your_rasa_config_file")  # replace with your rasa config file path
        rasa_project.train_and_save_model()

    # Write the skill_id_mapping to a JSON file
    with open('skill_id_mapping.json', 'w') as f:
        json.dump(skill_id_mapping, f)


if __name__ == "__main__":
    main()
