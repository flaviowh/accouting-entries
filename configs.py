#/settings.py
# UI FILES
#from main import show_popup
import os
import sqlite3
import shutil
import datetime
import sys
from PyQt5 import  uic
from PyQt5.QtWidgets import QMessageBox, QMainWindow
from form import CompanyForm

MAINWINDOW_UI = r".\UI\mainwindow.ui"
MAINWINDOW = r".\UI\mainwindow.py"
STATEMENT_UI = r".\UI\statement_win.ui"
STOCK_UI = r".\UI\stock_win.ui"
SETTINGS_UI = r".\UI\settings_win.ui"

DBNAME = "acc_settings"

SQLSTUDIO = ".\SQLiteStudio\SQLiteStudio.exe"
TESSERACT = r".\Tesseract\tesseract.exe"
POPPLER = r'.\Poppler\Release-21.10.0-0\poppler-21.10.0\Library\bin'


class DBeditor:
    def __init__(self):
        self.db_file = f"{DBNAME}.db"

    def restart_db(self):
        self.__backup_db()
        self.__create_db()
        self.__remake_tables()
        self.__fill_tables()

    def __backup_db(self):
        db_name = self.db_file
        if os.path.isfile(db_name):
            basename = os.path.basename(db_name).removesuffix(".db")
            time_string = str(datetime.datetime.now())[:-7].replace(":", "")
            filename = f"{os.getcwd()}\\backup\\{basename} backup {time_string}.db"
            shutil.copy(db_name, filename)

    def __create_db(self):
        db_file = self.db_file
        if os.path.isfile(db_file) is False:
            conn = None
            try:
                conn = sqlite3.connect(db_file)
            except Exception:
                return False
            finally:
                if conn:
                    conn.close()
                    return True
        else:
            return False

    def __remake_tables(self):
        for table, query in TABLES.items():
            self.create_table(table, query)

    def query_db(self, query):
        db_file = self.db_file
        conn = sqlite3.connect(db_file)
        cursor_obj = conn.cursor()
        cursor_obj.execute(query)
        conn.commit()
        cursor_obj.close()

    def create_table(self, table_name, creation_query):
        self.query_db(f"DROP TABLE IF EXISTS {table_name}")
        self.query_db(creation_query)

    def __fill_tables(self, ):
        for query in STARTING_DATA:
            self.query_db(query)


TABLES = {"companies": """CREATE TABLE companies (
    id              VARCHAR          PRIMARY KEY,
    bank            VARCHAR,
    bank_account    VARCHAR,
    ai_model        VARCHAR,
    name            VARCHAR,
    gen_credit      VARCHAR,
    gen_credit_hist VARCHAR,
    gen_debit       VARCHAR,
    gen_debit_hist  VARCHAR );""",

          "debits_0": """CREATE TABLE debits_0 (
    keywords VARCHAR,
    name     VARCHAR,
    history  VARCHAR,
    account  VARCHAR
);""",
          "banks":
          """
        CREATE TABLE banks (
    name VARCHAR PRIMARY KEY
);""",
          "bank_brasil": """CREATE TABLE bank_brasil (
    keywords VARCHAR,
    acc_type VARCHAR,
    history  VARCHAR,
    account  VARCHAR);""",

          "bank_itau": """CREATE TABLE bank_itau (
    keywords VARCHAR,
    acc_type VARCHAR,
    history  VARCHAR,
    account  VARCHAR);""",
          }

