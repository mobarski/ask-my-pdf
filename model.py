from sklearn.metrics.pairwise import cosine_distances
import pdf
import ai
import re

def use_key(api_key):
	ai.use_key(api_key)

def query_by_vector(vector, index, limit=None):
	vectors = index['vectors']
	texts = index['texts']
	#
	sim = cosine_distances([vector], vectors)[0]
	#
	id_dist_list = list(enumerate(sim))
	id_dist_list.sort(key=lambda x:x[1])
	id_list   = [x[0] for x in id_dist_list][:limit]
	dist_list = [x[1] for x in id_dist_list][:limit]
	text_list = [texts[x] for x in id_list] if texts else ['ERROR']*len(id_list)
	return id_list, dist_list, text_list

def get_vectors(text_list, pg=None):
	vectors = []
	for i,text in enumerate(text_list):
		resp = ai.embedding(text)
		v = resp['vector']
		vectors += [v]
		if pg:
			pg.progress((i+1)/len(text_list))
	return vectors

def index_file(f, fix_text=False, frag_size=0, pg=None):
	pages = pdf.pdf_to_pages(f)
	if fix_text:
		for i in range(len(pages)):
			pages[i] = fix_text_errors(pages[i], pg)
	texts = split_pages_into_fragments(pages, frag_size)
	vectors = get_vectors(texts, pg)
	out = {}
	out['pages']   = pages
	out['texts']   = texts
	out['vectors'] = vectors
	return out

def split_pages_into_fragments(pages, frag_size):
	page_offset = [0]
	for p,page in enumerate(pages):
		page_offset += [page_offset[-1]+len(page)+1]
	# TODO: del page_offset[-1] ???
	if frag_size:
		text = ' '.join(pages)
		return text_to_fragments(text, frag_size, page_offset)
	else:
		return pages

def text_to_fragments(text, size, page_offset):
	if size and len(text)>size:
		out = []
		pos = 0
		eos = find_eos(text)
		if len(text) not in eos:
			eos += [len(text)]
		for i in range(len(eos)):
			if eos[i]-pos>size:
				out += [text[pos:eos[i]]]
				pos = eos[i]
		out += [text[pos:eos[i]]]
		out = [x for x in out if x]
		return out
	else:
		return [text]

def find_eos(text):
	return [x.span()[1] for x in re.finditer('[.!?]\s+',text)]

###############################################################################

def fix_text_errors(text, pg=None):
	return re.sub('\s+[-]\s+','',text)

def query(text, index, task=None, temperature=0.0, max_frags=1, hyde=False, hyde_prompt=None, limit=None):
	out = {}
	
	if hyde:
		out['hyde'] = hypotetical_answer(text, index, hyde_prompt=hyde_prompt, temperature=temperature)
	
	# RANK FRAGMENTS
	if hyde:
		resp = ai.embedding(out['hyde']['text'])
	else:
		resp = ai.embedding(text)
	v = resp['vector']
	id_list, dist_list, text_list = query_by_vector(v, index, limit=limit)
	
	# BUILD PROMPT
	
	# build context
	context = ''
	context += text_list[0]
	context_len = ai.get_token_count(context)
	pages_cnt = 1
	for i in range(1,min(max_frags,len(id_list))):
		page_len = ai.get_token_count(text_list[i])
		if context_len+page_len <= 3000: # TODO: remove hardcode
			context += '\n---\n'+text_list[i]
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

def hypotetical_answer(text, index, hyde_prompt=None, temperature=0.0):
	hyde_prompt = hyde_prompt or 'Write document that answers the question.'
	prompt = f"""
	{hyde_prompt}
	Question: "{text}"
	Document:"""
	resp = ai.complete(prompt, temperature=temperature)
	return resp


if __name__=="__main__":
	print(text_to_fragments("to jest. test tego. programu", size=10))
	