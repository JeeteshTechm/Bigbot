import ruamel.yaml

class YamlFileProcessor:
    def __init__(self, file_path):
        self.file_path = file_path

    def remove_empty_keys(self, data):
        if isinstance(data, dict):
            cleaned_data = ruamel.yaml.comments.CommentedMap()
            for k, v in data.items():
                if v or isinstance(v, bool) or isinstance(v, int):
                    cleaned_data[k] = self.remove_empty_keys(v)
            return cleaned_data
        if isinstance(data, list):
            cleaned_data = ruamel.yaml.comments.CommentedSeq()
            for v in data:
                if v or isinstance(v, bool) or isinstance(v, int):
                    cleaned_data.append(self.remove_empty_keys(v))
            return cleaned_data
        return data

    def process_yaml_file(self):
        # Read YAML file
        yaml = ruamel.yaml.YAML()
        yaml.indent(sequence=4, offset=2)
        with open(self.file_path, "r") as f:
            data = yaml.load(f)

        # Remove empty keys
        cleaned_data = self.remove_empty_keys(data)

        # Save modified YAML file
        with open(self.file_path, "w") as f:
            yaml.dump(cleaned_data, f)

"""# Example usage
yaml_file_path = "skills/faq_bot/domain.yml"
processor = YamlFileProcessor(yaml_file_path)
processor.process_yaml_file()"""
