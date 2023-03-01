import logging
import invoices
from itau_statement import ItauStatement
from bb_statement import BBStatement
import table_viewer
import matcher
import filesreader
import configs
import os
import sys
import sqlite3
from PyQt5 import QtGui, QtWidgets, uic
from PyQt5.QtCore import QTimeLine
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QMainWindow, QTableWidgetItem


from sklearn.base import BaseEstimator, TransformerMixin
from scipy.sparse import csr_matrix


import urlextract
import unicodedata
import string
import re
import nltk
from collections import Counter
import numpy as np
np.random.seed(42)
logging.basicConfig(format='- %(message)s')


def dbquery(query, multiple=False):
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


COMPANIES = [company[0].title() for company in dbquery(
    "SELECT name FROM companies", multiple=True)]

BANKS = [bank[0].title() for bank in dbquery(
    "SELECT name FROM banks", multiple=True)]

STATEMENT_READERS = {"brasil": BBStatement, "itau": ItauStatement}

DESKTOP = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

# UX WINDOWS  - FADING EFFECT


class FaderWidget(QtWidgets.QWidget):

    def __init__(self, old_widget, new_widget):

        QtWidgets.QWidget.__init__(self, new_widget)

        self.old_pixmap = QPixmap(new_widget.size())
        old_widget.render(self.old_pixmap)
        self.pixmap_opacity = 1.0

        self.timeline = QTimeLine()
        self.timeline.valueChanged.connect(self.animate)
        self.timeline.finished.connect(self.close)
        self.timeline.setDuration(277)
        self.timeline.start()

        self.resize(new_widget.size())
        self.show()

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()

    def animate(self, value):
        self.pixmap_opacity = 1.0 - value
        self.repaint()


class StackedWidget(QtWidgets.QStackedWidget):

    def __init__(self, parent=None):
        QtWidgets.QStackedWidget.__init__(self, parent)

    def setCurrentIndex(self, index):
        self.fader_widget = FaderWidget(
            self.currentWidget(), self.widget(index))
        QtWidgets.QStackedWidget.setCurrentIndex(self, index)

# UI WINDOWS


def show_popup(window_title, text, icon):
    message_box = QMessageBox()
    message_box.setWindowTitle(window_title)
    message_box.setText(text)
    message_box.setIcon(icon)  # Information, Question,  Warning, Critical,
    message_box.setStyleSheet("font: 63 10pt \"Serif Sans\"; color: rgb(10, 0, 0); "
                              "background-color: white;")
    message_box.adjustSize()
    message_box.exec_()


