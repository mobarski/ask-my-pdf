import datetime
import hashlib
import redis
import os
from retry import retry

def hexdigest(text):
	return hashlib.md5(text.encode('utf8')).hexdigest()

def as_int(x):
	return int(x) if x is not None else None

class Feedback:
	"Dummy feedback adapter"
	def __init__(self, user):
		...
	def send(self, score, ctx, details=False):
		...
	def get_score(self):
		return 0

class RedisFeedback(Feedback):
	"Redis feedback adapter"
	def __init__(self, user):
		REDIS_URL = os.getenv('REDIS_URL')
		if not REDIS_URL:
			raise Exception('No Redis configuration in environment variables!')
		super().__init__(user)
		self.db = redis.Redis.from_url(REDIS_URL)
		self.user = user

	@retry(tries=5, delay=0.1)
	def send(self, score, ctx, details=False):
		p = self.db.pipeline()
		dist_list = ctx.get('debug',{}).get('model.query.resp',{}).get('dist_list',[])
		# feedback
		index = ctx.get('index',{})
		data = {}
		data['user'] = self.user
		data['task-prompt-version'] = ctx.get('task_name')
		data['model'] = ctx.get('model')
		data['model-embeddings'] = ctx.get('model_embed')
		data['task-prompt'] = ctx.get('task')
		data['temperature'] = ctx.get('temperature')
		data['frag-size'] = ctx.get('frag_size')
		data['frag-cnt'] = ctx.get('max_frags')
		data['frag-n-before'] = ctx.get('n_frag_before')
		data['frag-n-after'] = ctx.get('n_frag_after')
		data['filename'] = ctx.get('filename')
		data['filehash'] = index.get('hash') or index.get('filehash')
		data['filesize'] = index.get('filesize')
		data['n-pages'] = index.get('n_pages')
		data['n-texts'] = index.get('n_texts')
		data['use-hyde'] = as_int(ctx.get('use_hyde'))
		data['use-hyde-summary'] = as_int(ctx.get('use_hyde_summary'))
		data['question'] = ctx.get('question')
		data['answer'] = ctx.get('answer')
		data['hyde-summary'] = index.get('summary')
		data['resp-dist-list'] = '|'.join([f"{x:0.3f}" for x in dist_list])
		fb_hash = hexdigest(str(list(sorted(data.items()))))
		#
		data['score'] = score
		data['datetime'] = str(datetime.datetime.now())
		key1 = f'feedback:v2:{fb_hash}'
		if not details:
			for k in ['question','answer','hyde-summary']:
				data[k] = ''
		p.hset(key1, mapping=data)
		# feedback-daily
		date = datetime.date.today()
		key2 = f'feedback-daily:v1:{date}:{"positive" if score > 0 else "negative"}'
		p.sadd(key2, fb_hash)
		# feedback-score
		key3 = f'feedback-score:v2:{self.user}'
		p.sadd(key3, fb_hash)
		p.execute()
	
	@retry(tries=5, delay=0.1)
	def get_score(self):
		key = f'feedback-score:v2:{self.user}'
		return self.db.scard(key)


def get_feedback_adapter(user):
	MODE = os.getenv('FEEDBACK_MODE','').upper()
	if MODE=='REDIS':
		return RedisFeedback(user)
	else:
		return Feedback(user)
