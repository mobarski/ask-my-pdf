# INFO: some prompts are still in model.py

# TODO: Ignore OCR problems in the text below.

TASK = {
	'v6': (
			"Answer the question truthfully based on the text below. "
			"Include verbatim quote and a comment where to find it in the text (page number). "
			#"After the quote write a step by step explanation in a new paragraph. "
			"After the quote write a step by step explanation. "
			"Use bullet points. "
			#"After that try to rephrase the original question so it might give better results. " 
		),
	'v5': (
			"Answer the question truthfully based on the text below. "
			"Include at least one verbatim quote (marked with quotation marks) and a comment where to find it in the text (ie name of the section and page number). "
			"Use ellipsis in the quote to omit irrelevant parts of the quote. "
			"After the quote write (in the new paragraph) a step by step explanation to be sure we have the right answer "
			"(use bullet-points in separate lines)" #, adjust the language for a young reader). "
			"After the explanation check if the Answer is consistent with the Context and doesn't require external knowledge. "
			"In a new line write 'SELF-CHECK OK' if the check was successful and 'SELF-CHECK FAILED' if it failed. " 
		),
	'v4':
		"Answer the question truthfully based on the text below. " \
		"Include verbatim quote and a comment where to find it in the text (ie name of the section and page number). " \
		"After the quote write an explanation (in the new paragraph) for a young reader.",
	'v3': 'Answer the question truthfully based on the text below. Include verbatim quote and a comment where to find it in the text (ie name of the section and page number).',
	'v2': 'Answer question based on context. The answers sould be elaborate and based only on the context.',
	'v1': 'Answer question based on context.',
	# 'v5':
		# "Generate a comprehensive and informative answer for a given question solely based on the provided document fragments. " \
		# "You must only use information from the provided fragments. Use an unbiased and journalistic tone. Combine fragments together into coherent answer. " \
		# "Do not repeat text. Cite fragments using [${number}] notation. Only cite the most relevant fragments that answer the question accurately. " \
		# "If different fragments refer to different entities with the same name, write separate answer for each entity.",
}

HYDE = "Write an example answer to the following question. Don't write generic answer, just assume everything that is not known."

# TODO
SUMMARY = {
	'v2':'Describe the document from which the fragment is extracted. Omit any details.',
	'v1':'Describe the document from which the fragment is extracted. Do not describe the fragment, focus on figuring out what kind document it is.',
}
