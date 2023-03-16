import redis
from time import strftime
import os
from retry import retry

class Stats:
	def __init__(self):
		self.config = {}
	
	def render(self, key):
		variables = dict(
			date = strftime('%Y-%m-%d'),
			hour = strftime('%H'),
		)
		variables.update(self.config)
		for k,v in variables.items():
			key = key.replace('['+k+']',v)
		return key
	

class DictStats(Stats):
	def __init__(self, data_dict):
		self.data = data_dict
		self.config = {}
	
	def incr(self, key, kv_dict):
		data = self.data
		key = self.render(key)
		if key not in data:
			data[key] = {}
		for member,val in kv_dict.items():
			member = self.render(member)
			data[key][member] = data[key].get(member,0) + val
	
	def get(self, key):
		key = self.render(key)
		return self.data.get(key, {})


class RedisStats(Stats):
	def __init__(self):
		REDIS_URL = os.getenv('REDIS_URL')
		if not REDIS_URL:
			raise Exception('No Redis configuration in environment variables!')
		self.db = redis.Redis.from_url(REDIS_URL)
		self.config = {}
	
	@retry(tries=5, delay=0.1)
	def incr(self, key, kv_dict):
		# TODO: non critical code -> safe exceptions
		key = self.render(key)
		p = self.db.pipeline()
		for member,val in kv_dict.items():
			member = self.render(member)
			self.db.zincrby(key, val, member)
		p.execute()
	
	@retry(tries=5, delay=0.1)
	def get(self, key):
		# TODO: non critical code -> safe exceptions
		key = self.render(key)
		items = self.db.zscan_iter(key)
		return {k.decode('utf8'):v for k,v in items}


stats_data_dict = {}
def get_stats(**kw):
	MODE = os.getenv('STATS_MODE','').upper()
	if MODE=='REDIS':
		stats = RedisStats()
	else:
		stats = DictStats(stats_data_dict)
	stats.config.update(kw)
	return stats



if __name__=="__main__":
	s1 = get_stats(user='maciek')
	s1.incr('aaa:[date]:[user]', dict(a=1,b=2))
	s1.incr('aaa:[date]:[user]', dict(a=1,b=2))
	print(s1.data)
	print(s1.get('aaa:[date]:[user]'))
	#
	s2 = get_stats(user='kerbal')
	s2.incr('aaa:[date]:[user]', dict(a=1,b=2))
	s2.incr('aaa:[date]:[user]', dict(a=1,b=2))
	print(s2.data)
	print(s2.get('aaa:[date]:[user]'))

