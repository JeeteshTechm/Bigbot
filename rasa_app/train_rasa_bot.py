import rasa

class TrainBot:
    def __init__(self, bot_id):
        self.bot_id = bot_id

    def _create_file_paths(self):
        config = f"{self.bot_id}/config.yml"
        training_files = f"{self.bot_id}/data/"
        domain = f"{self.bot_id}/domain.yml"
        output = f"{self.bot_id}/models/"
        return config, training_files, domain, output

    def train_and_save_model(self):
        config, training_files, domain, output = self._create_file_paths()

        rasa.train(domain, config, [training_files], output, fixed_model_name='rasa_model')

        return "Your Rasa model has been trained and saved"

bot_id = "my_bot"
bot_trainer = TrainBot(bot_id)
response = bot_trainer.train_and_save_model()