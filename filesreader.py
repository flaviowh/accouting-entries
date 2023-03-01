"""This file reads PDFs with regular PDF extensions or OCR"""

import PyPDF2
import pdfplumber
import re
import pytesseract
import os
from pdf2image import convert_from_path
import configs
from PIL import Image
import shutil
import unicodedata
import string
import warnings
import logging
from PyQt5.QtCore import QThread, pyqtSignal
logging.basicConfig(format='- %(message)s')

# OCR DEPENDENCIES
pytesseract.pytesseract.tesseract_cmd = configs.TESSERACT



class ReadFiles:
    def read(self, file):
        if file.endswith(".pdf"):
            try:
                text = self._read_with_pypdf2(file)
                if self.is_valid(text):
                    return text
                else:
                    return self._read_with_pdfplumber(file)
            except Exception:
                pass
        elif file.endswith(".txt"):
            return open(file, "r", encoding="utf-8").read()

    def _read_with_pdfplumber(self, file):
        with pdfplumber.open(file) as pdf:
            pages = []
            for pagen in pdf.pages:
                text = pagen.extract_text()
                if text is not None:
                    pages.append(text)
            text = ''.join(pages)
        return text

    def _read_with_pypdf2(self, file):
        pdfFileObj = open(file, 'rb')
        # creating a pdf reader object
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        pages = []
        for page in range(0, pdfReader.numPages):
            pageObj = pdfReader.getPage(page)
            # extracting text from page
            pagetxt = pageObj.extractText()
            pages.append(pagetxt)
        return ''.join(pages)

    def is_valid(self, text):
        return True if len(text) >=100 else False

    def unpunctuate(self, text):
        """Remove all diacritic marks from Latin base characters"""
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


class PDFConverter(QThread):
    update_progress = pyqtSignal(int)
    update_text = pyqtSignal(str)
    finished = pyqtSignal(list)


    def __init__(self, path):
        super().__init__()
        self.preparator = PrepareFiles()
        self.path = path

    def run(self):
        path = self.path
        self.preparator.make_folders(path)
        text_list = self.conversions(path)
        logging.warning(f"Converted invoices: {len(text_list)}")
        self.update_text.emit("Processo completado")
        self.finished.emit(text_list)


    def conversions(self, dir):
        images_folder, text_folder = rf"{dir}\images", rf"{dir}\textfiles"
        logging.warning(f"\nLoading files...")
        self.update_text.emit("Carregando arquivos..")
        ocr_pdfs, readable_pdfs = self.preparator.filter_pdfs(dir)
        logging.warning("\nConverting PDFs")
        self.update_text.emit("Convertendo PDFs...")
        self.convert_pdf_to_text(readable_pdfs, text_folder)
        self.convert_pdf_to_image(ocr_pdfs, images_folder)
        if ocr_pdfs:
            logging.warning("\nReading files with OCR")
            self.update_text.emit("Lendo arquivos com OCR...")
        self.image_to_text_OCR(images_folder, text_folder)
        text_list = [os.path.join(text_folder, file) for file in os.listdir(
            text_folder) if file.endswith(".txt")]
        return text_list


    def convert_pdf_to_text(self, readable_pdfs, text_folder):
        reader = ReadFiles()
        for pdf in readable_pdfs:
            file_name = os.path.basename(pdf).removesuffix(".pdf")
            full_path = fr"{text_folder}\{file_name}.txt"
            if os.path.isfile(full_path) is False:
                text = reader.read(pdf)
                if text is None:
                    self.update_text.emit(f"Erro lendo arquivo: {pdf}")
                    warnings.warn(f"Error reading filtered file: {pdf}")
                    pass
                else:
                    with open(full_path, 'w', encoding="utf-8") as txtfile:
                            txtfile.write(text)
        self.update_progress.emit(60)


    def convert_pdf_to_image(self, ocr_list, images_folder):
        images_list = [os.path.join(images_folder, file) for file in os.listdir(
            images_folder) if file.endswith(".jpg")]
        for pdf_file in ocr_list:
            try:
                match = re.search(
                    (os.path.basename(pdf_file)[:-5]), str(images_list))
                if match is None:
                    pages = convert_from_path(
                        pdf_file, 500, grayscale=True, poppler_path=configs.POPPLER)
                    for i in range(len(pages)):
                        image = f"{images_folder}\{os.path.basename(pdf_file)[:-5]}{str(i)}.jpg"
                        pages[i].save(image, "JPEG")
            except Exception:
                pass
        self.update_progress.emit(75)

    def image_to_text_OCR(self, images_folder, text_folder):
        valid_types = (".jpg", ".png", ".jpeg", ".bmp")
        images_list = [os.path.join(images_folder, file) for file in os.listdir(
            images_folder) if file.endswith(valid_types)]
        total = len(images_list)
        rate = total / 20
        start = 75
        for image in images_list:
            filepath = fr"{text_folder}\{os.path.basename(image)[:-5]}.txt"
            if os.path.isfile(filepath) is False:
                with open(filepath, 'a', encoding='utf -8') as output:
                    output.write(pytesseract.image_to_string(
                        Image.open(image), lang='por'))
                    output.close()
                    self.update_progress.emit(round(start + rate))


class PrepareFiles:

    def make_folders(self, path):
        os.makedirs(rf"{path}\images", exist_ok=True)
        os.makedirs(rf"{path}\textfiles", exist_ok=True)
        return rf"{path}\images", rf"{path}\textfiles"

    def separate_files(self, path):
        images_folder, text_folder = self.make_folders(path)
        allfileslist = [os.path.join(path, file) for file in os.listdir(path)]
        valid_types = (".png", ".jpeg", ".jpg", ".bmp")
        for file in allfileslist:
            if file.endswith(valid_types):
                shutil.move(file, images_folder)
            if file.endswith(".txt") and not "extrato" in os.path.basename(file).lower():
                shutil.copy(file, text_folder)
        return images_folder, text_folder

    def filter_pdfs(self, path):
        reader = ReadFiles()
        logging.warning("Filtering PDFs...")
        all_pdfs = [os.path.join(path, file)
                    for file in os.listdir(path) if file.endswith(".pdf")]
        ocr_pdfs = []
        regular_pdfs = []
        for pdf in all_pdfs:
            text = reader.read(pdf)
            if self.is_valid(text):
                regular_pdfs.append(pdf)
            else:
                ocr_pdfs.append(pdf)
        logging.warning(f"OCR pdfs : {len(ocr_pdfs)}")
        logging.warning(f"readable pdfs : {len(regular_pdfs)}")
        return ocr_pdfs, regular_pdfs

    def is_valid(self, text):
        if text is not None:
            return True if len(text) >= 50 else False
        else:
            return False

