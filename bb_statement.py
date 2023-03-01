from os import remove
import re

from matplotlib.pyplot import text
from bb_statement_old import BBStatementOld

#>---------------------- NEW VERSION


class BBStatement:
    def __init__(self, statement_path):
        self.statement_path = statement_path
        self.lines = self.format_lines(self.statement_path)

    def raw_statement(self):
        if self.is_new_format():
            return self.prep_statement()
        else:
            return BBStatementOld().raw_statement(self.statement_path)

    def prep_statement(self):
        entries = []
        lines = self.lines
        for line in lines:
            entry = {}
            entry["date"] = self.get_date(line)
            entry["value"] = self.get_value(line)
            entry["info"] = self.get_info(line)
            entry["entrada"] = self.not_payment(line)
            if self.is_complete(entry):
                entries.append(entry)
        return entries

    def format_lines(self, txt):
        big_text = open(txt, 'r', encoding='utf8').read()
        deleted_spaces = re.sub(r"\n", ' ', big_text)
        result = re.search(r"Anterior(.*)(S A L D O| SALDO)", deleted_spaces)
        content = result.group(1)
        return re.split(r'.(?=\d\d/\d\d/\d\d\d\d)', content)

    def rem_page_breaks(self, line):
        pattern = r"extrato(.*?)histórico valor"
        match = re.search(pattern, line.lower())
        if match is not None:
            line = re.sub(match.group(0), '', line.lower())
        return line

    def get_value(self, line):
        pattern = re.compile(
            r'(\d+\.\d{3},|[1-9]\d\d,|[1-9]\d,|\d,)\d\d(\s|$)')
        match = pattern.search(line)
        if match is not None:
            return self.fix_value(match.group(0))

    def fix_value(self, value):
        value = re.sub(r"\.", '', value)
        return re.sub(r",", ".", value)

    def get_date(self, line):
        match = re.search(r"\d\d(/|-|\.)\d\d(/|-|\.)2\d\d\d", line)
        if match is not None:
            return match.group(0)

    def get_info(self, line):
        pattern1 = r"\s(.*?)\d"
        match1 = re.search(pattern1, line)
        info = " "
        if match1 is not None:
            info = match1.group(0).lower()
        pattern2 = r"\)\s(.*?)$"
        match2 = re.search(pattern2, line)
        # ignores page breaks
        if match2 is not None:
            info = f"{info} {self.rem_page_breaks(match2.group(1))}"
        return info

    def not_payment(self, line):
        return True if re.search(r"\(\-\)", line) is None else False

    def is_new_format(self):
        statement = open(self.statement_path, 'r', encoding="utf-8").read()
        test = re.search(r"\(\-\)", statement)
        return True if test is not None else False

    def is_complete(self, entry):
        return False if None in entry.values() else True
