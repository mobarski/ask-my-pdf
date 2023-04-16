from retry import retry

from binascii import hexlify,unhexlify
import pickle
import zlib
import io
import os

# pip install boto3
import boto3
import botocore

class Cache:
	"Dummy / Base Cache"
	def __init__(self):
		pass
	
	def put(self, key, obj):
		pass
	
	def get(self, key):
		return None
	
	def has(self, key):
		return False
	
	def delete(self, key):
		pass

	def serialize(self, obj):
		pickled = pickle.dumps(obj)
		compressed = self.compress(pickled)
		return compressed
	
	def deserialize(self, data):
		pickled = self.decompress(data)
		obj = pickle.loads(pickled)
		return obj

	def compress(self, data):
		return zlib.compress(data)
	
	def decompress(self, data):
		return zlib.decompress(data)

	def encode(self, name):
		return hexlify(name.encode('utf8')).decode('utf8')
	
	def decode(self, name):
		return unhexlify(name).decode('utf8')
	
	def call(self, key, fun, *a, **kw):
		if self.has(key):
			return self.get(key)
		else:
			resp = fun(*a, **kw)
			self.put(key, resp)
			return resp


class DiskCache(Cache):
	"Local disk based cache"

	def __init__(self, root):
		self.root = root
	
	def path(self, key):
		return os.path.join(self.root, self.encode(key))
	
	def put(self, key, obj):
		path = self.path(key)
		data = self.serialize(obj)
		with open(path, 'wb') as f:
			f.write(data)
	
	def get(self, key):
		path = self.path(key)
		with open(path, 'rb') as f:
			data = f.read()
		obj = self.deserialize(data)
		return obj

	def has(self, key):
		path = self.path(key)
		return os.path.exists(path)

	def delete(self, key):
		path = self.path(key)
		os.remove(path)


class S3Cache(Cache):
	"S3 based cache"

	def __init__(self, **kw):
		bucket = kw.get('bucket') or os.getenv('S3_CACHE_BUCKET','ask-my-pdf')
		prefix = kw.get('prefix') or os.getenv('S3_CACHE_PREFIX','cache/x1')
		region = kw.get('region') or os.getenv('S3_REGION','sfo3')
		url    = kw.get('url')    or os.getenv('S3_URL',f'https://{region}.digitaloceanspaces.com')
		key    = os.getenv('S3_KEY','')
		secret = os.getenv('S3_SECRET','')
		#
		if not key or not secret:
			raise Exception("No S3 credentials in environment variables!")
		#
		self.session = boto3.session.Session()
		self.s3 = self.session.client('s3',
				config=botocore.config.Config(s3={'addressing_style': 'virtual'}),
				region_name=region,
				endpoint_url=url,
				aws_access_key_id=key,
				aws_secret_access_key=secret,
			)
		self.bucket = bucket
		self.prefix = prefix

	def get_s3_key(self, key):
		return f'{self.prefix}/{key}'
	
	def put(self, key, obj):
		s3_key = self.get_s3_key(key)
		data = self.serialize(obj)
		f = io.BytesIO(data)
		self.s3.upload_fileobj(f, self.bucket, s3_key)

	def get(self, key, default=None):
		s3_key = self.get_s3_key(key)
		f = io.BytesIO()
		try:
			self.s3.download_fileobj(self.bucket, s3_key, f)
		except:
			f.close()
			return default
		f.seek(0)
		data = f.read()
		obj = self.deserialize(data)
		return obj
	
	def has(self, key):
		s3_key = self.get_s3_key(key)
		try:
			self.s3.head_object(Bucket=self.bucket, Key=s3_key)
			return True
		except:
			return False
	
	def delete(self, key):
		self.s3.delete_object(
			Bucket = self.bucket,
			Key = self.get_s3_key(key))


def get_cache(**kw):
	mode = os.getenv('CACHE_MODE','').upper()
	path = os.getenv('CACHE_PATH','')
	if mode == 'DISK':
		return DiskCache(path)
	elif mode == 'S3':
		return S3Cache(**kw)
	else:
		return Cache()


if __name__=="__main__":
	#cache = DiskCache('__pycache__')
	cache = S3Cache()
	cache.put('xxx',{'a':1,'b':22})
	print('get xxx', cache.get('xxx'))
	print('has xxx', cache.has('xxx'))
	print('has yyy', cache.has('yyy'))
	print('delete xxx', cache.delete('xxx'))
	print('has xxx', cache.has('xxx'))
	print('get xxx', cache.get('xxx'))
	#
