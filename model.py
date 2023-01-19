
from sklearn.metrics.pairwise import cosine_distances

def query_by_vector(vector, db, limit=None):
	vectors = db['vectors']
	texts = db['texts']
	#
	sim = cosine_distances([vector], vectors)[0]
	#
	id_dist_list = list(enumerate(sim))
	id_dist_list.sort(key=lambda x:x[1])
	id_list   = [x[0] for x in id_dist_list][:limit]
	dist_list = [x[1] for x in id_dist_list][:limit]
	text_list = [texts[x] for x in id_list] if texts else ['ERROR']*len(id_list)
	return id_list, dist_list, text_list

def index_pages(pages, pg=None):
	vectors = []
	for p,page in enumerate(pages):
		resp = ai.embedding(page)
		v = resp['vector']
		vectors += [v]
		if pg:
			pg.progress((p+1)/len(pages))
	return vectors

###############################################################################

import ai
import re

def fix_text_errors(text, pg=None):
	return re.sub('\s+[-]\s+','',text)

def query(text, db, task=None, temperature=0.0, max_pages=1, hyde=False, limit=None):
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
	
	# build context
	context = ''
	context += raw_list[0]
	context_len = ai.get_token_count(context)
	pages_cnt = 1
	for i in range(1,max_pages):
		page_len = ai.get_token_count(raw_list[i])
		if context_len+page_len <= 3000: # TODO: remove hardcode
			context += '\n\n'+raw_list[i]
			context_len += page_len
			pages_cnt +=1
	out['context_pages_cnt'] = pages_cnt
	out['context_len'] = context_len
	prompt = f"""
		{task or 'Task: Answer question based on context.'}
		
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
