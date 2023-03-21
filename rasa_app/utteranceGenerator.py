
# NLTK way to generate similar sentences

import nltk
# nltk.download('punkt')
# nltk.download('averaged_perceptron_tagger')
# nltk.download('wordnet')
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import random

# Example sentence
sentence = "How to book a hotel"

# Tokenize the sentence
tokens = word_tokenize(sentence)

# Identify the POS tags for each token
pos_tags = nltk.pos_tag(tokens)

# Lemmatize the tokens to reduce words to their base form
lemmatizer = WordNetLemmatizer()
lemmatized_tokens = []
for token, pos in pos_tags:
    if pos.startswith('V'):
        # If the token is a verb, use 'v' as the pos argument for the lemmatizer
        lemmatized_tokens.append(lemmatizer.lemmatize(token, pos='v'))
    else:
        lemmatized_tokens.append(lemmatizer.lemmatize(token))

# Identify synonyms for each token
synonyms = []
for token in lemmatized_tokens:
    token_synonyms = []
    for syn in wordnet.synsets(token):
        for lemma in syn.lemmas():
            if lemma.name() != token:
                token_synonyms.append(lemma.name().replace('_', ' '))
    synonyms.append(token_synonyms)

# Generate a random sentence using the synonyms
generated_sentence = []
for token_synonyms in synonyms:
    if token_synonyms:
        generated_sentence.append(random.choice(token_synonyms))
    else:
        generated_sentence.append(lemmatized_tokens[synonyms.index(token_synonyms)])

print(' '.join(generated_sentence))



# gpt library way to generate similar utterances
import gpt_2_simple as gpt2

model_name = "774M"
# gpt2.download_gpt2(model_name=model_name)
model_dir=".\models"
sess = gpt2.start_tf_sess()
gpt2.load_gpt2(sess, model_name=model_name,model_dir=model_dir)
input_text = "I want to book an hotel"
generated_text = gpt2.generate(sess, model_name=model_name, prefix=input_text, length=20, temperature=0.7, top_p=0.9, return_as_list=True)[0]

print(generated_text)
