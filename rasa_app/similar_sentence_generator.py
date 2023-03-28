import numpy as np
import nltk
from transformers import PegasusForConditionalGeneration, PegasusTokenizerFast
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

nltk.download('vader_lexicon')

class ParaphraserClusterer:
    def __init__(self, model_name):
        self.model = PegasusForConditionalGeneration.from_pretrained(model_name)
        self.tokenizer = PegasusTokenizerFast.from_pretrained(model_name)
        
    def get_paraphrased_sentences(self, sentence, num_return_sequences=5, num_beams=5):
        inputs = self.tokenizer([sentence], truncation=True, padding="longest", return_tensors="pt")
        outputs = self.model.generate(
            **inputs,
            num_beams=num_beams,
            num_return_sequences=num_return_sequences,
        )

        return self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
    
    def filter_sentences_by_sentiment(self, input_sentence, output_sentences):
        sid = SentimentIntensityAnalyzer()

        input_score = sid.polarity_scores(input_sentence)
        output_scores = [sid.polarity_scores(sentence) for sentence in output_sentences]

        filtered_sentences = []
        if input_score['neg'] == 0:
            for sentence, score in zip(output_sentences, output_scores):
                if score["neg"] == 0:
                    filtered_sentences.append(sentence)
        else:
            for sentence, score in zip(output_sentences, output_scores):
                if score["neg"] != 0:
                    filtered_sentences.append(sentence)

        return filtered_sentences
    
    def cluster_sentences(self, sentences, num_clusters):
        vectorizer = TfidfVectorizer(stop_words='english')
        X = vectorizer.fit_transform(sentences)

        kmeans = KMeans(n_clusters=num_clusters, random_state=0).fit(X)

        clustered_sentences = []
        for i in range(num_clusters):
            cluster_indices = np.where(kmeans.labels_ == i)[0]
            clustered_sentences.append(sentences[cluster_indices[0]])

        return clustered_sentences
