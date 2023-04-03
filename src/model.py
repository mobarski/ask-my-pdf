from sklearn.metrics.pairwise import cosine_distances

import datetime
from collections import Counter
from time import time as now
import hashlib
import re
import io
import os

import pdf
import ai

def use_key(api_key):
	ai.use_key(api_key)

def set_user(user):
	ai.set_user(user)

def query_by_vector(vector, index, limit=None):
	"return (ids, distances and texts) sorted by cosine distance"
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

def get_vectors(text_list):
	"transform texts into embedding vectors"
	batch_size = 128
	vectors = []
	usage = Counter()
	for i,texts in enumerate(batch(text_list, batch_size)):
		resp = ai.embeddings(texts)
		v = resp['vectors']
		u = resp['usage']
		u['call_cnt'] = 1
		usage.update(u)
		vectors.extend(v)
	return {'vectors':vectors, 'usage':dict(usage), 'model':resp['model']}

def index_file(f, filename, fix_text=False, frag_size=0, cache=None):
	"return vector index (dictionary) for a given PDF file"
	# calc md5
	h = hashlib.md5()
	h.update(f.read())
	md5 = h.hexdigest()
	filesize = f.tell()
	f.seek(0)
	#
	t0 = now()
	pages = pdf.pdf_to_pages(f)
	t1 = now()
	
	if fix_text:
		for i in range(len(pages)):
			pages[i] = fix_text_problems(pages[i])
	texts = split_pages_into_fragments(pages, frag_size)
	t2 = now()
	if cache:
		cache_key = f'get_vectors:{md5}:{frag_size}:{fix_text}'
		resp = cache.call(cache_key, get_vectors, texts)
	else:
		resp = get_vectors(texts)
	
	t3 = now()
	vectors = resp['vectors']
	summary_prompt = f"{texts[0]}\n\nDescribe the document from which the fragment is extracted. Omit any details.\n\n" # TODO: move to prompts.py
	summary = ai.complete(summary_prompt)
	t4 = now()
	usage = resp['usage']
	out = {}
	out['frag_size'] = frag_size
	out['n_pages']   = len(pages)
	out['n_texts']   = len(texts)
	out['texts']     = texts
	out['pages']     = pages
	out['vectors']   = vectors
	out['summary']   = summary['text']
	out['filename']  = filename
	out['filehash']  = f'md5:{md5}'
	out['filesize']  = filesize
	out['usage']     = usage
	out['model']     = resp['model']
	out['time']      = {'pdf_to_pages':t1-t0, 'split_pages':t2-t1, 'get_vectors':t3-t2, 'summary':t4-t3}
	out['size']      = len(texts)   # DEPRECATED -> filesize
	out['hash']      = f'md5:{md5}' # DEPRECATED -> filehash
	return out

def split_pages_into_fragments(pages, frag_size):
	"split pages (list of texts) into smaller fragments (list of texts)"
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
	"split single text into smaller fragments (list of texts)"
	if size and len(text)>size:
		out = []
		pos = 0
		page = 1
		p_off = page_offset.copy()[1:]
		eos = find_eos(text)
		if len(text) not in eos:
			eos += [len(text)]
		for i in range(len(eos)):
			if eos[i]-pos>size:
				text_fragment = f'PAGE({page}):\n'+text[pos:eos[i]]
				out += [text_fragment]
				pos = eos[i]
				if eos[i]>p_off[0]:
					page += 1
					del p_off[0]
		# ugly: last iter
		text_fragment = f'PAGE({page}):\n'+text[pos:eos[i]]
		out += [text_fragment]
		#
		out = [x for x in out if x]
		return out
	else:
		return [text]

def find_eos(text):
	"return list of all end-of-sentence offsets"
	return [x.span()[1] for x in re.finditer('[.!?。]\s+',text)]

###############################################################################

def fix_text_problems(text):
	"fix common text problems"
	text = re.sub('\s+[-]\s+','',text) # word continuation in the next line
	return text

def query(text, index, task=None, temperature=0.0, max_frags=1, hyde=False, hyde_prompt=None, limit=None, n_before=1, n_after=1, model=None):
	"get dictionary with the answer for the given question (text)."
	out = {}
	
	if hyde:
		# TODO: model param
		out['hyde'] = hypotetical_answer(text, index, hyde_prompt=hyde_prompt, temperature=temperature)
		# TODO: usage
	
	# RANK FRAGMENTS
	if hyde:
		resp = ai.embedding(out['hyde']['text'])
		# TODO: usage
	else:
		resp = ai.embedding(text)
		# TODO: usage
	v = resp['vector']
	t0 = now()
	id_list, dist_list, text_list = query_by_vector(v, index, limit=limit)
	dt0 = now()-t0
	
	# BUILD PROMPT
	
	# select fragments
	N_BEFORE = 1 # TODO: param
	N_AFTER =  1 # TODO: param
	selected = {} # text id -> rank
	for rank,id in enumerate(id_list):
		for x in range(id-n_before, id+1+n_after):
			if x not in selected and x>=0 and x<index['size']:
				selected[x] = rank
	selected2 = [(id,rank) for id,rank in selected.items()]
	selected2.sort(key=lambda x:(x[1],x[0]))
	
	# build context
	SEPARATOR = '\n---\n'
	context = ''
	context_len = 0
	frag_list = []
	for id,rank in selected2:
		frag = index['texts'][id]
		frag_len = ai.get_token_count(frag)
		if context_len+frag_len <= 3000: # TODO: remove hardcode
			context += SEPARATOR + frag # add separator and text fragment
			frag_list += [frag]
			context_len = ai.get_token_count(context)
	out['context_len'] = context_len
	prompt = f"""
		{task or 'Task: Answer question based on context.'}
		
		Context:
		{context}
		
		Question: {text}
		
		Answer:""" # TODO: move to prompts.py
	
	# GET ANSWER
	resp2 = ai.complete(prompt, temperature=temperature, model=model)
	answer = resp2['text']
	usage = resp2['usage']
	
	# OUTPUT
	out['vector_query_time'] = dt0
	out['id_list'] = id_list
	out['dist_list'] = dist_list
	out['selected'] = selected
	out['selected2'] = selected2
	out['frag_list'] = frag_list
	#out['query.vector'] = resp['vector']
	out['usage'] = usage
	out['prompt'] = prompt
	out['model'] = resp2['model']
	# CORE
	out['text'] = answer
	return out

def hypotetical_answer(text, index, hyde_prompt=None, temperature=0.0):
	"get hypotethical answer for the question (text)"
	hyde_prompt = hyde_prompt or 'Write document that answers the question.'
	prompt = f"""
	{hyde_prompt}
	Question: "{text}"
	Document:""" # TODO: move to prompts.py
	resp = ai.complete(prompt, temperature=temperature)
	return resp


def community_tokens_available_pct():
	used = ai.get_community_usage_cost()
	limit = float(os.getenv('COMMUNITY_DAILY_USD',0))
	pct = (100.0 * (limit-used) / limit) if limit else 0
	pct = max(0, pct)
	pct = min(100, pct)
	return pct


def community_tokens_refresh_in():
	x = datetime.datetime.now()
	dt = (x.replace(hour=23, minute=59, second=59) - x).seconds
	h = dt // 3600
	m = dt  % 3600 // 60
	return f"{h} h {m} min"

# util
def batch(data, n):
	for i in range(0, len(data), n):
		yield data[i:i+n]

if __name__=="__main__":
	print(text_to_fragments("to jest. test tego. programu", size=3, page_offset=[0,5,10,15,20]))
