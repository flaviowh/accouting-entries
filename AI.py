from filesreader import ReadFiles
import joblib
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import SGDClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from collections import namedtuple
from scipy.sparse import csr_matrix
import urlextract
import unicodedata
import string
import re
import os
import nltk
from collections import Counter
import numpy as np
np.random.seed(42)


BEST_MODEL = RandomForestClassifier(random_state=42, n_estimators=200)


class ModelTrainer:
    def __init__(self, path, untrained_model):
        self.path = path
        self.untrained_model = untrained_model

    def save_model(self, name, path=None):
        if not path:
            path = "./models"
        trained_model = self.train()
        joblib.dump(trained_model, f"{path}/{name}.sav" )
        print("\nModel saved.")

    def save_pipeline(self, name, path=None):
        if not path:
            path = "./models"
        pipeline = self.preprocess_pileline()
        X = self.filtered_files()
        trained_pipeline = pipeline.fit(X)
        joblib.dump(trained_pipeline, f"{path}/{name}.sav")
        print("\nPipeline saved.")

    def analyse_classes(self):
        path = self.path
        reader = ReadFiles()
        results = {}
        for folder, subfolder, filenames in os.walk(path):
            results.setdefault(os.path.basename(folder), 0)
            for filename in filenames:
                if filename.endswith((".pdf", ".txt")):
                    file = os.path.join(path, folder, filename)
                    test = reader.read(file)
                    if test is not None:
                        results[os.path.basename(folder)] += 1
        return results    

    def train(self):
        x, y = self.model_sets()
        preprocess = self.preprocess_pileline()
        preprocessed_x = preprocess.fit_transform(x)
        trained_model = self.untrained_model.fit(preprocessed_x, y)
        return trained_model

    def filtered_files(self):
        reader = ReadFiles()
        files = self.list_files()
        readable_files = []
        for file in files:
            text = reader.read(file)
            if text is not None:
                readable_files.append(file)
        return readable_files


    def model_sets(self, train_set=False):
        x = self.filtered_files()
        try:
            y = [re.sub(r'\.txt', '',
                        file.split(os.sep)[-2]) for file in x]
        except Exception:
            y = [re.sub(r'\.pdf', '',
                        file.split(os.sep)[-2]) for file in x]
        if not train_set:
            return x, y
        else:
            x_train, x_test, y_train, y_test = train_test_split(
                x, y, train_size=0.9)
            return x_train, x_test, y_train, y_test

    def cross_validate_models(self, scoring_criteria="accuracy", cv=10):
        model = self.untrained_model
        preprocess = self.preprocess_pileline()
        results = []
        X, y = self.model_sets()
        X = preprocess.fit_transform(X)
        if "squared" not in scoring_criteria:
            scores = cross_val_score(
                model, X, y, scoring=scoring_criteria, cv=cv)
        else:
            scores = np.sqrt(cross_val_score(
                model, X, y, scoring=scoring_criteria, cv=cv))
        mean, std = round(scores.mean(), 3), round(scores.std(), 3)
        cross_validation = namedtuple(
            "Cross_validation", ["model", "mean", "stdev"])
        results.append(cross_validation(model, mean, std))
        return results

    def list_files(self):
        path = self.path
        all_files = []
        valid_formats = (".txt", ".pdf")
        for folder, subfolder, filenames in os.walk(path):
            for file in filenames:
                if file.endswith(valid_formats):
                    all_files.append(os.path.join(path, folder, file))
        return all_files

    def preprocess_pileline(self):
        my_pipeline = Pipeline([
            ("Text_Filter", TextFilter(min_size=4)),
            ("Vectorizer", CountVectorizer(max_features=1000)),
        ])
        return my_pipeline

# ----- PRE PROCESSING ----------------------


class TextFilter(BaseEstimator, TransformerMixin):
    def __init__(self, max_size=25, min_size=None, lower_case=True, remove_punctuation=True,
                 replace_urls=True, remove_numbers=True, stem=False):
        self.lower_case = lower_case
        self.remove_punctuation = remove_punctuation
        self.replace_urls = replace_urls
        self.remove_numbers = remove_numbers
        self.stem = stem
        self.min_size = min_size
        self.max_size = max_size

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        X_transformed = []
        reader = ReadFiles()
        for file in X:
            text = reader.read(file)
            if text is None:
                pass
            else:
                if self.replace_urls:
                    url_extractor = urlextract.URLExtract()
                    urls = list(set(url_extractor.find_urls(text)))
                    urls.sort(key=lambda url: len(url), reverse=True)
                    for url in urls:
                        text = text.replace(url, " URL ")
                text = self._remove_symbols(text)
                if self.remove_numbers:
                    text = re.sub(r'\d+(?:\.\d*)?(?:[eE][+-]?\d+)?', '', text)
                if self.min_size != None:
                    words = [word for word in text.split() if len(
                        word) >= self.min_size and len(word) <= self.max_size]
                    text = ' '.join(word for word in words)
                if self.remove_punctuation:
                    text = self._remove_punctuation(text)
                if self.stem:
                    text = self._stem_words(text)
                if self.lower_case:
                    text = text.lower()
                X_transformed.append(text)
        return np.array(X_transformed)

    def _remove_symbols(self, text):
        for symbol in string.punctuation:
            text = text.replace(symbol, '')
        return re.sub(r'\W+', ' ', text, flags=re.M)

    def _remove_punctuation(self, text):
        """Remove all diacritic marks from Latin base characters"""
        norm_txt = unicodedata.normalize('NFD', text)
        latin_base = False
        preserve = []
        for c in norm_txt:
            if unicodedata.combining(c) and latin_base:
                continue  # ignore diacritic on Latin base char
            preserve.append(c)
        # if it isn't a combining char, it's a new base char
            if not unicodedata.combining(c):
                latin_base = c in string.ascii_letters
        normalized = ''.join(preserve)
        return unicodedata.normalize('NFC', normalized)

    def _stem_words(self, text):
        stemmer = nltk.stem.RSLPStemmer()
        results = [stemmer.stem(word) for word in text.split()]
        return ' '.join(word for word in results)


class TextCounter(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X: list, y=None):
        return [Counter(text.split()) for text in X]


class WordCounterToVectorTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, vocabulary_size=1000):
        self.vocabulary_size = vocabulary_size

    def fit(self, X, y=None):
        total_count = Counter()
        for word_count in X:
            for word, count in word_count.items():
                total_count[word] += min(count, 10)
        most_common = total_count.most_common()[:self.vocabulary_size]
        self.vocabulary_ = {word: index + 1 for index,
                            (word, count) in enumerate(most_common)}
        return self

    def transform(self, X, y=None):
        rows = []
        cols = []
        data = []
        for row, word_count in enumerate(X):
            for word, count in word_count.items():
                rows.append(row)
                cols.append(self.vocabulary_.get(word, 0))
                data.append(count)
        return csr_matrix((data, (rows, cols)), shape=(len(X), self.vocabulary_size + 1))

### ----------------------------


