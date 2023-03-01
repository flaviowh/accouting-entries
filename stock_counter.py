import os
import xml.etree.ElementTree as ET
import re
import send2trash

# OLD XML CODE  USING  REGEX


def cfop_5655(xml):
    """Confirms CFOP"""
    match= re.search(r"CFOP>5655", xml)
    if match is not None:
        return True


def cfop_fix(xml):
    """Confirms CFOP"""
    match= re.search(r"CFOP>5656", xml)
    cfop5656 = None
    glp13kg = None
    if match is not None:
        cfop5656 = True
    match = re.search(r"GLP EM BOTIJAO DE 13 KG", xml)
    if match is not None:
        glp13kg = True
    if cfop5656 and glp13kg is True:
        return True
    else:
        return False


def cfop_6655(xml):
    """Confirms CFOP"""
    match= re.search(r"CFOP>6655", xml)
    if match is not None:
        return True


def find_date(xml):
    match = re.search(r"\d\d\d\d-\d\d-\d\d", xml)
    if match is not None:
        data = (match.group(0))
        return data


def find_vendor(xml):
    match = re.search(r"xNome>.........", xml)
    if match is not None:
        vendor = (match.group(0)).removeprefix("xNome>")
        return vendor


def find_quantity(xml):
    match = re.search(r"<qCom>\d.....", xml)
    if match is not None:
        quantity = re.findall(r'\d+', (match.group(0)))[0]
        return quantity


def find_uni(xml):
    match = re.search(r"vUnCom>\d....", xml)
    if match is not None:
        uni = (match.group(0)).removeprefix("vUnCom>")
        return uni


def find_nf_number(xml):
    match = re.search(r"nNF>\d\d\d...", xml)
    if match is not None:
        nfnum = re.findall(r'\d+', (match.group(0)))[0]
        return nfnum


def find_cfop(xml):
    match = re.search(r"<CFOP>\d\d\d\d</CFOP>", xml)
    if match is not None:
        cfop = re.findall(r'\d+', (match.group(0)))[0]
        return cfop


def add_total(xml_info):
    total = float(xml_info["Quantidade"]) * float(xml_info["Valor Uni."])
    return round(total, 2)


def fix_float_values(line):
    newline = re.sub("\.", ",", str(line))
    return newline


#  NEW CODE


def clean_folder(path):
    """removes event files"""
    files_list = [os.path.join(path, xml) for xml in os.listdir(path)]
    for file in files_list:
        filename = os.path.basename(file)
        if "evento" in filename.lower():
            send2trash.send2trash(file)


def filter_cfops(root):
    """looks for intended CFOPS"""
    accepted = ["5655", "6655"]
    try:
        cfop = root[0][0][4][0][5].text
        if cfop in accepted:
            return True
    except Exception:
        return False


def cfop_fix_new(file):
    with open(file, 'r') as f:
        xml = f.read()
        """Confirms CFOP"""
        match= re.search(r"CFOP>5656", xml)
        cfop5656 = None
        glp13kg = None
        if match is not None:
            cfop5656 = True
        match = re.search(r"GLP EM BOTIJAO DE 13 KG", xml)
        if match is not None:
            glp13kg = True
        if cfop5656 and glp13kg is True:
            return True
        else:
            return False


def fix_dates(date):
    """fixes the dates"""
    day, year = date[-2:], date[:4]
    month = date[5:7]
    return f"{day}/{month}/{year}"


def filter_by_custom_cfop(xml, cfops):
    xml = open(xml, 'r').read()
    if "Qualquer" not in cfops:
        for cfop in cfops:
            find_this_cfop = re.search(rF"<CFOP>{cfop}</CFOP>", xml)
            if find_this_cfop is not None:
                return True
    else:
        return True


def create_glp_dict_with_regex(xml_path):
    with open(xml_path, 'r') as current_xml:
        try:
            content = current_xml.read()
            if cfop_5655(content) or cfop_6655(content) or cfop_fix(content) is True:
                xml_info = {"Data": find_date(content), "Nota Fiscal": find_nf_number(content),
                            "Quantidade": find_quantity(content), "Valor total": '', "Valor Uni.": find_uni(content),
                            "Fornecedor": find_vendor(content)}
                xml_info["Valor total"] = round(float(xml_info["Quantidade"]) * float(xml_info["Valor Uni."]), 2)
                xml_info["Valor total"] = fix_float_values(xml_info["Valor total"])
                xml_info["Valor Uni."] = fix_float_values(xml_info["Valor Uni."])
                return xml_info
        except Exception:
            pass


