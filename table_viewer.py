from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtWidgets import QDialog, QMainWindow, QMessageBox, QTableWidget, QTableWidgetItem, QFileDialog
import datetime
import csv
import stock_counter
import pandas as pd

model_glp_data = [{"Data": "0", "Nota Fiscal": "0", "Quantidade": "0", "Valor total": "0",
                  "Valor Uni.": "0", "Fornecedor": "0"}]
timestamp = (str(datetime.datetime.today()).split()[1])


class TableViewer(QDialog):
    def __init__(self, main_data_path, table_name, details=None):
        super(QDialog, self).__init__()
        uic.loadUi(r".\UI\tableviewer.ui", self)
        self.tablename = table_name
        self.TableTitle.setText(self.tablename)
        self.main_data_path = main_data_path
        self.data_details = details
        self.setWindowIcon(QtGui.QIcon(r'.\UI\pngegg2.png'))
        # very import to define if data is GLP or accounting entries
        self.define_received_data()

        self.savebutton.clicked.connect(self.write_updated_data_to_csv)

        if len(details) > 1:
            self.total_lcdnumber.setDisabled(True)
            self.total_lcdnumber.setVisible(False)
            self.label_total.setVisible(False)

        self.fill_table_with_data()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

    def define_received_data(self):
        if len(self.data_details) == 1:
            self.cfops = self.data_details[0]
            if len(stock_counter.process_nfes(self.main_data_path, self.cfops)) != 0:
                self.data_list = stock_counter.process_nfes(
                    self.main_data_path, self.cfops)
            else:
                self.tablename = "Notas XML não encontradas."
                self.data_list = model_glp_data
        elif len(self.data_details) > 1:
            self.data_list = self.main_data_path

    def fill_table_with_data(self):
        try:
            table_headers = self.data_list[0].keys()
            self.tableWidget.setRowCount(len(self.data_list))
            self.tableWidget.setColumnCount(len(self.data_list[0].keys()))
            self.tableWidget.setHorizontalHeaderLabels(table_headers)
            for dictionary in self.data_list:
                for key, value in dictionary.items():
                    value_to_cell = QTableWidgetItem(value)
                    self.tableWidget.setItem(self.data_list.index(dictionary),
                                            list(dictionary.keys()).index(key), value_to_cell)
        except IndexError:
            self.show_popup("Erro", "Não há dados para mostrar", QMessageBox.Warning)

    def get_updated_headers_and_rows(self):
        headers = [self.tableWidget.horizontalHeaderItem(header_num).text()
                   for header_num in range(self.tableWidget.columnCount())]
        rows = [[self.tableWidget.item(row_num, column).text() for column in range(self.tableWidget.columnCount())]
                for row_num in range(self.tableWidget.rowCount())]
        return headers, rows

    def create_new_dictionary_from_table(self):
        headers, rows = self.get_updated_headers_and_rows()
        updated_dictionaries = []
        for row in rows:
            entry = {}
            for value in row:
                entry[headers[row.index(value)]] = value
            updated_dictionaries.append(entry)
        return updated_dictionaries

    def write_updated_data_to_csv(self):    # TODO: add name argument ?
        updated_data = self.create_new_dictionary_from_table()
        output_location = str(QFileDialog.getExistingDirectory(self, "Selecionar Local"))
        if output_location:
            file = rf'{output_location}/Dados de {self.tablename}.csv'
            with open(file,'w', encoding='utf8', newline='') as output_file:
                writing_object = csv.DictWriter(
                    output_file, fieldnames=updated_data[0].keys())
                writing_object.writeheader()
                writing_object.writerows(updated_data)
                output_file.close()
            self.fix_csv_ids(file)
            self.show_popup(
                "Sucesso", "Arquivo CSV salvo na pasta selecionada.", QMessageBox.Information)

    def fix_csv_ids(self, file):
        df = pd.read_csv(file)
        df.id = pd.Series([1 for _ in df.id])
        df.to_csv(file, index=False)


    def show_popup(self, window_title, text, icon):
        message_box = QMessageBox()
        message_box.setWindowTitle(window_title)
        message_box.setText(text)
        message_box.setIcon(icon)  # Information, Question,  Warning, Critical,
        message_box.setStyleSheet("font: 63 10pt \"Segoe UI Variable Display Semib\";\n"
                                  "color: rgb(240, 240, 240); background-color: rgb(20,20,50)")
        message_box.adjustSize()
        message_box.exec_()

