"AI (LLM) adapter"
# TODO: replace with ai_bricks.ai_openai

BUTCHER_EMBEDDINGS = None # this should be None, as it cuts the embedding vector to n first values (for debugging)


import tiktoken
encoder = tiktoken.encoding_for_model("text-davinci-003")
def get_token_count(text):
	tokens = encoder.encode(text)
	return len(tokens)


# REF: https://platform.openai.com/docs/models
def get_model_max_tokens(model):
	model_max_tokens = {
		'gpt-3.5-turbo':4096,
		'text-davinci-003':4000,
		'text-davinci-002':4000,
		'text-davinci-001':4000,
		'code-davinci-002':8000,
	}
	return model_max_tokens.get(model, 2048)

def is_chat(model):
	return model.startswith('gpt') # TODO


import openai

def use_key(api_key):
	openai.api_key = api_key

def complete(prompt, temperature=0.0, model=None):
	model = model or 'text-davinci-003'
	kwargs = dict(
		model = model,
		max_tokens = get_model_max_tokens(model) - get_token_count(prompt),
		temperature = temperature,
		n = 1,
	)
	out = {}
	if is_chat(model):
		kwargs['messages'] = [
				{'role':'system', 'content':'output only in raw text'},
				{'role':'user',   'content':prompt},
			]
		kwargs['max_tokens'] -= 30 # UGLY: workaround for not counting chat specific tokens
		resp = openai.ChatCompletion.create(**kwargs) # API CALL
		out['text'] = resp['choices'][0]['message']['content']
	else:
		kwargs['prompt'] = prompt
		resp = openai.Completion.create(**kwargs) # API CALL
		out['text']  = resp['choices'][0]['text']
	out['usage'] = resp['usage']
	out['model'] = model
	return out


def embedding(text, model=None):
	model = model or "text-embedding-ada-002"
	resp = openai.Embedding.create(
		input=text,
		model=model,
	)
	out = {}
	out['vector'] = list(resp['data'][0]['embedding'][:BUTCHER_EMBEDDINGS])
	out['usage']  = dict(resp['usage'])
	out['model'] = model
	return out