class MainWindow(QMainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()
        uic.loadUi(configs.MAINWINDOW_UI, self)

        self.button_statementWindow.clicked.connect(self.go_statement_window)
        self.button_stockWindow.clicked.connect(self.go_stock_window)
        self.button_quit.clicked.connect(sys.exit)
        self.button_about.clicked.connect(self.about_info)

    def go_statement_window(self):
        all_windows.setCurrentIndex(1)

    def go_stock_window(self):
        all_windows.setCurrentIndex(2)

    def about_info(self):
        show_popup("Sobre", open('./Sobre.txt',
                   encoding='utf-8').read(), QMessageBox.Information)

# STATEMENT WINDOW


class StatementWindow(QMainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()
        uic.loadUi(configs.STATEMENT_UI, self)
        self.fill_boxes()
        self.button_menu.clicked.connect(self.go_menu)
        self.button_quit.clicked.connect(sys.exit)
        self.pbprocessar.clicked.connect(self.process_data)
        self.pushButton_2.clicked.connect(self.locate_invoice_folder)
        self.pushButton.clicked.connect(self.locate_textfile_statement)
        self.pbcancelar.setDisabled(True)
        self.progressBar.setVisible(False)
        self.pbcancelar.clicked.connect(self.stop_ocr_thread)
        self.button_settings.clicked.connect(self.open_settings)

    def fill_boxes(self):
        for company in COMPANIES:
            self.sel_empresa.addItem(company)
        for bank in BANKS:
            self.sel_banco.addItem(bank)

    def go_menu(self):
        all_windows.setCurrentIndex(0)

    def open_settings(self):
        all_windows.setCurrentIndex(3)

    def locate_textfile_statement(self):

        file_name = QFileDialog.getOpenFileName(
            self, 'Abrir arquivo', DESKTOP, 'text files (*.txt)')
        self.line_statement_path.setText(file_name[0])

    def locate_invoice_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self, 'Abrir pasta')
        self.line_invoices_path.setText(folder_name)

    def get_company_code(self):
        return COMPANIES.index(self.sel_empresa.currentText())

    def get_ai_option(self):
        return True if self.ai_option.isChecked() else False

    def select_process_type(self):
        statement_path = self.line_statement_path.text()
        invoices_path = self.line_invoices_path.text()
        selected_bank = self.sel_banco.currentText().lower()
        selected_company = self.sel_empresa.currentText().lower()
        if os.path.isfile(statement_path) and os.path.isdir(invoices_path) is False and selected_bank != "banco" and selected_company != "empresa":
            if self.bank_is_valid():
                return "statement_only"
        elif os.path.isfile(statement_path) and os.path.isdir(invoices_path) and selected_bank != "banco" and selected_company != "empresa":
            if self.bank_is_valid():
                return "complete_process"
        else:
            show_popup("Atenção", "Verifique as opções.",
                       QMessageBox.Warning)

    def bank_is_valid(self):
        statement_bank = self.get_statement_bank()
        selected_bank = self.sel_banco.currentText().lower()
        selected_company = self.sel_empresa.currentText().lower()
        banks = dbquery(
            fr'SELECT bank from companies WHERE name LIKE "%{selected_company}%"').split(",")
        if selected_bank == statement_bank and selected_bank in banks:
            return True
        else:
            show_popup("Atenção", "Extrato imcompatível com banco ou com esta empresa.",
                       QMessageBox.Warning)
            return False

    def get_statement_bank(self):
        statement_path = self.line_statement_path.text()
        for bank in BANKS:
            match = re.search(bank.lower(), open(
                statement_path, encoding="utf-8").read().lower())
            if match is not None:
                matched_bank = match.group(0).lower()
                return matched_bank

    def load_invoice_files(self):
        self.textEdit.setText("\n\n\n\nLendo e analisando documentos...")
        self.progressBar.setValue(30)
        self.textEdit.setText("Lendo e analisando documentos...")
        self.converter_thread = filesreader.PDFConverter(
            self.line_invoices_path.text())
        self.switch_buttons(True)
        self.converter_thread.start()
        self.converter_thread.finished.connect(self.prepare_matched_invoices)
        self.converter_thread.update_progress.connect(self.update_progress_bar)
        self.converter_thread.update_text.connect(self.update_progress_text)

    def get_raw_statement(self):
        bank = self.sel_banco.currentText().lower()
        statement_reader = STATEMENT_READERS[bank](
            self.line_statement_path.text())
        if statement_reader:
            return statement_reader.raw_statement()

    def prepare_statement_only(self):
        raw_statement = self.get_raw_statement()
        bank_name = self.get_statement_bank()
        self.progressBar.setValue(66)
        company_id = self.get_company_code()
        formatted_statement = matcher.FormatStatement(
            bank_name, raw_statement, company_id).format()
        self.progressBar.setValue(100)
        self.textEdit.setText("\n\n\n\nExtrato processado.")
        return formatted_statement

    def get_raw_invoices(self, invoices_list):
        bank = self.sel_banco.currentText().lower()
        invoices_reader = invoices.InvoicesReader()
        if invoices_reader:
            return invoices_reader.prep_invoices(invoices_list)

    def prepare_matched_invoices(self, invoices_list):
        self.switch_buttons(False)
        bank_name = self.get_statement_bank()
        raw_statement, raw_invoices = self.get_raw_statement(
        ), self.get_raw_invoices(invoices_list)
        self.progressBar.setValue(95)
        company_id = self.get_company_code()
        invoices_directory = f"{self.line_invoices_path.text()}/textfiles"
        ai_option = self.get_ai_option()
        entries_matcher = matcher.EntriesMatcher(
            raw_statement, invoices_directory, raw_invoices, company_id, bank_name, ai_option)
        matched_invoices_list = entries_matcher.matched()
        self.progressBar.setValue(100)
        self.update_progress_text(
            "\nTabela de lançamentos gerada com sucesso.")
        self.open_table_window(matched_invoices_list, "Lançamentos do Extrato")
        # self.create_report(matched_invoices_list)
        logging.warning("Process complete.")

    def update_progress_bar(self, new_value=None):
        if new_value:
            self.progressBar.setValue(new_value)
        else:
            value = self.progressBar.value()
            value += 1
            self.progressBar.setValue(value)

    def update_progress_text(self, message):
        self.textEdit.setText(message)

    def stop_ocr_thread(self):
        self.converter_thread.quit()
        self.switch_buttons()

    def process_data(self):
        match self.select_process_type():
            case "statement_only":
                self.open_table_window(
                    self.prepare_statement_only(), "Lançamentos do Extrato")
            case "complete_process":
                self.load_invoice_files()
        logging.warning("Process complete.")

    # def create_report(self, entries):
    #     run_date = str(datetime.datetime.now())[:-10]
    #     company_code = self.get_company_code()
    #     name = dbquery(
    #         fr'SELECT name from companies WHERE id == {company_code}')
    #     with open(os.path.join(DESKTOP, 'Relatório de lançamentos.txt'), 'w', encoding='utf-8') as report:
    #         report.write(
    #             f"\nRelatório de Lançamentos Contábeis Automáticos       ---------------------------      {run_date}"
    #             f"\n\nEmpresa: {name} "
    #             f"\n\n{len(entries)} lançamentos do extrato gerados."
    #             f"\n\n{len(ItauInvoices.itau_reading_errors)} documentos não foram procesados por erro."
    #             f"\n\n{len(ItauInvoices.itau_other_pmt)} documentos precisam ser lançados manualmente:"
    #             "\n")
    #         for file in ItauInvoices.itau_other_pmt:
    #             report.write(f"\n{file}")
    #         report.write(f"\n\n{len(ItauInvoices.itau_adjustments)} "
    #                      f"documentos contem juros, multas ou descontos a lançar manualmente:")
    #         for pmt in ItauInvoices.itau_adjustments:
    #             report.write(f"\n{pmt}")
    #         report.close()

    def open_table_window(self, data, table_name):
        self.statement_window = table_viewer.TableViewer(
            data, table_name, [1, 2])
        self.statement_window.show()

    def switch_buttons(self, disabled=False):
        buttons = (self.pbprocessar, self.sel_empresa, self.button_settings,
                   self.sel_banco, self.button_menu, self.pbajuda, self.button_quit)
        if disabled:
            for button in buttons:
                button.setDisabled(True)
            self.pbcancelar.setDisabled(False)
            self.progressBar.setVisible(True)
        else:
            for button in buttons:
                button.setDisabled(False)
            self.pbcancelar.setDisabled(True)

    def go_menu(self):
        all_windows.setCurrentIndex(0)


###########  STOCK WINDOW #################

class StockWindow(QMainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()
        uic.loadUi(configs.STOCK_UI, self)

        self.button_menu.clicked.connect(self.go_menu)
        self.button_quit.clicked.connect(sys.exit)

    def go_menu(self):
        all_windows.setCurrentIndex(0)


# SETTINGS WINDOW ###############  testing stability loading from other file

# class SettingsWindow(QMainWindow):
#     def __init__(self):
#         super(QMainWindow, self).__init__()
#         uic.loadUi(configs.SETTINGS_UI, self)

#         self.button_menu.clicked.connect(self.go_menu)
#         self.button_quit.clicked.connect(sys.exit)
#         self.button_goback.clicked.connect(self.go_back)

#     def go_menu(self):
#         all_windows.setCurrentIndex(0)

#     def go_back(self):
#         all_windows.setCurrentIndex(1)

####### MACHINE LEARNING classifier components called from matcher.py #####


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
        reader = filesreader.ReadFiles()
        X_transformed = []
        for file in X:
            text = reader.read(file)
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

# ------------------------------------------------------


class MyStack(StackedWidget):
    def __init__(self):
        super(StackedWidget, self).__init__()

    EXIT_CODE_REBOOT = -123


if __name__ == "__main__":
    currentExitCode = MyStack.EXIT_CODE_REBOOT
    while currentExitCode == MyStack.EXIT_CODE_REBOOT:
        app = QApplication(sys.argv)
        all_windows = MyStack()
        mainwindow = MainWindow()
        statement_window = StatementWindow()
        stock_window = StockWindow()
        settings_window = configs.SettingsWindow(all_windows)
        all_windows.addWidget(mainwindow)
        all_windows.addWidget(statement_window)
        all_windows.addWidget(stock_window)
        all_windows.addWidget(settings_window)
        all_windows.setFixedSize(640, 480)
        all_windows.setWindowIcon(QtGui.QIcon(r'.\UI\pngegg2.png'))
        all_windows.setWindowTitle("Accounting Assistant")
        all_windows.show()
        currentExitCode = app.exec_()
        app = None
