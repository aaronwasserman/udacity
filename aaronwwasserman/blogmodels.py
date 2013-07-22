import logging
import time
import random
import hashlib
import string

from google.appengine.ext import db
from datetime import timedelta
from google.appengine.api import memcache


# Used in memcache
USERNAME_PREFIX = 'aw_blog_user-'
BLOG_PREFIX = 'aw_blog_postID-'


"""
class User(db.Model)
Defines the "User" object for the blog.

All users will have a username, password, salt (for checking their hashed password),
and date created.  Email address is optional.
"""		
class User(db.Model):
	username = db.StringProperty(required = True)
	salt = db.StringProperty(required = True)
	password = db.StringProperty()	
	email = db.EmailProperty()
	created = db.DateTimeProperty(auto_now_add = True)
	
	
	
	@classmethod
	def get_user(cls, username):
		user = memcache.get(USERNAME_PREFIX + username)
		if not user:
			query = User.all()
			logging.error('DB lookup for username: %s' % username)
			query.filter("username =", username)
			user = query.get()
			if user:
				memcache.set(USERNAME_PREFIX + user.username, user)
				
		return user

	

	@classmethod
	def hash_pass(cls, password, salt):
		return hashlib.md5(salt + password).hexdigest()
		
		
		
	@classmethod
	def make_salt(cls):
		return "".join(random.choice(string.letters) for x in xrange(5))



	@classmethod
	def insert(cls, user):
		user.put()
		memcache.set(USERNAME_PREFIX + user.username, user)


	
	@classmethod
	def create(cls, user_form):
		user = User(username = user_form.get('username'), salt = cls.make_salt())
		user.password = cls.hash_pass(user_form.get('password'), user.salt)
		if user_form.get('email'):
			user.email = user_form.get('email')
		
		cls.insert(user)
		uid = str(user.key().id())
		
		return user


	
	@classmethod
	def check_pass(cls, user, password):
		if user and password:
			return user.password == cls.hash_pass(password, user.salt)
		else:
			return False
		




"""
class Blog(db.Model)
Defines the "Blog" object.

All blogs will have a subject, content, date created,
and time delta object for storing last cache point.

Helper methods include:
-most_recents: get 10 most recent blogs from memcache (or db)
-get_blog: get a single blog by id (from memcache or db)
-create: creates a new instance of Blog
"""			
class Blog(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_cached = timedelta()
	cache_age = db.IntegerProperty()
	
	
	
	@classmethod
	def flush_blog(cls, blog_id):
		memcache.delete(BLOG_PREFIX + blog_id)



	@classmethod
	def get_seconds(cls):
		return timedelta(seconds=time.time())



	@classmethod
	def cache_delta(cls, last_cached):
		now = cls.get_seconds()
		delta = (now - last_cached).total_seconds()
		return int(delta)



	@classmethod
	def most_recents(cls):
		front_page = memcache.get('front_page')
		
		if front_page:
			front_cache = memcache.get('front_cache')

		else:
			front_page = db.GqlQuery('SELECT * FROM Blog ORDER BY created DESC LIMIT 10')
			front_cache = cls.get_seconds()
			memcache.set('front_page', front_page)
			memcache.set('front_cache', front_cache)
		
		cache_age = cls.cache_delta(front_cache)

		return front_page, cache_age



	@classmethod	
	def get_blog(cls, blog_id):
		blog = memcache.get(BLOG_PREFIX + blog_id)
		
		if blog:
			blog.cache_age = cls.cache_delta(blog.last_cached)
		else:
			blog = Blog.get_by_id(int(blog_id))

			if blog:
				blog.last_cached = cls.get_seconds()
				blog.cache_age = cls.cache_delta(blog.last_cached)
				memcache.set(BLOG_PREFIX + blog_id, blog)

		return blog
	
	
	
	@classmethod	
	def create(cls, user_form):
		subject = user_form.get('subject')
		content = user_form.get('content')
		
		if not subject or not content:
			return None
		
		blog = Blog(subject = subject, content = content)
		blog.last_cached = cls.get_seconds()

		blog.put()
		blog_id = str(blog.key().id())

		memcache.set(BLOG_PREFIX + blog_id, blog)
		memcache.delete('front_page')

		return blog_id



