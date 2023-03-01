import re
import json
import os
import re
from statistics import mode


class ItauStatement:
    def __init__(self, statement_path):
        self.statement_path = statement_path

    def get_year(self):
        """Gets the year from the bank statement"""
        content = open(self.statement_path, 'r', encoding='utf-8').read()
        match = re.findall(r"20\d\d[\s|$]", content)
        if match is not None:
            years_found = [date for date in match]
            year = mode(years_found)
        return year


    def read_statement(self):
        year = self.get_year()
        months = {" / jan ": f"/01/{year}    ", " / fev ": f"/02/{year}    ",
                " / mar ": f"/03/{year}    ", " / abr ": f"/04/{year}  ",
                " / mai ": f"/05/{year}    ", " / jun ": f"/06/{year}    ",
                " / jul ": f"/07/{year}    ", " / ago ": f"/08/{year}  ",
                " / set ": f"/09/{year}    ", " / out ": f"/10/{year}    ",
                " / nov ": f"/11/{year}    ", " / dez ": f"/12/{year}  "}
        """Begins reading the statement"""
        lines1, lines2, lines3 = [], [], []
        content = open(self.statement_path, 'r', encoding='utf-8').readlines()
        for key, value in months.items():
            for line in content:
                match = re.search(key, line)
                if match is not None:
                    line = re.sub(fr"{key}", fr"{value}", line)
                    lines2.append(line)
        for line in lines2:
            if "saldo" not in line.lower():
                lines3.append(line)
        return lines3


    def clear_lines(self):
        """Starts filtering useless data by removing random numbers"""
        lines1 , lines2 = [], []
        lines = self.read_statement()
        for line in lines:
            clear1 = re.sub(r"\s\d\d\d\d\s",'    ', line )
            lines1.append(clear1)
        for x in lines1:
            clear2 = re.sub("\d\d\d\d\d-\d", '    ', x)
            lines2.append(clear2)
        return lines2


    def get_valor(self, text):
        """Gets the amount from a bank statement's line"""
        y = re.sub(r"\d\d/\d\d/\d\d\d\d", '', text)
        z = re.sub(r"-", '', y)
        m = "r\d\d\d.\d\d\d,\d\d\s"
        att =[m, m[3:], m[5:], m[8:], m[10:], m[12:]]
        for n in att:
            try:
                attempt = re.search(f"{n}", z)
                valor = attempt.group(0)
                fixed_valor = re.sub(r'\n','', valor)
                removedots = re.sub(r'\.', '', fixed_valor)
                swapped_comma = re.sub(',', '.', removedots)
                return swapped_comma
            except Exception:
                pass


    def raw_statement(self):
        """Gets the date, price, and if it's an entry or payment and returns a list"""
        raw_receipt = []
        for line in self.clear_lines():
            rdict = {"date":"" , 'value': '', 'info': '', "entrada": ''}
            check = re.search(r'\s-\d', line)
            if check is not None:
                rdict['entrada'] = False
            else:
                rdict['entrada'] = True
            date = re.search(r"\d\d/\d\d/\d\d\d\d", line)
            if date is not None:
                rdict["date"] = date.group(0)
            rdict['value'] = self.get_valor(line)
            subinfo = re.sub(r'([^a-zA-Z\s]+?)', '', line)
            info = re.sub("\s[a-zA-Z]\s",'', subinfo)
            rdict['info'] = re.sub("\n",'', info)
            raw_receipt.append(rdict)
        return raw_receipt