def create_glp_list(path):
    xmls = [os.path.join(path, xml) for xml in os.listdir(path) if xml.endswith(".xml")]
    """creates the NFe lists"""
    all_nfes = []
    for xml in xmls:
        try:
            tree = ET.parse(xml)
            root = tree.getroot()
            if filter_cfops(root) or cfop_fix_new(xml) is True:
                xml_info = {"Data": fix_dates(root[0][0][0][6].text[:10]), "Nota Fiscal": root[0][0][0][5].text,
                            "Quantidade": re.sub("\.0000", '', root[0][0][4][0][7].text), "Valor total": '',
                            "Valor Uni.": re.sub("0{8}", '', root[0][0][4][0][8].text),
                            "Fornecedor": root[0][0][1][1].text[:15]}
                xml_info["Valor total"] = round(float(xml_info["Valor Uni."]) * float(xml_info["Quantidade"]), 2)
                xml_info["Valor total"] = re.sub("\.", ',', str(xml_info["Valor total"]))
                xml_info["Valor Uni."] = fix_float_values(xml_info["Valor Uni."])
                all_nfes.append(xml_info)
        except Exception:
            # if XML module fails (most likely to reading problems with the xml), we try using Regex
            xml_info = create_glp_dict_with_regex(xml)
            if xml_info is not None:
                all_nfes.append(xml_info)
    return all_nfes


def extract_value_from_xml(xml, keyword):
    import xml.dom.minidom as minidom
    doc = minidom.parse(xml)
    elements = doc.getElementsByTagName(keyword)[0]
    for node in elements.childNodes:
        if node.nodeType == node.TEXT_NODE:
            return node.data


def create_nfe_list_from_custom_cfops(path, cfops):
    xmls = [os.path.join(path, xml) for xml in os.listdir(path) if xml.endswith(".xml")]
    """creates the NFe lists"""
    all_nfes = []
    for xml in xmls:
        if filter_by_custom_cfop(xml, cfops) is True:
            try:
                tree = ET.parse(xml)
                root = tree.getroot()
                xml_info = {"Data": fix_dates(root[0][0][0][6].text[:10]),
                            "Nota Fiscal": extract_value_from_xml(xml,"nNF"),
                            "Valor total NF": extract_value_from_xml(xml, 'vNF'),
                            "ICMS incluso": extract_value_from_xml(xml,'vICMS'),
                            "Frete pago": extract_value_from_xml(xml,'vFrete'),
                            "Seguro pago": extract_value_from_xml(xml,'vSeg'),
                            "Emitente":root[0][0][1][1].text}
                all_nfes.append(xml_info)
            except Exception:
                pass
    if len(all_nfes) > 0:
        return all_nfes



def find_nfe(nf_num, path):
    files_list = [os.path.join(path, xml) for xml in os.listdir(path)]
    for file in files_list:
        filename = os.path.basename(file)
        busca = re.search(nf_num, filename)
        if busca is not None:
            return file


def process_nfes(folder, cfops):
    if "5565" in cfops:
        all_nfe = create_glp_list(folder)
        return all_nfe
    else:
        return create_nfe_list_from_custom_cfops(folder, cfops)


# TESTS HERE  v



#examine_xml(test_path)

#print(find_nfe('81393', test_path))

# XML root adressess
# NFe                  root[0][0][0][5].text
# Nome emitente        root[0][0][1][1].text
# Nome recipiente      root[0][0][2][1].text
# CFOP                 root[0][0][4][0][5].text
# quantidade           root[0][0][4][0][7].text   (remove ".000")
# valor unit           root[0][0][4][0][8].text
# data                 root[0][0][0][6].text[:10]

# for any cfop
# total produtos       root[0][0][-5][0][0].text
# frete total produtos       root[0][0][-5][0][12].text
# seguro total produtos     root[0][0][-5][0][13].text
# ICMS total                root[0][0][-5][0][1].text


