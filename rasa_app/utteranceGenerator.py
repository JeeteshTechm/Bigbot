import random
import threading
from queue import Queue
import spacy
import torch
from langdetect import detect
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from nltk.corpus import wordnet

# Load the spaCy models
nlp_models = {
    "en": spacy.load("en_core_web_sm"),
    "es": spacy.load("es_core_news_sm"),
    "de": spacy.load("de_core_news_sm"),
}

# Define the Transformers text generation pipelines for each language
text_generators = {
    "en": [
        pipeline("text-generation", model="gpt2", tokenizer="gpt2"),
        pipeline("text-generation", model="distilgpt2", tokenizer="distilgpt2")
    ],
    "es": [
        pipeline("text-generation", model="mrm8488/spanish-gpt2", tokenizer="mrm8488/spanish-gpt2"),
    ],
    "de": [
        pipeline("text-generation", model="dbmdz/german-gpt2", tokenizer="dbmdz/german-gpt2"),
    ],
}

# Detect the language of the input text
def detect_language(input_text):
    detected_language = detect(input_text)
    if detected_language in nlp_models and detected_language in text_generators:
        return detected_language
    else:
        raise ValueError("Unsupported language. Please use English, Spanish, or German.")

def generate_nltk_sentence(input_sentence, replacement_rate, language):
    nlp = nlp_models[language]
    doc = nlp(input_sentence)
    lemmatized_tokens = [token.lemma_ for token in doc]

    synonyms = []
    for token in lemmatized_tokens:
        token_synonyms = []
        for syn in wordnet.synsets(token):
            for lemma in syn.lemmas():
                if lemma.name() != token:
                    token_synonyms.append(lemma.name().replace('_', ' '))
        synonyms.append(token_synonyms)

    new_sentence = []
    for token_synonyms in synonyms:
        if token_synonyms and random.random() < replacement_rate:
            new_sentence.append(random.choice(token_synonyms))
        else:
            new_sentence.append(lemmatized_tokens[synonyms.index(token_synonyms)])

    return ' '.join(new_sentence)

def generate_transformers_sentence(input_text, temperature, language, generator, num_return_sequences, num_beams):
    generated_sentences = generator(
        input_text,
        max_length=20,
        do_sample=True,
        temperature=temperature,
        top_p=0.9,
        num_return_sequences=num_return_sequences,
        num_beams=num_beams,
    )
    return [generated_sentence["generated_text"] for generated_sentence in generated_sentences]

def transformers_worker(generator):
    while len(sentence_list) < target_count:
        generated_sentences = generate_transformers_sentence(input_text, temperature, language, generator, num_return_sequences=5, num_beams=5)
        for sentence in generated_sentences:
            sentence_queue.put(sentence)

def generate_sentences(target_count, similarity, input_text, language):
    if not (0.0 <= similarity <= 1.0):
        raise ValueError("Similarity should be a float between 0.0 and 1.0")

    sentence_list = []
    sentence_queue = Queue()

    temperature = 1.0 - similarity
    replacement_rate = 1.0 - similarity

    def nltk_worker():
        while len(sentence_list) < target_count:
                        sentence_queue.put(generate_nltk_sentence(input_text, replacement_rate, language))

    workers = [threading.Thread(target=nltk_worker)]
    for generator in text_generators[language]:
        workers.append(threading.Thread(target=transformers_worker, args=(generator,)))

    for worker in workers:
        worker.start()

    while len(sentence_list) < target_count:
        sentence_list.append(sentence_queue.get())

    for worker in workers:
        worker.join()

    return sentence_list


if __name__ == "__main__":
    input_sentence = "How to book a hotel"
    target_count = 10
    similarity = 0.5
    language = detect_language(input_sentence)

    if language not in nlp_models or language not in text_generators:
        raise ValueError("Unsupported language. Please choose 'en', 'es', or 'de'.")

    sentences = generate_sentences(target_count, similarity, input_sentence, language)

    print("Generated sentences:")
    for sentence in sentences:
        print(sentence)
