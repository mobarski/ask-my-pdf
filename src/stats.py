import redis
from time import strftime
import os

class Stats:
	def __init__(self, user):
		self.user = user
	
	def render(self, key):
		# "usage:v1:{date}:{user}"
		variables = dict(
			date = strftime('%Y-%m-%d'),
			hour = strftime('%H'),
			user = self.user,
		)
		for k,v in variables.items():
			key = key.replace('{'+k+'}',v)
		return key
	

class DictStats(Stats):
	def __init__(self, user, data_dict):
		super().__init__(user)
		self.data = data_dict
	
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
		return self.data[key]


class RedisStats(Stats):
	def __init__(self, user):
		REDIS_URL = os.getenv('REDIS_URL')
		if not REDIS_URL:
			raise Exception('No Redis configuration in environment variables!')
		super().__init__(user)
		self.db = redis.Redis.from_url(REDIS_URL)
	
	def incr(self, key, kv_dict):
		# TODO: non critical code -> safe exceptions
		key = self.render(key)
		p = self.db.pipeline()
		for member,val in kv_dict.items():
			member = self.render(member)
			self.db.zincrby(key, val, member)
		p.execute()
	
	def get(self, key):
		# TODO: non critical code -> safe exceptions
		key = self.render(key)
		items = self.db.zscan_iter(key)
		return {k.decode('utf8'):v for k,v in items}


def get_stats(user):
	STATS_MODE = os.getenv('STATS_MODE','').upper()
	if STATS_MODE=='REDIS':
		return RedisStats(user)
	else:
		data_dict = {} # TODO: passed to get_stats
		return DictStats(user, data_dict)


if __name__=="__main__":
	s = get_stats('MACIEK')
	s.incr('aaa:{date}:{user}', dict(a=1,b=2))
	s.incr('aaa:{date}:{user}', dict(a=1,b=2))
	print(s.data)
	print(s.get('aaa:{date}:{user}'))

