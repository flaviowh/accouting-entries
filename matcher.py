import logging
from email.policy import default
import random

from matplotlib.pyplot import table
from filesreader import ReadFiles
import re
import os
import sqlite3
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
from scipy.sparse import csr_matrix
from sqlalchemy import true
import urlextract
import unicodedata
import string
import joblib
import re
import nltk
from collections import Counter
import numpy as np

np.random.seed(42)

logging.basicConfig(format='- %(message)s')

## DATABASE HANDLER ---------------------------------------


class ACDatabase:

    def query(self, query, multiple=False):
        con = sqlite3.connect(r"acc_settings.db")
        cur = con.cursor()
        if multiple is False:
            results = cur.execute(query).fetchone()
            if results is not None:
                return results[0]
        else:
            results = cur.execute(query).fetchall()
            if len(results) >= 1:
                return results

    def match_info(self, info: str, table_name: str, acc_type=None):
        """Returns account and history or None"""
        keyphrases = self.get_keywords(table_name)
        for phrases in keyphrases:
            for phrase in phrases:
                if phrase in info:
                    if acc_type:
                        conditions = f'keywords LIKE "%{phrase}%" AND acc_type="{acc_type}"'
                    else:
                        conditions = f'keywords LIKE "%{phrase}%"'
                    account_and_history = self.query(
                        f"SELECT account, history FROM {table_name} WHERE {conditions}", multiple=True)
                    if account_and_history is not None:
                        return account_and_history[0]
                    else:
                        pass

    def get_keywords(self, table_name):
        all_keywords = self.query(
            f"SELECT keywords from {table_name}", multiple=True)
        all_keywords = [keywords[0].split(',') for keywords in all_keywords]
        all_keywords = [keyword for keyword in all_keywords if re.match(
            r'\w', keyword[0]) is not None]
        return all_keywords

##---------------------------------------------------


class CompanyInfo:
    def __init__(self, company_id):
        DB = ACDatabase()
        self.company_id = company_id
        suffix = f"from companies WHERE id == {self.company_id}"
        self.model = DB.query(f'SELECT ai_model {suffix}')
        self.bank = DB.query(f'SELECT bank {suffix}').split(",")
        self.bank_acc = DB.query(f'SELECT bank_account {suffix}')
        self.default_credit, self.default_credit_hist, self.default_debit, self.default_debit_hist = DB.query(
            f'SELECT * {suffix}', multiple=True)[0][5:]

### --------------------------------------------------------------------

class EntriesMatcher:
    def __init__(self, statement_entries, invoices_dir, invoice_entries, company_id, bank_name, ai_option):
        self.unformatted_statement = statement_entries
        self.unformatted_invoices = invoice_entries
        self.company_id = company_id
        self.invoices_dir = invoices_dir
        self.bank_name = bank_name
        self.ai_option = ai_option
        
    def matched(self):
        formatted_statement, formatted_invoices = self.prepare_entries()
        count = 0
        for invoice_entry in formatted_invoices:
            for entry in formatted_statement:
                if invoice_entry['date'] == entry['date'] and invoice_entry['value'] == entry['value']:
                    count += 1
                    entry['debit'] = str(invoice_entry['debit'])
                    entry['credit'] = str(invoice_entry['credit'])
                    entry['history'] = str(invoice_entry['history'])
        logging.warning(f"Matched {count} invoices to the statement.")
        return formatted_statement

    def prepare_entries(self):
        statement_formatter = FormatStatement(self.bank_name,
                                              self.unformatted_statement, self.company_id)
        formatted_statement = statement_formatter.format()
    
        invoices_formatter = FormatInvoices(
            self.unformatted_invoices, self.invoices_dir, self.company_id, use_ai=self.ai_option)
        formatted_invoices = invoices_formatter.format()

        return formatted_statement, formatted_invoices
## -----------------------------------------------------


