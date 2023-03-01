import filesreader
import os
import shutil
import re
import statistics
import json

MONTHS = {'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04', 'maio': '05', 'junho': '06',
          'julho': '07', 'agosto': '08', 'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'}


class InvoicesReader:
    def __init__(self) -> None:
        self.reader = filesreader.ReadFiles()

    def prep_invoices(self, files_list):
        ready_entries = []
        for invoice in files_list:
            text = self.reader.read(invoice)
            entry = {}
            entry["date"] = self.get_date(text)
            entry["value"] = self.get_value(text)
            entry["info"] = text
            entry['location'] = invoice
            ready_entries.append(entry)
        return ready_entries

    def get_value(self, text):
        if self._bar_value(text):
            return self._bar_value(text)
        elif self._any_amount(text) is not None:
            return self._any_amount(text)

    def get_date(self, text):
        if self.pmt_date(text):
            return re.sub(r'\n', '', self.pmt_date(text)).strip()
        elif self.written_date(text):
            return self.written_date(text)
        elif self.any_date(text) is not None:
            return re.sub(r'\n', '', self.any_date(text)).strip()

    def _bar_value(self, text):
        try:
            match = re.search(r'\d{47}', text)
            if match is not None:
                match2 = re.search(r'0\d+$', match.group(0)[-9:])
                match3 = re.search(r'^0*(\d+)', match2.group(0))
                part1 = match3.group(1)[:-2]
                part2 = match3.group(1).removeprefix(part1)
                value = (f"{part1},{part2}")
                return self.fix_value(value)
        except AttributeError:
            pass

    def _any_amount(self, text, values=None):
        if values is None:
            values = []
        value_regex = re.compile(
            r'(\d+\.\d{3},|[1-9]\d\d,|[1-9]\d,|\d,)\d\d(\s|$)')
        match = value_regex.search(text)
        if match is not None:
            value = match.group(0)
            value = re.sub(r'\n', '', value)
            values.append(value)
            new_text = re.sub(value, '', text)
            self._any_amount(new_text, values)
        try:
            values = [self.fix_value(value) for value in values]
            return sorted(values, reverse=True)[0]
        except IndexError:
            pass

    def fix_value(self, value):
        value = re.sub(r"\.", '', value)
        return re.sub(r",", ".", value)

    def pmt_date(self, text):
        text = self.reader.unpunctuate(text)
        match = re.search(
            r"(data do pagamento|debito em:|pagar em:|data da transferencia)(.*)", text.lower())
        if match is not None:
            match2 = re.search(
                r"\s\d\d(/|-|\.)\d\d(/|-|\.)2\d2\d", match.group(2))
            if match2 is not None:
                return match2.group()

    def any_date(self, text):
        match = re.search(r"data:(.*)", text.lower())
        if match is not None:
            match2 = re.search(
                r"\s\d\d(/|-|\.)\d\d(/|-|\.)2\d2\d", match.group(1))
            if match2 is not None:
                return match2.group(0)
        else:
            match3 = re.search(
                r"\d\d(/|-|\.)\d\d(/|-|\.)2\d2\d", text.lower())
            if match3 is not None:
                return match3.group(0)

    def written_date(self, text):
        match = re.search(r"\s\d\d\sde\s(\w*)\sde\s\d\d2\d", text.lower())
        if match is not None:
            writtenDate = str(match.group())
            dateparts = writtenDate.split()
            if dateparts[2] in MONTHS.keys():
                reformatted_date = f"{dateparts[0]}/{MONTHS[dateparts[2]]}/{dateparts[4]}"
            else:
                reformatted_date = None
            return reformatted_date
