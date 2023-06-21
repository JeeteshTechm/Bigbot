import json
import yaml
import tempfile
import os
import logging
from flask_cors import CORS, cross_origin
from flask import Flask, jsonify, request, send_file
from bigbot_to_rasa3_adapter import JSONToYAMLConverter
from rasa3_to_bigbot_adapter import YAMLToJsonConverter

logging.basicConfig(level=logging.INFO, filename='logs/adapter.log')
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

@app.route('/json-to-yaml', methods=['POST'])
def convert_json_to_yaml():
    try:
        payload = request.get_json()
        logging.info('Received JSON payload: {}'.format(payload))

        json_converter = JSONToYAMLConverter(payload)
        yaml_data = json_converter.convert_to_yaml()

        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False) as temp_file:
            temp_file.write(yaml_data.encode('utf-8'))

        temp_filename = temp_file.name
        logging.info('Converted JSON to YAML: {}'.format(yaml_data))

        response = send_file(temp_filename, mimetype='text/yaml')
        response.headers['Content-Disposition'] = 'attachment; filename=output.yml'

        return response
    except Exception as e:
        logging.error('Error converting JSON to YAML: {}'.format(str(e)))
        return jsonify({'error': str(e)})

@app.route('/yaml-to-json', methods=['POST'])
@cross_origin()
def convert_yaml_to_json():
    try:
        file = request.files['file']
        logging.info('Received YAML file: {}'.format(file.filename))

        yaml_content = yaml.safe_load(file)
        filename = file.filename
        logging.info('Loaded YAML content: {}'.format(yaml_content))

        yaml_converter = YAMLToJsonConverter(yaml_content)
        json_data = yaml_converter.convert_to_json()

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_file.write(json_data.encode('utf-8'))

        temp_filename = temp_file.name
        logging.info('Converted YAML to JSON: {}'.format(json_data))

        response = send_file(temp_filename, mimetype='text/json')
        response.headers['Content-Disposition'] = 'attachment; filename=output.json'

        return response
    except Exception as e:
        logging.error('Error converting YAML to JSON: {}'.format(str(e)))
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
