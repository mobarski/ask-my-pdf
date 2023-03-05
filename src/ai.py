from ai_bricks.api import openai
import stats

def use_key(key):
	openai.use_key(key)

usage_stats = None
def set_user(user):
	global usage_stats
	usage_stats = stats.get_stats(user=user)
	openai.set_global('user', user)
	openai.add_callback('after', stats_callback)

def complete(text, **kw):
	model = kw.get('model','gpt-3.5-turbo')
	llm = openai.model(model)
	llm.config['pre_prompt'] = 'output only in raw text' # for chat models
	resp = llm.complete(text, **kw)
	resp['model'] = model
	return resp

def embedding(text, **kw):
	model = kw.get('model','text-embedding-ada-002')
	llm = openai.model(model)
	resp = llm.embed(text, **kw)
	resp['model'] = model
	return resp

tokenizer_model = openai.model('text-davinci-003')
def get_token_count(text):
	return tokenizer_model.token_count(text)

def stats_callback(out, resp, self):
	model = self.config['model']
	usage = resp['usage']
	usage_stats.incr(f'usage:v4:[date]:[user]', {f'{k}:{model}':v for k,v in usage.items()})
	usage_stats.incr(f'hourly:v4:[date]',       {f'{k}:{model}:[hour]':v for k,v in usage.items()})
