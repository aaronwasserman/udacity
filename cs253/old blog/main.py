#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import os
import jinja2
import re
import hashlib
import string
import random
import json
import time

from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import timedelta

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class Blog(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = timedelta(seconds=time.time())

		
class User(db.Model):
	username = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	salt = db.StringProperty()
	email = db.EmailProperty()
	created = db.DateTimeProperty(auto_now_add = True)


def username_exists(username):
	u = User.all()
	u.filter("username =", username)
	return True if u.get() else False


class Handler(webapp2.RequestHandler):	
	def get_blogs(self, key='front_page'):
		front_query = 'SELECT * FROM Blog ORDER BY created DESC LIMIT 10'
		age_key = 'cache_time'

		blog_list = memcache.get(key)
		if blog_list is None:
			blog_list = db.GqlQuery(front_query)
			memcache.set(key, blog_list)
			memcache.set(age_key, self.get_secs())

		return blog_list


	def get_secs(self):
		t = timedelta(seconds=time.time())
		return t
			

	def write(self, *a, **lw):
		self.response.out.write(*a, **lw)


	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)


	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))
			

	def blog_as_dict(self, blog):
		return json.dumps({'content' : blog.content, 'subject' : blog.subject, 
							'created' : blog.created.strftime('%b %d, %Y')})


class MainPage(Handler):
    def get(self, flush=None):
    	if flush:
    		memcache.flush_all()
    		self.redirect('/')
    		
        blog_list = self.get_blogs()
        age = (self.get_secs() - memcache.get('cache_time')).total_seconds()
        self.render("blog_home.html", blogs = blog_list, cache_age = age)


class MainPageJSON(MainPage):
	def get(self):
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		blog_list = db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC LIMIT 10")      
		j = []
		for blog in blog_list:
			j.append(self.blog_as_dict(blog))
		self.write(json.dumps(j))


class NewPost(Handler):
	def render_newPost(self, subject="", content="", posts="", error=""):
		self.render("blog_newpost.html", subject = subject, content = content,
					error = error)
		
	def get(self):
		self.render_newPost()

	def post(self):
		subject = self.request.get("subject")
		content = self.request.get("content")
		
		if subject and content:
			blog = Blog(subject = subject, content = content)
			blog.put()
			blog_key = str(blog.key().id())
			blog.last_modified = self.get_secs()
			memcache.set(blog_key, blog)
			memcache.delete('front_page')
			self.redirect("/" + blog_key)
		else:		
			self.render_newPost(subject = subject, content = content,
								error = "Please provide both subject and blog content.")
        

class PermaPage(Handler):
	def get_blog_at_id(self, blog_id):
		blog = memcache.get(blog_id)
		if blog is None:
			blog = Blog.get_by_id(int(blog_id))
			blog.last_modified = self.get_secs()
			memcache.set(blog_id, blog)
		return blog
		
		
	def get(self, blog_id):
		blog = self.get_blog_at_id(blog_id)
		age = (self.get_secs() - blog.last_modified).total_seconds()
		self.render("blog_home.html", blogs = [blog], cache_age = age)


class PermaPageJSON(Handler):
	def get(self, blog_id):
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		blog = Blog.get_by_id(int(blog_id))
		self.write(json.dumps(self.blog_as_dict(blog)))


class SignUp(Handler):
	def render_signup(self, username="", email="", username_error="", password_error="",
						verify_error="", email_error=""):
		self.render("blog_signup.html", username = username, email = email,
					username_error = username_error, password_error = password_error,
					verify_error = verify_error, email_error = email_error)
			
	def get(self):
		self.render_signup()
	
	
	def valid_email(self, email):
		EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
		if EMAIL_RE.match(email):
			return True
		else:
			return False
	
	
	def make_hash(self, input, salt=""):
		if not salt:
			salt = "".join(random.choice(string.letters) for x in xrange(5))
		return hashlib.md5(salt + input).hexdigest(), salt
	
	
	def add_new_user(self, username, password, email=""):
		hashed_pw, salt = self.make_hash(password)
		new_user = User(username = username, password = hashed_pw, salt = salt)
		if email:
			new_user.email = email
		new_user.put()
		new_user_id = str(new_user.key().id())
		self.response.headers.add_header('Set-Cookie','user_id=%s|%s;Path=/' %
										(new_user_id, hashed_pw))
		
	
	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		verify = self.request.get("verify")
		email = self.request.get("email")
		username_error = password_error = verify_error = email_error = ""
		
		# Username 3 - 20 characters?
		if len(username) < 3 or len(username) > 20:
			username_error = "Username must be 3-20 characters."
		# Does the username exist already?
		elif username_exists(username):
			username_error = "Username is already taken."
		# Password provided by user?
		if not password:
			password_error = "Password cannot be empty."
		# Passwords match?
		elif password != verify:
			verify_error = "Passwords must match."
		# If email provided, is it a valid email address?
		if email:
			if not self.valid_email(email):
				email_error = "Invalid email address."					

		if username_error == password_error == verify_error == email_error == "":
			self.add_new_user(username, password, email)
			self.redirect("/welcome")
		else:
			self.render_signup(username, email, username_error, password_error,
								verify_error, email_error)


class Login(Handler):
	def hash_pass(self, input, salt=""):
		if not salt:
			salt = "".join(random.choice(string.letters) for x in xrange(5))
		return hashlib.md5(salt + input).hexdigest()


	def get(self):
		self.render("blog_login.html")

	
	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		
		if username_exists(username):
			q = User.gql("WHERE username = '%s'" % username)
			user = q.get()
			if user.password == self.hash_pass(password, user.salt):
				self.response.headers.add_header('Set-Cookie','user_id=%s|%s; Path=/' % 
											(str(user.key().id()), str(user.password)))
				self.redirect("/welcome")
		else:
			self.render("blog_login.html", error = "Invalid login. Please try again.", 
						username = username)


class Logout(Handler):
	def get(self):
		self.response.headers.add_header('Set-Cookie','user_id=; Path=/')
		self.redirect('/')


class Welcome(SignUp):
	def get(self):
		cookie_id = self.request.cookies.get("user_id")
		if cookie_id:
			user_id = cookie_id.split("|")[0]
			hashed_pw = cookie_id.split("|")[1]
			u = User.get_by_id(int(user_id))

			if u and hashed_pw == u.password:			
				self.write("Welcome, %s!" % u.username)
		else:
			self.redirect("/login")
			
				
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/.json', MainPageJSON),
    ('/newpost', NewPost),
    ('/(\d+)', PermaPage),
    (r'/(\d+).json', PermaPageJSON),
    ('/signup', SignUp),
    ('/welcome', Welcome),
    ('/login', Login),
    ('/logout', Logout),
    ('/(flush)', MainPage),
], debug=True)


#self.response.headers['Content-Type'] = 'text/plain'