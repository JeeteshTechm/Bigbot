import os
import yaml
from flask import Flask, request, send_file
from flask_cors import CORS, cross_origin
import openai
import tempfile
from rasa3_to_bigbot_adapter import YAMLToJsonConverter
from datetime import date

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yml")
EXAMPLE_YAML = os.getenv("EXAMPLE_YAML", "yaml_shema.yml")
MODEL = os.getenv("MODEL", "gpt-3.5-turbo")

def read_yaml(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

config = read_yaml(CONFIG_PATH)
openai.api_key = config.get('endpoints', {}).get('api_url')

if not openai.api_key:
    raise ValueError("Missing OpenAI API key.")

example_yaml_data = read_yaml(EXAMPLE_YAML)
example_yaml_text = yaml.dump(example_yaml_data)

def get_completion(prompt):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=messages,
        temperature=0,
    )
    content = response.choices[0].message.get("content")
    if not content:
        raise ValueError("No content in response.")
    return content

def replace_in_structure(data, old_value, new_value):
    if isinstance(data, list):
        return [replace_in_structure(item, old_value, new_value) for item in data]
    elif isinstance(data, dict):
        return {k: replace_in_structure(v, old_value, new_value) for k, v in data.items()}
    elif isinstance(data, old_value):
        return new_value(data)
    return data

@app.route('/data_generator', methods=['POST'])
@cross_origin()
def chat():
    user_message = request.json['message']
    input_text = f"Craft a dialogue for this user-described scenario - {user_message}. The dialogue must contain multiple intents and adhere strictly to this YAML schema:\n{example_yaml_text}. Use slots, forms, actions and other fields where appropriate."
    response = get_completion(input_text)

    yaml_content = yaml.safe_load(response)
    yaml_content = replace_in_structure(yaml_content, date, date.isoformat)

    yaml_converter = YAMLToJsonConverter(yaml_content)
    json_data = yaml_converter.convert_to_json()

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
        temp_file.write(json_data.encode('utf-8'))

    temp_filename = temp_file.name
    response = send_file(temp_filename, mimetype='text/json')
    response.headers['Content-Disposition'] = 'attachment; filename=output.json'

    return response

if __name__ == '__main__':
    HOST = os.getenv("HOST", '0.0.0.0')
    PORT = int(os.getenv("PORT", 5003))
    app.run(debug=True, host=HOST, port=PORT)