STARTING_DATA = ["""
INSERT INTO banks (
                      name
                  )
                  VALUES (
                      'itau'
                  ),
                  (
                      'brasil'
                  );

""",
                 """
INSERT INTO companies (
                          gen_debit_hist,
                          gen_debit,
                          gen_credit_hist,
                          gen_credit,
                          name,
                          ai_model,
                          bank_account,
                          bank,
                          id
                      )
                      VALUES (
                          'Vlr. ref. outras despesas operacionais.',
                          259,
                          'Vlr. ref. recebimento nesta data.',
                          2,
                          'geral',
                          'model0',
                          1,
                          'brasil,itau',
                          0
                      );
""",
                 """
INSERT INTO debits_0 (
                         account,
                         history,
                         name,
                         keywords
                     )
                     VALUES (
                         265,
                         'Vlr. ref. consumo de energia.',
                         'energia',
                         'energisa'
                     ),
                     (
                         266,
                         'Vlr. ref. consumo de agua.',
                         'agua',
                         'cagepa'
                     ),
                     (
                         58,
                         'Vlr. ref. FGTS.',
                         'fgts',
                         'fgts'
                     ),
                     (
                         267,
                         'Vlr. ref. consumo de energia.',
                         'telefonia',
                         'vivo,tim,claro'
                     ),
                     (
                         57,
                         'Vlr. ref. INSS.',
                         'inss',
                         'inss,gps'
                     ),
                     (
                         259,
                         'Vlr. ref. outras despesas operacionais.',
                         'diversos',
                         ' '
                     ),
                     (
                         278,
                         'Vlr. ref. bem de uso e consumo.',
                         'consumo',
                         ''
                     ),
                     (
                         322,
                         'Vlr. ref. IPTU/TCR.',
                         'iptu',
                         'iptu,tcr'
                     ),
                     (
                         1,
                         'Vlr. ref. saque neste dia.',
                         'saque',
                         'saque'
                     ),
                     (
                         78,
                         'Vlr. ref. Simples Nacional.',
                         'simples nacional',
                         'simples nacional'
                     );
""",
                 """
INSERT INTO bank_itau (
                          account,
                          history,
                          acc_type,
                          keywords
                      )
                      VALUES (
                          398,
                          'Vlr. ref. resgate de aplicacao Itau.',
                          'debit',
                          'res aplic'
                      ),
                      (
                          209,
                          'Vlr. ref. rendimento de aplicacao Itau.',
                          'debit',
                          'rend pago'
                      ),
                      (
                          398,
                          'Vlr. ref. aplicacao Itau.',
                          'credit',
                          'apl aplic'
                      ),
                      (
                          333,
                          'Vlr. ref. taxa bancaria.',
                          'credit',
                          'tar,taxa,tarifa'
                      ),
                      (
                          1,
                          'Vlr. ref. saque nesta data.',
                          'credit',
                          'saque'
                      );

""",
                 """
INSERT INTO bank_brasil (
                            account,
                            history,
                            acc_type,
                            keywords
                        )
                        VALUES (
                            360,
                            'Vlr. ref. resgate de aplicacao BB rf aut.',
                            'debit',
                            'bb rf '
                        ),
                        (
                            360,
                            'Vlr. ref. aplicacao BB rf aut.',
                            'credit',
                            'bb rf'
                        ),
                        (
                            333,
                            'Vlr. ref. despesa bancaria.',
                            'credit',
                            'tar,taxa,tarifa'
                        ),
                        (
                            1,
                            'Vlr. ref. saque nesta data.',
                            'credit',
                            'saque'
                        );

""", ]


########## SETTINGS WINDOW ###############

class SettingsWindow(QMainWindow):
    def __init__(self, all_windows):
        super(QMainWindow, self).__init__()
        self.windows = all_windows
        uic.loadUi(SETTINGS_UI, self)

        self.button_menu.clicked.connect(self.go_menu)
        self.button_quit.clicked.connect(sys.exit)
        self.button_goback.clicked.connect(self.go_back)
        self.button_add_company.clicked.connect(self.open_new_company_form)
        self.button_edit_db.clicked.connect(self.open_sqleditor)
        self.button_restart_db.clicked.connect(self.restart_db_dialog)

    def go_menu(self):
        self.windows.setCurrentIndex(0)

    def go_back(self):
        self.windows.setCurrentIndex(1)
    
    def open_new_company_form(self):
        company_form = CompanyForm(self.windows)
        self.windows.addWidget(company_form)
        self.windows.setCurrentIndex(4)

    def open_sqleditor(self):
        os.startfile(SQLSTUDIO)


    def restart_db_dialog(self):
        message_box = QMessageBox()
        message_box.setWindowTitle("Aviso")
        message_box.setText(f"Essa ação irá apagar as informações do banco de dados. Deseja continuar?")
        message_box.setIcon(QMessageBox.Icon.Warning)  #Information, Question,  Warning, Critical,
        message_box.setStyleSheet("background-color: rgb(250, 250, 250);")
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        message_box.adjustSize()
        if message_box.exec_() == QMessageBox.Yes:
            editor = DBeditor()
            editor.restart_db()
            #show_popup("Aviso", "A base de dados foi reiniciada, reinicie a aplicação.", QMessageBox.Information)


# show_popup("Atenção", "Preencha todos os campos.", QMessageBox.Warning)
if __file__ == "__main__":
    DBeditor.restart_db()