class FormatStatement:
    def __init__(self, bank_name, statement_entries, company_id):
        self.entries = statement_entries
        self.company_ID = company_id
        self.company = CompanyInfo(self.company_ID)
        self.bank_name = bank_name

    def format(self):
        ready_entries = []
        filled_entries = self.fill_entries(self.bank_name)
        for entry in filled_entries:
            ready_entry = {}
            ready_entry["id"] = str(random.randint(0, 10000))
            ready_entry["date"] = entry["date"]
            ready_entry["value"] = entry["value"]
            ready_entry["debit"] = str(entry["debit"])
            ready_entry["credit"] = str(entry["credit"])
            ready_entry["history"] = entry["history"]

            ready_entries.append(ready_entry)
        return ready_entries

    def fill_entries(self, bank_name):
        filled_entries = []
        for entry in self.entries:
            if entry["entrada"] == True:
                entry["debit"] = self.company.bank_acc
                entry = self.solve_input(entry, bank_name)
            else:
                entry["credit"] = self.company.bank_acc
                entry = self.solve_output(entry, bank_name)

            filled_entries.append(entry)
        return filled_entries

    def solve_input(self, entry, bank_name):
        DB = ACDatabase()
        info = entry["info"].lower()
        bank_table = f"bank_{bank_name}"
        acc_and_hist = DB.match_info(info, bank_table, "debit")
        if acc_and_hist is not None:
            entry["credit"], entry["history"] = acc_and_hist
        else:
            entry["credit"] = self.company.default_credit
            entry["history"] = self.company.default_credit_hist
        return entry

    def solve_output(self, entry, bank_name):
        DB = ACDatabase()
        info = entry["info"].lower()
        bank_table = f"bank_{bank_name}"
        acc_and_hist = DB.match_info(info, bank_table, "credit")
        if acc_and_hist is not None:
            entry["debit"], entry["history"] = acc_and_hist
        else:
            table_name = "debits_0"
            acc_and_hist = DB.match_info(info, table_name)
            if acc_and_hist is not None:
                entry["debit"], entry["history"] = acc_and_hist
            else:
                table_name = f"debits_{self.company_ID}"
                acc_and_hist = DB.match_info(info, table_name)
                if acc_and_hist is not None:
                    entry["debit"], entry["history"] = acc_and_hist
                else:
                    entry["debit"] = self.company.default_debit
                    entry["history"] = self.company.default_debit_hist
        return entry

# ----------------------------------------------

class FormatInvoices:
    def __init__(self, invoice_entries, invoices_dir, company_id, use_ai):
        self.entries = invoice_entries
        self.company_ID = company_id
        logging.warning(f"Formatting {len(self.entries)} invoices")
        self.invoices_dir = invoices_dir
        self.ai_option = use_ai

    def format(self):
        if self.ai_option == True:
            logging.warning("\nUsing ML model\n")
            ai_classified = self.add_class(self.entries)
            good_entries = self.filter_bad_entries(ai_classified)
            filled = self.add_accounts_and_hist(good_entries)
        else:
            logging.warning("\nNot using ML model\n")
            classifier = RegexMatcher(self.entries, self.company_ID)
            regex_classified = classifier.classify()
            filled = self.filter_bad_entries(regex_classified)
        print("\ntesting entries v")
        for entry in filled:
            print(entry)
        return filled

    def add_accounts_and_hist(self, entries):
        DB = ACDatabase()
        company = CompanyInfo(self.company_ID)
        classified = []
        for entry in entries:
            classified_entry = {}
            class_ = entry["class"]
            general = f'FROM debits_0 WHERE name LIKE "%{class_}%"'
            specific = f'FROM debits_{self.company_ID} WHERE name LIKE "%{class_}%"'
            if DB.query(f'SELECT * {general}') is not None:
                hist = DB.query(f'SELECT history {general}')
                debit = DB.query(f'SELECT account {general}')
            elif DB.query(f'SELECT * {specific}') is not None:
                hist = DB.query(f'SELECT history {specific}')
                debit = DB.query(f'SELECT account {specific}')
            else:
                hist = company.default_debit_hist
                debit = company.default_debit
            classified_entry["date"] = entry["date"]
            classified_entry["value"] = entry["value"]
            classified_entry["debit"] = debit
            classified_entry["history"] = hist
            classified_entry["credit"] = company.bank_acc
            classified.append(classified_entry)
        return classified

    def filter_bad_entries(self, classified_entries):
        entries = classified_entries
        filtered = []
        failed = []
        initial_length = len(entries)
        for entry in entries:
            indx = entries.index(entry)
            if len(entry.values()) < 3 or None in entry.values():
                failed.append(entry["location"])
                del entries[indx]
            else:
                entry['info'] = ''
                filtered.append(entry)
        final_length = len(filtered)
        logging.warning(
            f"{initial_length - final_length} incomplete entries were discarded.")
        for file in failed:
            logging.warning(file)
        return filtered

    def format_value(self, value: str):
        try:
            edit1 = re.sub(r"\.", '', value)
            edit2 = re.sub(r",", ".", edit1)
            return edit2
        except Exception:
            raise Exception(f"Error transforming value: {value}")

    def add_class(self, entries):
        classifier = AIClassifier(
            self.invoices_dir, company_code=self.company_ID)
        classifications = classifier.model_predictions()
        logging.warning(f"Total classifications: {len(classifications)}.")
        logging.warning(f"Unique classes found: {len(set(classifications))}.")
        for entry in entries:
            entry["class"] = classifications[entries.index(entry)]
        return entries

