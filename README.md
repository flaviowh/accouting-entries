# accouting-entries
My first Python application to read and match bank statement entries

Before anything, notice this is just for showcase and needs a lot of refactoring and better design. It was my first ever application written 2 months into learning how to code.

The program reads bank statements saved as .txt , payment receipts as PDF or image files with Tesseract OCR and the two entry types are matched using keywords stored in a SQL3 editable database.

My more recent repo has classes that read OFX and PDF directly with specialized libraries. Ideally, clients should send their statements as OFX and receipts as readable PDFs or organized in excel sheets, but this rarely happens. Although OCR, regular expressions and machine learning classifiers are all prone to error, they have helped me and saved hours of useless typing.

Requires separate installation of Tesseract, Poppler and SQLLiteStudio and setting their paths in the config file.

If you'd like to contribute or have any questions, contact me.

![Captura de tela_20230301_171202](https://user-images.githubusercontent.com/91790030/222265326-fbb022b1-3371-4015-8998-67b8c922b1ff.png)
![Captura de tela_20230301_171247](https://user-images.githubusercontent.com/91790030/222265320-21fe2acb-afad-478b-9f69-eff1a9269c15.png)
![Captura de tela_20230301_171621](https://user-images.githubusercontent.com/91790030/222265323-6bb5615b-e1ab-4322-bb4b-d1593d1fcf2b.png)

