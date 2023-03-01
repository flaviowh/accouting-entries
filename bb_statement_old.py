"""This module reads and extracts info from a txt file of a BB bank statement"""
import re

class BBStatementOld:

    def get_value_BB(self, text):
        m = "r\d.\d\d\d.\d\d\d,\d\d\s[C|D]"
        att =[m, m[4:], m[6:], m[8:], m[11:], m[13:], m[15:]]
        for n in att:
            try:
                attempt = re.search(f"{n}", text)
                value = attempt.group(0)
                return value
            except Exception:
                pass


    def filter_BB(self, statement):
        """first filter for BB statement"""
        lines2, lines3, lines4, lines5, lines6, lines7, lines8, lines = [], [], [], [], [], [], [],[],
        with open(statement, "r", encoding='utf-8') as f:
            big_text = f.read()
            deleted_spaces = re.sub(r"\n", ' ', big_text)
            try:
                result = re.search("Anterior(.*)S A L D O", deleted_spaces)
                content = result.group(1)
            except AttributeError:
                try:
                    result = re.search("Anterior(.*)SALDO", deleted_spaces)
                    content = result.group(1)
                except AttributeError:
                    print("\nErro ao ler o extrato BB. Verifique o arquivo e tente novamente")
                    input("\nsair")
            lines1 = re.split(r'.(?=\d\d/\d\d/\d\d\d\d)', content)
            for line in lines1:
                clean_line1 = re.sub(r"\d\d\d.\d\d\d.\d\d\d\s", "      ", line)
                lines2.append(clean_line1)
            for line in lines2:
                clean_line2 = re.sub(r"\s\d\d.\d\d\d.\d\d\d\s", '       ', line)
                lines3.append(clean_line2)
            for line in lines3:
                clean_line3 = re.sub(r"\s0,00\s", "        ", line)
                lines4.append(clean_line3)
            for line in lines4:
                clean_line4 = re.sub(r"\s\d\d\d.\d\d\d\s", '       ', line)
                lines5.append(clean_line4)
            for line in lines5:
                clean_line5 = re.sub(r"\s\d\d\s", "        ", line)
                lines6.append(clean_line5)
            for line in lines6:
                clean_line6 = re.sub("[.|\s]\d\d\d\s", '        ', line)
                lines7.append(clean_line6)
            for line in lines7:
                clean_line7 = re.sub("\s\d\s", "      ", line)
                lines.append(clean_line7)
            #  First filter for confusing lines
            filters = ["Complementares", "Saldo Anterior", "S A L D O", "Período do extrato"]
            filtered_text = []
            for line in lines:
                if not any(word in line for word in filters):
                    filtered_text.append(line)
            return filtered_text


    def filter_BB_2(self, statement):
        """second filter for BB statement"""
        raw_dict_list = []
        for line in self.filter_BB(statement):
            raw_dict = {"date":[], "value": [],"info": []}
            match = re.match(r"\d\d/\d\d/\d\d\d\d", line)
            if match is not None:
                raw_dict["date"] = match.group(0)
            raw_dict["value"] = self.get_value_BB(line)
            raw_dict["info"] = re.sub (r'([^a-zA-Z\s]+?)', '', line)  # remove anything but letters and space
            raw_dict["info"] = re.sub(r"\s\w\s", '', raw_dict["info"])
            if raw_dict["value"] is not None:
                raw_dict_list.append(raw_dict)
        return raw_dict_list


    def raw_statement(self, statement):
        """prepares a raw BB statement list in the form of dictionaries"""
        raw_statement = []
        for dict in self.filter_BB_2(statement):
            if "D" in dict["value"]:
                dict["value"] = dict["value"].replace(" D", '')
                dict["value"] = ("-"+dict["value"])
            elif "C" in dict["value"]:
                dict["value"] = dict["value"].replace(" C", '')
            dict["value"] = dict["value"].replace(".", '')
            dict["value"] = dict["value"].replace(",", '.')
            raw_statement.append(dict)
        for dict in raw_statement:
            match = re.search("-", dict["value"])
            if match is not None:
                dict["value"] = re.sub("-", '', dict["value"])
                dict["entrada"] = False
            else:
                dict["entrada"] = True
        return raw_statement








