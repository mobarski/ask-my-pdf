"Storage adapter - one folder for each user / api_key"

# pip install pycryptodome
# REF: https://www.pycryptodome.org/src/cipher/aes
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad,unpad

from retry import retry

from binascii import hexlify,unhexlify
import hashlib
import pickle
import zlib
import os
import io

# pip install boto3
import boto3
import botocore

SALT = unhexlify(os.getenv('STORAGE_SALT','00'))

class Storage:
	"Encrypted object storage (base class)"
	
	def __init__(self, secret_key):
		k = secret_key.encode()
		self.folder = hashlib.blake2s(k, salt=SALT, person=b'folder', digest_size=8).hexdigest()
		self.passwd = hashlib.blake2s(k, salt=SALT, person=b'passwd', digest_size=32).hexdigest()
		self.AES_MODE = AES.MODE_ECB # TODO: better AES mode ???
		self.AES_BLOCK_SIZE = 16
	
	def get(self, name, default=None):
		"get one object from the folder"
		safe_name = self.encode(name)
		data = self._get(safe_name)
		obj = self.deserialize(data)
		return obj
	
	def put(self, name, obj):
		"put the object into the folder"
		safe_name = self.encode(name)
		data = self.serialize(obj)
		self._put(safe_name, data)
		return data

	def list(self):
		"list object names from the folder"
		return [self.decode(name) for name in self._list()]

	def delete(self, name):
		"delete the object from the folder"
		safe_name = self.encode(name)
		self._delete(safe_name)
	
	# IMPLEMENTED IN SUBCLASSES
	def _put(self, name, data):
		...
	def _get(self, name):
		...	
	def _delete(self, name):
		pass
	def _list(self):
		...
	
	# # #
	
	def serialize(self, obj):
		raw = pickle.dumps(obj)
		compressed = self.compress(raw)
		encrypted = self.encrypt(compressed)
		return encrypted
	
	def deserialize(self, encrypted):
		compressed = self.decrypt(encrypted)
		raw = self.decompress(compressed)
		obj = pickle.loads(raw)
		return obj

	def encrypt(self, raw):
		cipher = AES.new(unhexlify(self.passwd), self.AES_MODE)
		return cipher.encrypt(pad(raw, self.AES_BLOCK_SIZE))
	
	def decrypt(self, encrypted):
		cipher = AES.new(unhexlify(self.passwd), self.AES_MODE)
		return unpad(cipher.decrypt(encrypted), self.AES_BLOCK_SIZE)

	def compress(self, data):
		return zlib.compress(data)
	
	def decompress(self, data):
		return zlib.decompress(data)
	
	def encode(self, name):
		return hexlify(name.encode('utf8')).decode('utf8')
	
	def decode(self, name):
		return unhexlify(name).decode('utf8')


class DictStorage(Storage):
	"Dictionary based storage"
	
	def __init__(self, secret_key, data_dict):
		super().__init__(secret_key)
		self.data = data_dict
		
	def _put(self, name, data):
		if self.folder not in self.data:
			self.data[self.folder] = {}
		self.data[self.folder][name] = data
		
	def _get(self, name):
		return self.data[self.folder][name]
	
	def _list(self):
		# TODO: sort by modification time (reverse=True)
		return list(self.data.get(self.folder,{}).keys())
	
	def _delete(self, name):
		del self.data[self.folder][name]


class LocalStorage(Storage):
	"Local filesystem based storage"
	
	def __init__(self, secret_key, path):
		if not path:
			raise Exception('No storage path in environment variables!')
		super().__init__(secret_key)
		self.path = os.path.join(path, self.folder)
		if not os.path.exists(self.path):
			os.makedirs(self.path)
	
	def _put(self, name, data):
		with open(os.path.join(self.path, name), 'wb') as f:
			f.write(data)

	def _get(self, name):
		with open(os.path.join(self.path, name), 'rb') as f:
			data = f.read()
		return data
	
	def _list(self):
		# TODO: sort by modification time (reverse=True)
		return os.listdir(self.path)
	
	def _delete(self, name):
		os.remove(os.path.join(self.path, name))


class S3Storage(Storage):
	"S3 based encrypted storage"
	
	def __init__(self, secret_key, **kw):
		prefix = kw.get('prefix') or os.getenv('S3_PREFIX','index/x1')
		region = kw.get('region') or os.getenv('S3_REGION','sfo3')
		bucket = kw.get('bucket') or os.getenv('S3_BUCKET','ask-my-pdf')
		url    = kw.get('url')    or os.getenv('S3_URL',f'https://{region}.digitaloceanspaces.com')
		key    = os.getenv('S3_KEY','')
		secret = os.getenv('S3_SECRET','')
		#
		if not key or not secret:
			raise Exception("No S3 credentials in environment variables!")
		#
		super().__init__(secret_key)
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
	
	def get_key(self, name):
		return f'{self.prefix}/{self.folder}/{name}'
	
	def _put(self, name, data):
		key = self.get_key(name)
		f = io.BytesIO(data)
		self.s3.upload_fileobj(f, self.bucket, key)
	
	def _get(self, name):
		key = self.get_key(name)
		f = io.BytesIO()
		self.s3.download_fileobj(self.bucket, key, f)
		f.seek(0)
		return f.read()
	
	def _list(self):
		resp = self.s3.list_objects(
				Bucket=self.bucket,
				Prefix=self.get_key('')
			)
		contents = resp.get('Contents',[])
		contents.sort(key=lambda x:x['LastModified'], reverse=True)
		keys = [x['Key'] for x in contents]
		names = [x.split('/')[-1] for x in keys]
		return names
	
	def _delete(self, name):
		self.s3.delete_object(
				Bucket=self.bucket,
				Key=self.get_key(name)
			)

def get_storage(api_key, data_dict):
	"get storage adapter configured in environment variables"
	mode = os.getenv('STORAGE_MODE','').upper()
	path = os.getenv('STORAGE_PATH','')
	if mode=='S3':
		storage = S3Storage(api_key)
	elif mode=='LOCAL':
		storage = LocalStorage(api_key, path)
	else:
		storage = DictStorage(api_key, data_dict)
	return storage
