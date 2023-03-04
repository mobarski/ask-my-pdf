"PDF adapter"

import pypdf

def pdf_to_pages(file):
	"extract text (pages) from pdf file"
	pages = []
	pdf = pypdf.PdfReader(file)
	for p in range(len(pdf.pages)):
		page = pdf.pages[p]
		text = page.extract_text()
		pages += [text]
	return pages
