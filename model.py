from sklearn.metrics.pairwise import cosine_distances

def query_by_vector(vector, db, limit=None):
	vectors = db['vectors']
	texts = db['texts']
	print('index.query', vector, len(vectors), flush=True) # XXX
	#
	sim = cosine_distances([vector], vectors)[0]
	#
	id_dist_list = list(enumerate(sim))
	id_dist_list.sort(key=lambda x:x[1])
	id_list   = [x[0] for x in id_dist_list][:limit]
	dist_list = [x[1] for x in id_dist_list][:limit]
	text_list = [texts[x] for x in id_list] if texts else ['ERROR']*len(id_list)
	return id_list, dist_list, text_list

def index_pages(pages):
	vectors = []
	for p,page in enumerate(pages):
		resp = ai.embedding(page)
		v = resp['vector']
		vectors += [v]
	return vectors

###############################################################################

import ai

def query(text, db, temperature=0.0, hyde=False, limit=None):
	out = {}
	
	if hyde:
		out['hyde'] = hypotetical_answer(text, db, temperature=temperature)
	
	# RANK PAGES
	if hyde:
		resp = ai.embedding(out['hyde']['text'])
	else:
		resp = ai.embedding(text)
	v = resp['vector']
	id_list, dist_list, raw_list = query_by_vector(v, db, limit=limit)
	
	# BUILD PROMPT
	context = raw_list[0]
	prompt = f"""
		Answer question based on context.
		
		Context:
		{context}
		
		Question: {text}
		
		Answer:"""
	
	# GET ANSWER
	resp2 = ai.complete(prompt, temperature=temperature)
	answer = resp2['text']
	usage = resp2['usage']
	
	# OUTPUT
	out['id_list'] = id_list
	out['dist_list'] = dist_list
	#out['query.vector'] = resp['vector']
	out['usage'] = usage
	out['prompt'] = prompt
	out['text'] = answer
	return out

def hypotetical_answer(text, db, temperature=0.0):
	prompt = f"""
	Write document that answers the question: "{text}"
	Document:"""
	resp = ai.complete(prompt, temperature=temperature)
	return resp
