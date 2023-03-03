import pandas as pd
import numpy as np
import rasa
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin_min
from rasa.nlu.training_data import load_data
from rasa.nlu.model import Trainer
from rasa.nlu import config
from rasa.nlu.model import Interpreter
from rasa.nlu.config import RasaNLUModelConfig
from rasa.nlu.model import Metadata, Interpreter


# Load the training data
training_data = load_data('data/nlu.md')

# Train the Rasa model with TED policy
trainer = Trainer(config.load("config.yml"))
trainer.train(training_data)
model_directory = trainer.persist('models/nlu', fixed_model_name='current')

# Create an interpreter to generate embeddings
interpreter = Interpreter.load(model_directory)

# Get the embeddings for each intent and skill
intent_embeddings = []
skill_embeddings = []
for example in training_data.intent_examples:
    intent_embeddings.append(interpreter.featurize_message(example.text))
for example in training_data.training_examples:
    skill_embeddings.append(interpreter.featurize_message(example.text))

# Cluster the embeddings using K-means
kmeans = KMeans(n_clusters=5, random_state=0).fit(skill_embeddings)
labels = kmeans.labels_

# Identify duplicates within each cluster
unique_skills = []
for i in range(len(set(labels))):
    cluster_skills = [training_data.training_examples[j] for j in np.where(labels == i)[0]]
    unique_skills.extend(pairwise_distances_argmin_min(kmeans.cluster_centers_, cluster_skills)[0])

# Identify redundant skills and intents
skill_text = [training_data.training_examples[i].text for i in unique_skills]
skill_df = pd.DataFrame({'text': skill_text})
skill_df['text_len'] = skill_df['text'].apply(len)
skill_df = skill_df.sort_values('text_len')
skill_df = skill_df.drop_duplicates(subset='text', keep='last')

# Link skills together based on their embeddings
skill_links = {}
for i in range(len(skill_embeddings)):
    skill_links[i] = []
    for j in range(len(skill_embeddings)):
        if i == j:
            continue
        sim = np.dot(skill_embeddings[i], skill_embeddings[j]) / (np.linalg.norm(skill_embeddings[i]) * np.linalg.norm(skill_embeddings[j]))
        if sim > 0.8:
            skill_links[i].append(j)

# Print the results
print(skill_df)
print(skill_links)

# Load the NLU training data
training_data = load_data('data/nlu.md')

# Define the NLU pipeline and TED policy
config = RasaNLUModelConfig('config.yml')
config.pipeline

# Define and train the NLU model
trainer = Trainer(config)
interpreter = trainer.train(training_data)

# Save the trained model to a directory
model_directory = trainer.persist('models/nlu', fixed_model_name='current')

# Load the model as an interpreter
interpreter = Interpreter.load(model_directory)

"""
This module uses Rasa's NLU library, Pandas, and scikit-learn to:

Load training data.
Train an NLU model using the training data and a TED policy.
Load the trained model as an interpreter.
Generate embeddings for each intent and skill using the interpreter.
Cluster the skill embeddings using K-means clustering with 5 clusters.
Identify duplicate skills within each cluster.
Identify redundant skills and intents and link skills together based on their embeddings.
Print the resulting skill dataframe and skill links.
Load the NLU training data again.
Define and train the NLU model again using the same training data and TED policy as before.
Save the trained model to the same directory as before.
Load the trained model as an interpreter again.

It's primary purposes are (1) to identify duplicate skills and intents; and (2) link similar skills together based on their embeddings.
"""
