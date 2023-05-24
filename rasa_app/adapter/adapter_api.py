import json
import yaml
import tempfile
from flask import Flask, jsonify, request, send_file
from bigbot_to_rasa3_adapter import JSONToYAMLConverter
from rasa3_to_bigbot_adapter import YAMLToJsonConverter

app = Flask(__name__)

@app.route('/json-to-yaml', methods=['POST'])
def convert_json_to_yaml():
    try:
        payload = request.get_json()
        json_converter = JSONToYAMLConverter(payload)
        yaml_data = json_converter.convert_to_yaml()

        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False) as temp_file:
            temp_file.write(yaml_data.encode('utf-8'))

        temp_filename = temp_file.name

        response = send_file(temp_filename, mimetype='text/yaml')
        response.headers['Content-Disposition'] = 'attachment; filename=output.yml'

        return response
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5008)
