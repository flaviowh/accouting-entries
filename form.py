import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox, QMainWindow, QTableWidgetItem, QMainWindow, QMessageBox, QTableWidget, QFileDialog
import datetime
import pandas as pd
import re
import sqlite3
import os


NEW_DATA = []


class DBUpdate:
    def __init__(self) -> None:
        pass

    def write_new_company_data(self):
        try:
            new_id = self.get_new_company_ID()
            self.add_new_company(new_id)
            self.new_payment_table(new_id)
            self.fill_payment_table(new_id)
            show_popup(
                "Sucesso", "Empresa adicionada ao banco de dados. Reinicie a aplicação.", QMessageBox.Information)
            NEW_DATA.clear()
        except Exception:
            show_popup(
                "Erro", f"Ocorreu um erro:\n{Exception}", QMessageBox.Warning)
            db_write(f'DELETE from companies WHERE ID == {new_id}')
        self.app_restart()

    def app_restart(self):
        QApplication.exit(-123)

    def add_new_company(self, company_id):
        new_id = company_id
        data = [data.lower() for data in NEW_DATA[0]]
        query = f"""INSERT INTO companies ( gen_debit_hist, gen_debit, gen_credit_hist, 
                  gen_credit, name, ai_model, bank_account, bank, id)
            VALUES ('{data[3]}','{data[6]}','{data[5]}','{data[4]}','{data[0]}',
                    'model{new_id}', '{data[2]}', '{data[1]}', '{new_id}'); """
        db_write(query)

    def new_payment_table(self, company_id):
        table_name = f"debits_{company_id}"
        db_write(f"DROP TABLE IF EXISTS {table_name}")
        query = f"""CREATE TABLE {table_name} (keywords  VARCHAR, name  VARCHAR, history  VARCHAR,
        account  VARCHAR);"""
        db_write(query)

    def fill_payment_table(self, company_id):
        data = NEW_DATA[1]
        if len(data) > 0:
            table_name = f"debits_{company_id}"
            values = (tuple(entry.values()) for entry in data)
            values = ','.join(str(value) for value in values).lower()
            query = f"""INSERT INTO {table_name} (name, keywords, history, 
                        account) VALUES {values}"""
            db_write(query)

    def get_new_company_ID(self):
        ids = dbquery("SELECT id from companies", multiple=True)
        ids = [int(num[0]) for num in ids]
        new_id = str(max(ids) + 1)
        return new_id


class PaymentForm(QDialog):
    def __init__(self, windows_widget, table_name, fields, rows_num=1, continuation=True):
        super(QDialog, self).__init__()
        uic.loadUi(r".\UI\tableform.ui", self)
        self.windows = windows_widget
        self.TableTitle.setText(table_name)
        self.setWindowIcon(QtGui.QIcon(r'.\UI\pngegg2.png'))
        self.fields = fields
        self.continuation = continuation
        self.rows_num = rows_num
        self.savebutton.setText("Salvar")
        self.return_button.clicked.connect(self.return_window)
        self.savebutton.clicked.connect(self.save_inputs)
        self.ready_fields()

    def ready_fields(self):
        fields = [field.title() for field in self.fields]
        self.tableWidget.setColumnCount(len(self.fields))
        self.tableWidget.setRowCount(self.rows_num)
        self.tableWidget.setHorizontalHeaderLabels(fields)

    def save_inputs(self):
        form_data = []
        data = self.get_updated_headers_and_rows()
        if data:
            headers, rows = data
            for row in rows:
                entry = {}
                for value in row:
                    entry[headers[row.index(value)]] = value
                form_data.append(entry)
            NEW_DATA.append(form_data)
            DBUpdate().write_new_company_data()

    def return_window(self):
        self.windows.setCurrentIndex(4)

    def get_updated_headers_and_rows(self):
        column_size = self.tableWidget.columnCount()
        headers = [self.tableWidget.horizontalHeaderItem(header_num).text()
                   for header_num in range(self.tableWidget.columnCount())]
        rows = [[self.tableWidget.item(row_num, column) for column in range(column_size)]
                for row_num in range(self.tableWidget.rowCount())]
        filled_rows = [row for row in rows if not None in row]
        values = [[item.text() for item in row]
                  for row in filled_rows]
        return headers, values


class CompanyForm(QMainWindow):
    def __init__(self, all_windows):
        super(QMainWindow, self).__init__()
        self.windows = all_windows
        uic.loadUi(r".\UI\new_company.ui", self)
        self.savebutton.clicked.connect(self.add_company)
        self.cancel_button.clicked.connect(self.return_window)

    def add_company(self):
        company_details = self.get_company_details()
        if company_details:
            NEW_DATA.clear()
            NEW_DATA.append(company_details)
            self.open_payments_form()
        else:
            show_popup("Atenção", "Preencha todos os campos",
                       QMessageBox.Warning)

    def get_company_details(self):
        if self.fields_filled():
            values = [field.text()
                      for field in self.findChildren(QtWidgets.QLineEdit)]
            return values
        else:
            return False

    def open_payments_form(self):
        labels = ["nome", "palavras chave", "histórico", "conta"]
        payments_form = PaymentForm(
            self.windows, "Adicionar pagamentos", labels, 50)
        self.windows.addWidget(payments_form)
        self.windows.setCurrentIndex(5)

    def return_window(self):
        self.windows.setCurrentIndex(3)

    def fields_filled(self):
        fields = [field for field in self.findChildren(QtWidgets.QLineEdit)]
        for field in fields:
            if re.search("^\s*$", field.text()):
                return False
        return True


def show_popup(window_title, text, icon):
    message_box = QMessageBox()
    message_box.setWindowTitle(window_title)
    message_box.setText(text)
    message_box.setIcon(icon)  # Information, Question,  Warning, Critical,
    message_box.setStyleSheet("font: 63 10pt \"Serif Sans\"; color: rgb(10, 0, 0); "
                              "background-color: white;")
    message_box.adjustSize()
    message_box.exec_()


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


def db_write(query):
    con = sqlite3.connect(r"acc_settings.db")
    cur = con.cursor()
    cur.execute(query)
    con.commit()
    cur.close()


## new payments
# testdata = ["nome", "cnpj", "bancos", "c. bancária", "credora padrão", "hist. C. padrão", "devedora padrão", "hist. D. padrão"]
# testdata2 = ["nome", "palavras chave", "histórico", "conta contrapartida"]
# App = QApplication(sys.argv)
# table = Tableform("Adicionar Pagamentos", testdata2, rows_num=20 )
# table.show()
# sys.exit(table.exec_())

# new company
# App = QApplication(sys.argv)
# form = CompanyForm()
# form.show()
# sys.exit(App.exec_())
