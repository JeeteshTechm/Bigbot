import openai
import yaml
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from flask import Flask, jsonify, request, send_file
import requests
import tempfile
from rasa3_to_bigbot_adapter import YAMLToJsonConverter
from datetime import date

app = Flask(__name__)
CORS(app)

config_path = "config.yml"
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

openai.api_key = config['endpoints']['api_url']

example_yaml = "yaml_shema.yml"
with open(example_yaml, 'r') as file:
    example_yaml_data = yaml.safe_load(file)

example_yaml_text = yaml.dump(example_yaml_data)

def get_completion(prompt):
    #model="gpt-4"
    model="gpt-3.5-turbo"
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
    model=model,
    messages=messages,
    temperature=0,
    )
    return response.choices[0].message["content"]


def convert_dates_to_strings(yaml_obj):
    if isinstance(yaml_obj, list):
        for i in range(len(yaml_obj)):
            yaml_obj[i] = convert_dates_to_strings(yaml_obj[i])
    elif isinstance(yaml_obj, dict):
        for key, value in yaml_obj.items():
            yaml_obj[key] = convert_dates_to_strings(value)
    elif isinstance(yaml_obj, date):
        return yaml_obj.isoformat()
    return yaml_obj


@app.route('/data_generator', methods=['POST'])
@cross_origin()
def chat():
    # try:
        data = request.get_json()
        user_message = data['message']
        input= "Please generate rasa yaml with multiple intents for"+ user_message+ " similar to below schema with same structure like "+example_yaml_text
        prompt = (input)

        response = get_completion(prompt)
        print(response)
        yaml_content = yaml.safe_load(response)

        # Convert datetime.date objects to strings
        yaml_content=convert_dates_to_strings(yaml_content)

        # Continue with JSON conversion
        yaml_converter = YAMLToJsonConverter(yaml_content)
        json_data = yaml_converter.convert_to_json()
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_file.write(json_data.encode('utf-8'))

        temp_filename = temp_file.name
        response = send_file(temp_filename, mimetype='text/json')
        response.headers['Content-Disposition'] = 'attachment; filename=output.json'
        
        return (response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
