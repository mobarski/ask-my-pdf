"PDF adapter"

import PyPDF2

def pdf_to_pages(file):
	"extract text (pages) from pdf file"
	pages = []
	pdf = PyPDF2.PdfReader(file)
	for p in range(len(pdf.pages)):
		page = pdf.pages[p]
		text = page.extractText()
		pages += [text]
	return pages
