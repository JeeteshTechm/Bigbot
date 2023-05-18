import subprocess

class RasaTrainingDataValidator:
    
    def __init__(self, rasa_project_dir):
        self.rasa_project_dir = rasa_project_dir
    
    def validate_training_data(self):
        result = subprocess.run(["rasa", "data", "validate", "--fail-on-warnings"],
                                cwd=self.rasa_project_dir,
                                capture_output=True,
                                text=True)

        if "Data file is valid" in result.stdout and "Domain file is valid" in result.stdout:
            result="Rasa training data is valid"

        elif result.returncode == 0:
            result="Rasa training data is valid"
        else:
            if "Validation errors:" in result.stdout:
                error_lines = result.stdout.split("\n")[1:-1] 
                for line in error_lines:
                    print(line)
            else:
                print(result.stdout)

my_validator = RasaTrainingDataValidator(rasa_project_dir="123")
my_validator.validate_training_data()