## ---------- REGEX MATCHER ---


class RegexMatcher:
    def __init__(self, invoice_entries, company_code):
        self.entries = invoice_entries
        self.company_code = company_code
        self.DB = ACDatabase()

    def classify(self):
        classified = []
        for entry in self.entries:
            entry["credit"] = self.get_credit_acc()
            match = self.find_acc_hist(entry)
            if match is not None:
                entry["debit"], entry["history"] = match
                entry["info"] = ''
                classified.append(entry)
            else:
                entry["debit"], entry["history"] = self.get_default_acc_and_hist()
                entry["info"] = ''
                classified.append(entry)
        return classified

    def find_acc_hist(self, entry):
        text = entry["info"]
        general_pmts = f"debits_0"
        general_keywords = self.get_keywords(general_pmts)
        specific_pmts = f"debits_{self.company_code}"
        specific_keywords = self.get_keywords(specific_pmts)
        text = self.remove_punctuation(text).lower()
        match1 = self.get_acc_and_hist(text, general_keywords, general_pmts)
        if match1 is not None:
            return match1
        match2 = self.get_acc_and_hist(text, specific_keywords, specific_pmts)
        if match2 is not None:
            return match2

    def get_keywords(self, table_name):
        query = f"SELECT keywords FROM {table_name}"
        phrases = self.DB.query(query, True)
        keywords = [phrase for phrase in phrases if len(phrase[0]) > 1]
        keywords = [phrase[0].split(",") for phrase in keywords]
        keywords = [word for phrase in keywords for word in phrase]
        return keywords

    def get_credit_acc(self):
        query= (rf'SELECT bank_account from companies WHERE id == {self.company_code}')
        return str(self.DB.query(query))

    def get_acc_and_hist(self, text, keywords, tablename):
        for keyword in keywords:
            match = re.search(keyword, text)
            if match is not None:
                return self.DB.query(rf'SELECT account, history from {tablename} WHERE keywords LIKE "%{keyword}%"', multiple=True)[0]

    def get_default_acc_and_hist(self):
        company_id = self.company_code
        return self.DB.query(rf'SELECT gen_debit, gen_debit_hist from companies WHERE id == {company_id}', multiple=True)[0]

    def remove_punctuation(self, text):
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


## -----------------------------------------------------
##------MACHINE LEARNING PREDICTOR  ------------------


class AIClassifier:
    def __init__(self, invoices_dir, company_code):
        self.path = invoices_dir
        self.model = Models(company_code)
        self.files_list = [os.path.join(self.path, file) for file in os.listdir(
            self.path)]
        self.file_names = [os.path.basename(file) for file in self.files_list]

    def model_predictions(self):
        files = self.list_files(self.path)
        return self.model.predict(files).tolist()

    def list_files(self, path):
        all_files = [os.path.join(path, file) for file in os.listdir(path) if
                     file.endswith(".txt")]
        return all_files


class Models:
    def __init__(self, company_code):
        model_name = CompanyInfo(company_code).model
        self.model = joblib.load(fr'./models/{model_name}.sav')
        self.pipeline = joblib.load(fr'./models/pipeline{company_code}.sav')

    def predict(self, files_list):
        data = self.pipeline.transform(files_list)
        return self.model.predict(data)


# # TESTS
# Statement
# import Itau_statement
# path = r'C:/Users/flavi/Desktop/test/extrato 08-2021.txt'
# path2 = r"D:\Data for python\novo visual 2021\Extratos\EXTRATO 03.txt"
# statement = Itau_statement.ItauStatement().raw_statement(path2)
# #Ok
# formatter = FormatStatement(statement, 2)
# formatted_entries = formatter.format()
# for entry in formatted_entries:
#     print(entry)

# info = CompanyInfo(0)

# print(info.default_debit_hist)
