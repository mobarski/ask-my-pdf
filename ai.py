"AI (LLM) adapter"

BUTCHER_EMBEDDINGS = None # this should be None, as it cuts the embedding vector to n first values (for debugging)

import openai

def use_key(api_key):
	openai.api_key = api_key

def complete(prompt):
	kwargs = dict(
		model = 'text-davinci-003',
		max_tokens = 2000,
		temperature = 0.0,
		prompt = prompt,
		n = 1,
	)
	resp = openai.Completion.create(**kwargs)
	out = {}
	out['text']  = resp['choices'][0]['text']
	out['usage'] = resp['usage']
	return out


def embedding(text):
	resp = openai.Embedding.create(
		input=text,
		model="text-embedding-ada-002",
	)
	out = {}
	out['vector'] = list(resp['data'][0]['embedding'][:BUTCHER_EMBEDDINGS])
	out['usage']  = dict(resp['usage'])
	return out

