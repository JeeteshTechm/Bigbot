import json
from flask import Flask, jsonify, request
from bigbot_to_rasa3_adapter import JSONToYAMLConverter
from rasa3_to_bigbot_adapter import YAMLToJsonConverter

app = Flask(__name__)

@app.route('/json-to-yaml', methods=['POST'])
def convert_json_to_yaml():
    try:
        uploaded_file = request.files['file']
        payload = json.load(uploaded_file)
        json_converter = JSONToYAMLConverter(payload)
        yaml_data = json_converter.convert_to_yaml()
        return jsonify({'result': yaml_data})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/yaml-to-json', methods=['POST'])
def convert_yaml_to_json():
    try:
        uploaded_file = request.files['file']
        payload = json.load(uploaded_file)
        yaml_converter = YAMLToJsonConverter(payload)
        json_data = yaml_converter.convert_to_json()
        return jsonify({'result': json_data})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
